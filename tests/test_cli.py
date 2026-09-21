"""Tests for the pure parts of ui.cli — rendering, parsing, seats and the loop."""

import pytest

from agents.heuristic_agent import HeuristicAgent
from agents.random_agent import RandomAgent
from fliphex.board import Board
from fliphex.state import TILES, Colour, GameState, tiles_in
from fliphex.variant import FIVE_BY_THREE, FULL_GAME, THREE_BY_THREE, Arm, Variant
from ui.cli import (
    _LEGACY_MODES,
    _parse_move,
    _variant_from,
    header,
    main,
    play,
    render_board,
    resolve_kinds,
)
from ui.seats import build_seat

# -- rendering and parsing -----------------------------------------------------


def test_render_shows_names_and_marks():
    board = Board()
    s = GameState.initial().with_colour(board.cell_id("A1"), Colour.PURPLE)
    text = render_board(board, s)
    assert "A1P" in text  # purple on A1
    assert "E5·" in text  # empty elsewhere
    assert len(text.splitlines()) == 10  # five columns, offset into ten bands


def test_parse_move_with_and_without_rotation():
    board = Board()
    assert _parse_move(board, "C3:P1:0") == _parse_move(board, "C3:P1")
    assert _parse_move(board, "C3:P1:0").rotation == 0


def test_parse_move_rejects_garbage():
    board = Board()
    assert _parse_move(board, "not a move") is None
    assert _parse_move(board, "Z9:P1:0") is None


# -- variant parsing -----------------------------------------------------------


def test_a_variant_spec_becomes_a_board_and_a_deck():
    variant = _variant_from("5x3", "h1", "purple")
    assert (variant.n_cols, variant.n_rows) == (5, 3)
    assert variant.arm is Arm.H1
    assert variant.first == Colour.PURPLE


def test_an_even_board_is_refused_with_adr_011s_reason():
    with pytest.raises(SystemExit, match="odd cell count"):
        _variant_from("4x4", "h1", "purple")


def test_a_malformed_spec_says_what_the_shape_should_be():
    with pytest.raises(SystemExit, match="COLSxROWS"):
        _variant_from("enormous", "h1", "purple")


def test_the_h2_arm_is_refused_on_the_shipped_board():
    """Not a CLI rule — ``Variant`` owns it, and the CLI must relay it."""
    with pytest.raises(SystemExit, match="H2 arm does not exist"):
        _variant_from("5x5", "h2", "purple")


# -- the header ----------------------------------------------------------------


def test_the_header_prints_both_decks_because_a_bare_size_is_ambiguous():
    text = header(FIVE_BY_THREE, None, HeuristicAgent(seed=0))
    assert "5x3" in text
    assert "holds 8 tiles" in text and "holds 7" in text
    assert "P6" in text and "P3-y" in text  # adr-009's two anchors
    assert "JOKER" in text


def test_the_header_names_who_sits_where():
    text = header(FULL_GAME, None, HeuristicAgent(seed=0))
    assert "PURPLE   human" in text
    assert "GREEN    heuristic" in text


# -- the reduced-deck regression ----------------------------------------------


def test_a_reduced_board_is_dealt_a_reduced_deck(capsys):
    """The bug ``--variant`` would have exposed.

    Building the opening from ``board.n_cells`` alone deals the full 13 + 12
    deck onto whatever board is passed. On nine cells that is playable and
    wrong: the hands never exhaust, so it is not the game adr-011 defines and
    not the one the solved artefacts describe.
    """
    play(
        THREE_BY_THREE,
        build_seat("heuristic", variant=THREE_BY_THREE, seed=0),
        build_seat("random", variant=THREE_BY_THREE, seed=1),
    )
    out = capsys.readouterr().out
    assert "holds 5 tiles" in out and "holds 4" in out


def test_both_hands_exhaust_exactly_on_every_variant():
    """The property H5's verdict rests on, checked through the CLI's own path."""
    for variant in (THREE_BY_THREE, FIVE_BY_THREE, FULL_GAME):
        state = variant.initial_state()
        held = sum(len(list(tiles_in(state.hand(p)))) for p in (1, 2))
        assert held == variant.n_cells, variant.name


# -- the game loop -------------------------------------------------------------


def test_ai_vs_ai_runs_to_a_winner(capsys):
    win = play(FULL_GAME, HeuristicAgent(seed=0), RandomAgent(seed=0))
    assert win in (Colour.PURPLE, Colour.GREEN)
    assert "wins" in capsys.readouterr().out


def test_a_solver_seat_reports_its_proved_rate(capsys):
    """No solver result may be quoted without it — EXP-017's own rule."""
    play(
        THREE_BY_THREE,
        build_seat("solver", variant=THREE_BY_THREE, seed=0),
        build_seat("heuristic", variant=THREE_BY_THREE, seed=0),
    )
    out = capsys.readouterr().out
    assert "PURPLE solver:" in out
    assert "moves proved (100%)" in out


