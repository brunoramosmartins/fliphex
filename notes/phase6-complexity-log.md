# Phase 6 — Axis 3: Complexity Analysis and Cross-Game Comparison (experiment log)

**Objective.** Quantify FLIPHEX's structural complexity on both axes that the
literature separates — state space and game tree — and place the game in the
Allis/Schaeffer landscape. Then decide the three hypotheses that remain: H4
(where FLIPHEX lands), H5's surviving half (win contribution per archetype) and
H6 (robustness of the design to bounded perturbation).

**Dates.** None. The roadmap is sequenced by dependency, not by calendar, and
this phase carries no external deadline.

**What the phase must end with.** The last three rows of the verdict table in
`docs/research.md`, each with the interval or exact computation that justifies
it. After this phase the table has no empty rows, and Phase 7 writes up a
closed set rather than an open one.

**What it inherits, and it is more than the previous phases carried.** Three
Phase 5 deliverables were never started — `figures/`, TIL #4 and `ex05` — and
two Phase 3 experiments have stood at "registered; 3×3 pilot run" since August:
EXP-005 and EXP-007. Their registered rule runs on the 5×3 and has not. That is
not a loose end here; EXP-007's exact reachable closure is the input to the
tightened state-space bound this phase must produce.

**The gates are in force**, all nine —
[`docs/measurement-gates.md`](../docs/measurement-gates.md). Gate 9 was written
at the close of Phase 5, after the first eight let the same defect through three
times, and this phase is the first to have it available from the start. It is
the relevant gate here more than anywhere: a complexity bound is a quantity that
the rules constrain by construction, and H5's frequency half was withdrawn for
exactly that reason.

---

## `complexity/state_space.py` — the upper bound, and the reachable one

## `complexity/game_tree.py` — Monte Carlo estimation via random rollouts

## `complexity/branching.py` — legal-move count by turn number

## `complexity/comparison.py` — the cross-game table

## EXP-005 and EXP-007 on the 5×3 — the closure the bound depends on

## H4 — where FLIPHEX lands on both axes

## H5 — win contribution per archetype

## H6 — robustness to bounded design perturbation

## Tile criticality — the reference distribution H2's 17.07% is waiting for

## `figures/` — the canonical figure per hypothesis, carried from Phase 5

## TIL #4 — retrograde analysis, when backwards beats forwards

## `exercises/ex05_complexity_analysis.md`

## Lessons Learned

## Failed Attempts
