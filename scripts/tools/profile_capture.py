"""Compatibility entry point for the anonymous Xiaohongshu profile reader.

The former implementation used Playwright, a persistent profile, login prompts,
and intercepted XHS endpoints. Those behaviors have been removed. Use
``xhs_profile_reader.py --url ...`` for the current public-page-only workflow.
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
