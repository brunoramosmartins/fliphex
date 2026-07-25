# Research

**Status:** DRAFT. Hypotheses are **not yet locked** — locking happens at the
end of Phase 2 and is marked by the `v0.3-hypotheses` tag, which is what
timestamps the pre-registration. Until then H1–H5 may be reworded, split, or
dropped. After that tag, this file may only gain verdicts; anything else needs
an ADR.

## Research question

> **What is the strategic structure of FLIPHEX — does the first player have a
> provable advantage, does the joker break game balance, and does the game
> admit an efficient learned policy that approaches optimal play?**

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
| **H1** | With perfect play the first player wins (strictly, since draws are impossible). | Exhaustive solve of the 3×3 variant; 20-seed self-play win rate with Wilson 95% CI on the full game. | 1 + 2 |
| **H2** | Removing the joker does not change which player holds the theoretical advantage. | Solver + self-play on a joker-less variant. | 1 + 2 |
| **H3** | The learned policy converges to a stable win-rate across independent seeds, and agrees with the solver's exact verdict on shared variants. | 5-seed training; comparison against Axis 1. | 2 |
| **H4** | FLIPHEX's state-space complexity is comparable to Reversi 6×6 and strictly below Othello 8×8 and Hex 11×11. | Direct computation of state-space and game-tree bounds. | 3 |
| **H5** | No archetype dominates placement frequency in self-play, i.e. the 12-tile deck is well balanced. | Frequency and win-contribution analysis over the self-play database. | 2 + 3 |

Rejecting H1 or H2 would be a genuinely interesting finding: a student-designed
game that resists trivial first-player domination.

## Amendments arising from Phase 0

Phase 0 changed the standing of three hypotheses. Recorded here so the eventual
lock is made with these in view.

**H1 — no symmetry argument is available.** The board's symmetry group is
trivial ([board-geometry.md](board-geometry.md)): columns A/C/E and B/D sit at
different vertical centres, so no rotation or reflection maps the cell set onto
itself. There is therefore no strategy-stealing or pairing argument to lean on,
and H1 must be settled computationally. This makes H1 *more* interesting and
strictly harder.

**H1 — possible confound from `OPEN-2`.** If the two decks' chiral `P3-y` tiles
are mirror images of one another (see
[piece-archetypes.md](piece-archetypes.md)), the two seats do not hold
equivalent decks, and any first-player advantage measured would mix the
first-move effect with a deck effect. **This must be resolved before H1 is
locked.** If it resolves badly, H1 splits into H1a (first-move effect, decks
equalised) and H1b (deck effect).

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