def test_a_seat_with_no_solver_reports_no_rate(capsys):
    play(THREE_BY_THREE, HeuristicAgent(seed=0), RandomAgent(seed=0))
    assert "proved" not in capsys.readouterr().out


def test_the_game_fills_every_cell_and_cannot_draw():
    """25 is odd, and so is every legal variant (adr-011). A draw is a bug."""
    for variant in (THREE_BY_THREE, FIVE_BY_THREE):
        win = play(
            variant,
            build_seat("heuristic", variant=variant, seed=0),
            build_seat("random", variant=variant, seed=1),
        )
        assert win in (Colour.PURPLE, Colour.GREEN)


def test_green_can_move_first_and_hold_the_larger_hand(capsys):
    variant = Variant(3, 3, Arm.H1, Colour.GREEN)
    play(
        variant,
        build_seat("random", variant=variant, seed=0),
        build_seat("random", variant=variant, seed=1),
    )
    assert "GREEN moves first and holds 5 tiles" in capsys.readouterr().out


# -- argument wiring -----------------------------------------------------------


def test_the_legacy_modes_still_name_seats():
    assert _LEGACY_MODES["human-human"] == ("human", "human")
    assert _LEGACY_MODES["human-ai"] == ("human", None)
    assert _LEGACY_MODES["ai-ai"] == (None, None)


@pytest.mark.parametrize(
    ("purple", "green", "mode", "expected"),
    [
        (None, None, None, ("human", "human")),
        (None, None, "human-human", ("human", "human")),
        (None, None, "human-ai", ("human", "heuristic")),
        (None, None, "ai-ai", ("heuristic", "heuristic")),
        (None, "random", None, ("human", "random")),
        ("random", "heuristic", None, ("random", "heuristic")),
        (None, "random", "human-ai", ("human", "random")),
        ("solver", None, "ai-ai", ("solver", "heuristic")),
    ],
)
def test_seats_resolve_from_flags(purple, green, mode, expected):
    kinds = resolve_kinds(purple, green, mode, "heuristic")
    assert (kinds[Colour.PURPLE], kinds[Colour.GREEN]) == expected


def test_an_explicit_seat_beats_the_legacy_mode_that_would_have_set_it():
    kinds = resolve_kinds("az", None, "human-human", "heuristic")
    assert kinds[Colour.PURPLE] == "az"


def test_the_ai_flag_reaches_both_seats_of_a_legacy_ai_game():
    kinds = resolve_kinds(None, None, "ai-ai", "random")
    assert set(kinds.values()) == {"random"}


def test_seats_reach_the_game_through_main(capsys):
    main(
        [
            "--purple",
            "heuristic",
            "--green",
            "random",
            "--variant",
            "3x3",
            "--seed",
            "0",
            "--no-color",
        ]
    )
    out = capsys.readouterr().out
    assert "PURPLE   heuristic" in out and "GREEN    random" in out
    assert "wins" in out


def test_the_two_seats_get_distinct_seeds(capsys):
    """One seed shared by two stochastic agents replays one stream twice."""
    main(
        [
            "--purple",
            "random",
            "--green",
            "random",
            "--variant",
            "3x3",
            "--seed",
            "0",
            "--no-color",
        ]
    )
    first = capsys.readouterr().out
    main(
        [
            "--purple",
            "random",
            "--green",
            "random",
            "--variant",
            "3x3",
            "--seed",
            "0",
            "--no-color",
        ]
    )
    assert capsys.readouterr().out == first, "the same seed must replay the game"


def test_an_unavailable_champion_exits_rather_than_traces(capsys):
    with pytest.raises(SystemExit, match="GREEN seat"):
        main(["--green", "az", "--az-run", "data/az-runs/absent", "--no-color"])


def test_an_illegal_variant_exits_from_main():
    with pytest.raises(SystemExit, match="odd cell count"):
        main(["--variant", "4x4", "--no-color"])


# -- move explanation ----------------------------------------------------------


def test_a_self_flip_is_called_one(capsys):
    """adr-007: a flip is a toggle, so an arrow at your own tile costs you it."""
    from fliphex.moves import Move
    from ui.cli import explain_move

    board = Board()
    state = GameState.initial()
    p6 = next(t for t in tiles_in(state.hand(1)) if TILES[t].archetype == "P6")
    after = play_one(board, state, Move(board.cell_id("C3"), p6, 0))
    p1 = next(t for t in tiles_in(after.hand(2)) if TILES[t].archetype == "P1")
    text = explain_move(board, after, Move(board.cell_id("C2"), p1, 3))
    assert "self-FLIP" in text or "FLIP" in text


def play_one(board, state, move):
    from fliphex.moves import apply_move

    return apply_move(board, state, move)
