"""Transposition table for the exact solver.

The *hashing* already exists: ``fliphex.state`` maintains a 64-bit Zobrist
incrementally (`adr-004 <../docs/adr/adr-004-solver-approach.md>`_, 76 live
words on the 5×5 — 25 cells × 2 colours, 13 + 12 tiles, 1 side-to-move). What
lives here is the *table*: buckets, a replacement policy, and the two things
that decide whether a stored value may be believed.

Bounds, not values
------------------
Alpha-beta returns a **bound** whenever it fails high or low, and only an exact
value when the true score lands strictly inside the window. Storing a bound as
if it were exact is the defect class this whole axis is built to avoid: it does
not crash, it produces a plausible wrong answer. Every entry therefore carries a
:class:`Flag`, and :meth:`TranspositionTable.probe` returns a usable value only
when the stored bound settles the *current* window.

Zobrist collisions are a correctness threat here, not a nuisance
---------------------------------------------------------------
An engine playing a game can absorb a hash collision — it costs one bad move. An
*exhaustive solve* cannot: a collision writes a wrong value that then propagates,
and the result is a self-consistent wrong database. Nothing in
`adr-010 <../docs/adr/adr-010-solver-correctness.md>`_ catches that. V5
checksums the file after the fact, V4 samples entries against the same corrupted
recurrence, and V1 counts positions rather than values.

The numbers are not comfortable. A 64-bit key collides by the birthday bound at
around ``2**32 ≈ 4.3 × 10⁹`` distinct positions; the 5×3 variant has
``1.75 × 10¹⁰`` configurations — **four times past that point**. Collisions are
not a tail risk on this board, they are expected.

So ``verify=True`` (the default) stores the full :meth:`GameState.key` alongside
each entry and compares it on every hit. A collision then becomes a *detected
miss* and increments :attr:`TranspositionTable.collisions`, which is itself
evidence worth reporting with an adr-010 verification run. It costs memory, and
that is the correct trade for the proof-producing path. ``verify=False`` is for
the agent, where a rare collision costs a move rather than a theorem.

Depth
-----
FLIPHEX terminates at a fixed depth, so a position's *distance to the end* is
determined by how many cells are filled — two positions sharing a Zobrist share
a ply. What still varies is how far a given search actually looked. An entry
written by a depth-limited search must not be reused by a deeper one, so entries
carry the plies actually searched below the node.

A pleasant consequence for the exhaustive solve: every entry is written at full
remaining depth, so within a layer the depth test is trivially satisfied and the
table degenerates into a pure memo.

Provenance
----------
adr-004 R1 lets a result be cited as a proof only if the run terminated by
exhaustion, and R3 requires every artefact to record that. Prose cannot be
checked, so :attr:`TranspositionTable.truncated` latches the moment any
depth-limited entry is stored. An artefact writer reads it instead of asserting
``termination: exhausted`` on trust.
"""

from __future__ import annotations

from enum import IntEnum
from typing import NamedTuple

from fliphex.moves import Move
from fliphex.state import Colour, GameState

#: The full search key: colours, both hands, side to move. What
#: :meth:`fliphex.state.GameState.key` returns.
StateKey = tuple[tuple[Colour, ...], int, int, Colour]


class Flag(IntEnum):
    """What the stored value says about the true score."""

    #: The search window contained the true value: ``value`` is the score.
    EXACT = 0
    #: The search failed high: the true value is **at least** ``value``.
    LOWER = 1
    #: The search failed low: the true value is **at most** ``value``.
    UPPER = 2


class Entry(NamedTuple):
    """One table slot.

    Attributes:
        value: The score or bound, from the perspective of the side to move.
        flag: How to read ``value`` (:class:`Flag`).
        depth: Plies searched *below* this node when the entry was written.
        best: The move that produced ``value``, for move ordering. May be
            ``None`` for a node whose every move failed low.
        key: The full state key when the table verifies, else ``None``.
    """

    value: int
    flag: Flag
    depth: int
    best: Move | None
    key: StateKey | None


