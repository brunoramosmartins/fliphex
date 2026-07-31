# ADR-009 — Reduced-deck policy for small board variants

**Status:** Proposed
**Date:** 2026-07-31
**Deciders:** Bruno Ramos Martins
**Needs:** author ratification; ideally a check against the physical game (see
OPEN-3).

## Context

[adr-004](adr-004-solver-approach.md) parameterises the board as
`(n_columns, cells_per_column, deck)` and calls for "proportionally smaller
decks" on the 3×3 and 4×4 variants, but never says **which** tiles a reduced
board draws. That gap is load-bearing:

- **It decides solvability.** The Phase 2 complexity sweep shows the reduced-deck
  size swings the state-space bound by ~3 orders of magnitude — for 4×4,
  8.3 × 10¹³ with the full 13-piece deck versus 9.3 × 10¹⁰ with a minimal deck.
  One is borderline; the other is comfortably enumerable.
- **It decides meaning.** A badly chosen reduced deck makes the *exact solve*
  validate a game that is not a faithful shrink of FLIPHEX. Since the exact
  solve is the project's strongest claim (H1/H2 on a real FLIPHEX-family game),
  the deck must be principled, not incidental.

The tension is real. The full 12-archetype deck is a **theorem** — the complete
set of binary bracelets of length 6 ([adr-003](adr-003-piece-representation.md),
[piece-archetypes.md](../piece-archetypes.md)). Any strict subset loses that
completeness, so no reduced deck is a "faithful" shrink in the strong sense.
Faithfulness becomes a judgment call — which is exactly why it needs an ADR.

The 13 pieces per player, in ascending arrow count:

`joker`(0) · `P1`(1) · `P2-adj` `P2-skip` `P2-opp`(2) · `P3-fan` `P3-y` `P3-tri`(3)
· `P4-adj` `P4-skip` `P4-opp`(4) · `P5`(5) · `P6`(6).

## Decision (proposed)

For a board with capacity `a = ⌈N/2⌉` placements for the first player, the
**default reduced deck** is the `a`-tile set chosen by this priority:

1. **Always include `P6` and `P3-y`.** These two carry the dynamics the study
   exists to probe: `P6` is the maximum-flip tile (all six arrows — the largest
   possible swing), and `P3-y` is the sole **chiral** tile — the piece whose
   reflection leaves the deck and thereby breaks the board's Z/2 mirror at the
   game level ([adr-008](adr-008-board-mirror-symmetry.md)). A reduced game that
   keeps both still exercises the flip mechanic *and* the H1/mirror question.
2. **Fill the remaining `a − 2` slots by ascending arrow count** from the tiles
   not yet chosen (`P1`, then the 2-arrow group, then the rest). This spans the
   low-to-high "power" range instead of clustering at one flip strength.
3. **The joker is included only when H2 (the joker hypothesis) is under test on
   that variant.** Otherwise it is left out, keeping the reduced deck purely
   archetypal.

Worked examples:

- **3×3** (`a = 5`): `{P6, P3-y, P1, P2-adj, P2-skip}` (+ joker if testing H2).
- **4×4** (`a = 8`): `{P6, P3-y, P1, P2-adj, P2-skip, P2-opp, P3-fan, P3-tri}`.

Both players draw from an identical reduced deck, consistent with the
`OPEN-2`-resolved finding that the two physical decks are the same (no chiral
seat confound).

## Consequences

**Positive**

- The 4×4 exact solve lands near 9 × 10¹⁰ states, comfortably enumerable, so
  H1/H2 get an exact verdict on a *strategically non-trivial* board — a stronger
  result than 3×3 alone.
- Every reduced variant keeps the two most dynamically interesting tiles, so the
  solve speaks to the same questions as the full game rather than a toy.

**Negative / accepted costs**

- This is a **modeling choice, not a faithful shrink** — the reduced deck is not
  a complete bracelet enumeration, so results transfer to the full 5×5 as
  *evidence*, not proof. The writeup must state the deck explicitly with every
  reduced-board result.
- Ascending-arrow fill is a defensible default, not the only one; a different
  fill could change fine-grained tactics on very small boards.

## Alternatives considered

- **Full 13-deck, unused pieces.** Most faithful to "same deck, smaller board",
  and needs no selection rule — but ~3 orders of magnitude more expensive
  (4×4 → 8.3 × 10¹³, borderline) and it lets the player choose among tiles that
  will never fit, which is arguably *less* faithful to the tempo of a small game.
- **Random subset per seed.** Tests robustness to deck composition, but muddies
  interpretation of any single solve. Better as a *stretch* robustness check on
  top of the fixed default than as the default itself.
- **Arrow-count-balanced subset** (one of each count as far as possible).
  Reasonable, but does not guarantee `P6`/`P3-y` on the smallest boards, which
  are the two tiles the study most wants present.

## Open question

**OPEN-3.** Is a reduced FLIPHEX board something the physical game supports at
all, or is it a purely **computational device**? If purely computational, then
faithfulness is judged against the shipped 5×5, not a physical artifact, and this
ADR is entirely a modeling decision. If the physical set implies a natural
reduced deck (e.g. a printed 3×3 teaching variant), that should override the
default here. To be checked with the game's author before Phase 3 locks the
solver's variant list.

## Related

- [adr-003](adr-003-piece-representation.md) — the deck-as-theorem and the state bound
- [adr-004](adr-004-solver-approach.md) — the solver that consumes this deck
- [adr-008](adr-008-board-mirror-symmetry.md) — why `P3-y` is kept in every variant
- `docs/research.md` — H1, H2, and the (optional) counterfactual H6
