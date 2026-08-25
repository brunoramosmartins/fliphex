"""Tests for solver.minimax.

The load-bearing test is :func:`test_alpha_beta_agrees_with_plain_minimax`: a
pruning search is only correct if it returns what the unpruned search would, and
every other property here is downstream of that.

Boards are kept tiny on purpose. ``Variant(5, 1)`` is the smallest legal variant
— 5 cells, hands 3 + 2 — with about a thousand configurations, so a full solve
is instant. The 3×3 solve is ``EXP-001``'s job, not the test suite's.
"""

import pytest

from fliphex.moves import apply_move, legal_moves
from fliphex.rules import winner
from fliphex.variant import Arm, Variant
from solver.minimax import (
    LOSS,
    WIN,
    BudgetExceededError,
    Solver,
    solve,
)
from solver.transposition import Flag, TranspositionTable

TINY = Variant(5, 1)


@pytest.fixture
def tiny():
    return TINY.board(), TINY.initial_state()


def naive_minimax(board, state):
    """Unpruned negamax with no table. The reference the solver must match."""
    if state.is_terminal():
        return WIN if winner(state) == state.to_move else LOSS
    return max(
        -naive_minimax(board, apply_move(board, state, m))
        for m in legal_moves(board, state)
    )


def walk(board, state, plies):
    """Advance ``plies`` moves down the first legal line."""
    for _ in range(plies):
        state = apply_move(board, state, legal_moves(board, state)[0])
    return state


# -- the property everything else rests on ------------------------------------


@pytest.mark.parametrize("plies", [1, 2, 3])
def test_alpha_beta_agrees_with_plain_minimax(tiny, plies):
    """Pruning must not change the root value (exercises/ex03 Q1).

    Compared from ply 1 rather than ply 0: the unpruned tree at the root is
    ~1.7e6 leaves, which is a fine thing for a solver to chew through and a bad
    thing to put in a test suite. Alpha-beta's own root value is covered by
    ``test_the_table_does_not_change_the_value``, which needs no reference tree
    because it compares two independent search paths against each other.
    """
    board, root = tiny
    position = walk(board, root, plies)
    assert solve(board, position).value == naive_minimax(board, position)


def test_the_table_does_not_change_the_value(tiny):
    """Cold table, warm table, and no table must all agree at the root."""
    board, root = tiny
    shared = TranspositionTable(1 << 12)
    cold = Solver(board, tt=shared).solve(root).value
    warm = Solver(board, tt=shared).solve(root).value
    fresh = Solver(board, tt=TranspositionTable(1 << 12)).solve(root).value
    assert cold == warm == fresh


def test_move_ordering_does_not_change_the_value(tiny):
    """Ordering is a speed decision, never a correctness one."""
    board, root = tiny

    def reversed_order(_board, _state, moves, _tt_move):
        return list(reversed(moves))

    baseline = solve(board, root).value
    assert Solver(board, order=reversed_order).solve(root).value == baseline


# -- values -------------------------------------------------------------------


def test_value_is_never_zero(tiny):
    """Draws are impossible on an odd board (adr-011, adr-010 V2)."""
    board, root = tiny
    for plies in range(0, root.n_cells):
        assert solve(board, walk(board, root, plies)).value in (WIN, LOSS)


def test_terminal_position_is_decided_by_counting_cells(tiny):
    board, root = tiny
    terminal = walk(board, root, root.n_cells)
    assert terminal.is_terminal()
    expected = WIN if winner(terminal) == terminal.to_move else LOSS
    assert solve(board, terminal).value == expected


def test_the_two_arms_are_both_solvable(tiny):
    """Both H1 and H2 hands produce a well-formed game (adr-011)."""
    for arm in (Arm.H1, Arm.H2):
        v = Variant(5, 1, arm)
        assert solve(v.board(), v.initial_state()).value in (WIN, LOSS)


# -- the result carries its own provenance ------------------------------------


def test_a_completed_run_reports_exhausted_and_internal(tiny):
    board, root = tiny
    stats = solve(board, root).stats
    assert stats.termination == "exhausted"
    assert stats.ordering == "internal"
    assert stats.nodes > 0
    assert stats.terminals > 0


def test_an_external_orderer_is_recorded_as_such(tiny):
    """adr-004 R2: a run ordered from outside Axis 1 is not on the proof path."""
    board, root = tiny
    result = Solver(board, order=lambda b, s, m, t: m).solve(root)
    assert result.stats.ordering == "external"


