"""``atlas memory`` subcommand parser.

Extracted from ``atlas_cli/main.py:main()`` (god-file Phase 2 follow-up).
Handler injected to avoid importing ``main``.
"""

from __future__ import annotations

from typing import Callable


def build_memory_parser(subparsers, *, cmd_memory: Callable) -> None:
    """Attach the ``memory`` subcommand to ``subparsers``."""
    memory_parser = subparsers.add_parser(
        "memory",
        help="Configure external memory provider",
        description=(
            "Set up and manage external memory provider plugins.\n\n"
            "Available providers: honcho, openviking, mem0, hindsight,\n"
            "holographic, retaindb, byterover.\n\n"
            "Only one external provider can be active at a time.\n"
            "Built-in memory (MEMORY.md/USER.md) is always active."
        ),
    )
    memory_sub = memory_parser.add_subparsers(dest="memory_command")
    _setup_parser = memory_sub.add_parser(
        "setup", help="Interactive provider selection and configuration"
    )
    _setup_parser.add_argument(
        "provider",
        nargs="?",
        default=None,
        help="Provider to configure directly (e.g. honcho), skipping the picker",
    )
    memory_sub.add_parser("status", help="Show current memory provider config")
    memory_sub.add_parser("living-status", help="Show the evolving built-in memory index and worker status")
    catch_up_parser = memory_sub.add_parser(
        "catch-up",
        help="Process queued summaries into entities, claims, and dossiers",
    )
    catch_up_parser.add_argument("--limit", type=int, default=50, help="Maximum queued summaries to process")
    history_parser = memory_sub.add_parser(
        "history",
        help="Show current and superseded claims for an entity or topic",
    )
    history_parser.add_argument("query", nargs="+", help="Entity, predicate, or text to inspect")
    history_parser.add_argument("--limit", type=int, default=100, help="Maximum claims to print")
    memory_sub.add_parser("off", help="Disable external provider (built-in only)")
    _reset_parser = memory_sub.add_parser(
        "reset",
        help="Erase all built-in memory (MEMORY.md and USER.md)",
    )
    _reset_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )
    _reset_parser.add_argument(
        "--target",
        choices=["all", "memory", "user"],
        default="all",
        help="Which store to reset: 'all' (default), 'memory', or 'user'",
    )
    recall_parser = memory_sub.add_parser(
        "recall",
        help="Rank promoted facts and raw interactions for an agent prompt",
    )
    recall_parser.add_argument("query", nargs="+", help="Recall query")
    recall_parser.add_argument(
        "--limit",
        type=int,
        default=6,
        help="Maximum number of facts/snippets to print",
    )
    consolidate_parser = memory_sub.add_parser(
        "consolidate",
        help="Extract promoted memory facts from recent sessions",
    )
    consolidate_parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Maximum number of sessions to process",
    )
    summarize_parser = memory_sub.add_parser(
        "summarize",
        help="Create compact semantic memory summaries from sessions",
    )
    summarize_parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Maximum number of sessions to process",
    )
    archive_parser = memory_sub.add_parser(
        "archive",
        help="Search the raw full-memory archive fallback",
    )
    archive_sub = archive_parser.add_subparsers(dest="memory_archive_command")
    archive_search = archive_sub.add_parser("search", help="Search raw archived session memory")
    archive_search.add_argument("query", nargs="+", help="Archive search query")
    archive_search.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of raw results to print",
    )
    embeddings_parser = memory_sub.add_parser(
        "embeddings",
        help="Manage local semantic memory embeddings",
    )
    embeddings_sub = embeddings_parser.add_subparsers(dest="memory_embeddings_command")
    embeddings_sub.add_parser("rebuild", help="Build local embeddings for facts, summaries, claims, and dossiers")
    vault_parser = memory_sub.add_parser(
        "vault",
        help="Manage the generated Obsidian memory vault",
        description=(
            "Generate and inspect the Obsidian-compatible memory vault built "
            "from Atlas memory files and saved sessions."
        ),
    )
    vault_sub = vault_parser.add_subparsers(dest="memory_vault_command")
    vault_sub.add_parser("sync", help="Regenerate the memory vault")
    vault_sub.add_parser("path", help="Print the memory vault path")
    vault_sub.add_parser("open", help="Open the memory vault folder")
    vault_search = vault_sub.add_parser("search", help="Search memory vault sources")
    vault_search.add_argument("query", nargs="+", help="Search query")
    vault_search.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results to print",
    )
    memory_parser.set_defaults(func=cmd_memory)
