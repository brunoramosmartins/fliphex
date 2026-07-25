# Benchmark Protocol

**Status:** draft. Finalised in Phase 5 when `stats/` lands. The rules here
exist from Phase 0 so that no result is ever produced in a way that later has to
be thrown out.

## Why this file exists

Every strength claim in this project must be reproducible and must carry
uncertainty. A bare "beats the heuristic 87% of the time" is not a result.

## Match protocol

1. **Seats are balanced.** Every pairing plays an even number of games with the
   agents alternating as Player 1. Reporting a single-seat win rate is only
   allowed when the seat *is* the question (H1), and then it is labelled as such.
2. **Openings are not shared.** The game is deterministic with no chance nodes,
   so two deterministic agents replay one identical game forever. Variety comes
   from the agents' own stochasticity: MCTS with temperature > 0, or the random
   agent. Any deterministic-vs-deterministic pairing is reported as a **single
   game**, not a win rate.
3. **Seeds are recorded.** Every match records its RNG seed in the experiment
   registry entry.
4. **Compute is stated.** MCTS simulations per move, solver depth cap, and
   wall-clock budget are part of the result. "Agent A beats agent B" without
   both budgets is meaningless.

## Reporting

- Win rates carry a **Wilson 95% confidence interval**, never a normal
  approximation — win rates in this project cluster near 0 and 1, where the
  normal approximation misbehaves.
- Paired comparisons on the same positions use **McNemar's test**.
- When several hypotheses are tested on one experiment, apply a **Bonferroni**
  correction and say so.
- Draws do not exist, so every game contributes exactly one win and one loss.
  Any code path producing a draw is a bug, and should assert.

## Standard opponents

| Name | Definition | Role |
|---|---|---|
| `random_agent` | Uniform over legal moves | Floor. Anything not beating it ≥95% is broken. |
| `heuristic_agent` | Greedy: maximise pieces flipped this ply, ties broken randomly | The baseline every learned agent must clear. |
| `solver_agent` | Alpha-beta at a stated depth, endgame database when in range | Ground truth where its coverage reaches. |

## Minimum sample sizes

Chosen so a 10-point difference around 50% is detectable:

| Comparison | Games |
|---|---|
| Sanity check vs random | 200 |
| Strength vs heuristic | 1000 |
| AZ vs solver (H3) | 1000 per depth setting |
| First-player advantage (H1) | 20 seeds × 1000 games |
