"""Pytest path setup, and the optional-torch collection guard.

Puts the repo root (so ``import fliphex`` works without an editable install)
and ``scripts/`` (so tests can import the Phase 0 doc generators to cross-check
the engine against the canonical tables) on ``sys.path``.

**torch is an optional dependency and that is load-bearing, not incidental.**
`pyproject.toml` puts it in the ``az`` extra, `agents/__init__.py` deliberately
does not export ``AZAgent`` so that importing any other agent never pulls torch
in, and `tests/test_agents.py` asserts that in a subprocess. Axis 1's exact
solver runs under an interpreter with no torch build at all.

So a torch-free environment is a **supported configuration** and must collect
cleanly. The modules below import torch at module scope — directly, or through
``az.*``, or through a ``scripts/`` instrument that does — and are skipped
whole when it is absent.

**They are not skipped quietly.** A torch-free run that silently collected eight
fewer modules looks exactly like a full one in the summary line, and this project
already has one instance of a test suite that was green for the wrong reason.
The report header says which configuration ran, and because ``addopts`` carries
``-q`` — which suppresses that header — a warning is raised as well, since the
warnings summary survives quiet mode.

This guard is not a licence to leave the ``az`` package untested. CI runs two
jobs, and the second installs the ``az`` extra precisely so these modules run.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).parent
for _p in (_ROOT, _ROOT / "scripts"):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

#: Test modules that cannot be imported without torch. Listed explicitly rather
#: than matched by a wildcard so that adding a torch-free test to ``az`` does
#: not silently stop it running everywhere.
TORCH_ONLY = (
    "tests/test_az_agent.py",
    "tests/test_az_checkpoint.py",
    "tests/test_az_gate.py",
    "tests/test_az_loop.py",
    "tests/test_az_network.py",
    "tests/test_az_selfplay.py",
    "tests/test_az_train.py",
    "tests/test_exp006_agreement.py",
)


def _torch_importable() -> bool:
    """Whether torch can actually be imported, not merely located.

    ``importlib.util.find_spec`` answers a different question: it finds a module
    whose import would still raise, which is exactly the case on a broken or
    partial install. The guard has to survive that, so it imports.
    """
    try:
        import torch  # noqa: F401
    except ImportError:
        return False
    return True


_HAS_TORCH = _torch_importable()

#: Absolute, because ``collect_ignore`` entries are matched against the paths
#: pytest has already resolved — a repo-relative string silently matches
#: nothing and the guard then does exactly what it looks like it is doing.
collect_ignore = [] if _HAS_TORCH else [str(_ROOT / p) for p in TORCH_ONLY]


_ABSENT = (
    f"torch is not installed, so {len(TORCH_ONLY)} az test modules were not "
    "collected. This is a supported configuration and the run can be green; it "
    "is not a full run. The CI 'az' job installs the extra and runs them."
)


def pytest_report_header(config) -> str:
    """Say which configuration is running, so a green run is not ambiguous."""
    if _HAS_TORCH:
        return "torch: present — the az test modules are collected"
    return f"torch: ABSENT — {_ABSENT}"


def pytest_configure(config) -> None:
    """Warn as well as report, because ``-q`` hides the header."""
    if not _HAS_TORCH:
        config.issue_config_time_warning(UserWarning(_ABSENT), stacklevel=2)
