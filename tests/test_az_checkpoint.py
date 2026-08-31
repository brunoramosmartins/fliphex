"""Tests for ``az/replay_buffer.py`` and ``az/checkpoint.py``.

The load-bearing one is
:func:`test_a_resumed_run_is_indistinguishable_from_an_uninterrupted_one`. Every
other test here checks that some piece of state survives a round trip; that one
checks the property those pieces exist *for*, and it is the property the weaker
formulation — "resume produces a valid continuation" — would let through.

The distinction is not academic. The project's third hypothesis reports a
per-seed win rate across five or more seeds and the variance between them. A
resume that reseeded would produce runs that are individually fine and
collectively meaningless.
"""

from __future__ import annotations

import json
import random
import sys
from array import array

import pytest
import torch

from az.checkpoint import (
    FORMAT_VERSION,
    MANIFEST,
    Checkpoint,
    TrainingState,
    capture_rng,
    restore_rng,
)
from az.encoding import encode
from az.mcts import MCTS, ExpansionMode, policy_target
from az.network import FlipHexNet
from az.replay_buffer import (
    ReplayBuffer,
    Sample,
    pack_policy,
    samples_from_game,
)
from fliphex.moves import Move
from fliphex.state import Colour
from fliphex.variant import Arm, Variant

TINY = Variant(3, 3, Arm("h1"))


def a_sample(tag: int) -> Sample:
    return Sample(
        planes=bytes([tag % 2]) * 10,
        moves=bytes(Move(tag % 9, 0, 0)),
        probs=array("f", [1.0]).tobytes(),
        value=1.0 if tag % 2 else -1.0,
    )


# -- the value target ---------------------------------------------------------


def test_z_is_read_from_each_positions_own_mover():
    """The alternation is the easiest thing here to write backwards."""
    board, state = TINY.board(), TINY.initial_state()
    planes = encode(board, state)
    pi = {Move(0, 0, 0): 1.0}
    positions = [
        (planes, pi, Colour.PURPLE),
        (planes, pi, Colour.GREEN),
        (planes, pi, Colour.PURPLE),
    ]

    samples = samples_from_game(positions, winner=Colour.PURPLE)

    assert [s.value for s in samples] == [1.0, -1.0, 1.0]


def test_the_loser_moving_first_still_gets_alternating_signs():
    planes, pi = b"\x00" * 10, {Move(0, 0, 0): 1.0}
    positions = [(planes, pi, Colour.PURPLE), (planes, pi, Colour.GREEN)]

    samples = samples_from_game(positions, winner=Colour.GREEN)

    assert [s.value for s in samples] == [-1.0, 1.0]


def test_a_drawn_game_is_refused():
    """25 cells is odd, so a draw means the outcome was computed wrongly."""
    positions = [(b"\x00" * 10, {Move(0, 0, 0): 1.0}, Colour.PURPLE)]

    with pytest.raises(ValueError, match="odd cell count"):
        samples_from_game(positions, winner=Colour.EMPTY)


def test_every_z_is_exactly_plus_or_minus_one():
    planes, pi = b"\x00" * 10, {Move(0, 0, 0): 1.0}
    positions = [(planes, pi, c) for c in (Colour.PURPLE, Colour.GREEN) * 6]

    samples = samples_from_game(positions, winner=Colour.PURPLE)

    assert {s.value for s in samples} == {1.0, -1.0}


# -- the packed policy --------------------------------------------------------


def test_packing_round_trips_through_the_policy_property():
    pi = {Move(3, 7, 2): 0.5, Move(11, 0, 5): 0.25, Move(24, 12, 0): 0.25}
    moves, probs = pack_policy(pi)

    sample = Sample(planes=b"", moves=moves, probs=probs, value=1.0)

    assert dict(sample.policy) == pytest.approx(pi)


def test_packing_drops_unvisited_moves():
    """Zero-probability entries carry no gradient and would cost bytes forever."""
    pi = {Move(0, 0, 0): 1.0, Move(1, 0, 0): 0.0, Move(2, 0, 0): 0.0}

    moves, probs = pack_policy(pi)

    assert len(moves) == 3, "one move, three bytes"
    assert len(probs) == 4, "one float32"


def test_packing_is_three_bytes_and_one_float_per_move():
    pi = {Move(i, 0, 0): 1.0 / 20 for i in range(20)}

    moves, probs = pack_policy(pi)

    assert len(moves) == 60
    assert len(probs) == 80


def test_a_move_that_does_not_fit_a_byte_is_refused():
    """A silent truncation here would corrupt every target it touched."""
    with pytest.raises(ValueError, match="packed format"):
        pack_policy({Move(300, 0, 0): 1.0})


