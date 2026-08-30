"""EXP-002 — the exact game value of the 5×3, and the H1/H2 partial verdicts.

Registered in ``experiments/registry.md`` before this script existed. This is the
**strategically meaningful** exact solve: 15 cells, hands 8 + 7, both hands
exactly exhausted, Player 1 moves last with the joker as the extra tile, and the
same Z/2 mirror as the shipped 5×5
(`adr-011 <../docs/adr/adr-011-reduced-variant-parity.md>`_).

Why the verification differs from EXP-001
-----------------------------------------
The 3×3 is small enough to solve **twice**, so adr-010 **V3** — forward
alpha-beta against the retrograde sweep — carries the correctness argument
there. It cannot here: 1.75 × 10¹⁰ configurations is an enumeration, and the
forward searcher would never finish. So V3 is not attempted, and its weight
moves onto V4 and V6, which the sweep can support.

The database never exists all at once, either. Widened to one byte per entry the
5×3 layers total 17.5 GB; at two bits and two layers resident the sweep peaks
around 2.5 GB. Everything below is therefore sampled through the sweep's
``observer`` hook **while each layer is still in memory**, and the layer is then
discarded. Nothing is written to disk but the artefact.

What this run checks
--------------------
* **V0** — the terminal layer is ``2**15 = 32,768``, decided by counting cells.
* **V1** — per-layer counts against ``scripts/layer_profile.py``, which imports
  nothing from the engine. Exact equality, no tolerance.
* **V2** — a tied terminal raises. On 15 cells it cannot happen; the assertion
  is total and free.
* **V4** — sampled positions re-derived by **direct forward search that never
  consults the sweep**, with the sample size and seed fixed before the run.
  Honest limitation: only positions shallow enough to prove within the node
  budget can be checked, so V4 covers the endgame and thins out going up. Since
  2026-08-27 it reports *where* it succeeded — per layer, with the shallowest
  layer it actually searched — and terminal draws are re-derived through
  ``fliphex.rules`` instead of being skipped in silence.
* **V5** — a running SHA-256 over every layer, in layer order.
* **V6** — mirror consistency. The 5×3's automorphism is the same left-right
  reflection as the 5×5's, and `adr-008 <../docs/adr/adr-008-board-mirror-symmetry.md>`_
  says it is a *game* symmetry only once **both** copies of the chiral ``P3-y``
  are off the hands. So V6 samples only configurations satisfying that, and
  reports how many were eligible — a mirror check run indiscriminately would
  pass or fail for the wrong reason. This is the first board where V6 applies
  at all: the withdrawn 4×4's automorphism was a rotation, which no tile breaks.
  Since 2026-08-27 it also reports eligibility per layer and separates out the
  pairs where a configuration is *fixed* by the reflection — those compare a
  value with itself and are evidence of nothing.

    pypy scripts/exp002_solve_5x3.py --arm h1
    pypy scripts/exp002_solve_5x3.py --arm h1 --bits 2 --out data/subgame-solutions
    python scripts/exp002_solve_5x3.py --board 5 1 --arm h1     # smoke test
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from random import Random

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_symmetry import board_automorphisms  # noqa: E402
from layer_profile import layer as closed_form_layer  # noqa: E402

from fliphex.rules import winner as terminal_winner  # noqa: E402
from fliphex.state import TILE_INDEX, Colour  # noqa: E402
from fliphex.variant import Arm, Variant  # noqa: E402
from solver.checkpoint import Checkpoint  # noqa: E402
from solver.minimax import WIN, BudgetExceededError, Solver  # noqa: E402
from solver.packed_sweep import PackedSweep  # noqa: E402
from solver.retrograde import SLOT_LOSS, SLOT_WIN, LayerIndex  # noqa: E402
from solver.transposition import TranspositionTable  # noqa: E402

CHIRAL = "P3-y"


@dataclass
class Checks:
    """Everything the observer collects while the layers are still resident."""

    variant: Variant
    v4_per_layer: int
    v6_per_layer: int
    seed: int
    #: Print a line per layer. A 5×3 arm runs for the better part of a day and
    #: the summary only prints at the end, so without this the log is empty for
    #: hours and there is no way to tell a slow sweep from a hung one.
    progress: bool = True

    digest: object = field(default_factory=hashlib.sha256)
    layer_counts: dict[int, int] = field(default_factory=dict)
    v1_problems: list[str] = field(default_factory=list)
    v4_samples: list[tuple[int, int, int]] = field(default_factory=list)
    v6_checked: int = 0
    v6_rejected: int = 0
    v6_problems: list[str] = field(default_factory=list)
    #: Per-layer V6 accounting, keyed by ``t``. Aggregates alone cannot say
    #: *where* the mirror was tested, and adr-008 guarantees the answer is
    #: "only near the end" — see :meth:`_mirror_check`.
    v6_rows: dict[int, dict[str, int]] = field(default_factory=dict)
    #: True when this run resumed from a checkpoint predating the per-layer
    #: rows, so the breakdown covers only the layers swept in this session.
    v6_rows_partial: bool = False

    def __post_init__(self) -> None:
        self.rng = Random(self.seed)
        self.hand_sizes = tuple(len(h) for h in self.variant.deck_names())
        board = self.variant.board()
        self.mirror = _mirror_permutation(board)
        self.chiral_tile = TILE_INDEX[CHIRAL]
        self._started = self._last = time.perf_counter()

    # -- called once per layer, while `values` is still in memory -------------

    def __call__(self, t: int, values: bytearray, sweep: PackedSweep) -> None:
        size = sweep.layer_size(t)
        self.layer_counts[t] = size

        expected = closed_form_layer(self.variant.n_cells, *self.hand_sizes, t)
        if size != expected:
            self.v1_problems.append(f"layer {t}: {size:,} vs formula {expected:,}")

        self.digest.update(bytes(values))

        for _ in range(min(self.v4_per_layer, size)):
            index = self.rng.randrange(size)
            self.v4_samples.append((t, index, sweep.get(values, index)))

        self._mirror_check(t, values, sweep, size)

        if self.progress:
            now = time.perf_counter()
            print(
                f"    layer {t:2d}  {size:>15,} configs  "
                f"{now - self._last:7.1f}s  ({now - self._started:,.0f}s total)",
                flush=True,
            )
            self._last = now

    def _mirror_check(self, t, values, sweep, size) -> None:
        """A configuration and its mirror image must share a value.

        Only where the mirror is a game symmetry at all: adr-008 makes it one
        exactly when neither hand still holds ``P3-y``, because the chiral tile's
        reflection is not in the deck. Sampling without that filter would be
        measuring something else.

        Two coverage numbers are recorded here that the 2026-08-09 registry
        amendment asked for, and one it did not know to ask for.

        ``ineligible`` was already counted in aggregate; it is now counted per
        layer, which is what turns "V6 covered 9.8%" into the shape that figure
        was hiding. Measured on h2: eligibility climbs monotonically from 0% at
        ``t = 0`` and ``t = 1`` to 100% at ``t = 15``, and layers 2 and 3
        exhausted the attempt cap without finding their 40 pairs.

        ``self_mirror`` is new. A configuration fixed by the reflection encodes
        to its own index, so the comparison is a value against itself: it cannot
        fail, and counting it as a checked pair overstates the evidence. Such
        pairs are counted separately and **left in** ``checked`` deliberately —
        dropping them would mean drawing replacements, the RNG stream would
        diverge from the h2 arm's, and the two arms could no longer be compared
        on the samples the registry pins by seed. Report the difference; do not
        silently change the draw.
        """
        if self.mirror is None:
            return
        layer = LayerIndex(self.variant, t)
        row = self.v6_rows.setdefault(
            t, {"attempts": 0, "ineligible": 0, "checked": 0, "self_mirror": 0}
        )
        checked = 0
        # Bounded by attempts as well as by hits: in early layers almost nothing
        # is eligible, because both copies of P3-y are still in hand, and an
        # unbounded search for eligible samples would stall the sweep there.
        for _ in range(20 * self.v6_per_layer):
            if checked >= self.v6_per_layer:
                break
            row["attempts"] += 1
            index = self.rng.randrange(size)
            state = layer.decode(index)
            if not self._chiral_spent(state):
                self.v6_rejected += 1
                row["ineligible"] += 1
                continue
            mirrored = _mirror_state(state, self.mirror)
            other_index = layer.encode(mirrored)
            checked += 1
            self.v6_checked += 1
            row["checked"] += 1
            if other_index == index:
                row["self_mirror"] += 1
            if sweep.get(values, index) != sweep.get(values, other_index):
                self.v6_problems.append(
                    f"layer {t}: index {index} and its mirror {other_index} differ"
                )

    def _chiral_spent(self, state) -> bool:
        """Whether both players have already played their ``P3-y``.

        Until then the mirror is not a game symmetry at all (adr-008): the
        chiral tile's reflection is not in the deck, so a mirrored position has
        moves the original does not.
        """
        return all(not (hand >> self.chiral_tile) & 1 for hand in state.hands)

    # -- crash resume (solver/checkpoint.py) ---------------------------------

    def checkpoint_state(self) -> dict:
        """Everything a resumed run needs except the digest.

        The digest is deliberately absent: ``hashlib`` objects cannot be
        serialised, and storing a per-layer digest instead would redefine what
        adr-010 V5 measures halfway through an experiment. It is rebuilt in
        :meth:`restore_checkpoint` from the layers themselves.

        The RNG state travels so that a resumed run draws the *same* V4 and V6
        samples the uninterrupted run would have drawn. Without it a resume
        would silently re-seed the sampling, and the two arms would no longer be
        comparable on evidence that the registry pins by seed.
        """
        version, internal, gauss = self.rng.getstate()
        return {
            "rng": [version, list(internal), gauss],
            "layer_counts": {str(k): v for k, v in self.layer_counts.items()},
            "v1_problems": list(self.v1_problems),
            "v4_samples": [list(s) for s in self.v4_samples],
            "v6_checked": self.v6_checked,
            "v6_rejected": self.v6_rejected,
            "v6_problems": list(self.v6_problems),
            "v6_rows": {str(k): dict(v) for k, v in self.v6_rows.items()},
        }

    def restore_checkpoint(self, state: dict, checkpoint) -> None:
        """Rebuild the observer, including a byte-identical V5 digest.

        ``checkpoint.replay()`` yields the completed layers in **sweep order**,
        which is the order the digest was fed originally, so the checksum this
        run finally reports is the one an uninterrupted run would have reported.
        That is the whole reason every layer is retained on disk.
        """
        version, internal, gauss = state["rng"]
        self.rng.setstate((version, tuple(internal), gauss))
        self.layer_counts = {int(k): v for k, v in state["layer_counts"].items()}
        self.v1_problems = list(state["v1_problems"])
        self.v4_samples = [tuple(s) for s in state["v4_samples"]]
        self.v6_checked = state["v6_checked"]
        self.v6_rejected = state["v6_rejected"]
        self.v6_problems = list(state["v6_problems"])
        # ``.get`` because a checkpoint written before the coverage revision has
        # no per-layer rows. Such a resume loses the breakdown for the layers it
        # already passed, and the artefact says so via `v6_rows_partial` rather
        # than presenting a hole as a zero.
        self.v6_rows = {int(k): dict(v) for k, v in state.get("v6_rows", {}).items()}
        self.v6_rows_partial = "v6_rows" not in state

        self.digest = hashlib.sha256()
        replayed = []
        for t, values in checkpoint.replay():
            self.digest.update(bytes(values))
            replayed.append(t)
        print(
            f"  resumed: {len(replayed)} layers replayed into the V5 digest "
            f"(t={max(replayed)} down to t={min(replayed)}), "
            f"{len(self.v4_samples)} V4 samples and {self.v6_checked} V6 pairs "
            f"carried over",
            flush=True,
        )
        self._started = self._last = time.perf_counter()


def _mirror_permutation(board) -> tuple[int, ...] | None:
    """The board's non-identity automorphism as a cell permutation, if it has one."""
    identity = tuple(range(board.n_cells))
    for _name, _rho, cell_map in board_automorphisms(board):
        perm = tuple(cell_map[c] for c in range(board.n_cells))
        if perm != identity:
            return perm
    return None


