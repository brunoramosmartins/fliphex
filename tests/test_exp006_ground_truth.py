"""Tests for EXP-006's ground-truth generator, ``scripts/exp006_ground_truth.py``.

The run is hours of exact search on the shipped 5×5 and cannot be a fixture.
What is tested here is everything that decides whether those hours produce a
usable artefact, and each of these pins a way the run could quietly go wrong:

- **The orphan predicate is a closed form standing in for an enumeration.** The
  registration replaces a forward reachability sweep — infeasible at 5.017e16
  configurations — with an ``O(N)`` test on a single position. It is checked
  here against ``legal_moves``/``apply_move`` on a board small enough to
  enumerate, which is the only thing that makes the substitution evidence.
- **Resume must re-derive the same positions.** The sampling streams are the
  artefact's provenance; a resume that draws different positions produces a
  sample nobody registered.
- **Excluded positions must never be replaced.** Redrawing until a position
  proves in budget selects the sample on how hard it was to solve.
- **The calibration's check must be able to fail.** It verifies the 2026-09-16
  amendment's central claim — that every move preserves a loss — and a check
  that cannot fail verifies nothing.
- **Children are deduplicated by position.** Risk R13 measured 4.46× root
  aliasing; counting one position several times would inflate the random-move
  baseline the headline rate is quoted against.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from fliphex.moves import apply_move, legal_moves
from fliphex.variant import Arm, Variant
from solver.retrograde import LayerIndex

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


exp006 = _load("exp006_ground_truth")

#: Boards where every layer can be enumerated in test time.
SMALL = [Variant(5, 1), Variant(5, 1, Arm.H2)]


# -- the registration, restated so a drift in either direction fails ----------


def test_the_strata_match_what_was_registered():
    assert exp006.REGISTERED.seed == 2
    assert exp006.REGISTERED.counts == {6: 166, 7: 167, 8: 167}
    assert sum(exp006.REGISTERED.counts.values()) == 500

    assert exp006.LAYER_UNIFORM.seed == 4
    assert exp006.LAYER_UNIFORM.counts == {6: 84, 7: 83, 8: 83}
    assert sum(exp006.LAYER_UNIFORM.counts.values()) == 250


def test_the_calibration_subsample_is_the_pre_declared_hundred():
    assert sum(exp006.CALIBRATION.values()) == 100
    # Drawn from the registered stratum only; stratum B is descriptive.
    assert set(exp006.CALIBRATION) <= set(exp006.REGISTERED.counts)


# -- the orphan predicate -----------------------------------------------------


@pytest.mark.parametrize("variant", SMALL)
def test_the_orphan_predicate_agrees_with_enumerated_reachability(variant):
    """The closed form, checked against actually generating the moves.

    This is the substitution the registration makes: on the 5×5 no enumeration
    is possible, so the ``O(N)`` characterisation stands alone. Here both are
    affordable and must agree on **every** configuration of the layer, not on a
    sample.
    """
    board = variant.board()
    for t in range(1, variant.n_cells + 1):
        below, above = LayerIndex(variant, t - 1), LayerIndex(variant, t)
        reachable = set()
        for index in range(below.size):
            state = below.decode(index)
            for move in legal_moves(board, state):
                reachable.add(above.encode(apply_move(board, state, move)))

        for index in range(above.size):
            predicted = exp006.is_orphan(above.decode(index))
            assert predicted == (index not in reachable), f"t={t} index={index}"


@pytest.mark.parametrize("variant", SMALL)
def test_the_orphan_rate_is_the_two_to_the_minus_t_identity(variant):
    """EXP-005's identity, re-derived through this predicate rather than quoted."""
    for t in range(1, variant.n_cells + 1):
        index = LayerIndex(variant, t)
        orphans = sum(1 for i in range(index.size) if exp006.is_orphan(index.decode(i)))
        assert orphans * 2**t == index.size, f"t={t}"


def test_a_position_just_played_into_is_never_an_orphan():
    """The last-placed cell shows its placer's colour, by the flip rule."""
    variant = Variant(5, 1)
    board = variant.board()
    state = variant.initial_state()
    for _ in range(4):
        state = apply_move(board, state, legal_moves(board, state)[0])
        assert not exp006.is_orphan(state)


