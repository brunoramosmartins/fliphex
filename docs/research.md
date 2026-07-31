# Research

**Status:** DRAFT. Hypotheses are **not yet locked** — locking happens at the
end of Phase 2 and is marked by the `v0.3-hypotheses` tag, which is what
timestamps the pre-registration. Until then H1–H5 may be reworded, split, or
dropped. After that tag, this file may only gain verdicts; anything else needs
an ADR.

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

## Pre-registered hypotheses (DRAFT — lock at end of Phase 2)

| ID | Statement | Test | Axis |
|---|---|---|---|
| **H1** | With perfect play the first player wins (strictly, since draws are impossible). | Exhaustive solve of the 3×3 (calibration) and 4×4 (primary strategic) variants; 20-seed self-play win rate with Wilson 95% CI on the full game. | 1 + 2 |
| **H2** | Removing the joker does not change which player holds the theoretical advantage. | Solver + self-play on a joker-less variant (exact on 3×3/4×4). | 1 + 2 |
| **H3** | The learned policy converges to a stable win-rate across independent seeds, and agrees with the solver's exact verdict on shared variants. | ≥5-seed training; per-seed win rate with Wilson 95% CI and variance reported across seeds; comparison against Axis 1. | 2 |
| **H4** | FLIPHEX's state-space complexity is comparable to Reversi 6×6 and strictly below Othello 8×8 and Hex 11×11. | Direct computation of state-space and game-tree bounds. | 3 |
| **H5** | No archetype dominates placement frequency in self-play, i.e. the 12-tile deck is well balanced. | Frequency and win-contribution analysis over the self-play database. | 2 + 3 |
| **H6** *(optional / stretch)* | The design's balance is *robust to counterfactual variation* — the first-player advantage and joker effect hold their sign under a bounded set of design perturbations (board size 3×3→4×4→5×5; deck swaps, e.g. removing the chiral `P3-y`). | Re-run the H1/H2 verdicts against each perturbation and report whether the *direction* of the effect is preserved; exact where solvable, self-play otherwise. | 1 + 2 |

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

**H1/H2 — 4×4 is the primary exact-solve target, not 3×3.** The Phase 2
complexity sweep (same bound formula, varying board size) puts the
full-enumeration frontier at **N ≈ 13–15 cells**:

| Board | cells | reachable bound (full deck) |
|---|--:|--:|
| 3×3 | 9 | 3.1 × 10⁹ |
| 4×4 | 16 | 8.3 × 10¹³ (9.3 × 10¹⁰ reduced deck) |
| 5×5 | 25 | 4.9 × 10¹⁷ |

So 3×3 is a *correctness fixture* (too cramped for tactics like deferring a flip
to set up a later swing) and **4×4 is the strategically meaningful exact solve**
carrying the H1/H2 verdicts. Recorded in the
[adr-004 Phase 2 amendment](adr/adr-004-solver-approach.md). The reduced-deck
choice that makes 4×4 tractable is pinned in
[adr-009](adr/adr-009-reduced-deck-policy.md) (Proposed).

## Verdicts

Empty until Phase 5 and Phase 6. One row per hypothesis, each citing the
experiment ID in [`experiments/registry.md`](../experiments/registry.md).

| ID | Verdict | Evidence | Experiment | Phase |
|---|---|---|---|---|
| H1 | — | | | |
| H2 | — | | | |
| H3 | — | | | |
| H4 | — | | | |
| H5 | — | | | |
