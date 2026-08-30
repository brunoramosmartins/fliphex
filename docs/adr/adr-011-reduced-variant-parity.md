# ADR-011 — Reduced variants must have an odd cell count, and P1's extra tile is the joker

**Status:** Accepted
**Date:** 2026-08-05 (ratified 2026-08-05)
**Deciders:** Bruno Ramos Martins

## Context

[adr-009](adr-009-reduced-deck-policy.md) fixed *which tiles* a reduced board
draws but left two things implicit that turn out to be load-bearing: the board's
**cell parity**, and **how the two hands are sized relative to each other**. Both
were caught in a pre-run red-team of `EXP-001`/`EXP-002`, before either
experiment ran.

### The 4×4 breaks the no-draw theorem

The 4×4 variant promoted to primary exact-solve target by the
[adr-004 Phase 2 amendment](adr-004-solver-approach.md) has **16 cells**. Scoring
is a cell count ([rules-canonical.md](../rules-canonical.md) §7), so an 8–8
terminal is reachable, and **no tie-break rule exists anywhere in the canonical
rules** — §7 derives the impossibility of draws entirely from 25 being odd.
`C(16,8) = 12,870` of the 65,536 terminal configurations are ties: roughly 20%.

Three artefacts already contradict the 4×4 on this point:

- [adr-010](adr-010-solver-correctness.md) V2 states that cell counts are odd
  *"and any `N` used must be odd for the same reason"*, and asserts the no-draw
  invariant **totally**: any draw value anywhere in the database is a proof of a
  bug. `EXP-002` listed V2 as a gate on a board where V2's premise is false.
- `fliphex/rules.py` raises `ValueError` on a tied terminal position.
- `scripts/layer_profile.py` profiles any `N` because it never checks parity.

The failure mode is the one adr-010 exists to prevent. A multi-day 4×4 sweep hits
8–8 terminals; either V2 fires and voids the run, or a tie-break is invented
mid-run under time pressure. In the second case the run terminates normally and
reports a winner where the true value is a draw — a plausible wrong answer,
decided by a convention created after the data existed, on the run that carries
the H1/H2 verdicts.

### The 4×4 also deletes the mechanism H1 is about

[rules-canonical.md](../rules-canonical.md) §6 names the source of the
first-player advantage explicitly: *"Because the joker is the 25th tile and 25 is
odd, the joker is exactly what gives Player 1 the extra ply."*

The 4×4 as configured (`a = 8`, identical decks, no joker) removes P1's extra
ply, removes the joker, and hands the **final placement to P2** — in a game whose
entire mechanic is "arrows fire once, on placement", where the last tile lands on
the fullest board and therefore has maximal flip power. The variant designated
*"the strategically meaningful exact solve"* plausibly measures a game whose
structural advantage belongs to the second player.

This makes H1 unfalsifiable on that board in the direction that matters. "P1
wins" reads as support; "P2 wins" has a ready-made dismissal ("parity artefact"),
and nothing pre-registered distinguishes the readings.

### The 4×4's symmetry is a rotation, not a mirror

Measured with `scripts/check_symmetry.py 4 4`: `|Aut| = 2`, and the non-trivial
automorphism is a **180° rotation** (`A1↔D4`, `N↔S`, `NE↔SW`), not a reflection.
That is the opposite of the 5×5, where 180° is *not* a symmetry and the
left-right mirror is ([adr-008](adr-008-board-mirror-symmetry.md)).

A rotation maps every tile's arrow pattern to another rotation of the *same*
tile, so the chiral `P3-y` does **not** break it. adr-009 clause 1 keeps `P3-y`
in every reduced deck precisely to *"keep the H1/mirror question alive"* — a
justification that is void on the 4×4, where the symmetry in play is one no tile
can break.

### adr-009's hand rule contradicts the figures already in the repo

adr-009 sets `a = ⌈N/2⌉` and says both players draw an **identical** `a`-tile
deck. On an odd board that cannot be both identical and exactly exhausting: at
`N = 9`, `a = 5` gives 5 + 5 = 10 tiles for 9 cells, a bound of 1.47 × 10⁶.

But [adr-004](adr-004-solver-approach.md) and [adr-010](adr-010-solver-correctness.md)
both quote **7.1 × 10⁵** for the reduced 3×3 — which is reproducible only with
hands of **5 + 4** (`scripts/layer_profile.py --cells 9 --hands 5 4` → 712,320).
The documented numbers have always assumed a rule adr-009 never wrote down. This
ADR writes it down, and the existing figures become correct rather than being
revised.

## Decision

**1. Reduced boards must have an odd cell count.** `N` odd is a precondition of
the no-draw theorem, of adr-010 V2, and of `fliphex/rules.py`. A reduced board
with even `N` is not a FLIPHEX variant — it is a different game requiring a
tie-break rule the design does not have. `scripts/layer_profile.py` and the
reduced-variant constructor must both reject even `N`.

**2. The hands mirror the shipped game's structure.** For a board of `N` odd
cells, let `a = (N − 1) / 2`. Then:

- **Player 2** draws `a` archetypes, selected by adr-009's priority (`P6` and
  `P3-y` first, then ascending arrow count).
- **Player 1** draws **the same `a` archetypes plus the joker**, for `a + 1`
  tiles.

`(a + 1) + a = N`, so both hands are exactly exhausted, play alternates for
exactly `N` plies, **P1 moves last**, and P1's extra tile is the joker. This is
the 5×5's own structure at smaller scale: 13 = 12 + joker against 12.

**3. The joker is structural on reduced boards, not optional.** This supersedes
adr-009 clause 3. The joker is what makes P1's hand larger, so removing it does
not produce a joker-less variant of the same board — it produces a board that
cannot be filled.

