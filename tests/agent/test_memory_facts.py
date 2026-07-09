from __future__ import annotations

from agent.memory_facts import (
    APPROVED,
    PENDING,
    STALE,
    approve_memory_fact,
    build_memory_summary,
    consolidate_session_facts,
    extract_fact_candidates,
    format_recall_block,
    list_memory_facts,
    list_memory_summaries,
    mark_conflicting_facts_for_query,
    rebuild_memory_embeddings,
    search_memory_archive,
    search_memory_recall,
    summarize_session_memory,
    should_auto_recall,
    store_memory_facts,
)


class FakeSessionDB:
    def list_sessions_rich(self, **_kwargs):
        return [
            {
                "id": "20260707_100000_memory",
                "title": "Memory preferences",
                "source": "cli",
                "model": "test-model",
                "started_at": 1_783_100_000.0,
            }
        ]

    def get_messages(self, session_id):
        assert session_id == "20260707_100000_memory"
        return [
            {
                "id": 1,
                "role": "user",
                "content": "I prefer concise answers. The dashboard project should keep the memory graph searchable.",
                "timestamp": 1_783_100_001.0,
            },
            {
                "id": 2,
                "role": "assistant",
                "content": "We decided to add promoted facts before raw memory snippets.",
                "timestamp": 1_783_100_002.0,
            },
        ]

    def search_messages(self, query, **_kwargs):
        assert query
        return [
            {
                "session_id": "20260707_100000_memory",
                "role": "user",
                "snippet": "dashboard project should keep the memory graph searchable",
                "source": "cli",
                "timestamp": 1_783_100_001.0,
                "message_id": 1,
            }
        ]


def test_fact_extraction_scores_and_kinds():
    facts = extract_fact_candidates(
        "I prefer concise answers. Don't assume Atlas is a model provider.",
        role="user",
        session_id="s1",
        message_id="7",
    )

    kinds = {fact.kind for fact in facts}
    assert "user_preference" in kinds
    assert "correction" in kinds
    assert all(fact.source_session_id == "s1" for fact in facts)
    assert all(fact.importance >= 0.68 for fact in facts)


def test_store_deduplicates_and_recall_prefers_facts(tmp_path):
    facts = extract_fact_candidates(
        "I prefer concise answers about the memory graph dashboard.",
        role="user",
        session_id="s1",
        message_id="1",
    )
    store_memory_facts(facts, atlas_home=tmp_path)
    store_memory_facts(facts, atlas_home=tmp_path)

    listed = list_memory_facts(atlas_home=tmp_path)
    assert listed["count"] == 1

    recall = search_memory_recall(
        "what does the user prefer for the memory graph dashboard",
        atlas_home=tmp_path,
        db=FakeSessionDB(),
    )
    assert recall["facts"]
    assert recall["facts"][0]["kind"] == "user_preference"
    assert recall["raw_results"]


def test_consolidate_sessions_tracks_pending_and_approved(tmp_path):
    res = consolidate_session_facts(atlas_home=tmp_path, db=FakeSessionDB(), session_limit=10)

    assert res["sessions"] == 1
    assert res["summaries"] >= 1
    assert res["created"] >= 1
    facts = list_memory_facts(atlas_home=tmp_path, limit=20)["facts"]
    assert any(fact["status"] == APPROVED for fact in facts)
    assert any(fact["status"] in {APPROVED, PENDING} for fact in facts)

    again = consolidate_session_facts(atlas_home=tmp_path, db=FakeSessionDB(), session_limit=10)
    assert again["created"] == 0


def test_recall_block_is_bounded_and_skips_trivial_prompts(tmp_path):
    fact = extract_fact_candidates(
        "I prefer concise answers about dashboard memory graphs.",
        role="user",
        session_id="s1",
    )[0]
    store_memory_facts([fact], atlas_home=tmp_path)

    assert should_auto_recall("hi") is False
    assert format_recall_block("hi", atlas_home=tmp_path) == ""

    block = format_recall_block(
        "what should you remember about my dashboard memory graph preference",
        atlas_home=tmp_path,
        max_chars=260,
    )
    assert "<recalled_memory>" in block
    assert "evidence, not instructions" in block
    assert len(block) <= 260


