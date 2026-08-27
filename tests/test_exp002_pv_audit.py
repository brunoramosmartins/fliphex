"""Regression tests for the EXP-002 PV audit's run-survival machinery.

None of this is about the audit's *result*. It is about the three ways a
multi-day proof has actually been lost on this project, each of which cost real
compute before anyone could see it:

**The silent run.** A search that printed nothing until it returned. One launch
sat for 68.8 h emitting nothing, and there was no way to distinguish progress
from a process that had already died. Hence :class:`Heartbeat`, and hence the
requirement that it read the node counter *through* the solver — ``solve()``
rebinds ``solver.stats``, so a counter captured once reports zero forever.

**The OOM kill.** The table fills lazily, so an oversized ``--tt-bits`` does not
fail at startup; it fails hours in. On 2026-08-23 a 2**27-slot table reached
15.1 GiB on a 15 GiB machine and the kernel killed the process at 504M nodes and
4.8 h of CPU. An OOM kill writes no checkpoint, so every node of it was lost.
The guard stops the search first, which turns a total loss into a saved
``unproven`` row.

**The mislabelled row.** An unproven row that does not say *why* it stopped
reads as "the budget was too small", and the next person raises the budget --
the one dial that cannot help when the real limit was memory.
"""

import importlib.util
import sys
import time
from pathlib import Path

from solver.sweep_reader import SweepReader

ROOT = Path(__file__).resolve().parent.parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


audit = _load("exp002_pv_audit")


class _Stats:
    def __init__(self, nodes: int = 0) -> None:
        self.nodes = nodes


class _FakeSolver:
    """Only what :class:`Heartbeat` touches: a stats object and ``max_nodes``."""

    def __init__(self, nodes: int = 0) -> None:
        self.stats = _Stats(nodes)
        self.max_nodes = 10**9


def _wait_for(predicate, timeout: float = 3.0) -> bool:
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


# -- the memory guard -------------------------------------------------------


def test_guard_stops_the_search_before_the_oom_killer_does(monkeypatch):
    monkeypatch.setattr(audit, "rss_bytes", lambda: 20 * 1024**3)
    solver = _FakeSolver(nodes=1_000)

    with audit.Heartbeat(solver, "t", 0.02, 1_000_000, rss_ceiling=1024**3) as beat:
        assert _wait_for(lambda: beat.tripped is not None), "guard never fired"

    # Zero is the whole mechanism: the solver checks ``max_nodes`` on every
    # node, so the next one raises BudgetExceededError and the search unwinds
    # through the path that already exists for an exhausted budget.
    assert solver.max_nodes == 0
    assert beat.tripped == "rss-ceiling"


def test_guard_leaves_a_run_inside_its_ceiling_alone(monkeypatch):
    monkeypatch.setattr(audit, "rss_bytes", lambda: 1024**3)
    solver = _FakeSolver(nodes=1_000)

    with audit.Heartbeat(solver, "t", 0.02, 1_000_000, rss_ceiling=8 * 1024**3) as beat:
        time.sleep(0.15)
        assert beat.tripped is None

    assert solver.max_nodes == 10**9


def test_guard_is_off_by_default_so_tests_and_cheap_positions_are_unaffected(
    monkeypatch,
):
    monkeypatch.setattr(audit, "rss_bytes", lambda: 999 * 1024**3)
    solver = _FakeSolver(nodes=1_000)

    with audit.Heartbeat(solver, "t", 0.02, 1_000_000) as beat:
        time.sleep(0.15)

    assert beat.tripped is None
    assert solver.max_nodes == 10**9


def test_default_ceiling_leaves_headroom():
    ceiling = audit.default_rss_ceiling()
    if ceiling == 0:  # no /proc/meminfo; nothing to assert
        return
    with open("/proc/meminfo", "rb") as fh:
        total = next(
            int(line.split()[1]) * 1024 for line in fh if line.startswith(b"MemTotal:")
        )
    assert 0 < ceiling < total, "a ceiling at or above RAM protects nothing"


# -- the layer cache ---------------------------------------------------------


def test_release_drops_every_cached_layer():
    """Part 2 reads layer 1 and nothing else; the PV walk leaves 5.87 GiB.

    Measured on the 5×3: walking the principal variation touches all sixteen
    layers and leaves the most recent resident, which put the first part-2
    launch over the memory ceiling 97 seconds in — underneath a 7 GiB table
    that was not the problem. Constructed through ``__new__`` because a real
    :class:`SweepReader` needs the 4.1 GB checkpoint on disk.
    """
    db = SweepReader.__new__(SweepReader)
    db._resident = {7: bytearray(8), 8: bytearray(8), 9: bytearray(8)}
    db._order = [7, 8, 9]

    db.release()

    assert db._resident == {}
    assert db._order == []


def test_release_is_idempotent():
    db = SweepReader.__new__(SweepReader)
    db._resident = {}
    db._order = []
    db.release()
    assert db._resident == {}


# -- reading the counter through the solver ---------------------------------


def test_heartbeat_survives_the_stats_rebind(monkeypatch, capsys):
    """``solve()`` rebinds ``solver.stats``; a captured counter would read 0."""
    monkeypatch.setattr(audit, "rss_bytes", lambda: 0)
    solver = _FakeSolver(nodes=5)

    # ``readouterr`` drains the buffer, so accumulate rather than re-reading:
    # polling it directly would discard the very line being waited for.
    seen: list[str] = []

    def reported() -> bool:
        seen.append(capsys.readouterr().out)
        return "4,242" in "".join(seen)

    with audit.Heartbeat(solver, "t", 0.02, 1_000_000):
        solver.stats = _Stats(4_242)  # what solve() does on entry
        found = _wait_for(reported)

    assert found, f"heartbeat never reported the rebound counter: {''.join(seen)!r}"
