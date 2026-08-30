"""Tests for the V4/V6 coverage reporting added on 2026-08-27.

The registry amendment of 2026-08-09 recorded that both gates return a verdict
without saying how much of their own sample produced it, and called it "the V3
lesson recurring". These tests pin the three things that revision has to get
right.

**Nothing may be dropped in silence.** V4 used to skip terminal samples with a
bare ``continue``, so 40 of h2's 601 draws vanished from every counter and the
artefact's own numbers did not add up to its own sample size. A gate that
discards evidence must at minimum leave a countable trace.

**The RNG stream must not move.** Coverage reporting is accounting, not a new
sampling rule. The h1 arm is about to be re-run against h2's archived numbers,
and a changed draw sequence would silently destroy that comparison — so the
draws are pinned here against values computed before the revision.

**The replay must be the instrument.** ``exp002_coverage_replay`` recovers a
finished arm's coverage by driving the real observer over stored layers. If it
ever drifts into being a second implementation of the sampling rule, this stops
being an audit.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

from fliphex.variant import Arm, Variant
from solver.checkpoint import Checkpoint
from solver.packed_sweep import PackedSweep
from solver.retrograde import SLOT_LOSS, SLOT_WIN

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


exp002 = _load("exp002_solve_5x3")
replay_tool = _load("exp002_coverage_replay")

#: The 5×1 is five cells and hands 3 + 2 — a real sweep with a real mirror,
#: fast enough to run inside a test.
TINY = Variant(5, 1, Arm("h2"))


@pytest.fixture(scope="module")
def swept(tmp_path_factory):
    """Sweep the 5×1 once, keeping its layers, and return the observer."""
    root = tmp_path_factory.mktemp("coverage")
    checks = exp002.Checks(TINY, 40, 40, seed=3, progress=False)
    ckpt = Checkpoint(root / TINY.name)
    PackedSweep(TINY, TINY.board(), 2).sweep(observer=checks, checkpoint=ckpt)
    return checks, ckpt


# -- V4: the silent drop -----------------------------------------------------


def test_terminal_samples_are_verified_not_discarded(swept):
    """The bug this revision exists for.

    Terminal draws left no trace at all, so ``agreed + unaffordable`` came up
    short of the sample size with nothing to say why.
    """
    checks, _ = swept
    v4 = exp002.run_v4(TINY, checks, budget=2_000_000)

    assert v4["terminal_agreed"] > 0, "terminal draws produced no evidence"
    assert v4["terminal_disagreed"] == 0


def test_every_drawn_sample_lands_in_exactly_one_bucket(swept):
    """The arithmetic the old artefact could not do."""
    checks, _ = swept
    v4 = exp002.run_v4(TINY, checks, budget=2_000_000)

    accounted = (
        v4["agreed"]
        + v4["disagreed"]
        + v4["unaffordable"]
        + v4["terminal_agreed"]
        + v4["terminal_disagreed"]
    )
    assert accounted == v4["coverage"]["samples_drawn"] == len(checks.v4_samples)


def test_terminal_rederivation_uses_an_independent_path(swept):
    """It re-derives through ``rules.winner``, not through the sweep's counter.

    ``PackedSweep`` decides a terminal layer by counting set bits in a packed
    integer and taking the mover from layer parity. This asserts the other path
    — decode a ``GameState``, count its colours — agrees, which is what makes
    the terminal check evidence rather than a tautology.
    """
    from fliphex.rules import winner
    from solver.retrograde import LayerIndex

    checks, _ = swept
    index = LayerIndex(TINY, TINY.n_cells)
    terminal = [s for s in checks.v4_samples if s[0] == TINY.n_cells]
    assert terminal, "the fixture drew no terminal samples"

    for _t, i, slot in terminal:
        state = index.decode(i)
        expected = SLOT_WIN if winner(state) == state.to_move else SLOT_LOSS
        assert slot == expected


def test_coverage_names_the_layers_that_produced_no_evidence(swept):
    checks, _ = swept
    cov = exp002.run_v4(TINY, checks, budget=2_000_000)["coverage"]

    assert cov["shallowest_layer_searched"] is not None
    assert set(cov["layers_searched"]).isdisjoint(cov["layers_without_evidence"])
    assert 0.0 < cov["verified_fraction"] <= 1.0


def test_a_budget_of_one_node_reports_zero_coverage_not_a_pass(swept):
    """The failure mode the amendment described: silence read as agreement."""
    checks, _ = swept
    v4 = exp002.run_v4(TINY, checks, budget=1)

    assert v4["agreed"] == 0
    assert v4["passed"] is False
    assert v4["coverage"]["shallowest_layer_searched"] is None
    assert v4["coverage"]["layers_searched"] == []


# -- V6: eligibility and vacuous pairs ---------------------------------------


def test_mirror_fixed_pairs_are_counted_apart(swept):
    """A configuration fixed by the reflection is compared with itself."""
    checks, _ = swept
    v6 = exp002.v6_coverage(checks, TINY)

    assert v6["self_mirror"] > 0, "the 5x1 fixture should produce vacuous pairs"
    assert v6["non_trivial"] == v6["pairs_checked"] - v6["self_mirror"]
    assert v6["non_trivial"] < v6["pairs_checked"]


def test_v6_reports_where_it_had_no_coverage(swept):
    """adr-008 confines the mirror to the endgame; the gate must say so."""
    checks, _ = swept
    v6 = exp002.v6_coverage(checks, TINY)

    assert 0 in v6["layers_without_coverage"], "layer 0 still holds both P3-y"
    assert 0.0 < v6["eligible_fraction"] < 1.0


# -- the draw sequence is frozen ---------------------------------------------


def test_the_rng_stream_did_not_move(swept):
    """Pinned against the pre-revision instrument.

    Recorded by running the 5×1-h2 arm before coverage reporting was added. If
    this fails, the h1 re-run can no longer be compared against h2's archived
    V4/V6 numbers, which is a far worse loss than any coverage figure is a gain.
    """
    checks, _ = swept

    assert len(checks.v4_samples) == 183
    assert checks.v6_checked == 160
    assert checks.v6_rejected == 1904


def test_counting_vacuous_pairs_did_not_change_how_many_were_drawn(swept):
    """Excluding them would mean drawing replacements. That is why they stay in."""
    checks, _ = swept
    v6 = exp002.v6_coverage(checks, TINY)

    assert v6["pairs_checked"] == checks.v6_checked
    assert sum(r["attempts"] for r in checks.v6_rows.values()) == v6["attempts"]


# -- the replay is the instrument, not a copy of it ---------------------------


def test_replay_reproduces_the_arm_exactly(swept, tmp_path):
    """Same digest, same draws, same verdicts — from the stored layers alone.

    The V5 checksum is the load-bearing assertion: it is a hash of every layer
    fed in sweep order, so it fails if the replay visits the layers in the wrong
    order — which is also the order the RNG stream depends on.
    """
    checks, ckpt = swept

    args = replay_tool.argparse.Namespace(
        board=[5, 1],
        arm="h2",
        checkpoint=ckpt.root.parent,
        seed=3,
        v4_per_layer=40,
        v6_per_layer=40,
        v4_budget=0,
        out=tmp_path,
        no_write=True,
    )
    artefact = replay_tool.replay(TINY, args)

    assert artefact["v5_checksum_sha256"] == checks.digest.hexdigest()
    assert artefact["v4_samples_drawn"] == len(checks.v4_samples)
    assert artefact["V6_coverage"]["pairs_checked"] == checks.v6_checked
    assert (
        artefact["V6_coverage"]["self_mirror"]
        == (exp002.v6_coverage(checks, TINY)["self_mirror"])
    )


def test_replay_skips_the_searches_by_default(swept, tmp_path):
    """``--v4-budget 0`` recovers only what needs no search — 20 h saved."""
    _checks, ckpt = swept
    args = replay_tool.argparse.Namespace(
        board=[5, 1],
        arm="h2",
        checkpoint=ckpt.root.parent,
        seed=3,
        v4_per_layer=40,
        v6_per_layer=40,
        v4_budget=0,
        out=tmp_path,
        no_write=True,
    )

    assert replay_tool.replay(TINY, args)["V4_sampled_rederivation"] is None


# -- checkpoint compatibility -------------------------------------------------


def test_an_old_checkpoint_resumes_and_says_its_rows_are_partial():
    """A checkpoint written before this revision has no per-layer V6 rows.

    h2's 4.1 GB checkpoint is one of those. Resuming from it must not present
    the missing breakdown as a row of zeroes.
    """
    checks = exp002.Checks(TINY, 40, 40, seed=3, progress=False)
    legacy = {
        "rng": list(checks.rng.getstate()[:1])
        + [list(checks.rng.getstate()[1]), checks.rng.getstate()[2]],
        "layer_counts": {},
        "v1_problems": [],
        "v4_samples": [],
        "v6_checked": 7,
        "v6_rejected": 3,
        "v6_problems": [],
    }

    class _OneLayer:
        def replay(self):
            yield TINY.n_cells, bytearray(8)

    checks.restore_checkpoint(legacy, _OneLayer())

    assert checks.v6_checked == 7
    assert checks.v6_rows == {}
    assert checks.v6_rows_partial is True
