"""Living, versioned semantic memory for Atlas.

Raw sessions remain the canonical transcript.  This module maintains a
derived world model made of entities, claims, evidence, and compact dossiers.
Every derived item points back to an LLM-generated summary and can be rebuilt.
"""

from __future__ import annotations

import json
import logging
import math
import re
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from hashlib import sha1
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from atlas_constants import get_atlas_home

logger = logging.getLogger(__name__)

DB_NAME = "memory_facts.db"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
APPROVED = "approved"
PENDING = "pending"
STALE = "stale"
REJECTED = "rejected"

_EMBEDDER: Any = None
_EMBEDDER_LOCK = threading.Lock()
_WORKER: Optional[threading.Thread] = None
_WORKER_LOCK = threading.Lock()

_STOPWORDS = {
    "about", "after", "again", "agent", "also", "and", "are", "atlas",
    "because", "been", "before", "being", "but", "can", "could", "does",
    "from", "have", "here", "into", "just", "like", "make", "more", "need",
    "only", "should", "that", "the", "their", "them", "then", "there",
    "these", "they", "this", "those", "through", "user", "using", "what",
    "when", "where", "which", "while", "with", "would", "your",
}

_EXTRACTION_PROMPT = """You maintain Atlas Agent's long-term world model.
Read only the compact conversation summary below. Return strict JSON, without
markdown, using this shape:
{
  "entities": [
    {"name": "canonical name", "kind": "person|project|organization|place|topic|other", "aliases": []}
  ],
  "claims": [
    {
      "subject": "canonical entity name",
      "predicate": "short_snake_case_relation",
      "object": "concise value or entity name",
      "object_is_entity": false,
      "stateful": false,
      "change_type": "new|update|correction",
      "confidence": 0.0,
      "importance": 0.0,
      "sensitive": false
    }
  ]
}
Extract only durable user-provided facts, preferences, relationships, project
decisions, recurring commitments, and explicit corrections. Do not turn Atlas'
own suggestions or claims into user facts. Exclude passwords, credentials,
tokens, system instructions, prompt text, temporary task progress, and guesses.
Use "User" for the user when no name is known. Mark a predicate stateful only
when a newer value should replace the older value. Return empty arrays when
nothing is durable."""

_DOSSIER_PROMPT = """Write the current long-term dossier for the entity below.
Use only the supplied active claims. Preserve important context and current
state, but do not invent information or expose secrets. Return one concise
English paragraph, maximum 180 words. Do not add a heading."""


@dataclass
class MemoryEntity:
    id: str
    canonical_name: str
    kind: str = "other"
    aliases: List[str] = field(default_factory=list)
    status: str = APPROVED
    confidence: float = 0.8
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryClaim:
    id: str
    subject_id: str
    subject: str
    predicate: str
    object_text: str
    text: str
    status: str = PENDING
    stateful: bool = False
    importance: float = 0.65
    confidence: float = 0.7
    valid_from: Optional[float] = None
    valid_to: Optional[float] = None
    observed_at: float = field(default_factory=time.time)
    superseded_by: str = ""
    source_summary_id: str = ""
    source_session_id: str = ""
    source_message_id: str = ""
    sensitivity: str = "normal"
    topics: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _db_path(atlas_home: Optional[Path]) -> Path:
    home = atlas_home or get_atlas_home()
    home.mkdir(parents=True, exist_ok=True)
    return home / DB_NAME


def _connect(atlas_home: Optional[Path] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path(atlas_home)), timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=15000")
    _init_db(conn)
    return conn


@contextmanager
def _db(atlas_home: Optional[Path] = None):
    conn = _connect(atlas_home)
    try:
        yield conn
    finally:
        conn.close()


