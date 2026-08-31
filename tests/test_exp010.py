"""Tests for EXP-010's instrument, ``scripts/exp010_mcts_dedup.py``.

The search itself is tested in ``test_az_mcts.py``. What is tested here is the
scaffolding that decides *what the run means* — and every one of these was a
red-team finding on the registration before the code existed:

- The falsifier is a **non-inferiority** test. "Worse by more than 2 points"
  requires the interval to exclude **-2**, not 0; the weaker reading fires an
  ADR amendment on a difference fully consistent with -0.2.
- Power is **reported from the realised discordance**, not assumed. The first
  registration declared a 2-point falsifier at a sample size whose floor was
  ~3.4 points, so the only branch that could change anything was invisible.
- Ground truth is **pinned by digest**. "5x3-h2" does not identify an artefact.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


exp010 = _load("exp010_mcts_dedup")


# -- the paired comparison ----------------------------------------------------


def test_mcnemar_is_signed_from_the_second_arm():
    """``mcnemar(a, b)`` reports ``b - a``, so B beating A is positive."""
    a = [True, True, False, False]
    b = [True, True, True, True]

    result = exp010.mcnemar(a, b)
    assert result["difference"] == pytest.approx(0.5)
    assert result["b_only"] == 2
    assert result["a_only"] == 0


def test_swapping_the_arms_flips_the_sign():
    a = [True, False, False, True, False]
    b = [False, True, True, True, False]

    forward = exp010.mcnemar(a, b)
    backward = exp010.mcnemar(b, a)
    assert forward["difference"] == pytest.approx(-backward["difference"])
    assert forward["discordant"] == backward["discordant"]


def test_perfect_agreement_has_no_discordance_and_does_not_divide_by_zero():
    same = [True, False, True, True]

    result = exp010.mcnemar(same, list(same))
    assert result["discordant"] == 0
    assert result["difference"] == 0.0
    assert result["ci_low"] == result["ci_high"] == 0.0
    assert result["below_minus_2_margin"] is False


# -- the falsifier is non-inferiority, not "excludes zero" --------------------


def test_a_difference_consistent_with_minus_zero_point_two_does_not_fire():
    """The exact defect the red-team named.

    A point estimate below -2 whose interval reaches past -2 is compatible with
    a trivial true difference. Under the wrong reading — "interval excludes
    zero" — this fires an ADR amendment.
    """
    n = 400
    # 30 discordant, leaning negative: point estimate ~-2.5 pts, wide interval.
    a = [True] * 16 + [False] * 14 + [True] * (n - 30)
    b = [False] * 16 + [True] * 14 + [True] * (n - 30)

    result = exp010.mcnemar(a, b)
    assert result["difference"] < -0.004
    assert result["ci_high"] > -0.02, "interval must reach past the margin"
    assert result["below_minus_2_margin"] is False


def test_a_clearly_worse_arm_does_fire():
    n = 3000
    a = [True] * 300 + [True] * (n - 300)
    b = [False] * 300 + [True] * (n - 300)

    result = exp010.mcnemar(a, b)
    assert result["difference"] == pytest.approx(-0.1)
    assert result["ci_high"] < -0.02
    assert result["below_minus_2_margin"] is True


# -- power is measured, not assumed -------------------------------------------


def test_detectable_difference_shrinks_with_sample_size():
    coarse = exp010.detectable_difference(0.15, 1_000)
    fine = exp010.detectable_difference(0.15, 3_000)

    assert fine < coarse
    assert 0.02 < coarse < 0.06, "1,000 paired positions should sit near 3.4 pts"
    assert fine < 0.025, "3,000 must resolve the registered 2-point margin"


def test_detectable_difference_is_defined_when_nothing_is_discordant():
    assert exp010.detectable_difference(0.0, 3_000) == 1.0
    assert exp010.detectable_difference(0.15, 0) == 1.0


# -- provenance ---------------------------------------------------------------


def test_ground_truth_must_match_the_pinned_digest(tmp_path):
    bad = tmp_path / "wrong-arm.json"
    bad.write_text(
        json.dumps(
            {
                "termination": "exhausted",
                "verification": {"V5_checksum_sha256": "deadbeef"},
            }
        )
    )

    with pytest.raises(SystemExit, match="digest mismatch"):
        exp010.verify_ground_truth(bad)


def test_an_unexhausted_solve_is_refused(tmp_path):
    """adr-004 R1: a truncated search may not ground an axis."""
    truncated = tmp_path / "truncated.json"
    truncated.write_text(
        json.dumps(
            {
                "termination": "budget",
                "verification": {"V5_checksum_sha256": exp010.EXPECTED_V5},
            }
        )
    )

    with pytest.raises(SystemExit, match="R1"):
        exp010.verify_ground_truth(truncated)


def test_the_real_artefact_passes_its_own_gate():
    path = ROOT / "data" / "subgame-solutions" / "5x3-h2.json"
    if not path.exists():
        pytest.skip("solved database not present")

    artefact = exp010.verify_ground_truth(path)
    assert artefact["value"] == "P1"


# -- the aliasing diagnostic --------------------------------------------------


def test_aliased_mass_matches_the_measured_root_collapse():
    """1,450 actions over 325 positions leaves 1,125 labels beyond the first."""
    from fliphex.moves import legal_moves
    from fliphex.variant import Arm, Variant

    variant = Variant(5, 5, Arm("h1"))
    board, state = variant.board(), variant.initial_state()
    moves = legal_moves(board, state)

    mass = exp010.aliased_mass(board, state, moves)
    assert mass == pytest.approx((1450 - 325) / 1450)
    assert 0.60 < mass < 0.80, "the pre-registered 5x5-root band"


def test_the_registered_constants_are_what_the_registry_says():
    """A silent edit to a default is a silent change to the experiment."""
    assert exp010.SEED == 17
    assert tuple(range(5, 15)) == exp010.LAYERS
    assert exp010.PER_LAYER == 300
    assert exp010.BUDGETS == (100, 400, 1600)
    assert exp010.PRIMARY_BUDGET == 400
    assert exp010.EXPECTED_V5.startswith("51192b4d403ac1cb")
