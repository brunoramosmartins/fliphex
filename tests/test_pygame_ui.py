"""Tests for the display-free half of ui.pygame_ui.

The window itself needs a display and is not tested here. What *is* tested is
everything that decides where a hexagon goes and which one a click landed on —
the part that can be silently wrong and look merely "a bit off".
"""

import pytest

from fliphex.board import OFF_BOARD, Board
from fliphex.piece import N_SLOTS
from fliphex.variant import FIVE_BY_THREE, FULL_GAME, THREE_BY_THREE
from ui.pygame_ui import (
    EMPTY,
    GREEN,
    PURPLE,
    Placement,
    cell_at,
    colour_of,
    describe,
    direction_vector,
    fit_board,
    hex_corners,
    net_label,
)
from ui.session import layout

BOARDS = [Board(5, 5), Board(5, 3), Board(3, 3)]


# -- the hexagon ---------------------------------------------------------------


def test_a_hexagon_has_six_corners_at_one_radius():
    corners = hex_corners(100.0, 50.0, 20.0)
    assert len(corners) == 6
    for x, y in corners:
        assert ((x - 100.0) ** 2 + (y - 50.0) ** 2) ** 0.5 == pytest.approx(20.0)


def test_the_hexagon_is_flat_topped_not_pointy():
    """Flat top means a vertex due East and West, never due North."""
    corners = hex_corners(0.0, 0.0, 1.0)
    assert any(x == pytest.approx(1.0) and y == pytest.approx(0.0) for x, y in corners)
    assert not any(abs(x) < 1e-9 and y == pytest.approx(-1.0) for x, y in corners)


def test_the_flat_edges_are_horizontal():
    ys = sorted({round(y, 6) for _, y in hex_corners(0.0, 0.0, 1.0)})
    assert len(ys) == 3, "two corners share the top edge and two the bottom"


# -- directions ----------------------------------------------------------------


def test_slot_zero_points_north():
    dx, dy = direction_vector(0)
    assert dx == pytest.approx(0.0)
    assert dy == pytest.approx(-1.0), "screen y grows downwards"


def test_slot_three_points_south():
    dx, dy = direction_vector(3)
    assert (dx, dy) == pytest.approx((0.0, 1.0))


def test_the_six_directions_are_unit_vectors_sixty_degrees_apart():
    vectors = [direction_vector(s) for s in range(N_SLOTS)]
    for dx, dy in vectors:
        assert (dx * dx + dy * dy) ** 0.5 == pytest.approx(1.0)
    assert len({(round(x, 6), round(y, 6)) for x, y in vectors}) == N_SLOTS