def test_stats_serialise_for_an_artefact_header(tiny):
    board, root = tiny
    d = solve(board, root).stats.as_dict()
    assert set(d) >= {"nodes", "ordering", "termination"}
    assert d["termination"] == "exhausted"


# -- the budget raises rather than returning something unproved ---------------


def test_budget_raises_instead_of_returning_a_partial_value(tiny):
    board, root = tiny
    s = Solver(board, max_nodes=5)
    with pytest.raises(BudgetExceededError, match="node budget"):
        s.solve(root)


def test_a_budgeted_failure_is_recorded_as_such(tiny):
    board, root = tiny
    s = Solver(board, max_nodes=5)
    with pytest.raises(BudgetExceededError):
        s.solve(root)
    assert s.stats.termination == "budget"


def test_a_budget_large_enough_still_proves(tiny):
    board, root = tiny
    result = Solver(board, max_nodes=10_000_000).solve(root)
    assert result.value in (WIN, LOSS)
    assert result.stats.termination == "exhausted"


def test_stats_reset_between_solves(tiny):
    """A budget failure must not leave `termination` poisoned for the next run."""
    board, root = tiny
    s = Solver(board, max_nodes=5)
    with pytest.raises(BudgetExceededError):
        s.solve(root)
    s.max_nodes = None
    assert s.solve(root).stats.termination == "exhausted"


# -- principal variation ------------------------------------------------------


def test_best_move_is_legal_and_preserves_the_value(tiny):
    board, root = tiny
    result = solve(board, root)
    assert result.best in legal_moves(board, root)
    child = apply_move(board, root, result.best)
    # The child is the opponent's node, so its value is the negation.
    assert -solve(board, child).value == result.value


def test_principal_variation_is_a_legal_line(tiny):
    board, root = tiny
    s = Solver(board, tt=TranspositionTable(1 << 14))
    s.solve(root)
    line = s.principal_variation(root)

    assert line
    state = root
    for move in line:
        assert move in legal_moves(board, state)
        state = apply_move(board, state, move)


def test_principal_variation_of_a_terminal_position_is_empty(tiny):
    board, root = tiny
    s = Solver(board)
    terminal = walk(board, root, root.n_cells)
    assert s.principal_variation(terminal) == []


# -- unpruned mode is a measuring instrument, not just a slow solver ----------


def _stored(tt):
    return [e for e in tt.entries() if e.key is not None]


def test_unpruned_stores_only_extremal_bounds(tiny):
    """EXP-001's V3 reads the table on this invariant, so it is pinned here.

    On a two-valued objective every score sits on a window endpoint, so nothing
    is ever flagged EXACT: a value is stored as UPPER of ``LOSS`` or LOWER of
    ``WIN``, and an extremal bound *is* the value. That is what lets V3 compare
    a forward entry against the sweep at all.

    It stops being true the moment an unpruned node is searched in a narrowed
    window. Disabling the cutoff while still passing ``(-beta, -alpha)`` lets
    alpha reach ``WIN`` and the remaining subtree be searched at ``alpha ==
    beta``, which yields UPPER-of-``WIN`` — an upper bound on the maximum, which
    constrains nothing. V3 cannot compare those and has to discard them, which
    is how the defect was found: an unpruned 3×3 run reported 46.2% coverage and
    ``DISAGREE``, with every reported problem reading "an UPPER bound of 1 is
    not extremal" and not one of them an actual value mismatch.
    """
    board, root = tiny
    tt = TranspositionTable(1 << 14, verify=True)
    Solver(board, tt=tt, prune=False).solve(root)

    entries = _stored(tt)
    assert entries, "the probe never exercised the table"
    for entry in entries:
        if entry.flag is Flag.UPPER:
            assert entry.value == LOSS, "an UPPER bound of WIN constrains nothing"
        elif entry.flag is Flag.LOWER:
            assert entry.value == WIN, "a LOWER bound of LOSS constrains nothing"


def test_unpruned_reaches_more_positions_than_pruned(tiny):
    """The whole reason V3 has an unpruned mode: coverage, not a different value."""
    board, root = tiny

    pruned_tt = TranspositionTable(1 << 14, verify=True)
    pruned = Solver(board, tt=pruned_tt, prune=True).solve(root)

    open_tt = TranspositionTable(1 << 14, verify=True)
    unpruned = Solver(board, tt=open_tt, prune=False).solve(root)

    assert pruned.value == unpruned.value
    assert len(_stored(open_tt)) > len(_stored(pruned_tt))
