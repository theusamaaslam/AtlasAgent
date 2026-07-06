"""Resolve ATLAS_HOME for standalone skill scripts.

Skill scripts may run outside the Atlas process (e.g. system Python,
nix env, CI) where ``atlas_constants`` is not importable.  This module
provides the same ``get_atlas_home()`` and ``display_atlas_home()``
contracts as ``atlas_constants`` without requiring it on ``sys.path``.

When ``atlas_constants`` IS available it is used directly so that any
future enhancements (profile resolution, Docker detection, etc.) are
picked up automatically.  The fallback path replicates the core logic
from ``atlas_constants.py`` using only the stdlib.

All scripts under ``google-workspace/scripts/`` should import from here
instead of duplicating the ``ATLAS_HOME = Path(os.getenv(...))`` pattern.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from atlas_constants import display_atlas_home as display_atlas_home
    from atlas_constants import get_atlas_home as get_atlas_home
except (ModuleNotFoundError, ImportError):

    def get_atlas_home() -> Path:
        """Return the Atlas home directory (default: ~/.atlas).

        Mirrors ``atlas_constants.get_atlas_home()``."""
        val = os.environ.get("ATLAS_HOME", "").strip()
        return Path(val) if val else Path.home() / ".atlas"

    def display_atlas_home() -> str:
        """Return a user-friendly ``~/``-shortened display string.

        Mirrors ``atlas_constants.display_atlas_home()``."""
        home = get_atlas_home()
        try:
            return "~/" + str(home.relative_to(Path.home()))
        except ValueError:
            return str(home)
