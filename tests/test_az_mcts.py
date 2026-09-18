"""Tests for ``az/mcts.py`` — PUCT and the three expansion modes.

The load-bearing test here is
:func:`test_the_cheap_class_key_agrees_with_applying_the_move`. Grouping aliased
actions *should* be defined as "these two moves reach the same
:meth:`GameState.key`", and that definition costs an ``apply_move`` per move —
at the 5x5 root, 1,450 of them per expansion, which is more than the search.
``occupied_arrow_key`` replaces it with an integer AND, justified by adr-003
(placed tiles are inert) and adr-006 (flips never chain). That justification is
an argument, and an argument can be wrong or can stop being true, so the two
definitions are checked against each other on real positions rather than trusted.

EXP-010's three arms are only interpretable if the modes differ in exactly the
way the registry says they do, so those properties are pinned too.
"""

from __future__ import annotations

import pytest

from az.mcts import (
    MCTS,
    ExpansionMode,
    best_move,
    group_by_position,
    occupied_arrow_key,
    policy_target,
    visit_counts,
)
from fliphex.moves import apply_move, legal_moves
from fliphex.rules import is_terminal
from fliphex.state import Colour
from fliphex.variant import Arm, Variant

TINY = Variant(3, 3, Arm("h1"))
SMALL = Variant(5, 3, Arm("h2"))
FULL = Variant(5, 5, Arm("h1"))


def _play(variant, plies: int, seed: int = 1):
    """Advance ``plies`` moves with a fixed pseudo-random walk."""
    from random import Random

    rng = Random(seed)
    board, state = variant.board(), variant.initial_state()
    for _ in range(plies):
        if is_terminal(state):
            break
        state = apply_move(board, state, rng.choice(legal_moves(board, state)))
    return board, state


# -- the cheap key must mean what the expensive one means ---------------------


@pytest.mark.parametrize("variant", [TINY, SMALL, FULL])
@pytest.mark.parametrize("plies", [0, 3, 7])
def test_the_cheap_class_key_agrees_with_applying_the_move(variant, plies):
    """``(cell, tile, arrows & occupied)`` partitions exactly as ``key()`` does.

    Both directions matter. Same key implies the same resulting position, or the
    search merges two genuinely different moves and silently loses one. Different
    key implies different positions, or deduplication leaves aliases behind and
    R13 is only partly addressed.
    """
    board, state = _play(variant, plies)
    if is_terminal(state):
        pytest.skip("walk ended the game")
    moves = legal_moves(board, state)

    by_cheap: dict[tuple[int, int, int], list] = {}
    by_exact: dict[object, list] = {}
    for move in moves:
        cheap = (move.cell, move.tile, occupied_arrow_key(board, state, move))
        by_cheap.setdefault(cheap, []).append(move)
        by_exact.setdefault(apply_move(board, state, move).key(), []).append(move)

    assert sorted(map(sorted, by_cheap.values())) == sorted(
        map(sorted, by_exact.values())
    )


def test_the_measured_collapse_is_reproduced_at_the_5x5_root():
    """adr-005's Phase 3 amendment: 1,450 actions, 325 positions, 4.46x.

    325 is 25 cells x 13 tiles — every rotation is inert on an empty board.
    """
    board, state = FULL.board(), FULL.initial_state()
    moves = legal_moves(board, state)
    classes = group_by_position(board, state, moves)

    assert len(moves) == 1450
    assert len(classes) == 325 == 25 * 13
    assert round(len(moves) / len(classes), 2) == 4.46


def test_rotation_matters_once_a_neighbour_is_occupied():
    """The mechanism, isolated: inertness is a property of the neighbourhood.

    On an empty board every rotation of a tile is the same move. Put one stone
    beside the target cell and the rotations that point at it separate from the
    ones that do not.
    """
    board, empty = FULL.board(), FULL.initial_state()
    cell = 12
    neighbour = next(n for n in board.neighbours(cell) if n >= 0)

    on_empty = {
        occupied_arrow_key(board, empty, m)
        for m in legal_moves(board, empty)
        if m.cell == cell and m.tile == 0
    }
    assert on_empty == {0}, "no arrow can hit anything on an empty board"

    occupied = empty.with_colour(neighbour, Colour.PURPLE)
    keys = {
        occupied_arrow_key(board, occupied, m)
        for m in legal_moves(board, occupied)
        if m.cell == cell and m.tile == 0
    }
    assert len(keys) > 1, "a single-arrow tile must now distinguish its rotations"


# -- the three modes differ exactly as EXP-010 says ---------------------------


def test_position_mode_has_one_child_per_distinct_position():
    board, state = SMALL.board(), SMALL.initial_state()
    root = MCTS(board, mode=ExpansionMode.POSITION, seed=3).run(state, 30)

    assert len(root.children) == len(
        group_by_position(board, state, legal_moves(board, state))
    )
    assert sum(c.multiplicity for c in root.children) == len(legal_moves(board, state))


def test_action_and_multiplicity_keep_every_action_as_its_own_child():
    board, state = SMALL.board(), SMALL.initial_state()
    n_actions = len(legal_moves(board, state))

    for mode in (ExpansionMode.ACTION, ExpansionMode.MULTIPLICITY):
        root = MCTS(board, mode=mode, seed=3).run(state, 20)
        assert len(root.children) == n_actions, mode


