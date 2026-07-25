# ADR-005 — Small residual policy/value net over a factored action space

**Status:** Accepted (Phase 0)
**Date:** 2026-07-23
**Deciders:** Bruno Ramos Martins

## Context

Axis 2 implements AlphaZero on the full 5×5 game, trained on a single laptop
GPU (Dell G7). Two design pressures dominate, and they pull against each other:

**The action space is large for the size of the game.** A move is
(cell, tile, rotation) = 25 × 13 × 6 = **1950** slots, of which at most 1450 are
ever legal and typically far fewer. A flat policy head over 1950 logits on a
game with only 25 plies is a poor ratio of parameters to signal.

**The game is short and small.** 25 plies, no draws, ~4.9 × 10¹⁷ states
([adr-003](adr-003-piece-representation.md)). This is much closer to Connect
Four than to Go, and the published AlphaZero architecture (20–40 residual
blocks, 256 filters) is wildly oversized.

## Decision

**Input encoding.** The board is a `5 × 5` offset grid of planes (hex adjacency
is handled by the network learning it, not by the geometry of the tensor):

| Plane(s) | Content |
|---|---|
| 1 | own colour, per cell |
| 2 | opponent colour, per cell |
| 3 | empty, per cell |
| 4 | side to move (constant plane) |
| 5–17 | own hand: one constant plane per remaining tile (13, joker included) |
| 18–29 | opponent hand: one constant plane per remaining tile (12) |

29 planes of 5×5. Deliberately **no orientation planes** — placed tiles are
inert, so orientation is not part of the state (adr-003).

**Architecture.** A small residual tower: `3×3` conv stem to 64 filters, then
**4 residual blocks** of 64 filters, then the two heads. Target **~0.5–1.5 M
parameters**. Start at the small end; grow only if training plateaus below the
heuristic baseline.

**Factored policy head.** Rather than 1950 logits, the head emits three
factors — 25 cell logits, 13 tile logits, 6 rotation logits — combined as
`log p(cell) + log p(tile) + log p(rotation)`, then masked to legal moves and
renormalised. 44 logits instead of 1950.

**Value head.** Single `tanh` output in `[-1, 1]`. Since draws are impossible,
the training target `z` is always exactly `±1`.

**MCTS.** Plain PUCT over the real state — no determinization, no information
sets ([adr-001](adr-001-perfect-information-scope.md)). Dirichlet noise at the
root, temperature 1 for the opening plies then greedy.

**No symmetry augmentation.** The board's symmetry group is trivial (adr-002),
so unlike Go's 8× or Connect Four's 2×, there is none to exploit.

## Consequences

**Positive**

- The factored head cuts policy parameters by ~40× and shares statistics across
  moves: learning that a cell is good transfers across all tiles played there.
  On a game with 25 plies per self-play game, sample efficiency is the binding
  constraint, and this directly attacks it.
- Dropping orientation planes shrinks the input and removes a large block of
  input the network would have had to learn to ignore.
- `z = ±1` always means the value head faces a clean binary target with no
  draw-mass to smear the output toward zero. Value learning should be fast.
- A ~1 M-parameter model trains comfortably on a G7, so the "two independent
  seeds" exit criterion for Phase 4 is realistic rather than aspirational.

**Negative / accepted costs**

- **The factored policy cannot represent arbitrary joint distributions.** It
  assumes cell, tile, and rotation choices are conditionally independent given
  the state, which is false — the best rotation depends heavily on the cell.
  This is the main risk in Axis 2. Mitigations, in order: (a) rely on MCTS to
  correct the prior, which is exactly what MCTS is for; (b) if the policy loss
  plateaus, condition rotation logits on the chosen cell; (c) fall back to a
  flat 1950-logit head, which is the safe design.
  **This must be checked explicitly in Phase 4 and logged**, not assumed away.
- No data augmentation means more self-play games for the same signal.
- Constant planes for hand contents are a wasteful encoding (13 planes of 25
  identical values each). Accepted for v1 because it keeps the tower
  convolutional and uniform; a concatenated vector at the head is the
  optimisation if memory bites.

**Neutral**

- Laying hex cells on a square 5×5 grid means the conv kernel's neighbourhood
  does not match hex adjacency. With a 4-block tower the receptive field covers
  the whole board anyway, so the network can learn the true adjacency. Worth a
  sentence in the writeup; not worth a hex-conv implementation in v1.

## Alternatives considered

**Flat 1950-logit policy head.** The literal AlphaZero design. Rejected as the
default on parameter-efficiency grounds, but explicitly retained as the
fallback if the independence assumption proves too costly. The comparison
between the two is a legitimate experiment for Phase 4.

**Reuse `pgx` or `open_spiel`.** Would supply tested self-play plumbing. Rejected
for v1: the roadmap's stated skill goal is "implemented from first principles",
and FLIPHEX's action space would need a custom registration in either framework
anyway. Revisit if the training loop becomes the bottleneck.

**Larger network (10+ blocks, 128+ filters).** Rejected until the small one
demonstrably plateaus. Starting small makes the training curve legible and the
"grew the network because X" decision documentable — which is itself portfolio
material.

**AlphaZero-style with a learned model (MuZero).** Out of scope. The rules are
known and cheap to simulate; there is nothing to gain.

## Related

- [adr-003](adr-003-piece-representation.md) — why no orientation planes
- [adr-004](adr-004-solver-approach.md) — the ground truth this is compared against
- `docs/research.md` — H3, H5
