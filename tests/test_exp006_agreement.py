"""Tests for EXP-006's agreement instrument, ``scripts/exp006_agreement.py``.

The measurement is cheap to run and expensive to get subtly wrong, because every
way of getting it wrong makes the learner look better:

- **Agreement is value preservation, never move identity.** A won position
  usually has several winning moves. Scoring identity with the solver's move
  would measure imitation of one arbitrary principal variation and would report
  a *lower* rate for correct play — the error is not symmetric, so it is pinned.
- **The denominator is won positions.** Lost and unproved positions must never
  enter it; from a lost position every move preserves the value, which is the
  defect the 2026-09-16 amendment exists to fix.
- **adr-004 R1 filters before anything is computed.** A ground truth that is not
  exhausted, or not internally ordered, may not ground an axis.
- **A failing seed is recorded, not averaged.** The rule is per seed, for the
  reason EXP-015 measured: five champions of one pipeline are not
  interchangeable.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from fliphex.moves import apply_move, legal_moves
from fliphex.variant import Variant
from solver.minimax import WIN, Solver
from solver.transposition import TranspositionTable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


exp006 = _load("exp006_agreement")


# -- the registered constants -------------------------------------------------


def test_the_rule_matches_what_was_registered():
    assert exp006.THRESHOLD == 0.90
    assert exp006.SIMULATIONS == 400
    assert exp006.SEEDS == (1, 2, 3, 4, 5)
    assert exp006.DECISION_ARM == "search"
    assert exp006.DECISION_STRATUM == "registered"


# -- the R1 filter ------------------------------------------------------------


def _truth(**overrides) -> dict:
    base = {
        "experiment": "EXP-006",
        "ordering": "internal",
        "termination": "exhausted",
        "variant": "5x5-h1",
        "calibration": {"random_move_agreement_on_won": 0.219},
        "positions": [],
    }
    return base | overrides


def test_a_budget_terminated_ground_truth_is_refused(tmp_path):
    path = tmp_path / "truth.json"
    path.write_text(json.dumps(_truth(termination="budget")))

    with pytest.raises(SystemExit, match="not 'exhausted'"):
        exp006.load_ground_truth(path)


def test_an_externally_ordered_ground_truth_is_refused(tmp_path):
    path = tmp_path / "truth.json"
    path.write_text(json.dumps(_truth(ordering="az-seeded")))

    with pytest.raises(SystemExit, match="adr-004 R2"):
        exp006.load_ground_truth(path)


def test_a_foreign_artefact_is_refused(tmp_path):
    path = tmp_path / "truth.json"
    path.write_text(json.dumps(_truth(experiment="EXP-003")))

    with pytest.raises(SystemExit, match="not an EXP-006 artefact"):
        exp006.load_ground_truth(path)


# -- the denominator ----------------------------------------------------------


def test_the_denominator_holds_won_positions_only():
    truth = _truth(
        positions=[
            {
                "stratum": "registered",
                "k": 6,
                "index": 0,
                "proved": True,
                "value": "WIN",
            },
            {
                "stratum": "registered",
                "k": 6,
                "index": 1,
                "proved": True,
                "value": "LOSS",
            },
            {"stratum": "registered", "k": 7, "index": 0, "proved": False},
            {
                "stratum": "layer_uniform",
                "k": 8,
                "index": 0,
                "proved": True,
                "value": "WIN",
            },
        ]
    )

    rows = exp006.denominator(truth)

    assert [(r["stratum"], r["k"], r["index"]) for r in rows] == [
        ("layer_uniform", 8, 0),
        ("registered", 6, 0),
    ]


def test_the_denominator_order_is_stable():
    """Ordinals seed the searches; a reshuffle would change what was measured."""
    positions = [
        {"stratum": "registered", "k": k, "index": i, "proved": True, "value": "WIN"}
        for k in (8, 6, 7)
        for i in (2, 0, 1)
    ]

    first = exp006.denominator(_truth(positions=positions))
    second = exp006.denominator(_truth(positions=list(reversed(positions))))

    assert [(r["k"], r["index"]) for r in first] == [
        (r["k"], r["index"]) for r in second
    ]


# -- agreement is value preservation ------------------------------------------


def _won_position(variant):
    """A reachable position the mover wins, with at least one losing move."""
    board = variant.board()
    state = variant.initial_state()
    while True:
        moves = legal_moves(board, state)
        table = TranspositionTable(1 << 16)
        if Solver(board, tt=table).solve(state).value == WIN:
            children = {}
            for move in moves:
                child = apply_move(board, state, move)
                children[move] = Solver(board, tt=table).solve(child).value
            if any(v == WIN for v in children.values()) and any(
                v != WIN for v in children.values()
            ):
                return board, state, children
        state = apply_move(board, state, moves[0])
        if state.is_terminal():  # pragma: no cover - the 5x1 always finds one
            raise AssertionError("no discriminating position on this board")


def test_a_winning_move_agrees_and_a_losing_move_does_not():
    board, state, children = _won_position(Variant(5, 1))
    keeps = next(m for m, v in children.items() if v != WIN)
    throws = next(m for m, v in children.items() if v == WIN)

    assert exp006.preserves(board, state, keeps, {})["agrees"] is True
    assert exp006.preserves(board, state, throws, {})["agrees"] is False


def test_every_winning_move_agrees_not_just_one():
    """The measure must not privilege a single principal variation.

    If agreement were scored by identity with the solver's move, at most one of
    these would count — and the instrument would report correct play as an
    error.
    """
    board, state, children = _won_position(Variant(5, 1))
    keeping = [m for m, v in children.items() if v != WIN]

    assert len(keeping) >= 1
    assert all(exp006.preserves(board, state, m, {})["agrees"] for m in keeping)


def test_the_child_cache_answers_identically():
    board, state, children = _won_position(Variant(5, 1))
    move = next(iter(children))
    cache: dict = {}

    cold = exp006.preserves(board, state, move, cache)
    warm = exp006.preserves(board, state, move, cache)

    assert cold["agrees"] == warm["agrees"]
    assert cache, "nothing was cached, so every champion re-solves every child"


# -- rates and the rule -------------------------------------------------------


def _rows(seed: int, arm: str, stratum: str, hits: int, misses: int) -> list[dict]:
    rows = []
    for i in range(hits + misses):
        rows.append(
            {
                "seed": seed,
                "arm": arm,
                "ordinal": i,
                "stratum": stratum,
                "k": 6,
                "index": i,
                "move": "m",
                "proved": True,
                "agrees": i < hits,
            }
        )
    return rows


def test_the_rule_reads_the_lower_bound_not_the_point_estimate():
    """92% of 100 has a lower bound of 84.8% and does not clear 90%."""
    result = exp006.rate(_rows(1, "search", "registered", 92, 8))

    assert result["rate"] == pytest.approx(0.92)
    assert result["ci"][0] < exp006.THRESHOLD
    assert not result["clears"]


def test_a_rate_clears_only_when_the_whole_interval_is_above_the_threshold():
    clears = exp006.rate(_rows(1, "search", "registered", 486, 14))  # 97.2% of 500

    assert clears["clears"]
    assert clears["ci"][0] > exp006.THRESHOLD


def test_unscored_positions_are_reported_and_leave_the_denominator():
    rows = _rows(1, "search", "registered", 9, 1)
    rows.append({**rows[0], "ordinal": 99, "proved": False, "agrees": None})
    rows[-1].pop("agrees")

    result = exp006.rate(rows)

    assert result["n"] == 10
    assert result["unscored_at_budget"] == 1


def test_one_failing_seed_fails_the_member(tmp_path, capsys):
    rows = []
    for seed in exp006.SEEDS:
        hits = 486 if seed != 4 else 440  # 97.2% vs 88.0%
        rows += _rows(seed, "search", "registered", hits, 500 - hits)

    artefact = exp006.assemble(rows, _truth(), tmp_path / "out.json", 1.0)
    exp006.report(artefact)
    out = " ".join(capsys.readouterr().out.split())

    assert "H3 FAILS ON THE SHIPPED GAME" in out
    assert "[4]" in out
    assert "EVERY SEED CLEARS" not in out


def test_all_seeds_clearing_satisfies_the_member(tmp_path, capsys):
    rows = []
    for seed in exp006.SEEDS:
        rows += _rows(seed, "search", "registered", 486, 14)

    artefact = exp006.assemble(rows, _truth(), tmp_path / "out.json", 1.0)
    exp006.report(artefact)
    out = " ".join(capsys.readouterr().out.split())

    assert "EVERY SEED CLEARS" in out
    assert "one member of three" in out
    assert "clause 1 was already recorded as failing" in out


def test_an_incomplete_set_of_seeds_reads_nothing(tmp_path, capsys):
    rows = _rows(1, "search", "registered", 486, 14) + _rows(
        2, "search", "registered", 486, 14
    )

    artefact = exp006.assemble(rows, _truth(), tmp_path / "out.json", 1.0)
    exp006.report(artefact)
    out = " ".join(capsys.readouterr().out.split())

    assert "INCOMPLETE" in out
    assert "EVERY SEED CLEARS" not in out
    assert "H3 FAILS" not in out


# -- pooling and the descriptive arm ------------------------------------------


def test_the_strata_are_kept_apart(tmp_path):
    rows = _rows(1, "search", "registered", 9, 1) + _rows(
        1, "search", "layer_uniform", 5, 5
    )

    artefact = exp006.assemble(rows, _truth(), tmp_path / "out.json", 1.0)
    block = artefact["seeds"]["1"]["search"]

    assert set(block) == {"registered", "layer_uniform"}
    assert block["registered"]["pooled"]["n"] == 10
    assert block["layer_uniform"]["pooled"]["n"] == 10
    assert "Forbidden" in artefact["pooling"]


def test_the_prior_arm_never_decides(tmp_path, capsys):
    """It is reported for every seed and the rule ignores it entirely."""
    rows = []
    for seed in exp006.SEEDS:
        rows += _rows(seed, "search", "registered", 486, 14)
        rows += _rows(seed, "prior", "registered", 200, 300)  # 40%, hopeless

    artefact = exp006.assemble(rows, _truth(), tmp_path / "out.json", 1.0)
    exp006.report(artefact)
    out = " ".join(capsys.readouterr().out.split())

    assert "EVERY SEED CLEARS" in out
    assert "descriptive, gates nothing" in out


def test_the_random_move_baseline_is_carried_into_the_artefact(tmp_path, capsys):
    """No rate may be quoted without the floor it sits on."""
    rows = _rows(1, "search", "registered", 9, 1)

    artefact = exp006.assemble(rows, _truth(), tmp_path / "out.json", 1.0)
    exp006.report(artefact)
    out = capsys.readouterr().out

    assert artefact["random_move_baseline"] == pytest.approx(0.219)
    assert "random-move baseline" in out


# -- resume -------------------------------------------------------------------


def test_a_truncated_final_line_is_reported(tmp_path):
    work = tmp_path / "work.jsonl"
    work.write_text('{"seed": 1, "arm": "search", "ordinal": 0}\n{"seed": 1, "ar')

    with pytest.raises(SystemExit, match="not JSON"):
        exp006.read_work(work)


def test_work_rows_identify_a_position_uniquely(tmp_path):
    """Resume skips on (seed, arm, ordinal); a collision would drop a position."""
    rows = _rows(1, "search", "registered", 3, 2) + _rows(
        1, "prior", "registered", 3, 2
    )
    keys = {(r["seed"], r["arm"], r["ordinal"]) for r in rows}

    assert len(keys) == len(rows)
