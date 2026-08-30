"""Axis 1 — exact analysis.

Alpha-beta with a transposition table, exhaustive solves of reduced variants
(`adr-011 <../docs/adr/adr-011-reduced-variant-parity.md>`_), and — if the
crossover measurement says they are worth building — retrograde endgame
databases (`adr-012 <../docs/adr/adr-012-endgame-database-storage.md>`_).

This package imports ``fliphex`` and nothing else from the project. It must
never import ``az`` and ``az`` must never import it: that separation is what
makes the Phase 5 cross-axis comparison mean anything
(`adr-004 <../docs/adr/adr-004-solver-approach.md>`_ R1–R3).
"""

from solver.minimax import (
    LOSS,
    WIN,
    BudgetExceededError,
    SearchResult,
    SearchStats,
    Solver,
    solve,
)
from solver.retrograde import (
    SLOT_LOSS,
    SLOT_UNSET,
    SLOT_WIN,
    LayerIndex,
    RetrogradeResult,
    SweepStats,
)
from solver.retrograde import solve as retrograde_solve
from solver.transposition import Flag, NullTable, TranspositionTable

__all__ = [
    # search
    "LOSS",
    "WIN",
    "BudgetExceededError",
    "SearchResult",
    "SearchStats",
    "Solver",
    "solve",
    # retrograde. Note `retrograde_solve` rather than `solve`: the two solvers
    # answer the same question by different means (adr-010 V3) and must never be
    # reachable under one name.
    "LayerIndex",
    "RetrogradeResult",
    "SweepStats",
    "retrograde_solve",
    "SLOT_LOSS",
    "SLOT_UNSET",
    "SLOT_WIN",
    # transposition
    "Flag",
    "NullTable",
    "TranspositionTable",
]
