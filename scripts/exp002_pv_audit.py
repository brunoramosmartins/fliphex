"""EXP-002's principal-variation audit — the gate that targets the reported number.

Registered in ``experiments/registry.md`` with EXP-002 from the start, and not
run on either arm until now (amendment of 2026-08-09). The registration states
why it is not redundant with adr-010 V4:

    "V4 bounds the *rate* of errors in the database; only the PV audit targets
    the number actually reported."

V4 samples 40 configurations per layer out of layers up to 5.0 × 10⁹. If the
sweep were wrong about *the opening position specifically*, V4 would almost
certainly miss it and still pass. This audit re-derives the one line the claim
rests on.

What it checks
--------------
1. **The principal variation.** The PV is walked out of the *sweep's* layer files
   — at each position the mover picks a child the database calls a loss for the
   opponent. Every position on that line is then re-derived by
   ``solver/minimax.py``, which reaches the game through
   ``fliphex.legal_moves``/``apply_move`` and shares no code with the packed
   sweep. Two implementations, as adr-010 V3 requires of evidence.
2. **Every distinct first move.** The root value is only as good as the claim
   that *no other* opening does better. For each legal first move the audit
   compares the database's verdict against a forward proof, so a sweep that got
   one opening wrong cannot hide behind the one the PV happens to take.

Why it needs the checkpoint files
---------------------------------
The sweep's layers are the thing being audited, and they only exist on disk since
``solver/checkpoint.py``. The h2 arm has them; **h1 does not** — it ran before
crash resume existed and its layers were discarded. Auditing h1 therefore
requires re-running it with ``--checkpoint``, which the registry already wants
for two other reasons.

    python scripts/exp002_pv_audit.py --board 3 3 --arm h1 --checkpoint data/ck
    ~/pypy3.11-v7.3.23-linux64/bin/pypy scripts/exp002_pv_audit.py --arm h2

Cost: one forward proof per PV position (15 of them) plus one per distinct first
move. Each of those is a *full* subgame proof in its own right — an earlier
version of this docstring claimed they partition the root's own search, which is
false and made part 2 look far cheaper than it is. Positions that exceed the
node budget are reported as **unproven**, never as agreeing.

Because a single proof can run for hours with nothing to show, every search is
wrapped in a :class:`Heartbeat`. See its docstring for the run that made that
non-negotiable.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fliphex.moves import apply_move, legal_moves  # noqa: E402
from fliphex.notation import encode_move  # noqa: E402
from fliphex.state import Colour  # noqa: E402
from fliphex.variant import Arm, Variant  # noqa: E402
from solver.checkpoint import Checkpoint, atomic_write  # noqa: E402
from solver.minimax import LOSS, WIN, BudgetExceededError, Solver  # noqa: E402
from solver.packed_sweep import PackedSweep  # noqa: E402
from solver.retrograde import SLOT_LOSS, SLOT_WIN, LayerIndex  # noqa: E402
from solver.transposition import TranspositionTable  # noqa: E402


class Database:
    """Read-only view of a sweep's layers, as written by ``solver.checkpoint``.

    Layers are loaded **on demand and evicted**, never all at once. Holding all
    sixteen costs 4.1 GB on the 5×3, and the first attempt at this audit did
    exactly that: 12.9 GB resident on a 15 GB machine, with the transposition
    table on top, and it began paging before it finished 7 of 540 positions.

    A small cache suffices because every consumer walks `t` monotonically: the
    PV walk needs layer `t` and `t + 1` together, part 1 needs one at a time,
    and part 2 only ever touches layer 1 (240 configurations on the 5×3).
    """

    #: Enough for the PV walk's ``t``/``t+1`` pair, with one spare.
    MAX_RESIDENT = 3

    def __init__(self, variant: Variant, checkpoint: Checkpoint) -> None:
        self.variant = variant
        self.checkpoint = checkpoint
        self.sweep = PackedSweep(variant, variant.board(), 2)
        manifest = checkpoint.load_manifest()
        if manifest is None:
            raise SystemExit(
                f"no checkpoint at {checkpoint.root} — the PV audit reads the "
                f"sweep's own layers, so the arm must have been run with "
                f"--checkpoint. h1 predates crash resume and must be re-run."
            )
        missing = set(range(variant.n_cells + 1)) - set(manifest["complete_layers"])
        if missing:
            raise SystemExit(
                f"checkpoint at {checkpoint.root} is incomplete: layers "
                f"{sorted(missing)} are absent. A partial database cannot be "
                f"audited — the sweep must have finished."
            )
        self._resident: dict[int, bytearray] = {}
        self._order: list[int] = []
        self.index = {t: LayerIndex(variant, t) for t in range(variant.n_cells + 1)}

    def layer(self, t: int) -> bytearray:
        cached = self._resident.get(t)
        if cached is not None:
            self._order.remove(t)
            self._order.append(t)
            return cached
        values = self.checkpoint.load_layer(t)
        self._resident[t] = values
        self._order.append(t)
        while len(self._order) > self.MAX_RESIDENT:
            del self._resident[self._order.pop(0)]
        return values

    def slot(self, state) -> int:
        """The database's verdict for ``state``, relative to the side to move."""
        t = sum(1 for c in state.colours if c != Colour.EMPTY)
        return self.sweep.get(self.layer(t), self.index[t].encode(state))

    def value(self, state) -> int:
        slot = self.slot(state)
        if slot == SLOT_WIN:
            return WIN
        if slot == SLOT_LOSS:
            return LOSS
        raise AssertionError(
            f"database holds no value for a reachable position: {slot}"
        )

    def principal_variation(self, board, state) -> list:
        """Walk the database's own optimal line from ``state`` to a terminal.

        At a winning node the mover must have a child the database calls a loss
        for the opponent; if none exists the database contradicts itself, and
        that is a finding rather than an exception to swallow.
        """
        line = []
        current = state
        while not current.is_terminal():
            want = SLOT_LOSS if self.slot(current) == SLOT_WIN else None
            chosen = None
            for move in legal_moves(board, current):
                child = apply_move(board, current, move)
                slot = self.slot(child)
                if want is None or slot == want:
                    chosen = (move, child)
                    if want is not None:
                        break
            if chosen is None:
                raise AssertionError(
                    f"database calls a position a win but no child is a loss "
                    f"— it is internally inconsistent at ply {len(line)}"
                )
            move, current = chosen
            line.append(move)
        return line


