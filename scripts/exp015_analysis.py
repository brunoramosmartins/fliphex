"""EXP-015 analysis: apply the registered floor to the saved artefact.

Registered in ``experiments/registry.md`` on 2026-09-04, which names this file
before it existed. The run instrument prints a verdict as each seed lands; this
exists so the verdict is reproducible from the result file rather than from a
~146-hour run, and — more usefully — so the registered rule is applied by code
that did not produce the numbers. Every interval below is **recomputed** and
cross-checked against what the run stored; a disagreement is a hard failure,
because one of the two paths is then wrong and the summary cannot say which.

Nothing here imports ``az`` or torch. The analysis must run from the artefact
alone, on a machine that never trained anything, or "reproducible from the raw
result file" means nothing.

The registered rule
-------------------
**Primary — equal simulations.** Champion against prior-free UCT, both at 400
simulations, 200 games, seats alternating, per seed. **Every seed's Wilson 95%
interval must lie entirely above 50%.** Not a margin: a margin would turn a floor
into a strength claim.

The wording understates the bar and this script recomputes by how much — the
smallest win count out of 200 whose interval clears 50% is printed rather than
quoted from the registration.

**Stability, made falsifiable.** H3's clause 1 says "stable across seeds" and its
measurement column says "variance reported", which alone is unfalsifiable. So:
**a seed that fails the floor is recorded as instability and is never averaged
away.** The five rates and their spread go in the output whatever happens.

**Secondary — equal time.** Reported, quoted in the write-up, and gating nothing.
Its difficulty is *not* constant across seeds: the simulation budget UCT receives
is measured per seed against whatever the machine was doing at the time, so the
per-seed budgets are printed beside the rates.

**Reference — generation 0.** Where the seed started. Nothing branches on it.

What this script refuses to do
------------------------------
**Cross-seed quantities before all five seeds exist.** H3's clause 1 is about
stability, and the mean or spread of an incomplete set satisfies nothing. Until
the artefact holds five seeds this prints per-seed rows and stops. The single
registered exception is the seed-1 go/no-go, which is a *floor-only* check on
that seed alone and is already applied by the instrument.

Note a small leak in the instrument, recorded rather than patched mid-run:
``exp015_h3_run.py::summarise`` prints the running spread from two seeds onward.
It is a print, it gates nothing, and editing an instrument between seeds is worse
than noting it. This script is the authority on cross-seed reads.

The durable history
-------------------
Each seed's per-generation record lives at ``data/az-runs/h3-seed<N>/history.jsonl``,
which is **gitignored** — so the training curve, the gate outcomes and the
off-policy ``refresh_fraction`` that the registration promised to report were not
in the repository at all. This script consolidates them into a tracked
``results/exp015-histories.json``. A completed seed's rows are immutable: if the
snapshot and the live file disagree on a seed that already has all 30
generations, that is a hard failure, not a refresh.

Usage::

    .venv/bin/python scripts/exp015_analysis.py
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import textwrap
from pathlib import Path

# -- restated from the registration, so an artefact produced under a different
# -- configuration fails loudly rather than being analysed as if it matched.

SEEDS = (1, 2, 3, 4, 5)
GENERATIONS = 30
GAMES = 200
SIMULATIONS = 400
BUFFER_CAPACITY = 20_000
GATE_EVERY = 5
GATE_GAMES = 400
GATE_THRESHOLD = 0.55
FLOOR_GAMES = 200

#: 25 cells, filled every game, so a generation is exactly 200 x 25 samples.
#: Draws are impossible on an odd cell count, so no game ends early.
SAMPLES_PER_GENERATION = GAMES * 25

FLOORS = ("equal_simulations", "generation_0", "equal_time")
PRIMARY = "equal_simulations"

#: chi-square 0.95 quantile at 4 degrees of freedom, for the homogeneity
#: diagnostic. A constant so this file needs no scipy.
CHI2_CRIT_DF4 = 9.488


# --------------------------------------------------------------------------
# Statistics. Reimplemented rather than imported from ``az.gate``: this script
# exists to check that code, and a shared implementation would agree with
# itself no matter what it computed.
# --------------------------------------------------------------------------


def say(text: str, indent: str = "  ") -> None:
    """Print a prose paragraph wrapped to the width the tables are built for."""
    print(
        textwrap.fill(
            " ".join(text.split()),
            width=88,
            initial_indent=indent,
            subsequent_indent=indent,
        )
    )


def wilson(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def smallest_clearing(n: int) -> int:
    """Smallest win count out of ``n`` whose Wilson interval clears 50%.

    The registration says the effective bar is "around 58%", which is a
    quotation. This computes it.
    """
    for wins in range(n + 1):
        if wilson(wins, n)[0] > 0.5:
            return wins
    return n + 1


def binomial_tail(n: int, p: float, k: int) -> float:
    """``P(X >= k)`` for ``X ~ Binomial(n, p)``."""
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))


def wins_needed(n: int, threshold: float) -> int:
    needed = int(n * threshold)
    while needed / n < threshold:
        needed += 1
    return needed


def homogeneity(wins: list[int], n: int) -> dict:
    """Are the per-seed rates consistent with one underlying win rate?

    A descriptive diagnostic that **gates nothing**. The registered criterion is
    per-seed and deliberately so: a chi-square can pass while a seed sits below
    50%, and the whole point of the stability clause is that such a seed is not
    averaged away. This is reported because "variance reported" needs something
    to compare the variance *to*.
    """
    pooled = sum(wins) / (len(wins) * n)
    expected = pooled * n
    if expected in (0.0, float(n)):
        return {"degenerate": True}
    chi2 = sum(
        (w - expected) ** 2 / expected
        + ((n - w) - (n - expected)) ** 2 / (n - expected)
        for w in wins
    )
    rates = [w / n for w in wins]
    return {
        "degenerate": False,
        "pooled": pooled,
        "chi2": chi2,
        "df": len(wins) - 1,
        "critical": CHI2_CRIT_DF4,
        "heterogeneous": chi2 > CHI2_CRIT_DF4,
        "observed_sd": statistics.stdev(rates),
        "binomial_sd": math.sqrt(pooled * (1 - pooled) / n),
    }


# --------------------------------------------------------------------------
# Validity guards. Nothing is printed before these pass.
# --------------------------------------------------------------------------


def guard_artefact(artefact: dict) -> list[int]:
    if artefact.get("experiment") != "EXP-015":
        raise SystemExit(f"not an EXP-015 artefact: {artefact.get('experiment')!r}")

    schedule = artefact.get("schedule", {})
    expected = {
        "seeds": list(SEEDS),
        "generations": GENERATIONS,
        "games": GAMES,
        "simulations": SIMULATIONS,
        "buffer_capacity": BUFFER_CAPACITY,
        "gate_every": GATE_EVERY,
        "gate_games": GATE_GAMES,
        "gate_threshold": GATE_THRESHOLD,
        "floor_games": FLOOR_GAMES,
    }
    for key, want in expected.items():
        if schedule.get(key) != want:
            raise SystemExit(
                f"schedule.{key} is {schedule.get(key)!r}, registered as {want!r}; "
                "this artefact was produced under a different configuration"
            )

    present = sorted(int(s) for s in artefact.get("seeds", {}))
    if not present:
        raise SystemExit("the artefact holds no seeds")
    unknown = [s for s in present if s not in SEEDS]
    if unknown:
        raise SystemExit(f"unregistered seeds in the artefact: {unknown}")

    for seed in present:
        entry = artefact["seeds"][str(seed)]
        floors = entry.get("floors", {})
        for name in FLOORS:
            if name not in floors:
                # A seed mid-flight is not a defect; a seed claiming a verdict
                # without its matches is.
                continue
            guard_match(seed, name, floors[name])
        if PRIMARY in floors and "equal_time" in floors:
            budget = entry.get("equal_time_budget")
            if not budget:
                raise SystemExit(
                    f"seed {seed} has an equal-time match with no recorded budget; "
                    "the ratio must be measured before the match, not inferred"
                )
            if floors["equal_time"]["uct_simulations"] != budget["uct_simulations"]:
                raise SystemExit(
                    f"seed {seed}: the equal-time match ran at "
                    f"{floors['equal_time']['uct_simulations']} simulations but the "
                    f"budget recorded {budget['uct_simulations']}"
                )
    return present


def guard_match(seed: int, name: str, match: dict) -> None:
    where = f"seed {seed} floor {name}"
    if match["games"] != FLOOR_GAMES:
        raise SystemExit(f"{where}: {match['games']} games, registered {FLOOR_GAMES}")
    if match["as_first"] + match["as_second"] != match["wins"]:
        raise SystemExit(
            f"{where}: seat split {match['as_first']}/{match['as_second']} does not "
            f"sum to {match['wins']} wins"
        )
    if abs(match["wins"] / match["games"] - match["win_rate"]) > 1e-12:
        raise SystemExit(
            f"{where}: stored win_rate {match['win_rate']} is not "
            f"{match['wins']}/{match['games']}"
        )
    if match["net_simulations"] != SIMULATIONS:
        raise SystemExit(
            f"{where}: the network played at {match['net_simulations']} simulations, "
            f"registered {SIMULATIONS}"
        )
    if name != "equal_time" and match["uct_simulations"] != SIMULATIONS:
        raise SystemExit(
            f"{where}: an equal-simulations match gave UCT "
            f"{match['uct_simulations']} simulations"
        )

    low, high = wilson(match["wins"], match["games"])
    for stored, recomputed, label in (
        (match["ci"][0], low, "lower"),
        (match["ci"][1], high, "upper"),
    ):
        if abs(stored - recomputed) > 1e-12:
            raise SystemExit(
                f"{where}: stored {label} limit {stored} != recomputed {recomputed}"
            )
    if match["clears_floor"] != (low > 0.5):
        raise SystemExit(
            f"{where}: stored clears_floor={match['clears_floor']} contradicts its "
            f"own interval [{low:.4f}, {high:.4f}]"
        )


def guard_history(seed: int, rows: list[dict]) -> None:
    where = f"seed {seed} history"
    if len(rows) > GENERATIONS:
        raise SystemExit(f"{where}: {len(rows)} rows, registered {GENERATIONS}")
    if [r["generation"] for r in rows] != list(range(len(rows))):
        raise SystemExit(f"{where}: generations are not 0..{len(rows) - 1} in order")
    for row in rows:
        if row["samples"] != SAMPLES_PER_GENERATION:
            raise SystemExit(
                f"{where} gen {row['generation']}: {row['samples']} samples, "
                f"expected {SAMPLES_PER_GENERATION} (200 games x 25 plies, and "
                "every game fills the board)"
            )
        gated = (row["generation"] + 1) % GATE_EVERY == 0
        if row["gated"] != gated:
            raise SystemExit(
                f"{where} gen {row['generation']}: gated={row['gated']} but the "
                f"schedule gates every {GATE_EVERY} generations"
            )
        if row["gated"]:
            rate, (low, high) = row["gate_win_rate"], row["gate_ci"]
            wins = round(rate * GATE_GAMES)
            if abs(wins / GATE_GAMES - rate) > 1e-9:
                raise SystemExit(
                    f"{where} gen {row['generation']}: gate rate {rate} is not a "
                    f"whole number of wins out of {GATE_GAMES}"
                )
            if row["gate_as_first"] + row["gate_as_second"] != wins:
                raise SystemExit(
                    f"{where} gen {row['generation']}: gate seat split does not sum "
                    f"to {wins} wins"
                )
            if row["promoted"] != (rate >= GATE_THRESHOLD):
                raise SystemExit(
                    f"{where} gen {row['generation']}: promoted={row['promoted']} "
                    f"contradicts rate {rate} against threshold {GATE_THRESHOLD}"
                )
            recomputed = wilson(wins, GATE_GAMES)
            if abs(recomputed[0] - low) > 1e-9 or abs(recomputed[1] - high) > 1e-9:
                raise SystemExit(
                    f"{where} gen {row['generation']}: stored gate interval "
                    f"[{low}, {high}] != recomputed {recomputed}"
                )


# --------------------------------------------------------------------------
# The durable history
# --------------------------------------------------------------------------


def read_live(base: Path, seed: int) -> list[dict] | None:
    """Rows from a seed's JSONL, tolerating a half-written final line.

    A seed may be running while this is read: the loop appends a row per
    generation, and catching it mid-append gives a truncated last line. That is a
    benign race, not corruption, so the last line alone is allowed to fail —
    anything earlier is a real defect and raises.
    """
    path = base / f"h3-seed{seed}" / "history.jsonl"
    if not path.exists():
        return None
    lines = [line for line in path.read_text().splitlines() if line.strip()]
    rows = []
    for index, line in enumerate(lines):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            if index != len(lines) - 1:
                raise SystemExit(
                    f"seed {seed}: history line {index + 1} of {len(lines)} is not "
                    "JSON, and it is not the last line, so this is not a "
                    "mid-append race"
                ) from None
    return rows


def discover(base: Path) -> list[int]:
    """Registered seeds with a run directory on disk.

    Wider than the seeds in the artefact on purpose: a seed's artefact entry is
    written only once its 30 generations finish, so a seed that is *running* — or
    one killed halfway — has a history and no entry. Those are exactly the rows
    the snapshot exists to keep.
    """
    return [seed for seed in SEEDS if (base / f"h3-seed{seed}").is_dir()]


def consolidate(base: Path, snapshot_path: Path, seeds: list[int]) -> dict:
    """Merge the gitignored per-seed histories into one tracked file.

    A completed seed's rows are immutable. If the snapshot and the live file
    disagree on a seed that already holds all 30 generations, something re-ran a
    finished seed and one of the two records is now fiction — so that is a hard
    failure rather than a silent refresh.
    """
    snapshot = {}
    if snapshot_path.exists():
        snapshot = json.loads(snapshot_path.read_text()).get("seeds", {})

    merged, sources = {}, {}
    stored_seeds = {int(k) for k in snapshot if k.isdigit() and int(k) in SEEDS}
    for seed in sorted({*seeds, *discover(base), *stored_seeds}):
        key = str(seed)
        live = read_live(base, seed)
        stored = snapshot.get(key)
        if live is None and stored is None:
            continue
        if live is None:
            merged[key], sources[seed] = stored, "snapshot"
            continue
        guard_history(seed, live)
        if stored is not None and len(stored) == GENERATIONS and stored != live:
            raise SystemExit(
                f"seed {seed}: the tracked snapshot and "
                f"{base / f'h3-seed{seed}' / 'history.jsonl'} disagree on a seed "
                "that was already complete. A finished seed's rows are immutable; "
                "one of the two records is now fiction and this script will not "
                "choose between them."
            )
        merged[key], sources[seed] = live, "live"
    return {"merged": merged, "sources": sources}


def write_snapshot(path: Path, merged: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "experiment": "EXP-015",
                "what": (
                    "Per-generation training records, consolidated from "
                    "data/az-runs/h3-seed<N>/history.jsonl, which is gitignored. "
                    "Written by scripts/exp015_analysis.py. Rows of a completed "
                    "seed are immutable."
                ),
                "generations": GENERATIONS,
                "seeds": merged,
            },
            indent=2,
        )
    )


# --------------------------------------------------------------------------
# Reading one seed
# --------------------------------------------------------------------------


def training_summary(rows: list[dict]) -> dict:
    best = min(rows, key=lambda r: r["policy_loss"])
    gates = [r for r in rows if r["gated"]]
    promotions = [r for r in gates if r["promoted"]]
    tail = rows[-10] if len(rows) >= 10 else rows[0]
    return {
        "generations": len(rows),
        "hours": sum(r["seconds"] for r in rows) / 3600,
        "policy_first": rows[0]["policy_loss"],
        "policy_best": best["policy_loss"],
        "policy_best_generation": best["generation"],
        "policy_last": rows[-1]["policy_loss"],
        "policy_last_ten": tail["policy_loss"] - rows[-1]["policy_loss"],
        "value_first": rows[0]["value_loss"],
        "value_last": rows[-1]["value_loss"],
        "gates": len(gates),
        "promotions": len(promotions),
        "champion_generation": promotions[-1]["generation"] if promotions else None,
        "final_gate_promoted": bool(gates and gates[-1]["promoted"]),
        "refresh_fraction": rows[-1]["refresh_fraction"],
        "gate_rates": [
            (r["generation"], r["gate_win_rate"], r["promoted"]) for r in gates
        ],
    }


def complete(entry: dict) -> bool:
    return all(name in entry.get("floors", {}) for name in FLOORS)


# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artefact", default="results/exp015-h3-training-5x5.json")
    parser.add_argument("--base", default="data/az-runs")
    parser.add_argument("--histories", default="results/exp015-histories.json")
    parser.add_argument(
        "--no-snapshot",
        action="store_true",
        help="read the histories without rewriting the tracked snapshot",
    )
    args = parser.parse_args()

    path = Path(args.artefact)
    if not path.exists():
        raise SystemExit(
            f"artefact not found: {path}\n"
            "Each seed writes its own entry as it completes; if none has, wait."
        )
    artefact = json.loads(path.read_text())
    present = guard_artefact(artefact)

    snapshot_path = Path(args.histories)
    bundle = consolidate(Path(args.base), snapshot_path, present)
    histories = {int(k): v for k, v in bundle["merged"].items()}
    if not args.no_snapshot and histories:
        write_snapshot(snapshot_path, bundle["merged"])

    finished = [s for s in present if complete(artefact["seeds"][str(s)])]
    bar = smallest_clearing(FLOOR_GAMES)
    print(
        f"guards passed: {len(present)} seed(s) in the artefact, "
        f"{len(finished)} with all three floor matches, "
        f"{len(histories)} history file(s) verified"
    )
    if not args.no_snapshot and histories:
        live = sorted(s for s, src in bundle["sources"].items() if src == "live")
        print(f"  histories consolidated into {snapshot_path} (live: {live})")

    # ---- the bar, recomputed ------------------------------------------------
    low, high = wilson(bar, FLOOR_GAMES)
    print("\n== the bar, recomputed rather than quoted ==")
    print(
        f"  at {FLOOR_GAMES} games the smallest clearing count is {bar} = "
        f"{bar / FLOOR_GAMES:.1%}, giving [{low:.1%}, {high:.1%}]"
    )
    below = wilson(bar - 1, FLOOR_GAMES)
    print(
        f"  one win fewer, {bar - 1} = {(bar - 1) / FLOOR_GAMES:.1%}, gives "
        f"[{below[0]:.1%}, {below[1]:.1%}] and FAILS"
    )
    say("'Entirely above 50%' is therefore a ~58% bar, not a 50% one.")

    # ---- per seed -----------------------------------------------------------
    print("\n== per seed: the floor matches ==")
    print(
        f"  {'seed':<5} {'arm':<20} {'wins':>8} {'rate':>7} {'Wilson 95%':>17} "
        f"{'seats':>9} {'UCT':>5}  verdict"
    )
    for seed in present:
        entry = artefact["seeds"][str(seed)]
        for name in FLOORS:
            match = entry["floors"].get(name)
            if match is None:
                print(f"  {seed:<5} {name:<20} {'-- not yet played --':>8}")
                continue
            lo, hi = wilson(match["wins"], match["games"])
            verdict = "CLEARS" if lo > 0.5 else "fails"
            if name == "generation_0":
                verdict += "  (reference; nothing branches on it)"
            print(
                f"  {seed:<5} {name:<20} {match['wins']:>4}/{match['games']:<3} "
                f"{match['win_rate']:>6.1%} [{lo:>6.1%},{hi:>6.1%}] "
                f"{match['as_first']:>4}/{match['as_second']:<4} "
                f"{match['uct_simulations']:>5}  {verdict}"
            )
        print()

    # ---- training -----------------------------------------------------------
    if histories:
        print("== per seed: training, diagnostic and never a gate ==")
        print(
            f"  {'seed':<5} {'gens':>5} {'hours':>6} {'policy loss':>22} "
            f"{'value':>13} {'gates':>7} {'champion':>9}"
        )
        for seed in sorted(histories):
            t = training_summary(histories[seed])
            champion = (
                f"gen {t['champion_generation']}"
                if t["champion_generation"] is not None
                else "gen 0"
            )
            print(
                f"  {seed:<5} {t['generations']:>5} {t['hours']:>6.1f} "
                f"{t['policy_first']:>6.3f} -> {t['policy_last']:<6.3f} "
                f"(best {t['policy_best']:.3f} @ {t['policy_best_generation']:>2}) "
                f"{t['value_first']:>5.3f} -> {t['value_last']:<5.3f} "
                f"{t['promotions']:>3}/{t['gates']:<3} {champion:>9}"
                + (
                    f"  (in flight, {t['generations']}/{GENERATIONS})"
                    if t["generations"] < GENERATIONS
                    else ""
                    if t["final_gate_promoted"]
                    else "  (last gate failed)"
                )
            )
        for seed in sorted(histories):
            t = training_summary(histories[seed])
            trail = "  ".join(
                f"g{g}:{r:.1%}{'+' if p else '-'}" for g, r, p in t["gate_rates"]
            )
            print(f"    seed {seed} gates  {trail}")
        first = training_summary(histories[sorted(histories)[0]])
        print()
        say(
            f"refresh_fraction is {first['refresh_fraction']:.2f} throughout: "
            f"{SAMPLES_PER_GENERATION} samples into a {BUFFER_CAPACITY} buffer, so a "
            f"sample's expected age is {BUFFER_CAPACITY // SAMPLES_PER_GENERATION} "
            "generations. This is the registered off-policy assumption, reported as "
            "promised. It is a steady-state figure computed against capacity, so it "
            "understates the first four generations, while the buffer is still "
            "filling and a generation replaces more of what is actually in it."
        )

    # ---- the equal-time budget ----------------------------------------------
    budgets = [
        (s, artefact["seeds"][str(s)]["equal_time_budget"])
        for s in present
        if "equal_time_budget" in artefact["seeds"][str(s)]
    ]
    if budgets:
        print("\n== the equal-time budget, measured per seed ==")
        for seed, b in budgets:
            print(
                f"  seed {seed}: net {b['net_seconds_per_move']:.3f} s/move, UCT "
                f"{b['uct_seconds_per_move_at_400']:.3f} s/move at 400 -> ratio "
                f"{b['ratio']:.2f}, UCT gets {b['uct_simulations']} simulations"
            )
        counts = [b["uct_simulations"] for _, b in budgets]
        if len(counts) > 1 and min(counts) != max(counts):
            say(
                f"The budgets differ across seeds ({min(counts)}-{max(counts)} "
                "simulations). They are measured against whatever the machine was "
                "doing at the time, so the secondary arm is not a constant-difficulty "
                "bar and its rates are not strictly comparable seed to seed."
            )
        say(
            "The registration predicted UCT would get 'several times' the "
            "simulations here; measured, it gets barely more, because random "
            "playouts run to the end of the game while the network does one forward "
            "pass. The secondary is therefore a much closer comparison than it was "
            "registered to be, which makes it a weaker charge for the network's cost "
            "than intended -- and that is a correction to the registration, not a "
            "result."
        )

    # ---- seats --------------------------------------------------------------
    print("\n== seat splits, recorded and not interpreted ==")
    for seed in present:
        match = artefact["seeds"][str(seed)]["floors"].get(PRIMARY)
        if match is None:
            continue
        half = FLOOR_GAMES // 2
        flo = wilson(match["as_first"], half)
        slo = wilson(match["as_second"], half)
        print(
            f"  seed {seed}: as first {match['as_first']}/{half} = "
            f"{match['as_first'] / half:.1%} [{flo[0]:.1%}, {flo[1]:.1%}], "
            f"as second {match['as_second']}/{half} = "
            f"{match['as_second'] / half:.1%} [{slo[0]:.1%}, {slo[1]:.1%}]"
        )
    say(
        "Large and consistent, and NOT evidence for H1. The two seats are played by "
        "different agents here, so a seat effect is confounded with the champion "
        "being stronger than prior-free UCT by a different amount in one role than "
        "in the other. H1 is measured in Phase 5 under a matched protocol."
    )

    # ---- cross-seed, only when the set is complete --------------------------
    print("\n== stability, H3 clause 1 ==")
    if len(finished) < len(SEEDS):
        missing = [s for s in SEEDS if s not in finished]
        say(
            f"REFUSED: {len(finished)} of {len(SEEDS)} seeds complete "
            f"(missing {missing}). The clause is about stability across seeds, and "
            "the mean or spread of an incomplete set satisfies nothing. Each seed's "
            "own floor above is a complete read of that seed; nothing is combined "
            "until five exist. The one registered exception is the seed-1 go/no-go, "
            "which is a floor-only check on seed 1 alone."
        )
        print("\n== verdict ==")
        print("  INCOMPLETE: no verdict is available until all five seeds are run.")
        return 0

    wins = [
        artefact["seeds"][str(s)]["floors"][PRIMARY]["wins"] for s in sorted(finished)
    ]
    rates = [w / FLOOR_GAMES for w in wins]
    failures = [
        s
        for s in sorted(finished)
        if not (
            wilson(artefact["seeds"][str(s)]["floors"][PRIMARY]["wins"], FLOOR_GAMES)[0]
            > 0.5
        )
    ]
    print(
        "  rates    "
        + "  ".join(f"{r:.1%}" for r in rates)
        + f"\n  mean {statistics.fmean(rates):.1%}   sd "
        f"{statistics.stdev(rates):.1%}   range "
        f"{min(rates):.1%}-{max(rates):.1%}"
    )
    hom = homogeneity(wins, FLOOR_GAMES)
    if not hom["degenerate"]:
        print(
            f"  observed sd {hom['observed_sd']:.1%} against "
            f"{hom['binomial_sd']:.1%} expected from sampling alone at the pooled "
            f"{hom['pooled']:.1%}"
        )
        print(
            f"  homogeneity chi2 = {hom['chi2']:.2f} on {hom['df']} df "
            f"(0.05 critical {hom['critical']}): "
            + (
                "the seeds differ by more than sampling noise"
                if hom["heterogeneous"]
                else "consistent with one underlying rate"
            )
        )
        say(
            "This diagnostic gates nothing. The registered criterion is per-seed, "
            "deliberately: a homogeneity test can pass while one seed sits below 50%, "
            "and such a seed is exactly what must not be averaged away. Read it the "
            "other way round -- as a description of how much of the spread is "
            "sampling noise and how much is the seed."
        )

    secondary = [
        artefact["seeds"][str(s)]["floors"]["equal_time"] for s in sorted(finished)
    ]
    cleared_secondary = [m for m in secondary if wilson(m["wins"], m["games"])[0] > 0.5]
    print(
        f"\n  secondary (equal time): {len(cleared_secondary)}/{len(secondary)} seeds "
        "clear, reported and gating nothing"
    )

    # ---- the gate's own discipline -----------------------------------------
    if histories:
        gates_total = sum(training_summary(h)["gates"] for h in histories.values())
        per_gate = binomial_tail(
            GATE_GAMES, 0.5, wins_needed(GATE_GAMES, GATE_THRESHOLD)
        )
        print()
        say(
            f"gate discipline: {gates_total} gates at {GATE_GAMES} games and a "
            f"{GATE_THRESHOLD:.0%} point-estimate threshold promote an exactly-equal "
            f"challenger {per_gate:.2%} of the time, so a "
            f"{1 - (1 - per_gate) ** gates_total:.1%} chance of at least one false "
            "promotion over the run. This is the registered threat that the gate "
            "promotes on the point estimate. It does not touch the floor, which is "
            "read on the interval and against an opponent the gate never sees."
        )

    # ---- verdict ------------------------------------------------------------
    print("\n== verdict ==")
    if failures:
        say(
            f"INSTABILITY RECORDED: seeds {failures} fail the equal-simulations "
            "floor. Per the registration this is not averaged away -- the run does "
            "not support H3's stability clause, and the five rates above are the "
            "result."
        )
    else:
        say(
            "THE FLOOR HOLDS ON EVERY SEED. H3's clause 1 is satisfied in the sense "
            "it was registered: five independent seeds, each beating prior-free UCT "
            "with the whole interval above 50%."
        )

    print()
    say(
        "Not established by either branch: beating prior-free UCT licenses 'the "
        "learner learned something' and nothing more. How good the learner is comes "
        "from H3's clause 2 -- agreement with the solver's exact verdict on the "
        "pre-declared comparison set -- which is a measurement, gates nothing here, "
        "and cannot be computed until EXP-006 ships the 5x5 endgame sample at k <= 8. "
        "Nothing above separates a property of the learner from a property of this "
        "laptop: one machine, one run.",
        indent="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
