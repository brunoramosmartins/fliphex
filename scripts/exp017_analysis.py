"""EXP-017 analysis: apply the registered rule to the saved artefact.

Registered in ``experiments/registry.md`` on 2026-09-18, which names this file.
Separate from the instrument on purpose — the EXP-015 split, which is what let
that entry's analysis refuse to combine seeds and cross-check its own
recomputation. **This file reads only the artefact.** It imports nothing from
``agents``, ``az`` or ``solver``, so the verdict is reproducible on a machine
that can neither train nor solve anything.

The registered rule
-------------------
The pooled Wilson 95% interval on 5,000 games, against 50%:

- **entirely above** — the first-player advantage survives this level of play.
  Descriptive. H1's verdict still rests on the four exhaustive solves.
- **entirely below** — the advantage does not survive play that is heuristic for
  seventeen plies and exact for eight. **The Phase 5 sensitivity sweep becomes
  mandatory** and a risk row is opened. Whether that is about the game or about
  the level of play is *not* answered here.
- **containing 50%** — no detected direction at the 2-point MDE. **Not**
  evidence that the seats are equivalent; that claim needs a margin declared in
  advance and this entry has none.

What this refuses to print
--------------------------
**A rate without ``proved_rate``.** The agent proves about 31% of its plies and
plays a one-ply greedy heuristic for the rest; a bare first-player rate reads as
a fact about FLIPHEX and is substantially a fact about ``HeuristicAgent``. The
requirement is in ``agents/solver_agent.py``'s own docstring, and EXP-008 set the
precedent.

**A rate over more games than the run actually distinguished.** If the distinct
game count is below the nominal one, the interval is recomputed against the
distinct count and the shortfall is stated. EXP-006's amendment is the reason
this check exists: a denominator that reads plausible and is not measuring what
it claims.

Usage::

    .venv/bin/python scripts/exp017_analysis.py
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

GAMES = 5_000
THRESHOLD = 0.50

#: Power, not half-width. At se = 0.5/sqrt(5000) = 0.707 pp, two-sided alpha
#: 0.05 needs delta = 2.80 * se = 1.98 pp for 80% power.
MDE = 0.02
POWER_AT_MDE = 0.804


def wilson(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def guard(artefact: dict) -> None:
    """Nothing is printed before these pass."""
    if artefact.get("experiment") != "EXP-017":
        raise SystemExit(f"not an EXP-017 artefact: {artefact.get('experiment')!r}")

    probes = artefact.get("self_check") or []
    names = {p.get("probe") for p in probes}
    if "SKIPPED" in names or len(probes) < 2:
        raise SystemExit(
            "the run skipped its gate-7 self-check. An instrument that never met "
            "a known answer does not get a verdict."
        )
    for probe in probes:
        if probe.get("first_player_rate") != probe.get("expected"):
            raise SystemExit(
                f"self-check probe {probe.get('probe')!r} recorded "
                f"{probe.get('first_player_rate')} against an expected "
                f"{probe.get('expected')}. The run wrote a number its own "
                "instrument check contradicts."
            )

    wins, games = artefact["first_player_wins"], artefact["games"]
    if not 0 <= wins <= games:
        raise SystemExit(f"{wins} wins out of {games} games is not possible")
    if abs(wins / games - artefact["first_player_rate"]) > 1e-12:
        raise SystemExit(
            f"stored rate {artefact['first_player_rate']} is not {wins}/{games}"
        )
    low, high = wilson(wins, games)
    if (
        abs(low - artefact["wilson_low"]) > 1e-12
        or abs(high - artefact["wilson_high"]) > 1e-12
    ):
        raise SystemExit(
            "the stored interval is not the recomputed one:\n"
            f"  stored     [{artefact['wilson_low']}, {artefact['wilson_high']}]\n"
            f"  recomputed [{low}, {high}]"
        )
    print(
        f"guards passed: {games} games, self-check {len(probes)}/{len(probes)} "
        "probes met their known answers, interval recomputed"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artefact", default="results/exp017-first-player-5x5.json")
    args = parser.parse_args()

    path = Path(args.artefact)
    if not path.exists():
        raise SystemExit(
            f"artefact not found: {path}\n"
            "Run scripts/eval_first_player_advantage.py first (~3.0 h under "
            "PyPy 3.11); it is resumable."
        )
    artefact = json.loads(path.read_text())
    guard(artefact)

    games = artefact["games"]
    wins = artefact["first_player_wins"]
    distinct = artefact["distinct_games"]

    print("\n== what was actually played ==")
    print(f"  interpreter        {artefact.get('interpreter')}")
    print(
        f"  agent              SolverAgent both seats, search_below_k="
        f"{artefact.get('search_below_k')}, max_nodes={artefact.get('max_nodes')}"
    )
    print(
        f"  proved_rate        {artefact.get('proved_rate', 0):.1%}"
        f"  ({artefact.get('proved_plies')} proved, "
        f"{artefact.get('unattempted_plies')} not attempted)"
    )
    print(
        "  So this is the heuristic for roughly seventeen plies and exact play\n"
        "  for the last eight. No rate below may be quoted without that."
    )

    print("\n== the denominator ==")
    print(f"  nominal games      {games}")
    print(f"  distinct games     {distinct}")
    effective = games
    if distinct < games:
        effective = distinct
        print(
            f"  SHORTFALL: {games - distinct} games repeated an earlier game "
            "exactly.\n  The interval below is recomputed against the distinct "
            "count, because a\n  repeated game is not a second observation."
        )
    else:
        print("  no shortfall: every game is distinct")

    scaled_wins = round(wins * effective / games) if games else 0
    low, high = wilson(scaled_wins, effective)

    print("\n== the first-player rate ==")
    print(
        f"  {scaled_wins}/{effective} = {scaled_wins / effective:.1%} "
        f"[{low:.1%}, {high:.1%}]"
    )
    print(
        f"  design: {MDE:.0%} MDE at {POWER_AT_MDE:.0%} power. Below that this "
        "run is not expected\n  to resolve direction, and that is the registered "
        "limit."
    )

    print("\n== verdict ==")
    if low > THRESHOLD:
        print(
            "  ABOVE 50%: the first-player advantage survives this level of play.\n"
            "  Descriptive. H1's verdict rests on the four exhaustive solves, and\n"
            "  this changes nothing about it."
        )
    elif high < THRESHOLD:
        print(
            "  BELOW 50%: the advantage does not survive play that is heuristic\n"
            "  for seventeen plies and exact for eight. Per the registration the\n"
            "  Phase 5 sensitivity sweep is now MANDATORY and a risk row opens.\n"
            "  Whether this is about the game or about the level of play is not\n"
            "  answered here."
        )
    else:
        print(
            f"  NO DETECTED DIRECTION at a {MDE:.0%} MDE. The interval contains "
            "50%.\n  This is **not** evidence that the seats are equivalent — that "
            "claim needs\n  a margin declared in advance and this entry has none."
        )

    print(
        "\nNot established: anything about perfect play. H1 is a claim about\n"
        "perfect play and its evidence is the exhaustive solves of the 3x3 and\n"
        "5x3, both deck arms, all at termination: exhausted. This measured a\n"
        "named, imperfect level of play on a board no solver reaches."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
