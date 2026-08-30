"""Tests for solver.transposition.

Two properties carry the weight, because both are silent when they break:

- an entry stores a **bound**, and a bound may only be believed when it settles
  the current window;
- a Zobrist collision must be **detected**, not used. On the 5×3 the state count
  is four times past the 64-bit birthday bound, so this is expected behaviour
  rather than a defensive flourish.
"""

import pytest

from fliphex.moves import apply_move, legal_moves
from fliphex.state import GameState
from fliphex.variant import FIVE_BY_THREE, THREE_BY_THREE
from solver.transposition import (
    Flag,
    NullTable,
    TranspositionTable,
    max_capacity_for,
    pack_key,
    unpack_key,
)


@pytest.fixture
def states():
    """Return two distinct positions from the 3×3 variant."""
    board = THREE_BY_THREE.board()
    root = THREE_BY_THREE.initial_state()
    child = apply_move(board, root, legal_moves(board, root)[0])
    assert root.key() != child.key()
    return root, child


# -- construction -------------------------------------------------------------


@pytest.mark.parametrize("capacity", [0, 3, 5, 100, -8])
def test_capacity_must_be_a_power_of_two(capacity):
    with pytest.raises(ValueError, match="power of two"):
        TranspositionTable(capacity)


@pytest.mark.parametrize("capacity", [1, 2, 1024, 1 << 20])
def test_powers_of_two_are_accepted(capacity):
    assert TranspositionTable(capacity).capacity == capacity


def test_empty_table(states):
    root, _ = states
    tt = TranspositionTable(16)
    assert len(tt) == 0
    assert tt.load == 0.0
    assert tt.probe(root, 0, -1, 1) == (None, None)
    assert tt.misses == 1


# -- bounds: the defect class this exists to prevent --------------------------


def test_exact_entry_is_returned_whatever_the_window(states):
    root, _ = states
    tt = TranspositionTable(16)
    tt.store(root, 1, Flag.EXACT, depth=9)
    for alpha, beta in ((-1, 1), (-1, 0), (1, 2), (5, 9)):
        value, _ = tt.probe(root, 9, alpha, beta)
        assert value == 1


def test_lower_bound_only_settles_a_fail_high(states):
    root, _ = states
    tt = TranspositionTable(16)
    # True value is at least 5.
    tt.store(root, 5, Flag.LOWER, depth=9)

    # beta <= 5: the bound already proves a cutoff.
    assert tt.probe(root, 9, -100, 5)[0] == 5
    assert tt.probe(root, 9, -100, 3)[0] == 5
    # beta > 5: "at least 5" says nothing about where inside the window it lands.
    assert tt.probe(root, 9, -100, 6)[0] is None
    assert tt.probe(root, 9, 0, 100)[0] is None


def test_upper_bound_only_settles_a_fail_low(states):
    root, _ = states
    tt = TranspositionTable(16)
    # True value is at most 5.
    tt.store(root, 5, Flag.UPPER, depth=9)

    assert tt.probe(root, 9, 5, 100)[0] == 5
    assert tt.probe(root, 9, 7, 100)[0] == 5
    assert tt.probe(root, 9, 4, 100)[0] is None
    assert tt.probe(root, 9, -100, 100)[0] is None


def test_a_bound_is_never_mistaken_for_a_value(states):
    """The whole point: a LOWER entry inside the window must not be returned."""
    root, _ = states
    tt = TranspositionTable(16)
    tt.store(root, 0, Flag.LOWER, depth=9)
    assert tt.probe(root, 9, -100, 100)[0] is None
    tt.clear()
    tt.store(root, 0, Flag.EXACT, depth=9)
    assert tt.probe(root, 9, -100, 100)[0] == 0


# -- depth --------------------------------------------------------------------