# -- state round-trip ---------------------------------------------------------


def test_a_stored_position_reloads_identically():
    """The agreement measurement reads these records; a lossy encode is fatal."""
    variant = exp006.VARIANT
    board = variant.board()
    state = variant.initial_state()
    for _ in range(6):
        state = apply_move(board, state, legal_moves(board, state)[0])

    reloaded = exp006.decode_state(json.loads(json.dumps(exp006.encode_state(state))))

    assert reloaded.colours == state.colours
    assert reloaded.hands == state.hands
    assert reloaded.to_move == state.to_move
    assert reloaded.ply() == state.ply()
    # History is metadata and is deliberately not stored; ply() counts cells.
    assert legal_moves(board, reloaded) == legal_moves(board, state)


# -- resume -------------------------------------------------------------------


def _toy(monkeypatch, counts, calibration):
    registered = exp006.Stratum("registered", 2, counts, "playout", "toy")
    monkeypatch.setattr(exp006, "REGISTERED", registered)
    monkeypatch.setattr(exp006, "STRATA", {"registered": registered})
    monkeypatch.setattr(exp006, "CALIBRATION", calibration)
    return registered


def test_resume_redraws_exactly_the_positions_it_had(tmp_path, monkeypatch):
    stratum = _toy(monkeypatch, {3: 5}, {})
    board = exp006.VARIANT.board()
    work = tmp_path / "work.jsonl"

    exp006.generate(stratum, work, board, [])
    complete = exp006.read_work(work)

    # Simulate a kill: keep the first two rows only.
    work.write_text("".join(json.dumps(r) + "\n" for r in complete[:2]))
    exp006.generate(stratum, work, board, exp006.read_work(work))
    resumed = exp006.read_work(work)

    assert len(resumed) == len(complete) == 5
    for before, after in zip(complete, resumed, strict=True):
        assert before["colours"] == after["colours"]
        assert before["value"] == after["value"]
        assert before["index"] == after["index"]


def test_a_finished_stratum_solves_nothing_on_a_rerun(tmp_path, monkeypatch):
    stratum = _toy(monkeypatch, {3: 3}, {})
    board = exp006.VARIANT.board()
    work = tmp_path / "work.jsonl"

    exp006.generate(stratum, work, board, [])
    first = work.read_text()
    exp006.generate(stratum, work, board, exp006.read_work(work))

    assert work.read_text() == first


def test_a_truncated_final_line_is_reported_rather_than_discarded(tmp_path):
    """These rows cost hours; the script must not decide to drop one."""
    work = tmp_path / "work.jsonl"
    work.write_text('{"stratum": "registered", "k": 3}\n{"stratum": "reg')

    with pytest.raises(SystemExit, match="cost hours"):
        exp006.read_work(work)


# -- exclusions ---------------------------------------------------------------


def test_a_position_over_budget_is_recorded_not_replaced(tmp_path, monkeypatch):
    """Redrawing until it proves would select the sample on solving difficulty."""
    stratum = _toy(monkeypatch, {6: 3}, {})
    monkeypatch.setattr(exp006, "MAX_NODES", 1)
    board = exp006.VARIANT.board()
    work = tmp_path / "work.jsonl"

    exp006.generate(stratum, work, board, [])
    rows = exp006.read_work(work)

    assert len(rows) == 3
    assert all(not r["proved"] for r in rows)
    assert all(r["termination"] == "budget" for r in rows)
    assert all("value" not in r for r in rows)

    artefact = exp006.assemble(rows, tmp_path / "out.json")
    summary = artefact["summary"]["registered"]["6"]
    assert summary["excluded_at_budget"] == 3
    assert summary["proved"] == 0
    assert summary["decision_denominator"] == 0


# -- the calibration sweep ----------------------------------------------------


def test_the_sweep_deduplicates_children_by_position(tmp_path, monkeypatch):
    """R13: aliased actions reach one position and must be counted once."""
    stratum = _toy(monkeypatch, {3: 2}, {3: 2})
    board = exp006.VARIANT.board()
    work = tmp_path / "work.jsonl"

    exp006.generate(stratum, work, board, [])
    rows = [r for r in exp006.read_work(work) if "sweep" in r]

    assert rows, "the calibration subsample produced no sweep"
    for row in rows:
        sweep = row["sweep"]
        assert 0 < sweep["distinct_children"] <= sweep["legal_moves"]
        assert sweep["opponent_wins"] <= sweep["distinct_children"]


