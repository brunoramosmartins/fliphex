# ADR-001 — Scope the project as a perfect-information game study

**Status:** Accepted (Phase 0)
**Date:** 2026-07-23
**Deciders:** Bruno Ramos Martins

## Context

The previous portfolio project (PTCG) studied an *imperfect-information* card
game with Information-Set MCTS. FLIPHEX has to justify existing as a separate
project rather than a second helping of the same thing.

FLIPHEX is deterministic and fully observable: both hands are open, every placed
tile and its orientation are visible, and the joker's colour is public. The only
stochastic element in the physical game is the opening coin toss, which selects
a seat before any decision is made.

The question this ADR settles is whether to model the game as it is, or to
introduce hidden information (closed hands) to reuse the PTCG machinery.

## Decision

**Model FLIPHEX exactly as designed: a finite, deterministic, 2-player,
zero-sum game of perfect information with no draws.** Do not hide hands. Treat
the coin toss as outside the game tree — the solver and the learner both study
the game *given* who moves first, which is precisely what H1 asks about.

This unlocks the three axes in the roadmap, none of which were available on
PTCG:

- **Axis 1** — minimax has a well-defined exact value, so alpha-beta with
  transposition tables and retrograde analysis are meaningful. Under imperfect
  information there is no single game value to compute.
- **Axis 2** — AlphaZero applies in its canonical form: plain PUCT MCTS over
  the real state, no determinization, no information sets.
- **Axis 3** — state-space and game-tree complexity are comparable against the
  published literature for Reversi, Hex, and Connect Four, all of which are
  perfect-information.

## Consequences

**Positive**

- The two axes produce *independent* answers to the same questions, and their
  agreement (or disagreement) is the project's core intellectual claim.
- The portfolio gains a clean contrast: "here is the same author solving the
  imperfect-information case and the perfect-information case, and here is what
  actually changes." That contrast is TIL #1.
- Standard vocabulary and standard baselines apply, so results are legible to
  anyone who knows game AI.

**Negative / accepted costs**

- No reuse of the PTCG ISMCTS code. Accepted: the point is the contrast.
- The coin toss being out of scope means the project answers "does the first
  player win under perfect play", not "is the game fair to sit down to". These
  are different questions and the writeup must not conflate them.

**Neutral**

- The absence of draws (25 cells, odd) means the game value is a strict win for
  one side, so H1 is a binary question with no third outcome. Convenient for
  the solver, and worth saying out loud because it is unusual.

## Alternatives considered

**Hide the opponent's hand.** Would have made ISMCTS reusable, but it
invents a rule the game does not have, invalidates the comparison against the
literature in Axis 3, and destroys Axis 1 entirely. Rejected.

**Model the coin toss as a chance node at the root.** Technically tidy, and it
would let a single number describe "fairness". Rejected for v1 because it
doubles every experiment for no new information: the value at the chance node is
just the average of the two seats' values, which the per-seat results already
give. Revisit if the paper track activates.

## Related

- [adr-004](adr-004-solver-approach.md), [adr-005](adr-005-alphazero-scope-and-network.md)
- `docs/research.md` — H1, H2, H3
