"""The FIFO of training samples, and what one sample has to carry.

A sample is a position, the search policy at that position, and the eventual
outcome. What makes this cheap on FLIPHEX is the shape of the game: a game is at
most 25 plies, so a generation of 200 games contributes at most 5,000 samples and
the arithmetic below has no long tail in it.

The value target is exact
-------------------------
``z`` is always exactly ``+1`` or ``-1`` — draws are impossible on an odd cell
count. There is no draw mass to smear the value head toward zero, which is a real
advantage over the games this architecture is borrowed from.

The sign convention is the thing to get wrong. ``z`` is stored **from the
perspective of the player to move at that position**, matching both the encoding
(own/opponent planes) and the value head. A sample from a lost game where the
mover eventually won carries ``+1``. :func:`samples_from_game` is the only place
the alternation is written, so it is the only place it can be written wrongly.

The policy target is sparse, and packed
---------------------------------------
``pi`` is stored only for moves that received a visit, and it stores the moves
themselves rather than a dense vector aligned to ``legal_moves`` order. That
order is deterministic today but nothing enforces it, and a reordering would
silently misalign every stored target — a bug that surfaces as a training curve
that never quite converges rather than as an error.

It is stored **packed**, as two byte strings rather than a tuple of ``Move``
objects, and that is not premature optimisation. Measured on the 5x5 at 400
simulations:

===  ==========  =========  ============  ==========  ======
ply  children    visited    as objects    packed      ratio
===  ==========  =========  ============  ==========  ======
0    325         16          3,643 B       1,049 B    3.5x
6    280         3           1,415 B         958 B    1.5x
12   149         149        24,139 B       1,980 B    12.2x
===  ==========  =========  ============  ==========  ======

A move is three integers that each fit in a byte — cell, tile, rotation — and a
probability is a float32. As Python objects the same information costs up to an
order of magnitude more, and it costs most in exactly the case that dominates
the buffer: late positions, where the simulation budget spreads over every child
and the support is widest.

The buffer is the largest resident structure in the run. At the worst measured
sample, 100,000 samples is **198 MB** packed against **2.4 GB** as objects, on a
machine with 15 GB. The checkpoint is written once per generation across sixty
hours, so the same factor applies to every write.

:attr:`Sample.policy` unpacks on demand, so callers still see ``(Move, float)``
pairs.

Positions are stored encoded
----------------------------
A sample holds the ``az.encoding`` byte buffer, not a ``GameState``. That is both
smaller — 750 bytes on the 5x5, against a tuple of 25 enum references plus the
object overhead — and it removes re-encoding from the training loop.
"""

from __future__ import annotations

import pickle
import random
from array import array
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass

from fliphex.moves import Move
from fliphex.state import Colour

#: Pickle protocol pinned so a checkpoint written by one run reads back in
#: another. The buffer holds only bytes, tuples, ints and floats, so nothing
#: here depends on a class definition that might move.
PICKLE_PROTOCOL = 5


@dataclass(frozen=True, slots=True)
class Sample:
    """One training example.

    Attributes:
        planes: The position, already encoded by :func:`az.encoding.encode`.
        moves: Packed ``pi`` support — three bytes per move, ``(cell, tile,
            rotation)``.
        probs: Packed ``pi`` weights — one float32 per move, aligned to
            ``moves``.
        value: ``z`` in ``{-1.0, +1.0}``, from the point of view of the player
            to move in ``planes``.
    """

    planes: bytes
    moves: bytes
    probs: bytes
    value: float

    @property
    def policy(self) -> tuple[tuple[Move, float], ...]:
        """Unpack ``pi`` into ``(move, probability)`` pairs."""
        weights = array("f")
        weights.frombytes(self.probs)
        return tuple(
            (Move(self.moves[i * 3], self.moves[i * 3 + 1], self.moves[i * 3 + 2]), p)
            for i, p in enumerate(weights)
        )


def pack_policy(pi: dict[Move, float]) -> tuple[bytes, bytes]:
    """Pack a search policy into ``(moves, probs)``, dropping unvisited moves.

    Args:
        pi: The search policy. Entries at probability zero carry no training
            signal and are dropped.

    Returns:
        Three bytes per surviving move and one float32 per surviving move.

    Raises:
        ValueError: If any component of a move does not fit in a byte. Cells,
            tiles and rotations are all far below 256 on every variant, so this
            firing means a move was built wrongly rather than that the format
            is too small.
    """
    support = sorted((m, p) for m, p in pi.items() if p > 0.0)
    moves = bytearray()
    for move, _ in support:
        if not all(0 <= v < 256 for v in move):
            raise ValueError(f"move does not fit the packed format: {move}")
        moves += bytes(move)
    return bytes(moves), array("f", [p for _, p in support]).tobytes()


