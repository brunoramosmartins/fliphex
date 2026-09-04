"""Tests for ``az/loop.py``.

The claim under test is not "the loop runs". It is that **an interrupted run
resumes into the same run it would have been** — same self-play games, same
batches, same gate, same weights — because everything downstream of Phase 4 is a
comparison between runs, and a resume that is merely a correct continuation of
something else quietly changes what is being compared.
"""

from __future__ import annotations

import json

import pytest
import torch

from az.checkpoint import Checkpoint
from az.loop import LoopConfig, run
from az.network import ConvRotationNet, FlipHexNet
from fliphex.variant import Arm, Variant

TINY = Variant(3, 3, Arm("h1"))


def a_config(tmp_path, **overrides) -> LoopConfig:
    """A loop small enough to run in a test and shaped like the real one."""
    defaults = dict(
        variant=TINY,
        seed=3,
        generations=2,
        games=4,
        simulations=4,
        steps=3,
        batch_size=8,
        buffer_capacity=200,
        gate_every=1,
        gate_games=4,
        gate_checkpoint_every=2,
        gate_simulations=4,
        workers=1,
        root=tmp_path / "run",
    )
    return LoopConfig(**{**defaults, **overrides})


def weights(state_dict) -> list:
    return [v.clone() for v in state_dict.values()]


def same(left, right) -> bool:
    return all(torch.equal(a, b) for a, b in zip(left, right, strict=True))


# -- the loop closes ----------------------------------------------------------


def test_the_loop_runs_generations_and_writes_history(tmp_path):
    config = a_config(tmp_path)
    rows = run(config, lambda: ConvRotationNet(3, 3))

    assert [r["generation"] for r in rows] == [0, 1]
    assert all(r["samples"] > 0 for r in rows)
    assert all(r["buffer"] >= r["samples"] for r in rows)
    assert all(r["gated"] for r in rows)

    lines = config.history_path.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["generation"] == 0


def test_the_buffer_crosses_generations(tmp_path):
    """The registered choice, and the loop's main off-policy assumption.

    Generation 1 must train on generation 0's samples as well as its own, or the
    slowly-moving target the design relies on is not there.
    """
    rows = run(a_config(tmp_path), lambda: ConvRotationNet(3, 3))

    assert rows[1]["buffer"] > rows[0]["buffer"]
    assert rows[1]["buffer"] == rows[0]["samples"] + rows[1]["samples"]
    # refresh_fraction is what makes the assumption legible rather than implicit.
    assert 0.0 < rows[1]["refresh_fraction"] <= 1.0


def test_champion_and_challenger_start_from_identical_weights(tmp_path):
    """Two draws would make the first gate a contest between two random nets."""
    config = a_config(tmp_path, generations=0)
    run(config, lambda: ConvRotationNet(3, 3))

    state = Checkpoint(config.root).load()
    assert same(weights(state.challenger), weights(state.champion))


# -- resume -------------------------------------------------------------------


def test_a_resumed_run_is_indistinguishable_from_an_uninterrupted_one(tmp_path):
    """The property the whole checkpoint design exists for.

    Run two generations straight through; run one, drop everything, and resume.
    The final weights, buffer contents and history must match exactly — not
    approximately, and not "the losses look similar".
    """
    straight = a_config(tmp_path / "a", generations=2)
    run(straight, lambda: ConvRotationNet(3, 3))
    whole = Checkpoint(straight.root).load()

    piecemeal = a_config(tmp_path / "b", generations=1)
    run(piecemeal, lambda: ConvRotationNet(3, 3))
    resumed_config = a_config(tmp_path / "b", generations=2)
    run(resumed_config)  # no make_net: the checkpoint's spec is authoritative
    resumed = Checkpoint(resumed_config.root).load()

    assert resumed.generation == whole.generation
    assert same(weights(resumed.challenger), weights(whole.challenger))
    assert same(weights(resumed.champion), weights(whole.champion))
    assert len(resumed.buffer) == len(whole.buffer)
    for left, right in zip(resumed.buffer, whole.buffer, strict=True):
        assert left.planes == right.planes
        assert left.moves == right.moves
        assert left.value == right.value

    left_rows = [json.loads(x) for x in straight.history_path.read_text().splitlines()]
    right_rows = [
        json.loads(x) for x in resumed_config.history_path.read_text().splitlines()
    ]
    assert [r["policy_loss"] for r in left_rows] == [
        r["policy_loss"] for r in right_rows
    ]


