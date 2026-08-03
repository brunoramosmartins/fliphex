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

- ~~No board symmetries to canonicalise with (the board's symmetry group is
  trivial, per adr-002), so the TT gets no free symmetry folding.~~
  **Superseded** — see the Phase 2 amendment below and
  [adr-008](adr-008-board-mirror-symmetry.md): the board has a Z/2 mirror, and
  it is usable for TT folding *in the endgame databases*.

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

## Amendment — Phase 2 (2026-07-31): Allis 1994 grounding + intermediate-board frontier

Reading Allis (1994) *Searching for Solutions* produced three refinements. None
overturns the decision; two sharpen it and one corrects a stale premise.

**1. Allis's taxonomy confirms alpha-beta + retrograde over proof-number
search.** FLIPHEX classifies as **diverging** (a tile is *added* each ply) and
**fixed-termination** (ends at ply 25 by board-fill, with no sudden-death
pattern) — the Othello profile. Allis: endgame databases are creatable for
*converging* games and "generally unfeasible for diverging" ones; and fixed
termination "renders solving the game in similar fashion to the solution of
qubic and go-moku impossible." Two consequences for this ADR:

- Proof-number search (the alternative parked under *Alternatives considered*)
  shines on **sudden-death** goal-proving — proving a forced threat sequence, as
  in qubic and go-moku. FLIPHEX has no such goal to prove, so pn-search loses its
  structural edge here. The reading therefore *strengthens* the original
  alpha-beta + TT choice rather than reopening it.
- The diverging nature is exactly *why* the retrograde databases must stay
  shallow: the position count grows fast as you recede from the full board.
  The `k ≤ 5` target is now justified, not merely assumed.

**2. There is a solvable-and-rich intermediate board — the 4×4 (16 cells).**
Computing the reachable bound (the adr-003 formula) across board sizes:

| Board | cells | full 13-deck | reduced deck |
|---|--:|--:|--:|
| 3×3 | 9 | 3.1 × 10⁹ | 7.1 × 10⁵ |
| 4×4 | 16 | 8.3 × 10¹³ | 9.3 × 10¹⁰ |
| 5×5 (shipped) | 25 | — | 4.9 × 10¹⁷ |

The full-enumeration frontier sits at **N ≈ 13–15** (≈10¹²–10¹³). This sharpens
part 1 of the Decision ("solve 3×3, attempt 4×4"):

- **3×3 is a correctness fixture, not a strategy microcosm.** At 9 cells it is
  too cramped for tactics like deferring a flip to set up a larger later swing.
  It validates the engine, the search, and the H3 cross-check — it is *not*
  claimed to reveal 5×5 strategy, and the writeup must not imply otherwise.
- **4×4 is promoted from "attempt" to the primary exact-solve target for
  strategic claims.** 16 cells give room for spatial/tempo tactics, and
  8.3 × 10¹³ (full deck) — or 9.3 × 10¹⁰ with a reduced deck, ~3 orders of
  magnitude cheaper — is within reach of retrograde analysis on modern storage.
  3×3 stays the fast calibration solve; 4×4 carries the H1/H2 exact verdicts.

**3. Symmetry correction (supersedes the struck "Neutral" bullet).** The claim
that the board's symmetry group is trivial is wrong — [adr-008](adr-008-board-mirror-symmetry.md)
established a Z/2 left-right mirror. The mirror is a *game-level partial*
symmetry: it holds only once **both** chiral `P3-y` tiles are placed and inert.
That condition is met **precisely in the endgame** — exactly where the
retrograde databases live. So the endgame DBs (and the TT within them) **can**
fold mirror-image positions ~2×, a saving this ADR originally assumed
unavailable. Full-game alpha-beta still gets no folding while a `P3-y` is in a
hand.

**Open item forwarded.** "Proportionally smaller decks" (Decision, part 1) is
still undefined — *which* tiles a reduced board draws. That choice swings the
4×4 bound by ~3 orders of magnitude (table above) and decides whether a reduced
solve is a faithful shrink of FLIPHEX. Pinned in
[adr-009](adr-009-reduced-deck-policy.md) (Accepted): keep `P6` + `P3-y`, fill by
ascending arrow count; reduced boards are a purely computational device
(OPEN-3 resolved), so faithfulness is judged against the shipped 5×5.

## Related

- [adr-003](adr-003-piece-representation.md) — the state space this rests on
- [adr-005](adr-005-alphazero-scope-and-network.md) — the axis this is compared against
- [adr-008](adr-008-board-mirror-symmetry.md) — the mirror the endgame DBs can fold on
- [adr-009](adr-009-reduced-deck-policy.md) — the reduced-deck policy this defers to
- `docs/research.md` — H1, H2, H3
