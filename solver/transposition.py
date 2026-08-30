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

Why the slots are five arrays and not a list of objects
------------------------------------------------------
A ``list[Entry | None]`` of namedtuples, each holding a ``StateKey`` that holds
a colours tuple, measured **331 bytes per filled entry** — so a 2²⁶-slot table
needs 21.2 GiB. That is larger than the machine this project runs on, and it
failed in the worst possible way: the table fills lazily, so an impossible
configuration does not fail at startup, it runs for hours and then dies to the
OOM killer with no checkpoint. Two 5×3 audit runs were lost that way on
2026-08-23, one of them 4.8 h of CPU.

The entry is now five parallel ``array`` buffers of fixed-width machine
integers: **28 bytes** with verification, 12 without — the same 2²⁶ table in
1.8 GiB. This is the trick ``solver.packed_sweep`` already uses on the layer
files, and its finding carries over: under PyPy the shift-and-mask is free
(0.97× a byte read), because the JIT folds it into native instructions.

Verification is **not** weakened to buy this. The whole ``StateKey`` is a
bounded bit-field — ``n_cells × 2`` bits of colour, two 13-bit hands, one bit
of side to move: 55 bits on the 5×3 and 77 on the 5×5 — so it packs losslessly
into two 63-bit words and compares exactly, as before. Packing and comparing a
key costs 87 ns against 68 ns for the old tuple compare (measured, PyPy 3.11).
That 1.3× on the probe path buys a table an order of magnitude larger, which is
the trade the hit rate cares about.
"""

from __future__ import annotations

from array import array
from collections.abc import Iterator
from enum import IntEnum
from typing import NamedTuple

from fliphex.moves import Move
from fliphex.piece import DECK
from fliphex.state import Colour, GameState

#: The full search key: colours, both hands, side to move. What
#: :meth:`fliphex.state.GameState.key` returns.
StateKey = tuple[tuple[Colour, ...], int, int, Colour]

#: Bits per hand bitmask: one per archetype plus the joker.
_HAND_BITS = len(DECK) + 1
_HAND_MASK = (1 << _HAND_BITS) - 1

#: The packed key is split across two signed 64-bit words at this boundary.
_WORD_BITS = 63
_WORD_MASK = (1 << _WORD_BITS) - 1

#: ``_meta`` layout: bit 0 marks the slot occupied, bits 1-2 hold the
#: :class:`Flag`, and the rest holds the depth. Zero therefore means *empty*,
#: which is what makes a freshly zeroed buffer a valid empty table.
_OCCUPIED = 1
_FLAG_SHIFT = 1
_DEPTH_SHIFT = 3


class Flag(IntEnum):
    """What the stored value says about the true score."""

    #: The search window contained the true value: ``value`` is the score.
    EXACT = 0
    #: The search failed high: the true value is **at least** ``value``.
    LOWER = 1
    #: The search failed low: the true value is **at most** ``value``.
    UPPER = 2


class Entry(NamedTuple):
    """One table slot, as a **view**.

    The table does not store these — it stores parallel arrays of machine
    integers (see the module docstring). :meth:`TranspositionTable.entries`
    rebuilds an ``Entry`` per occupied slot for the consumers that read the
    table as evidence, which is adr-010 V3's whole method.

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


def pack_key(state: GameState) -> tuple[int, int]:
    """Pack the search key into two 63-bit words, losslessly.

    Layout, most significant first: ``n_cells`` two-bit colours, the first
    hand, the second hand, one bit of side to move. The width is bounded by
    the variant, so this is a bijection onto the integers it produces — a
    packed comparison is exactly as strong as comparing ``state.key()``.
    """
    v = 0
    for colour in state.colours:
        v = (v << 2) | colour
    v = (v << _HAND_BITS) | state.hands[0]
    v = (v << _HAND_BITS) | state.hands[1]
    v = (v << 1) | (state.to_move - 1)
    return v & _WORD_MASK, v >> _WORD_BITS


def unpack_key(lo: int, hi: int, n_cells: int) -> StateKey:
    """Invert :func:`pack_key`. ``n_cells`` is not recoverable from the bits."""
    v = (hi << _WORD_BITS) | lo
    to_move = Colour((v & 1) + 1)
    v >>= 1
    second = v & _HAND_MASK
    v >>= _HAND_BITS
    first = v & _HAND_MASK
    v >>= _HAND_BITS
    colours = []
    for _ in range(n_cells):
        colours.append(Colour(v & 3))
        v >>= 2
    colours.reverse()
    return (tuple(colours), first, second, to_move)


def _pack_move(move: Move | None) -> int:
    """``-1`` for ``None``; otherwise cell, tile and rotation in 12 bits."""
    if move is None:
        return -1
    return move.cell | (move.tile << 5) | (move.rotation << 9)