def test_a_resume_rebuilds_the_architecture_from_the_checkpoint(tmp_path):
    """Not from its caller. A caller that changed would change the experiment."""
    config = a_config(tmp_path, generations=1)
    run(config, lambda: ConvRotationNet(3, 3))

    # A caller asking for a different architecture must not get one.
    resumed = a_config(tmp_path, generations=2)
    run(resumed, lambda: FlipHexNet(3, 3))

    state = Checkpoint(resumed.root).load()
    assert state.meta["net_spec"]["class"] == "ConvRotationNet"
    assert "rotation_head.weight" in state.challenger
    assert state.challenger["rotation_head.weight"].shape == (6, 32, 1, 1)


def test_a_fresh_run_without_make_net_is_refused(tmp_path):
    with pytest.raises(ValueError, match="needs make_net"):
        run(a_config(tmp_path))


def test_a_checkpoint_without_a_net_spec_is_refused(tmp_path):
    """Guessing the architecture is how a resume becomes a different experiment."""
    config = a_config(tmp_path, generations=1)
    run(config, lambda: ConvRotationNet(3, 3))

    checkpoint = Checkpoint(config.root)
    state = checkpoint.load()
    state.meta.pop("net_spec")
    checkpoint.save(state)

    with pytest.raises(ValueError, match="no net_spec"):
        run(a_config(tmp_path, generations=2))


# -- the gate -----------------------------------------------------------------


def test_the_gate_runs_on_cadence_and_not_otherwise(tmp_path):
    rows = run(
        a_config(tmp_path, generations=4, gate_every=2), lambda: ConvRotationNet(3, 3)
    )
    assert [r["gated"] for r in rows] == [False, True, False, True]


def test_a_promoted_challenger_becomes_the_champion(tmp_path):
    config = a_config(tmp_path, generations=1, gate_threshold=0.0)
    rows = run(config, lambda: ConvRotationNet(3, 3))

    assert rows[0]["promoted"]
    state = Checkpoint(config.root).load()
    assert same(weights(state.champion), weights(state.challenger))


def test_a_refused_challenger_leaves_the_champion_alone(tmp_path):
    config = a_config(tmp_path, generations=1, gate_threshold=1.01)
    rows = run(config, lambda: ConvRotationNet(3, 3))

    assert not rows[0]["promoted"]
    state = Checkpoint(config.root).load()
    assert not same(weights(state.champion), weights(state.challenger))


def test_the_checkpoint_carries_the_gates_seat_split(tmp_path):
    """``run_gate`` needs all three counts to resume, and says so.

    A mid-gate checkpoint holding only the total restores the right win rate and
    a fabricated per-seat breakdown, which is worse than losing the match: the
    seat split is what distinguishes a seat effect from an average.
    """
    from az.checkpoint import TrainingState

    assert "gate_first_wins" in TrainingState.__dataclass_fields__

    config = a_config(tmp_path, generations=1)
    run(config, lambda: ConvRotationNet(3, 3))

    checkpoint = Checkpoint(config.root)
    state = checkpoint.load()
    state.gate_wins, state.gate_games, state.gate_first_wins = 7, 12, 4
    checkpoint.save(state)

    restored = checkpoint.load()
    assert (restored.gate_wins, restored.gate_games, restored.gate_first_wins) == (
        7,
        12,
        4,
    )


# -- configuration guards -----------------------------------------------------


def test_an_odd_gate_length_is_refused(tmp_path):
    with pytest.raises(ValueError, match="even so the seats balance"):
        a_config(tmp_path, gate_games=5)


def test_a_buffer_too_small_for_one_batch_is_refused(tmp_path):
    with pytest.raises(ValueError, match="not enough to start"):
        run(
            a_config(tmp_path, games=1, batch_size=4096),
            lambda: ConvRotationNet(3, 3),
        )


def test_the_resume_comparison_actually_discriminates(tmp_path):
    """Proves the test above is not vacuous.

    ``test_a_resumed_run_is_indistinguishable_from_an_uninterrupted_one``
    compares two runs of the same code, so any defect present in both cancels
    out and the test passes on a broken loop. Two probes confirmed that risk is
    real: removing ``restore_rng`` and pinning the self-play generation counter
    to zero both leave it green.

    What the comparison *is* sensitive to is the buffer's sampling RNG, which is
    the stream a resume must carry. This asserts that sensitivity, so the test
    above cannot silently stop proving anything.
    """
    straight = a_config(tmp_path / "a", generations=2)
    run(straight, lambda: ConvRotationNet(3, 3))
    whole = Checkpoint(straight.root).load()

    config = a_config(tmp_path / "b", generations=1)
    run(config, lambda: ConvRotationNet(3, 3))

    checkpoint = Checkpoint(config.root)
    state = checkpoint.load()
    state.buffer._rng.seed(999_999)  # the batch stream the resume must preserve
    checkpoint.save(state)
    run(a_config(tmp_path / "b", generations=2))

    corrupted = Checkpoint(config.root).load()
    assert not same(weights(corrupted.challenger), weights(whole.challenger)), (
        "corrupting the buffer's sampling RNG changed nothing, so the resume "
        "comparison is measuring neither the batches nor anything downstream "
        "of them"
    )