def test_shallow_entry_yields_no_value_but_still_a_move(states):
    """A shallow hit is useless as a score and still the best move to try first.

    This is what makes TT-move-first ordering pay, so the move must survive the
    depth rejection.
    """
    root, _ = states
    board = THREE_BY_THREE.board()
    move = legal_moves(board, root)[0]
    tt = TranspositionTable(16)
    tt.store(root, 1, Flag.EXACT, depth=2, best=move)

    value, best = tt.probe(root, 5, -100, 100)
    assert value is None
    assert best == move

    value, best = tt.probe(root, 2, -100, 100)
    assert value == 1
    assert best == move


def test_deeper_entry_is_not_replaced_by_a_shallower_one(states):
    root, _ = states
    tt = TranspositionTable(16)
    tt.store(root, 1, Flag.EXACT, depth=9)
    tt.store(root, -1, Flag.EXACT, depth=2)
    assert tt.probe(root, 9, -100, 100)[0] == 1
    assert tt.stores == 1


def test_equal_or_deeper_entry_replaces(states):
    root, _ = states
    tt = TranspositionTable(16)
    tt.store(root, 1, Flag.EXACT, depth=2)
    tt.store(root, -1, Flag.EXACT, depth=4)
    assert tt.probe(root, 2, -100, 100)[0] == -1
    assert tt.replacements == 1


# -- collisions ---------------------------------------------------------------


def test_verified_table_detects_a_slot_collision(states):
    """A single-slot table forces every position into the same bucket."""
    root, child = states
    tt = TranspositionTable(1, verify=True)
    tt.store(root, 1, Flag.EXACT, depth=9)

    value, best = tt.probe(child, 9, -100, 100)
    assert value is None
    assert best is None
    assert tt.collisions == 1
    assert tt.misses == 1
    assert tt.hits == 0


def test_unverified_table_returns_the_wrong_entry(states):
    """The trade, made explicit.

    Without verification the same collision is served as a hit. For an agent
    that costs one bad move; for an exhaustive solve it writes a wrong value
    that then propagates, which is why ``verify`` defaults to on.
    """
    root, child = states
    tt = TranspositionTable(1, verify=False)
    tt.store(root, 1, Flag.EXACT, depth=9)

    value, _ = tt.probe(child, 9, -100, 100)
    assert value == 1  # wrong, and undetectable without the key
    assert tt.collisions == 0
    assert tt.hits == 1


def test_verification_is_on_by_default():
    assert TranspositionTable(4).verify is True


# -- NullTable: "without a table" must mean no memo, not a tiny table ---------


def test_null_table_never_remembers(states):
    root, _ = states
    tt = NullTable()
    tt.store(root, 1, Flag.EXACT, depth=9)
    assert tt.probe(root, 9, -100, 100) == (None, None)
    assert len(tt) == 0
    assert tt.hits == 0
    assert tt.misses == 1  # the probe; store() counts nothing


def test_null_table_reports_no_collisions(states):
    """Why this exists rather than a one-slot real table.

    A capacity-1 verified table would serve every probe as a *detected
    collision* — correct, but it would pollute ``collisions``, a counter that
    exists to be reported as adr-010 verification evidence rather than as an
    artefact of a benchmark configuration.
    """
    root, child = states
    tt = NullTable()
    tt.store(root, 1, Flag.EXACT, depth=9)
    tt.probe(child, 9, -100, 100)
    assert tt.collisions == 0

    real = TranspositionTable(1, verify=True)
    real.store(root, 1, Flag.EXACT, depth=9)
    real.probe(child, 9, -100, 100)
    assert real.collisions == 1


def test_null_table_still_latches_provenance(states):
    """Discarding entries must not discard adr-004 R1 provenance."""
    root, _ = states
    tt = NullTable()
    tt.store(root, 1, Flag.EXACT, depth=3, exhaustive=False)
    assert tt.truncated is True


# -- provenance (adr-004 R1/R3) -----------------------------------------------


