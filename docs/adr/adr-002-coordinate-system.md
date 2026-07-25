# ADR-002 — Axial coordinates internally, `A1`–`E5` offset labels externally

**Status:** Accepted (Phase 0)
**Date:** 2026-07-23
**Deciders:** Bruno Ramos Martins

## Context

The physical board is a honeycomb of flat-top hexagons in five vertical columns
of five cells, odd columns dropped half a cell (established from the poster
photographs; see [board-geometry.md](../board-geometry.md)).

Hex grids admit several standard coordinate systems, and the choice propagates
into every module: adjacency, the flip rule, Zobrist hashing, the network's
input tensor, notation, and the UI. Getting it wrong is expensive to undo, which
is why it is an ADR.

The specific difficulty: in **offset** coordinates the six neighbour deltas
depend on column parity, so the flip rule becomes a case analysis. In **axial**
coordinates the deltas are six constants.

## Decision

Use **two representations with a clear division of labour**:

- **Axial `(q, r)` is canonical inside the engine.** Neighbour lookup is
  `(q, r) + AXIAL_DELTAS[direction]` with no parity branch.
- **Offset labels `A1`–`E5` are canonical at every boundary** — notation,
  logs, the CLI, replay files, docs, and issue titles.

Conversion (odd-q, flat-top): `q = col`, `r = row - (col - (col & 1)) // 2`.

Directions are indexed **clockwise from North**: `N=0, NE=1, SE=2, S=3, SW=4,
NW=5`, with rotation `k` mapping slot `i` to `(i + k) mod 6` and opposite
directions differing by 3.

Concretely, the engine stores the board as a **flat 25-element array** indexed
by cell id, with adjacency precomputed once into a `25 × 6` table of cell ids
(`-1` off-board). Axial coordinates are how that table is *built*; they are not
carried around at runtime.

## Consequences

**Positive**

- The flip rule is a six-iteration loop over a precomputed table — no geometry
  at runtime, which matters when the solver evaluates 10⁹ nodes.
- Direction indexing and rotation are the same `mod 6` arithmetic everywhere, so
  piece rotation and board adjacency compose without conversion.
- Humans never see axial coordinates. `C3` is legible in a log; `(2, 1)` is not.
- The `25 × 6` table is small enough to print in full in the docs, which is what
  makes the Phase 0 exit criterion ("every cell has a fully specified neighbour
  list") literally checkable.

**Negative / accepted costs**

- Two representations means a conversion layer and the risk of leaking one into
  the other. Mitigated by keeping conversion in `board.py` only, and by
  `notation.py` being the sole producer of `A1`-style strings.
- Generalising to the reduced variants of Phase 3 (3×3, 4×4) requires the
  adjacency table to be built per-variant rather than hardcoded. That is a
  feature, not a cost, but it must be designed in from the start.

**Neutral**

- The board has a **trivial symmetry group** (see board-geometry.md), so there
  are no board symmetries to exploit for canonicalisation in the transposition
  table or for data augmentation in Axis 2. This is a real loss relative to
  Reversi or Go, where 4–8× augmentation is free. Better to know now.

## Alternatives considered

**Offset `(col, row)` only.** Simplest to read, but every neighbour computation
carries a parity branch, and rotation composition gets fiddly. Rejected: the
flip rule is the hottest code path in the project.

**Cube coordinates `(x, y, z)` with `x+y+z=0`.** Elegant, and rotation is a
coordinate permutation. Rejected as redundant: axial carries the same
information in two integers, and the project never needs cube-only operations
like distance or line-drawing.

**Row-major flat index with a hand-written neighbour table.** What the engine
effectively compiles to. Rejected as the *authoring* representation because a
hand-written 25×6 table is unreviewable and untestable; generating it from
axial coordinates and asserting symmetry is how `scripts/gen_board_geometry.py`
proves it correct.

## Related

- [board-geometry.md](../board-geometry.md) — the generated adjacency table
- `scripts/gen_board_geometry.py` — the generator and its symmetry check
- [adr-003](adr-003-piece-representation.md)