def _mirror_state(state, perm: tuple[int, ...]):
    colours = [Colour.EMPTY] * state.n_cells
    for cell, colour in enumerate(state.colours):
        colours[perm[cell]] = colour
    return type(state).build(tuple(colours), state.hands, state.to_move)


def v6_coverage(checks: Checks, variant: Variant) -> dict:
    """Summarise where the mirror check actually had purchase.

    ``non_trivial`` is the honest pair count: a configuration fixed by the
    reflection is compared with itself and can never disagree, so it is evidence
    of nothing. On the 5×3 the mirror fixes column C, which makes such
    configurations common in sparse layers and rare in full ones.
    """
    rows = checks.v6_rows
    attempts = sum(r["attempts"] for r in rows.values())
    checked = sum(r["checked"] for r in rows.values())
    self_mirror = sum(r["self_mirror"] for r in rows.values())
    return {
        "attempts": attempts,
        "eligible_fraction": checked / attempts if attempts else 0.0,
        "pairs_checked": checked,
        "self_mirror": self_mirror,
        "non_trivial": checked - self_mirror,
        "layers_without_coverage": sorted(
            t for t in range(variant.n_cells + 1) if not rows.get(t, {}).get("checked")
        ),
        "per_layer": {str(t): rows[t] for t in sorted(rows)},
        "rows_partial": checks.v6_rows_partial,
    }


