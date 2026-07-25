#!/usr/bin/env bash
# Seed the Phase 0 and Phase 1 issues. Run after labels.sh and milestones.sh.
set -euo pipefail

issue() {
  local title="$1" milestone="$2" labels="$3" body="$4"
  gh issue create --title "$title" --milestone "$milestone" \
    --label "$labels" --body "$body" >/dev/null && echo "created: $title"
}

M0="Phase 0 — Foundation"
M1="Phase 1 — Game Engine"

# --- Phase 0: the two questions the physical game has to answer -------------
issue "OPEN-1: confirm the board is five columns of five cells" "$M0" \
  "phase:0,type:documentation,area:rules,blocked" \
  "The poster photograph is consistent with 5x5 = 25 cells, but it is low
resolution and taken at an angle. Confirm against the physical board that every
column holds five sockets and no corner is missing.

Resolving this may require an ADR amendment to adr-002.
See docs/rules-canonical.md#open-questions."

issue "OPEN-2: are the two decks' chiral P3-y tiles mirror images?" "$M0" \
  "phase:0,type:documentation,area:rules,blocked,H1" \
  "P3-y is the only chiral tile: its faces show (0,1,3) and (0,1,4).

If the purple and green decks are the same physical objects, the two players
play genuinely different patterns, so the seats are **not equivalent** and any
measured first-player advantage mixes a move-order effect with a deck effect.

**This is a confound for H1 and must be resolved before hypotheses lock at the
end of Phase 2.** Needs a photograph of both decks' 3-arrow tiles.

See docs/piece-archetypes.md and R2 in docs/risk-register.md."

# --- Phase 1: engine --------------------------------------------------------
issue "Implement fliphex/board.py" "$M1" "phase:1,type:code,area:engine" \
  "Board with 25 cells, axial internals, flat 25x6 adjacency table.

Must reproduce docs/board-geometry.md exactly — tests import
scripts/gen_board_geometry.py and assert agreement. See adr-002."

issue "Implement fliphex/piece.py" "$M1" "phase:1,type:code,area:engine" \
  "Arrow patterns as 6-bit masks; rotation as a circular shift; the 12
archetypes as module constants.

Move generation must deduplicate rotations — orbit sizes are not all 6 (P6 has
1, P3-tri has 2, the opposite-pair tiles have 3). See adr-003 and
docs/piece-archetypes.md."

issue "Implement fliphex/state.py" "$M1" "phase:1,type:code,area:engine" \
  "Immutable, hashable GameState. Per adr-003 the search state stores only a
colour per cell plus hand bitmasks — **never** tile identity or rotation.
Placement history is a separate append-only list for notation and H5 only.

Include Zobrist hashing keyed on (cell, colour) and (player, tile)."

issue "Implement fliphex/moves.py and rules.py" "$M1" "phase:1,type:code,area:engine" \
  "Legal move generation (empty cell x tile in hand x distinct rotation), move
application with the flip rule, terminal detection, winner and score.

Flip is unconditional, one deep, never chained (adr-006)."

issue "Test suite for the engine" "$M1" "phase:1,type:code,area:engine" \
  "Coverage required before Phase 1 closes — see docs/engineering.md:
adjacency and its symmetry, rotation orbits, flip logic and its non-chaining,
invariants I1-I6, joker rules, termination in exactly 25 plies, no draws, and
1000 random games completing cleanly."

issue "Set up CI" "$M1" "phase:1,type:code,area:infra" \
  "GitHub Actions on push and PR: ruff check, ruff format --check, pytest, then
'python scripts/build_docs.py && git diff --exit-code docs/' so the generated
docs cannot drift (R12)."

echo "done"