def test_the_rng_snapshot_is_insurance_and_the_loop_says_so(tmp_path):
    """Measured, not assumed: nothing in the loop reads the global streams.

    Every stochastic decision derives from an explicit seed, so the checkpoint's
    torch/python RNG state currently affects no output. It is kept because the
    first thing that uses a global generator would make it load-bearing and its
    absence would be invisible — and this pins the claim so a future change that
    *does* read a global stream is noticed here rather than in a 60-hour run.
    """
    import random

    config = a_config(tmp_path, generations=1)

    torch.manual_seed(12345)
    random.seed(12345)
    run(config, lambda: ConvRotationNet(3, 3))
    first = Checkpoint(config.root).load()

    import shutil

    shutil.rmtree(config.root)
    torch.manual_seed(999)
    random.seed(999)
    run(a_config(tmp_path, generations=1), lambda: ConvRotationNet(3, 3))
    second = Checkpoint(config.root).load()

    assert same(weights(first.challenger), weights(second.challenger)), (
        "the run's output depends on the ambient global RNG, so the loop is no "
        "longer fully seed-derived and the checkpoint's RNG snapshot has become "
        "load-bearing -- update az/loop.py's Resume section, which says it is not"
    )


# -- resuming from inside a gate ----------------------------------------------


def _mid_gate_state(config, **overrides):
    """A checkpoint written inside a gate, as the mid-gate path writes one."""
    checkpoint = Checkpoint(config.root)
    state = checkpoint.load()
    state.generation = 0
    state.last_gated = -1
    state.gate_games, state.gate_wins, state.gate_first_wins = 2, 1, 1
    state.meta = dict(state.meta) | {
        "pending_row": {
            "generation": 0,
            "samples": 40,
            "buffer": len(state.buffer),
            "refresh_fraction": 0.2,
            "policy_loss": 1.0,
            "value_loss": 1.0,
            "gated": False,
        }
    }
    for key, value in overrides.items():
        setattr(state, key, value)
    checkpoint.save(state)
    return state


def test_a_mid_gate_resume_does_not_replay_the_generation(tmp_path):
    """The defect EXP-014's C4 caught, at toy scale, on its first run.

    A checkpoint written inside a gate carries a generation whose self-play and
    training already happened — they are baked into the buffer and the
    challenger it stores. Replaying them extends the buffer with the same games
    twice and takes another `steps` gradient steps, so the resumed run is a
    different run rather than a continuation. Nothing raises; the weights simply
    diverge, which is invisible without a byte comparison against an
    uninterrupted run.
    """
    config = a_config(tmp_path, generations=1, gate_every=1)
    run(config, lambda: ConvRotationNet(3, 3))

    before = len(Checkpoint(config.root).load().buffer)
    _mid_gate_state(config)
    run(a_config(tmp_path, generations=1, gate_every=1))

    after = Checkpoint(config.root).load()
    assert len(after.buffer) == before, (
        "the resume replayed the generation's self-play: the buffer grew, so the "
        "same games are in it twice"
    )
    assert after.generation == 1


def test_a_mid_gate_checkpoint_without_its_pending_row_is_refused(tmp_path):
    """Without it the resumed run cannot write the history row it owes.

    Silently writing a generation with no samples or losses would leave a hole in
    the record exactly where a run was interrupted, which is the worst place for
    one.
    """
    config = a_config(tmp_path, generations=1, gate_every=1)
    run(config, lambda: ConvRotationNet(3, 3))

    checkpoint = Checkpoint(config.root)
    state = checkpoint.load()
    state.generation, state.last_gated = 0, -1
    state.gate_games, state.gate_wins, state.gate_first_wins = 2, 1, 1
    checkpoint.save(state)

    with pytest.raises(ValueError, match="no pending row"):
        run(a_config(tmp_path, generations=1, gate_every=1))


def test_a_gate_cadence_longer_than_the_match_is_refused(tmp_path):
    """Then no mid-gate checkpoint is ever written and a kill costs the match.

    With the loop's default cadence of 25 and EXP-014's 20-game gate, the path
    would never fire — which is invisible until something actually kills a run.
    """
    with pytest.raises(ValueError, match="gate_checkpoint_every must be in"):
        a_config(tmp_path, gate_games=20, gate_checkpoint_every=25)
