"""Pieces: arrow patterns as 6-bit masks, rotation, and the 12 archetypes.

Per adr-003, an arrow pattern is a 6-bit integer: bit ``i`` set means the piece
has an arrow in slot ``i``, indexed clockwise from North exactly as in
:mod:`fliphex.board` (``N=0 .. NW=5``). Rotation by ``k`` is a circular shift of
those six bits, so slot ``i`` moves to slot ``(i + k) mod 6`` — matching the
tuple rotation in ``scripts/gen_piece_archetypes.py``.

Each player's deck is the complete set of 12 distinct two-sided tiles (see
docs/piece-archetypes.md); they are module constants here. The joker is a
zero-arrow piece.

A piece may be *rotated* freely when placed but never *reflected* (turning it
over would change its colour), so move generation iterates the rotation orbit,
which is not always six: ``P6`` has 1, ``P3-tri`` 2, the opposite-pair pieces 3.
"""

from __future__ import annotations

from dataclasses import dataclass

from fliphex.board import DIRECTION_NAMES

#: Number of edge slots on a hexagon.
N_SLOTS = 6

#: A pattern with every arrow present.
FULL_MASK = (1 << N_SLOTS) - 1


def slots_to_mask(slots: tuple[int, ...]) -> int:
    """Return the 6-bit mask for an iterable of slot indices."""
    mask = 0
    for slot in slots:
        if not 0 <= slot < N_SLOTS:
            raise ValueError(f"slot out of range: {slot}")
        mask |= 1 << slot
    return mask


def mask_to_slots(mask: int) -> tuple[int, ...]:
    """Return the ascending tuple of slot indices set in ``mask``."""
    return tuple(i for i in range(N_SLOTS) if mask >> i & 1)


def rotate_mask(mask: int, k: int) -> int:
    """Rotate a pattern ``k * 60`` degrees clockwise.

    Bit ``i`` moves to bit ``(i + k) mod 6``, i.e. a circular left shift by
    ``k`` within six bits.
    """
    k %= N_SLOTS
    return ((mask << k) | (mask >> (N_SLOTS - k))) & FULL_MASK


@dataclass(frozen=True, slots=True)
class Piece:
    """An arrow pattern with a stable archetype name.

    The piece is orientation-free: it stores the canonical (unrotated) pattern.
    Rotation is applied at placement via :meth:`rotated`; the search state never
    stores a placed piece's rotation (adr-003).

    Attributes:
        archetype: Stable name, e.g. ``"P3-tri"`` or ``"JOKER"``.
        mask: The 6-bit arrow pattern.
    """

    archetype: str
    mask: int

    @classmethod
    def from_slots(cls, archetype: str, slots: tuple[int, ...]) -> Piece:
        """Build a piece from an archetype name and its arrow slots."""
        return cls(archetype, slots_to_mask(slots))

    @property
    def n_arrows(self) -> int:
        """Number of arrows on the piece."""
        return self.mask.bit_count()

    @property
    def slots(self) -> tuple[int, ...]:
        """The ascending tuple of arrow slots."""
        return mask_to_slots(self.mask)

    def rotated(self, k: int) -> int:
        """Return the mask after rotating this piece by ``k`` (0..5)."""
        return rotate_mask(self.mask, k)

    def distinct_rotations(self) -> tuple[int, ...]:
        """Return the rotation values giving distinct placements.

        One ``k`` per distinct rotated mask, smallest first. Its length is the
        piece's rotation-orbit size — 6 for an asymmetric piece, fewer for a
        rotationally symmetric one (``P6`` -> ``(0,)``).
        """
        seen: set[int] = set()
        ks: list[int] = []
        for k in range(N_SLOTS):
            m = rotate_mask(self.mask, k)
            if m not in seen:
                seen.add(m)
                ks.append(k)
        return tuple(ks)

    def __str__(self) -> str:
        dirs = ",".join(DIRECTION_NAMES[s] for s in self.slots) or "—"
        return f"{self.archetype}[{dirs}]"


# The deck: every distinct two-sided tile, derived in docs/piece-archetypes.md.
# Slot tuples are the canonical (lexicographically smallest rotation) form and
# match scripts/gen_piece_archetypes.py term for term.
_DECK_SLOTS: dict[str, tuple[int, ...]] = {
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

#: The 12 archetypes by name.
ARCHETYPES: dict[str, Piece] = {
    name: Piece.from_slots(name, slots) for name, slots in _DECK_SLOTS.items()
}

#: One player's deck, in canonical order.
DECK: tuple[Piece, ...] = tuple(ARCHETYPES.values())

#: The neutral joker: no arrows, one orientation.
JOKER = Piece("JOKER", 0)

__all__ = [
    "ARCHETYPES",
    "DECK",
    "FULL_MASK",
    "JOKER",
    "N_SLOTS",
    "Piece",
    "mask_to_slots",
    "rotate_mask",
    "slots_to_mask",
]
