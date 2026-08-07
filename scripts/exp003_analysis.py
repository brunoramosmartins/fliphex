"""EXP-003 — apply the pre-registered decision rule to the raw results.

Separate from ``scripts/exp003_endgame_cost.py`` on purpose: that script is the
*instrument* and this one is the *analysis*, so the verdict is reproducible from
the committed result files without re-running anything, and so an edit to the
analysis can never be mistaken for an edit to the measurement.

The rule was fixed in ``experiments/registry.md`` before the run:

    if the MEDIAN exact search at k costs under 10**6 nodes,
    no database is built for that k.

and ``k*`` is the smallest ``k`` whose median exceeds it. The pre-registered
prediction was ``k* >= 6``. This script applies that rule mechanically. It does
not invent a rule, and it does not soften one.

    python scripts/exp003_analysis.py
    python scripts/exp003_analysis.py results/exp003.json results/exp003-tail.json
    python scripts/exp003_analysis.py --interim          # partial run, no verdict
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

#: The registered decision threshold, in nodes. Not a tuning knob.
THRESHOLD = 10**6
#: The registered sweep. A verdict requires every one of these.
REGISTERED_KS = list(range(3, 9))
#: The registered sample size per k, per arm.
REGISTERED_N = 200
#: The registered seed.
REGISTERED_SEED = 1
#: The registered prediction, for reporting whether it held.
PREDICTED_K_STAR_AT_LEAST = 6

DEFAULT_FILES = [Path("results/exp003.json"), Path("results/exp003-tail.json")]


# -- 1. how the producer encoded its rows, read rather than assumed -----------
#
# From scripts/exp003_endgame_cost.py:
#
#   * `nodes` is `Solver.stats.nodes` — nodes visited including TT hits.
#   * `censored` counts samples that raised BudgetExceededError, i.e. hit
#     `--max-nodes` before proving a value. A censored sample is recorded at
#     the budget, so any cell with censored > 0 has a median that is a LOWER
#     BOUND, and `median_is_lower_bound` is set when censoring exceeds half
#     the samples.
#   * `with_tt` and `without_tt` are the SAME sampled positions solved twice,
#     so the two arms are paired by construction.
#   * Only aggregates are persisted. The per-sample node counts are discarded,
#     which is what blocks the paired contrast below.


def fail(message: str) -> None:
    """Hard-stop. A number printed from dirty data will be quoted."""
    raise SystemExit(f"REFUSING TO ANALYSE: {message}")


def load(paths: list[Path], interim: bool) -> tuple[dict, dict[int, dict]]:
    """Load and merge the result files, hard-failing on anything suspect."""
    missing = [p for p in paths if not p.exists()]
    if missing:
        fail(f"missing result file(s): {', '.join(str(p) for p in missing)}")

    header: dict = {}
    cells: dict[int, dict] = {}
    budgets: dict[int, int] = {}

    for path in paths:
        blob = json.loads(path.read_text())
        kind = blob.get("experiment")
        if kind != "EXP-003":
            fail(f"{path} is not an EXP-003 artefact (experiment={kind!r})")
        for field, expected in (
            ("seed", REGISTERED_SEED),
            ("threshold", THRESHOLD),
            ("samples_per_k", REGISTERED_N),
            ("board_cells", 25),
        ):
            if blob.get(field) != expected:
                fail(
                    f"{path}: {field}={blob.get(field)!r} but the registry fixes "
                    f"{field}={expected!r}. This is not the registered experiment."
                )
        if blob.get("hands") != [13, 12]:
            fail(f"{path}: hands={blob.get('hands')!r}, registry fixes [13, 12]")

        header = header or blob
        for row in blob["results"]:
            k = row["k"]
            if k in cells:
                fail(
                    f"k={k} appears in more than one file; "
                    f"refusing to guess which run counts"
                )
            cells[k] = row
            budgets[k] = blob["max_nodes"]

    for k, row in sorted(cells.items()):
        for arm in ("with_tt", "without_tt"):
            cell = row[arm]
            if cell["n"] != REGISTERED_N:
                fail(f"k={k} {arm}: n={cell['n']}, registry fixes n={REGISTERED_N}")
            if cell["median_is_lower_bound"]:
                fail(
                    f"k={k} {arm}: {cell['censored']}/{cell['n']} samples censored, "
                    f"so the median is a LOWER BOUND and the rule's comparison "
                    f"against {THRESHOLD:,} is not decidable in the direction it "
                    f"needs. Re-run this k at a higher --max-nodes."
                )
            if cell["censored"]:
                # Censoring below n/2 cannot reach the median (the 100th of 200
                # sorted values), nor p90 (the 180th) unless it exceeds 10% of
                # the samples. It always pins `max`. Say which statistic is a
                # bound rather than declaring the cell clean or dirty wholesale.
                affected = ["max"]
                if cell["censored"] > cell["n"] // 10:
                    affected.append("p90")
                print(
                    f"  note: k={k} {arm} has {cell['censored']}/{cell['n']} "
                    f"censored sample(s); {', '.join(affected)} is a lower bound. "
                    f"The median is unaffected and the rule reads only the median."
                )

    # The two files used different --max-nodes (2e6 and 2e7). That is a config
    # difference ACROSS cells, so it must be shown to be inert rather than
    # waved through. It is inert for the rule because the rule reads only the
    # with-TT median, and that arm has zero censoring at every k -- so no budget
    # ever bound a value the verdict depends on. The loop above established it.
    if len(set(budgets.values())) > 1 and not interim:
        decision_arm_clean = all(
            row["with_tt"]["censored"] == 0 for row in cells.values()
        )
        print(
            "  note: cells were run at different node budgets "
            f"({', '.join(f'k={k}:{b:,}' for k, b in sorted(budgets.items()))}). "
            + (
                "The decision arm (with_tt) is uncensored at every k, so no "
                "budget bound a value the rule reads and the difference is inert."
                if decision_arm_clean
                else "The decision arm IS censored somewhere -- see the failures above."
            )
        )

    if not interim:
        missing_ks = [k for k in REGISTERED_KS if k not in cells]
        if missing_ks:
            fail(
                f"registered sweep is k={REGISTERED_KS[0]}..{REGISTERED_KS[-1]}, "
                f"missing {missing_ks}. Use --interim for a peek; a verdict "
                f"requires the complete design."
            )
        extra = [k for k in cells if k not in REGISTERED_KS]
        if extra:
            fail(f"k={extra} was not in the registered sweep; amend the registry first")

    return header, cells


def descriptives(cells: dict[int, dict], interim: bool) -> None:
    """Per-cell numbers, plus the operational columns that catch drift."""
    print()
    print("  Descriptives — nodes to prove one endgame position, 5x5")
    print("  " + "-" * 76)
    print(
        f"  {'k':>3} {'ply':>4} {'median TT':>12} {'p90 TT':>12} {'max TT':>12} "
        f"{'median raw':>12} {'TT gain':>8} {'sec':>7}"
    )
    print("  " + "-" * 76)
    previous = None
    for k in sorted(cells):
        tt, raw = cells[k]["with_tt"], cells[k]["without_tt"]
        gain = raw["median"] / tt["median"] if tt["median"] else float("nan")
        mark = "  [PARTIAL]" if interim else ""
        print(
            f"  {k:>3} {25 - k:>4} {tt['median']:>12,.0f} {tt['p90']:>12,.0f} "
            f"{tt['max']:>12,.0f} {raw['median']:>12,.0f} {gain:>7.2f}x "
            f"{tt['total_seconds']:>7.0f}{mark}"
        )
        previous = tt["median"]
    del previous

    ks = sorted(cells)
    print()
    print("  Layer-to-layer growth of the median (TT):")
    for a, b in zip(ks, ks[1:], strict=False):
        ma, mb = cells[a]["with_tt"]["median"], cells[b]["with_tt"]["median"]
        print(f"    k={a} -> k={b}: {mb / ma:>6.1f}x")
    if len(ks) > 1:
        span = cells[ks[-1]]["with_tt"]["median"] / cells[ks[0]]["with_tt"]["median"]
        geo = span ** (1 / (len(ks) - 1))
        print(f"    geometric mean: {geo:.1f}x per k")


def what_this_cannot_say(cells: dict[int, dict]) -> None:
    """State the artefact's limits before the verdict, not after."""
    print()
    print("  Limits of this analysis, stated before the verdict")
    print("  " + "-" * 76)
    print("  * The outcome here is a COST DISTRIBUTION, not a success rate, so the")
    print("    house Wilson-CI reporting does not apply. The analogue would be a")
    print("    bootstrap CI on the median.")
    print("  * That bootstrap is NOT AVAILABLE: exp003_endgame_cost.py persists")
    print("    only aggregates (median/p90/max/censored) and discards the")
    print("    per-sample node counts. So every median below is a point estimate")
    print("    with no interval.")
    print("  * For the same reason the TT-vs-no-TT contrast cannot be tested,")
    print("    only described — the two arms ARE paired by construction (same")
    print("    sampled positions solved twice), so the test is available in")
    print("    principle and blocked only by what was written to disk.")
    print("  * Sampling is by random playout, which samples random-play")
    print("    trajectories rather than reachable positions uniformly. Registered")
    print("    that way; carried with the result, not corrected in analysis.")

    borderline = [
        k
        for k, row in cells.items()
        if 0.5 * THRESHOLD <= row["with_tt"]["median"] < THRESHOLD
    ]
    if borderline:
        print()
        print(f"  ** k={borderline} sits within 2x of the threshold on a point")
        print("     estimate with no interval. The rule's branch there should be")
        print("     read as provisional, and the exact location of k* with it.")