def test_every_move_preserves_a_loss_and_the_check_can_fail():
    """The 2026-09-16 amendment's central claim, and its detector.

    A lost position where some child is *not* a win for the opponent would mean
    the mover had a move out of a lost position, which cannot happen — so the
    check exists to catch an instrument fault, and it is only worth having if a
    fault would trip it.
    """
    honest = [
        {
            "stratum": "registered",
            "k": 6,
            "index": 0,
            "proved": True,
            "value": "LOSS",
            "sweep": {
                "legal_moves": 10,
                "distinct_children": 8,
                "opponent_wins": 8,
                "seconds": 1.0,
            },
        }
    ]
    assert exp006.calibration(honest)["lost_positions_all_moves_preserve"]

    broken = json.loads(json.dumps(honest))
    broken[0]["sweep"]["opponent_wins"] = 7

    result = exp006.calibration(broken)
    assert not result["lost_positions_all_moves_preserve"]
    assert result["violations"]


def test_the_random_move_baseline_is_reported_on_won_positions():
    """The headline rate may never be quoted without the floor it sits on."""
    rows = [
        {
            "stratum": "registered",
            "k": 6,
            "index": i,
            "proved": True,
            "value": "WIN",
            "sweep": {
                "legal_moves": 10,
                "distinct_children": 10,
                "opponent_wins": 9,
                "seconds": 1.0,
            },
        }
        for i in range(3)
    ]

    result = exp006.calibration(rows)

    assert result["median_losing_move_share"] == pytest.approx(0.9)
    assert result["random_move_agreement_on_won"] == pytest.approx(0.1)
    assert result["won_but_no_losing_move"] == 0


def test_a_won_position_with_no_losing_move_is_counted_as_vacuous():
    rows = [
        {
            "stratum": "registered",
            "k": 6,
            "index": 0,
            "proved": True,
            "value": "WIN",
            "sweep": {
                "legal_moves": 4,
                "distinct_children": 4,
                "opponent_wins": 0,
                "seconds": 1.0,
            },
        }
    ]

    assert exp006.calibration(rows)["won_but_no_losing_move"] == 1


# -- the artefact -------------------------------------------------------------


def test_the_artefact_carries_the_adr_004_r3_header(tmp_path, monkeypatch):
    """H3's comparison set is defined by *filtering* on these two fields."""
    stratum = _toy(monkeypatch, {3: 2}, {})
    board = exp006.VARIANT.board()
    work = tmp_path / "work.jsonl"
    exp006.generate(stratum, work, board, [])

    artefact = exp006.assemble(exp006.read_work(work), tmp_path / "out.json")

    assert artefact["ordering"] == "internal"
    assert artefact["termination"] == "exhausted"
    assert artefact["variant"] == "5x5-h1"
    assert artefact["max_nodes"] == exp006.MAX_NODES


def test_the_denominator_counts_won_positions_only(tmp_path, monkeypatch):
    stratum = _toy(monkeypatch, {3: 6}, {})
    board = exp006.VARIANT.board()
    work = tmp_path / "work.jsonl"
    exp006.generate(stratum, work, board, [])
    rows = exp006.read_work(work)

    artefact = exp006.assemble(rows, tmp_path / "out.json")
    summary = artefact["summary"]["registered"]["3"]

    wins = sum(1 for r in rows if r["proved"] and r["value"] == "WIN")
    assert summary["decision_denominator"] == wins
    assert summary["mover_wins"] + summary["mover_loses"] == summary["proved"]


def test_the_registered_stratum_runs_first():
    """Alphabetical order would put the descriptive stratum ahead of the primary.

    An interruption is the normal case here, not the exception — the run spans
    hours and the machine hibernates — so a run stopped partway must hold the
    stratum the decision rule reads, not the one that only describes.
    """
    assert exp006.DEFAULT_ORDER[0] == "registered"
    assert set(exp006.DEFAULT_ORDER) == set(exp006.STRATA)
