# ADR-009 — Reduced-deck policy for small board variants

**Status:** Accepted
**Date:** 2026-07-31 (ratified 2026-07-31)
**Deciders:** Bruno Ramos Martins

## Context

[adr-004](adr-004-solver-approach.md) parameterises the board as
`(n_columns, cells_per_column, deck)` and calls for "proportionally smaller
decks" on the 3×3 and 4×4 variants, but never says **which** tiles a reduced
board draws. That gap is load-bearing:

- **It decides solvability.** The Phase 2 complexity sweep shows the reduced-deck
  size swings the state-space bound by ~3 orders of magnitude — for 4×4,
  4.8 × 10¹³ with the full deck versus 9.3 × 10¹⁰ with a minimal deck.
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
  (4×4 → 4.8 × 10¹³, borderline) and it lets the player choose among tiles that
  will never fit, which is arguably *less* faithful to the tempo of a small game.
- **Random subset per seed.** Tests robustness to deck composition, but muddies
  interpretation of any single solve. Better as a *stretch* robustness check on
  top of the fixed default than as the default itself.
- **Arrow-count-balanced subset** (one of each count as far as possible).
  Reasonable, but does not guarantee `P6`/`P3-y` on the smallest boards, which
  are the two tiles the study most wants present.

## OPEN-3 — RESOLVED (2026-07-31): reduced boards are a purely computational device

The game's author confirms that reduced FLIPHEX boards have **no physical
counterpart** — they exist only as a computational instrument for exact solving.
Consequences:

- **Faithfulness is judged against the shipped 5×5**, not against any physical
  artifact. This ADR is therefore entirely a modeling decision, and the default
  above stands without needing to match a printed variant.
- There is no external constraint on the reduced deck, so the `P6` + `P3-y`
  anchor and the ascending-arrow fill are free to optimise for *what the study
  wants to observe* (max-flip dynamics and the chiral/mirror question) rather
  than for physical fidelity.
- Any reduced-board result must be reported as evidence *about the 5×5 design*,
  carrying its board size and deck explicitly — never as a game in its own right.

## Amendment — Phase 3 (2026-08-05): parity, hand sizes, and clause 3

Superseded in part by [adr-011](adr-011-reduced-variant-parity.md). **Clause 1
and clause 2 stand unchanged** — `P6` and `P3-y` first, then ascending arrow
count. What changes is the capacity formula, the symmetry of the two hands, and
the joker's status.

**1. `a = ⌈N/2⌉` is replaced by `a = (N − 1) / 2`, and `N` must be odd.** The
board-size formula was written without a parity constraint, which is how the 4×4
(16 cells) became a target on a game whose no-draw theorem depends on odd cell
counts. adr-011 makes odd `N` a precondition.

**2. "Both players draw an identical reduced deck" is superseded.** It cannot
hold on an odd board together with exact exhaustion: at `N = 9`, `a = 5` gives
5 + 5 = 10 tiles for 9 cells. The rule becomes **P2 draws `a` archetypes; P1
draws the same `a` plus the joker**, so `(a + 1) + a = N`. Both hands exhaust
exactly, P1 moves last, and P1's extra tile is the joker — the shipped 5×5's own
structure (13 = 12 + joker against 12) at smaller scale.

This is not a revision of the project's figures but a *correction of this ADR to
match them*: [adr-004](adr-004-solver-approach.md) and
[adr-010](adr-010-solver-correctness.md) both already quote 7.1 × 10⁵ for the
reduced 3×3, which is reproducible only with hands of 5 + 4 — the rule above.
The identical-decks wording never produced the numbers the repo was using.

**3. Clause 3 is withdrawn.** The joker is **structural**, not conditional on H2
being under test: it is what makes P1's hand larger, so removing it leaves the
board unfillable. H2's contrast becomes *what P1's extra tile is* — the
zero-arrow joker, or the next archetype by ascending arrow count — with both arms
holding `a + 1` and `a` tiles and therefore identically sized state spaces.

**4. The worked examples are reissued.**

| Board | cells | `a` | P2 draws | P1 draws (H1 arm) | bound |
|---|--:|--:|---|---|--:|
| 3×3 | 9 | 4 | `{P6, P3-y, P1, P2-adj}` | the same four **+ joker** | 7.12 × 10⁵ |
| **5×3** | **15** | **7** | `{P6, P3-y, P1, P2-adj, P2-skip, P2-opp, P3-fan}` | the same seven **+ joker** | **1.75 × 10¹⁰** |

The H2 arm swaps the joker for the next archetype: `P2-skip` on the 3×3,
`P3-tri` on the 5×3. The old 4×4 example (`a = 8`) is withdrawn.

**5. Clause 1's justification for `P3-y` is board-dependent, and this was not
noticed.** `P3-y` is kept because its reflection leaves the deck and so breaks
the board's Z/2 mirror at the game level. That reasoning requires the board's
automorphism to *be* a reflection. Measured with `scripts/check_symmetry.py`, the
4×4's non-trivial automorphism is a **180° rotation**, which no tile can break —
so on that board the justification was void. The 5×3's is the same mirror as the
5×5's (`A↔E`, `B↔D`, `C` fixed), so clause 1 holds there as intended. **Any
future reduced board must have its automorphism group measured and recorded
before its deck is justified under clause 1.**

## Related

- [adr-011](adr-011-reduced-variant-parity.md) — parity, hand sizes, and the 5×3
- [adr-003](adr-003-piece-representation.md) — the deck-as-theorem and the state bound
- [adr-004](adr-004-solver-approach.md) — the solver that consumes this deck
- [adr-008](adr-008-board-mirror-symmetry.md) — why `P3-y` is kept in every variant
- `docs/research.md` — H1, H2, and the (optional) counterfactual H6
