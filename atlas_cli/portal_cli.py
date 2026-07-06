"""Removed hosted-gateway command.

This white-labeled build does not expose the former hosted gateway or its
provider login flow.
"""
from __future__ import annotations

import sys
from atlas_cli.colors import Colors, color


def _removed_message() -> int:
    print()
    print(color("  Hosted gateway login has been removed from this Atlas build.", Colors.YELLOW))
    print("  Configure a direct provider or custom endpoint with `atlas model` instead.")
    return 1


def portal_command(args) -> int:
    """Top-level dispatch for `atlas portal <subcommand>`."""
    return _removed_message()


def add_parser(subparsers) -> None:
    """Register `atlas portal` on the given argparse subparsers object."""
    portal_parser = subparsers.add_parser(
        "portal",
        help="Removed hosted-gateway login command",
        description="Hosted gateway login is removed in this white-labeled Atlas build.",
    )
    portal_sub = portal_parser.add_subparsers(dest="portal_command")
    for name in ("login", "info", "status", "open", "tools"):
        portal_sub.add_parser(name, help="removed")

    portal_parser.set_defaults(func=portal_command)
