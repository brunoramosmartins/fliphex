"""Tests for ui.session — the half of the web interface that has no browser.

The point of this file is that the page's rules can be wrong *here*, where a
test can see it, rather than only in a browser where it looks like a drawing
bug.
"""

import pytest

from fliphex.board import OFF_BOARD, Board
from fliphex.moves import legal_moves
from fliphex.piece import N_SLOTS
from fliphex.state import TILES, Colour, tiles_in
from fliphex.variant import FIVE_BY_THREE, FULL_GAME, THREE_BY_THREE
from ui.session import COL_PITCH, ROW_PITCH, GameSession, arrows_of, layout

# -- geometry ------------------------------------------------------------------

#: Where each direction's neighbour must sit relative to a cell's centre, in
#: hex-radius units, clockwise from North. Flat-top hexagons: the two vertical
#: neighbours are a full row apart, the four diagonal ones half a row.
OFFSETS = {
    0: (0.0, -ROW_PITCH),  # N
    1: (COL_PITCH, -ROW_PITCH / 2),  # NE
    2: (COL_PITCH, ROW_PITCH / 2),  # SE
    3: (0.0, ROW_PITCH),  # S
    4: (-COL_PITCH, ROW_PITCH / 2),  # SW
    5: (-COL_PITCH, -ROW_PITCH / 2),  # NW
}


@pytest.mark.parametrize("board", [Board(5, 5), Board(5, 3), Board(3, 3)])
def test_the_drawn_layout_agrees_with_the_adjacency_table(board):
    """The test the whole module exists to make possible.

    ``docs/board-geometry.md`` is generated from ``Board``; a hand-placed SVG
    would be a third description of the board able to disagree with both. Here
    the drawing is derived instead, and this asserts it lands exactly where the
    engine says the neighbour is.
    """
    centres = {cell["id"]: (cell["x"], cell["y"]) for cell in layout(board)}
    checked = 0
    for cid in board.cells:
        x, y = centres[cid]
        for direction in range(N_SLOTS):
            neighbour = board.neighbour(cid, direction)
            if neighbour == OFF_BOARD:
                continue
            dx, dy = OFFSETS[direction]
            nx, ny = centres[neighbour]
            assert (nx - x, ny - y) == pytest.approx((dx, dy)), (
                f"{board.cell_name(cid)} {direction} -> {board.cell_name(neighbour)}"
            )
            checked += 1
    assert checked > 0


def test_every_cell_gets_exactly_one_record():
    board = Board(5, 5)
    cells = layout(board)
    assert len(cells) == board.n_cells
    assert {c["id"] for c in cells} == set(board.cells)
    assert {c["name"] for c in cells} == {board.cell_name(c) for c in board.cells}


def test_a1_is_the_origin():
    """Column-major from A1, as ``fliphex.board`` documents."""
    first = layout(Board(5, 5))[0]
    assert first["name"] == "A1"
    assert (first["x"], first["y"]) == (0.0, 0.0)


def test_odd_columns_are_dropped_half_a_row():
    cells = {c["name"]: c for c in layout(Board(5, 5))}
    assert cells["B1"]["y"] == pytest.approx(ROW_PITCH / 2)
    assert cells["C1"]["y"] == pytest.approx(0.0)


# -- arrows --------------------------------------------------------------------


def test_the_joker_carries_no_arrows():
    joker = next(t for t in range(len(TILES)) if TILES[t].archetype == "JOKER")
    assert arrows_of(joker, 0) == []


def test_p6_carries_all_six_at_every_rotation():
    p6 = next(t for t in range(len(TILES)) if TILES[t].archetype == "P6")
    for rotation in range(N_SLOTS):
        assert arrows_of(p6, rotation) == list(range(N_SLOTS))


def test_rotation_shifts_the_arrows():
    p1 = next(t for t in range(len(TILES)) if TILES[t].archetype == "P1")
    assert arrows_of(p1, 1) == [(arrows_of(p1, 0)[0] + 1) % N_SLOTS]


# -- the game surface ----------------------------------------------------------


def test_a_game_starts_on_the_variant_it_was_asked_for():
    game = GameSession(3, 3)
    geometry = game.geometry()
    assert geometry["n_cells"] == 9
    assert len(geometry["decks"]["first"]) == 5
    assert len(geometry["decks"]["second"]) == 4
    assert "JOKER" in geometry["decks"]["first"]


def test_the_h2_arm_swaps_the_joker_out():
    geometry = GameSession(3, 3, arm="h2").geometry()
    assert "JOKER" not in geometry["decks"]["first"]
    assert len(geometry["decks"]["first"]) == 5


def test_an_even_board_is_refused_by_the_variant():
    with pytest.raises(ValueError, match="odd cell count"):
        GameSession(4, 4)


def test_the_opening_snapshot_is_empty_and_purple_to_move():
    snapshot = GameSession().snapshot()
    assert set(snapshot["colours"]) == {"EMPTY"}
    assert snapshot["to_move"] == "PURPLE"
    assert snapshot["ply"] == 0
    assert snapshot["terminal"] is False
    assert snapshot["can_undo"] is False


