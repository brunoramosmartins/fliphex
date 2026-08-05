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

~~**No symmetry augmentation.** The board's symmetry group is trivial (adr-002),
so unlike Go's 8× or Connect Four's 2×, there is none to exploit.~~
**Decision unchanged, justification superseded** — see the Phase 2 amendment
below and [adr-008](adr-008-board-mirror-symmetry.md). The board *does* have a
Z/2 mirror; augmentation is still rejected, on measured grounds.

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

## Amendment — Phase 2 (2026-08-05): symmetry justification, the evaluator gate, and two guard rails

Reading R&N Ch.6, Silver 2017/2018 and Schaeffer 2007 produced four refinements.
None changes the network; one corrects a false premise, two add decisions the
original ADR left implicit, and one closes a methodological trap.

**1. The "no augmentation" justification was wrong; the decision survives.** The
board's symmetry group is **not** trivial — it is Z/2, a left-right mirror across
column C ([adr-008](adr-008-board-mirror-symmetry.md)). The struck bullet above
is replaced by:

> **No symmetry augmentation.** The board has a Z/2 mirror, but the chiral
> `P3-y` tile makes it a *partial* game symmetry: the mirror of a legal move need
> not be legal, so `M(s)` may not be augmented while either copy of `P3-y` is in
> a hand. Every tile is played (rules-canonical §2, I3/I5), so the condition is
> always reached — but late: under a uniform-random play order the second `P3-y`
> lands on ply 17.2 on average, leaving ≈**31 %** of plies augmentable. The
> available gain is therefore ≈**1.31×** in data, against a per-sample validity
> check and the risk that a wrong check silently trains the policy toward a move
> that does not exist. Not worth it.

Verified by `scripts/check_mirror_game_symmetry.py`: 150 of the 1450 opening
moves have no legal mirror image, all of them `P3-y`; the mirror becomes a full
game symmetry exactly once both copies are placed and inert.

**2. The evaluator gate is RETAINED, with an explicit game budget.** AlphaGo Zero
promotes a challenger only at ≥55 % over 400 games; AlphaZero drops the gate.
That removal is **bundled** with several other changes (single continuously
updated network, self-play from the current rather than the best network, reused
hyper-parameters) and no experiment in either paper isolates it — so the
published evidence is "a system without the gate works", not "the gate is
unnecessary". AlphaZero's replacement is a large replay buffer plus small
continuous updates, which damps regressions by construction but was never
measured. On a single laptop, where a collapsed run costs days and there is no
external benchmark for an original game, the discrete measured guard is worth its
compute.

The budget is not optional. At n = 400 evaluation games, two equal networks clear
55 % about 2 % of the time; at n = 100 they clear it **16 %** — a gate promoting
noise one time in six is worse than no gate, because it also manufactures
confidence. Adopt **400 games at 55 %**, or an explicit relaxation (gate every
`k` generations, or a lower threshold with its false-promotion rate stated).
Removing the gate is a Phase 4 optimisation to be justified by measurement, never
inherited from AlphaZero by default.

**3. Plain UCT with random playouts is the Axis-2 baseline.** AlphaZero makes two
substitutions and they have different standing for FLIPHEX. Replacing UCB1 with
PUCT is **required**: `√(ln N / n(a))` is infinite at `n(a) = 0`, so prior-free
selection must visit all 1450 opening children before it distinguishes any of
them, and UCB1's distribution-free regret guarantee needs far more simulations
than a laptop will run. Dropping rollouts is **inherited, not forced**: FLIPHEX
playouts are ≤25 plies, always terminate and always yield a decided winner, so
R&N §6.4's early-playout-termination machinery is void. Plain UCT is therefore
cheap to build and gives an absolute floor that depends on no trained network.
The learned agent must beat it before any result is reported.

**4. Checkpoint selection may not read Axis 1.** Scoring candidate networks
against the exact 4×4 database is tempting — near-zero compute, an objective
yardstick where none otherwise exists — and it is **circular**: selecting
networks by agreement with the solver and then reporting agreement with the
solver as H3's evidence optimises the metric directly. Solver positions may be
logged, plotted and watched as a *reported diagnostic*; no promotion,
early-stopping or checkpoint-selection decision may read them. This is the mirror
image of the rule [adr-004](adr-004-solver-approach.md) adopts for the other
direction, and the general form is stated there: *neither axis may be used to
select or terminate the other along the dimension on which they are later
compared.*

## Related

- [adr-003](adr-003-piece-representation.md) — why no orientation planes
- [adr-004](adr-004-solver-approach.md) — the ground truth this is compared against
- [adr-008](adr-008-board-mirror-symmetry.md) — the mirror that does *not* fund augmentation
- [adr-010](adr-010-solver-correctness.md) — the verification the diagnostic in (4) reads from
- `docs/research.md` — H3, H5
- `notes/phase2-synthesis.md` — S1, S2, S3 (the readings behind the amendment)