def test_truncated_starts_false_and_latches(states):
    root, child = states
    tt = TranspositionTable(16)
    assert tt.truncated is False

    tt.store(root, 1, Flag.EXACT, depth=9)
    assert tt.truncated is False

    tt.store(child, 1, Flag.LOWER, depth=3, exhaustive=False)
    assert tt.truncated is True


def test_clearing_does_not_un_truncate_a_run(states):
    """``truncated`` records the run, not the current contents."""
    root, _ = states
    tt = TranspositionTable(16)
    tt.store(root, 1, Flag.EXACT, depth=3, exhaustive=False)
    tt.clear()
    assert len(tt) == 0
    assert tt.hits == tt.misses == tt.stores == 0
    assert tt.truncated is True


# -- bookkeeping --------------------------------------------------------------


def test_load_and_len(states):
    root, child = states
    tt = TranspositionTable(4)
    assert len(tt) == 0
    tt.store(root, 1, Flag.EXACT, depth=9)
    tt.store(child, 1, Flag.EXACT, depth=9)
    assert len(tt) == 2
    assert tt.load == 0.5


def test_stats_reports_what_a_run_record_needs(states):
    root, child = states
    tt = TranspositionTable(16)
    tt.store(root, 1, Flag.EXACT, depth=9)
    tt.probe(root, 9, -100, 100)
    tt.probe(child, 9, -100, 100)

    s = tt.stats()
    assert s["hits"] == 1
    assert s["misses"] == 1
    assert s["probes"] == 2
    assert s["hit_rate"] == 0.5
    assert s["verify"] is True
    assert s["truncated"] is False
    assert s["occupied"] == 1


def test_hit_rate_is_zero_before_any_probe():
    assert TranspositionTable(4).stats()["hit_rate"] == 0.0


# -- it actually transposes ---------------------------------------------------


def test_a_position_is_found_by_any_state_with_the_same_key():
    """The invariant the whole table rests on.

    The Zobrist must be a pure function of the search key — colours, hands, side
    to move — and of nothing else. If it ever depended on the path taken (on
    ``history``, say), two orderings reaching the same position would occupy
    different slots and every transposition would be missed silently, costing
    correctness nothing but making the table useless. Rebuilding a state from
    its own key and probing with the rebuilt copy is the direct test.
    """
    board = FIVE_BY_THREE.board()
    root = FIVE_BY_THREE.initial_state()
    walked = root
    for _ in range(3):
        walked = apply_move(board, walked, legal_moves(board, walked)[0])

    rebuilt = GameState.build(walked.colours, walked.hands, walked.to_move)
    assert rebuilt.zobrist == walked.zobrist
    assert rebuilt.history == ()  # the path is gone, the key is not

    tt = TranspositionTable(1 << 12)
    tt.store(walked, 1, Flag.EXACT, depth=12)
    assert tt.probe(rebuilt, 12, -100, 100)[0] == 1
    assert tt.collisions == 0


# -- the packed key: exactly as strong as the tuple it replaced ---------------


def _walk_states(variant, depth=3, width=40):
    """A spread of real positions: every first move, then a few plies deep."""
    board = variant.board()
    states = [variant.initial_state()]
    frontier = [variant.initial_state()]
    for _ in range(depth):
        nxt = []
        for state in frontier[:width]:
            if state.is_terminal():
                continue
            for move in legal_moves(board, state)[:width]:
                child = apply_move(board, state, move)
                states.append(child)
                nxt.append(child)
        frontier = nxt
    return states


@pytest.mark.parametrize("variant", [THREE_BY_THREE, FIVE_BY_THREE])
def test_packed_key_round_trips(variant):
    for state in _walk_states(variant):
        lo, hi = pack_key(state)
        assert unpack_key(lo, hi, state.n_cells) == state.key()


