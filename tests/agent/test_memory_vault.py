from __future__ import annotations

import json

from agent.memory_vault import (
    GRAPH_JSON,
    mark_memory_vault_dirty,
    memory_vault_graph,
    memory_vault_status,
    search_memory_vault,
    sync_memory_vault,
)
from agent.prompt_builder import load_creator_profile_prompt


class FakeSessionDB:
    def list_sessions_rich(self, **_kwargs):
        return [
            {
                "id": "20260706_123456_demo",
                "title": "Customer asks about memory graph",
                "source": "cli",
                "model": "test-model",
                "started_at": 1_783_000_000.0,
            }
        ]

    def get_messages(self, session_id):
        assert session_id == "20260706_123456_demo"
        return [
            {
                "id": 1,
                "role": "user",
                "content": "Can Atlas remember customer interactions in an Obsidian graph?",
                "timestamp": 1_783_000_001.0,
            },
            {
                "id": 2,
                "role": "assistant",
                "content": "Yes. The memory vault links sessions, topics, and interactions.",
                "timestamp": 1_783_000_002.0,
            },
            {
                "id": 3,
                "role": "tool",
                "content": "ignored",
                "timestamp": 1_783_000_003.0,
            },
        ]

    def search_messages(self, query, **_kwargs):
        assert "graph" in query.lower()
        return [
            {
                "session_id": "20260706_123456_demo",
                "role": "user",
                "snippet": "Obsidian graph",
                "source": "cli",
                "timestamp": 1_783_000_001.0,
            }
        ]


def test_memory_vault_sync_includes_creator_memory_and_sessions(tmp_path):
    mem_dir = tmp_path / "memories"
    mem_dir.mkdir()
    (mem_dir / "MEMORY.md").write_text("- The user wants graph memory.\n", encoding="utf-8")
    (mem_dir / "USER.md").write_text("- The user's name is Usama.\n", encoding="utf-8")

    payload = sync_memory_vault(atlas_home=tmp_path, db=FakeSessionDB())

    assert payload["ok"] is True
    assert payload["stats"]["creators"] == 1
    assert payload["stats"]["sessions"] == 1
    assert payload["stats"]["interactions"] == 2
    assert (tmp_path / "memory-vault" / "Creator" / "Usama Aslam.md").exists()

    graph_path = tmp_path / "memory-vault" / GRAPH_JSON
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    titles = {node["title"] for node in graph["nodes"]}
    assert "Usama Aslam" in titles
    assert any(title.startswith("User 20260706") for title in titles)
    assert graph["edges"]


def test_memory_vault_search_and_dirty_status(tmp_path):
    mark_memory_vault_dirty(atlas_home=tmp_path)
    assert memory_vault_status(atlas_home=tmp_path)["dirty"] is True

    res = search_memory_vault(
        "graph",
        atlas_home=tmp_path,
        db=FakeSessionDB(),
        limit=10,
    )

    assert res["ok"] is True
    assert any("graph" in item["snippet"].lower() for item in res["results"])


def test_memory_vault_graph_autosyncs_without_existing_session_db(tmp_path):
    (tmp_path / "memories").mkdir()
    mark_memory_vault_dirty(atlas_home=tmp_path)

    graph = memory_vault_graph(atlas_home=tmp_path)

    assert graph["ok"] is True
    assert graph["dirty"] is False
    assert any(node["title"] == "Usama Aslam" for node in graph["nodes"])


def test_creator_profile_prompt_is_available():
    prompt = load_creator_profile_prompt()

    assert "Usama Aslam" in prompt
    assert "creator of Atlas Agent" in prompt
