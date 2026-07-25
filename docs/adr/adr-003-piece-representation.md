# ADR-003 — Pieces as 6-bit masks; placed tiles collapse to a colour

**Status:** Accepted (Phase 0)
**Date:** 2026-07-23
**Deciders:** Bruno Ramos Martins

## Context

A tile has an arrow pattern (a subset of six edge slots), a rotation, a colour,
and a deck membership. The naive state representation stores all of it for all
25 cells, which is what the roadmap's Phase 2 exercise assumes when it puts a
factor of `6^25` in the state-space bound.

That factor is wrong, and noticing why is the single most consequential
modelling decision in Phase 0.

**A placed tile's arrows fire exactly once, on the ply it is placed, and never
again** — because there is no chain reaction
([adr-006](adr-006-no-chain-reaction.md)). From ply *t+1* onward, a tile placed
at ply *t* is indistinguishable from a bare coloured token. Its pattern and its
rotation cannot influence any future legal move, flip, or outcome.

## Decision

**Arrow patterns are 6-bit integers.** Slot `i` is bit `i`, indexed clockwise
from North per [adr-002](adr-002-coordinate-system.md). Rotation by `k` is a
6-bit circular left shift. The 12 archetypes are module-level constants derived
in `scripts/gen_piece_archetypes.py`; `Piece` is a frozen dataclass of
`(archetype_id, mask)`, not a class hierarchy.

**The game state stores, per cell, only `EMPTY | PURPLE | GREEN`.** Which tile
sits where is *not* part of the state used for search, hashing, or the network.

**Hands are 13-bit and 12-bit bitmasks** over each player's tiles (Player 1's
includes the joker), because what matters is which archetypes remain, not their
identity.

**Placement history — cell, archetype, rotation per ply — is kept in a separate
append-only list** on the state, used exclusively by `notation.py`, the replay
viewer, and Phase 6's archetype-usage analysis (H5). Nothing in the search or
the network may read it.

So: `GameState = (cell_colours[25], hand_p1_mask, hand_p2_mask, to_move)` for
search; `+ history[]` for humans.

## Consequences

**Positive — this is the headline**

State-space upper bound over reachable ply counts:

| Representation | Bound |
|---|---|
| Storing rotation per cell (`× 6^25`) | ~1.4 × 10³⁷ |
| **This decision** | **~4.9 × 10¹⁷** |

A reduction of **19.5 orders of magnitude**, computed as
`Σₜ C(25,t) · 2ᵗ · C(13,⌈t/2⌉) · C(12,⌊t/2⌋)`. Downstream:

- Transposition tables become genuinely effective. At 10¹⁷ states a
  16-byte-per-entry table covers a meaningful slice of the reachable endgame;
  at 10³⁷ it would be noise.
- Retrograde endgame databases (Phase 3) become feasible for larger `k`.
- The network input tensor drops from ~7 channels of orientation encoding to
  3 board planes plus 2 hand vectors — a much smaller model on the same GPU.
- **Transpositions actually exist.** Two different move orders reaching the same
  colouring with the same tiles spent are the same node. With rotation stored
  they would almost always differ, and the "transposition" table would be a
  slow cache with a ~0% hit rate.

**This invalidates exercise 6 of `exercises/ex02_game_theory.md` as written.**
The roadmap's suggested bound includes `6^25` and a `binom` term that
double-counts. The exercise should be reframed as: derive the naive bound,
notice the inertness argument, and derive the corrected one. That is a better
exercise anyway — it is the actual insight.

**Negative / accepted costs**

- The history list is a second source of truth about the board. Mitigated by
  making it strictly write-only from the engine's perspective and asserting in
  `tests/test_state.py` that replaying the history reproduces `cell_colours`.
- H5 (archetype usage) depends on the history, so self-play records must retain
  it. That is a serialisation requirement, not a search requirement.
- If a future rule variant introduces chain reactions, this collapses. Explicit
  in [adr-006](adr-006-no-chain-reaction.md): such a variant is a different
  game and gets its own state class.

**Neutral**

- Zobrist hashing keys on `(cell, colour)` and `(player, tile)` only — 25 × 2 +
  25 random words. Incremental update is O(1) per flip.

## Alternatives considered

**Store the full placed tile per cell.** The obvious model, and wrong for this
game: it inflates the state space by 10¹⁹ for information that provably cannot
affect play. Rejected.

**Drop the history entirely.** Smallest possible state, but kills H5 and makes
replays impossible. Rejected — the cost of an append-only list is trivial and
it is never touched by hot code.

**Class hierarchy for archetypes.** Rejected: 12 constants and a bitmask are
faster, hashable for free, and rotation is one shift instead of a method call.

## Related

- [piece-archetypes.md](../piece-archetypes.md) — the 12 tiles and why there are 12
- [adr-006](adr-006-no-chain-reaction.md) — the premise this decision rests on
- [adr-004](adr-004-solver-approach.md) — what the smaller state space buys