class TranspositionTable:
    """A fixed-size, direct-indexed transposition table.

    Args:
        capacity: Number of slots. Must be a power of two, so the index is a
            mask rather than a modulo.
        verify: Store and compare the full state key on every hit. Leave this
            on for any run whose result will be cited (see the module
            docstring); turn it off only for play.

    Attributes:
        collisions: Hits whose Zobrist matched but whose key did not. Zero is
            not expected on a large solve — a nonzero count is the table doing
            its job, and belongs in the run's verification record.
        truncated: Latches ``True`` once any entry is stored from a search that
            did not reach the end of the game (adr-004 R1).
    """

    def __init__(self, capacity: int = 1 << 20, verify: bool = True) -> None:
        if capacity <= 0 or capacity & (capacity - 1):
            raise ValueError(f"capacity must be a power of two, got {capacity}")
        self.capacity = capacity
        self.verify = verify
        self._mask = capacity - 1
        self._slots: list[Entry | None] = [None] * capacity

        self.hits = 0
        self.misses = 0
        self.collisions = 0
        self.stores = 0
        self.replacements = 0
        self.truncated = False

    def __len__(self) -> int:
        """Return the number of occupied slots."""
        return sum(1 for slot in self._slots if slot is not None)

    @property
    def load(self) -> float:
        """Occupied fraction, ``0.0`` to ``1.0``."""
        return len(self) / self.capacity

    def clear(self) -> None:
        """Empty the table and reset the counters.

        :attr:`truncated` is **not** reset: it records something about the run,
        not about the table's current contents, and clearing the table does not
        un-truncate a search that already happened.
        """
        self._slots = [None] * self.capacity
        self.hits = self.misses = self.collisions = 0
        self.stores = self.replacements = 0

    # -- probe / store --------------------------------------------------------

    def probe(
        self, state: GameState, depth: int, alpha: int, beta: int
    ) -> tuple[int | None, Move | None]:
        """Look the position up.

        Returns:
            ``(value, best)``. ``value`` is not ``None`` only when the stored
            entry was searched at least as deep as ``depth`` *and* its bound
            settles the ``(alpha, beta)`` window. ``best`` may be present even
            when ``value`` is ``None`` — a shallow entry is useless as a score
            but still the first move worth trying, which is what makes
            TT-move-first ordering pay.
        """
        entry = self._slots[state.zobrist & self._mask]
        if entry is None:
            self.misses += 1
            return None, None
        if self.verify and entry.key != state.key():
            self.collisions += 1
            self.misses += 1
            return None, None

        self.hits += 1
        if entry.depth < depth:
            return None, entry.best
        if entry.flag is Flag.EXACT:
            return entry.value, entry.best
        if entry.flag is Flag.LOWER and entry.value >= beta:
            return entry.value, entry.best
        if entry.flag is Flag.UPPER and entry.value <= alpha:
            return entry.value, entry.best
        return None, entry.best

    def store(
        self,
        state: GameState,
        value: int,
        flag: Flag,
        depth: int,
        best: Move | None = None,
        *,
        exhaustive: bool = True,
    ) -> None:
        """Write an entry, keeping the deeper of the two on a slot conflict.

        Args:
            state: The position.
            value: Score or bound, from the side to move's perspective.
            flag: How ``value`` is to be read.
            depth: Plies searched below this node.
            best: The move that produced ``value``.
            exhaustive: Whether this search reached the end of the game. Pass
                ``False`` from any depth- or time-capped search; it latches
                :attr:`truncated`, which is what an artefact reads instead of
                trusting a prose claim (adr-004 R1/R3).
        """
        if not exhaustive:
            self.truncated = True

        index = state.zobrist & self._mask
        current = self._slots[index]
        if current is not None:
            if current.depth > depth:
                return
            self.replacements += 1

        self._slots[index] = Entry(
            value=value,
            flag=flag,
            depth=depth,
            best=best,
            key=state.key() if self.verify else None,
        )
        self.stores += 1

    # -- reporting ------------------------------------------------------------

    def stats(self) -> dict[str, float | int | bool]:
        """Return the counters, for an experiment record or a run log."""
        probes = self.hits + self.misses
        return {
            "capacity": self.capacity,
            "occupied": len(self),
            "load": self.load,
            "probes": probes,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / probes if probes else 0.0,
            "collisions": self.collisions,
            "stores": self.stores,
            "replacements": self.replacements,
            "verify": self.verify,
            "truncated": self.truncated,
        }

    def __repr__(self) -> str:
        return (
            f"TranspositionTable(capacity={self.capacity}, verify={self.verify}, "
            f"load={self.load:.3f}, collisions={self.collisions})"
        )


class NullTable(TranspositionTable):
    """A table that remembers nothing, for measuring what the table is worth.

    ``EXP-003`` compares alpha-beta with and without transposition, and "without"
    has to mean *no memo* rather than *a table too small to help*: a one-slot
    real table would serve every probe as a detected collision, which counts as a
    miss but pollutes :attr:`collisions` — a number that exists to be reported as
    verification evidence, not as an artefact of a benchmark configuration.

    Pruning is unaffected. Only the memo goes away.
    """

    def __init__(self) -> None:
        super().__init__(capacity=1, verify=False)

    def probe(
        self, state: GameState, depth: int, alpha: int, beta: int
    ) -> tuple[int | None, Move | None]:
        """Always miss."""
        self.misses += 1
        return None, None

    def store(
        self,
        state: GameState,
        value: int,
        flag: Flag,
        depth: int,
        best: Move | None = None,
        *,
        exhaustive: bool = True,
    ) -> None:
        """Discard the entry, but still latch provenance (adr-004 R1)."""
        if not exhaustive:
            self.truncated = True

    def __repr__(self) -> str:
        return "NullTable()"