def test_the_packed_form_is_much_smaller_than_the_objects():
    """The reason the format exists, checked rather than asserted in prose."""
    pi = {Move(i % 25, i % 13, i % 6): 1.0 / 149 for i in range(149)}
    moves, probs = pack_policy(pi)

    packed = len(moves) + len(probs)
    as_objects = sum(
        sys.getsizeof(m) + sys.getsizeof(p) for m, p in pi.items()
    ) + sys.getsizeof(pi)

    assert packed < as_objects / 8


def test_a_real_search_policy_packs_and_unpacks(tmp_path):
    """End to end, from the search's own output rather than a synthetic dict."""
    board, state = TINY.board(), TINY.initial_state()
    search = MCTS(board, mode=ExpansionMode.POSITION, seed=2)
    root = search.run(state, 60)
    pi = policy_target(root, temperature=1.0)

    [sample] = samples_from_game(
        [(encode(board, state), pi, Colour.PURPLE)], winner=Colour.PURPLE
    )
    unpacked = dict(sample.policy)

    assert unpacked.keys() == {m for m, p in pi.items() if p > 0}
    assert sum(unpacked.values()) == pytest.approx(1.0, abs=1e-5)
    for move, probability in unpacked.items():
        assert probability == pytest.approx(pi[move], abs=1e-6)


# -- the ring buffer ----------------------------------------------------------


def test_the_buffer_evicts_oldest_first():
    buffer = ReplayBuffer(capacity=3)

    buffer.extend(a_sample(i) for i in range(5))

    assert len(buffer) == 3
    assert [s.policy[0][0].cell for s in buffer] == [2, 3, 4]


def test_capacity_must_be_positive():
    with pytest.raises(ValueError, match="capacity"):
        ReplayBuffer(capacity=0)


def test_sampling_an_empty_buffer_is_an_error_not_an_empty_batch():
    with pytest.raises(ValueError, match="empty buffer"):
        ReplayBuffer(capacity=4).sample(2)


def test_a_batch_can_exceed_the_buffer_while_it_is_still_filling():
    """Sampling is with replacement, so early generations still form batches."""
    buffer = ReplayBuffer(capacity=100)
    buffer.extend([a_sample(1)])

    assert len(buffer.sample(32)) == 32


def test_the_refresh_fraction_is_the_closed_form():
    buffer = ReplayBuffer(capacity=1000)

    assert buffer.refresh_fraction(250) == pytest.approx(0.25)
    assert buffer.refresh_fraction(1000) == pytest.approx(1.0)
    assert buffer.refresh_fraction(4000) == pytest.approx(1.0), "saturates at one"


def test_serialising_preserves_contents_order_and_the_write_cursor():
    """The cursor is invisible to a contents check but decides what dies next."""
    buffer = ReplayBuffer(capacity=4, seed=11)
    buffer.extend(a_sample(i) for i in range(6))

    restored = ReplayBuffer.from_bytes(buffer.to_bytes())
    restored.extend([a_sample(99)])
    buffer.extend([a_sample(99)])

    assert list(restored) == list(buffer)


def test_serialising_preserves_the_sampling_stream():
    buffer = ReplayBuffer(capacity=50, seed=3)
    buffer.extend(a_sample(i) for i in range(50))
    buffer.sample(10)

    restored = ReplayBuffer.from_bytes(buffer.to_bytes())

    assert restored.sample(20) == buffer.sample(20)


# -- the checkpoint -----------------------------------------------------------


def a_state(generation: int = 0, *, trained: bool = False) -> TrainingState:
    net = FlipHexNet(3, 3)
    champion = FlipHexNet(3, 3)
    optimiser = torch.optim.Adam(net.parameters(), lr=1e-3)
    if trained:
        # One real step, so the optimiser has moment estimates to lose.
        net(torch.zeros(2, 30, 3, 3))[3].sum().backward()
        optimiser.step()
    buffer = ReplayBuffer(capacity=32, seed=5)
    buffer.extend(a_sample(i) for i in range(20))
    python_rng, torch_rng = capture_rng()
    return TrainingState(
        generation=generation,
        last_gated=-1,
        challenger=net.state_dict(),
        champion=champion.state_dict(),
        optimiser=optimiser.state_dict(),
        buffer=buffer,
        python_rng=python_rng,
        torch_rng=torch_rng,
        meta={"seed": 5, "variant": "3x3-h1"},
    )


def test_a_fresh_directory_has_no_resume_point(tmp_path):
    assert Checkpoint(tmp_path).resume_point() is None


