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
    BOARDS as STRIP_BOARDS,
)
from ui.pygame_ui import (
    EMPTY,
    GREEN,
    PURPLE,
    Control,
    Placement,
    board_values,
    cell_at,
    colour_of,
    control_at,
    describe,
    direction_vector,
    fit_board,
    hex_corners,
    net_label,
)
from ui.seats import SEAT_KINDS
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


# -- the replay viewer ---------------------------------------------------------


def test_the_scrubber_maps_its_ends_to_the_ends_of_the_game():
    pygame = pytest.importorskip("pygame")
    from ui.replay_viewer import ply_at, scrubber_rect

    rect = scrubber_rect(pygame)
    assert ply_at(rect.left, 25, rect) == 0
    assert ply_at(rect.right, 25, rect) == 25
    assert ply_at(rect.centerx, 24, rect) == 12


def test_the_scrubber_clamps_a_click_outside_itself():
    pygame = pytest.importorskip("pygame")
    from ui.replay_viewer import ply_at, scrubber_rect

    rect = scrubber_rect(pygame)
    assert ply_at(rect.left - 500, 25, rect) == 0
    assert ply_at(rect.right + 500, 25, rect) == 25


def test_an_empty_recording_does_not_divide_by_zero():
    pygame = pytest.importorskip("pygame")
    from ui.replay_viewer import ply_at, scrubber_rect

    assert ply_at(100, 0, scrubber_rect(pygame)) == 0


_REPLAY_SMOKE = """
from ui.replay import Recording, Replay
from ui.replay_viewer import Viewer, ply_at, scrubber_rect
from fliphex.variant import THREE_BY_THREE
import pygame

recording = Recording.from_seats(THREE_BY_THREE, "heuristic", "random", seed=2)
recording.replay()
viewer = Viewer(Replay(recording))

viewer._paint()
assert viewer.replay.ply == 0

viewer.step(1)
viewer._paint()
assert viewer.replay.ply == 1 and "ply 1/9" in viewer.replay.caption()

viewer.goto(9)
viewer._paint()
assert viewer.snapshot["terminal"]
assert viewer.snapshot["winner"] == recording.outcome["winner"]

viewer.goto(0)
assert set(viewer.snapshot["colours"]) == {"EMPTY"}

rect = scrubber_rect(pygame)
viewer.goto(ply_at(rect.centerx, viewer.replay.total, rect))
viewer._paint()
assert viewer.replay.ply == 4

viewer.playing = True
viewer.goto(9)
viewer.step(1)
assert viewer.playing is False, "playing must stop at the end"
print("SMOKE OK")
"""


