# Submission Log

One row per trained agent version. Freely editable, append-only in practice.
"Submission" here means *an agent version considered done enough to evaluate* —
there is no external leaderboard.

Every row must be reproducible from the commit and config named in it.

## Phase 4 — five replicates, not a version series

The log was designed for a progression: `az-v1`, `az-v2`, each improving on the
last. Phase 4 produced something else — **five independent seeds of one frozen
configuration**, run to answer H3's stability clause. Nothing distinguishes them
but the seed, so numbering them `v1…v5` would invent a progression that does not
exist. The IDs carry the experiment and the seed instead.

That matters for how the rows read: **the spread between them is a measurement,
not a series of improvements.** EXP-015 rejected a single underlying win rate
across these five (`χ² = 18.52`, 4 df), so quoting any one row as "the agent" is
wrong in a way the table cannot stop on its own.

| ID | Date | Commit | Config | Training | vs random | vs heuristic | vs UCT floor | vs solver | Notes |
|---|---|---|---|---|---|---|---|---|---|
| `az-exp015-s1` | 2026-09-06 | `9b4d001` | EXP-015 | 30 gen × 200 games = 6,000 games, 150,000 positions, 24.3 h, seed 1 | — | — | 64.0% [57.1, 70.3] (n=200) | 75.6% [70.8, 79.8] (n=352) | Clears the floor. Champion is generation 24; the final gate failed at 54.8%. |
| `az-exp015-s2` | 2026-09-10 | `9b4d001` | EXP-015 | 30 gen × 200 games = 6,000 games, 150,000 positions, 23.0 h, seed 2 | — | — | **76.0%** [69.6, 81.4] (n=200) | **77.0%** [72.3, 81.1] (n=352) | Clears. Best on both measures. Champion is generation 29. |
| `az-exp015-s3` | 2026-09-11 | `9b4d001` | EXP-015 | 30 gen × 200 games = 6,000 games, 150,000 positions, 26.3 h, seed 3 | — | — | 63.0% [56.1, 69.4] (n=200) | 75.9% [71.1, 80.0] (n=352) | Clears. Champion is generation 24; the final gate failed at 49.8%. |
| `az-exp015-s4` | 2026-09-13 | `9b4d001` | EXP-015 | 30 gen × 200 games = 6,000 games, 150,000 positions, 26.0 h, seed 4 | — | — | **56.0%** [49.1, 62.7] (n=200) | 74.4% [69.6, 78.7] (n=352) | **Fails the floor** — the interval includes 50%, by two games. Fewest promotions (4 of 6). Recorded as instability, never averaged away. |
| `az-exp015-s5` | 2026-09-16 | `9b4d001` | EXP-015 | 30 gen × 200 games = 6,000 games, 150,000 positions, 25.0 h, seed 5 | — | — | 62.0% [55.1, 68.4] (n=200) | 75.6% [70.8, 79.8] (n=352) | Clears. Champion is generation 29. Its equal-time floor arm is a duplicate of the primary, not a measurement — see EXP-015. |

**No row clears the solver bar.** H3's threshold on the shipped-5×5 member is a
Wilson lower bound above **0.90**; the best here is 72.3%. The column is the
result, not a progress indicator.

**Two empty columns, deliberately.** `vs random` and `vs heuristic` are the
protocol built for Axis 1's agents in EXP-008, and these champions were never
played against `RandomAgent` or `HeuristicAgent`. Their registered opponents are
prior-free UCT and exact ground truth. The cells stay empty rather than being
filled with a different measurement wearing their name.

**Context every row needs and none of them can hold.** The `vs solver` column
scores **value preservation on positions the mover wins** — never identity with
the solver's move — and a random mover scores **21.9%** on the same set. The raw
policy head with no search scores **50.9% to 56.0%**. Search is worth about 22
points on top of the prior, and the prior about 32 on top of random.

## Column meanings

- **ID** — Phase 4 uses `az-{experiment}-s{seed}`. The original `az-v{n}` scheme
  assumed a version series; see above. The checkpoint is at
  `data/az-runs/h3-seed{n}/`, which is **gitignored** — these runs are 27 hours
  each and are reproduced from the commit, config and seed, not restored from the
  repository.
- **Commit** — short SHA of the code that produced it. All five rows share one:
  no file under `az/`, `agents/` or `fliphex/` changed between the first seed and
  the last, which is checkable with `git log 9b4d001..HEAD -- az/ agents/ fliphex/`.
- **Config** — the experiment ID in `experiments/registry.md`.
- **Training** — self-play games, positions seen, wall-clock, seed. Positions are
  exact, not approximate: the board fills every game, so 200 games is exactly
  5,000 samples.
- **vs \*** — win or agreement rate with a Wilson 95% CI and the number of games
  or positions, per `benchmark-protocol.md`. Never a bare percentage.
- **Notes** — what changed relative to the previous version, and why. For Phase 4
  there is no "previous version"; the notes carry what distinguishes each seed's
  own run instead.
