"""Generate the archetype catalogue in docs/piece-archetypes.md.

Phase 0 tool, standalone for the same reason as gen_board_geometry.py.

The deck composition on the MAP 2001 poster (1 piece with 1 arrow, 3 with 2,
3 with 3, 3 with 4, 1 with 5, 1 with 6 = 12 pieces) is not an arbitrary list:
it is exactly the number of distinct arrow patterns on a two-sided hexagonal
tile. A tile can be turned in six rotations and turned over, so two patterns are
the same physical piece iff one is a rotation or a reflection of the other.
Those equivalence classes are binary *bracelets* of length 6, and there are
exactly 1, 3, 3, 3, 1, 1 of them with 1..6 arrows. This module proves that.

Run:  python scripts/gen_piece_archetypes.py
"""

from __future__ import annotations

from itertools import combinations

# Must match scripts/gen_board_geometry.py: clockwise from North.
DIRECTION_NAMES = ["N", "NE", "SE", "S", "SW", "NW"]

Pattern = tuple[int, ...]


def rotate(pattern: Pattern, k: int) -> Pattern:
    """Rotate the tile k * 60 degrees clockwise."""
    return tuple(sorted((i + k) % 6 for i in pattern))


def reflect(pattern: Pattern) -> Pattern:
    """Turn the tile over, mirroring across the N-S axis.

    This is what physically happens when a piece is flipped to the other
    colour, so the two faces of one tile carry mirror-image arrow patterns.
    """
    return tuple(sorted((-i) % 6 for i in pattern))


def rotations(pattern: Pattern) -> set[Pattern]:
    return {rotate(pattern, k) for k in range(6)}


def necklace(pattern: Pattern) -> Pattern:
    """Canonical form under rotation alone — one *face* of a tile."""
    return min(rotations(pattern))


def bracelet(pattern: Pattern) -> Pattern:
    """Canonical form under rotation and reflection — one physical *tile*."""
    return min(rotations(pattern) | rotations(reflect(pattern)))


def orientations(pattern: Pattern) -> int:
    """Distinct placements of one face on the board.

    Reflection is excluded on purpose: on the board a player may rotate a piece
    freely but may not turn it over, because turning it over would change its
    colour. So the move generator uses the *rotation* orbit, not the bracelet.
    """
    return len(rotations(pattern))


def is_chiral(pattern: Pattern) -> bool:
    """True if the tile's two faces show genuinely different patterns."""
    return necklace(pattern) != necklace(reflect(pattern))


def enumerate_bracelets(n_arrows: int) -> list[Pattern]:
    seen = {bracelet(c) for c in combinations(range(6), n_arrows)}
    return sorted(seen)


def enumerate_necklaces(n_arrows: int) -> list[Pattern]:
    seen = {necklace(c) for c in combinations(range(6), n_arrows)}
    return sorted(seen)


# The deck, derived rather than chosen: every bracelet with 1..6 arrows.
DECK: dict[str, Pattern] = {
    "P1": (0,),
    "P2-adj": (0, 1),
    "P2-skip": (0, 2),
    "P2-opp": (0, 3),
    "P3-fan": (0, 1, 2),
    "P3-y": (0, 1, 3),
    "P3-tri": (0, 2, 4),
    "P4-adj": (2, 3, 4, 5),
    "P4-skip": (1, 3, 4, 5),
    "P4-opp": (1, 2, 4, 5),
    "P5": (0, 1, 2, 3, 4),
    "P6": (0, 1, 2, 3, 4, 5),
}


def to_bool_tuple(pattern: Pattern) -> tuple[bool, ...]:
    """The `tuple[bool] * 6` representation required by the Phase 0 exit criteria."""
    return tuple(i in pattern for i in range(6))


def render(pattern: Pattern) -> list[str]:
    """Five-line ASCII flat-top hex. Slots: N=0 NE=1 SE=2 S=3 SW=4 NW=5."""
    glyph = {0: "↑", 1: "↗", 2: "↘", 3: "↓", 4: "↙", 5: "↖"}
    g = [glyph[i] if i in pattern else "·" for i in range(6)]
    return [
        f"    {g[0]}    ",
        f"  {g[5]}   {g[1]}  ",
        "    ⬡    ",
        f"  {g[4]}   {g[2]}  ",
        f"    {g[3]}    ",
    ]


def catalogue() -> str:
    lines = []
    for name, pattern in DECK.items():
        dirs = ", ".join(DIRECTION_NAMES[i] for i in pattern)
        bools = to_bool_tuple(pattern)
        mask = "".join("1" if b else "0" for b in bools)
        chiral = (
            "chiral — the two faces differ"
            if is_chiral(pattern)
            else "achiral — both faces identical"
        )
        lines += [
            f"### `{name}` — {len(pattern)} arrow(s)",
            "",
            "```",
            *render(pattern),
            "```",
            "",
            f"- slots `{pattern}` = {dirs}",
            f"- bitmask (N,NE,SE,S,SW,NW): `{mask}`",
            f"- `tuple[bool]*6`: `{bools}`",
            f"- distinct rotations on the board: **{orientations(pattern)}**",
            f"- reverse face: `{necklace(reflect(pattern))}` — {chiral}",
            "",
        ]
    return "\n".join(lines)


def class_counts() -> str:
    lines = [
        "| arrows | patterns | faces (necklaces) | tiles (bracelets) |",
        "|---|---|---|---|",
    ]
    for n in range(1, 7):
        raw = len(list(combinations(range(6), n)))
        lines.append(
            f"| {n} | {raw} | {len(enumerate_necklaces(n))} | "
            f"**{len(enumerate_bracelets(n))}** |"
        )
    raw_total = sum(len(list(combinations(range(6), n))) for n in range(1, 7))
    neck_total = sum(len(enumerate_necklaces(n)) for n in range(1, 7))
    brac_total = sum(len(enumerate_bracelets(n)) for n in range(1, 7))
    lines.append(f"| **total** | {raw_total} | {neck_total} | **{brac_total}** |")
    return "\n".join(lines)


def total_orientations() -> int:
    """Distinct (piece, rotation) pairs available to a player: 12 pieces + joker."""
    return sum(orientations(p) for p in DECK.values()) + 1


def check_deck() -> None:
    counts = {n: len(enumerate_bracelets(n)) for n in range(1, 7)}
    assert counts == {1: 1, 2: 3, 3: 3, 4: 3, 5: 1, 6: 1}, counts
    assert sum(counts.values()) == 12 == len(DECK)
    # Every deck entry is a distinct tile, and together they are *all* the tiles.
    assert len({bracelet(p) for p in DECK.values()}) == 12
    every = {b for n in range(1, 7) for b in enumerate_bracelets(n)}
    assert {bracelet(p) for p in DECK.values()} == every
    # Exactly one piece is chiral: the 3-arrow "Y".
    chiral = [name for name, p in DECK.items() if is_chiral(p)]
    assert chiral == ["P3-y"], chiral


if __name__ == "__main__":
    check_deck()
    print(catalogue())
    print(class_counts())
    print()
    print("chiral pieces:", [n for n, p in DECK.items() if is_chiral(p)])
    print("(piece, rotation) pairs per player incl. joker:", total_orientations())