class Heartbeat:
    """Print progress from *inside* one opaque proof, on a background thread.

    Why this exists
    ---------------
    A single ``Solver.solve`` on the 5×3 root is hours long and, until this
    class, printed nothing until it returned. One run was launched, the machine
    stayed up for 68.8 hours, and it emitted not one line — leaving no way to
    tell whether the search was making progress, had been killed, or was orders
    of magnitude past its projection. That is an unacceptable instrument for a
    proof measured in days, and the same blindness is what let an earlier
    projection miss by 4× without anyone noticing mid-run.

    The thread only sleeps and reads a counter, so it costs nothing the search
    can measure. It is a daemon, so it never keeps a finished run alive.

    Reading the counter
    -------------------
    ``Solver.solve`` **rebinds** ``solver.stats`` when it starts, so the counter
    is looked up through the solver on every tick rather than captured once. A
    tick that lands during the rebind reads the old object and reports a stale
    count for one interval, which is harmless: nothing but the log depends on
    it, and the row's node count still comes from the search itself.
    """

    def __init__(self, solver, label: str, every: float, budget: int) -> None:
        self.solver = solver
        self.label = label
        self.every = every
        self.budget = budget
        # Two clocks on purpose. ``perf_counter`` is CLOCK_MONOTONIC, which does
        # not advance while the machine is suspended; ``time.time`` does. This
        # laptop's lid gets closed mid-run, so the gap between them *is* the
        # suspended time, reported directly instead of inferred. An earlier
        # round of this work spent a day on a "corrupt clock" theory that a
        # measurement this cheap would have settled outright.
        self.started = time.perf_counter()
        self.wall_started = time.time()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def __enter__(self) -> Heartbeat:
        if self.every > 0:
            self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()

    def _run(self) -> None:
        # ``Event.wait`` rather than ``sleep`` so the last interval does not
        # delay the line the search itself wants to print.
        while not self._stop.wait(self.every):
            elapsed = time.perf_counter() - self.started
            wall = time.time() - self.wall_started
            nodes = self.solver.stats.nodes
            rate = nodes / elapsed if elapsed > 0 else 0.0
            suspended = max(0.0, wall - elapsed)
            line = (
                f"      [{time.strftime('%m-%d %H:%M')}] {self.label}  "
                f"{nodes:>14,} nodes  {rate:>9,.0f}/s  {elapsed / 3600:5.2f} h cpu"
                f"  {100 * nodes / self.budget:5.1f}% of budget"
            )
            if suspended > 60:
                line += f"  (+{suspended / 3600:.2f} h suspended)"
            print(line, flush=True)


