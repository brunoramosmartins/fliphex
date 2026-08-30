"""Regression tests for the EXP-003 instrument and its analysis.

Both pin a defect that was found *after* a real run, by the analysis guard
rather than by the run's own output — which is the wrong way round and is what
these tests exist to prevent recurring.

**The defect.** ``exp003_endgame_cost.py``'s ``cens`` column printed only the
with-TT arm's censored count, so the k=8 run displayed ``cens 0`` while the
no-TT arm had one sample pinned at the 20,000,000-node budget. The JSON recorded
it correctly, which is the only reason it was recoverable: a run that hides
censoring is worse than one that reports it.

**The over-strict guard.** The first analysis script hard-failed on *any*
censoring. That is wrong in the other direction — one censored sample out of 200
cannot move a median (the 100th of 200 sorted values), so refusing to analyse
throws away a usable result. The correct criterion is the producer's own
``median_is_lower_bound`` (censoring past half the samples), with the affected
statistics named individually.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load(name: str):
    """Import a module from ``scripts/``, which is not a package.

    The ``sys.modules`` registration is not optional: ``@dataclass`` resolves a
    class's annotations through ``sys.modules[cls.__module__]``, so a module
    executed without being registered there makes that lookup return ``None``
    and the decorator raises inside ``dataclasses``.
    """
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


cost = _load("exp003_endgame_cost")
analysis = _load("exp003_analysis")


def _cell(median: float, censored: int = 0, n: int = 200) -> dict:
    return {
        "n": n,
        "median": median,
        "p90": median * 3,
        "max": median * 10,
        "total_seconds": 1.0,
        "censored": censored,
        "median_is_lower_bound": censored > n // 2,
    }


def _artefact(rows: dict[int, tuple[dict, dict]], max_nodes: int = 2_000_000) -> dict:
    return {
        "experiment": "EXP-003",
        "board_cells": 25,
        "hands": [13, 12],
        "seed": 1,
        "samples_per_k": 200,
        "max_nodes": max_nodes,
        "threshold": 10**6,
        "k_star": None,
        "sampling": "random playout (see registry: known bias)",
        "results": [
            {"k": k, "with_tt": tt, "without_tt": raw} for k, (tt, raw) in rows.items()
        ],
    }


def _write(tmp_path: Path, name: str, blob: dict) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(blob))
    return path


def _full() -> dict[int, tuple[dict, dict]]:
    """A clean, complete sweep: k = 3..8, every cell well under the threshold."""
    return {k: (_cell(10.0**i), _cell(10.0**i)) for i, k in enumerate(range(3, 9))}


# -- the instrument must not be able to hide censoring ------------------------


def test_the_censored_column_reports_both_arms(capsys):
    """The defect: only the with-TT count was shown, so k=8 printed 'cens 0'."""
    m = cost.Measurement(k=8)
    m.with_tt = [cost.Sample(nodes=100, seconds=0.1, censored=False)] * 200
    m.without_tt = [cost.Sample(nodes=100, seconds=0.1, censored=False)] * 199 + [
        cost.Sample(nodes=20_000_001, seconds=9.0, censored=True)
    ]

    cost.report([m], cost.THRESHOLD)
    line = next(
        row
        for row in capsys.readouterr().out.splitlines()
        if row.strip().startswith("8 ")
    )
    assert "0/1" in line, f"censoring in the no-TT arm is invisible in: {line!r}"


def test_the_censored_column_shows_a_clean_run_as_clean(capsys):
    m = cost.Measurement(k=5)
    m.with_tt = [cost.Sample(nodes=10, seconds=0.0, censored=False)] * 200
    m.without_tt = [cost.Sample(nodes=10, seconds=0.0, censored=False)] * 200

    cost.report([m], cost.THRESHOLD)
    line = next(
        row
        for row in capsys.readouterr().out.splitlines()
        if row.strip().startswith("5 ")
    )
    assert "0/0" in line


# -- the analysis guard must be strict in the right place ---------------------


def test_censoring_below_the_median_does_not_block_the_analysis(tmp_path, capsys):
    """One censored sample in 200 cannot move the 100th sorted value."""
    rows = _full()
    rows[8] = (_cell(806_474.0), _cell(1_736_922.0, censored=1))
    path = _write(tmp_path, "exp003.json", _artefact(rows))

    _, cells = analysis.load([path], interim=False)
    assert cells[8]["without_tt"]["censored"] == 1
    assert "max is a lower bound" in capsys.readouterr().out


def test_censoring_past_half_the_samples_blocks_the_analysis(tmp_path):
    """Then the median IS a lower bound and the rule is not decidable."""
    rows = _full()
    rows[8] = (_cell(806_474.0, censored=150), _cell(1_736_922.0))
    path = _write(tmp_path, "exp003.json", _artefact(rows))

    with pytest.raises(SystemExit, match="LOWER BOUND"):
        analysis.load([path], interim=False)


def test_an_incomplete_sweep_refuses_a_verdict(tmp_path):
    rows = _full()
    del rows[8]
    path = _write(tmp_path, "exp003.json", _artefact(rows))

    with pytest.raises(SystemExit, match="missing"):
        analysis.load([path], interim=False)


def test_an_incomplete_sweep_is_allowed_for_an_interim_peek(tmp_path):
    rows = _full()
    del rows[8]
    path = _write(tmp_path, "exp003.json", _artefact(rows))

    _, cells = analysis.load([path], interim=True)
    assert set(cells) == {3, 4, 5, 6, 7}


def test_a_run_at_the_wrong_seed_is_refused(tmp_path):
    blob = _artefact(_full())
    blob["seed"] = 7
    path = _write(tmp_path, "exp003.json", blob)

    with pytest.raises(SystemExit, match="not the registered experiment"):
        analysis.load([path], interim=False)


def test_the_same_k_in_two_files_is_refused(tmp_path):
    a = _write(tmp_path, "a.json", _artefact(_full()))
    b = _write(tmp_path, "b.json", _artefact(_full()))

    with pytest.raises(SystemExit, match="more than one file"):
        analysis.load([a, b], interim=False)