def test_a_saved_state_reloads(tmp_path):
    store = Checkpoint(tmp_path)
    state = a_state(generation=7)

    store.save(state)
    loaded = store.load()

    assert store.resume_point() == 7
    assert loaded.generation == 7
    assert loaded.meta == {"seed": 5, "variant": "3x3-h1"}
    assert list(loaded.buffer) == list(state.buffer)
    assert torch.equal(loaded.torch_rng, state.torch_rng)


def test_both_networks_survive_the_round_trip(tmp_path):
    """The champion matters as much as the challenger: it generates the data."""
    store = Checkpoint(tmp_path)
    state = a_state()

    store.save(state)
    loaded = store.load()

    for saved, restored in (
        (state.challenger, loaded.challenger),
        (state.champion, loaded.champion),
    ):
        assert saved.keys() == restored.keys()
        for key, tensor in saved.items():
            assert torch.equal(restored[key], tensor)

    rebuilt = FlipHexNet(3, 3)
    rebuilt.load_state_dict(loaded.challenger)


def test_the_optimiser_moments_are_kept(tmp_path):
    """Dropping Adam's moments restarts them and dents the loss curve on resume."""
    store = Checkpoint(tmp_path)
    state = a_state(trained=True)
    assert state.optimiser["state"], "the fixture must have taken a real step"

    store.save(state)
    loaded = store.load()

    assert loaded.optimiser["state"].keys() == state.optimiser["state"].keys()
    for key, moments in state.optimiser["state"].items():
        for name, tensor in moments.items():
            assert torch.equal(loaded.optimiser["state"][key][name], tensor)


def test_the_manifest_is_written_last(tmp_path):
    """A payload with no manifest is a crashed write, not a checkpoint."""
    store = Checkpoint(tmp_path)
    store.save(a_state())

    (tmp_path / MANIFEST).unlink()

    assert (tmp_path / Checkpoint.PAYLOAD).exists()
    assert store.resume_point() is None
    with pytest.raises(FileNotFoundError):
        store.load()


def test_an_incompatible_format_version_refuses_rather_than_guesses(tmp_path):
    store = Checkpoint(tmp_path)
    store.save(a_state())
    manifest = json.loads((tmp_path / MANIFEST).read_text())
    manifest["format_version"] = FORMAT_VERSION + 1
    (tmp_path / MANIFEST).write_text(json.dumps(manifest))

    with pytest.raises(ValueError, match="format version"):
        store.resume_point()


def test_a_checkpoint_without_rng_state_is_refused(tmp_path):
    state = a_state()
    state.python_rng = None

    with pytest.raises(ValueError, match="indistinguishable"):
        Checkpoint(tmp_path).save(state)


def test_saving_leaves_no_temporary_files(tmp_path):
    store = Checkpoint(tmp_path)

    store.save(a_state())

    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".")]


def test_the_gate_records_partial_progress(tmp_path):
    """400 games is ~34 minutes; a part-finished gate should not restart at zero."""
    store = Checkpoint(tmp_path)
    state = a_state()
    state.gate_wins, state.gate_games = 118, 210

    store.save(state)

    assert store.load().gate_games == 210
    assert store.manifest()["gate_wins"] == 118


# -- the property all of the above exists for ---------------------------------


def drive(steps: int) -> list[float]:
    """A stand-in for the stochastic part of a training loop."""
    return [random.random() + torch.rand(1).item() for _ in range(steps)]


def test_a_resumed_run_is_indistinguishable_from_an_uninterrupted_one(tmp_path):
    """The DoD: not a valid continuation -- the *same* run.

    A resume that restored the weights and the buffer but reseeded the
    generators would pass every other test in this file and still produce a run
    that cannot be reproduced from the seed it reports.
    """
    random.seed(1234)
    torch.manual_seed(1234)
    uninterrupted = drive(8)

    random.seed(1234)
    torch.manual_seed(1234)
    first_half = drive(4)

    # Captured at the checkpoint boundary, before anything else touches the
    # generators. Building the state below constructs two networks, and weight
    # initialisation draws from the torch stream -- capturing afterwards would
    # save a point the uninterrupted run never passed through.
    python_rng, torch_rng = capture_rng()

    store = Checkpoint(tmp_path)
    state = a_state(generation=4)
    state.python_rng, state.torch_rng = python_rng, torch_rng
    store.save(state)

    # Anything at all happens in between -- another process, a different seed.
    random.seed(999)
    torch.manual_seed(999)
    drive(50)

    loaded = store.load()
    restore_rng(loaded.python_rng, loaded.torch_rng)
    second_half = drive(4)

    assert first_half + second_half == uninterrupted
    assert loaded.generation == 4