def rederive(
    board, state, tt, budget: int, label: str = "", every: float = 0.0
) -> tuple[int | None, int]:
    """Prove ``state`` by forward search. ``None`` means the budget ran out.

    ``label`` and ``every`` drive a :class:`Heartbeat`; ``every <= 0`` disables
    it, which is what the cheap positions and the tests want.

    The table is supplied by the caller and **shared across every position this
    audit proves**, for two reasons. Allocating a 2²⁴-slot table costs ~200 ms,
    which is 1.8 minutes of pure allocation across the 5×3's first moves and
    dwarfs some of the searches it serves. And sharing is a real speedup rather
    than only an economy: sibling openings transpose heavily, so a position
    proved under one first move is often already proved under the next.

    Sharing is sound because entries are keyed by Zobrist and depth, and a given
    configuration has the same depth wherever it appears — the same property the
    sweep relies on to index by layer.
    """
    solver = Solver(board, tt=tt, max_nodes=budget)
    with Heartbeat(solver, label, every, budget):
        try:
            result = solver.solve(state)
        except BudgetExceededError:
            return None, solver.stats.nodes
    return result.value, result.stats.nodes


def partial_path(args, variant: Variant) -> Path:
    return args.out / f"exp002-pv-audit-{variant.name}.json"


def load_partial(args, variant: Variant) -> dict:
    """Completed rows from an earlier session, keyed so they can be skipped.

    The audit is hours of forward proofs and has no state beyond "which
    positions are already settled", so resume is just: write the artefact after
    every position, and on start skip what it already names. Each first-move
    proof is independent of the others, which is what makes this sound — unlike
    the sweep, there is no digest or RNG stream whose order matters.
    """
    path = partial_path(args, variant)
    if args.no_resume or not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        print(f"  partial artefact at {path} is unreadable; starting over")
        return {}


