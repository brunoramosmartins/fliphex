"""Read-only access to a completed sweep's layer files.

Extracted from ``scripts/exp002_pv_audit.py`` once a second instrument needed
it. Two consumers now read the same layers for different purposes — the PV
audit re-derives positions by forward search, and the recurrence check verifies
the layers against each other — and a shared reader keeps them agreeing about
what a layer *is*.

Memory is the whole design constraint. Holding all sixteen layers of the 5×3
costs 4.1 GB, and the PV audit's first attempt did exactly that: 12.9 GB
resident on a 15 GB machine with a transposition table on top, paging before it
finished 7 of 540 positions. Layers are therefore loaded on demand and evicted,
and :meth:`SweepReader.release` exists because *evicting is not enough when the
access pattern changes* — see its docstring for the run that proved it.
"""

from __future__ import annotations

from fliphex.moves import Move, apply_move, legal_moves
from fliphex.state import Colour, GameState
from fliphex.variant import Variant
from solver.checkpoint import Checkpoint
from solver.minimax import LOSS, WIN
from solver.packed_sweep import PackedSweep
from solver.retrograde import SLOT_LOSS, SLOT_WIN, LayerIndex


class SweepReader:
    """Read-only view of a sweep's layers, as written by ``solver.checkpoint``.

    A small cache suffices because every consumer walks ``t`` monotonically: the
    PV walk needs layer ``t`` and ``t + 1`` together, the audit's part 1 needs
    one at a time, and its part 2 only ever touches layer 1 (240 configurations
    on the 5×3).
    """

    #: Enough for the PV walk's ``t``/``t+1`` pair, with one spare.
    MAX_RESIDENT = 3

    def __init__(self, variant: Variant, checkpoint: Checkpoint) -> None:
        self.variant = variant
        self.checkpoint = checkpoint
        self.sweep = PackedSweep(variant, variant.board(), 2)
        manifest = checkpoint.load_manifest()
        if manifest is None:
            raise SystemExit(
                f"no checkpoint at {checkpoint.root} — this instrument reads "
                f"the sweep's own layers, so the arm must have been run with "
                f"--checkpoint. h1 predates crash resume and must be re-run."
            )
        missing = set(range(variant.n_cells + 1)) - set(manifest["complete_layers"])
        if missing:
            raise SystemExit(
                f"checkpoint at {checkpoint.root} is incomplete: layers "
                f"{sorted(missing)} are absent. A partial database cannot be "
                f"audited — the sweep must have finished."
            )
        self._resident: dict[int, bytearray] = {}
        self._order: list[int] = []
        self.index = {t: LayerIndex(variant, t) for t in range(variant.n_cells + 1)}

    def layer(self, t: int) -> bytearray:
        cached = self._resident.get(t)
        if cached is not None:
            self._order.remove(t)
            self._order.append(t)
            return cached
        values = self.checkpoint.load_layer(t)
        self._resident[t] = values
        self._order.append(t)
        while len(self._order) > self.MAX_RESIDENT:
            del self._resident[self._order.pop(0)]
        return values

    def release(self) -> None:
        """Drop every cached layer.

        Eviction keeps the cache *bounded*; it does not make it *small*. Walking
        the principal variation touches all sixteen layers and leaves the most
        recent three resident — **5.87 GiB** on the 5×3, measured — and the PV
        audit's part 2, which reads only layer 1, then started 1.4 GiB over its
        memory ceiling and aborted 97 seconds in. Freeing genuinely returns the
        memory to the OS here: the same measurement shows 5.87 GiB fall to
        0.12 GiB.

        Call this at any point where the access pattern changes.
        """
        self._resident.clear()
        self._order.clear()

    def ply_of(self, state: GameState) -> int:
        """The layer a state belongs to: how many cells it has filled."""
        return sum(1 for c in state.colours if c != Colour.EMPTY)

    def slot(self, state: GameState) -> int:
        """The database's verdict for ``state``, relative to the side to move."""
        t = self.ply_of(state)
        return self.sweep.get(self.layer(t), self.index[t].encode(state))

    def value(self, state: GameState) -> int:
        slot = self.slot(state)
        if slot == SLOT_WIN:
            return WIN
        if slot == SLOT_LOSS:
            return LOSS
        raise AssertionError(
            f"database holds no value for a reachable position: {slot}"
        )

    def principal_variation(self, board, state: GameState) -> list[Move]:
        """Walk the database's own optimal line from ``state`` to a terminal.

        At a winning node the mover must have a child the database calls a loss
        for the opponent; if none exists the database contradicts itself, and
        that is a finding rather than an exception to swallow.
        """
        line: list[Move] = []
        current = state
        while not current.is_terminal():
            want = SLOT_LOSS if self.slot(current) == SLOT_WIN else None
            chosen = None
            for move in legal_moves(board, current):
                child = apply_move(board, current, move)
                slot = self.slot(child)
                if want is None or slot == want:
                    chosen = (move, child)
                    if want is not None:
                        break
            if chosen is None:
                raise AssertionError(
                    f"database calls a position a win but no child is a loss "
                    f"— it is internally inconsistent at ply {len(line)}"
                )
            move, current = chosen
            line.append(move)
        return line
