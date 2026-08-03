# ADR-008 — The board has a mirror symmetry (Z/2), not a trivial group

**Status:** Accepted (Phase 2)
**Date:** 2026-07-29
**Deciders:** Bruno Ramos Martins (co-designer)
**Amends:** the "trivial symmetry group" claim in
[board-geometry.md](../board-geometry.md).

## Context

Phase 0 concluded that the board has a **trivial symmetry group**. The argument
in `board-geometry.md` is: columns A, C, E sit at vertical offsets 0..4 while B
and D sit at 0.5..4.5, so the two sets have different vertical centres and "no
rotation or reflection maps the cell set onto itself." This was used to justify
three downstream claims: no data augmentation for Axis 2, no transposition-table
canonicalisation for Axis 1, and that H1 (first-player advantage) must be settled
computationally because there is no strategy-stealing argument.

Studying **AlphaZero (Silver 2018)** put pressure on this. AlphaZero *drops*
symmetry augmentation precisely because chess and shogi are asymmetric, and was
read as the closer template for FLIPHEX. That prompted a direct check of
FLIPHEX's symmetry rather than trusting the Phase 0 prose.

## Decision

Adopt the computed result: the automorphism group of the board — as a **directed
hex graph** (adjacency *and* the six arrow directions the flip rule consumes) —
is **Z/2**. Its non-trivial element is a **left-right mirror across column C**:

- Cells: `A ↔ E`, `B ↔ D`, column `C` fixed (same row throughout).
- Directions: `N → N`, `S → S`, `NE ↔ NW`, `SE ↔ SW`.
- **180° rotation is _not_ a symmetry** (columns B and D are staggered half a
  cell, so a half-turn lands them off the grid; and 25 is odd, so any involution
  must fix a cell — the mirror fixes column C, a rotation would fix none).

Computed by `scripts/check_symmetry.py` (brute force over the 12 dihedral
direction actions × all cell permutations), pinned by `tests/test_symmetry.py`,
and confirmed to hold on the 3×3 reduced variant as well.

### Why the Phase 0 argument was wrong

The "different vertical centres" observation is true but does not imply
triviality. The mirror maps A↔E and C↔C **within** the offset-0 group and B↔D
**within** the offset-0.5 group — it never equates an offset-0 column with an
offset-0.5 one, so the differing centres are irrelevant to it. The Phase 0 prose
only ruled out symmetries that *mix* the two groups (90° rotation, top-bottom
mirror, 180°), which do indeed fail.

The doc's own degree evidence in fact **contains** the mirror: it names `A1` and
`E1` as the two degree-2 cells and then claims they "have no degree-2 partners" —
but the mirror makes them each other's image. `C1` (deg 3) and `C5` (deg 5) lie
on the mirror axis and are fixed points, so they need no partner.

## Scope — board symmetry vs. game symmetry (the chiral-tile obstruction)

This is a symmetry of the **board geometry and the flip rule**, not automatically
of the game *dynamics*. The mirror reflects arrow patterns, and the deck is closed
under reflection **except** the single chiral piece `P3-y`, whose mirror is a
distinct pattern **no player holds**. Mirroring a move that places `P3-y` would
require a tile with the reflected arrow pattern, which is in neither hand, so the
mirrored move cannot reproduce the mirrored outcome. (Checked by hand: `P3-y` =
arrow slots {0,1,3}; its reflection {0,3,5} is not a rotation of {0,1,3}.)

- **Board-level automorphism: Z/2 — confirmed, unconditional.**
- **Game-level (dynamics) symmetry: broken while a `P3-y` remains in either
  hand.** Once *both* `P3-y` tiles are placed they are inert (adr-003), the
  obstruction vanishes, and the mirror *is* a symmetry of the remaining sub-game.
  So the usable symmetry is **partial — restricted to states with no `P3-y` in
  hand.**

**Relation to OPEN-2 (RESOLVED 2026-07-29).** The two decks' `P3-y` tiles are
*identical* (same manufacturing mould, same chirality), **not** mirror images.
This settles **seat equivalence** — both players hold `(0,1,3)` on their own face
— so there is **no deck confound for H1**. It does *not* grant the mirror
augmentation: the obstruction is the mere *existence* of a chiral tile,
independent of how the two decks relate. (A colour-swapping mirror
τ = mirror ∘ swap-colours would need *mirrored* decks, which these are not, and
would be broken anyway by the joker / first-move asymmetry.) An earlier draft of
this ADR wrongly tied the augmentation to OPEN-2; corrected here.

## Consequences

**Positive — but partial (endgame-restricted)**

- **Mirror-canonical transposition keys** for Axis 1 and MCTS, valid on states
  where neither player still holds `P3-y` (both already placed). Useful for
  endgame databases and late-game search, not the whole tree.
- **Data augmentation** for Axis 2 is valid on that same sub-space only — *not* a
  clean whole-game 2×, since the chiral tile blocks it earlier. Treat any mirror
  augmentation as an ablation to measure, not a free win.
- Applies to the 3×3/4×4 reduced variants (same Z/2, same chiral-tile caveat).

**Unchanged — H1 still needs computation**

- The mirror **preserves the player to move**; it is *not* a colour/player swap.
  So it yields **no strategy-stealing or pairing argument for H1**. The Phase 0
  *conclusion* about H1 stands — only its stated *premise* ("no symmetry") was
  wrong. H1 must still be settled by the solver and self-play.

**Documentation edits (applied)**

- `board-geometry.md` is **generated**: the §symmetry prose was corrected in
  `scripts/build_docs.py` and the file regenerated; the generated file is not
  hand-edited.
- The augmentation opportunity should be noted in
  [adr-005](adr-005-alphazero-scope-and-network.md) and the canonicalisation
  opportunity in [adr-004](adr-004-solver-approach.md) when those axes begin.

## Alternatives considered

- **Keep "trivial symmetry group."** Rejected: it is computationally false
  (`|Aut| = 2`), and the doc's own degree data exhibits the counterexample.
- **Claim the full 2× game augmentation now.** Rejected: premature. The
  game-level symmetry is conditional on OPEN-2; only the board-level symmetry is
  unconditional today.

## Related

- `scripts/check_symmetry.py`, `tests/test_symmetry.py` — the computation and its
  regression test.
- **OPEN-2** in [rules-canonical.md](../rules-canonical.md) — the chiral tile that
  decides whether the game inherits the board's mirror.
- [board-geometry.md](../board-geometry.md) — the amended claim.
- [adr-004](adr-004-solver-approach.md) (canonicalisation),
  [adr-005](adr-005-alphazero-scope-and-network.md) (augmentation).
- [notes/silver-2018-alphazero.md](../../notes/silver-2018-alphazero.md) §1.2/§3.1
  — the reading that prompted the check.