def audit(variant: Variant, args) -> dict:
    board = variant.board()
    ckpt = Checkpoint(args.checkpoint / variant.name)
    db = Database(variant, ckpt)
    root = variant.initial_state()

    print(f"\n  === EXP-002 PV audit — {variant.name} ===")
    print(f"  database: {ckpt.root}")
    print(f"  root value from the sweep: {'P1' if db.value(root) == WIN else 'P2'}")
    print(f"  interpreter: {sys.implementation.name} {sys.version.split()[0]}")
    print(f"  node budget: {args.budget:,} per position")
    print(
        "  heartbeat: "
        + (f"every {args.heartbeat:g}s" if args.heartbeat > 0 else "disabled"),
        flush=True,
    )

    prior = load_partial(args, variant)
    prior_pv = prior.get("pv", {}).get("rows", [])
    prior_first = prior.get("first_moves", {}).get("rows", [])

    # **Only a decided row is settled.** A row whose search ran out of budget is
    # not evidence of anything, and re-running is usually how you spend a bigger
    # budget on exactly those — the first attempt at the 5×3 left the root
    # unproven at 200M nodes, and an earlier version of this resume skipped it,
    # so a run launched at 5×10⁹ finished in 40 seconds having proved nothing
    # while the artefact recorded the larger budget. Unproven rows are retried.
    done_pv = {r["ply"]: r for r in prior_pv if r["got"] is not None}
    done_first = {r["move"]: r for r in prior_first if r["got"] is not None}
    retry_pv = len(prior_pv) - len(done_pv)
    retry_first = len(prior_first) - len(done_first)

    if done_pv or done_first or retry_pv or retry_first:
        print(
            f"  RESUMING from {partial_path(args, variant)}: "
            f"{len(done_pv)} PV positions and {len(done_first)} first moves "
            f"decided",
            flush=True,
        )
        if retry_pv or retry_first:
            print(
                f"  retrying {retry_pv} PV positions and {retry_first} first "
                f"moves that ran out of budget last time",
                flush=True,
            )
    print(flush=True)

    tt = TranspositionTable(1 << args.tt_bits, verify=True)

    started = time.perf_counter()
    line = db.principal_variation(board, root)
    print(f"  principal variation, {len(line)} plies:")
    print(f"    {' '.join(encode_move(board, m) for m in line)}\n", flush=True)

    moves = legal_moves(board, root)

    # Rows carried over from an earlier session live in these dicts from the
    # start; they are **not** appended as the loops reach them. A checkpoint
    # written mid-loop serialises whatever the dict holds, so a run that dies
    # early no longer takes the earlier session's proofs down with it. The
    # 2026-08-20 resume did exactly that: it carried thirteen decided plies,
    # spent 21 h proving ply 0, saved — and that save wrote a single row,
    # because plies 2-14 had not been re-appended yet. Thirteen proofs gone,
    # silently, at the one moment the checkpoint was supposed to be earning
    # its keep.
    pv_done = dict(done_pv)
    first_done = dict(done_first)

    def pv_snapshot() -> list:
        return [pv_done[k] for k in sorted(pv_done)]

    def first_snapshot() -> list:
        ordered = (encode_move(board, m) for m in moves)
        return [first_done[n] for n in ordered if n in first_done]

    # -- part 1: every position on the PV -----------------------------------
    # Each PV position gets its **own** table, deliberately, even though sharing
    # one would make eight of these nine searches return in a single node: every
    # PV position lies inside the root's proof tree, so a shared table answers
    # them from entries the ply-0 search wrote. That is fast and it is still
    # forward-searcher output, but it collapses fifteen checks into one — a
    # single table fault (the depth-preferred silent drop of adr-010's V3
    # amendment was exactly that) would corrupt all of them together. A fresh
    # table per position costs ~200 ms each and removes the table as a shared
    # failure mode across the line the whole claim rests on.
    if args.parts == "first":
        print(f"  part 1 — SKIPPED (--parts first); {len(pv_done)} rows carried over")
    else:
        print("  part 1 — re-deriving every position on the PV by forward search")
        print("    (independent table per position — see the comment in the source)")
        state = root
        for ply, move in enumerate([None, *line]):
            if move is not None:
                state = apply_move(board, state, move)
            if state.is_terminal():
                break
            expected = db.value(state)
            if ply in pv_done:
                print(f"    ply {ply:2d}  (from a previous session)", flush=True)
                continue
            fresh = TranspositionTable(1 << args.tt_bits, verify=True)
            got, nodes = rederive(
                board, state, fresh, args.budget, f"pv ply {ply}", args.heartbeat
            )
            status = (
                "unproven"
                if got is None
                else ("agree" if got == expected else "DISAGREE")
            )
            pv_done[ply] = {
                "ply": ply,
                "expected": expected,
                "got": got,
                "nodes": nodes,
                # Rows can outlive the run that made them, and a resume may use
                # a different budget or table size, so each row carries its own.
                # The node count is only interpretable against both.
                "budget": args.budget,
                "tt_bits": args.tt_bits,
            }
            print(
                f"    ply {ply:2d}  sweep={'WIN ' if expected == WIN else 'LOSS'}  "
                f"{status:9s}  {nodes:>12,} nodes",
                flush=True,
            )
            _save(
                args,
                variant,
                db,
                root,
                line,
                pv_snapshot(),
                first_snapshot(),
                started,
                board,
            )

    # -- part 2: every distinct first move ----------------------------------
    if args.parts == "pv":
        print(
            f"\n  part 2 — SKIPPED (--parts pv); "
            f"{len(first_done)}/{len(moves):,} rows carried over"
        )
        return _finish(
            variant,
            args,
            db,
            root,
            line,
            pv_snapshot(),
            first_snapshot(),
            started,
            board,
        )

    print(f"\n  part 2 — re-deriving the root under each of {len(moves):,} first moves")
    for i, move in enumerate(moves):
        name = encode_move(board, move)
        if name in first_done:
            continue
        child = apply_move(board, root, move)
        expected = db.value(child)
        # A heartbeat here is self-limiting: the thread's first tick is one
        # interval in, so a position that proves quickly — which is most of
        # them — prints nothing at all, and only a stalled one becomes visible.
        label = f"first {i + 1}/{len(moves)} {name}"
        got, nodes = rederive(board, child, tt, args.budget, label, args.heartbeat)
        first_done[name] = {
            "move": name,
            "expected": expected,
            "got": got,
            "nodes": nodes,
            "budget": args.budget,
            "tt_bits": args.tt_bits,
        }
        _save(
            args,
            variant,
            db,
            root,
            line,
            pv_snapshot(),
            first_snapshot(),
            started,
            board,
        )
        if got is not None and got != expected:
            print(f"    DISAGREE on {encode_move(board, move)}", flush=True)
        if (i + 1) % args.report_every == 0:
            rows = first_snapshot()
            done = sum(1 for r in rows if r["got"] is not None)
            bad = sum(1 for r in rows if r["got"] not in (None, r["expected"]))
            print(
                f"    {i + 1:>6,}/{len(moves):,}  proven {done:,}  disagree {bad}  "
                f"{time.perf_counter() - started:,.0f}s",
                flush=True,
            )

    return _finish(
        variant,
        args,
        db,
        root,
        line,
        pv_snapshot(),
        first_snapshot(),
        started,
        board,
    )


