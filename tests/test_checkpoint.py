"""Crash resume must be indistinguishable from never having crashed.

The property under test is not "resume runs" — it is that a sweep interrupted at
an arbitrary layer and resumed produces the **same value and the same adr-010 V5
checksum** as an uninterrupted one. A resume that quietly re-seeds the sampling
or restarts the digest would still print a plausible answer, which is the failure
mode adr-010 exists to catch.

Board choice follows ``test_packed_sweep.py``: the 5×1 (5 cells, six layers) is
the affordable one. The 3×3 is 711,963 configurations and ~17 s per sweep under
CPython — EXP-001's job, not a unit test's, and this file needs ~20 sweeps.
"""

from __future__ import annotations

import hashlib
from random import Random

import pytest

from fliphex.variant import Variant
from solver.checkpoint import Checkpoint
from solver.packed_sweep import PackedSweep

#: Six layers, t = 5 down to 0, so there are interior layers to die on.
BOARD = Variant(5, 1)


class Recorder:
    """A stand-in for EXP-002's ``Checks``: carries a digest and an RNG."""

    def __init__(self, seed: int = 3) -> None:
        self.rng = Random(seed)
        self.digest = hashlib.sha256()
        self.layers: list[int] = []
        self.draws: list[int] = []

    def __call__(self, t, values, sweep) -> None:
        self.digest.update(bytes(values))
        self.layers.append(t)
        self.draws.append(self.rng.randrange(1_000_000))

    def checkpoint_state(self) -> dict:
        version, internal, gauss = self.rng.getstate()
        return {
            "rng": [version, list(internal), gauss],
            "layers": list(self.layers),
            "draws": list(self.draws),
        }

    def restore_checkpoint(self, state, checkpoint) -> None:
        version, internal, gauss = state["rng"]
        self.rng.setstate((version, tuple(internal), gauss))
        self.layers = list(state["layers"])
        self.draws = list(state["draws"])
        self.digest = hashlib.sha256()
        for _t, values in checkpoint.replay():
            self.digest.update(bytes(values))


class Interrupted(Exception):
    """Raised by the observer to simulate the machine dying mid-sweep."""


class Killer(Recorder):
    def __init__(self, die_at: int, seed: int = 3) -> None:
        super().__init__(seed)
        self.die_at = die_at

    def __call__(self, t, values, sweep) -> None:
        super().__call__(t, values, sweep)
        if t == self.die_at:
            raise Interrupted


def _sweep(observer=None, checkpoint=None):
    return PackedSweep(BOARD, BOARD.board(), 2).sweep(
        observer=observer, checkpoint=checkpoint
    )


def _crash_then_resume(tmp_path, die_at: int) -> tuple[Checkpoint, Recorder]:
    """Kill a sweep at ``die_at``, then resume it. Returns the resumed observer."""
    ckpt = Checkpoint(tmp_path / "run")
    with pytest.raises(Interrupted):
        _sweep(observer=Killer(die_at=die_at), checkpoint=ckpt)
    resumed = Recorder()
    _sweep(observer=resumed, checkpoint=ckpt)
    return ckpt, resumed


@pytest.fixture(scope="module")
def clean() -> Recorder:
    """One uninterrupted run, reused as the reference by every test here."""
    observer = Recorder()
    _sweep(observer=observer)
    return observer


@pytest.fixture(scope="module")
def clean_value():
    return _sweep().value


def test_a_resumed_sweep_returns_the_same_value(clean_value, tmp_path):
    ckpt = Checkpoint(tmp_path / "run")
    with pytest.raises(Interrupted):
        _sweep(observer=Killer(die_at=3), checkpoint=ckpt)

    # The layer is saved *after* the observer returns, so a layer whose observer
    # raised is deliberately not a resume point: its evidence is half-collected.
    assert ckpt.resume_point() == 4

    assert _sweep(observer=Recorder(), checkpoint=ckpt).value == clean_value


def test_a_resumed_sweep_reproduces_the_v5_checksum_exactly(clean, tmp_path):
    """The point of retaining every layer. A per-layer digest would fail this."""
    _, resumed = _crash_then_resume(tmp_path, die_at=3)

    assert resumed.digest.hexdigest() == clean.digest.hexdigest()
    assert resumed.layers == clean.layers


def test_a_resumed_sweep_draws_the_same_samples(clean, tmp_path):
    """The RNG state must travel, or V4/V6 evidence stops being seed-pinned."""
    _, resumed = _crash_then_resume(tmp_path, die_at=2)

    assert resumed.draws == clean.draws


@pytest.mark.parametrize("die_at", [4, 3, 2, 1])
def test_resume_works_from_any_layer(clean, clean_value, die_at, tmp_path):
    _, resumed = _crash_then_resume(tmp_path, die_at=die_at)

    assert resumed.digest.hexdigest() == clean.digest.hexdigest()
    assert resumed.draws == clean.draws


def test_a_half_written_layer_is_never_resumed_from(tmp_path):
    """The manifest is written after the layer, so a torn write is invisible."""
    ckpt = Checkpoint(tmp_path / "run")
    with pytest.raises(Interrupted):
        _sweep(observer=Killer(die_at=3), checkpoint=ckpt)

    # Simulate a crash between the layer write and the manifest write: layer 3
    # exists on disk but no manifest ever named it.
    ckpt.layer_path(3).write_bytes(b"\x00" * 16)

    assert ckpt.resume_point() == 4, "an unnamed layer must not be resumed from"


def test_a_manifest_naming_a_missing_layer_refuses_to_resume(tmp_path):
    ckpt = Checkpoint(tmp_path / "run")
    with pytest.raises(Interrupted):
        _sweep(observer=Killer(die_at=3), checkpoint=ckpt)

    ckpt.layer_path(4).unlink()
    ckpt.load_manifest()
    with pytest.raises(FileNotFoundError, match="must not be resumed"):
        ckpt.load_layer(4)


def test_an_uninterrupted_sweep_with_a_checkpoint_matches_one_without(clean, tmp_path):
    """Checkpointing is I/O only — it must not perturb the sweep at all."""
    saved = Recorder()
    _sweep(observer=saved, checkpoint=Checkpoint(tmp_path / "run"))

    assert saved.digest.hexdigest() == clean.digest.hexdigest()
    assert saved.draws == clean.draws


def test_resuming_twice_still_reproduces_the_checksum(clean, tmp_path):
    """Two power cuts in one run. The digest is rebuilt from disk each time."""
    ckpt = Checkpoint(tmp_path / "run")
    with pytest.raises(Interrupted):
        _sweep(observer=Killer(die_at=4), checkpoint=ckpt)
    with pytest.raises(Interrupted):
        _sweep(observer=Killer(die_at=2), checkpoint=ckpt)

    resumed = Recorder()
    _sweep(observer=resumed, checkpoint=ckpt)

    assert resumed.digest.hexdigest() == clean.digest.hexdigest()
    assert resumed.draws == clean.draws
