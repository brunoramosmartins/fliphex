# FLIPHEX — Canonical Rules

**Status:** canonical. This document is the authoritative specification of the
game. Changing it requires an ADR.

**Version:** 1.0 (Phase 0)

## Provenance

FLIPHEX was designed in 2017 by students of IME-USP and FAU-USP in the course
**MAP 2001 — Matemática, Arquitetura e Design**, and exists as a physical
laser-cut wooden board with 25 hexagonal tiles.

This rulebook is reconstructed from three sources, in decreasing authority:

1. **Photographs of the physical board and pieces** on the MAP 2001 poster
   (`FLIPHEX.pdf`). Authoritative for geometry, deck composition, and arrow
   placement.
2. **Decisions by the author** (Bruno Ramos Martins, co-designer), recorded in
   `writeup/decision-journal.md`.
3. **The prose rules on the poster.** Used for structure only. The author has
   stated this text is out of date, so where it conflicts with (1) or (2) it
   loses.

Everything below is stated precisely enough to implement. Anything still open
is collected in [Open questions](#open-questions) and is flagged `OPEN-n`.

---

## 1. Components

### 1.1 Board

25 hexagonal sockets in a honeycomb: five vertical columns of five cells,
flat-top hexagons, odd columns dropped half a cell. Cells are named `A1`–`E5`.

The full coordinate system, direction indexing, and the complete adjacency
table are in **[board-geometry.md](board-geometry.md)**, which is generated
from code and is the single source of truth for adjacency.

### 1.2 Pieces

25 hexagonal tiles. Every tile is **two-sided**: purple on one face, green on
the other. A tile's visible face is its **colour**.

| Group | Count | Physical marking | Owner |
|---|---|---|---|
| Purple deck | 12 | circular hole | the player who takes purple |
| Green deck | 12 | no hole | the player who takes green |
| Joker (*coringa*) | 1 | flower-shaped hole | Player 1 |

The hole is a through-hole, so a tile's deck membership stays visible after it
changes colour. Deck membership matters only during setup — a player may never
place a tile from the opponent's deck — and is irrelevant to scoring.

**Arrows.** Each of the 24 deck tiles carries between 1 and 6 arrows, each
sitting on one of the six edges and pointing outward at the neighbouring cell.
Each deck contains exactly one tile of each of the 12 possible arrow patterns.
The enumeration, the proof that there are exactly 12, and the ASCII catalogue
are in **[piece-archetypes.md](piece-archetypes.md)**.

The joker carries **no arrows**.

---

## 2. Setup

1. Both players resolve a fair 50/50 randomiser (coin toss). The winner is
   **Player 1** and moves first.
2. **Player 2 chooses** which of the two 12-tile decks to play. Player 1 takes
   the other.
3. Player 1 additionally receives the **joker**, which starts in Player 1's
   colour. Player 1 therefore holds 13 tiles and Player 2 holds 12.
4. The board starts **empty**. All information — both hands, every placed tile,
   its orientation, and the joker's colour — is public at all times.

The seat-to-colour mapping carries no strategic weight in the current model:
the two decks hold the same 12 arrow patterns. See `OPEN-2` for the one way
that could turn out to be false.

---

## 3. Turn structure

Players alternate, Player 1 first. The game lasts exactly **25 plies**: Player
1 moves on plies 1, 3, …, 25 (13 moves), Player 2 on plies 2, 4, …, 24 (12
moves).

A move is a triple **(cell, tile, rotation)**:

- **cell** — any empty cell.
- **tile** — any tile still in the mover's hand. Player 1 may play the joker on
  any of their turns.
- **rotation** — any `k ∈ {0,…,5}`, turning the tile `k × 60°` clockwise. A
  tile with rotational symmetry has fewer *distinct* rotations; the move
  generator must deduplicate (see [piece-archetypes.md](piece-archetypes.md)).

The tile is placed **mover's colour face up**. Then the flip rule fires.

**There is no passing and no legal move can ever be unavailable** — see
[invariant I4](#5-invariants).

---

## 4. The flip rule

This is the whole game, so it is stated twice: once in prose, once in code.

> When a tile is placed, look at each of its arrows. If an arrow points at an
> adjacent cell that is **occupied**, the tile in that cell is flipped to the
> colour of the player who just moved. Arrows pointing off the board, or at
> empty cells, do nothing.

```python
def apply_move(state, cell, tile, rotation):
    mover = state.to_move
    state.board[cell] = Placed(tile, rotation, colour=mover)

    for slot in tile.arrow_slots:                  # e.g. (0, 1, 3)
        direction = (slot + rotation) % 6          # clockwise from North
        target = ADJACENCY[cell][direction]        # None if off-board
        if target is not None and state.board[target] is not None:
            state.board[target].colour = mover     # flip; do NOT recurse

    state.hands[mover].remove(tile)
    state.to_move = opponent(mover)
```

Four consequences worth stating explicitly, because each one is a place an
implementation could plausibly go wrong:

- **No chain reaction.** A flipped tile does not fire its own arrows. The
  recursion depth is exactly one. See
  [adr-006](adr/adr-006-no-chain-reaction.md).
- **A flip is unconditional.** There is no bracketing or line-capture as in
  Reversi. Adjacency plus an arrow is sufficient.
- **Already-your-colour tiles are still "flipped"** — the operation is an
  assignment, not a toggle. Pointing an arrow at your own tile is legal and is
  a no-op.
- **A tile's arrows fire exactly once, on the ply it is placed.** From then on
  it is inert for the rest of the game. Its stored rotation is bookkeeping for
  notation and replay, nothing more. This is what makes the flip rule cheap and
  it is the single most important fact for the engine design
  ([adr-003](adr/adr-003-piece-representation.md)).

Placing a tile where none of its arrows hit anything is legal, and the poster
explicitly calls it out as a real strategic option.

---

## 5. Invariants

These hold in every reachable state and belong in `tests/test_state.py`:

- **I1.** occupied cells = plies played.
- **I2.** After ply 25 the board is full: 25 tiles on 25 cells.
- **I3.** tiles in Player 1's hand = 13 − ⌈plies/2⌉; in Player 2's hand =
  12 − ⌊plies/2⌋.
- **I4.** Before every ply there is at least one empty cell and the mover holds
  at least one tile, so a legal move always exists. (From I1 and I3: the mover
  runs out of tiles exactly when the board runs out of cells, on ply 26.)
- **I5.** Every tile is on the board or in exactly one hand; none is ever
  removed or destroyed.
- **I6.** Deck membership never changes. Colour changes freely.

---

## 6. The joker

The joker is a full tile with three properties that set it apart:

1. It has **no arrows**. Placing it flips nothing, ever.
2. It starts as **Player 1's colour** and belongs to Player 1's hand. Player 1
   may play it on any of their 13 turns.
3. Once on the board it is an ordinary tile: it occupies a cell, it can be
   flipped by an opponent's arrow, and **it counts for whoever's colour it
   shows at the end**.

Because the joker is the 25th tile and 25 is odd, the joker is exactly what
gives Player 1 the extra ply. Its strategic content is entirely in *tempo* —
it is Player 1's only zero-arrow move, playable as a pass-like filler.

---

## 7. End of game and scoring

The game ends after ply 25, when the board is full.

**Score** = number of cells showing your colour. Purple + Green = 25.

Since 25 is odd, the two scores can never be equal: **draws are impossible**.
The player with the higher count wins.

---

## 8. Worked example

Player 1 is Purple. Ply 1: Purple plays `P1` (single arrow, slot `N`) on `C3`
at rotation 0.

- `C3`'s neighbours are `C2` (N), `D2` (NE), `D3` (SE), `C4` (S), `B3` (SW),
  `B2` (NW).
- Slot 0 + rotation 0 = direction 0 = N → target `C2`.
- `C2` is empty, so nothing flips.

Board: Purple on `C3`. Score 1–0.

Ply 2: Green plays `P2-opp` (arrows at `N` and `S`) on `C2` at rotation 0.

- Slot 0 → N → `C1`: empty, nothing.
- Slot 3 → S → `C3`: **occupied by Purple → flips to Green.**

Board: Green on `C2` and `C3`. Score 0–2. Note that `C3`'s own arrow does not
retaliate: it fired on ply 1 and is inert.

Ply 3: Purple plays `P2-opp` on `C4` at rotation 0.

- Slot 0 → N → `C3`: occupied → **flips to Purple.**
- Slot 3 → S → `C5`: empty.

Score 2–1. Notice `P2-opp` has only **3** distinct rotations, not 6, because
`{N, S}` maps to itself under a 180° turn.

---

## 9. Differences from the 2017 poster text

Recorded so the reconstruction is auditable:

| Poster | This rulebook | Why |
|---|---|---|
| "3 peças com 3 setas" left unspecified | The three 3-arrow tiles are derived as bracelet classes | The deck is provably the complete set of 12 tiles; nothing is left to choose |
| Deck choice framed as a real decision | Modelled as cosmetic | Both decks hold the same 12 patterns, subject to `OPEN-2` |
| Turn order after the coin toss not spelled out | Player 1 takes 13 plies including the joker | Forced: 25 tiles, 25 cells, alternating |
| Scoring described loosely | Count of cells by colour, draws impossible | 25 is odd |

The roadmap's own "8 archetypes" is likewise corrected to **12**; see
[piece-archetypes.md](piece-archetypes.md).

---

## Open questions

Both are blocking for Phase 1 only in the weak sense that the engine should be
written so either answer is a one-line change.

- **OPEN-1** *(geometry)* — Confirm on the physical board that all five columns
  hold five cells with no missing corner. Evidence so far: the photograph, and
  25 pieces filling 25 sockets.
- **OPEN-2** *(chirality)* — `P3-y` is the only chiral tile: its two faces show
  mirror-image arrow patterns. Are the purple deck's and green deck's `P3-y`
  the same physical object, so that the two players play *different* patterns?
  If yes, the decks are not interchangeable and the game is asymmetric between
  players independently of the first-move advantage — a live confound for
  **H1**. Until answered, the engine assumes both players hold `(0,1,3)` on
  their own face.

---

## See also

- [board-geometry.md](board-geometry.md) — coordinates, directions, adjacency
- [piece-archetypes.md](piece-archetypes.md) — the 12 tiles
- [adr/](adr/) — the six Phase 0 decision records
- [glossary.md](glossary.md) — terms used across the project