@pytest.mark.parametrize("variant", [THREE_BY_THREE, FIVE_BY_THREE])
def test_packed_comparison_is_exactly_the_tuple_comparison(variant):
    """The property the whole memory saving rests on.

    Verification may only get cheaper, never weaker: two states must pack alike
    **iff** their keys are equal. A packing that merged two distinct positions
    would turn a detected collision back into a silent wrong value, which is the
    one failure mode this module exists to prevent.
    """
    states = _walk_states(variant)
    packed = {}
    for state in states:
        packed.setdefault(pack_key(state), set()).add(state.key())
    for keys in packed.values():
        assert len(keys) == 1, "distinct keys packed to the same bits"
    assert len({s.key() for s in states}) == len(packed)


def test_packed_words_fit_signed_64_bit():
    """Both halves must be storable in ``array('q')`` without overflowing."""
    for variant in (THREE_BY_THREE, FIVE_BY_THREE):
        for state in _walk_states(variant, depth=2):
            for word in pack_key(state):
                assert 0 <= word < 1 << 63


# -- entries(): how adr-010 V3 reads the table --------------------------------


def test_entries_yields_every_occupied_slot_decoded(states):
    root, child = states
    board = THREE_BY_THREE.board()
    move = legal_moves(board, root)[0]
    tt = TranspositionTable(64)
    tt.store(root, 1, Flag.EXACT, depth=9, best=move)
    tt.store(child, -1, Flag.LOWER, depth=4)

    got = sorted(tt.entries(), key=lambda e: e.value)
    assert len(got) == 2
    assert [e.value for e in got] == [-1, 1]

    exact = next(e for e in got if e.flag is Flag.EXACT)
    assert exact.key == root.key()
    assert exact.depth == 9
    assert exact.best == move

    lower = next(e for e in got if e.flag is Flag.LOWER)
    assert lower.key == child.key()
    assert lower.best is None


def test_entries_is_empty_without_verification():
    """No key is stored, so V3 has nothing to compare — and must see that."""
    root = THREE_BY_THREE.initial_state()
    tt = TranspositionTable(16, verify=False)
    tt.store(root, 1, Flag.EXACT, depth=9)
    assert [e.key for e in tt.entries()] == [None]


# -- sizing: the arithmetic that must not be folklore -------------------------


def test_bytes_per_slot_matches_the_buffers_actually_allocated():
    """Pins the constant a caller sizes a table against.

    Adding a sixth array and forgetting this constant would make
    ``max_capacity_for`` under-count, and an under-counted table does not fail
    on construction — it fills over hours and dies to the OOM killer with no
    checkpoint written. That happened twice on 2026-08-23.
    """
    n = 1 << 8
    verified = TranspositionTable(n, verify=True)
    buffers = (
        verified._meta,  # noqa: SLF001 — measuring the layout *is* the test
        verified._value,  # noqa: SLF001
        verified._best,  # noqa: SLF001
        verified._key_lo,  # noqa: SLF001
        verified._key_hi,  # noqa: SLF001
    )
    total = sum(b.buffer_info()[1] * b.itemsize for b in buffers)
    assert total / n == TranspositionTable.BYTES_PER_SLOT

    plain = TranspositionTable(n, verify=False)
    bare = (plain._meta, plain._value, plain._best)  # noqa: SLF001
    assert sum(b.buffer_info()[1] * b.itemsize for b in bare) / n == (
        TranspositionTable.BYTES_PER_SLOT_UNVERIFIED
    )


def test_max_capacity_never_exceeds_its_budget():
    for budget in (0, 27, 28, 1 << 20, 3 * 1024**3, 12 * 1024**3):
        capacity = max_capacity_for(budget)
        assert capacity * TranspositionTable.BYTES_PER_SLOT <= budget
        if capacity:
            assert capacity & (capacity - 1) == 0
            assert 2 * capacity * TranspositionTable.BYTES_PER_SLOT > budget


def test_max_capacity_is_zero_when_nothing_fits():
    assert max_capacity_for(0) == 0
    assert max_capacity_for(TranspositionTable.BYTES_PER_SLOT - 1) == 0
