# Research

**Status: LOCKED (2026-08-05, tag `v0.3-hypotheses`).** The tag timestamps the
pre-registration of H1–H6. From this point the file may only **gain verdicts**;
any other change requires an ADR and must appear as a dated, visible amendment
below — never as a silent rewrite of a hypothesis. The status line previously
still read "DRAFT — not yet locked" after the tag had been pushed; that was a
stale line, corrected here, not a change of standing.

## Thesis

FLIPHEX is treated not only as a game to master but as a **design to understand**.
Self-play reinforcement learning and exact search are used as *instruments* to
characterise the properties of an original, previously un-analysed game — its
first-player balance, the joker's effect, its board geometry, and its tile
distribution — with strong play as the *means* and understanding of the design as
the *end*. Where a property can be measured against ground truth (small variants,
endgames), it is; where it cannot, self-play supplies statistical evidence. The
existing 5×5 design is characterised first; design variants are a stretch that
tests the robustness of the findings, never the spine.

## Research question

> **What is the strategic structure of FLIPHEX — does the first player have a
> provable advantage, does the joker break game balance, is the deck's archetype
> distribution well designed, and does the game admit an efficient learned policy
> that approaches optimal play?**

## Method

Three independent axes, deliberately built to fail differently:

| Axis | Method | Produces |
|---|---|---|
| 1 | Alpha-beta + TT, retrograde endgames | exact ground truth on reduced variants and endgames |
| 2 | AlphaZero-style self-play | a strong learned policy on the full game |
| 3 | Combinatorial and Monte Carlo analysis | structural complexity metrics |

Each hypothesis gets a verdict of **supported / rejected / inconclusive**,
justified by an exact computation, a confidence interval, or a structural
argument — stated explicitly, never by narrative.

## Pre-registered hypotheses (LOCKED at tag `v0.3-hypotheses`)