def _unpack_move(packed: int) -> Move | None:
    if packed < 0:
        return None
    return Move(packed & 31, (packed >> 5) & 15, packed >> 9)


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

    #: Bytes of buffer per slot, verified and unverified. Callers sizing a
    #: table against real memory need this to be arithmetic rather than folklore
    #: — see :func:`max_capacity_for`.
    BYTES_PER_SLOT = 28
    BYTES_PER_SLOT_UNVERIFIED = 12

    def __init__(self, capacity: int = 1 << 20, verify: bool = True) -> None:
        if capacity <= 0 or capacity & (capacity - 1):
            raise ValueError(f"capacity must be a power of two, got {capacity}")
        self.capacity = capacity
        self.verify = verify
        self._mask = capacity - 1
        self._allocate()

        self.hits = 0
        self.misses = 0
        self.collisions = 0
        self.stores = 0
        self.replacements = 0
        self.truncated = False

    def _allocate(self) -> None:
        """(Re)allocate the slot buffers, zeroed.

        ``array * n`` allocates the whole buffer once, which matters at the
        sizes this table is used at: building it by repeated append would spend
        the run's first minutes resizing.
        """
        n = self.capacity
        self._meta = array("i", [0]) * n
        self._value = array("i", [0]) * n
        self._best = array("i", [-1]) * n
        if self.verify:
            self._key_lo = array("q", [0]) * n
            self._key_hi = array("q", [0]) * n
        else:
            self._key_lo = self._key_hi = None
        self._occupied = 0
        #: Learned from the first stored state; needed only to decode keys back
        #: out in :meth:`entries`, since the width is not in the bits.
        self._n_cells = 0

    def __len__(self) -> int:
        """Return the number of occupied slots.

        Counted incrementally rather than by scanning: at 2²⁶ slots a scan per
        ``stats()`` call is seconds of pure bookkeeping.
        """
        return self._occupied

    @property
    def load(self) -> float:
        """Occupied fraction, ``0.0`` to ``1.0``."""
        return self._occupied / self.capacity

    def clear(self) -> None:
        """Empty the table and reset the counters.

        :attr:`truncated` is **not** reset: it records something about the run,
        not about the table's current contents, and clearing the table does not
        un-truncate a search that already happened.
        """
        self._allocate()
        self.hits = self.misses = self.collisions = 0
        self.stores = self.replacements = 0

    def entries(self) -> Iterator[Entry]:
        """Yield one :class:`Entry` per occupied slot.

        This is how adr-010 V3 reads the table as evidence. Keys come back
        decoded, so a consumer sees exactly what the old object-per-slot table
        handed it.
        """
        for i in range(self.capacity):
            meta = self._meta[i]
            if not meta:
                continue
            key = None
            if self.verify:
                key = unpack_key(self._key_lo[i], self._key_hi[i], self._n_cells)
            yield Entry(
                value=self._value[i],
                flag=Flag((meta >> _FLAG_SHIFT) & 3),
                depth=meta >> _DEPTH_SHIFT,
                best=_unpack_move(self._best[i]),
                key=key,
            )

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
        index = state.zobrist & self._mask
        meta = self._meta[index]
        if not meta:
            self.misses += 1
            return None, None
        if self.verify:
            lo, hi = pack_key(state)
            if self._key_lo[index] != lo or self._key_hi[index] != hi:
                self.collisions += 1
                self.misses += 1
                return None, None

        self.hits += 1
        best = _unpack_move(self._best[index])
        if (meta >> _DEPTH_SHIFT) < depth:
            return None, best
        flag = (meta >> _FLAG_SHIFT) & 3
        value = self._value[index]
        if flag == Flag.EXACT:
            return value, best
        if flag == Flag.LOWER and value >= beta:
            return value, best
        if flag == Flag.UPPER and value <= alpha:
            return value, best
        return None, best

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
        meta = self._meta[index]
        if meta:
            if (meta >> _DEPTH_SHIFT) > depth:
                return
            self.replacements += 1
        else:
            self._occupied += 1
        if not self._n_cells:
            self._n_cells = len(state.colours)

        self._meta[index] = (
            _OCCUPIED | (int(flag) << _FLAG_SHIFT) | (depth << _DEPTH_SHIFT)
        )
        self._value[index] = value
        self._best[index] = _pack_move(best)
        if self.verify:
            self._key_lo[index], self._key_hi[index] = pack_key(state)
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


def max_capacity_for(budget_bytes: int, verify: bool = True) -> int:
    """Largest power-of-two capacity whose buffers fit in ``budget_bytes``.

    Exists so a caller can refuse an impossible table **at startup**. The
    buffers fill lazily, so an oversized table does not fail when it is built —
    it fails hours later under the OOM killer, having written no checkpoint.
    Both 5×3 audit runs lost on 2026-08-23 died that way.
    """
    per = (
        TranspositionTable.BYTES_PER_SLOT
        if verify
        else TranspositionTable.BYTES_PER_SLOT_UNVERIFIED
    )
    slots = budget_bytes // per
    return 1 << (slots.bit_length() - 1) if slots >= 1 else 0


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
