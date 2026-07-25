# Submission Log

One row per trained agent version. Freely editable, append-only in practice.
"Submission" here means *an agent version considered done enough to evaluate* —
there is no external leaderboard.

Every row must be reproducible from the commit and config named in it.

| ID | Date | Commit | Config | Training | vs random | vs heuristic | vs solver | Notes |
|---|---|---|---|---|---|---|---|---|
| _(none yet — first entry lands in Phase 4)_ | | | | | | | | |

## Column meanings

- **ID** — `az-v{n}`, matching the checkpoint filename in `data/models/`.
- **Commit** — short SHA of the code that produced it.
- **Config** — path to the config file or the experiment ID in `experiments/registry.md`.
- **Training** — self-play games, positions seen, wall-clock, seed.
- **vs \*** — win rate with a Wilson 95% CI and the number of games, per
  `benchmark-protocol.md`. Never a bare percentage.
- **Notes** — what changed relative to the previous version, and why.