def test_hands_are_reported_per_colour_and_shrink_as_they_are_played():
    game = GameSession(3, 3)
    before = len(game.snapshot()["hands"]["PURPLE"])
    tile = game.snapshot()["hands"]["PURPLE"][0]["tile"]
    game.play(game.playable_cells(tile)[0], tile, 0)
    assert len(game.snapshot()["hands"]["PURPLE"]) == before - 1


def test_rotation_options_are_the_distinct_ones_and_no_more():
    """P6 has one orbit, not six: offering six would be six identical previews."""
    game = GameSession()
    p6 = next(t for t in tiles_in(game.state.hand(1)) if TILES[t].archetype == "P6")
    assert len(game.options(game.playable_cells(p6)[0], p6)) == 1


def test_playable_cells_come_from_the_engine_not_from_emptiness():
    game = GameSession(3, 3)
    tile = next(iter(tiles_in(game.state.hand(1))))
    engine = sorted(
        {m.cell for m in legal_moves(game.board, game.state) if m.tile == tile}
    )
    assert game.playable_cells(tile) == engine


# -- moves and their effects ---------------------------------------------------


def test_a_first_move_on_an_empty_board_flips_nothing():
    game = GameSession()
    p6 = next(t for t in tiles_in(game.state.hand(1)) if TILES[t].archetype == "P6")
    result = game.play(game.board.cell_id("C3"), p6, 0)
    assert result["flipped"] == []
    assert {e["kind"] for e in result["effects"]} == {"empty"}
    assert result["net"] == 0


def test_an_arrow_off_the_board_is_reported_as_an_edge():
    game = GameSession()
    p6 = next(t for t in tiles_in(game.state.hand(1)) if TILES[t].archetype == "P6")
    result = game.play(game.board.cell_id("A1"), p6, 0)
    assert any(e["kind"] == "edge" for e in result["effects"])
    assert all(e["target"] is None for e in result["effects"] if e["kind"] == "edge")


def test_a_flip_is_reported_with_the_colour_it_becomes():
    """The page animates from this; if it lies, the animation lies."""
    game = GameSession()
    board = game.board
    p6 = next(t for t in tiles_in(game.state.hand(1)) if TILES[t].archetype == "P6")
    game.play(board.cell_id("C3"), p6, 0)

    green_p6 = next(
        t for t in tiles_in(game.state.hand(2)) if TILES[t].archetype == "P6"
    )
    result = game.play(board.cell_id("C2"), green_p6, 0)
    flips = [e for e in result["effects"] if e["kind"] == "flip"]
    assert flips, "green's P6 at C2 points south at purple's tile on C3"
    assert all(e["becomes"] == "GREEN" for e in flips)
    assert board.cell_id("C3") in result["flipped"]


def test_a_self_flip_hands_the_tile_to_the_opponent():
    """adr-007: a flip is a toggle, so your own arrow costs you the tile."""
    game = GameSession()
    board = game.board
    p6 = next(t for t in tiles_in(game.state.hand(1)) if TILES[t].archetype == "P6")
    game.play(board.cell_id("C3"), p6, 0)
    green = next(iter(tiles_in(game.state.hand(2))))
    game.play(board.cell_id("A1"), green, 0)

    # Any remaining purple tile with an arrow due South. Each player holds each
    # archetype once, so the P6 just played is gone and this must be general.
    south = 3
    tile, rotation = next(
        (t, r)
        for t in tiles_in(game.state.hand(1))
        for r in TILES[t].distinct_rotations()
        if south in arrows_of(t, r)
    )
    result = game.play(board.cell_id("C2"), tile, rotation)
    selfs = [e for e in result["effects"] if e["kind"] == "self-flip"]
    assert selfs, "purple's own tile sits on C3, due south of C2"
    assert all(e["becomes"] == "GREEN" for e in selfs)
    assert result["net"] < 0


def test_the_snapshot_after_a_move_reflects_it():
    game = GameSession(3, 3)
    tile = next(iter(tiles_in(game.state.hand(1))))
    result = game.play(game.playable_cells(tile)[0], tile, 0)
    assert result["snapshot"]["ply"] == 1
    assert result["snapshot"]["to_move"] == "GREEN"
    assert result["snapshot"]["can_undo"] is True


def test_an_illegal_move_is_refused_rather_than_applied():
    """The page offers only legal moves, so this firing means the two disagree."""
    game = GameSession(3, 3)
    tile = next(iter(tiles_in(game.state.hand(1))))
    cell = game.playable_cells(tile)[0]
    game.play(cell, tile, 0)
    with pytest.raises(ValueError, match="illegal move"):
        game.play(cell, tile, 0)  # the cell is occupied now