def test_opposite_slots_are_opposite_vectors():
    for slot in range(N_SLOTS // 2):
        a = direction_vector(slot)
        b = direction_vector(slot + 3)
        assert a == pytest.approx((-b[0], -b[1]))


# -- fitting -------------------------------------------------------------------


@pytest.mark.parametrize("board", BOARDS)
def test_every_hexagon_lands_inside_the_window(board):
    cells = layout(board)
    placement = fit_board(cells, 900, 620)
    for cell in cells:
        cx, cy = placement.centre(cell)
        assert cx - placement.radius >= 0 and cx + placement.radius <= 900
        assert cy - placement.radius >= 0 and cy + placement.radius <= 620


@pytest.mark.parametrize("board", BOARDS)
def test_the_board_is_centred(board):
    cells = layout(board)
    placement = fit_board(cells, 900, 620)
    xs = [placement.centre(c)[0] for c in cells]
    ys = [placement.centre(c)[1] for c in cells]
    assert (min(xs) + max(xs)) / 2 == pytest.approx(450, abs=1.0)
    assert (min(ys) + max(ys)) / 2 == pytest.approx(310, abs=1.0)


def test_a_smaller_board_gets_bigger_hexagons():
    """The fit comes from the layout, so no per-board constant exists anywhere."""
    big = fit_board(layout(Board(5, 5)), 900, 620).radius
    small = fit_board(layout(Board(3, 3)), 900, 620).radius
    assert small > big


def test_neighbouring_hexagons_touch_but_do_not_overlap():
    """Pitch is a property of the layout; this asserts the scaling preserves it."""
    board = Board(5, 5)
    cells = layout(board)
    placement = fit_board(cells, 900, 620)
    centres = {c["id"]: placement.centre(c) for c in cells}
    for cid in board.cells:
        for direction in range(N_SLOTS):
            neighbour = board.neighbour(cid, direction)
            if neighbour == OFF_BOARD:
                continue
            ax, ay = centres[cid]
            bx, by = centres[neighbour]
            distance = ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
            # Flat-top hexagons of radius r sit sqrt(3)*r apart in every
            # direction they share an edge with.
            assert distance == pytest.approx(placement.radius * 3**0.5)


# -- hit testing ---------------------------------------------------------------


@pytest.mark.parametrize("board", BOARDS)
def test_clicking_a_centre_selects_that_cell(board):
    cells = layout(board)
    placement = fit_board(cells, 900, 620)
    for cell in cells:
        assert cell_at(placement.centre(cell), cells, placement) == cell["id"]


def test_clicking_outside_the_board_selects_nothing():
    cells = layout(Board(5, 5))
    placement = fit_board(cells, 900, 620)
    assert cell_at((5.0, 5.0), cells, placement) is None
    assert cell_at((895.0, 615.0), cells, placement) is None


def test_a_click_near_a_centre_still_lands_on_it():
    cells = layout(Board(5, 5))
    placement = fit_board(cells, 900, 620)
    cx, cy = placement.centre(cells[7])
    nudge = placement.radius * 0.3
    for dx, dy in ((nudge, 0), (-nudge, 0), (0, nudge), (0, -nudge)):
        assert cell_at((cx + dx, cy + dy), cells, placement) == cells[7]["id"]


def test_a_click_between_two_cells_picks_the_nearer():
    cells = layout(Board(5, 5))
    placement = fit_board(cells, 900, 620)
    a, b = cells[0], cells[1]
    ax, ay = placement.centre(a)
    bx, by = placement.centre(b)
    point = (ax + (bx - ax) * 0.3, ay + (by - ay) * 0.3)
    assert cell_at(point, cells, placement) == a["id"]


def test_the_placement_scales_the_layout_rather_than_recomputing_it():
    """The layout arrives in radius units; the window only multiplies."""
    placement = Placement(radius=10.0, origin_x=100.0, origin_y=200.0)
    assert placement.centre({"x": 0.0, "y": 0.0}) == (100.0, 200.0)
    assert placement.centre({"x": 1.5, "y": 2.0}) == (115.0, 220.0)


# -- small renderable bits -----------------------------------------------------


def test_cell_colours_match_the_palette():
    assert colour_of("PURPLE") == PURPLE
    assert colour_of("GREEN") == GREEN
    assert colour_of("EMPTY") == EMPTY


def test_an_unknown_state_reads_as_empty_rather_than_raising():
    assert colour_of("nonsense") == EMPTY


@pytest.mark.parametrize(("net", "text"), [(2, "+2"), (0, "0"), (-1, "-1")])
def test_the_net_swing_carries_its_sign(net, text):
    assert net_label(net) == text


def test_a_move_that_flips_says_so():
    result = {
        "placed_as": "PURPLE",
        "archetype": "P6",
        "effects": [{"kind": "flip"}, {"kind": "flip"}, {"kind": "empty"}],
    }
    assert describe(result, "C3") == "Purple played P6 on C3, flipping 2."


def test_a_self_flip_is_named_in_the_status_line():
    result = {
        "placed_as": "GREEN",
        "archetype": "P1",
        "effects": [{"kind": "self-flip"}],
    }
    assert "handing back 1" in describe(result, "B2")


def test_a_move_with_nothing_to_flip_says_that_too():
    result = {"placed_as": "PURPLE", "archetype": "JOKER", "effects": []}
    assert "nothing to flip" in describe(result, "A1")


# -- the module stays importable without a display -----------------------------


def test_importing_the_window_module_does_not_require_pygame():
    """`pygame` is imported inside `Window.__init__`, so CI needs no display."""
    import subprocess
    import sys

    probe = "import sys, ui.pygame_ui; print('pygame' in sys.modules)"
    out = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == "False", out.stdout


@pytest.mark.parametrize("variant", [THREE_BY_THREE, FIVE_BY_THREE, FULL_GAME])
def test_every_variant_fits_without_a_per_board_constant(variant):
    placement = fit_board(layout(variant.board()), 900, 620)
    assert placement.radius > 10


# -- the window itself, headless -----------------------------------------------

_SMOKE = """
import pygame
from ui.pygame_ui import Window
from ui.session import GameSession

window = Window(GameSession(3, 3), "heuristic", seed=0)
window._paint()

rect, _ = window.hand_rects[0]
window._on_click(rect.center)
assert window.selected_tile is not None, "clicking a piece selected nothing"
assert len(window._playable_cells()) == 9, "every empty cell should be playable"

cell = sorted(window._playable_cells())[4]
window._on_click(tuple(int(v) for v in window.placement.centre(window.cells[cell])))
assert window.options, "clicking a cell offered no rotation"
window._rotate(1)
window._paint()

window._commit()
assert window.snapshot["ply"] == 2, "the agent did not reply"
assert "played" in window.status

window._undo()
assert window.snapshot["ply"] == 0

window._new_game()
assert window.snapshot["ply"] == 0 and len(window.cells) == 9
window._paint()
print("SMOKE OK")
"""


def test_the_window_opens_paints_and_plays_a_move():
    """Driven under SDL's dummy video driver, so CI needs no display.

    Everything above this point is geometry with no pygame in it. This is the
    one test that builds the real window — and it exists because the web page's
    two defects were both in code the test suite structurally could not reach,
    which is a mistake worth not repeating in the same phase.
    """
    import os
    import subprocess
    import sys

    pytest.importorskip("pygame")
    environment = {**os.environ, "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}
    result = subprocess.run(
        [sys.executable, "-c", _SMOKE],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert "SMOKE OK" in result.stdout
