"""Step through a recorded game, forwards and backwards.

    python -m ui.replay_viewer                          # record one and watch it
    python -m ui.replay_viewer --purple solver --variant 3x3
    python -m ui.replay_viewer --load game.json
    python -m ui.replay_viewer --save game.json --seed 7

Needs the ``ui`` extra: ``pip install -e ".[ui]"``.

Arrow keys step, Home and End jump, the scrubber seeks, space plays and pauses.

Why it does not open a file by default
--------------------------------------
The roadmap asks this to *"play back saved games from ``data/``"*, and no
tracked artefact in this repository holds a single ordered game — EXP-017's
``games`` field is the integer 5,000, not five thousand move lists, and
``data/az-runs/`` and ``results/*.jsonl`` are gitignored. A viewer that could
only read files nobody has would run on one machine, which is the defect the
``figures/`` clause exists to catch.

So the default source is a game **recorded on the spot** from two named seats
and a seed. That works on a fresh clone, on the first run, with no arguments —
and because agents take their seed at construction, the same three values
reproduce the same game anywhere. ``--load`` still reads a file when there is
one; :mod:`ui.replay` refuses any recording that does not replay legally.

What this file may and may not do
---------------------------------
It draws and reads input. The position at every ply comes from
:class:`ui.replay.Replay`, which walks the recording through
:class:`ui.session.GameSession` — the same engine the browser page and the
playing window use. Cell centres come from :func:`ui.session.layout` and are
only scaled here.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from fliphex.state import Colour
from fliphex.variant import Arm, Variant
from ui.pygame_ui import (
    DANGER,
    GREEN,
    GREEN_SOFT,
    INK,
    INK_SOFT,
    LINE,
    PURPLE,
    PURPLE_SOFT,
    WHITE,
    WOOD,
    WOOD_DEEP,
    colour_of,
    draw_arrow,
    draw_hex,
    fit_board,
)
from ui.replay import Recording, RecordingError, Replay
from ui.seats import SEAT_KINDS

WIDTH = 900
BOARD_H = 600
PANEL_H = 130
HEIGHT = BOARD_H + PANEL_H

#: Milliseconds per ply when playing. Slow enough to watch a flip land.
PLAY_INTERVAL = 700


def scrubber_rect(pygame) -> Any:
    """The seek bar. One place, so drawing and hit-testing cannot disagree."""
    return pygame.Rect(30, BOARD_H + 78, WIDTH - 60, 10)


def ply_at(x: float, total: int, rect: Any) -> int:
    """Which ply a click at ``x`` on the scrubber means."""
    if total <= 0 or rect.width <= 0:
        return 0
    fraction = (x - rect.left) / rect.width
    return max(0, min(total, round(fraction * total)))


class Viewer:
    """Draws one :class:`~ui.replay.Replay` and seeks it."""

    def __init__(self, replay: Replay) -> None:
        import pygame

        self.pygame = pygame
        self.replay = replay
        self.cells = replay.session.geometry()["cells"]
        self.placement = fit_board(self.cells, WIDTH, BOARD_H)
        self.snapshot = replay.snapshot()
        self.playing = False
        self.next_step = 0

        pygame.init()
        pygame.display.set_caption("FLIPHEX — replay")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.font = pygame.font.SysFont("dejavusans,arial", 15)
        self.small = pygame.font.SysFont("dejavusans,arial", 12)
        self.big = pygame.font.SysFont("dejavusans,arial", 24, bold=True)
        self.clock = pygame.time.Clock()

    # -- drawing ---------------------------------------------------------------

    def _draw_board(self) -> None:
        flipped = set(self.replay.flipped())
        placed = {p["cell"]: p for p in self.replay.session.history_for_drawing()}
        latest = self.replay.last["move"]["cell"] if self.replay.last else None

        for cell in self.cells:
            centre = self.placement.centre(cell)
            cid = cell["id"]
            state = self.snapshot["colours"][cid]
            radius = self.placement.radius * 0.94
            draw_hex(self.pygame, self.screen, centre, radius, colour_of(state))
            # The tile just placed gets a white rim; the tiles it flipped get a
            # coloured one. Reading a replay means seeing cause and effect.
            if cid == latest:
                draw_hex(self.pygame, self.screen, centre, radius, WHITE, 3)
            elif cid in flipped:
                draw_hex(self.pygame, self.screen, centre, radius, GREEN_SOFT, 3)
            else:
                draw_hex(self.pygame, self.screen, centre, radius, LINE, 2)

            if cid in placed:
                for slot in placed[cid]["arrows"]:
                    draw_arrow(
                        self.pygame,
                        self.screen,
                        centre,
                        self.placement.radius,
                        slot,
                        WHITE,
                    )
            label = self.small.render(
                cell["name"], True, INK_SOFT if state == "EMPTY" else WHITE
            )
            self.screen.blit(label, label.get_rect(center=centre))

    def _draw_panel(self) -> None:
        pygame = self.pygame
        top = BOARD_H
        pygame.draw.rect(self.screen, WOOD_DEEP, (0, top, WIDTH, PANEL_H))
        pygame.draw.line(self.screen, LINE, (0, top), (WIDTH, top), 2)

        score = self.snapshot["score"]
        purple = self.big.render(str(score["PURPLE"]), True, PURPLE)
        self.screen.blit(purple, (30, top + 12))
        self.screen.blit(self.small.render("PURPLE", True, INK_SOFT), (30, top + 42))
        right = self.big.render(str(score["GREEN"]), True, GREEN)
        self.screen.blit(right, (WIDTH - 30 - right.get_width(), top + 12))
        tag = self.small.render("GREEN", True, INK_SOFT)
        self.screen.blit(tag, (WIDTH - 30 - tag.get_width(), top + 42))

        headline = self.replay.caption()
        text = self.font.render(headline, True, INK)
        self.screen.blit(text, text.get_rect(center=(WIDTH // 2, top + 22)))

        if self.snapshot["terminal"]:
            won = self.font.render(
                f"{self.snapshot['winner'].title()} wins", True, PURPLE_SOFT
            )
            self.screen.blit(won, won.get_rect(center=(WIDTH // 2, top + 46)))

        self._draw_scrubber()

        keys = self.small.render(
            "← → step   ·   home / end   ·   space play   ·   esc quit",
            True,
            INK_SOFT,
        )
        self.screen.blit(keys, keys.get_rect(center=(WIDTH // 2, HEIGHT - 16)))

    def _draw_scrubber(self) -> None:
        pygame = self.pygame
        rect = scrubber_rect(pygame)
        pygame.draw.rect(self.screen, LINE, rect, border_radius=5)
        total = max(1, self.replay.total)
        done = rect.width * self.replay.ply / total
        if done > 0:
            filled = pygame.Rect(rect.left, rect.top, done, rect.height)
            pygame.draw.rect(self.screen, PURPLE_SOFT, filled, border_radius=5)
        # A tick per ply, so the scale is visible rather than implied.
        for ply in range(total + 1):
            x = rect.left + rect.width * ply / total
            pygame.draw.line(self.screen, WOOD_DEEP, (x, rect.top), (x, rect.bottom), 1)
        head = rect.left + rect.width * self.replay.ply / total
        pygame.draw.circle(
            self.screen,
            DANGER if self.playing else PURPLE,
            (int(head), rect.centery),
            8,
        )

    def _paint(self) -> None:
        self.screen.fill(WOOD)
        self._draw_board()
        self._draw_panel()
        self.pygame.display.flip()

    # -- seeking ---------------------------------------------------------------

    def goto(self, ply: int) -> None:
        self.snapshot = self.replay.goto(ply)

    def step(self, delta: int) -> None:
        self.goto(self.replay.ply + delta)
        if self.replay.at_end:
            self.playing = False

    # -- loop ------------------------------------------------------------------

    def run(self) -> None:
        pygame = self.pygame
        running = True
        while running:
            now = pygame.time.get_ticks()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    rect = scrubber_rect(pygame)
                    if rect.inflate(0, 24).collidepoint(event.pos):
                        self.playing = False
                        self.goto(ply_at(event.pos[0], self.replay.total, rect))
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_RIGHT:
                        self.playing = False
                        self.step(1)
                    elif event.key == pygame.K_LEFT:
                        self.playing = False
                        self.step(-1)
                    elif event.key == pygame.K_HOME:
                        self.playing = False
                        self.goto(0)
                    elif event.key == pygame.K_END:
                        self.playing = False
                        self.goto(self.replay.total)
                    elif event.key == pygame.K_SPACE:
                        if self.replay.at_end:
                            self.goto(0)
                        self.playing = not self.playing
                        self.next_step = now + PLAY_INTERVAL

            if self.playing and now >= self.next_step:
                self.step(1)
                self.next_step = now + PLAY_INTERVAL

            self._paint()
            self.clock.tick(60)
        pygame.quit()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Step through a recorded FLIPHEX game."
    )
    parser.add_argument("--load", type=Path, help="a recording written by --save")
    parser.add_argument("--save", type=Path, help="write the recording before viewing")
    parser.add_argument("--variant", default="5x5", help="board as COLSxROWS")
    parser.add_argument("--arm", choices=[a.value for a in Arm], default=Arm.H1.value)
    parser.add_argument("--purple", choices=SEAT_KINDS, default="heuristic")
    parser.add_argument("--green", choices=SEAT_KINDS, default="heuristic")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="re-derive a loaded recording from its provenance and stop",
    )
    args = parser.parse_args(argv)

    try:
        if args.load:
            recording = Recording.load(args.load)
        else:
            cols, _, rows = args.variant.lower().partition("x")
            variant = Variant(int(cols), int(rows), Arm(args.arm), Colour.PURPLE)
            recording = Recording.from_seats(
                variant, args.purple, args.green, args.seed
            )
        if args.verify:
            print(f"  {recording.verify()}")
            return
        recording.replay()
    except (RecordingError, ValueError) as exc:
        raise SystemExit(f"  ✗ {exc}") from None

    if args.save:
        print(f"  wrote {recording.save(args.save)}")

    source = recording.provenance
    print(
        f"  {recording.variant.n_cols}x{recording.variant.n_rows}-"
        f"{recording.variant.arm.value}  {source.purple} vs {source.green}, "
        f"seed {source.seed}  —  {recording.outcome['plies']} plies, "
        f"{recording.outcome['winner']} wins"
    )
    Viewer(Replay(recording)).run()


if __name__ == "__main__":
    main()
