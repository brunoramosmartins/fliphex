# Experiment Registry

Every experiment is registered **before it runs**. Results are appended after.
An experiment that is not in this table did not happen.

Freely editable (append-only in practice).

## Format

- **ID** — `EXP-NNN`, allocated in order, never reused.
- **Hypothesis** — H1–H6, or `—` for exploratory runs.
- **Status** — `registered` → `running` → `complete` / `abandoned`.
- **Seed** — the RNG seed. Required. `—` only for deterministic exhaustive solves.
- **Result** — one line, with a CI or an exact value. Links to the notebook or figure.

## Registry

| ID | Date | Hypothesis | Axis | Description | Config / commit | Seed | Status | Result |
|---|---|---|---|---|---|---|---|---|
| _(none yet — first entries land in Phase 3)_ | | | | | | | | |

## Planned

Sketched in Phase 0 so the phases have targets. IDs are allocated on
registration, not here.

| Phase | Experiment | Hypothesis |
|---|---|---|
| 3 | Exhaustive solve of the 3×3 variant; record game value and a principal variation | H1, H2 |
| 3 | Exhaustive solve of the 4×4 variant (stretch) | H1, H2 |
| 3 | Retrograde endgame database, `k ≤ 5` empty cells on 5×5 | H3 |
| 3 | Alpha-beta + endgame DB vs random and heuristic, 1000 games | — |
| 3 | **adr-010 V3** — 3×3 solved twice (forward alpha-beta vs retrograde), values must match on every position | — |
| 3 | **adr-010 V4** — random-sample re-derivation of 4×4 entries by direct search, database not consulted | — |
| 4 | AZ training run, seed 1, to 1M self-play positions | H3 |
| 4 | AZ training run, seed 2 (convergence replication) | H3 |
| 4 | Factored vs flat policy head (adr-005 risk R5) | — |
| 5 | First-player win rate, 20 seeds × 1000 games, Wilson CI | H1 |
| 5 | Joker-less variant, matched protocol | H2 |
| 5 | AZ vs solver at matched depth caps | H3 |
| 5 | Sensitivity: MCTS simulations, `c_puct`, temperature schedule | — |
| 6 | State-space and game-tree bounds; cross-game comparison table | H4 |
| 6 | Archetype placement frequency and win contribution | H5 |
| 6 | **Tile criticality** — for each archetype, the fraction of solved 4×4 positions whose value changes when that tile is removed from the hand | H5 |
| 6 | **Mirror-optimality rate** — on solved positions where the Z/2 mirror is a valid game symmetry (both `P3-y` placed), the fraction of optimal moves whose mirror image is also optimal | H5, H6 |
| 6 | **First-player advantage curve** — fraction of solved positions at each ply `t` won by the player to move, 4×4 | H1 |