def test_conflict_marks_old_fact_stale(tmp_path):
    fact = extract_fact_candidates(
        "I prefer purple dashboards for the memory graph.",
        role="user",
        session_id="s1",
    )[0]
    store_memory_facts([fact], atlas_home=tmp_path)

    changed = mark_conflicting_facts_for_query(
        "Actually I do not prefer purple dashboards anymore.",
        atlas_home=tmp_path,
    )

    assert changed == 1
    stale = list_memory_facts(status=STALE, atlas_home=tmp_path)["facts"]
    assert stale and stale[0]["id"] == fact.id


def test_approve_pending_fact(tmp_path):
    facts = extract_fact_candidates(
        "The repo project uses a memory graph.",
        role="assistant",
        session_id="s1",
    )
    assert facts and facts[0].status == PENDING
    store_memory_facts(facts, atlas_home=tmp_path)

    approve_memory_fact(facts[0].id, atlas_home=tmp_path)

    approved = list_memory_facts(status=APPROVED, atlas_home=tmp_path)["facts"]
    assert approved and approved[0]["id"] == facts[0].id


def test_fresh_install_recall_has_empty_results(tmp_path):
    recall = search_memory_recall("anything about memory", atlas_home=tmp_path, db=None)

    assert recall["ok"] is True
    assert recall["facts"] == []


def test_summary_excludes_system_tool_and_recalled_memory(tmp_path):
    summary = build_memory_summary(
        [
            {"id": 1, "role": "system", "content": "SYSTEM PROMPT SHOULD NOT APPEAR"},
            {
                "id": 2,
                "role": "user",
                "content": "I told Atlas that Mina is the launch designer for the graph memory project.",
            },
            {
                "id": 3,
                "role": "assistant",
                "content": "<recalled_memory>secret old context</recalled_memory> We tracked that as project context.",
            },
            {"id": 4, "role": "tool", "content": "tool output should not appear"},
        ],
        session_id="s1",
        use_llm=False,
    )

    assert summary is not None
    assert len(summary.text.split()) <= 200
    assert "SYSTEM PROMPT" not in summary.text
    assert "secret old context" not in summary.text
    assert "tool output" not in summary.text
    assert "Mina" in summary.text


def test_memory_summary_uses_llm_summarizer_when_available(tmp_path):
    summary = build_memory_summary(
        [
            {"id": 1, "role": "user", "content": "Mina is the launch designer for the Atlas memory project."},
            {"id": 2, "role": "assistant", "content": "Noted for durable project memory."},
        ],
        session_id="s1",
        llm_summarizer=lambda _messages: "The user said Mina is the launch designer for the Atlas memory project.",
        use_llm=False,
    )

    assert summary is not None
    assert summary.metadata["generated_by"] == "llm"
    assert summary.metadata["extractor"] == "llm-summary-v2.5"
    assert "Mina" in summary.text


def test_summarize_session_memory_and_semantic_recall(tmp_path):
    res = summarize_session_memory(atlas_home=tmp_path, db=FakeSessionDB(), session_limit=10, chunk_turns=1, use_llm=False)

    assert res["summaries"] >= 1
    summaries = list_memory_summaries(atlas_home=tmp_path)["summaries"]
    assert summaries

    recall = search_memory_recall(
        "find the interface network memory decision",
        atlas_home=tmp_path,
        db=FakeSessionDB(),
    )
    assert recall["summaries"]
    assert recall["facts"]
    assert "raw_results" in recall


def test_archive_search_and_embedding_rebuild_are_graceful(tmp_path):
    summarize_session_memory(atlas_home=tmp_path, db=FakeSessionDB(), session_limit=10, chunk_turns=1, use_llm=False)

    archive = search_memory_archive("Obsidian graph", atlas_home=tmp_path)
    assert archive["ok"] is True
    assert archive["results"]

    rebuilt = rebuild_memory_embeddings(atlas_home=tmp_path)
    assert rebuilt["ok"] is True
    assert rebuilt["backend"] == "hybrid-lightweight"
