"""The FLIPHEX board in a window, in the physical game's palette.

    python -m ui.pygame_ui                                # you vs the heuristic
    python -m ui.pygame_ui --variant 3x3 --opponent solver
    python -m ui.pygame_ui --play green                   # the agent opens
    python -m ui.pygame_ui --opponent human               # hotseat

Needs the ``ui`` extra: ``pip install -e ".[ui]"``.

The arguments are a starting point, not a commitment
----------------------------------------------------
Every one of them is also a control in the window: the board, the colour you
hold and who you are playing are three chips in the panel, and clicking one
cycles it. The flags only say where the first game starts.

That is not a convenience. Until 2026-09-21 this window was configured once, on
the command line, so trying a different opponent meant quitting and losing the
position — and the browser page, which has had selectors from the start, was
the friendlier of the two by a distance nobody intended. Only the board restarts
a game here, because a different board *is* a different game. Changing who is
playing takes effect on the position in front of you, which is what makes
handing a live game from the heuristic to the exact solver possible at all.

How a move is made
------------------
Click a piece, click a cell, then **rotate with the wheel or the arrow keys**
and click again to commit. The tile sits on the cell while you rotate, with its
arrows live and the net swing shown, so the rotation is chosen by *looking* at
it rather than by reading a list. That is the one affordance a physical board
cannot give you — the tile is already down before you have decided — and it is
the whole reason this interface exists rather than only the text one.

What this file may and may not do
---------------------------------
It draws and reads input. Every legality question, every flip and every score
comes from :mod:`ui.session`, which the browser page also drives. Cell centres
come from :func:`ui.session.layout` and are only *scaled* here, never
recomputed: two renderers making the same geometry mistake independently is
worse than one making it, so neither is allowed to try.

``pygame`` is imported lazily, inside :func:`run`, so that the pure geometry
below can be imported and tested with no display and no dependency.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from math import cos, radians, sin, sqrt
from typing import Any

from fliphex.state import Colour
from fliphex.variant import Arm, Variant
from ui.seats import SEAT_KINDS, ChampionUnavailableError, build_seat, describe_seat
from ui.session import GameSession

# -- palette, matching web/style.css ------------------------------------------

PURPLE = (107, 63, 160)
PURPLE_SOFT = (139, 98, 189)
GREEN = (61, 143, 92)
GREEN_SOFT = (95, 174, 124)
WOOD = (243, 236, 226)
WOOD_DEEP = (228, 216, 199)
INK = (35, 32, 29)
INK_SOFT = (106, 98, 90)
LINE = (202, 191, 174)
EMPTY = (251, 247, 241)
DANGER = (179, 69, 58)
WHITE = (255, 255, 255)

#: Flat-top hexagon: vertices every 60 degrees from due East, so the flat edges
#: land on top and bottom. The same outline ``web/app.js`` draws.
VERTEX_ANGLES = tuple(radians(d) for d in (0, 60, 120, 180, 240, 300))


def hex_corners(cx: float, cy: float, r: float) -> list[tuple[float, float]]:
    """The six corners of a flat-top hexagon centred at ``(cx, cy)``."""
    return [(cx + r * cos(a), cy + r * sin(a)) for a in VERTEX_ANGLES]


def direction_vector(slot: int) -> tuple[float, float]:
    """Unit vector for an arrow slot, clockwise from North."""
    angle = radians(-90 + 60 * slot)
    return cos(angle), sin(angle)


@dataclass(frozen=True)
class Placement:
    """Where the board landed on screen: a radius and an origin, in pixels."""

    radius: float
    origin_x: float
    origin_y: float

    def centre(self, cell: dict[str, Any]) -> tuple[float, float]:
        """Pixel centre of one cell from :func:`ui.session.layout`."""
        return (
            self.origin_x + cell["x"] * self.radius,
            self.origin_y + cell["y"] * self.radius,
        )


def fit_board(
    cells: list[dict[str, Any]], width: int, height: int, margin: float = 28.0
) -> Placement:
    """Scale the engine's layout to fill ``width`` x ``height``, centred.

    The layout arrives in hex-radius units — that is the contract with
    :func:`ui.session.layout` — so fitting is one division, and the aspect ratio
    comes out of the board rather than being assumed. A 3x3 and a 5x5 therefore
    both fill the window without a per-board constant anywhere.
    """
    xs = [c["x"] for c in cells]
    ys = [c["y"] for c in cells]
    # Spans measured centre to centre, plus one radius of hexagon on each side.
    span_x = (max(xs) - min(xs)) + 2.0
    span_y = (max(ys) - min(ys)) + sqrt(3.0)
    radius = min(
        (width - 2 * margin) / span_x,
        (height - 2 * margin) / span_y,
    )
    board_w, board_h = span_x * radius, span_y * radius
    return Placement(
        radius=radius,
        origin_x=(width - board_w) / 2 + radius - min(xs) * radius,
        origin_y=(height - board_h) / 2 + radius * sqrt(3.0) / 2 - min(ys) * radius,
    )


def cell_at(
    point: tuple[float, float],
    cells: list[dict[str, Any]],
    placement: Placement,
) -> int | None:
    """Which cell contains ``point``, or ``None``.

    Nearest-centre within one radius rather than a polygon test. Hexagons tile
    the plane, so for a point inside the board the nearest centre *is* the
    containing cell; the radius cut is what rejects a click in the margin.
    """
    best: tuple[float, int] | None = None
    for cell in cells:
        cx, cy = placement.centre(cell)
        distance = ((point[0] - cx) ** 2 + (point[1] - cy) ** 2) ** 0.5
        if distance <= placement.radius and (best is None or distance < best[0]):
            best = (distance, cell["id"])
    return None if best is None else best[1]


def colour_of(name: str) -> tuple[int, int, int]:
    """Fill colour for a cell state, by the name the session reports."""
    return {"PURPLE": PURPLE, "GREEN": GREEN}.get(name, EMPTY)


def net_label(net: int) -> str:
    """``+2`` / ``-1`` / ``0`` — the swing a rotation would produce."""
    return f"+{net}" if net > 0 else str(net)


def describe(result: dict[str, Any], cell_name: str) -> str:
    """One line about the move just played, for the status bar."""
    flips = sum(1 for e in result["effects"] if e["kind"] == "flip")
    selfs = sum(1 for e in result["effects"] if e["kind"] == "self-flip")
    who = result["placed_as"].title()
    parts = [f"{who} played {result['archetype']} on {cell_name}"]
    if flips:
        parts.append(f"flipping {flips}")
    if selfs:
        parts.append(f"handing back {selfs}")
    if not flips and not selfs:
        parts.append("with nothing to flip")
    return ", ".join(parts) + "."


# -- drawing primitives, shared with the replay viewer -------------------------


def draw_hex(pygame, screen, centre, radius, fill, width=0) -> None:
    """One hexagon. Module level so ``ui.replay_viewer`` draws the same shape."""
    pygame.draw.polygon(screen, fill, hex_corners(centre[0], centre[1], radius), width)


def draw_arrow(pygame, screen, centre, radius, slot, colour, scale=1.0) -> None:
    """One arrow, from just outside the centre to just inside the edge."""
    dx, dy = direction_vector(slot)
    cx, cy = centre
    start = (cx + dx * radius * 0.24, cy + dy * radius * 0.24)
    end = (cx + dx * radius * 0.64, cy + dy * radius * 0.64)
    pygame.draw.line(screen, colour, start, end, max(2, int(radius * 0.075 * scale)))
    tip = (cx + dx * radius * 0.86, cy + dy * radius * 0.86)
    px, py = -dy, dx
    wing = radius * 0.15 * scale
    pygame.draw.polygon(
        screen,
        colour,
        [
            tip,
            (end[0] + px * wing, end[1] + py * wing),
            (end[0] - px * wing, end[1] - py * wing),
        ],
    )


# -- the window ----------------------------------------------------------------


BOARD_H = 576
CONTROL_H = 48
PANEL_H = 150 + CONTROL_H
WIDTH = 900
HEIGHT = BOARD_H + PANEL_H

#: Boards the strip offers. Every one has an odd cell count, per adr-011 — a
#: board with an even one admits draws and has no tie-break, which is why the
#: 4x4 is withdrawn rather than merely absent.
BOARDS = ("3x3", "5x3", "5x5")

SIDES = ("purple", "green")


def board_values(current: str) -> tuple[str, ...]:
    """The boards the strip cycles, including one named on the command line.

    ``--variant 5x1`` is legal and useful — it is what `perft` runs on — so a
    board the strip does not normally offer must not vanish from the window the
    moment somebody asks for it.
    """
    return BOARDS if current in BOARDS else (current, *BOARDS)


@dataclass
class Control:
    """One cycleable setting in the window's strip.

    ``rect`` is filled when the control is drawn, so hit-testing and drawing
    cannot disagree about where it is — the same reason the replay viewer keeps
    its scrubber rectangle in one function.
    """

    label: str
    values: tuple[str, ...]
    index: int = 0
    rect: Any = None

    @property
    def value(self) -> str:
        return self.values[self.index]

    def step(self, delta: int) -> str:
        """Move by ``delta``, wrapping. Returns the new value."""
        self.index = (self.index + delta) % len(self.values)
        return self.value


def control_at(position: tuple[int, int], controls: dict[str, Control]) -> str | None:
    """Which control a click landed on, or ``None``."""
    for key, control in controls.items():
        if control.rect is not None and control.rect.collidepoint(position):
            return key
    return None


class Window:
    """Draws one :class:`~ui.session.GameSession` and reads the mouse.

    Holds no rules and no geometry of its own — only what is on screen and what
    the player is part-way through choosing.
    """

    def __init__(
        self,
        session: GameSession,
        opponent: str,
        seed: int | None,
        human: str = "PURPLE",
    ) -> None:
        import pygame

        self.pygame = pygame
        self.session = session
        self.seed = seed
        #: The three things a game is. Every one is also a command-line flag,
        #: and every one can be changed without leaving the window.
        board = f"{session.variant.n_cols}x{session.variant.n_rows}"
        values = board_values(board)
        self.controls: dict[str, Control] = {
            "board": Control("Board", values, values.index(board)),
            "side": Control("You play", SIDES, SIDES.index(human.lower())),
            "opponent": Control("Against", SEAT_KINDS, SEAT_KINDS.index(opponent)),
        }
        self.cells = session.geometry()["cells"]
        self.names = {c["id"]: c["name"] for c in self.cells}
        self.snapshot = session.snapshot()
        self.placement = fit_board(self.cells, WIDTH, BOARD_H)

        self.selected_tile: int | None = None
        self.selected_cell: int | None = None
        self.options: list[dict[str, Any]] = []
        self.option_index = 0
        self.flash: set[int] = set()
        self.flash_until = 0
        self.status = "Click a piece, then a cell."
        self.hand_rects: list[tuple[Any, int]] = []

        #: Keyboard equivalents of the three chips, shift for backwards. Built
        #: here rather than at module level because `pygame` is imported lazily.
        self.control_keys = {
            pygame.K_b: "board",
            pygame.K_c: "side",
            pygame.K_o: "opponent",
        }

        pygame.init()
        pygame.display.set_caption("FLIPHEX")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.font = pygame.font.SysFont("dejavusans,arial", 15)
        self.small = pygame.font.SysFont("dejavusans,arial", 12)
        self.big = pygame.font.SysFont("dejavusans,arial", 26, bold=True)
        self.clock = pygame.time.Clock()

    # -- drawing ---------------------------------------------------------------

    def _hex(self, centre: tuple[float, float], r: float, fill, width: int = 0) -> None:
        draw_hex(self.pygame, self.screen, centre, r, fill, width)

    def _arrow(self, centre, r, slot, colour, scale=1.0) -> None:
        draw_arrow(self.pygame, self.screen, centre, r, slot, colour, scale)

    def _draw_board(self) -> None:
        placement = self.placement
        playable = self._playable_cells()
        for cell in self.cells:
            centre = placement.centre(cell)
            cid = cell["id"]
            state = self.snapshot["colours"][cid]
            radius = placement.radius * 0.94
            if cid in self.flash:
                # A flipped tile pulses once, so the player sees which moved.
                radius *= 0.86
            self._hex(centre, radius, colour_of(state))
            self._hex(centre, radius, LINE, 2)
            if cid in playable:
                self._hex(centre, radius * 0.97, PURPLE_SOFT, 3)
                self.pygame.draw.circle(
                    self.screen, PURPLE_SOFT, (int(centre[0]), int(centre[1])), 5
                )
            label = self.small.render(
                cell["name"], True, INK_SOFT if state == "EMPTY" else WHITE
            )
            self.screen.blit(label, label.get_rect(center=centre))

        for placed in self.session.history_for_drawing():
            centre = placement.centre(self.cells[placed["cell"]])
            for slot in placed["arrows"]:
                self._arrow(centre, placement.radius, slot, (255, 255, 255, 190))

        self._draw_preview()

    def _draw_preview(self) -> None:
        """The tile sitting on the chosen cell, at the rotation being scrolled."""
        if self.selected_cell is None or not self.options:
            return
        option = self.options[self.option_index]
        placement = self.placement
        centre = placement.centre(self.cells[self.selected_cell])
        mover = self.snapshot["to_move"]
        tile_colour = PURPLE if mover == "PURPLE" else GREEN
        self._hex(centre, placement.radius * 0.94, tile_colour)
        self._hex(centre, placement.radius * 0.94, WHITE, 3)
        for slot in option["arrows"]:
            self._arrow(centre, placement.radius, slot, WHITE, scale=1.2)

        for effect in option["effects"]:
            if effect["target"] is None:
                continue
            target = placement.centre(self.cells[effect["target"]])
            if effect["kind"] == "flip":
                self._hex(target, placement.radius * 0.82, GREEN_SOFT, 4)
            elif effect["kind"] == "self-flip":
                self._hex(target, placement.radius * 0.82, DANGER, 4)

        net = net_label(option["net"])
        swing = option["net"]
        colour = GREEN_SOFT if swing > 0 else DANGER if swing < 0 else INK_SOFT
        chip = self.big.render(net, True, colour)
        self.screen.blit(
            chip, chip.get_rect(center=(centre[0], centre[1] - placement.radius * 1.35))
        )

    def _draw_controls(self, top: int) -> None:
        """The three chips. Click cycles forward, right-click back."""
        pygame = self.pygame
        x = 20
        for control in self.controls.values():
            value = self.font.render(f"{control.value}  ›", True, INK)
            label = self.small.render(control.label.upper(), True, INK_SOFT)
            width = max(value.get_width(), label.get_width()) + 26
            rect = pygame.Rect(x, top + 5, width, CONTROL_H - 14)
            pygame.draw.rect(self.screen, WOOD, rect, border_radius=8)
            pygame.draw.rect(self.screen, LINE, rect, 1, border_radius=8)
            self.screen.blit(label, (rect.x + 13, rect.y + 4))
            self.screen.blit(value, (rect.x + 13, rect.y + 17))
            control.rect = rect
            x += width + 10

    def _draw_panel(self) -> None:
        pygame = self.pygame
        top = BOARD_H
        pygame.draw.rect(self.screen, WOOD_DEEP, (0, top, WIDTH, PANEL_H))
        pygame.draw.line(self.screen, LINE, (0, top), (WIDTH, top), 2)
        self._draw_controls(top)
        top += CONTROL_H

        score = self.snapshot["score"]
        purple, green = score["PURPLE"], score["GREEN"]
        self.screen.blit(self.big.render(str(purple), True, PURPLE), (20, top + 12))
        self.screen.blit(self.small.render("PURPLE", True, INK_SOFT), (20, top + 44))
        right = self.big.render(str(green), True, GREEN)
        self.screen.blit(right, (WIDTH - 20 - right.get_width(), top + 12))
        tag = self.small.render("GREEN", True, INK_SOFT)
        self.screen.blit(tag, (WIDTH - 20 - tag.get_width(), top + 44))

        if self.snapshot["terminal"]:
            headline = f"{self.snapshot['winner'].title()} wins"
        else:
            headline = f"{self.snapshot['to_move'].title()} to move"
        text = self.font.render(headline, True, INK)
        self.screen.blit(text, text.get_rect(center=(WIDTH // 2, top + 22)))

        status = self.font.render(self.status, True, INK_SOFT)
        self.screen.blit(status, status.get_rect(center=(WIDTH // 2, top + 46)))

        self._draw_hand(top + 70)

        keys = self.small.render(
            "wheel / arrows rotate   ·   click commits   ·   esc cancels   "
            "·   u undo   ·   n new game   ·   b board, c colour, o opponent "
            "(right-click or shift for back)",
            True,
            INK_SOFT,
        )
        self.screen.blit(keys, keys.get_rect(center=(WIDTH // 2, HEIGHT - 14)))

    def _draw_hand(self, y: int) -> None:
        self.hand_rects = []
        hand = self.snapshot["hands"][self.snapshot["to_move"]]
        if not hand or self.snapshot["terminal"]:
            return
        mover = self.snapshot["to_move"]
        size = 26
        gap = 8
        total = len(hand) * (2 * size + gap) - gap
        x = (WIDTH - total) / 2 + size
        for piece in hand:
            centre = (x, y + size)
            chosen = piece["tile"] == self.selected_tile
            self._hex(centre, size, PURPLE if mover == "PURPLE" else GREEN)
            self._hex(centre, size, WHITE if chosen else LINE, 3 if chosen else 1)
            for slot in piece["arrows"]:
                self._arrow(centre, size, slot, WHITE, scale=0.85)
            if not piece["arrows"]:
                self.pygame.draw.circle(
                    self.screen, WHITE, (int(centre[0]), int(centre[1])), 6
                )
            rect = self.pygame.Rect(x - size, y, 2 * size, 2 * size)
            self.hand_rects.append((rect, piece["tile"]))
            x += 2 * size + gap

    # -- state -----------------------------------------------------------------

    def _playable_cells(self) -> set[int]:
        if self.selected_tile is None or self.snapshot["terminal"]:
            return set()
        return set(self.session.playable_cells(self.selected_tile))

    def _seat_kind(self, colour: str) -> str | None:
        """Which agent holds ``colour``, or ``None`` when a person does.

        Read from the controls on every call rather than fixed at construction,
        so changing the opponent mid-game changes who answers the *next* move
        instead of requiring a new process.
        """
        opponent = self.controls["opponent"].value
        if opponent == "human":
            return None  # hotseat: both colours are the person's
        return None if colour == self.controls["side"].value.upper() else opponent

    def _human_to_move(self) -> bool:
        """Whether the side to move is a seat no agent holds.

        Derived from the seats rather than assumed to be purple. This window
        hardcoded the human as purple until 2026-09-21, which meant a player
        could only ever experience the side of the board H1 says is favoured —
        in a project whose whole question is whether that side is favoured.
        """
        return self._seat_kind(self.snapshot["to_move"]) is None

    def _reset_selection(self) -> None:
        self.selected_tile = None
        self.selected_cell = None
        self.options = []
        self.option_index = 0

    def _refresh(self, result: dict[str, Any] | None = None) -> None:
        self.snapshot = result["snapshot"] if result else self.session.snapshot()
        if result:
            self.flash = set(result["flipped"])
            self.flash_until = self.pygame.time.get_ticks() + 320
            self.status = describe(result, self.names[result["move"]["cell"]])
        self._reset_selection()

    # -- input -----------------------------------------------------------------

    def _on_click(self, position: tuple[int, int], backwards: bool = False) -> None:
        # Checked first: the controls have to work when the game is over and
        # when it is the agent's turn, which is exactly when you want them.
        key = control_at(position, self.controls)
        if key is not None:
            self._apply_control(key, -1 if backwards else 1)
            return
        if self.snapshot["terminal"] or not self._human_to_move():
            return
        if position[1] >= BOARD_H:
            for rect, tile in self.hand_rects:
                if rect.collidepoint(position):
                    self.selected_tile = None if tile == self.selected_tile else tile
                    self.selected_cell = None
                    self.options = []
                    self.status = (
                        "Now click a highlighted cell."
                        if self.selected_tile is not None
                        else "Click a piece, then a cell."
                    )
                    return
            return

        if self.selected_tile is None:
            self.status = "Pick a piece first."
            return

        # Second click on the chosen cell commits the rotation on screen.
        on_chosen_cell = cell_at(position, self.cells, self.placement)
        if (
            self.selected_cell is not None
            and self.options
            and on_chosen_cell == self.selected_cell
        ):
            self._commit()
            return

        cell = cell_at(position, self.cells, self.placement)
        if cell is None or cell not in self._playable_cells():
            return
        self.selected_cell = cell
        self.options = self.session.options(cell, self.selected_tile)
        self.option_index = 0
        self.status = (
            f"{len(self.options)} rotation(s) — wheel or arrows to turn, "
            f"click to place."
        )

    def _rotate(self, step: int) -> None:
        if self.options:
            self.option_index = (self.option_index + step) % len(self.options)

    def _commit(self) -> None:
        option = self.options[self.option_index]
        result = self.session.play(
            self.selected_cell, self.selected_tile, option["rotation"]
        )
        self._refresh(result)
        self._agent_reply()

    def _agent_reply(self) -> bool:
        """Let whoever holds the side to move play. ``False`` if it could not.

        The one failure that is expected rather than exceptional: the learner
        seat needs weights a fresh clone does not have. Saying so in the status
        bar and putting the control back beats a window that dies mid-game.
        """
        if self.snapshot["terminal"] or self._human_to_move():
            return True
        kind = self._seat_kind(self.snapshot["to_move"])
        self.status = (
            "The solver is searching — the window will not respond until it answers."
            if kind == "solver"
            else f"{kind.title()} is thinking…"
        )
        self._paint()  # show the human's move before the search blocks
        try:
            result = self.session.agent_move_by_name(kind, seed=self.seed)
        except ChampionUnavailableError as exc:
            self.status = str(exc).splitlines()[0]
            return False
        self._refresh(result)
        return True

    def _undo(self) -> None:
        self.session.undo()
        if self.controls["opponent"].value != "human":
            # An agent holds a seat, so one more ply belongs to it.
            self.session.undo()
        self._refresh()
        self.status = "Took it back."

    def _apply_control(self, key: str, step: int) -> None:
        """Cycle one control and act on it.

        Only the board restarts the game. The other two say who answers from
        here, and a position is worth more than a setting — swapping the
        heuristic for the exact solver in the middle of a game you are losing is
        the most informative thing this window can do.
        """
        opponent = self.controls["opponent"]
        was = opponent.index
        value = self.controls[key].step(step)

        if key == "board":
            played = self._new_game()
        else:
            self._reset_selection()
            self.snapshot = self.session.snapshot()
            if key == "side":
                self.status = f"You hold {value} now. The position stands."
            elif value == "human":
                self.status = "Hotseat — both colours are yours."
            else:
                self.status = f"Playing {value} from here. The position stands."
            played = self._agent_reply()

        if not played:
            # Whichever control was touched, the seat that could not be built is
            # not the seat any more.
            opponent.index = was

    def _new_game(self) -> bool:
        cols, _, rows = self.controls["board"].value.partition("x")
        self.session = GameSession(int(cols), int(rows), self.session.variant.arm.value)
        # All three follow the board, and until the board could change none of
        # them needed to: a 3x3 drawn with a 5x5's cell list and placement puts
        # every hexagon in the wrong place and every click on the wrong cell.
        self.cells = self.session.geometry()["cells"]
        self.names = {c["id"]: c["name"] for c in self.cells}
        self.placement = fit_board(self.cells, WIDTH, BOARD_H)
        self._refresh()
        self.status = "New game. Click a piece, then a cell."
        return self._agent_reply()

    # -- loop ------------------------------------------------------------------

    def _paint(self) -> None:
        self.screen.fill(WOOD)
        if self.flash and self.pygame.time.get_ticks() > self.flash_until:
            self.flash = set()
        self._draw_board()
        self._draw_panel()
        self.pygame.display.flip()

    def run(self) -> None:
        pygame = self.pygame
        # When the person holds the second seat, the agent owns the opening and
        # has to take it, or the window waits for a move the player cannot make.
        self._agent_reply()
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
                    self._on_click(event.pos, backwards=event.button == 3)
                elif event.type == pygame.MOUSEWHEEL:
                    self._rotate(-event.y)
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE,):
                        chosen = self.selected_cell is not None
                        if chosen or self.selected_tile is not None:
                            self._reset_selection()
                            self.status = "Click a piece, then a cell."
                        else:
                            running = False
                    elif event.key in (pygame.K_RIGHT, pygame.K_UP):
                        self._rotate(1)
                    elif event.key in (pygame.K_LEFT, pygame.K_DOWN):
                        self._rotate(-1)
                    elif (
                        event.key in (pygame.K_RETURN, pygame.K_SPACE) and self.options
                    ):
                        self._commit()
                    elif event.key == pygame.K_u:
                        self._undo()
                    elif event.key == pygame.K_n:
                        self._new_game()
                    elif event.key in self.control_keys:
                        back = bool(event.mod & pygame.KMOD_SHIFT)
                        key = self.control_keys[event.key]
                        self._apply_control(key, -1 if back else 1)
            self._paint()
            self.clock.tick(60)
        pygame.quit()


def run(
    variant: Variant,
    opponent: str = "heuristic",
    seed: int | None = None,
    human: str = "PURPLE",
) -> None:
    """Open the window and play. Blocks until it is closed."""
    session = GameSession(variant.n_cols, variant.n_rows, variant.arm.value)
    Window(session, opponent, seed, human).run()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Play FLIPHEX in a window.")
    parser.add_argument("--variant", default="5x5", help="board as COLSxROWS")
    parser.add_argument("--arm", choices=[a.value for a in Arm], default=Arm.H1.value)
    parser.add_argument(
        "--opponent",
        choices=SEAT_KINDS,
        default="heuristic",
        help="who you play against; 'human' is a hotseat game. Cycle it in the "
        "window with o, so this only names where the first game starts",
    )
    parser.add_argument(
        "--play",
        choices=["purple", "green"],
        default="purple",
        help="which colour you hold. Purple moves first and holds the joker, "
        "so --play green is how you face the advantage H1 is about",
    )
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args(argv)

    cols, _, rows = args.variant.lower().partition("x")
    try:
        variant = Variant(int(cols), int(rows), Arm(args.arm), Colour.PURPLE)
    except ValueError as exc:
        raise SystemExit(f"  ✗ {exc}") from None

    # Fail before opening a window, not after: building the learner seat can
    # raise, and a window that appears and vanishes explains nothing. Once the
    # window is up the same failure is recoverable — the control goes back —
    # because by then there is somewhere to say it.
    try:
        seat = build_seat(args.opponent, variant=variant, seed=args.seed)
    except ChampionUnavailableError as exc:
        raise SystemExit(f"  ✗ opponent seat: {exc}") from None

    human = args.play.upper()
    hotseat = args.opponent == "human"
    opening = "you open" if human == "PURPLE" or hotseat else "the agent opens"
    print(
        f"  {variant.n_cols}x{variant.n_rows}  you play {args.play} against "
        f"{describe_seat(seat)} — {opening}\n"
        f"  board, colour and opponent are all changeable in the window"
    )

    run(variant, args.opponent, args.seed, human)


if __name__ == "__main__":
    main()