def run_v4(variant: Variant, checks: Checks, budget: int) -> dict:
    """Re-derive sampled values by forward search, never consulting the sweep.

    Reports **where** it succeeded, not just how often. The 2026-08-09 registry
    amendment asked V4 to publish a coverage figure; measuring it exposed two
    further things the aggregate had been hiding.

    *Terminal samples were being dropped in silence.* The old loop skipped them
    with a bare ``continue``, so they left no trace in any counter — 40 of the
    601 draws on the h2 arm, which is why that run's `agreed + unaffordable`
    fell 40 short of its own sample size and nothing said so. They are now
    re-derived instead. This is cheap and it is not circular: the sweep decides
    a terminal layer by counting set bits in a packed integer and taking the
    mover from layer parity, while this path decodes a ``GameState`` and asks
    ``fliphex.rules.winner``. A parity or colour-orientation error in either
    would show up here. The evidence is weaker than a search — it exercises no
    move generation — so it is counted separately and never folded into
    ``agreed``.

    *Coverage is not uniform, and the shape is the finding.* Search cost grows
    with empty cells, so V4 buys the endgame and thins out going up. An
    aggregate percentage hides that completely; ``shallowest_layer_searched``
    is the number that says what the gate actually witnessed.
    """
    board = variant.board()
    rows: dict[int, dict[str, int]] = {}
    problems: list[str] = []

    def row(t: int) -> dict[str, int]:
        return rows.setdefault(
            t,
            {
                "sampled": 0,
                "agreed": 0,
                "disagreed": 0,
                "unaffordable": 0,
                "terminal_agreed": 0,
                "terminal_disagreed": 0,
            },
        )

    for t, index, slot in checks.v4_samples:
        here = row(t)
        here["sampled"] += 1
        state = LayerIndex(variant, t).decode(index)

        if state.is_terminal():
            expected = (
                SLOT_WIN if terminal_winner(state) == state.to_move else SLOT_LOSS
            )
            if expected == slot:
                here["terminal_agreed"] += 1
            else:
                here["terminal_disagreed"] += 1
                problems.append(
                    f"layer {t} index {index} (terminal): sweep {slot}, "
                    f"rules {expected}"
                )
            continue

        try:
            forward = Solver(
                board, tt=TranspositionTable(1 << 16), max_nodes=budget
            ).solve(state)
        except BudgetExceededError:
            here["unaffordable"] += 1
            continue
        expected = SLOT_WIN if forward.value == WIN else SLOT_LOSS
        if expected == slot:
            here["agreed"] += 1
        else:
            here["disagreed"] += 1
            problems.append(
                f"layer {t} index {index}: sweep {slot}, forward {expected}"
            )

    def total(key: str) -> int:
        return sum(r[key] for r in rows.values())

    drawn = total("sampled")
    searched = total("agreed") + total("disagreed")
    at_terminal = total("terminal_agreed") + total("terminal_disagreed")
    searchable = drawn - at_terminal
    layers_searched = sorted(
        t for t, r in rows.items() if r["agreed"] or r["disagreed"]
    )
    blind = sorted(
        t
        for t, r in rows.items()
        if r["sampled"] and not (r["agreed"] or r["disagreed"] or r["terminal_agreed"])
    )

    return {
        "agreed": total("agreed"),
        "disagreed": total("disagreed"),
        "unaffordable": total("unaffordable"),
        "terminal_agreed": total("terminal_agreed"),
        "terminal_disagreed": total("terminal_disagreed"),
        "node_budget": budget,
        "passed": total("disagreed") == 0
        and total("terminal_disagreed") == 0
        and total("agreed") > 0,
        "problems": problems[:20],
        "coverage": {
            # Denominator is every sample DRAWN. The 2026-08-09 amendment quoted
            # 61.3% against the non-terminal count, which flattered the gate by
            # excluding the samples it was silently discarding.
            "samples_drawn": drawn,
            "verified": searched + at_terminal,
            "verified_fraction": (searched + at_terminal) / drawn if drawn else 0.0,
            "search_fraction": searched / searchable if searchable else 0.0,
            "layers_searched": layers_searched,
            "shallowest_layer_searched": layers_searched[0]
            if layers_searched
            else None,
            "layers_without_evidence": blind,
            "per_layer": {str(t): rows[t] for t in sorted(rows)},
        },
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--arm", choices=["h1", "h2"], default="h1")
    p.add_argument(
        "--board", type=int, nargs=2, default=(5, 3), metavar=("COLS", "ROWS")
    )
    p.add_argument("--bits", type=int, choices=(2, 8), default=2)
    p.add_argument("--seed", type=int, default=3, help="sampling seed (registered: 3)")
    p.add_argument("--v4-per-layer", type=int, default=40)
    p.add_argument("--v6-per-layer", type=int, default=40)
    p.add_argument("--v4-budget", type=int, default=2_000_000)
    p.add_argument("--out", type=Path, default=Path("data/subgame-solutions"))
    p.add_argument("--no-write", action="store_true")
    p.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("data/checkpoints"),
        help=(
            "directory for crash-resume layers; an existing checkpoint for this "
            "variant is RESUMED, not overwritten. ~4.4 GB for the 5x3. "
            "Pass --no-checkpoint to disable."
        ),
    )
    p.add_argument(
        "--no-checkpoint",
        dest="checkpoint",
        action="store_const",
        const=None,
        help="run without crash resume (the pre-2026-08-12 behaviour)",
    )
    args = p.parse_args()

    variant = Variant(args.board[0], args.board[1], Arm(args.arm))
    board = variant.board()
    hands = "+".join(str(len(h)) for h in variant.deck_names())
    total = sum(
        closed_form_layer(variant.n_cells, *(len(h) for h in variant.deck_names()), t)
        for t in range(variant.n_cells + 1)
    )

    print(f"  === EXP-002 — {variant.name}, {variant.n_cells} cells, hands {hands} ===")
    print(f"  {total:,} configurations, {args.bits} bits/entry, seed {args.seed}")
    print(
        f"  interpreter: {sys.implementation.name} {sys.version.split()[0]}",
        flush=True,
    )

    checks = Checks(variant, args.v4_per_layer, args.v6_per_layer, args.seed)
    ckpt = None
    resumed_from = None
    if args.checkpoint is not None:
        ckpt = Checkpoint(args.checkpoint / variant.name)
        resumed_from = ckpt.resume_point()
        if resumed_from is None:
            print(f"  checkpoint: {ckpt.root} (fresh start)", flush=True)
        else:
            print(
                f"  checkpoint: {ckpt.root} — RESUMING, layer {resumed_from} is on "
                f"disk, the sweep restarts at layer {resumed_from - 1}",
                flush=True,
            )

    started = time.perf_counter()
    result = PackedSweep(variant, board, args.bits).sweep(
        observer=checks, checkpoint=ckpt
    )
    sweep_seconds = time.perf_counter() - started
    if resumed_from is not None:
        # A resumed run cannot report a rate: the earlier session's time died
        # with the process, and the layers differ in cost by an order of
        # magnitude, so the two pieces are not addable into anything meaningful.
        print(f"  sweep done — {sweep_seconds / 3600:.2f} h in THIS session only")
        print("  (resumed run: total elapsed is not recoverable, no cfg/s reported)")
    else:
        print(
            f"  sweep done in {sweep_seconds / 3600:.2f} h "
            f"({total / sweep_seconds:,.0f} cfg/s)"
        )

    print("  V4 — re-deriving sampled positions by forward search ...", flush=True)
    v4 = run_v4(variant, checks, args.v4_budget)

    terminal = checks.layer_counts[variant.n_cells]
    v0_ok = terminal == 2**variant.n_cells
    checksum = checks.digest.hexdigest()
    who = "P1" if result.value == WIN else "P2"

    print()
    print(f"    VALUE ................. {who} wins with perfect play")
    print(f"    V0 terminal layer ..... {terminal:,} ({'ok' if v0_ok else 'MISMATCH'})")
    print(f"    V1 per-layer counts ... {'ok' if not checks.v1_problems else 'FAILED'}")
    for problem in checks.v1_problems:
        print(f"       {problem}")
    print("    V2 no-draw ............ asserted on every terminal")
    cov = v4["coverage"]
    print(
        f"    V4 sampled re-derive .. {v4['agreed']:,} agree, "
        f"{v4['disagreed']} disagree, {v4['unaffordable']} over budget, "
        f"{v4['terminal_agreed']} terminal"
    )
    print(
        f"       coverage ........... {cov['verified']:,} of "
        f"{cov['samples_drawn']:,} drawn ({100 * cov['verified_fraction']:.1f}%); "
        f"search reached {100 * cov['search_fraction']:.1f}% of the rest"
    )
    shallowest = cov["shallowest_layer_searched"]
    if shallowest is None:
        print("       searched layers .... NONE — V4 witnessed no search evidence")
    else:
        print(
            f"       searched layers .... {len(cov['layers_searched'])} of "
            f"{variant.n_cells + 1}, shallowest t = {shallowest}"
        )
    if cov["layers_without_evidence"]:
        print(
            "       no evidence at ..... t = "
            + ", ".join(str(t) for t in cov["layers_without_evidence"])
        )
    for problem in v4["problems"][:5]:
        print(f"       {problem}")
    print(f"    V5 checksum ........... {checksum[:16]}...")
    if checks.mirror is None:
        print("    V6 mirror ............. N/A — this board has no reflection")
    else:
        v6_cov = v6_coverage(checks, variant)
        print(
            f"    V6 mirror ............. {checks.v6_checked:,} eligible pairs "
            f"checked, {len(checks.v6_problems)} differ "
            f"({checks.v6_rejected:,} sampled but ineligible — P3-y still in hand)"
        )
        print(
            f"       eligibility ........ {100 * v6_cov['eligible_fraction']:.1f}% "
            f"of {v6_cov['attempts']:,} draws"
        )
        print(
            f"       non-trivial pairs .. {v6_cov['non_trivial']:,} "
            f"({v6_cov['self_mirror']:,} were mirror-fixed, comparing a value "
            f"with itself)"
        )
        if v6_cov["layers_without_coverage"]:
            print(
                "       no coverage at ..... t = "
                + ", ".join(str(t) for t in v6_cov["layers_without_coverage"])
            )
        if checks.v6_rows_partial:
            print(
                "       (per-layer rows are partial — resumed from an old checkpoint)"
            )
    for problem in checks.v6_problems[:5]:
        print(f"       {problem}")

    passed = (
        v0_ok and not checks.v1_problems and v4["passed"] and not checks.v6_problems
    )
    print()
    print(
        f"  {variant.name}: {who} wins — "
        f"{'ALL CHECKS PASSED' if passed else 'CHECKS FAILED'}"
    )
    print()
    print("  adr-009: a reduced-board result transfers to the shipped 5x5 as")
    print("  evidence, never as proof. Report it with its board and deck.")

    artefact = {
        "experiment": "EXP-002",
        "variant": variant.name,
        "board": list(args.board),
        "cells": variant.n_cells,
        "hands": [list(h) for h in variant.deck_names()],
        "configurations": total,
        "value": who,
        "ordering": "internal",
        "termination": "exhausted",
        "bits_per_entry": args.bits,
        "interpreter": f"{sys.implementation.name} {sys.version.split()[0]}",
        "seed": args.seed,
        # On a resumed run this is THIS SESSION only. The earlier session's
        # elapsed time died with its process and is not recoverable, so the two
        # are not addable — `resumed_from_layer` is what says the figure is
        # partial, and it must travel with any timing claim made from it.
        "seconds": sweep_seconds,
        "resumed_from_layer": resumed_from,
        "verification": {
            "V0_terminal_layer": {"count": terminal, "passed": v0_ok},
            "V1_layer_counts": {
                "passed": not checks.v1_problems,
                "problems": checks.v1_problems,
            },
            "V2_no_draw": {"passed": True, "mode": "asserted on every terminal"},
            "V4_sampled_rederivation": v4,
            "V5_checksum_sha256": checksum,
            "V6_mirror": {
                "applicable": checks.mirror is not None,
                "pairs_checked": checks.v6_checked,
                "sampled_but_ineligible": checks.v6_rejected,
                "problems": checks.v6_problems[:20],
                "passed": not checks.v6_problems,
                "coverage": (
                    v6_coverage(checks, variant) if checks.mirror is not None else None
                ),
            },
        },
        "layer_counts": dict(sorted(checks.layer_counts.items())),
        "passed": passed,
    }

    if not args.no_write:
        args.out.mkdir(parents=True, exist_ok=True)
        path = args.out / f"{variant.name}.json"
        path.write_text(json.dumps(artefact, indent=2))
        print(f"  artefact -> {path}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