def samples_from_game(
    positions: Sequence[tuple[bytes, dict[Move, float], Colour]],
    winner: Colour,
) -> list[Sample]:
    """Label a finished game's positions with its outcome.

    Args:
        positions: One ``(planes, pi, mover)`` per ply, in play order.
        winner: The colour that won. Never ``Colour.EMPTY`` — a draw is
            impossible on an odd cell count, so one is a bug upstream, not a
            case to handle.

    Returns:
        One :class:`Sample` per position, with ``z`` read from each position's
        own mover.

    Raises:
        ValueError: If ``winner`` is not one of the two playing colours.
    """
    if winner == Colour.EMPTY:
        raise ValueError(
            "a game cannot be drawn: the board has an odd cell count, so a "
            "draw here means the outcome was computed wrongly upstream"
        )

    samples = []
    for planes, pi, mover in positions:
        moves, probs = pack_policy(pi)
        samples.append(
            Sample(
                planes=planes,
                moves=moves,
                probs=probs,
                value=1.0 if mover == winner else -1.0,
            )
        )
    return samples


class ReplayBuffer:
    """A fixed-capacity FIFO of :class:`Sample`, sampled uniformly.

    Backed by a **ring buffer** rather than a ``deque``. A deque is the obvious
    FIFO, but sampling indexes into it at random, and deque indexing is O(n) in
    the middle — on a buffer holding 100,000 samples that turns every batch into
    a scan. A list with a write cursor makes eviction and random access both
    O(1), which is what this structure is actually asked to do.

    Args:
        capacity: Maximum samples retained. Older samples are overwritten first.
        seed: Seeds the sampling RNG. Saved and restored by the checkpoint, so
            that a resumed run draws the same batches an uninterrupted one
            would have drawn.

    Raises:
        ValueError: If ``capacity`` is not positive.
    """

    def __init__(self, capacity: int, *, seed: int = 0) -> None:
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        self.capacity = capacity
        self._items: list[Sample] = []
        #: Write cursor. Meaningful only once the buffer is full.
        self._next = 0
        self._rng = random.Random(seed)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Sample]:
        """Iterate oldest to newest, so the FIFO order is inspectable."""
        if len(self._items) < self.capacity:
            return iter(self._items)
        return iter(self._items[self._next :] + self._items[: self._next])

    def extend(self, samples: Iterable[Sample]) -> None:
        """Add samples, overwriting the oldest once the capacity is reached."""
        for sample in samples:
            if len(self._items) < self.capacity:
                self._items.append(sample)
            else:
                self._items[self._next] = sample
                self._next = (self._next + 1) % self.capacity

    def sample(self, batch_size: int) -> list[Sample]:
        """Draw ``batch_size`` samples uniformly, **with** replacement.

        With replacement rather than without, so that a batch is well defined
        even while the buffer is still filling during the first generations.

        Raises:
            ValueError: If the buffer is empty.
        """
        if not self._items:
            raise ValueError("cannot sample from an empty buffer")
        items = self._items
        randrange = self._rng.randrange
        n = len(items)
        return [items[randrange(n)] for _ in range(batch_size)]

    def refresh_fraction(self, incoming: int) -> float:
        """Fraction of the buffer that ``incoming`` new samples would replace.

        The closed form is ``min(1, incoming / capacity)``: a generation of
        ``g`` samples into a buffer of ``c`` refreshes ``g / c`` of it, and
        saturates once a single generation can fill the buffer outright. The
        expected age of a sample is then ``c / g`` generations, which is the
        number the buffer size should actually be chosen against — a buffer
        much larger than the run keeps positions from a network that no longer
        exists.
        """
        return min(1.0, incoming / self.capacity)

    # -- persistence ----------------------------------------------------------

    def to_bytes(self) -> bytes:
        """Serialise the samples **and** the sampling RNG state.

        The RNG state is part of the buffer's state, not an extra. A resume that
        restored the samples but reseeded the sampler would draw different
        batches from the same data, which is enough to make a run that claims a
        seed irreproducible from it.
        """
        return pickle.dumps(
            {
                "capacity": self.capacity,
                "items": self._items,
                "next": self._next,
                "rng": self._rng.getstate(),
            },
            protocol=PICKLE_PROTOCOL,
        )

    @classmethod
    def from_bytes(cls, payload: bytes) -> ReplayBuffer:
        """Rebuild a buffer written by :meth:`to_bytes`.

        The write cursor is restored along with the samples. Dropping it would
        leave the buffer holding the right data but evicting in the wrong order,
        which no test of length or contents would catch.
        """
        blob = pickle.loads(payload)
        buffer = cls(blob["capacity"])
        buffer._items = list(blob["items"])
        buffer._next = blob["next"]
        buffer._rng.setstate(blob["rng"])
        return buffer
