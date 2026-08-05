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
| **H3** | The learned policy converges to a stable win-rate across independent seeds, and agrees with the solver's exact verdict on **every member of the pre-declared comparison set**: 3×3, **5×3** ([adr-011](adr/adr-011-reduced-variant-parity.md) deck), and the 5×5 retrograde endgame layers at the largest `k` achieved **[contingent on adr-012]**. | ≥5-seed training; per-seed win rate with Wilson 95% CI and variance reported across seeds; per-variant agreement rate against Axis 1, restricted to Axis-1 artefacts satisfying [adr-004](adr/adr-004-solver-approach.md) R1 (`termination: exhausted`). | 2 |
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

**H3's 5×5 endgame member is contingent (2026-08-05, [adr-012](adr/adr-012-endgame-database-storage.md)).**
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

Empty until Phase 5 and Phase 6. One row per hypothesis, each citing the
experiment ID in [`experiments/registry.md`](../experiments/registry.md).

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
| H1 | — | | | | |
| H2 | — | | | | |
| H3 | — | | | | |
| H4 | — | | | | |
| H5 | — | | | | |
| H6 | — | | | | |