def test_a_tile_not_in_hand_is_refused():
    game = GameSession(3, 3)
    absent = next(
        t for t in range(len(TILES)) if t not in set(tiles_in(game.state.hand(1)))
    )
    with pytest.raises(ValueError, match="illegal move"):
        game.play(0, absent, 0)


# -- undo ----------------------------------------------------------------------


def test_undo_returns_the_previous_position():
    game = GameSession(3, 3)
    opening = game.snapshot()
    tile = next(iter(tiles_in(game.state.hand(1))))
    game.play(game.playable_cells(tile)[0], tile, 0)
    assert game.undo()["colours"] == opening["colours"]
    assert game.snapshot()["ply"] == 0


def test_undo_at_the_opening_is_a_no_op_not_an_error():
    game = GameSession(3, 3)
    assert game.undo()["ply"] == 0


# -- whole games ---------------------------------------------------------------


@pytest.mark.parametrize("variant", [THREE_BY_THREE, FIVE_BY_THREE, FULL_GAME])
def test_a_game_played_through_the_bridge_fills_the_board_and_decides(variant):
    """No draw is possible on an odd cell count, so a draw here is a bug."""
    game = GameSession(variant.n_cols, variant.n_rows)
    while not game.snapshot()["terminal"]:
        move = legal_moves(game.board, game.state)[0]
        game.play(move.cell, move.tile, move.rotation)
    final = game.snapshot()
    assert "EMPTY" not in final["colours"]
    assert final["winner"] in ("PURPLE", "GREEN")
    assert sum(final["score"].values()) == variant.n_cells


def test_an_agent_can_take_a_seat_through_the_bridge():
    from ui.seats import build_seat

    game = GameSession(3, 3)
    agent = build_seat("heuristic", variant=THREE_BY_THREE, seed=0)
    result = game.agent_move(agent)
    assert result["snapshot"]["ply"] == 1
    assert result["placed_as"] == "PURPLE"


def test_both_hands_exhaust_exactly_so_every_tile_is_played():
    """H5's structural finding, arrived at through the interface."""
    game = GameSession(3, 3)
    played = []
    while not game.snapshot()["terminal"]:
        move = legal_moves(game.board, game.state)[0]
        played.append(game.play(move.cell, move.tile, move.rotation)["archetype"])
    assert len(played) == 9
    assert game.snapshot()["hands"] == {"PURPLE": [], "GREEN": []}


def test_the_score_is_a_cell_count_and_always_sums_to_the_board():
    game = GameSession(3, 3)
    while not game.snapshot()["terminal"]:
        move = legal_moves(game.board, game.state)[0]
        snapshot = game.play(move.cell, move.tile, move.rotation)["snapshot"]
        filled = sum(1 for c in snapshot["colours"] if c != "EMPTY")
        assert sum(snapshot["score"].values()) == filled


def test_colour_names_cross_the_boundary_as_strings():
    """The page is JavaScript; an enum would arrive as an opaque proxy."""
    snapshot = GameSession(3, 3).snapshot()
    assert all(isinstance(c, str) for c in snapshot["colours"])
    assert isinstance(snapshot["to_move"], str)
    assert Colour.PURPLE.name in {"PURPLE"}


# -- what the page calls that a CLI does not -----------------------------------


def test_history_for_drawing_records_what_each_placed_tile_fired():
    """adr-003 throws tile identity away; this is where it survives for drawing."""
    game = GameSession(3, 3)
    p6 = next(t for t in tiles_in(game.state.hand(1)) if TILES[t].archetype == "P6")
    game.play(game.playable_cells(p6)[0], p6, 0)
    drawn = game.history_for_drawing()
    assert len(drawn) == 1
    assert drawn[0]["arrows"] == list(range(N_SLOTS))
    assert drawn[0]["cell"] == game.state.history[0][0]


def test_history_for_drawing_is_empty_at_the_opening_and_grows_by_one():
    game = GameSession(3, 3)
    assert game.history_for_drawing() == []
    for expected in range(1, 4):
        move = legal_moves(game.board, game.state)[0]
        game.play(move.cell, move.tile, move.rotation)
        assert len(game.history_for_drawing()) == expected


def test_history_for_drawing_survives_an_undo():
    game = GameSession(3, 3)
    move = legal_moves(game.board, game.state)[0]
    game.play(move.cell, move.tile, move.rotation)
    game.undo()
    assert game.history_for_drawing() == []


def test_a_seat_can_be_named_as_a_string_the_page_can_send():
    game = GameSession(3, 3)
    result = game.agent_move_by_name("heuristic", seed=0)
    assert result["snapshot"]["ply"] == 1


def test_naming_the_human_seat_is_refused_rather_than_silently_passing():
    game = GameSession(3, 3)
    with pytest.raises(ValueError, match="human seat"):
        game.agent_move_by_name("human")


def test_naming_a_seat_that_does_not_exist_is_refused():
    game = GameSession(3, 3)
    with pytest.raises(ValueError, match="unknown seat"):
        game.agent_move_by_name("grandmaster")