| ID | Statement | Test | Axis |
|---|---|---|---|
| **H1** | With perfect play the first player wins (strictly, since draws are impossible). | Exhaustive solve of the 3×3 (calibration) and **5×3 (primary strategic, [adr-011](adr/adr-011-reduced-variant-parity.md))** variants; 20-seed self-play win rate with Wilson 95% CI on the full game. | 1 + 2 |
| **H2** | Removing the joker does not change which player holds the theoretical advantage. | Solver + self-play on a joker-less variant (exact on 3×3/5×3; per [adr-011](adr/adr-011-reduced-variant-parity.md) the contrast is what P1's extra tile is, not joker presence). | 1 + 2 |
| **H3** | The learned policy converges to a stable win-rate across independent seeds, and agrees with the solver's exact verdict on **every member of the pre-declared comparison set**: 3×3, **5×3** ([adr-011](adr/adr-011-reduced-variant-parity.md) deck), and a pre-declared random sample of **shipped-5×5 endgame positions at `k ≤ 8` empty cells, solved exactly on demand** (`EXP-006`, registered 2026-08-05 — replaces the retrograde endgame layers, which `EXP-003` showed are not worth materialising). | ≥5-seed training; per-seed win rate with Wilson 95% CI and variance reported across seeds; per-variant agreement rate against Axis 1, restricted to Axis-1 artefacts satisfying [adr-004](adr/adr-004-solver-approach.md) R1 (`termination: exhausted`). | 2 |
| **H4** | FLIPHEX 5×5 is out of reach on **both** complexity axes: its state space (~4.9 × 10¹⁷) exceeds every game solved by full enumeration (Nine Men's Morris 10¹¹, Awari 10¹², Connect Four 10¹⁴), and its game-tree complexity (~10⁶¹; ~10³⁰·⁵ at the Knuth–Moore minimal tree) puts it beyond the weak-solution route that carried checkers *despite* checkers' larger 5 × 10²⁰ state space. | Direct computation of both bounds; placement in the Allis/Schaeffer cross-game table. | 3 |
| **H5** | No archetype dominates placement frequency in self-play, i.e. the 12-tile deck is well balanced. | Frequency and win-contribution analysis over the self-play database. | 2 + 3 |
| **H6** *(optional / stretch)* | The design's balance is *robust to counterfactual variation* — the first-player advantage and joker effect hold their sign under a bounded set of design perturbations (board size 3×3→5×3→5×5; deck swaps, e.g. removing the chiral `P3-y`). | Re-run the H1/H2 verdicts against each perturbation and report whether the *direction* of the effect is preserved; exact where solvable, self-play otherwise. | 1 + 2 |

Under the game-design thesis, **H1, H2, H5** are the spine (they ask directly
whether the design is balanced and fair); **H3** is the cross-axis honesty check;
**H4** situates the game. Rejecting H1 or H2 would be a genuinely interesting
finding: a student-designed game that resists trivial first-player domination.

**H6 is optional and guard-railed.** It turns the "what if we changed the pieces
or the board?" question into a *robustness* claim about the shipped design, never
a redesign. It is tested only *after* H1–H5 are settled on the shipped 5×5, uses
the shipped game as the fixed baseline, and every variant result carries its deck
and board size explicitly ([adr-009](adr/adr-009-reduced-deck-policy.md)). It may
be dropped at lock without affecting the spine.

## Amendments arising from Phase 0

Phase 0 changed the standing of three hypotheses. Recorded here so the eventual
lock is made with these in view.

**H1 — the board's mirror gives no strategy-stealing argument.** The board's
automorphism group is *not* trivial — it is Z/2, a left-right mirror across
column C ([adr-008](adr/adr-008-board-mirror-symmetry.md),
[board-geometry.md](board-geometry.md)) — correcting the Phase 0 claim. But the
mirror preserves the player to move (it is not a colour swap), so it still yields
no strategy-stealing or pairing argument. H1 must be settled computationally.
The Phase 0 *conclusion* was right; its "no symmetry" *premise* was wrong.

**`OPEN-2` — RESOLVED (2026-07-29): the decks are equivalent.** The two decks'
`P3-y` tiles are *identical* (same manufacturing mould, same chirality), not
mirror images, so both players hold `(0,1,3)` on their own face. There is
therefore **no deck confound for H1** — it is a clean first-move (plus joker)
question and does not split into H1a/H1b. This clears the last blocker to locking
the hypotheses. (Per [adr-008](adr/adr-008-board-mirror-symmetry.md), this does
*not* grant a mirror augmentation: that is blocked separately by the chiral tile
and is at best a partial, endgame-restricted gain — which is why there is no
symmetry hypothesis in the table above.)

**H4 — the baseline bound in the roadmap is wrong.** The roadmap's suggested
state-space expression includes a factor of `6^25` for tile orientations. Placed
tiles are inert ([adr-006](adr/adr-006-no-chain-reaction.md)), so orientation is
not part of the state. The corrected reachable bound is

```
Σ_t  C(25,t) · 2^t · C(13,⌈t/2⌉) · C(12,⌊t/2⌋)  ≈  4.9 × 10^17
```

against ~1.4 × 10³⁷ with orientation retained. H4 should be evaluated against
the corrected figure. Note 4.9 × 10¹⁷ sits *below* Reversi 6×6's commonly cited
~10²⁰, so **H4 as currently worded may already be false** — it says
"comparable to Reversi 6×6" but FLIPHEX now looks smaller. Reword before
locking; the honest version is a prediction of where FLIPHEX lands, not that it
lands next to a particular game.

## Amendments arising from Phase 2

**H1/H2 — 4×4 is the primary exact-solve target, not 3×3.**
*(Superseded 2026-08-05 — the board is withdrawn by [adr-011](adr/adr-011-reduced-variant-parity.md);
the argument survives on the 5×3. Left as written, since amendments record what
was believed when they were made.)* The Phase 2
complexity sweep (same bound formula, varying board size) puts the
full-enumeration frontier at **N ≈ 13–15 cells**:

| Board | cells | reachable bound (full deck) |
|---|--:|--:|
| 3×3 | 9 | 2.3 × 10⁹ |
| 4×4 | 16 | 4.8 × 10¹³ (9.3 × 10¹⁰ reduced deck) |
| 5×5 | 25 | 4.9 × 10¹⁷ |

So 3×3 is a *correctness fixture* (too cramped for tactics like deferring a flip
to set up a later swing) and **4×4 is the strategically meaningful exact solve**
carrying the H1/H2 verdicts. Recorded in the
[adr-004 Phase 2 amendment](adr/adr-004-solver-approach.md). The reduced-deck
choice that makes 4×4 tractable is pinned in
[adr-009](adr/adr-009-reduced-deck-policy.md) (Accepted: keep `P6` + `P3-y`,
fill by ascending arrow count; reduced boards are a purely computational
device).

**H3 — the comparison set is now named, because it was going to be n = 1.** As
originally worded, H3's cross-axis clause said "shared variants" and left the
count to be discovered in Phase 5. The only variant both axes were committed to
was the 4×4, so the hypothesis would have rested on a **single** board. Two fixes,
both already available: [adr-009](adr/adr-009-reduced-deck-policy.md)'s policy
generates a family of reduced boards, and — more valuable — the **5×5 retrograde
endgame layers give solver-vs-learner comparison on the shipped game**, not on a
toy. H3 now enumerates its comparison set explicitly, and restricts it to Axis-1
artefacts that terminated by exhaustion
([adr-004](adr/adr-004-solver-approach.md) R1), so no comparison can be drawn
from a run whose search order was seeded by the learner it is being compared to.

**H4 — reworded onto both complexity axes.** The Phase 0 wording ("comparable to
Reversi 6×6") was flagged above as probably false against the corrected bound,
and it was also the wrong *shape* of claim: it asserted proximity to one game
rather than a position in the landscape. Reading Allis against Schaeffer supplied
the missing distinction — state-space and game-tree complexity are **independent**
axes, and checkers was weakly solved with ~1000× *more* states than FLIPHEX 5×5
because it is easy on the axis that governs a forward proof. H4 now states a
falsifiable position on both axes and names the datapoints it is measured against.

**Verification is now an ADR, and the verdict table carries an evidence class.**
The 4×4 solve produces one verdict out of ~10¹¹ states, where the failure mode is
a *plausible wrong answer* rather than a crash.
[adr-010](adr/adr-010-solver-correctness.md) fixes the six checks that must pass
before any Axis-1 number may appear in the table below, and drafts — before the
result exists — the strongest sentence a single implementation run once is
entitled to. Its last clause ("it has not been independently reimplemented") is
what the evidence-class column exists to carry.

## Amendments arising from Phase 3

These are **post-lock** amendments. Each is authorised by an ADR, dated, and
recorded here rather than applied by rewriting a hypothesis in place. The
hypothesis *statements* are unchanged; what changes is the set of variants they
are measured on.

**The 4×4 is withdrawn as an exact-solve target (2026-08-05, [adr-011](adr/adr-011-reduced-variant-parity.md)).**
A pre-run red-team of `EXP-001`/`EXP-002` found that the 4×4 has **16 cells**,
which is even. Scoring is a cell count, so an 8–8 terminal is reachable —
`C(16,8) = 12,870` of its 65,536 terminal configurations — and **no tie-break
rule exists** in [rules-canonical.md](rules-canonical.md), whose §7 derives the
impossibility of draws entirely from 25 being odd.
[adr-010](adr/adr-010-solver-correctness.md) V2 asserts the no-draw invariant
totally and states that any `N` used must be odd; `fliphex/rules.py` raises on a
tied terminal. The 4×4 is therefore not a variant of this game, and the
withdrawal is a defect fix, not a scope choice.

Two further defects on the same board, recorded because they would have survived
a parity fix: the 4×4 gives P1 **no extra ply** and hands the **final placement
to P2**, deleting the mechanism [rules-canonical.md](rules-canonical.md) §6 names
as the source of the first-player advantage — so H1 could not have failed there
in any interpretable way. And its automorphism group, measured with
`scripts/check_symmetry.py 4 4`, is a **180° rotation**, not the 5×5's mirror; no
tile can break a rotation, so [adr-009](adr/adr-009-reduced-deck-policy.md)'s
reason for keeping the chiral `P3-y` in that deck does not apply to it.

The replacement proposed by adr-011 is the **5×3** (15 cells, odd, hands 8 + 7,
bound 1.75 × 10¹⁰), which preserves P1's extra ply, the joker as that extra ply,
and the same Z/2 mirror as the shipped board. **Pending acceptance** — until then
H1's and H3's variant lists carry a gap rather than a substitute.

**H2 gains a paired design it did not have (2026-08-05, adr-011).** As registered,
H2 had no second arm. On an odd board the joker cannot simply be removed — it is
what makes P1's hand larger, so removing it leaves the board unfillable. H2's
contrast becomes **what P1's extra tile is**: the zero-arrow joker, or the next
archetype by ascending arrow count. Both arms hold `a + 1` and `a` tiles, so the
two state spaces are exactly the same size and the comparison is matched. This
isolates the joker's *strategic* content from the *structural* extra ply — the
distinction rules-canonical.md §6 draws and the earlier design confounded.

**H2 is not reported from root-value agreement (2026-08-05).** Agreement between
two binary values carries at most 1 bit against a 50% prior, and on small boards
most cells are boundary cells, so many ordinary placements flip nothing and act
as joker substitutes. The H2 verdict comes from the **criticality** measure — the
fraction of solved positions whose value changes when P1's extra tile is swapped
— which requires the solved database to be indexed by hand. That is a constraint
on the solver, decided before the solve.

**H3 re-scoped: the shipped 5×5 stays in the comparison set, without a database
(2026-08-05, `EXP-003`, authorised by [adr-012](adr/adr-012-endgame-database-storage.md)).**
The contingency recorded below fired. `EXP-003` measured the cost of an exact
endgame search on the shipped board and found it trivial: **480 nodes** at
`k = 5` — the layer whose database would be ~1.2 × 10¹⁵ positions and ~150 TB —
and 806,474 nodes at `k = 8`. `k* > 8`, so no database is built.

But the member H3 loses and the member it needs are not the same thing. The
Phase 2 amendment added the 5×5 endgame layers so that H3 would not rest entirely
on reduced boards; what it actually required was **exact ground truth on the
shipped game**, and the *database* was only the assumed means of getting it.
EXP-003 shows a cheaper means: solve sampled endgame positions **on demand**.

H3's comparison set therefore becomes 3×3, 5×3, and a pre-declared random sample
of shipped-5×5 positions at `k ≤ 8`, each solved exactly at query time
(`EXP-006`). This is stronger than what it replaces, on two counts. The
retrograde route would have delivered whatever `k` the disk allowed, discovered
after the fact; the sample is fixed in advance at a `k` already measured to be
affordable. And `solver/minimax.py` proves or raises — it cannot return an
approximate value — so every ground-truth value in the set satisfies
[adr-004](adr/adr-004-solver-approach.md) R1 `termination: exhausted` by
construction rather than by audit.

`EXP-006`'s sampling protocol is registered **now**, before Axis 2 exists. That
ordering is the point: a comparison set fixed after seeing the learner is not a
comparison set.

**The contingency as it was written, before the measurement
(2026-08-05, [adr-012](adr/adr-012-endgame-database-storage.md)).**
The Phase 2 amendment gave H3 the 5×5 retrograde endgame layers so it would not
rest on toy boards. adr-012 now defers the decision to build those databases at
all, pending `EXP-003`: Othello — FLIPHEX's structural twin — was weakly solved
with forward alpha-beta and **no materialised endgame database** (Takizawa 2023),
and the subtree below a `k = 5` node is order 10⁵–10⁷ nodes against ~150 TB of
storage at that depth. If `EXP-003` puts the crossover beyond reachable `k`, H3
loses that member and must be re-scoped or dropped. This is recorded now, before
the measurement, so the outcome cannot be presented as having been anticipated
either way.

**adr-010 V1 restated (2026-08-05, adr-010 Phase 3 amendment).** V1 was specified
as both a pass/fail gate and the reachability measurement, which is not
decidable: the closed-form formula counts configurations, so a correct
reachable-closure enumerator disagrees with it by exactly 2× at layer 1. V1 is
now exact per-layer equality against the configuration space — a genuine `perft`,
with no tolerance — and the reachability gap is measured separately by `EXP-005`.
No Axis-1 figure in the Verdicts table below may cite V1 under the old wording.

## Verdicts

One row per hypothesis, each citing the experiment ID in
[`experiments/registry.md`](../experiments/registry.md).

**Complete as of 2026-09-20.** Empty from the lock on 2026-08-05 until Phase 5,
filled for H1, H2, H3 and H5 there, and closed in Phase 6 with H4 and H6. Every
row is written; none says "inconclusive". Three of the six, however, report that
the **locked test** could not do what it was written to do — H1's 20-seed
tournament was not performed as written, H4's cited game-tree magnitude is 236×
high, and both halves of H5's measure are fixed by the rules — and those are
recorded in the rows as deviations rather than smoothed over. A verdict table
with no gaps is not the same as a set of hypotheses that were all well posed.

Every row carries an **evidence class**, because the hypotheses do not all get the
same *kind* of answer and a bare "supported" erases the difference between an
enumerated fact and a 20-seed win rate:

- **`exact`** — an exhaustive computation, qualified by its verification status
  per [adr-010](adr/adr-010-solver-correctness.md). E.g. *"supported (exact,
  single implementation, V0–V5 passed, not independently reimplemented)"*.
- **`statistical`** — an estimate with a stated interval and seed count.
- **`structural`** — a closed-form bound or an argument from the rules, with no
  run behind it.

| ID | Verdict | Evidence class | Evidence | Experiment | Phase |
|---|---|---|---|---|---|
| H1 | **supported** on every board where perfect play is computable; **not decidable** on the shipped 5×5 | `exact` on the reduced boards — 3×3 by **two independent methods** (forward alpha-beta and retrograde sweep) agreeing on **604,347 of 711,963 positions, 84.9%**, V1 exact at every layer; 5×3 by retrograde sweep, V0–V6 with coverage stated (V4 has **no search evidence at `t = 0..5`**, V6 covers `t ≥ 2` only). Plus `statistical` on the shipped board, **corroborative only** | Four exhaustive solves, all `termination: exhausted`, all returning **P1**: 3×3-`h1`/`h2` and 5×3-`h1`/`h2`. On the shipped 5×5 no exhaustive solve is reachable, so the claim cannot be decided there. **The locked test's "20-seed self-play win rate" was not performed as written, and that is a deviation rather than an omission**: [EXP-016](../experiments/registry.md) registered it and was withdrawn the same day, before running — prior-free UCT at 400 simulations visits 10–18 of 325 root children in board-cell order, and the learner-based alternative needs 20 training seeds at 540 h. [EXP-017](../experiments/registry.md) replaced it with a registered design measuring a **different quantity**: **54.2% [52.9%, 55.6%]** over 5,000 games under play that is heuristic for ~17 plies and exact for the last 8 (`proved_rate` 32.0%). That corroborates the direction and **says nothing about perfect play**. Also not evidence here: EXP-015's seat splits, which are confounded because the two seats are held by different agents. | [EXP-001](../experiments/registry.md), [EXP-002](../experiments/registry.md), [EXP-016](../experiments/registry.md) (withdrawn), [EXP-017](../experiments/registry.md) | 3 (exact evidence), 5 (shipped-board arm and verdict) |
| H2 | **supported** on the boards where it is computable; **out of reach by construction** on the shipped 5×5 | `exact` — four exhaustive solves, `termination: exhausted` on all four, with the same adr-010 verification status H1 carries: the 3×3 cross-checked by two independent methods on 84.9% of positions, the 5×3 by retrograde sweep with V4 and V6 coverage stated rather than assumed | Both arms return **P1** on both boards: 3×3-`h1`/`h2` and 5×3-`h1`/`h2`. Swapping P1's extra tile from the joker to `P3-tri` does not change which player holds the advantage. The arms are **verified distinct** rather than assumed so — extra-tile criticality **17.07%** (1,237,229,498 of 7,248,350,863 positions with the tile still in hand), and 10,258,229,474 cross-arm positions compared with **0 mismatches** where it is already spent. **The 17.07% is a magnitude, not a verdict**: it measures positional sensitivity, H2 asserts a root property, and no threshold for it was ever registered — see the EXP-002 amendment of 2026-09-18. Its interpretation waits on Phase 6's per-archetype tile criticality, which supplies the reference distribution. **No shipped-5×5 arm exists**: at capacity 12 there is no next archetype to promote, so the joker is the only tile that can give P1 the extra ply and `Variant(5, 5, Arm.H2)` raises. | [EXP-001](../experiments/registry.md), [EXP-002](../experiments/registry.md) + its 2026-09-18 amendment | 3 (evidence), 5 (verdict) |
| H3 | **rejected**, on both clauses independently | `statistical` — five training seeds, Wilson 95% intervals throughout, read against `exact` ground truth satisfying [adr-004](adr/adr-004-solver-approach.md) R1 (`termination: exhausted`) | **Clause 1, stability across seeds: rejected.** [EXP-015](../experiments/registry.md), 5 seeds × 30 generations, 135.0 h. Four seeds clear the prior-free UCT floor and one does not — seed 4 at **56.0% [49.1%, 62.7%]**, two games short of the bar — and per the pre-registered falsifiability clause a failing seed is recorded, never averaged away. The failure is not one unlucky draw: the between-seed `sd` is **7.3%** against the **3.4%** sampling alone predicts, and homogeneity **`χ² = 18.52` on 4 df rejects a single underlying rate**. **Clause 2, agreement on every member: rejected.** [EXP-006](../experiments/registry.md) reads the shipped-5×5 member — 352 exactly solved won endgame positions at `k ≤ 8` — and all five champions score **74.4% to 77.0%** against a threshold of **0.90** pre-declared on 2026-08-05, the best seed's *upper* limit being 81.1%. Context the rate may not be quoted without: a random mover scores 21.9% and the raw policy head 53.5%. **The 3×3 and 5×3 members are unread, and that changes nothing** — the clause says "every member", so one failure decides it. They are also **unreadable with the artefacts that exist**: the champions are shape-locked to the 5×5 (`ConvRotationNet` flattens 32 × 25 into a 25-logit head, so a 5×3 raises), and the only reduced-board networks this project has were trained **supervised on solver labels** (EXP-011/012/013), which R1 forbids for the comparison H3 *is*. **Not established:** any cause for either failure — nothing varies architecture, budget or training length — and not that the learner is weak in general, since it beats prior-free UCT on four seeds of five and a random mover by 54 points. | [EXP-015](../experiments/registry.md), [EXP-006](../experiments/registry.md) | 4 (both readings), 5 (verdict) |
| H4 | **clause 1 supported; clause 2 survives only as literally worded, and the "out of reach" reading it serves does not** | `structural` — both bounds in closed form, each verified against the engine's own move generator; the cross-game placement rests on cited figures rather than on computation, and each carries a provenance grade, six of them checked against the source text held in this project | **Both bounds are exact, not estimated.** State space **4.886 × 10¹⁷** reachable — 4.887 × 10¹⁷ before the one-step correction of **0.0079%**, so the locked ~4.9 × 10¹⁷ is right on either reading. Game tree **4.229 × 10⁵⁸ = 10^58.63**, an exact count of distinct complete games rather than a `b^d` estimate: the solution depth is exactly 25 (at ply 24 the last tile's rotation still decides the colour count, so a depth-24 full-width search cannot determine the value), every (empty cell, tile in hand, distinct rotation) triple is legal, and the leaf count is therefore `25! × 13! × ∏orbits × 12! × ∏orbits`. Checked against `fliphex.legal_moves` at **full depth** on the 5×1 and to three plies on both reduced boards and both arms — sixteen cases, sixteen exact matches. **Clause 1 — supported.** 10^17.69 exceeds every strongly solved game this project could source: **Nine Men's Morris 10¹¹** and **Awari 10¹²** (both quoted from Schaeffer 2007, quotes resolved against the text), **Connect Four** (Schaeffer and Allis both cite 10¹⁴; Tromp's exact enumeration is 4.53 × 10¹², and FLIPHEX exceeds either), and **Reversi 6×6**, which the hypothesis does not name — strongly solved, and bounded above by `3^36 = 1.501 × 10¹⁷` before any legality constraint, so the comparison uses that ceiling rather than a figure, there being no sourced one. **One classification caveat:** the hypothesis lists Connect Four among the games "solved by full enumeration", but Allis solved it *weakly* in 1988 and that is how this project's table grades it; it appears to have been strongly solved later by symbolic classification (Edelkamp & Kissmann 2008, not held here and not verified). The comparison runs the same direction either way. **This also closes the Phase 0 worry recorded above**, that H4 "may already be false" because 4.9 × 10¹⁷ sits *below* Reversi 6×6's commonly cited ~10²⁰: that figure cannot exist, and FLIPHEX is in fact the larger of the two by at least 3.26×. The worry was reasoning from a phantom. The rewording it prompted was still the right move, for the separate reason given in the Phase 2 amendment — proximity to one game was the wrong *shape* of claim. The clause's universal form, "every game solved by full enumeration", is **not decidable from a table of eight rows**; what is established is that it holds against every such game with a sourced figure. **Clause 2 — the magnitude is wrong, and the comparison is narrower than the claim it is made to carry.** The locked **~10⁶¹ is 236× high**. The locked Knuth–Moore figure **~10³⁰·⁵ is right** (computed: 10^30.49) — and the two are mutually inconsistent, which is how the error is visible with no new measurement: recover `b` from `10^30.5 = b^13` and `b^25 = 10^58.65`, the exact answer. The minimal-tree figure was derived correctly from a branching factor and a depth; the full-tree figure does not follow from the same pair. **This is a deviation recorded, not an omission** — the hypotheses are locked at `v0.3-hypotheses` and the statement is not edited. Against **checkers specifically the clause holds**: 10^58.63 is far beyond the ~10⁴⁰ commonly attributed to checkers' game tree, a figure this project declines to print because the reproductions of van den Herik Table 1 disagree by one to two in the exponent. **But the "out of reach" reading does not survive Othello 8×8** — game tree **10^58.00** on the estimate Takizawa 2023 quotes from Allis, **weakly solved in 2023**, three years before this hypothesis was written and by a paper held in this repository and read in Phase 2. FLIPHEX is **4.2× larger: a factor, not an order**. Takizawa also reports that the actual search was "far less than predicted in previous research", which is evidence against game-tree complexity as a measure of reach at all. **Not established:** that FLIPHEX is solvable — nobody has attempted it, and clause 1 stands against every strongly solved datapoint. Nor that the Othello comparison is tight: Othello's 10⁵⁸ is a `b^d` estimate (10 average moves over 58 ply) while FLIPHEX's is an exact count, so they are the same order *as the literature reports them* and the comparison inherits the estimate's uncertainty. | No experiment — closed-form computation with tests: [`complexity/state_space.py`](../complexity/state_space.py), [`complexity/game_tree.py`](../complexity/game_tree.py), [`complexity/comparison.py`](../complexity/comparison.py). See the note in [`experiments/registry.md`](../experiments/registry.md) `## Planned` | 6 |
| H5 | **true by construction on the measure it names, and therefore not evidence of anything** — the balance inference it draws does not follow | `structural` — a consequence of the rules, demonstrated empirically rather than only argued | **Placement frequency is forced by the rules and cannot vary.** 25 cells, no passing, and both hands exhaust exactly, so every tile in hand is played every game: **12 archetypes × 2 (one per player) + 1 joker = 25**. Checked on 500 recorded games from [EXP-017](../experiments/registry.md): the per-archetype count vector is `[2]×12 + [1]` in **every single game**, identical throughout. So "no archetype dominates placement frequency" is true of *any* deck, *any* agent and *any* strategy on a board whose hands exhaust — it is a restatement of the rules, not a measurement, and the inference *"i.e. the 12-tile deck is well balanced"* **does not follow from it**. This is the same defect class as EXP-006's denominator, which scored a hit for every move from a lost position: a quantity the game itself fixes. **Correction, 2026-09-20 — the other half is forced too, and this row said otherwise.** Written in Phase 5, this verdict claimed *win contribution* "is not forced and was never run". **That was wrong**, and the same 5,000 EXP-017 games settle it: hands exhaust exactly and each player holds each of the 12 archetypes once, so **every archetype is played exactly once by the winner and once by the loser, in every game — 5,000 games, zero exceptions**. "Win rate given archetype X was played by the winner" is therefore 100% for all twelve, by the rules. The joker is worse than vacuous: only P1 holds it, so "the joker was played by the winner" is "P1 won", and the count comes out at **2,712 / 2,288 — exactly EXP-017's first-player split**. Measuring the joker's win contribution measures the first-player advantage under another name. **So both halves of the locked test are forced, and H5's verdict is complete here rather than half-open to Phase 6.** **The unforced alternatives are confounded, which is why none is registered.** Placement *timing* does vary — mean ply runs from **5.11** (`P5`) to **22.80** (joker) — but a uniform-random null shows it is stratified almost entirely by **rotation-orbit size**: orbit 6 → ply 9.7, orbit 3 → 13.7, orbit 2 → 16.1, orbit 1 → 19.0, with all eight orbit-6 tiles inside 9.58–9.87. Net of that null the residual is large and monotone in arrow count (`r = −0.855`; `P6` −8.56 plies, `P5` −4.73, `P1` +6.59) — **but it is not attributable to the deck**, because the only complete-game database this project holds was played by an agent whose objective *is* net flips ([`agents/heuristic_agent.py`](../agents/heuristic_agent.py)), and a flip-maximiser avoids many-arrowed tiles late precisely because their arrows start landing on its own pieces. The observed timing is a prediction of that objective, not a finding about the game. **No entry is registered on it**: doing so would need a game database from an agent that is not a flip-maximiser, and the champions record positions rather than ordered games, so none exists. Recorded as the reason, not as a plan. | [EXP-017](../experiments/registry.md) (recorded games, used as a check on the structural argument, and again for the 2026-09-20 correction) | 5 (the frequency finding), 6 (the win-contribution finding and the correction) |
| H6 | **supported on every perturbation that exists, and the perturbation set cannot falsify it** | `exact` on the sign readings — the same four exhaustive solves H1 and H2 rest on, all `termination: exhausted`, carrying the adr-010 verification status recorded there — and `structural` on the scope, which is decided by [adr-009](adr/adr-009-reduced-deck-policy.md) and [adr-011](adr/adr-011-reduced-variant-parity.md) rather than measured | **Adopted at the Phase 6 open rather than dropped.** H6 is marked *optional / stretch* at the lock and had no owning phase — Phase 6 named only H4 and H5, and Phase 7 is interface and writeup — so it was taken by the last phase that can measure anything. **Board-size family: three points, and adr-011 holds the mechanism constant across all of them.** 3×3-`h1`/`h2` and 5×3-`h1`/`h2` all return **P1** at `termination: exhausted`; the shipped 5×5 is not decidable and contributes only [EXP-017](../experiments/registry.md)'s corroborative **54.2% [52.9%, 55.6%]** on the `h1` arm, which says nothing about perfect play. But adr-011 **requires** every reduced board to have an odd cell count and gives P1 the extra tile, so **P1 moves last on every legal board, the shipped one included** — the structural feature that most plausibly causes the advantage is held constant by construction, not varied. [EXP-009](../experiments/registry.md) makes that concrete on the 5×3-`h1`: **every one of the 12,841,920 configurations at `t = 4` is a P1 win**, and every one of the 713,440 at `t = 3` a P2 loss. An early-game advantage that is total rather than positional is what a structural cause looks like. And the one board that *would* have perturbed the structure — the **4×4**, whose cell count is even and whose non-trivial automorphism is a 180° rotation rather than the mirror — **is withdrawn by adr-011**, because an even board admits draws and the canonical rules define no tie-break. **Deck-swap family: the named example is forbidden, and no other is constructible.** H6's example is "removing the chiral `P3-y`". `P3-y` is one of adr-009's two **anchors**, and clause 1 reads *"Always include `P6` and `P3-y`"* — kept precisely **because** it is the sole chiral tile, the piece whose reflection leaves the deck and breaks the board's Z/2 mirror at the game level. **adr-009 was ratified 2026-07-31, five days before the hypotheses locked on 2026-08-05.** Beyond that example there is no lever: `Variant` carries only `n_cols`, `n_rows`, `arm` and `first`, and `archetypes_for` is deterministic in capacity, so **the only deck perturbation the engine admits is the `arm` swap — which is H2**. The remaining field, `first`, selects which colour moves first; with the two decks identical (`OPEN-2`, resolved 2026-07-29) that is a relabelling, not a perturbation. **The joker half has no sign to preserve.** H2 found the root value unchanged on both boards and both arms: swapping P1's extra tile from the joker to `P3-tri` does not change who wins. The joker effect on the game value is therefore exactly **zero** — not positive, not negative — so *"holds its sign"* is not a statement that can be true or false of it. **Nothing here is new evidence.** Every exact datapoint is one of the four solves already read for H1 and again for H2; H6 reports them a third time and adds no independent computation. Producing one would have needed arbitrary-deck machinery the engine does not have, an adr-009 amendment against a ratified clause, and roughly **31–34 h** per new 5×3 arm at EXP-002's measured sweep cost. **Not established:** that the design is robust in the sense H6 intends. What *is* established is that the sign holds across every perturbation the project's own decision records permit, and that those records were written to preserve the mechanism rather than to vary it. A falsifying test would need a board whose parity construction differs, which adr-011 forbids, or a deck without an anchor, which adr-009 forbids. | [EXP-001](../experiments/registry.md), [EXP-002](../experiments/registry.md) (both arms), [EXP-009](../experiments/registry.md), [EXP-017](../experiments/registry.md) — all re-read, none re-run | 6 |
