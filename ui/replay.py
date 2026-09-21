"""Recorded games, and a cursor that walks one.

No tracked artefact in this repository holds a single ordered game
--------------------------------------------------------------------
That was worth checking before building a viewer for them. `results/*.json` is
tracked, but EXP-017's is summary statistics; its ``games`` field is the integer
5,000, not five thousand move lists. EXP-008's ``moves`` is a count.
EXP-014's ``history`` is training generations. The 5,000 ordered games EXP-017
played were never written down, and `data/az-runs/` and `results/*.jsonl` are
gitignored anyway.

So the roadmap's *"play back saved games from `data/`"* had nothing to play
back on a clone — the same defect the `figures/` clause was written to catch,
appearing a third time.

A game is cheaper than a file
-----------------------------
Agents take their seed at construction (the :class:`~agents.base.Agent`
contract), so a game between two of them is a **deterministic function of
variant, seats and seed**. A recording therefore does not have to store a
position per ply, or a file at all: five short fields reproduce it exactly, and
:func:`Recording.verify` re-derives the moves and refuses a recording whose
provenance does not reproduce what it claims.

That makes a saved game shareable as a line of text, replayable from a fresh
clone, and impossible to quietly corrupt — a move list that no longer replays
legally is rejected rather than drawn.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fliphex.moves import Move, legal_moves
from fliphex.state import TILES, Colour
from fliphex.variant import Arm, Variant
from ui.seats import build_seat
from ui.session import GameSession

#: Bumped when the on-disk shape changes in a way an old reader cannot handle.
FORMAT = "fliphex-recording/1"


class RecordingError(ValueError):
    """A recording that cannot be trusted to be the game it says it is."""


@dataclass(frozen=True)
class Provenance:
    """How a recording was produced, in enough detail to reproduce it.

    ``seed`` being ``None`` means the game was not seeded and cannot be
    re-derived; :meth:`Recording.verify` says so rather than pretending.
    """

    purple: str
    green: str
    seed: int | None = None
    note: str = ""

    def reproducible(self) -> bool:
        """Whether the seats and seed determine the game.

        A human seat makes a game unreproducible whatever the seed, because the
        moves came from a person rather than from a function.
        """
        return self.seed is not None and "human" not in (self.purple, self.green)

    def as_dict(self) -> dict[str, Any]:
        return {
            "purple": self.purple,
            "green": self.green,
            "seed": self.seed,
            "note": self.note,
        }


@dataclass
class Recording:
    """One complete or partial game: a variant, an ordered move list, a source."""

    variant: Variant
    moves: list[Move]
    provenance: Provenance
    #: Filled by :meth:`replay`, so a viewer can show the result without
    #: recomputing it.
    outcome: dict[str, Any] = field(default_factory=dict)

    # -- construction ----------------------------------------------------------

    @classmethod
    def from_seats(
        cls,
        variant: Variant,
        purple: str = "heuristic",
        green: str = "heuristic",
        seed: int = 0,
        note: str = "",
    ) -> Recording:
        """Play a game between two named seats and record it.

        This is the source that always works: it needs no file, no network and
        no artefact, so a fresh clone can open the viewer on its first run.
        """
        session = GameSession(variant.n_cols, variant.n_rows, variant.arm.value)
        agents = {
            Colour.PURPLE: build_seat(purple, variant=variant, seed=seed),
            # Distinct seeds: one seed on both sides replays one stream twice.
            Colour.GREEN: build_seat(
                variant=variant, kind=green, seed=None if seed is None else seed + 1
            ),
        }
        if None in agents.values():
            raise RecordingError(
                "both seats must be agents to record a game from seats; "
                "a human seat has no function to replay"
            )
        moves: list[Move] = []
        while not session.state.is_terminal():
            agent = agents[session.state.to_move]
            move = agent.select(session.board, session.state)
            session.play(move.cell, move.tile, move.rotation)
            moves.append(move)
        return cls(variant, moves, Provenance(purple, green, seed, note))

    @classmethod
    def from_dict(cls, blob: dict[str, Any]) -> Recording:
        """Rebuild from the on-disk shape, refusing anything unrecognised."""
        if blob.get("format") != FORMAT:
            raise RecordingError(
                f"unknown recording format {blob.get('format')!r}; this reader "
                f"understands {FORMAT!r}"
            )
        shape = blob["variant"]
        variant = Variant(
            shape["n_cols"],
            shape["n_rows"],
            Arm(shape.get("arm", "h1")),
            Colour.PURPLE if shape.get("first", "PURPLE") == "PURPLE" else Colour.GREEN,
        )
        source = blob.get("provenance", {})
        return cls(
            variant,
            [Move(cell, tile, rotation) for cell, tile, rotation in blob["moves"]],
            Provenance(
                source.get("purple", "unknown"),
                source.get("green", "unknown"),
                source.get("seed"),
                source.get("note", ""),
            ),
        )

    @classmethod
    def load(cls, path: Path | str) -> Recording:
        """Read a recording from disk.

        Does not validate the moves; :meth:`replay` is what does that.
        """
        return cls.from_dict(json.loads(Path(path).read_text()))

    # -- writing ---------------------------------------------------------------

    def as_dict(self) -> dict[str, Any]:
        return {
            "format": FORMAT,
            "variant": {
                "n_cols": self.variant.n_cols,
                "n_rows": self.variant.n_rows,
                "arm": self.variant.arm.value,
                "first": self.variant.first.name,
            },
            "provenance": self.provenance.as_dict(),
            "moves": [[m.cell, m.tile, m.rotation] for m in self.moves],
            "outcome": self.outcome,
        }

    def save(self, path: Path | str) -> Path:
        path = Path(path)
        path.write_text(json.dumps(self.as_dict(), indent=1) + "\n")
        return path

    # -- checking --------------------------------------------------------------

    def replay(self) -> GameSession:
        """Apply every move to a fresh session, refusing the first illegal one.

        A recording is data, and data from a file is not trusted to be a game.
        Playing it back through the engine is the only check that means
        anything: a corrupted, truncated or hand-edited move list fails here
        rather than being drawn as though it were real.
        """
        session = GameSession(
            self.variant.n_cols, self.variant.n_rows, self.variant.arm.value
        )
        for index, move in enumerate(self.moves):
            if move not in set(legal_moves(session.board, session.state)):
                raise RecordingError(
                    f"move {index + 1} of {len(self.moves)} is not legal here: "
                    f"{TILES[move.tile].archetype} at "
                    f"{session.board.cell_name(move.cell)} rotation {move.rotation}"
                )
            session.play(move.cell, move.tile, move.rotation)
        snapshot = session.snapshot()
        self.outcome = {
            "terminal": snapshot["terminal"],
            "winner": snapshot["winner"],
            "score": snapshot["score"],
            "plies": len(self.moves),
        }
        return session

    def verify(self) -> str:
        """Re-derive the game from its provenance and compare. Returns a verdict.

        A recording that names its seats and seed is claiming the game is a
        function of them. That claim is checkable, and checking it is what stops
        a move list from carrying a provenance it did not come from.
        """
        self.replay()
        if not self.provenance.reproducible():
            return (
                "moves replay legally; provenance is not reproducible "
                f"(seats {self.provenance.purple}/{self.provenance.green}, "
                f"seed {self.provenance.seed})"
            )
        again = Recording.from_seats(
            self.variant,
            self.provenance.purple,
            self.provenance.green,
            self.provenance.seed,
        )
        if again.moves != self.moves:
            raise RecordingError(
                "this recording does not reproduce from the provenance it "
                "carries: replaying those seats at that seed gives a different "
                "game"
            )
        return "moves replay legally and reproduce exactly from the provenance"


class Replay:
    """A cursor over a :class:`Recording`. Step forward, back, or jump.

    Rebuilds from ply zero on every seek rather than keeping an undo stack. A
    game is at most 25 plies and the engine applies one in microseconds, so the
    simple thing is also the fast thing, and a scrubber that can land anywhere
    needs no special case.
    """

    def __init__(self, recording: Recording) -> None:
        recording.replay()  # refuse a bad recording before anything draws it
        self.recording = recording
        self.session = GameSession(
            recording.variant.n_cols,
            recording.variant.n_rows,
            recording.variant.arm.value,
        )
        self.ply = 0
        self.last: dict[str, Any] | None = None

    @property
    def total(self) -> int:
        return len(self.recording.moves)

    @property
    def at_start(self) -> bool:
        return self.ply == 0

    @property
    def at_end(self) -> bool:
        return self.ply >= self.total

    def goto(self, ply: int) -> dict[str, Any]:
        """Seek to ``ply``, clamped into range. Returns the snapshot there."""
        target = max(0, min(ply, self.total))
        self.session = GameSession(
            self.recording.variant.n_cols,
            self.recording.variant.n_rows,
            self.recording.variant.arm.value,
        )
        self.last = None
        for move in self.recording.moves[:target]:
            self.last = self.session.play(move.cell, move.tile, move.rotation)
        self.ply = target
        return self.snapshot()

    def forward(self, steps: int = 1) -> dict[str, Any]:
        return self.goto(self.ply + steps)

    def back(self, steps: int = 1) -> dict[str, Any]:
        return self.goto(self.ply - steps)

    def snapshot(self) -> dict[str, Any]:
        return self.session.snapshot()

    def flipped(self) -> list[int]:
        """Cells the most recent step flipped, for the viewer to animate."""
        return list(self.last["flipped"]) if self.last else []

    def _targets(self, kind: str) -> list[int]:
        effects = self.last["effects"] if self.last else []
        return [e["target"] for e in effects if e["kind"] == kind]

    def gained(self) -> list[int]:
        """Cells the last move took from the opponent."""
        return self._targets("flip")

    def handed_back(self) -> list[int]:
        """Cells the last move handed to the opponent.

        A flip is a toggle (adr-007), so an arrow pointing at your own tile
        loses it. The viewer drew these the same green as a capture, which is
        the one thing about this rule a reader must not be taught wrongly.
        """
        return self._targets("self-flip")

    def caption(self) -> str:
        """One line describing where the cursor is."""
        if self.at_start:
            source = self.recording.provenance
            return (
                f"opening position — {source.purple} (purple) vs {source.green} "
                f"(green), seed {source.seed}"
            )
        result = self.last
        flips = sum(1 for e in result["effects"] if e["kind"] == "flip")
        selfs = sum(1 for e in result["effects"] if e["kind"] == "self-flip")
        cell = self.session.board.cell_name(result["move"]["cell"])
        parts = [
            f"ply {self.ply}/{self.total} — {result['placed_as'].title()} "
            f"played {result['archetype']} on {cell}"
        ]
        if flips:
            parts.append(f"flipping {flips}")
        if selfs:
            parts.append(f"handing back {selfs}")
        if not flips and not selfs:
            parts.append("with nothing to flip")
        return ", ".join(parts)