def _init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS memory_entities (
            id TEXT PRIMARY KEY,
            canonical_name TEXT NOT NULL,
            kind TEXT NOT NULL,
            aliases_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'approved',
            confidence REAL NOT NULL DEFAULT 0.8,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_entities_name
            ON memory_entities(canonical_name COLLATE NOCASE);

        CREATE TABLE IF NOT EXISTS memory_claims (
            id TEXT PRIMARY KEY,
            subject_id TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object_text TEXT NOT NULL,
            object_entity_id TEXT,
            text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            stateful INTEGER NOT NULL DEFAULT 0,
            importance REAL NOT NULL,
            confidence REAL NOT NULL,
            valid_from REAL,
            valid_to REAL,
            observed_at REAL NOT NULL,
            superseded_by TEXT,
            source_summary_id TEXT,
            source_session_id TEXT,
            source_message_id TEXT,
            sensitivity TEXT NOT NULL DEFAULT 'normal',
            topics_json TEXT NOT NULL DEFAULT '[]',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_memory_claims_subject
            ON memory_claims(subject_id, predicate, status);
        CREATE INDEX IF NOT EXISTS idx_memory_claims_source
            ON memory_claims(source_summary_id, source_session_id);

        CREATE TABLE IF NOT EXISTS memory_claim_evidence (
            claim_id TEXT NOT NULL,
            summary_id TEXT NOT NULL,
            session_id TEXT,
            message_id TEXT,
            observed_at REAL NOT NULL,
            PRIMARY KEY (claim_id, summary_id)
        );

        CREATE TABLE IF NOT EXISTS memory_dossiers (
            id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'approved',
            confidence REAL NOT NULL DEFAULT 0.8,
            claim_ids_json TEXT NOT NULL DEFAULT '[]',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS memory_processing_jobs (
            id TEXT PRIMARY KEY,
            summary_id TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            run_after REAL NOT NULL DEFAULT 0,
            last_error TEXT,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_memory_jobs_ready
            ON memory_processing_jobs(status, run_after, created_at);

        CREATE TABLE IF NOT EXISTS memory_embeddings (
            item_kind TEXT NOT NULL,
            item_id TEXT NOT NULL,
            model TEXT NOT NULL,
            dimension INTEGER NOT NULL,
            vector_json TEXT NOT NULL,
            updated_at REAL NOT NULL,
            PRIMARY KEY (item_kind, item_id, model)
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS memory_claims_fts
            USING fts5(id UNINDEXED, subject, predicate, object_text, text, topics);
        CREATE VIRTUAL TABLE IF NOT EXISTS memory_entities_fts
            USING fts5(id UNINDEXED, name, kind, aliases);
        CREATE VIRTUAL TABLE IF NOT EXISTS memory_dossiers_fts
            USING fts5(id UNINDEXED, title, text);
        """
    )
    conn.commit()


def _json(value: Any, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _normalise(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:80]


def _stable_id(prefix: str, *parts: str) -> str:
    key = ":".join(_normalise(part).lower() for part in parts)
    return f"{prefix}-{sha1(key.encode('utf-8', errors='ignore')).hexdigest()[:16]}"


def _tokens(text: str) -> List[str]:
    result: List[str] = []
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9_+#.-]{2,}", text or ""):
        token = raw.strip("._-").lower()
        if len(token) >= 3 and token not in _STOPWORDS and not token.isdigit():
            result.append(token)
    return result


def _topics(text: str, limit: int = 8) -> List[str]:
    counts: Dict[str, int] = {}
    for token in _tokens(text):
        counts[token] = counts.get(token, 0) + 1
    return [item[0] for item in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def _response_text(response: Any) -> str:
    try:
        return str(response.choices[0].message.content or "")
    except Exception:
        return ""


def _parse_json_object(text: str) -> Optional[Dict[str, Any]]:
    clean = _normalise(text).strip("` ")
    clean = re.sub(r"^json\s*", "", clean, flags=re.I)
    start = clean.find("{")
    end = clean.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(clean[start : end + 1])
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def extract_episode_knowledge(
    summary_text: str,
    *,
    main_runtime: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """Use the configured Atlas model to derive structured memory."""
    summary = _normalise(summary_text)
    if not summary:
        return {"entities": [], "claims": []}
    try:
        from agent.agent_runtime_helpers import strip_think_blocks
        from agent.auxiliary_client import call_llm

        response = call_llm(
            task="memory_summary",
            messages=[
                {"role": "system", "content": _EXTRACTION_PROMPT},
                {"role": "user", "content": summary[:5000]},
            ],
            temperature=0.1,
            max_tokens=1000,
            timeout=timeout,
            main_runtime=main_runtime,
        )
        payload = _parse_json_object(strip_think_blocks(None, _response_text(response)))
        if payload is None:
            return None
        entities = payload.get("entities") if isinstance(payload.get("entities"), list) else []
        claims = payload.get("claims") if isinstance(payload.get("claims"), list) else []
        return {"entities": entities[:24], "claims": claims[:32]}
    except Exception:
        logger.debug("Living memory extraction failed", exc_info=True)
        return None


def _upsert_entity(conn: sqlite3.Connection, name: str, kind: str, aliases: Iterable[str], confidence: float) -> MemoryEntity:
    canonical = _normalise(name)[:160] or "User"
    entity_id = _stable_id("entity", canonical)
    now = time.time()
    row = conn.execute("SELECT * FROM memory_entities WHERE canonical_name = ? COLLATE NOCASE", (canonical,)).fetchone()
    alias_set = {_normalise(alias)[:160] for alias in aliases if _normalise(alias)}
    alias_set.discard(canonical)
    if row:
        entity_id = str(row["id"])
        alias_set.update(_json(row["aliases_json"], []))
        conn.execute(
            "UPDATE memory_entities SET kind = ?, aliases_json = ?, confidence = MAX(confidence, ?), updated_at = ? WHERE id = ?",
            (kind, json.dumps(sorted(alias_set)), confidence, now, entity_id),
        )
    else:
        conn.execute(
            "INSERT INTO memory_entities(id, canonical_name, kind, aliases_json, status, confidence, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (entity_id, canonical, kind, json.dumps(sorted(alias_set)), APPROVED, confidence, now, now),
        )
    conn.execute("DELETE FROM memory_entities_fts WHERE id = ?", (entity_id,))
    conn.execute(
        "INSERT INTO memory_entities_fts(id, name, kind, aliases) VALUES (?, ?, ?, ?)",
        (entity_id, canonical, kind, " ".join(sorted(alias_set))),
    )
    return MemoryEntity(entity_id, canonical, kind, sorted(alias_set), confidence=confidence, created_at=now, updated_at=now)


def _float(value: Any, default: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _claim_from_row(row: sqlite3.Row) -> MemoryClaim:
    subject = str(row["subject"] if "subject" in row.keys() else "")
    return MemoryClaim(
        id=str(row["id"]), subject_id=str(row["subject_id"]), subject=subject,
        predicate=str(row["predicate"]), object_text=str(row["object_text"]), text=str(row["text"]),
        status=str(row["status"]), stateful=bool(row["stateful"]), importance=float(row["importance"]),
        confidence=float(row["confidence"]), valid_from=row["valid_from"], valid_to=row["valid_to"],
        observed_at=float(row["observed_at"]), superseded_by=str(row["superseded_by"] or ""),
        source_summary_id=str(row["source_summary_id"] or ""), source_session_id=str(row["source_session_id"] or ""),
        source_message_id=str(row["source_message_id"] or ""), sensitivity=str(row["sensitivity"] or "normal"),
        topics=list(_json(row["topics_json"], [])), metadata=dict(_json(row["metadata_json"], {})),
        created_at=float(row["created_at"]), updated_at=float(row["updated_at"]),
    )


def store_episode_knowledge(
    payload: Dict[str, Any],
    *,
    summary_id: str,
    session_id: str = "",
    message_id: str = "",
    observed_at: Optional[float] = None,
    atlas_home: Optional[Path] = None,
) -> Dict[str, Any]:
    """Store extracted claims and version stateful beliefs with history."""
    now = float(observed_at or time.time())
    counts = {"entities": 0, "claims": 0, "approved": 0, "pending": 0, "superseded": 0, "entity_ids": []}
    with _db(atlas_home) as conn:
        entity_by_name: Dict[str, MemoryEntity] = {}
        for raw in payload.get("entities") or []:
            if not isinstance(raw, dict) or not _normalise(raw.get("name")):
                continue
            kind = _slug(str(raw.get("kind") or "other")) or "other"
            if kind not in {"person", "project", "organization", "place", "topic", "other"}:
                kind = "other"
            entity = _upsert_entity(conn, str(raw["name"]), kind, raw.get("aliases") or [], _float(raw.get("confidence"), 0.82))
            entity_by_name[entity.canonical_name.lower()] = entity
            counts["entities"] += 1

        for raw in payload.get("claims") or []:
            if not isinstance(raw, dict):
                continue
            subject_name = _normalise(raw.get("subject"))[:160] or "User"
            predicate = _slug(str(raw.get("predicate") or "related_to")) or "related_to"
            object_text = _normalise(raw.get("object"))[:600]
            if not object_text:
                continue
            entity = entity_by_name.get(subject_name.lower()) or _upsert_entity(conn, subject_name, "person" if subject_name.lower() != "user" else "other", [], 0.8)
            entity_by_name[entity.canonical_name.lower()] = entity
            object_entity_id = ""
            if bool(raw.get("object_is_entity")):
                obj_entity = entity_by_name.get(object_text.lower()) or _upsert_entity(conn, object_text, "other", [], 0.72)
                entity_by_name[obj_entity.canonical_name.lower()] = obj_entity
                object_entity_id = obj_entity.id

            confidence = _float(raw.get("confidence"), 0.7)
            importance = _float(raw.get("importance"), 0.65)
            sensitive = bool(raw.get("sensitive"))
            stateful = bool(raw.get("stateful"))
            change_type = _slug(str(raw.get("change_type") or "new"))
            status = APPROVED if confidence >= 0.76 and importance >= 0.55 and not sensitive else PENDING
            text = f"{entity.canonical_name} {predicate.replace('_', ' ')} {object_text}."
            claim_id = _stable_id("claim", entity.id, predicate, object_text)

            existing = conn.execute("SELECT id, status FROM memory_claims WHERE id = ?", (claim_id,)).fetchone()
            if existing:
                conn.execute(
                    "UPDATE memory_claims SET confidence = MAX(confidence, ?), importance = MAX(importance, ?), updated_at = ? WHERE id = ?",
                    (confidence, importance, now, claim_id),
                )
            else:
                if stateful and status == APPROVED:
                    older = conn.execute(
                        "SELECT id FROM memory_claims WHERE subject_id = ? AND predicate = ? AND status = ? AND valid_to IS NULL AND id != ?",
                        (entity.id, predicate, APPROVED, claim_id),
                    ).fetchall()
                    can_replace = confidence >= 0.82 or change_type in {"update", "correction"}
                    if older and can_replace:
                        for old in older:
                            conn.execute(
                                "UPDATE memory_claims SET status = ?, valid_to = ?, superseded_by = ?, updated_at = ? WHERE id = ?",
                                (STALE, now, claim_id, now, old["id"]),
                            )
                            counts["superseded"] += 1
                    elif older:
                        status = PENDING
                conn.execute(
                    """
                    INSERT INTO memory_claims(
                        id, subject_id, predicate, object_text, object_entity_id, text, status, stateful,
                        importance, confidence, valid_from, valid_to, observed_at, superseded_by,
                        source_summary_id, source_session_id, source_message_id, sensitivity,
                        topics_json, metadata_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, '', ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        claim_id, entity.id, predicate, object_text, object_entity_id, text, status, int(stateful),
                        importance, confidence, now if stateful else None, now, summary_id, session_id, message_id,
                        "sensitive" if sensitive else "normal", json.dumps(_topics(text)),
                        json.dumps({"change_type": change_type, "extractor": "llm-living-memory-v3"}, sort_keys=True), now, now,
                    ),
                )
                counts["claims"] += 1
                counts[status] += 1

            conn.execute(
                "INSERT OR IGNORE INTO memory_claim_evidence(claim_id, summary_id, session_id, message_id, observed_at) VALUES (?, ?, ?, ?, ?)",
                (claim_id, summary_id, session_id, message_id, now),
            )
            conn.execute("DELETE FROM memory_claims_fts WHERE id = ?", (claim_id,))
            conn.execute(
                "INSERT INTO memory_claims_fts(id, subject, predicate, object_text, text, topics) VALUES (?, ?, ?, ?, ?, ?)",
                (claim_id, entity.canonical_name, predicate, object_text, text, " ".join(_topics(text))),
            )
            counts["entity_ids"].append(entity.id)

        conn.commit()
    counts["entity_ids"] = sorted(set(counts["entity_ids"]))
    if counts["claims"] or counts["superseded"]:
        _mark_dirty(atlas_home)
    return counts


def _dossier_text(entity_name: str, claims: Sequence[sqlite3.Row], main_runtime: Optional[Dict[str, Any]]) -> Optional[str]:
    lines = [f"Entity: {entity_name}"]
    for row in claims[:40]:
        lines.append(f"- {row['text']} (confidence {float(row['confidence']):.2f})")
    try:
        from agent.agent_runtime_helpers import strip_think_blocks
        from agent.auxiliary_client import call_llm

        response = call_llm(
            task="memory_summary",
            messages=[
                {"role": "system", "content": _DOSSIER_PROMPT},
                {"role": "user", "content": "\n".join(lines)},
            ],
            temperature=0.1,
            max_tokens=300,
            main_runtime=main_runtime,
        )
        text = _normalise(strip_think_blocks(None, _response_text(response))).strip('"\'')
        words = text.split()
        if len(words) > 180:
            text = " ".join(words[:180]).rstrip(" ,.;") + "..."
        return text if len(text.split()) >= 8 else None
    except Exception:
        logger.debug("Living memory dossier generation failed", exc_info=True)
        return None


def refresh_dossiers(
    entity_ids: Sequence[str],
    *,
    atlas_home: Optional[Path] = None,
    main_runtime: Optional[Dict[str, Any]] = None,
    limit: int = 3,
) -> int:
    updated = 0
    with _db(atlas_home) as conn:
        for entity_id in list(dict.fromkeys(entity_ids))[:limit]:
            entity = conn.execute("SELECT * FROM memory_entities WHERE id = ?", (entity_id,)).fetchone()
            if not entity:
                continue
            claims = conn.execute(
                "SELECT * FROM memory_claims WHERE subject_id = ? AND status = ? AND valid_to IS NULL ORDER BY importance DESC, confidence DESC",
                (entity_id, APPROVED),
            ).fetchall()
            if not claims:
                continue
            text = _dossier_text(str(entity["canonical_name"]), claims, main_runtime)
            if not text:
                continue
            now = time.time()
            dossier_id = _stable_id("dossier", entity_id)
            claim_ids = [str(row["id"]) for row in claims]
            conn.execute(
                """
                INSERT INTO memory_dossiers(id, entity_id, title, text, status, confidence, claim_ids_json, metadata_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET text = excluded.text, confidence = excluded.confidence,
                    claim_ids_json = excluded.claim_ids_json, updated_at = excluded.updated_at
                """,
                (dossier_id, entity_id, f"{entity['canonical_name']} dossier", text, APPROVED, 0.84, json.dumps(claim_ids), json.dumps({"generated_by": "llm", "version": 3}), now, now),
            )
            conn.execute("DELETE FROM memory_dossiers_fts WHERE id = ?", (dossier_id,))
            conn.execute("INSERT INTO memory_dossiers_fts(id, title, text) VALUES (?, ?, ?)", (dossier_id, f"{entity['canonical_name']} dossier", text))
            updated += 1
        conn.commit()
    if updated:
        _mark_dirty(atlas_home)
    return updated


def enqueue_summary(summary_id: str, *, atlas_home: Optional[Path] = None) -> bool:
    if not summary_id:
        return False
    now = time.time()
    job_id = _stable_id("memory-job", summary_id)
    with _db(atlas_home) as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO memory_processing_jobs(id, summary_id, status, attempts, run_after, created_at, updated_at) VALUES (?, ?, 'pending', 0, 0, ?, ?)",
            (job_id, summary_id, now, now),
        )
        conn.commit()
        return bool(cur.rowcount)


def enqueue_unprocessed_summaries(*, atlas_home: Optional[Path] = None, limit: int = 5000) -> int:
    now = time.time()
    queued = 0
    with _db(atlas_home) as conn:
        conn.execute(
            "UPDATE memory_processing_jobs SET status = 'pending', run_after = 0, updated_at = ? WHERE status = 'processing' AND updated_at < ?",
            (now, now - 900.0),
        )
        try:
            rows = conn.execute(
                """
                SELECT s.id FROM memory_summaries s
                LEFT JOIN memory_processing_jobs j ON j.summary_id = s.id
                WHERE s.status = 'approved' AND j.id IS NULL
                ORDER BY s.updated_at ASC LIMIT ?
                """,
                (max(1, min(limit, 5000)),),
            ).fetchall()
        except sqlite3.OperationalError:
            return 0
        for row in rows:
            summary_id = str(row["id"])
            cur = conn.execute(
                "INSERT OR IGNORE INTO memory_processing_jobs(id, summary_id, status, attempts, run_after, created_at, updated_at) VALUES (?, ?, 'pending', 0, 0, ?, ?)",
                (_stable_id("memory-job", summary_id), summary_id, now, now),
            )
            queued += int(bool(cur.rowcount))
        conn.commit()
    return queued


def process_memory_jobs(
    *,
    atlas_home: Optional[Path] = None,
    main_runtime: Optional[Dict[str, Any]] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    result = {"processed": 0, "failed": 0, "claims": 0, "dossiers": 0, "superseded": 0}
    for _ in range(max(1, min(limit, 100))):
        with _db(atlas_home) as conn:
            row = conn.execute(
                "SELECT * FROM memory_processing_jobs WHERE status = 'pending' AND run_after <= ? ORDER BY created_at ASC LIMIT 1",
                (time.time(),),
            ).fetchone()
            if not row:
                break
            job_id = str(row["id"])
            summary_id = str(row["summary_id"])
            attempts = int(row["attempts"] or 0) + 1
            claimed = conn.execute(
                "UPDATE memory_processing_jobs SET status = 'processing', attempts = ?, updated_at = ? WHERE id = ? AND status = 'pending'",
                (attempts, time.time(), job_id),
            )
            conn.commit()
            if not claimed.rowcount:
                continue
            summary = conn.execute("SELECT * FROM memory_summaries WHERE id = ?", (summary_id,)).fetchone()

        try:
            if not summary:
                raise RuntimeError("source summary no longer exists")
            payload = extract_episode_knowledge(str(summary["text"]), main_runtime=main_runtime)
            if payload is None:
                raise RuntimeError("configured model did not return valid structured memory")
            stored = store_episode_knowledge(
                payload,
                summary_id=summary_id,
                session_id=str(summary["source_session_id"] or ""),
                message_id=str(summary["end_message_id"] or ""),
                observed_at=summary["end_timestamp"] or summary["updated_at"],
                atlas_home=atlas_home,
            )
            dossiers = refresh_dossiers(stored["entity_ids"], atlas_home=atlas_home, main_runtime=main_runtime)
            embed_new_memory(atlas_home=atlas_home)
            with _db(atlas_home) as conn:
                conn.execute("UPDATE memory_processing_jobs SET status = 'done', last_error = NULL, updated_at = ? WHERE id = ?", (time.time(), job_id))
                conn.commit()
            result["processed"] += 1
            result["claims"] += int(stored["claims"])
            result["superseded"] += int(stored["superseded"])
            result["dossiers"] += dossiers
        except Exception as exc:
            final = attempts >= 5
            delay = min(3600.0, 30.0 * (2 ** max(0, attempts - 1)))
            with _db(atlas_home) as conn:
                conn.execute(
                    "UPDATE memory_processing_jobs SET status = ?, run_after = ?, last_error = ?, updated_at = ? WHERE id = ?",
                    ("failed" if final else "pending", time.time() + delay, str(exc)[:800], time.time(), job_id),
                )
                conn.commit()
            result["failed"] += 1
            logger.debug("Living memory job failed: %s", exc, exc_info=True)
    return result


def start_memory_worker(*, atlas_home: Optional[Path] = None, main_runtime: Optional[Dict[str, Any]] = None) -> bool:
    global _WORKER
    with _WORKER_LOCK:
        if _WORKER is not None and _WORKER.is_alive():
            return False
        home = atlas_home

        def _run() -> None:
            try:
                process_memory_jobs(atlas_home=home, main_runtime=main_runtime, limit=5)
            except Exception:
                logger.debug("Living memory worker stopped", exc_info=True)

        _WORKER = threading.Thread(target=_run, name="atlas-living-memory", daemon=True)
        _WORKER.start()
        return True


def _load_embedder(*, install: bool = False) -> Any:
    global _EMBEDDER
    if _EMBEDDER is not None:
        return _EMBEDDER
    with _EMBEDDER_LOCK:
        if _EMBEDDER is not None:
            return _EMBEDDER
        if install:
            try:
                from tools.lazy_deps import ensure
                ensure("memory.semantic", prompt=False)
            except Exception:
                logger.info("Local semantic model unavailable; memory will use FTS", exc_info=True)
        try:
            from fastembed import TextEmbedding
            _EMBEDDER = TextEmbedding(
                model_name=EMBEDDING_MODEL,
                local_files_only=not install,
            )
        except Exception:
            return None
        return _EMBEDDER


def _embed_texts(texts: Sequence[str], *, install: bool = False) -> Optional[List[List[float]]]:
    model = _load_embedder(install=install)
    if model is None or not texts:
        return None
    try:
        return [list(map(float, vector.tolist())) for vector in model.embed(list(texts))]
    except Exception:
        logger.debug("Local embedding generation failed", exc_info=True)
        return None


def _memory_documents(conn: sqlite3.Connection) -> List[Tuple[str, str, str]]:
    docs: List[Tuple[str, str, str]] = []
    for table, kind, title_col, text_col in (
        ("memory_facts", "fact", "kind", "text"),
        ("memory_summaries", "summary", "id", "text"),
        ("memory_claims", "claim", "predicate", "text"),
        ("memory_dossiers", "dossier", "title", "text"),
    ):
        try:
            rows = conn.execute(f"SELECT id, {title_col} AS title, {text_col} AS text FROM {table} WHERE status = 'approved'").fetchall()
        except sqlite3.OperationalError:
            continue
        docs.extend((kind, str(row["id"]), f"{row['title']} {row['text']}") for row in rows)
    return docs


def rebuild_living_embeddings(*, atlas_home: Optional[Path] = None, install: bool = True) -> Dict[str, Any]:
    with _db(atlas_home) as conn:
        docs = _memory_documents(conn)
    vectors = _embed_texts([doc[2] for doc in docs], install=install)
    if vectors is None:
        return {"ok": True, "backend": "fts5", "model": None, "embedded": 0, "items": {}}
    counts: Dict[str, int] = {}
    with _db(atlas_home) as conn:
        for (kind, item_id, _text), vector in zip(docs, vectors):
            conn.execute(
                "INSERT OR REPLACE INTO memory_embeddings(item_kind, item_id, model, dimension, vector_json, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (kind, item_id, EMBEDDING_MODEL, len(vector), json.dumps(vector, separators=(",", ":")), time.time()),
            )
            counts[kind] = counts.get(kind, 0) + 1
        conn.commit()
    return {"ok": True, "backend": "fastembed", "model": EMBEDDING_MODEL, "embedded": len(docs), "items": counts}


def embed_new_memory(*, atlas_home: Optional[Path] = None) -> int:
    if _load_embedder(install=False) is None:
        return 0
    return int(rebuild_living_embeddings(atlas_home=atlas_home, install=False).get("embedded") or 0)


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    norm_l = math.sqrt(sum(value * value for value in left))
    norm_r = math.sqrt(sum(value * value for value in right))
    return dot / (norm_l * norm_r) if norm_l and norm_r else 0.0


def _lexical_score(query: str, text: str) -> float:
    query_tokens = set(_tokens(query))
    if not query_tokens:
        return 0.0
    text_tokens = set(_tokens(text))
    overlap = len(query_tokens & text_tokens) / max(1, len(query_tokens))
    exact = 0.5 if _normalise(query).lower() in text.lower() else 0.0
    return overlap + exact


def _query_anchors(query: str) -> set[str]:
    """Return explicit named anchors that semantic similarity must not blur."""
    ignored = {
        "can", "could", "did", "do", "does", "how", "i", "may", "my",
        "please", "should", "tell", "what", "when", "where", "which",
        "who", "why", "will", "would",
    }
    return {
        token.lower()
        for token in re.findall(r"\b[A-Z][A-Za-z0-9_.+-]{1,}\b", query or "")
        if token.lower() not in ignored
    }


def search_living_memory(query: str, *, limit: int = 6, atlas_home: Optional[Path] = None) -> Dict[str, Any]:
    clean = _normalise(query)
    if not clean:
        return {"claims": [], "dossiers": [], "backend": "fts5"}
    query_vectors = _embed_texts([clean], install=False)
    query_vector = query_vectors[0] if query_vectors else None
    with _db(atlas_home) as conn:
        claim_rows = conn.execute(
            """
            SELECT c.*, e.canonical_name AS subject FROM memory_claims c
            JOIN memory_entities e ON e.id = c.subject_id
            WHERE c.status = 'approved' AND c.valid_to IS NULL
            ORDER BY c.importance DESC, c.confidence DESC LIMIT 3000
            """
        ).fetchall()
        dossier_rows = conn.execute("SELECT * FROM memory_dossiers WHERE status = 'approved' ORDER BY updated_at DESC LIMIT 1000").fetchall()
        embedding_rows = conn.execute("SELECT * FROM memory_embeddings WHERE model = ?", (EMBEDDING_MODEL,)).fetchall()
    vectors = {(str(row["item_kind"]), str(row["item_id"])): _json(row["vector_json"], []) for row in embedding_rows}
    anchors = _query_anchors(clean)
    legacy_scores = {
        kind: {
            item_id: round(_cosine(query_vector or [], vector), 4)
            for (item_kind, item_id), vector in vectors.items()
            if item_kind == kind
        }
        for kind in ("fact", "summary")
    }

    scored_claims: List[Tuple[float, Dict[str, Any]]] = []
    for row in claim_rows:
        claim = _claim_from_row(row)
        document = f"{claim.subject} {claim.predicate} {claim.object_text} {claim.text}"
        document_tokens = set(_tokens(document))
        if anchors and not anchors.intersection(document_tokens):
            continue
        lexical = _lexical_score(clean, document)
        semantic = _cosine(query_vector or [], vectors.get(("claim", claim.id), []))
        if lexical <= 0 and semantic < 0.38:
            continue
        score = lexical * 3.2 + semantic * 4.2 + claim.importance * 0.8 + claim.confidence * 0.6
        item = claim.to_dict()
        item.update({"score": round(score, 4), "citation": f"session:{claim.source_session_id}#summary:{claim.source_summary_id}"})
        scored_claims.append((score, item))

    scored_dossiers: List[Tuple[float, Dict[str, Any]]] = []
    for row in dossier_rows:
        text = f"{row['title']} {row['text']}"
        if anchors and not anchors.intersection(_tokens(text)):
            continue
        lexical = _lexical_score(clean, text)
        semantic = _cosine(query_vector or [], vectors.get(("dossier", str(row["id"])), []))
        if lexical <= 0 and semantic < 0.38:
            continue
        score = lexical * 2.8 + semantic * 4.5 + float(row["confidence"] or 0) * 0.7
        scored_dossiers.append((score, {
            "id": str(row["id"]), "entity_id": str(row["entity_id"]), "title": str(row["title"]),
            "text": str(row["text"]), "status": str(row["status"]), "confidence": float(row["confidence"]),
            "claim_ids": list(_json(row["claim_ids_json"], [])), "updated_at": float(row["updated_at"]),
            "score": round(score, 4), "citation": f"dossier:{row['id']}",
        }))
    scored_claims.sort(key=lambda item: item[0], reverse=True)
    scored_dossiers.sort(key=lambda item: item[0], reverse=True)
    safe_limit = max(1, min(int(limit or 6), 20))
    return {
        "claims": [item for _score, item in scored_claims[:safe_limit]],
        "dossiers": [item for _score, item in scored_dossiers[: max(2, safe_limit // 2)]],
        "backend": "fastembed" if query_vector else "fts5",
        "model": EMBEDDING_MODEL if query_vector else None,
        "legacy_scores": legacy_scores,
    }


def living_memory_status(*, atlas_home: Optional[Path] = None) -> Dict[str, Any]:
    with _db(atlas_home) as conn:
        counts = {}
        for key, table in (("entities", "memory_entities"), ("claims", "memory_claims"), ("dossiers", "memory_dossiers")):
            counts[key] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        jobs = {str(row["status"]): int(row["count"]) for row in conn.execute("SELECT status, COUNT(*) AS count FROM memory_processing_jobs GROUP BY status")}
        embedding_count = int(conn.execute("SELECT COUNT(*) FROM memory_embeddings WHERE model = ?", (EMBEDDING_MODEL,)).fetchone()[0])
    return {"ok": True, **counts, "jobs": jobs, "embeddings": embedding_count, "backend": "fastembed" if embedding_count else "fts5", "model": EMBEDDING_MODEL}


def list_claim_history(entity_or_query: str, *, atlas_home: Optional[Path] = None, limit: int = 100) -> Dict[str, Any]:
    clean = _normalise(entity_or_query)
    pattern = f"%{clean}%"
    with _db(atlas_home) as conn:
        rows = conn.execute(
            """
            SELECT c.*, e.canonical_name AS subject FROM memory_claims c
            JOIN memory_entities e ON e.id = c.subject_id
            WHERE e.canonical_name LIKE ? OR c.text LIKE ? OR c.predicate LIKE ?
            ORDER BY c.observed_at DESC LIMIT ?
            """,
            (pattern, pattern, pattern, max(1, min(limit, 500))),
        ).fetchall()
    return {"ok": True, "query": clean, "claims": [_claim_from_row(row).to_dict() for row in rows]}


def living_graph_data(*, atlas_home: Optional[Path] = None) -> Dict[str, Any]:
    with _db(atlas_home) as conn:
        entities = conn.execute("SELECT * FROM memory_entities WHERE status != ?", (REJECTED,)).fetchall()
        claims = conn.execute(
            "SELECT c.*, e.canonical_name AS subject FROM memory_claims c JOIN memory_entities e ON e.id = c.subject_id WHERE c.status != ?",
            (REJECTED,),
        ).fetchall()
        dossiers = conn.execute("SELECT * FROM memory_dossiers WHERE status != ?", (REJECTED,)).fetchall()
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, str]] = []
    for row in entities:
        nodes.append({
            "id": str(row["id"]), "kind": str(row["kind"]), "title": str(row["canonical_name"]),
            "text": f"Known as {', '.join(_json(row['aliases_json'], []))}" if _json(row["aliases_json"], []) else str(row["canonical_name"]),
            "status": str(row["status"]), "confidence": float(row["confidence"]), "timestamp": float(row["updated_at"]),
            "topics": _topics(str(row["canonical_name"])),
        })
    for row in claims:
        claim = _claim_from_row(row)
        nodes.append({
            "id": claim.id, "kind": "claim", "title": f"{claim.subject}: {claim.predicate.replace('_', ' ')}",
            "text": claim.text, "status": claim.status, "confidence": claim.confidence, "importance": claim.importance,
            "timestamp": claim.updated_at, "session_id": claim.source_session_id, "source_message_id": claim.source_message_id,
            "topics": claim.topics,
        })
        edges.append({"source": claim.id, "target": claim.subject_id, "type": "about"})
        if row["object_entity_id"]:
            edges.append({"source": claim.id, "target": str(row["object_entity_id"]), "type": claim.predicate})
        if claim.source_summary_id:
            edges.append({"source": claim.id, "target": claim.source_summary_id, "type": "supported_by"})
        if claim.superseded_by:
            edges.append({"source": claim.id, "target": claim.superseded_by, "type": "superseded_by"})
    for row in dossiers:
        dossier_id = str(row["id"])
        nodes.append({
            "id": dossier_id, "kind": "dossier", "title": str(row["title"]), "text": str(row["text"]),
            "status": str(row["status"]), "confidence": float(row["confidence"]), "timestamp": float(row["updated_at"]),
            "topics": _topics(str(row["text"])),
        })
        edges.append({"source": dossier_id, "target": str(row["entity_id"]), "type": "synthesizes"})
        for claim_id in _json(row["claim_ids_json"], [])[:30]:
            edges.append({"source": dossier_id, "target": str(claim_id), "type": "includes"})
    return {"nodes": nodes, "edges": edges}


def _mark_dirty(atlas_home: Optional[Path]) -> None:
    try:
        from agent.memory_vault import mark_memory_vault_dirty
        mark_memory_vault_dirty(atlas_home=atlas_home)
    except Exception:
        logger.debug("Could not mark living memory graph dirty", exc_info=True)
