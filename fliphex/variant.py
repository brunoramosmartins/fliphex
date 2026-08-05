"""Variant: a board size plus a deck composition, as data rather than a code path.

A *variant* is the pair (board, hands). ``fliphex.board.Board`` already handles
the board; this module supplies the hands, following
`adr-009 <../docs/adr/adr-009-reduced-deck-policy.md>`_ as amended by
`adr-011 <../docs/adr/adr-011-reduced-variant-parity.md>`_:

- the cell count ``N`` must be **odd**;
- with ``a = (N - 1) / 2``, Player 2 draws ``a`` archetypes and Player 1 draws
  **the same ``a`` plus the joker**, so ``(a + 1) + a = N``.

Both hands are therefore exactly exhausted, play alternates for exactly ``N``
plies, Player 1 moves last, and Player 1's extra tile is the joker. That is not
a convention invented for the reduced boards — it is the shipped 5×5's own
structure (13 = 12 archetypes + joker against 12), and ``Variant(5, 5)``
reproduces :meth:`GameState.initial` exactly —
``tests/test_variant.py::test_full_variant_reproduces_the_shipped_initial_state``
asserts it, and it is the evidence that the reduced rule is a shrink of FLIPHEX
rather than a convention invented for small boards.

Archetype priority (adr-009): always ``P6`` and ``P3-y``, then fill by ascending
arrow count, ties broken by the canonical :data:`fliphex.piece.DECK` order.

Why the parity guard lives here and not on ``Board``
----------------------------------------------------
``Board(4, 4)`` is a perfectly good *graph* and ``scripts/check_symmetry.py``
needs to build it — that is how the 4×4's automorphism was measured and found to
be a 180° rotation rather than a mirror. What is forbidden is treating an
even-celled board as a *game*: scoring is a cell count, so an even board admits
ties, and the canonical rules define no tie-break. Moving this check onto
``Board`` would break the symmetry tooling; removing it would let the 4×4 class
of bug back in.

No closed-form state count lives here, deliberately. The bound formula stays in
``scripts/layer_profile.py``, which imports nothing from this package, because
adr-010 V1 compares the solver's enumeration against that formula and a
comparison is only evidence if the two sides are computed by different means.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from fliphex.board import Board
from fliphex.piece import DECK
from fliphex.state import JOKER_INDEX, TILE_INDEX, Colour, GameState

#: Archetypes that every reduced deck keeps, in the order adr-009 lists them.
#: ``P6`` is the maximum-flip tile; ``P3-y`` is the sole chiral one, whose
#: reflection leaves the deck and so breaks a *mirror* at the game level.
ANCHORS: tuple[str, ...] = ("P6", "P3-y")


class Arm(StrEnum):
    """Which experimental arm a variant's hands realise.

    Player 1 always holds one tile more than Player 2. What that tile *is* is
    the manipulated variable for H2, because on an odd board the joker cannot
    simply be removed — it is what makes Player 1's hand larger, so dropping it
    leaves the board unfillable.
    """

    #: Player 1's extra tile is the **joker**. The shipped 5×5's structure.
    H1 = "h1"
    #: Player 1's extra tile is the **next archetype** by ascending arrow count.
    #: No joker anywhere. Same state-space size as :attr:`H1`, so the two arms
    #: are matched.
    #:
    #: This arm **does not exist on the shipped 5×5**, where the capacity is the
    #: whole 12-archetype deck and there is no next archetype to promote. That
    #: is not a limitation of the code: on the full board the joker is the only
    #: tile that can give Player 1 the extra ply, which is why H2 is answered
    #: exactly on the reduced boards and statistically on the shipped one.
    H2 = "h2"


def _by_arrow_count(names: list[str]) -> list[str]:
    """Sort archetype names by arrow count, ties in canonical ``DECK`` order."""
    order = {piece.archetype: i for i, piece in enumerate(DECK)}
    return sorted(names, key=lambda n: (DECK[order[n]].n_arrows, order[n]))


def archetypes_for(capacity: int) -> tuple[str, ...]:
    """Return the ``capacity``-tile archetype deck, per adr-009's priority.

    Args:
        capacity: Number of archetypes to draw, ``2 <= capacity <= 12``.

    Returns:
        Archetype names, anchors first, then ascending arrow count.

    Raises:
        ValueError: If ``capacity`` is outside ``2..12``. Below 2 the anchors do
            not fit, and the anchors are the reason a reduced deck is a shrink
            of FLIPHEX rather than an unrelated game.
    """
    if not 2 <= capacity <= len(DECK):
        raise ValueError(
            f"capacity must be in 2..{len(DECK)} (the two adr-009 anchors must "
            f"fit and the deck has {len(DECK)} archetypes), got {capacity}"
        )
    rest = [p.archetype for p in DECK if p.archetype not in ANCHORS]
    return (*ANCHORS, *_by_arrow_count(rest)[: capacity - 2])


@dataclass(frozen=True)
class Variant:
    """A board size and the two hands that exactly fill it.

    Attributes:
        n_cols: Board columns.
        n_rows: Cells per column.
        arm: Which tile Player 1 holds in excess of Player 2 (:class:`Arm`).
        first: The colour that moves first and holds the larger hand.
    """

    n_cols: int = 5
    n_rows: int = 5
    arm: Arm = Arm.H1
    first: Colour = Colour.PURPLE

    def __post_init__(self) -> None:
        if self.n_cells % 2 == 0:
            raise ValueError(
                f"a variant needs an odd cell count (adr-011); "
                f"{self.n_cols}x{self.n_rows} has {self.n_cells}. Scoring is a "
                f"cell count, so an even board admits ties and the rules define "
                f"no tie-break. Board() itself accepts even sizes — only playing "
                f"a game on one is forbidden."
            )
        if self.n_cells < 5:
            raise ValueError(
                f"a variant needs at least 5 cells so that both adr-009 anchors "
                f"reach the board, got {self.n_cells}"
            )
        if self.arm is Arm.H2 and self.capacity >= len(DECK):
            raise ValueError(
                f"the H2 arm does not exist at capacity {self.capacity}: it "
                f"replaces the joker with the next archetype, and the deck has "
                f"only {len(DECK)}. On the shipped {self.n_cols}x{self.n_rows} "
                f"the joker is not a design choice — it is the only tile that "
                f"can give Player 1 the extra ply, so H2 is exact on the reduced "
                f"boards and statistical on this one (docs/research.md H2)."
            )

    @property
    def n_cells(self) -> int:
        """Cells on the board, ``n_cols * n_rows``."""
        return self.n_cols * self.n_rows

    @property
    def capacity(self) -> int:
        """``a`` — the number of archetypes Player 2 draws, ``(N - 1) / 2``."""
        return (self.n_cells - 1) // 2

    @property
    def name(self) -> str:
        """Short label for filenames and artefact headers, e.g. ``"5x3-h1"``."""
        return f"{self.n_cols}x{self.n_rows}-{self.arm.value}"

    def board(self) -> Board:
        """Return the board this variant is played on."""
        return Board(self.n_cols, self.n_rows)

    def deck_names(self) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Return ``(first_player_tiles, second_player_tiles)`` by name.

        Every artefact header must carry this verbatim (adr-004 R3, adr-009):
        a bare "5×3 result" is ambiguous, and the deck is a modeling choice.
        """
        shared = archetypes_for(self.capacity)
        if self.arm is Arm.H1:
            return (*shared, "JOKER"), shared
        # Lazily: at capacity == len(DECK) there is no next archetype, which is
        # why __post_init__ rejects the H2 arm there rather than failing here.
        return (*shared, archetypes_for(self.capacity + 1)[-1]), shared

    def hands(self) -> tuple[int, int]:
        """Return the hand bitmasks as ``(purple, green)``.

        The larger hand belongs to :attr:`first`; the masks are ordered by
        colour so they can be handed straight to :meth:`GameState.build`.
        """
        larger, smaller = (_mask(names) for names in self.deck_names())
        hands = [smaller, smaller]
        hands[self.first - 1] = larger
        return hands[0], hands[1]

    def initial_state(self) -> GameState:
        """Return the opening position for this variant."""
        colours = (Colour.EMPTY,) * self.n_cells
        return GameState.build(colours, self.hands(), self.first)


def _mask(names: tuple[str, ...]) -> int:
    """Return the hand bitmask holding exactly ``names``."""
    mask = 0
    for name in names:
        mask |= 1 << (JOKER_INDEX if name == "JOKER" else TILE_INDEX[name])
    return mask


#: The shipped game. ``Variant(5, 5)`` is not a special case of the reduced-deck
#: rule — it is what the rule reduces *from*.
FULL_GAME = Variant(5, 5)

#: The primary exact-solve target (adr-011): 15 cells, hands 8 + 7.
FIVE_BY_THREE = Variant(5, 3)

#: The correctness fixture and adr-010 V3 double-solve artefact: 9 cells, 5 + 4.
THREE_BY_THREE = Variant(3, 3)
