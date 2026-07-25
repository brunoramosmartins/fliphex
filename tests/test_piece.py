"""Tests for fliphex.piece.

Independent facts about the bitmask representation and the deck, plus a
cross-check that the bitmask rotation agrees with the tuple rotation in
scripts/gen_piece_archetypes.py (risk R12).
"""

import gen_piece_archetypes as gen
import pytest

from fliphex.piece import (
    ARCHETYPES,
    DECK,
    FULL_MASK,
    JOKER,
    N_SLOTS,
    mask_to_slots,
    rotate_mask,
    slots_to_mask,
)

# -- mask <-> slots -----------------------------------------------------------


@pytest.mark.parametrize("mask", range(1 << N_SLOTS))
def test_mask_slots_roundtrip(mask):
    assert slots_to_mask(mask_to_slots(mask)) == mask


def test_slots_to_mask_rejects_out_of_range():
    with pytest.raises(ValueError):
        slots_to_mask((6,))


# -- rotation -----------------------------------------------------------------


def test_rotate_identity_and_period():
    for mask in range(1 << N_SLOTS):
        assert rotate_mask(mask, 0) == mask
        assert rotate_mask(mask, 6) == mask
        assert rotate_mask(mask, 12) == mask


def test_rotate_single_bit_moves_clockwise():
    # slot 0 -> slot 1 under a rotation of 1.
    assert rotate_mask(0b000001, 1) == 0b000010
    # slot 5 wraps to slot 0.
    assert rotate_mask(0b100000, 1) == 0b000001


def test_rotate_full_mask_is_invariant():
    assert rotate_mask(FULL_MASK, 3) == FULL_MASK


# -- archetypes and orbits ----------------------------------------------------


def test_deck_has_twelve_named_archetypes():
    assert len(DECK) == 12
    assert len(ARCHETYPES) == 12
    assert {p.archetype for p in DECK} == set(ARCHETYPES)


@pytest.mark.parametrize(
    "name,arrows",
    [
        ("P1", 1),
        ("P2-adj", 2),
        ("P2-opp", 2),
        ("P3-fan", 3),
        ("P3-tri", 3),
        ("P4-adj", 4),
        ("P5", 5),
        ("P6", 6),
    ],
)
def test_arrow_counts(name, arrows):
    assert ARCHETYPES[name].n_arrows == arrows


@pytest.mark.parametrize(
    "name,orbit",
    [
        ("P1", 6),
        ("P2-adj", 6),
        ("P2-skip", 6),
        ("P2-opp", 3),  # {N,S} maps to itself under a half turn
        ("P3-fan", 6),
        ("P3-y", 6),
        ("P3-tri", 2),  # threefold symmetry
        ("P4-opp", 3),
        ("P5", 6),
        ("P6", 1),  # fully symmetric
    ],
)
def test_distinct_rotation_orbits(name, orbit):
    assert len(ARCHETYPES[name].distinct_rotations()) == orbit


def test_joker_has_no_arrows_and_one_orientation():
    assert JOKER.n_arrows == 0
    assert JOKER.slots == ()
    assert JOKER.distinct_rotations() == (0,)
    assert all(JOKER.rotated(k) == 0 for k in range(6))


def test_total_distinct_placements_is_58():
    # 12 deck pieces + joker; 25 cells * 58 = 1450 legal moves on ply 1.
    total = sum(len(p.distinct_rotations()) for p in DECK) + len(
        JOKER.distinct_rotations()
    )
    assert total == 58


# -- cross-check against the canonical generator (R12) ------------------------


def test_archetype_slots_match_generator():
    assert {name: p.slots for name, p in ARCHETYPES.items()} == gen.DECK


def test_bitmask_rotation_agrees_with_tuple_rotation():
    for name, pattern in gen.DECK.items():
        piece = ARCHETYPES[name]
        for k in range(6):
            assert mask_to_slots(piece.rotated(k)) == gen.rotate(pattern, k)


def test_orbit_sizes_match_generator():
    for name, pattern in gen.DECK.items():
        assert len(ARCHETYPES[name].distinct_rotations()) == gen.orientations(pattern)


def test_deck_is_the_complete_set_of_bracelets():
    every = {b for n in range(1, 7) for b in gen.enumerate_bracelets(n)}
    assert {gen.bracelet(p.slots) for p in DECK} == every


def test_only_p3y_is_chiral():
    chiral = [p.archetype for p in DECK if gen.is_chiral(p.slots)]
    assert chiral == ["P3-y"]
