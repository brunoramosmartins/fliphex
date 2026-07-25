# FLIPHEX — working notes for Claude

Computational study of FLIPHEX, an original perfect-information hexagonal board
game designed at IME + FAU-USP (MAP 2001, 2017). Three axes: an exact solver, an
AlphaZero-style learner, and a complexity analysis. Portfolio-grade, public repo,
no external deadline.

Start with `roadmap-fliphex-v1.md`. It sequences the phases by dependency.

## Read before touching anything

| File | Why |
|---|---|
| `docs/rules-canonical.md` | The authoritative rules. If code and this disagree, the code is wrong. |
| `docs/board-geometry.md` | Coordinates, directions, the 25×6 adjacency table. **Generated.** |
| `docs/piece-archetypes.md` | The 12 tiles and the proof there are exactly 12. **Generated.** |
| `docs/adr/` | Six decision records. adr-003 and adr-006 shape the most code. |
| `docs/engineering.md` | Layout, dependency rules, testing requirements. |

## Facts that are easy to get wrong

- **Hexagons are flat-top**, in five vertical columns of five. Directions are
  `N, NE, SE, S, SW, NW` indexed **clockwise from North**. The roadmap's prose
  says "5-row zigzag", which is the same board seen transposed — trust
  `board-geometry.md`.
- **Placed tiles are inert.** Arrows fire once, on the ply the tile is placed.
  The search state stores only a colour per cell — never a tile identity or
  rotation. This is adr-003 and it is load-bearing.
- **Flips never chain** (adr-006). `apply_move` recursion depth is exactly 1.
- **There are 12 archetypes, not 8.** The roadmap says 8; it is wrong.
- **Rotation orbits are not always 6.** `P6` has 1, `P3-tri` has 2, the
  opposite-pair tiles have 3. Move generation must deduplicate: 58 distinct
  (tile, rotation) pairs per player, so 1450 legal moves on ply 1.
- **Draws are impossible** — 25 cells, odd. Code producing a draw is a bug.
- **The board has no symmetries.** No canonicalisation, no data augmentation.

## Conventions

- Python 3.12+, `ruff` for lint and format, `pytest` for tests.
- Cells are `A1`–`E5` everywhere a human might read them; axial `(q,r)` only
  inside `fliphex/board.py`.
- `fliphex/` imports nothing from the project. `solver/`, `az/`, and
  `complexity/` import `fliphex/` and never each other.
- Conventional commits. Branches are `phase-N/slug`. Squash merges.

## Generated files — never edit by hand

`docs/board-geometry.md` and `docs/piece-archetypes.md` come from
`scripts/build_docs.py`. Edit the prose in the generator, then rerun it. CI
fails if the working tree is dirty after a rebuild.

## Open questions

Both are in `docs/rules-canonical.md` and need the physical game to resolve:

- **OPEN-1** — confirm all five columns hold five cells.
- **OPEN-2** — are the two decks' chiral `P3-y` tiles mirror images of each
  other? If so the seats are not equivalent, which confounds H1. **Must be
  resolved before hypotheses lock at the end of Phase 2.**

## Working agreements

- Hypotheses lock at the end of Phase 2 (tag `v0.3-hypotheses`). After that,
  `docs/research.md` may only gain verdicts.
- Register experiments in `experiments/registry.md` **before** running them.
- `rules-canonical.md`, `board-geometry.md`, `piece-archetypes.md`, and the
  Axis 2 architecture require an ADR to change.
- Notes, TILs, the glossary, and the registries are freely editable.