def _finish(variant, args, db, root, line, pv_rows, first_rows, started, board) -> dict:
    """Build the artefact, print the summary, and persist. One exit for both
    the full run and the ``--parts`` short circuits, so a partial run reports
    itself the same way a complete one does."""
    artefact = _artefact(
        variant, args, db, root, line, pv_rows, first_rows, started, board
    )
    _print_summary(variant, artefact, first_rows)
    _save(args, variant, db, root, line, pv_rows, first_rows, started, board)
    return artefact


def _tally(rows) -> tuple[int, int, int]:
    agree = sum(1 for r in rows if r["got"] == r["expected"])
    disagree = sum(1 for r in rows if r["got"] not in (None, r["expected"]))
    unproven = sum(1 for r in rows if r["got"] is None)
    return agree, disagree, unproven


def _artefact(
    variant, args, db, root, line, pv_rows, first_rows, started, board
) -> dict:
    """Build the artefact. Written after *every* position, so it doubles as the
    resume point — which is why ``rows`` is carried in full for both parts."""
    pv_a, pv_d, pv_u = _tally(pv_rows)
    fm_a, fm_d, fm_u = _tally(first_rows)
    total_first = len(legal_moves(board, root))
    complete = len(first_rows) == total_first and pv_u == 0
    return {
        "experiment": "EXP-002",
        "audit": "principal-variation",
        "variant": variant.name,
        "root_value": "P1" if db.value(root) == WIN else "P2",
        "principal_variation": [encode_move(board, m) for m in line],
        # The budget *this session* ran at. Rows carry their own, since a
        # resumed audit can mix budgets and the summary must not imply one.
        "node_budget_this_session": args.budget,
        "tt_bits": args.tt_bits,
        "pv": {"agree": pv_a, "disagree": pv_d, "unproven": pv_u, "rows": pv_rows},
        "first_moves": {
            "agree": fm_a,
            "disagree": fm_d,
            "unproven": fm_u,
            "settled": len(first_rows),
            "total": total_first,
            "rows": first_rows,
            "disagreements": [
                r for r in first_rows if r["got"] not in (None, r["expected"])
            ],
        },
        # A partial run is never "passed": the audit exists to cover a specific
        # line, and a line half-covered is a gap, not a weaker pass.
        "complete": complete,
        "passed": complete and pv_d == 0 and fm_d == 0,
        "interpreter": f"{sys.implementation.name} {sys.version.split()[0]}",
        "seconds": time.perf_counter() - started,
    }


