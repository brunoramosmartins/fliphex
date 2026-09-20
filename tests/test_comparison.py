"""Tests for ``complexity/comparison.py``.

This module's job is provenance, so most of these tests are about provenance
rather than arithmetic. The important one is
``test_every_verified_quote_resolves_in_its_source``: it opens each cited file
under ``notes/sources`` and looks for the quoted text. A citation that stops
resolving -- because the source was re-ingested, re-OCR'd or moved -- fails here
instead of quietly becoming decoration.

The second group pins the two claims this project makes *against* the
literature: that the widely repeated 6x6 Reversi state space is impossible, and
that Connect Four's cited 10^14 is an estimate roughly 22x above the exact
count. Both are the reason the table grades cells instead of just filling them.
"""

from __future__ import annotations

from math import log10

import pytest

from complexity.comparison import (
    REVERSI_6X6_CLAIM,
    SOURCES,
    SOURCES_PRESENT,
    TAXONOMY,
    Provenance,
    external_rows,
    fliphex_row,
    gaps,
    reversi_6x6_ceiling,
    reversi_6x6_overshoot,
    self_check,
    table,
)
from complexity.game_tree import games
from complexity.state_space import profile
from fliphex.variant import Arm, Variant

ROWS = table()


def _figures():
    for row in ROWS:
        yield row.game, "state space", row.state_space
        yield row.game, "game tree", row.game_tree


# -- provenance -------------------------------------------------------------


def test_self_check_is_clean():
    assert self_check() == []


@pytest.mark.skipif(
    not SOURCES_PRESENT,
    reason="notes/sources/ is gitignored; a fresh clone has the bibliography, "
    "not the ingested texts. The citation stands on SOURCES either way.",
)
def test_every_verified_quote_resolves_in_its_source():
    """The check that makes a citation mean something. Duplicated from
    ``self_check`` on purpose: this one fails loudly and by name."""
    from pathlib import Path

    sources = Path(__file__).resolve().parent.parent / "notes" / "sources"
    checked = 0
    for game, axis, figure in _figures():
        if figure.provenance is not Provenance.VERIFIED:
            continue
        path = sources / figure.locator
        assert path.exists(), f"{game} {axis}: {path} is gone"
        assert figure.quote in path.read_text(), f"{game} {axis}: quote moved"
        checked += 1
    # A floor, so a loop that silently checks nothing cannot pass. Six today:
    # Othello on both axes, and the state space of checkers, Nine Men's Morris,
    # Awari and chess.
    assert checked >= 6


def test_every_verified_figure_carries_a_quote_even_without_the_text():
    """Runs everywhere, including CI. The quote is tracked in this file; only
    checking it against the source needs the gitignored text."""
    for game, axis, figure in _figures():
        if figure.provenance is Provenance.VERIFIED:
            assert figure.quote, f"{game} {axis}"
            assert figure.locator, f"{game} {axis}"


def test_the_bibliography_is_self_contained():
    """Each external entry names a year, so the repo cites without depending on
    ``notes/sources/``, which is gitignored and absent from a fresh clone."""
    import re

    for key, entry in SOURCES.items():
        assert len(entry) > 60, key
        if key == "this project":
            continue
        assert re.search(r"\b(19|20)\d{2}\b", entry), key


def test_every_source_key_is_in_the_bibliography():
    for game, axis, figure in _figures():
        if figure.source and figure.source != "—":
            assert figure.source in SOURCES, f"{game} {axis}"
    for row in ROWS:
        if row.solved_source:
            assert row.solved_source in SOURCES, row.game


def test_absent_and_refuted_cells_print_nothing():
    """The whole point: a cell nobody could source must not carry a number."""
    for game, axis, figure in _figures():
        if figure.provenance in (Provenance.ABSENT, Provenance.REFUTED):
            assert figure.log10 is None, f"{game} {axis}"
            assert figure.printable == "—"


def test_graded_cells_all_carry_a_figure():
    for game, axis, figure in _figures():
        if figure.provenance in (Provenance.EXACT, Provenance.VERIFIED):
            assert figure.log10 is not None, f"{game} {axis}"


def test_every_absent_cell_says_why():
    """A gap without a reason is indistinguishable from an oversight."""
    assert gaps()
    for game, axis, note in gaps():
        assert note.strip(), f"{game} {axis}"


def test_no_figure_is_cited_to_the_unverified_table():
    """van den Herik Table 1 is named in notes, never used as a figure.

    Two secondary reproductions of it disagree by 1-2 in the exponent on four
    rows, so nothing is printed from it until the PDF is opened.
    """
    for game, axis, figure in _figures():
        if figure.source == "van den Herik 2002":
            assert figure.provenance is Provenance.ABSENT, f"{game} {axis}"


def test_solved_status_uses_allis_s_terms():
    for row in ROWS:
        assert row.solved in set(TAXONOMY) | {"unsolved"}


def test_the_taxonomy_is_quoted_not_paraphrased():
    assert TAXONOMY["weakly solved"].startswith("For the initial position(s)")
    assert set(TAXONOMY) == {
        "ultra-weakly solved",
        "weakly solved",
        "strongly solved",
    }


# -- the two claims against the literature ----------------------------------