def test_the_replay_viewer_opens_paints_and_seeks():
    """The window itself, under SDL's dummy driver."""
    import os
    import subprocess
    import sys

    pytest.importorskip("pygame")
    environment = {**os.environ, "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}
    result = subprocess.run(
        [sys.executable, "-c", _REPLAY_SMOKE],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert "SMOKE OK" in result.stdout


# -- which colour the person holds ---------------------------------------------


def test_the_net_badge_flips_below_a_cell_it_would_clip_above():
    """Caught in a screenshot: previewing on the top row drew it off-window.

    The badge is the one number the rotation preview exists to show, and it was
    invisible on the row a player is most likely to open on.
    """
    from ui.pygame_ui import badge_y

    # Comfortably inside: above, as normal.
    assert badge_y(300.0, 50.0, 20.0, 580.0) == pytest.approx(232.5)
    # Near the top: below instead.
    assert badge_y(40.0, 50.0, 20.0, 580.0) == pytest.approx(107.5)
    # Near the bottom: back above.
    assert badge_y(560.0, 50.0, 20.0, 580.0) == pytest.approx(492.5)


def test_a_cell_too_tight_for_either_side_keeps_the_badge_on_the_cell():
    """Never off-window, even on a board so cramped neither side fits."""
    from ui.pygame_ui import badge_y

    assert badge_y(50.0, 60.0, 20.0, 100.0) == pytest.approx(50.0)


# -- the control strip ---------------------------------------------------------


def test_every_board_the_strip_offers_has_an_odd_cell_count():
    """adr-011: an even board admits draws and has no tie-break.

    The 4x4 is withdrawn rather than merely absent, and a control that cycles
    onto it would put a player in a game the rules cannot finish.
    """
    for board in STRIP_BOARDS:
        cols, _, rows = board.partition("x")
        assert (int(cols) * int(rows)) % 2 == 1, f"{board} has an even cell count"


def test_the_strip_keeps_a_board_named_on_the_command_line():
    assert board_values("5x5") == STRIP_BOARDS
    assert board_values("5x1") == ("5x1", *STRIP_BOARDS)
    assert board_values("5x1")[0] == "5x1", "the board asked for is the one shown"


def test_a_control_cycles_in_both_directions_and_wraps():
    control = Control("Against", ("human", "random", "heuristic"), 2)
    assert control.value == "heuristic"
    assert control.step(1) == "human", "forwards from the last wraps to the first"
    assert control.step(-1) == "heuristic", "and backwards wraps the other way"
    assert control.step(-1) == "random"


def test_a_control_can_hold_every_seat_the_project_builds():
    """The window is local, so it offers what `ui.seats` offers — all six.

    The browser page is the one that restricts its list, and it restricts it by
    origin rather than by deleting a seat: `web/app.js` publishes human and
    heuristic and widens to the solver on a local host.
    """
    control = Control("Against", SEAT_KINDS, 0)
    seen = {control.step(1) for _ in SEAT_KINDS}
    assert seen == set(SEAT_KINDS)


class _FakeRect:
    """Just enough of ``pygame.Rect`` to hit-test without a display."""

    def __init__(self, hit: bool) -> None:
        self.hit = hit

    def collidepoint(self, _position) -> bool:
        return self.hit


def test_a_click_finds_the_control_it_landed_on():
    controls = {
        "board": Control("Board", ("3x3",), 0, _FakeRect(False)),
        "side": Control("You play", ("purple",), 0, _FakeRect(True)),
    }
    assert control_at((0, 0), controls) == "side"


def test_a_click_outside_every_control_is_not_a_control():
    controls = {"board": Control("Board", ("3x3",), 0, _FakeRect(False))}
    assert control_at((0, 0), controls) is None


def test_an_undrawn_control_is_never_hit():
    """``rect`` is filled by drawing, so before the first paint there is no
    target — and a click must not be attributed to one that is not on screen."""
    assert control_at((0, 0), {"board": Control("Board", ("3x3",), 0)}) is None


_SEAT_SMOKE = """
from ui.pygame_ui import Window
from ui.session import GameSession

# Holding purple: the person opens.
first = Window(GameSession(3, 3), "heuristic", seed=0, human="PURPLE")
assert first._human_to_move(), "purple moves first and the person holds it"
assert first.snapshot["ply"] == 0

# Holding green: the agent owns the opening, and must take it unprompted.
second = Window(GameSession(3, 3), "heuristic", seed=0, human="GREEN")
assert not second._human_to_move(), "purple moves first and an agent holds it"
second._agent_reply()
assert second.snapshot["ply"] == 1, "the agent did not open"
assert second._human_to_move(), "it should be the person's turn now"

# A move from the second seat still lands, and the reply follows.
rect, _ = second.hand_rects[0]
second._on_click(rect.center)
cell = sorted(second._playable_cells())[0]
second._on_click(tuple(int(v) for v in second.placement.centre(second.cells[cell])))
second._commit()
assert second.snapshot["ply"] == 3, f"expected ply 3, got {second.snapshot['ply']}"

# Undo gives the person their turn back from either seat.
second._undo()
assert second._human_to_move()
print("SEATS OK")
"""


def test_the_person_can_hold_either_colour():
    """Until 2026-09-21 the window assumed the person was purple.

    That meant a player could only ever experience the side of the board H1
    says is favoured, in a project whose question is whether it is favoured.
    """
    import os
    import subprocess
    import sys

    pytest.importorskip("pygame")
    environment = {**os.environ, "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}
    result = subprocess.run(
        [sys.executable, "-c", _SEAT_SMOKE],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert "SEATS OK" in result.stdout


_CONTROL_SMOKE = """
from ui import pygame_ui
from ui.pygame_ui import Window

_real_build_seat = pygame_ui.build_seat
from ui.seats import ChampionUnavailableError, SEAT_KINDS
from ui.session import GameSession

window = Window(GameSession(3, 3), "heuristic", seed=0, human="PURPLE")
window._paint()   # rectangles are filled by drawing, so draw once

rects = [c.rect for c in window.controls.values()]
assert all(r is not None for r in rects), "a chip was drawn without a target"
assert all(
    not a.colliderect(b) for i, a in enumerate(rects) for b in rects[i + 1:]
), "two chips overlap, so one click would mean two things"
assert all(r.bottom <= window.hand_rects[0][0].top for r in rects), (
    "the strip overlaps the hand"
)

# A position worth keeping.
rect, _ = window.hand_rects[0]
window._on_click(rect.center)
cell = sorted(window._playable_cells())[0]
window._on_click(tuple(int(v) for v in window.placement.centre(window.cells[cell])))
window._commit()
assert window.snapshot["ply"] == 2, window.snapshot["ply"]

# Changing the opponent keeps it, and does not steal the move.
window._on_click(window.controls["opponent"].rect.center, backwards=True)
assert window.controls["opponent"].value == "random"
assert window.snapshot["ply"] == 2, "changing the opponent restarted the game"
assert window._human_to_move(), "changing the opponent took the person's turn"

# Handing your colour over makes the new seat answer from that same position.
window._on_click(window.controls["side"].rect.center)
assert window.controls["side"].value == "green"
assert window.snapshot["ply"] == 3, "the new seat did not answer"

# Right-click cycles back.
window._on_click(window.controls["side"].rect.center, backwards=True)
assert window.controls["side"].value == "purple"

# Seats are built once and kept: the solver shares a transposition table
# across moves on purpose, and a sweep reader would reload a 1.2 GB layer every
# ply if it were rebuilt.
window.controls["side"].index = 0
first = window._seat("heuristic")
assert window._seat("heuristic") is first, "the seat was rebuilt mid-game"

# A seat that cannot be built is not the seat. The learner needs weights a
# fresh clone does not have, and that is the expected failure, not a crash.
window.controls["side"].index = 1   # you hold green, so purple is the agent
assert not window._human_to_move(), "the setup must leave the agent to move"
# Step onto a seat the cache has never held, or `_seat` answers from the cache
# and `build_seat` is never reached — which is what the first version of this
# check did, silently testing nothing.
window.controls["opponent"].index = SEAT_KINDS.index("uct")
before = window.controls["opponent"].index
def _no_champion(*args, **kwargs):
    raise ChampionUnavailableError("no trained network in data/az-runs/nowhere")
pygame_ui.build_seat = _no_champion
window._apply_control("opponent", 1)
assert window.controls["opponent"].index == before, "an unbuildable seat was kept"
assert "no trained network" in window.status, window.status

# The board is the one control that does restart, and everything follows it.
pygame_ui.build_seat = _real_build_seat
window.controls["side"].index = 0
window._on_click(window.controls["board"].rect.center)
assert window.controls["board"].value == "5x3"
assert window.snapshot["ply"] == 0, "a new board kept the old position"
assert len(window.cells) == 15, len(window.cells)
assert len(window.names) == 15, "the cell names did not follow the board"
assert len(window.snapshot["hands"]["PURPLE"]) == 8, "the 5x3 deck is reduced"
assert window._seats == {} or all(
    s is not first for s in window._seats.values()
), "a seat bound to the old board survived the new one"
window._paint()   # a wrongly-sized placement would put hexagons off screen
assert all(
    0 <= window.placement.centre(c)[0] <= 900 for c in window.cells
), "the placement did not follow the board"
print("CONTROLS OK")
"""


def test_the_game_is_reconfigured_in_the_window_not_in_a_new_process():
    """Until 2026-09-21 this window was configured once, on the command line.

    Trying a different opponent meant quitting and losing the position, which
    made the browser page — which has had selectors from the start — the
    friendlier of the two interfaces by a distance nobody intended.
    """
    import os
    import subprocess
    import sys

    pytest.importorskip("pygame")
    environment = {**os.environ, "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}
    result = subprocess.run(
        [sys.executable, "-c", _CONTROL_SMOKE],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert "CONTROLS OK" in result.stdout