**4. H2 therefore contrasts *what P1's extra tile is*, not whether the joker is
present.** The two arms are:

| Arm | P1 | P2 | bound at `N = 15` |
|---|---|---|---|
| **H1 / shipped-faithful** | `a` archetypes + **joker** | `a` archetypes | 1.751 × 10¹⁰ |
| **H2 / joker-less** | `a + 1` **archetypes** | `a` archetypes | 1.751 × 10¹⁰ |

Both arms have `a + 1` and `a` tiles, so **the two state spaces are exactly the
same size** and the only thing that varies is whether P1's extra tile is the
zero-arrow joker or the next archetype by ascending arrow count. This is a
stronger H2 than "joker present/absent": it isolates the joker's *strategic*
content (its tempo/pass-like role) from the *structural* extra ply, which is the
distinction rules-canonical.md §6 draws and which the old design confounded.

**5. The primary exact-solve target becomes the 5×3 (15 cells).** It replaces
the 4×4, which is withdrawn as a solve target.

| | 4×4 (16) — withdrawn | **5×3 (15) — adopted** | 5×5 (25) — shipped |
|---|---|---|---|
| draws possible | **yes** | no | no |
| moves last | P2 | **P1** | P1 |
| P1's extra tile | none | **joker** | joker |
| automorphism | rot180 | **mirror A↔E, B↔D, C fixed** | mirror A↔E, B↔D, C fixed |
| `P3-y` breaks it | no | **yes** | yes |
| hands | 8 + 8 | **8 + 7** | 13 + 12 |
| bound | 9.3 × 10¹⁰ | **1.75 × 10¹⁰** | 4.9 × 10¹⁷ |
| terminal layer | 65,536 | 32,768 | 33,554,432 |

The 5×3 is 5.3× cheaper than the withdrawn 4×4 *and* structurally faithful on
every axis the 4×4 broke. Its mirror, measured with
`scripts/check_symmetry.py 5 3`, is the same reflection as the 5×5's — so
adr-008's partial-symmetry analysis and adr-010 V6 transfer to it unchanged,
which they do not to the 4×4.

**6. The 3×3 becomes `N = 9`, `a = 4`: P1 `{P6, P3-y, P1, P2-adj}` + joker, P2
the same four.** Bound 7.12 × 10⁵, matching the figure adr-004 and adr-010
already carry. It remains the correctness fixture and the adr-010 V3
double-solve artefact.

## Consequences

**Positive**

- The no-draw theorem, adr-010 V2, and `fliphex/rules.py` become true of every
  board the project solves, rather than of the 5×5 only.
- H1 is measured on a board that preserves the mechanism H1 names. A P2 win on
  the 5×3 is now genuinely informative rather than dismissible as parity.
- H2 gains a matched-size paired design, which it did not have.
- The reduced boards keep the *same* automorphism as the shipped board, so
  adr-008 and V6 transfer.
- Cheaper: 1.75 × 10¹⁰ against 9.3 × 10¹⁰.

**Negative / accepted costs**

- **The 4×4 is lost as a datapoint**, and with it the 3×3→4×4→5×5 "ladder"
  framing in H6. Odd boards near it are 15 and 17 (5.3 × 10¹¹ at `a = 8`), so
  the ladder becomes 9 → 15 → (17) → 25.
- The 5×3 is 3 rows against the 5×5's 5, so it is proportionally more *edge* than
  the 4×4 was. Arrow-count effects remain non-transferable from any reduced board
  (see Consequences of adr-009); this ADR does not fix that.
- adr-009's clause 3 and its `a = ⌈N/2⌉` formula are superseded. Its worked
  examples are now wrong and must be reissued as an amendment.
- `docs/research.md` H1's Test column names the 4×4 explicitly and was frozen at
  tag `v0.3-hypotheses`. Changing it is a post-lock edit and must be recorded as
  an amendment with its reason, not a silent rewrite. (Note that the file's own
  status line still reads DRAFT — see Related.)

## Alternatives considered

- **Keep the 4×4 and define a tie-break.** Costs a three-valued H1 on that board,
  invalidates adr-010 V2 as a total assertion, and makes the reduced variant
  differ from the shipped game in its *outcome space* — the deepest kind of
  infidelity available. Rejected.
- **Keep the 4×4 but treat draws as second-player wins.** A convention with no
  basis in the rules; it would silently decide ~20% of terminals by fiat.
  Rejected.
- **17 cells instead of 15.** Preserves everything the 5×3 does and is closer in
  size to the 5×5, but at 5.3 × 10¹¹ it is ~30× more expensive and 17 is not a
  rectangle — it needs an irregular board the geometry generator does not
  produce. Held as a stretch target if the 5×3 proves too small to be
  interesting.
- **Both players draw identical decks on an odd board (5 + 5 at `N = 9`).**
  Preserves adr-009's literal wording, but leaves a tile unplayed, breaks exact
  exhaustion, and contradicts the 7.1 × 10⁵ figure already documented. Rejected.

## Related

- [adr-004](adr-004-solver-approach.md) — names the 4×4 as primary target; needs
  an amendment
- [adr-009](adr-009-reduced-deck-policy.md) — superseded in clause 3 and in the
  `a = ⌈N/2⌉` formula
- [adr-008](adr-008-board-mirror-symmetry.md) — the mirror, which the 5×3 keeps
  and the 4×4 did not
- [adr-010](adr-010-solver-correctness.md) — V2's odd-`N` requirement, now
  enforced rather than assumed
- `docs/research.md` — H1's Test column, H2, and the H6 ladder framing
- `experiments/registry.md` — `EXP-001`, `EXP-002`
