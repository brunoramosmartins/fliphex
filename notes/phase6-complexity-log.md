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

Three numbers, in decreasing order of size and increasing order of honesty.

| | 3×3 | 5×3 | 5×5 (shipped) |
|---|---:|---:|---:|
| orientation-inflated | 7.175 × 10¹² | 8.231 × 10²¹ | **1.389 × 10³⁷** |
| configuration space | 711,963 | 17,506,580,337 | **488,676,694,181,949,003** |
| one-step orphans | 23,371 (3.2826%) | 60,009,757 (0.3428%) | 38,814,863,794,591 (**0.0079%**) |
| reachable bound | 688,592 | 17,446,570,580 | **488,637,879,318,154,412** |
| peak layer | `t = 5` | `t = 9` | `t = 15` |

The inflated row is kept in the module, under `orientation_inflated()`, because
"the bound was corrected" is a claim that should come with the discarded figure
attached. It is the roadmap's original expression, multiplying by `6^25` for
tile orientations. adr-006 makes placed tiles inert, so nothing downstream can
read a placed tile's rotation and the rotation is not part of the state. The
correction is a factor of 2.8 × 10¹⁹.

**The reachable bound needs no run.** A configuration has no predecessor exactly
when every occupied cell carries the colour of the player who did *not* just
move — the last cell placed always shows its placer's colour, because a tile's
own arrows never point at the cell it occupies. That is one colouring in `2^t`,
so the `2^t` cancels and the orphan count is a closed form. This is the identity
EXP-005's amendment proved on 2026-08-07, and it is why EXP-007's hundred-hour
5×3 closure was stopped: the correction it would refine is already in the fourth
decimal place on the shipped board.

**The correction shrinks by roughly an order of magnitude per board step** —
3.28% → 0.343% → 0.0079% — because the mass of the space sits at high `t`, where
`2^t` is enormous. A test asserts the ordering, so the claim is checked rather
than observed once.

**The profile is a hump, not a funnel**, on all three boards: the peak layer is
interior and the sizes rise then fall exactly once. That is the shape that says
the game does not converge, and it is the opposite of checkers.

### On the duplication with `scripts/layer_profile.py`

Both compute the same sum, and that is deliberate. `layer_profile` imports
nothing from `fliphex` on purpose — adr-010 V1 compares it against the solver's
own enumerator, and a comparison is only evidence if the two sides are computed
by different means. Collapsing them into one implementation would delete the
check. `test_agrees_with_the_independent_layer_profile` asserts they agree, per
layer, on all three boards, which is Phase 5's lesson 9 applied rather than
restated.

### The off-by-one, and why it has its own test

The identity calls layer 0 an orphan, because the opening position genuinely has
no predecessor. It is reachable: it is where the game starts. Without the guard
the 3×3 reports 23,372 against EXP-005's measured 23,371 — a difference that
vanishes in a percentage (3.2828% against 3.2826%) and survives in a count. I
wrote it wrong first, in the EXP-007 amendment, on all three boards, and it was
the 3×3's recorded count that caught it. `test_the_unguarded_sum_is_exactly_one_too_many`
pins the size of the mistake so a regression is recognisable rather than merely
detectable.

### Probes

Both load-bearing tests were checked by breaking the code they guard. Removing
the `t == 0` guard turns six tests red; swapping the two hand-parity factors in
`configurations()` turns eight red, including the independence check against
`layer_profile` and the `2^n` terminal-layer identity.

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
