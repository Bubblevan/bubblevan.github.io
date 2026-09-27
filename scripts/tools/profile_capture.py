"""Compatibility entry point for the existing-Chrome Xiaohongshu profile reader.

The former implementation used Playwright, a persistent profile, login prompts,
and intercepted XHS endpoints. The current implementation delegates to
``xhs_profile_reader.py --url ...``, which uses chrome-use to read the user's
already-running Chrome profile without exporting credentials.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.tools.xhs_profile_reader import main


if __name__ == "__main__":
    raise SystemExit(main())
