from __future__ import annotations

from agent.living_memory import (
    enqueue_summary,
    list_claim_history,
    living_graph_data,
    living_memory_status,
    process_memory_jobs,
    search_living_memory,
    store_episode_knowledge,
)
from agent.memory_facts import MemorySummary, format_recall_block, store_memory_summaries


def _payload(value: str, change_type: str = "new"):
    return {
        "entities": [
            {"name": "Atlas rollout", "kind": "project", "aliases": ["rollout"]},
        ],
        "claims": [
            {
                "subject": "Atlas rollout",
                "predicate": "deployment_state",
                "object": value,
                "object_is_entity": False,
                "stateful": True,
                "change_type": change_type,
                "confidence": 0.94,
                "importance": 0.88,
                "sensitive": False,
            }
        ],
    }


def test_state_changes_keep_history_and_activate_new_claim(tmp_path):
    first = store_episode_knowledge(
        _payload("testing"),
        summary_id="summary-1",
        session_id="session-1",
        message_id="4",
        observed_at=100.0,
        atlas_home=tmp_path,
    )
    second = store_episode_knowledge(
        _payload("production", "update"),
        summary_id="summary-2",
        session_id="session-2",
        message_id="8",
        observed_at=200.0,
        atlas_home=tmp_path,
    )

    assert first["claims"] == 1
    assert second["claims"] == 1
    assert second["superseded"] == 1

    history = list_claim_history("Atlas rollout", atlas_home=tmp_path)["claims"]
    active = next(item for item in history if item["status"] == "approved")
    old = next(item for item in history if item["status"] == "stale")
    assert "production" in active["text"]
    assert old["valid_to"] == 200.0
    assert old["superseded_by"] == active["id"]


def test_living_recall_and_graph_work_without_embedding_backend(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.living_memory._embed_texts", lambda *_args, **_kwargs: None)
    store_episode_knowledge(
        {
            "entities": [{"name": "Mina", "kind": "person", "aliases": []}],
            "claims": [{
                "subject": "Mina",
                "predicate": "role",
                "object": "launch designer for Atlas",
                "stateful": True,
                "change_type": "new",
                "confidence": 0.93,
                "importance": 0.9,
                "sensitive": False,
            }],
        },
        summary_id="summary-mina",
        session_id="session-mina",
        message_id="12",
        atlas_home=tmp_path,
    )

    recall = search_living_memory("Who is the launch designer?", atlas_home=tmp_path)
    assert recall["backend"] == "fts5"
    assert recall["claims"]
    assert "Mina" in recall["claims"][0]["text"]

    block = format_recall_block("Mina?", atlas_home=tmp_path)
    assert "current claim" in block
    assert "launch designer" in block

    graph = living_graph_data(atlas_home=tmp_path)
    kinds = {node["kind"] for node in graph["nodes"]}
    assert {"person", "claim"}.issubset(kinds)
    assert any(edge["type"] == "about" for edge in graph["edges"])


def test_living_recall_respects_named_entity_anchors(tmp_path):
    for name, role in (("Usama", "Atlas creator"), ("Laiba", "AI student")):
        store_episode_knowledge(
            {
                "entities": [{"name": name, "kind": "person", "aliases": []}],
                "claims": [{
                    "subject": name,
                    "predicate": "role",
                    "object": role,
                    "stateful": True,
                    "change_type": "new",
                    "confidence": 0.95,
                    "importance": 0.9,
                    "sensitive": False,
                }],
            },
            summary_id=f"summary-{name.lower()}",
            session_id="session-people",
            message_id=name,
            atlas_home=tmp_path,
        )

    recall = search_living_memory("What does Usama work on?", atlas_home=tmp_path)

    assert recall["claims"]
    assert all("Usama" in item["text"] for item in recall["claims"])


def test_durable_job_queue_processes_summary_idempotently(tmp_path, monkeypatch):
    summary = MemorySummary(
        id="summary-job",
        text="The user said Mina is the launch designer for Atlas.",
        source_session_id="session-job",
        end_message_id="4",
        end_timestamp=123.0,
    )
    store_memory_summaries([summary], atlas_home=tmp_path)
    assert enqueue_summary(summary.id, atlas_home=tmp_path) is True
    assert enqueue_summary(summary.id, atlas_home=tmp_path) is False

    monkeypatch.setattr(
        "agent.living_memory.extract_episode_knowledge",
        lambda *_args, **_kwargs: {
            "entities": [{"name": "Mina", "kind": "person", "aliases": []}],
            "claims": [{
                "subject": "Mina", "predicate": "role", "object": "launch designer",
                "stateful": True, "change_type": "new", "confidence": 0.9,
                "importance": 0.85, "sensitive": False,
            }],
        },
    )
    monkeypatch.setattr("agent.living_memory.refresh_dossiers", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr("agent.living_memory.embed_new_memory", lambda **_kwargs: 0)

    result = process_memory_jobs(atlas_home=tmp_path, limit=5)
    assert result["processed"] == 1
    assert result["claims"] == 1
    assert living_memory_status(atlas_home=tmp_path)["jobs"] == {"done": 1}
