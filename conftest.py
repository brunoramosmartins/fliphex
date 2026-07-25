"""Pytest path setup.

Puts the repo root (so ``import fliphex`` works without an editable install)
and ``scripts/`` (so tests can import the Phase 0 doc generators to cross-check
the engine against the canonical tables) on ``sys.path``.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).parent
for _p in (_ROOT, _ROOT / "scripts"):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)
