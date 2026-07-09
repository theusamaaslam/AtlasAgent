"""Generated Obsidian-compatible memory vault for Atlas.

The vault is a read-only projection over existing Atlas state:

* built-in curated memory files (MEMORY.md and USER.md)
* compact memory summaries, promoted facts, and source session evidence
* the checked-in creator profile

It deliberately does not become a second source of truth. Rebuilding the vault
is idempotent and safe; source data stays in the existing memory/session stores.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from hashlib import sha1
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from atlas_constants import get_atlas_home

logger = logging.getLogger(__name__)

VAULT_DIRNAME = "memory-vault"
GRAPH_JSON = ".atlas-memory-graph.json"
DIRTY_FILE = ".atlas-memory-vault.dirty"
CREATOR_PROFILE_PATH = (
    Path(__file__).resolve().parent.parent / "assets" / "creator-profile.md"
)

STOPWORDS = {
    "about", "after", "again", "agent", "also", "and", "are", "atlas", "because",
    "been", "before", "being", "between", "but", "can", "could", "does", "from",
    "have", "here", "into", "just", "like", "make", "more", "need", "needs",
    "only", "should", "that", "the", "their", "them", "then", "there", "these",
    "they", "this", "those", "through", "user", "using", "what", "when", "where",
    "which", "while", "with", "would", "your",
}


@dataclass
class VaultNode:
    id: str
    kind: str
    title: str
    path: str
    text: str = ""
    source: str = ""
    timestamp: Optional[float] = None
    session_id: Optional[str] = None
    source_message_id: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    importance: Optional[float] = None
    confidence: Optional[float] = None
    topics: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)


def get_memory_vault_dir(atlas_home: Optional[Path] = None) -> Path:
    return (atlas_home or get_atlas_home()) / VAULT_DIRNAME


def mark_memory_vault_dirty(atlas_home: Optional[Path] = None) -> None:
    """Best-effort marker that session state changed since the last sync."""
    try:
        home = atlas_home or get_atlas_home()
        home.mkdir(parents=True, exist_ok=True)
        (home / DIRTY_FILE).write_text(str(time.time()), encoding="utf-8")
    except Exception:
        logger.debug("Could not mark memory vault dirty", exc_info=True)


def _stable_id(prefix: str, text: str) -> str:
    return f"{prefix}-{sha1(text.encode('utf-8', errors='ignore')).hexdigest()[:12]}"


def _slug(text: str, *, fallback: str = "untitled") -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "-", text.strip()).strip("-").lower()
    return value[:80] or fallback


def _note_name(title: str, node_id: str) -> str:
    slug = _slug(title, fallback=node_id)
    return f"{slug}-{node_id[-8:]}.md"


def _escape_yaml(value: Any) -> str:
    if value is None:
        return '""'
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def _wikilink(title: str) -> str:
    return f"[[{title}]]"


def _topic_title(topic: str) -> str:
    return "Topic " + topic.replace("-", " ").title()


def _text_content(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for part in value:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(str(part.get("text") or ""))
        return " ".join(p for p in parts if p).strip() or "[multimodal content]"
    if value is None:
        return ""
    return str(value)


def _extract_topics(text: str, limit: int = 8) -> List[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_+#.-]{2,}", text)
    counts: Dict[str, int] = {}
    for raw in words:
        word = raw.strip("._-").lower()
        if len(word) < 3 or word in STOPWORDS:
            continue
        if word.isdigit():
            continue
        counts[word] = counts.get(word, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [_slug(word) for word, _count in ordered[:limit]]


def _read_memory_file(path: Path) -> List[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    entries: List[str] = []
    current: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            if current:
                entries.append("\n".join(current).strip())
                current = []
            current.append(stripped[2:].strip())
        elif stripped and current:
            current.append(stripped)
    if current:
        entries.append("\n".join(current).strip())
    if not entries and text.strip():
        entries = [chunk.strip() for chunk in re.split(r"\n\s*\n", text) if chunk.strip()]
    return list(dict.fromkeys(e for e in entries if e))


def _load_creator_profile() -> str:
    try:
        return CREATOR_PROFILE_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return (
            "Usama Aslam is the creator of Atlas Agent. He works on AI systems, "
            "LLM inference, MLOps, RAG/Graph RAG, MCP, observability, and AI security."
        )


def _source_nodes(atlas_home: Path, db: Any = None, session_limit: int = 5000) -> List[VaultNode]:
    nodes: List[VaultNode] = []
    mem_dir = atlas_home / "memories"

    creator_text = _load_creator_profile()
    nodes.append(
        VaultNode(
            id="creator-usama-aslam",
            kind="creator",
            title="Usama Aslam",
            path="Creator/Usama Aslam.md",
            text=creator_text,
            source="creator-profile",
            topics=_extract_topics(creator_text, 10),
        )
    )

    for target, folder, kind in (
        ("MEMORY.md", "Curated Memory", "memory"),
        ("USER.md", "User Profile", "user"),
    ):
        for idx, entry in enumerate(_read_memory_file(mem_dir / target), 1):
            node_id = _stable_id(kind, f"{target}:{entry}")
            title = f"{'Memory' if kind == 'memory' else 'User'} {idx}"
            nodes.append(
                VaultNode(
                    id=node_id,
                    kind=kind,
                    title=title,
                    path=f"{folder}/{_note_name(title, node_id)}",
                    text=entry,
                    source=target,
                    topics=_extract_topics(entry),
                )
            )

    close_db = False
    if db is None:
        try:
            from atlas_state import SessionDB

            db = SessionDB(read_only=True)
            close_db = True
        except Exception:
            logger.debug("Could not open session DB for memory vault", exc_info=True)
            db = None
    if db is not None:
        try:
            try:
                sessions = db.list_sessions_rich(
                    limit=session_limit,
                    include_archived=True,
                    include_children=True,
                    project_compression_tips=False,
                    order_by_last_active=True,
                )
            except TypeError:
                sessions = db.list_sessions_rich(limit=session_limit)

            for session in sessions:
                session_id = str(session.get("id") or "")
                if not session_id:
                    continue
                title = str(session.get("title") or session.get("preview") or f"Session {session_id[:8]}").strip()
                session_node_id = f"session-{_slug(session_id)}"
                session_title = f"Session {session_id[:8]}"
                session_text = (
                    f"{title}\n\nSource: {session.get('source') or 'unknown'}\n"
                    f"Model: {session.get('model') or 'unknown'}"
                )
                nodes.append(
                    VaultNode(
                        id=session_node_id,
                        kind="session",
                        title=session_title,
                        path=f"Sessions/{_note_name(session_title, session_node_id)}",
                        text=session_text,
                        source=str(session.get("source") or ""),
                        timestamp=session.get("started_at"),
                        session_id=session_id,
                        topics=_extract_topics(title),
                    )
                )

        finally:
            if close_db:
                try:
                    db.close()
                except Exception:
                    pass

    try:
        from agent.memory_facts import list_memory_facts, list_memory_summaries

        summary_res = list_memory_summaries(atlas_home=atlas_home, limit=1000)
        for idx, summary in enumerate(summary_res.get("summaries") or [], 1):
            status = str(summary.get("status") or "")
            if status in {"rejected"}:
                continue
            summary_id = str(summary.get("id") or _stable_id("summary", str(summary.get("text") or "")))
            title = f"Summary {idx}"
            session_id = str(summary.get("source_session_id") or "")
            links = []
            if session_id:
                links.append(f"session-{_slug(session_id)}")
            nodes.append(
                VaultNode(
                    id=summary_id,
                    kind="summary",
                    title=title,
                    path=f"Summaries/{_note_name(title, summary_id)}",
                    text=str(summary.get("text") or ""),
                    source="compact-summary",
                    timestamp=summary.get("updated_at") or summary.get("created_at"),
                    session_id=session_id or None,
                    source_message_id=str(summary.get("end_message_id") or "") or None,
                    role="summary",
                    status=status,
                    importance=summary.get("importance"),
                    confidence=summary.get("confidence"),
                    topics=list(summary.get("topics") or []),
                    links=links,
                )
            )

        fact_res = list_memory_facts(atlas_home=atlas_home, limit=1000)
        for idx, fact in enumerate(fact_res.get("facts") or [], 1):
            status = str(fact.get("status") or "")
            if status in {"rejected"}:
                continue
            fact_id = str(fact.get("id") or _stable_id("fact", str(fact.get("text") or "")))
            kind = str(fact.get("kind") or "fact")
            title = f"Fact {idx}: {kind.replace('_', ' ').title()}"
            session_id = str(fact.get("source_session_id") or "")
            source_message_id = str(fact.get("source_message_id") or "")
            links = []
            if session_id:
                links.append(f"session-{_slug(session_id)}")
            summary_id = (fact.get("metadata") or {}).get("source_summary_id")
            if summary_id:
                links.append(str(summary_id))
            nodes.append(
                VaultNode(
                    id=fact_id,
                    kind="fact",
                    title=title,
                    path=f"Facts/{_note_name(title, fact_id)}",
                    text=str(fact.get("text") or ""),
                    source="promoted-fact",
                    timestamp=fact.get("updated_at") or fact.get("created_at"),
                    session_id=session_id or None,
                    source_message_id=source_message_id or None,
                    role=str(fact.get("source_role") or "") or None,
                    status=status,
                    importance=fact.get("importance"),
                    confidence=fact.get("confidence"),
                    topics=list(fact.get("topics") or []),
                    links=links,
                )
            )
    except Exception:
        logger.debug("Could not load memory facts for vault", exc_info=True)

    return nodes


def _connect_nodes(nodes: List[VaultNode]) -> None:
    by_topic: Dict[str, List[VaultNode]] = {}
    for node in nodes:
        for topic in node.topics:
            by_topic.setdefault(topic, []).append(node)

    creator = next((n for n in nodes if n.kind == "creator"), None)
    for node in nodes:
        if creator and node.id != creator.id and re.search(r"\busama\b|\baslam\b|creator", node.text, re.I):
            node.links.append(creator.id)
        for topic in node.topics[:6]:
            node.links.append(f"topic-{topic}")
            peers = [p for p in by_topic.get(topic, []) if p.id != node.id]
            for peer in peers[:3]:
                if peer.kind in {"memory", "user", "creator", "fact", "summary"} or node.kind in {"memory", "user", "fact", "summary"}:
                    node.links.append(peer.id)
        node.links = sorted(set(node.links))


def _topic_nodes(nodes: List[VaultNode]) -> List[VaultNode]:
    topics = sorted({topic for node in nodes for topic in node.topics})
    result: List[VaultNode] = []
    for topic in topics:
        title = _topic_title(topic)
        result.append(
            VaultNode(
                id=f"topic-{topic}",
                kind="topic",
                title=title,
                path=f"Topics/{_note_name(title, 'topic-' + topic)}",
                text=f"Generated topic node for `{topic}`.",
                source="generated",
                topics=[],
            )
        )
    return result


def _write_note(vault: Path, node: VaultNode, by_id: Dict[str, VaultNode]) -> None:
    path = vault / node.path
    path.parent.mkdir(parents=True, exist_ok=True)
    backlinks = [by_id[link] for link in node.links if link in by_id]
    frontmatter = [
        "---",
        f"type: {node.kind}",
        "atlas_generated: true",
        f"id: {_escape_yaml(node.id)}",
        f"source: {_escape_yaml(node.source)}",
    ]
    if node.session_id:
        frontmatter.append(f"session_id: {_escape_yaml(node.session_id)}")
    if node.source_message_id:
        frontmatter.append(f"source_message_id: {_escape_yaml(node.source_message_id)}")
    if node.role:
        frontmatter.append(f"role: {_escape_yaml(node.role)}")
    if node.status:
        frontmatter.append(f"status: {_escape_yaml(node.status)}")
    if node.importance is not None:
        frontmatter.append(f"importance: {_escape_yaml(node.importance)}")
    if node.confidence is not None:
        frontmatter.append(f"confidence: {_escape_yaml(node.confidence)}")
    if node.timestamp is not None:
        frontmatter.append(f"timestamp: {_escape_yaml(node.timestamp)}")
    if node.topics:
        frontmatter.append("topics:")
        for topic in node.topics:
            frontmatter.append(f"  - {topic}")
    frontmatter.append("---")

    body = [
        *frontmatter,
        "",
        f"# {node.title}",
        "",
        node.text.strip() or "_No content._",
        "",
    ]
    if backlinks:
        body.extend(["## Links", ""])
        body.extend(f"- {_wikilink(item.title)}" for item in backlinks[:40])
        body.append("")
    path.write_text("\n".join(body).rstrip() + "\n", encoding="utf-8")


def _write_index(vault: Path, nodes: List[VaultNode]) -> None:
    counts: Dict[str, int] = {}
    for node in nodes:
        counts[node.kind] = counts.get(node.kind, 0) + 1
    lines = [
        "---",
        "type: atlas-memory-index",
        "atlas_generated: true",
        f"generated_at: {_escape_yaml(time.time())}",
        "---",
        "",
        "# Atlas Memory",
        "",
        "Generated Obsidian vault for Atlas Agent memory and interactions.",
        "",
        "## Creator",
        "",
        "- [[Usama Aslam]]",
        "",
        "## Counts",
        "",
    ]
    for kind in sorted(counts):
        lines.append(f"- {kind}: {counts[kind]}")
    lines.extend(["", "## Main Areas", "", "- [[Usama Aslam]]"])
    for title in ("Curated Memory", "User Profile", "Sessions", "Summaries", "Facts", "Topics"):
        lines.append(f"- {title}")
    (vault / "Atlas Memory.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def sync_memory_vault(
    *,
    atlas_home: Optional[Path] = None,
    db: Any = None,
    session_limit: int = 5000,
) -> Dict[str, Any]:
    """Regenerate the Obsidian vault and return graph metadata."""
    home = atlas_home or get_atlas_home()
    vault = get_memory_vault_dir(home)
    vault.mkdir(parents=True, exist_ok=True)

    for name in ("Creator", "Curated Memory", "User Profile", "Sessions", "Summaries", "Facts", "Topics"):
        shutil.rmtree(vault / name, ignore_errors=True)

    nodes = _source_nodes(home, db=db, session_limit=session_limit)
    _connect_nodes(nodes)
    nodes.extend(_topic_nodes(nodes))
    by_id = {node.id: node for node in nodes}

    for node in nodes:
        _write_note(vault, node, by_id)
    _write_index(vault, nodes)

    edges = []
    for node in nodes:
        for target in node.links:
            if target in by_id:
                edges.append({"source": node.id, "target": target})

    plural = {
        "creator": "creators",
        "interaction": "interactions",
        "fact": "facts",
        "memory": "memories",
        "session": "sessions",
        "summary": "summaries",
        "topic": "topics",
        "user": "user_profile",
    }
    stats: Dict[str, int] = {}
    for node in nodes:
        key = plural.get(node.kind, node.kind + "s")
        stats[key] = stats.get(key, 0) + 1

    payload = {
        "ok": True,
        "vault_path": str(vault),
        "last_sync": time.time(),
        "dirty": False,
        "stats": stats,
        "nodes": [
            {
                "id": node.id,
                "kind": node.kind,
                "title": node.title,
                "path": node.path,
                "source": node.source,
                "timestamp": node.timestamp,
                "session_id": node.session_id,
                "source_message_id": node.source_message_id,
                "role": node.role,
                "status": node.status,
                "importance": node.importance,
                "confidence": node.confidence,
                "topics": node.topics,
                "links": node.links,
                "snippet": node.text[:240],
            }
            for node in nodes
        ],
        "edges": edges,
    }
    (vault / GRAPH_JSON).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        (home / DIRTY_FILE).unlink()
    except FileNotFoundError:
        pass
    return payload


def memory_vault_status(*, atlas_home: Optional[Path] = None) -> Dict[str, Any]:
    home = atlas_home or get_atlas_home()
    vault = get_memory_vault_dir(home)
    graph_path = vault / GRAPH_JSON
    dirty = (home / DIRTY_FILE).exists()
    if graph_path.exists():
        try:
            payload = json.loads(graph_path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
    else:
        payload = {}
    return {
        "ok": True,
        "vault_path": str(vault),
        "exists": graph_path.exists(),
        "dirty": dirty or bool(payload.get("dirty")),
        "last_sync": payload.get("last_sync"),
        "stats": payload.get("stats") or {},
    }


def memory_vault_graph(*, atlas_home: Optional[Path] = None) -> Dict[str, Any]:
    home = atlas_home or get_atlas_home()
    graph_path = get_memory_vault_dir(home) / GRAPH_JSON
    if not graph_path.exists() or (home / DIRTY_FILE).exists():
        return sync_memory_vault(atlas_home=home)
    payload = json.loads(graph_path.read_text(encoding="utf-8"))
    payload["dirty"] = (home / DIRTY_FILE).exists()
    return payload


def search_memory_vault(query: str, *, limit: int = 20, db: Any = None, atlas_home: Optional[Path] = None) -> Dict[str, Any]:
    home = atlas_home or get_atlas_home()
    q = (query or "").strip().lower()
    if not q:
        return {"ok": True, "query": query, "results": []}

    results: List[Dict[str, Any]] = []
    for node in _source_nodes(home, db=db, session_limit=250):
        hay = f"{node.title}\n{node.text}\n{' '.join(node.topics)}".lower()
        if q in hay:
            results.append(
                {
                    "kind": node.kind,
                    "title": node.title,
                    "snippet": node.text[:360],
                    "path": node.path,
                    "source": node.source,
                    "timestamp": node.timestamp,
                    "session_id": node.session_id,
                    "role": node.role,
                    "topics": node.topics,
                }
            )
        if len(results) >= limit:
            break

    if len(results) < limit:
        close_db = False
        if db is None:
            try:
                from atlas_state import SessionDB
                db = SessionDB(read_only=True)
                close_db = True
            except Exception:
                db = None
        try:
            if db is not None:
                for row in db.search_messages(query, limit=limit - len(results), sort="newest"):
                    results.append(
                        {
                            "kind": "interaction",
                            "title": f"{row.get('role', 'message').title()} in {str(row.get('session_id', ''))[:8]}",
                            "snippet": str(row.get("snippet") or ""),
                            "path": f"Interactions/",
                            "source": row.get("source") or "",
                            "timestamp": row.get("timestamp"),
                            "session_id": row.get("session_id"),
                            "role": row.get("role"),
                            "topics": _extract_topics(str(row.get("snippet") or "")),
                        }
                    )
        finally:
            if close_db:
                try:
                    db.close()
                except Exception:
                    pass

    return {"ok": True, "query": query, "results": results[:limit]}


def open_memory_vault(*, atlas_home: Optional[Path] = None) -> Dict[str, Any]:
    vault = get_memory_vault_dir(atlas_home)
    vault.mkdir(parents=True, exist_ok=True)
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(vault))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(vault)])
        else:
            subprocess.Popen(["xdg-open", str(vault)])
        return {"ok": True, "vault_path": str(vault)}
    except Exception as exc:
        return {"ok": False, "vault_path": str(vault), "error": str(exc)}
