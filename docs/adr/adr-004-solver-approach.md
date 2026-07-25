# ADR-004 — Alpha-beta with transposition tables, plus retrograde endgames

**Status:** Accepted (Phase 0)
**Date:** 2026-07-23
**Deciders:** Bruno Ramos Martins

## Context

Axis 1 must produce **ground truth**: exact game values that the learned agent
of Axis 2 can be measured against. The question is how much of FLIPHEX is
exactly solvable and by what method.

Sizing the problem, using the corrected bound from
[adr-003](adr-003-piece-representation.md):

- Reachable states: **~4.9 × 10¹⁷**. Far too many to enumerate, so the full
  5×5 game is not weakly solvable by brute force.
- Game tree: fixed depth **25**, with a branching factor that starts at
  **1450** (25 cells × 58 distinct (tile, rotation) pairs — see
  [piece-archetypes.md](../piece-archetypes.md)) and falls as cells fill and
  hands empty.

That opening branching factor is the defining constraint. It is far above
Reversi's (~10) and Connect Four's (7), and `b^d` with `b` in the hundreds and
`d = 25` is hopeless without both pruning and a smaller `b`.

Two facts work in our favour: the depth is *fixed and shallow* (25, versus ~60
for Reversi and ~80 for chess), and the branching factor **collapses** near the
end — on ply 25 there is exactly one empty cell and one tile left, so `b = 1`.

## Decision

A three-part strategy, weakest-to-strongest coverage:

**1. Reduced variants, solved exactly.** Parameterise the board as
`(n_columns, cells_per_column, deck)` so that 3×3 and 4×4 zigzag variants with
proportionally smaller decks are first-class. Solve 3×3 exhaustively; attempt
4×4. These give exact values for H1 and H2 on a *real* FLIPHEX-family game.

**2. Alpha-beta with transposition tables on the full game**, with iterative
deepening and move ordering (TT move first, then killer moves, then a static
heuristic). Depth-limited, so it yields strong play rather than proof — used as
a strength baseline and as the opponent in H3's comparison.

**3. Retrograde endgame databases on the full 5×5.** Enumerate positions with
`k` empty cells and compute exact values backwards from ply 25. Because `b`
collapses at the end, small `k` is cheap. Target `k ≤ 5`; report whatever `k`
is achieved. Alpha-beta consults the database as a perfect evaluation function
once it reaches depth `25 − k`, which converts a heuristic search into an exact
one over the last `k` plies.

Zobrist hashing keys on `(cell, colour)` and `(player, tile)` only, per
adr-003 — 50 random words, O(1) incremental update per flip.

## Consequences

**Positive**

- H1 and H2 get *exact* verdicts on reduced variants, which is a stronger claim
  than any amount of self-play statistics, and it is the part of the project
  most likely to interest the original professor.
- Retrograde databases make endgame play provably optimal on the full game, so
  the H3 comparison against the AZ agent has a rigorous anchor rather than
  "two heuristics disagree".
- Transpositions genuinely exist thanks to adr-003, so the TT earns its keep.
  Move order permutations reaching the same colouring collapse to one node.

**Negative / accepted costs**

- The full 5×5 game will almost certainly **not** be solved. The roadmap already
  frames this correctly; the writeup must not overclaim. "Solved on 3×3,
  endgame-exact on 5×5, strong elsewhere" is the honest headline.
- Move ordering quality drives everything (`b^d` → `b^(d/2)` only with perfect
  ordering). Time spent on ordering heuristics is time well spent, and
  `exercises/ex03_alpha_beta.md` question 3 is directly on the critical path.
- The reduced-variant framework must exist from Phase 1, not be retrofitted.
  This is a Phase 1 design constraint flowing out of a Phase 0 ADR.

**Neutral**

- No board symmetries to canonicalise with (the board's symmetry group is
  trivial, per adr-002), so the TT gets no free symmetry folding. Expected, but
  it means TT hit rates will be lower than a Reversi solver's.

## Alternatives considered

**Proof-number search / PN².** Strong for binary win-loss questions with
non-uniform trees, which describes H1 well. Rejected for v1 as a second search
paradigm to implement, debug, and explain, on top of an already three-axis
project. A good extension if the paper track activates.

**Monte Carlo tree search as the Axis 1 method.** Rejected on principle: MCTS is
Axis 2's method, and using it for Axis 1 would destroy the independence that
makes cross-axis verification meaningful. The two axes must fail differently.

**Full retrograde analysis of the whole game (à la Checkers).** At 10¹⁷ states,
storage alone is prohibitive on a laptop. Rejected; the endgame slice is the
tractable, honest version of the same idea.

**Solve only reduced variants, skip the 5×5 solver.** Cheaper, but leaves Axis 2
with no strong non-learned opponent on the real game, and H3 becomes untestable
where it matters most. Rejected.

## Related

- [adr-003](adr-003-piece-representation.md) — the state space this rests on
- [adr-005](adr-005-alphazero-scope-and-network.md) — the axis this is compared against
- `docs/research.md` — H1, H2, H3