def test_the_6x6_reversi_figure_is_impossible():
    """3^36 bounds it before any legality constraint is applied."""
    ceiling, ceiling_log = reversi_6x6_ceiling()
    assert ceiling == 3**36
    assert ceiling == 150_094_635_296_999_121
    assert round(ceiling_log, 2) == 17.18
    assert ceiling < REVERSI_6X6_CLAIM
    assert round(reversi_6x6_overshoot()) == 666


def test_the_refuted_row_names_no_alternative_figure():
    """Refuting a number does not entitle us to invent one."""
    reversi = next(row for row in ROWS if row.game == "Reversi 6×6")
    assert reversi.state_space.provenance is Provenance.REFUTED
    assert reversi.state_space.log10 is None
    assert reversi.state_space.exact is None


def test_connect_four_carries_the_exact_count_not_the_cited_estimate():
    """10^14 is cited by two primary sources and is 22x the enumeration."""
    row = next(r for r in ROWS if r.game == "Connect Four")
    assert row.state_space.exact == 4_531_985_219_092
    assert 21 < 1e14 / row.state_space.exact < 23


# -- FLIPHEX's own rows -----------------------------------------------------


@pytest.mark.parametrize("board", [(3, 3), (5, 3), (5, 5)])
def test_fliphex_rows_come_from_the_modules_that_compute_them(board):
    variant = Variant(board[0], board[1], Arm.H1)
    row = fliphex_row(variant)
    assert row.state_space.exact == profile(variant).reachable
    assert row.game_tree.exact == games(variant)
    assert row.state_space.provenance is Provenance.EXACT
    assert row.game_tree.provenance is Provenance.EXACT


def test_the_state_space_cell_is_the_reachable_one_not_the_superset():
    """Allis's definition says reachable; the two differ by 0.0079% here."""
    variant = Variant(5, 5, Arm.H1)
    space = profile(variant)
    row = fliphex_row(variant)
    assert row.state_space.exact == space.reachable
    assert row.state_space.exact != space.configurations
    assert "reachable" in row.state_space.note


def test_the_game_tree_cell_is_leaves_and_says_so():
    variant = Variant(5, 5, Arm.H1)
    row = fliphex_row(variant)
    assert row.game_tree.exact == games(variant)
    assert "leaves" in row.game_tree.note
    assert "all nodes" in row.game_tree.note


def test_the_shipped_board_is_not_claimed_solved():
    row = next(r for r in ROWS if r.game == "FLIPHEX 5×5")
    assert row.solved == "unsolved"


# -- what the table shows ---------------------------------------------------

SHIPPED = next(r for r in ROWS if r.game == "FLIPHEX 5×5")


def test_checkers_has_a_larger_state_space_and_was_solved_anyway():
    """H4's own premise, and it survives: 10^20.7 against FLIPHEX's 10^17.7."""
    checkers = next(r for r in ROWS if r.game == "Checkers 8×8")
    assert checkers.state_space.log10 > SHIPPED.state_space.log10
    assert checkers.solved == "weakly solved"


def test_the_shipped_board_exceeds_every_strongly_solved_state_space():
    """H4 clause 1, checked against the rows that are actually graded."""
    strong = [
        r
        for r in ROWS
        if r.solved == "strongly solved" and r.state_space.log10 is not None
    ]
    assert strong
    assert all(SHIPPED.state_space.log10 > r.state_space.log10 for r in strong)


def test_othello_sits_at_the_same_game_tree_order_and_was_weakly_solved():
    """The finding H4's verdict has to answer.

    Othello 8x8's game tree is 10^58 and it was weakly solved in 2023. FLIPHEX
    is 10^58.63 -- a factor of four, not an order of magnitude. Whatever the
    verdict says about "beyond the weak-solution route", it has to address this
    row rather than only the checkers row H4 names.
    """
    othello = next(r for r in ROWS if r.game == "Othello 8×8")
    assert othello.solved == "weakly solved"
    assert abs(othello.game_tree.log10 - SHIPPED.game_tree.log10) < 1.0
    assert SHIPPED.game_tree.log10 > othello.game_tree.log10


def test_the_shipped_game_tree_is_not_the_locked_ten_to_the_61():
    """H4 cites ~10^61; the exact count is 10^58.63, about 240x smaller."""
    assert round(SHIPPED.game_tree.log10, 2) == 58.63
    assert 200 < 10 ** (61 - SHIPPED.game_tree.log10) < 300


def test_rows_are_ordered_by_state_space_with_gaps_last():
    graded = [r.state_space.log10 for r in ROWS if r.state_space.log10 is not None]
    assert graded == sorted(graded)
    ungraded = [i for i, r in enumerate(ROWS) if r.state_space.log10 is None]
    assert all(i >= len(graded) for i in ungraded)


def test_the_table_holds_every_fliphex_board_and_the_external_rows():
    assert len(ROWS) == 3 + len(external_rows())
    assert sum(1 for r in ROWS if r.game.startswith("FLIPHEX")) == 3


def test_imports_nothing_from_solver_or_az():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parent.parent / "complexity" / "comparison.py"
    ).read_text()
    for forbidden in ("import solver", "from solver", "import az", "from az"):
        assert forbidden not in source


def test_as_dict_round_trips_through_json():
    import json

    payload = json.loads(json.dumps([row.as_dict() for row in ROWS]))
    shipped = next(r for r in payload if r["game"] == "FLIPHEX 5×5")
    assert shipped["state_space"]["provenance"] == "exact"
    assert round(shipped["game_tree"]["log10"], 2) == round(
        log10(games(Variant(5, 5, Arm.H1))), 2
    )