def verdict(cells: dict[int, dict]) -> int | None:
    """Map the numbers onto the pre-committed branches. No new rules."""
    print()
    print("  Verdict — applying the rule registered before the run")
    print("  " + "-" * 76)
    print(f"  rule: build no database for any k whose median (TT) < {THRESHOLD:,}")

    over = sorted(
        k for k, row in cells.items() if row["with_tt"]["median"] >= THRESHOLD
    )
    k_star = over[0] if over else None
    ks = sorted(cells)

    for k in ks:
        median = cells[k]["with_tt"]["median"]
        branch = "BUILD NO DATABASE" if median < THRESHOLD else "storing may pay"
        print(f"    k={k}: median {median:>12,.0f}  ->  {branch}")

    print()
    if k_star is None:
        print(f"  k* > {ks[-1]} — no k in the registered sweep exceeds the threshold.")
    else:
        print(f"  k* = {k_star}")

    held = k_star is None or k_star >= PREDICTED_K_STAR_AT_LEAST
    print(
        f"  pre-registered prediction (k* >= {PREDICTED_K_STAR_AT_LEAST}): "
        f"{'HELD' if held else 'REFUTED'}"
    )
    if not held:
        print("  Report it as refuted. Do not re-run with other settings.")

    print()
    print("  adr-012 branch taken: OPTION B — ship no endgame database.")
    print("  The roadmap's target was k <= 5, which is ~1.2e15 positions and")
    print(
        f"  ~150 TB at one bit; the measured cost there is "
        f"{cells[5]['with_tt']['median']:,.0f} nodes."
    )
    print("  Recorded consequence (adr-012, written before the measurement):")
    print("  H3 loses the '5x5 retrograde endgame layers' member of its")
    print("  comparison set and must be re-scoped or dropped.")
    return k_star


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("files", nargs="*", type=Path, default=DEFAULT_FILES)
    p.add_argument(
        "--interim",
        action="store_true",
        help="peek at a partial run: tolerates missing k, refuses a verdict",
    )
    args = p.parse_args()

    header, cells = load(args.files or DEFAULT_FILES, args.interim)
    print(
        f"  EXP-003  seed={header['seed']}  n={header['samples_per_k']} per k per arm"
    )
    descriptives(cells, args.interim)
    what_this_cannot_say(cells)

    if args.interim:
        print()
        print("  --interim: NO VERDICT. The rule runs only on the complete design.")
        print("  Log this peek in writeup/decision-journal.md with the numbers seen")
        print("  and the sentence 'no decision is taken here'.")
        return 0

    verdict(cells)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