def test_multiplicity_gives_each_position_the_same_prior_mass_as_position_mode():
    """Arm C's whole purpose: same prior mass per position, more children.

    Without this, arm C would not separate "fewer children" from "prior mass",
    and EXP-010's attribution of the benefit collapses.
    """
    board, state = SMALL.board(), SMALL.initial_state()
    per_class = MCTS(board, mode=ExpansionMode.MULTIPLICITY, seed=3).run(state, 1)
    classes = group_by_position(board, state, legal_moves(board, state))

    mass: dict[tuple[int, int, int], float] = {}
    for child in per_class.children:
        key = (
            child.move.cell,
            child.move.tile,
            occupied_arrow_key(board, state, child.move),
        )
        mass[key] = mass.get(key, 0.0) + child.prior

    assert len(mass) == len(classes)
    assert max(mass.values()) - min(mass.values()) < 1e-9


def test_action_mode_concentrates_prior_on_aliased_positions():
    """The bias R13 describes, stated as a test rather than as prose."""
    board, state = SMALL.board(), SMALL.initial_state()
    root = MCTS(board, mode=ExpansionMode.ACTION, seed=3).run(state, 1)

    mass: dict[tuple[int, int, int], float] = {}
    for child in root.children:
        key = (
            child.move.cell,
            child.move.tile,
            occupied_arrow_key(board, state, child.move),
        )
        mass[key] = mass.get(key, 0.0) + child.prior

    assert max(mass.values()) > 3 * min(mass.values())


# -- search invariants --------------------------------------------------------


@pytest.mark.parametrize("mode", list(ExpansionMode))
def test_visits_are_conserved(mode):
    board, state = SMALL.board(), SMALL.initial_state()
    root = MCTS(board, mode=mode, seed=7).run(state, 120)

    assert root.visits == 120
    assert sum(c.visits for c in root.children) == 120


@pytest.mark.parametrize("mode", list(ExpansionMode))
def test_the_search_is_deterministic_given_a_seed(mode):
    board, state = SMALL.board(), SMALL.initial_state()
    a = MCTS(board, mode=mode, seed=11).run(state, 80)
    b = MCTS(board, mode=mode, seed=11).run(state, 80)

    assert visit_counts(a) == visit_counts(b)
    assert best_move(a) == best_move(b)


def test_a_forced_win_is_found_when_the_budget_can_see_it():
    """One empty cell left: every playout is the whole game, so the value is
    exact and search cannot be wrong."""
    board, state = _play(TINY, TINY.n_cells - 1, seed=4)
    assert not is_terminal(state)

    root = MCTS(board, mode=ExpansionMode.POSITION, seed=2).run(state, 60)
    chosen = apply_move(board, state, best_move(root))
    from fliphex.rules import winner

    values = {
        winner(apply_move(board, state, m)) == state.to_move
        for m in legal_moves(board, state)
    }
    if True in values:
        assert winner(chosen) == state.to_move, "a winning move existed and was missed"


def test_policy_target_at_zero_temperature_is_greedy():
    board, state = SMALL.board(), SMALL.initial_state()
    root = MCTS(board, mode=ExpansionMode.POSITION, seed=9).run(state, 100)

    pi = policy_target(root, temperature=0.0)
    assert abs(sum(pi.values()) - 1.0) < 1e-9
    assert pi[best_move(root)] > 0
    assert sum(1 for v in pi.values() if v > 0) <= len(root.children)


def test_temperature_one_is_normalised_visit_counts():
    board, state = SMALL.board(), SMALL.initial_state()
    root = MCTS(board, mode=ExpansionMode.POSITION, seed=9).run(state, 100)

    pi = policy_target(root, temperature=1.0)
    counts = visit_counts(root)
    total = sum(counts.values())
    for move, share in pi.items():
        assert abs(share - counts[move] / total) < 1e-9


def test_dirichlet_noise_only_touches_the_root():
    """adr-005 puts noise at the root; a child's prior must be untouched."""
    board, state = SMALL.board(), SMALL.initial_state()
    quiet = MCTS(board, mode=ExpansionMode.POSITION, seed=6, dirichlet_weight=0.0)
    noisy = MCTS(board, mode=ExpansionMode.POSITION, seed=6, dirichlet_weight=0.25)

    a, b = quiet.run(state, 1), noisy.run(state, 1)
    assert [c.prior for c in a.children] != [c.prior for c in b.children]
    assert abs(sum(c.prior for c in b.children) - 1.0) < 1e-9


def test_sibling_merging_does_not_create_a_dag():
    """Every node has exactly one parent, so there is no DAG backup problem.

    adr-005 predicted deduplication would turn the tree into a DAG and called
    the backup rule an unresolved subtlety. That is true of *cross-parent*
    transposition; it is not true of the sibling-alias merging that addresses
    R13. Pinned as a test because the registry's EXP-010 entry was corrected on
    the strength of it.
    """
    board, state = SMALL.board(), SMALL.initial_state()
    root = MCTS(board, mode=ExpansionMode.POSITION, seed=8).run(state, 150)

    seen: set[int] = set()
    stack = [root]
    while stack:
        node = stack.pop()
        assert id(node) not in seen, "a node was reached twice — the tree is a DAG"
        seen.add(id(node))
        stack.extend(node.children)