def _save(args, variant, db, root, line, pv_rows, first_rows, started, board) -> None:
    if args.no_write:
        return
    artefact = _artefact(
        variant, args, db, root, line, pv_rows, first_rows, started, board
    )
    atomic_write(partial_path(args, variant), json.dumps(artefact, indent=2).encode())


def _print_summary(variant, artefact, first_rows) -> None:
    pv, fm = artefact["pv"], artefact["first_moves"]
    print()
    print(
        f"    PV positions .......... {pv['agree']} agree, {pv['disagree']} "
        f"disagree, {pv['unproven']} unproven"
    )
    print(
        f"    first moves ........... {fm['agree']} agree, {fm['disagree']} "
        f"disagree, {fm['unproven']} unproven"
    )
    print(f"    coverage (first moves)  {fm['agree'] / max(fm['total'], 1):.1%}")
    print(f"    elapsed ............... {artefact['seconds']:,.1f}s")
    print()
    if artefact["passed"]:
        print(f"    {variant.name}: PV AUDIT PASSED")
    elif fm["disagree"] or pv["disagree"]:
        print(f"    {variant.name}: PV AUDIT FAILED — see disagreements above")
    else:
        print(f"    {variant.name}: INCOMPLETE — no disagreement, but not full cover")
    if pv["unproven"]:
        print(
            "    note: an unproven position on the PV is a gap, not a pass — the "
            "audit exists precisely to cover this line."
        )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--board", type=int, nargs=2, default=(5, 3), metavar=("COLS", "ROWS")
    )
    p.add_argument("--arm", choices=["h1", "h2"], default="h2")
    p.add_argument("--checkpoint", type=Path, default=Path("data/checkpoints"))
    p.add_argument("--budget", type=int, default=200_000_000)
    p.add_argument("--tt-bits", type=int, default=24)
    p.add_argument(
        "--parts",
        choices=["all", "pv", "first"],
        default="all",
        help=(
            "which halves to run. 'pv' is the one that targets the reported "
            "value and is far cheaper; 'first' is the coverage half over every "
            "distinct opening."
        ),
    )
    p.add_argument("--report-every", type=int, default=25)
    p.add_argument(
        "--heartbeat",
        type=float,
        default=60.0,
        metavar="SECONDS",
        help=(
            "print nodes and rate from inside a running proof this often. "
            "0 disables it. A single 5x3 proof is hours long and otherwise "
            "silent, which once hid a 68.8 h run that produced no output at all."
        ),
    )
    p.add_argument(
        "--no-resume",
        action="store_true",
        help="ignore a partial artefact and re-prove every position",
    )
    p.add_argument("--out", type=Path, default=Path("results"))
    p.add_argument("--no-write", action="store_true")
    args = p.parse_args()

    variant = Variant(args.board[0], args.board[1], Arm(args.arm))
    artefact = audit(variant, args)

    if not args.no_write:
        print(f"\n    artefact -> {partial_path(args, variant)}")
    return 0 if artefact["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
