"""Crash-resume for a training run measured in days.

Why this exists
---------------
Five seeds of the planned schedule cost ~60 hours on a laptop that sleeps,
throttles and reboots. The exact-solver axis already lost two runs to exactly
that — one of them 20.8 hours in — which is why ``solver/checkpoint.py`` exists.
This is the same guarantee for the learner. It is a separate module because the
``az`` package may not import ``solver``.

What does not carry over is the cheap part. The retrograde sweep resumes from a
single array, because layer ``t`` is computed from layer ``t + 1`` and nothing
else. A training loop has no such single-object state, and the tempting analogue
— save the weights — is **not** a resume point.

The standard a resume has to meet
---------------------------------
**Indistinguishable from an uninterrupted run, not merely a correct continuation
of one.** This is stricter than it sounds and it is not pedantry here: the
project's third hypothesis reports a per-seed win rate across five or more
independent seeds *and the variance between them*. A resume that restored the
weights but reseeded the generators would produce a run that is still valid, yet
no longer reproducible from the seed it claims — and reproducibility across seeds
is the quantity the hypothesis is built on. The same reasoning drives
``solver/checkpoint.py``, where a resumed sweep must reproduce its verification
checksum byte-for-byte rather than merely restart the arithmetic.

That is why the RNG states are first-class contents here rather than an
afterthought, and why :meth:`Checkpoint.save` refuses a state that is missing
one.

What a complete resume point holds
----------------------------------
=========================  =====================================================
piece                      why it cannot be dropped
=========================  =====================================================
challenger weights         the obvious half
optimiser state            Adam's moment estimates; dropping them restarts the
                           estimates and puts a visible transient in the loss
                           curve at every resume
champion weights           it generates the self-play data and is the gate's
                           opponent
replay buffer              positions from earlier generations that have not
                           aged out; regenerating them costs the generations
                           that made them
generation counters        which generation is next, and which one last gated
RNG states                 Python's and torch's; see above
gate progress              the running win count, so a part-finished gate is
                           not repeated from zero
=========================  =====================================================

Granularity
-----------
The longest uninterruptible unit is not a generation (~24 min) but the
**evaluator gate at ~34 min** — 400 games at ~5.1 s each. Saving once per
generation caps the worst case at the gate's length; the gate additionally
records its running win count, which is one integer and turns a 34-minute loss
into a five-second one.

Crash safety
------------
Every write goes to a temporary file in the same directory followed by
``os.replace``, which is atomic on POSIX, and the manifest is written **after**
the payloads it names. A run killed mid-write leaves either the previous complete
checkpoint or the new one — never a half-written buffer that resumes into silent
corruption. A payload on disk is not trusted until the manifest names it.
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch

from az.replay_buffer import ReplayBuffer

#: Bumped when the on-disk layout changes incompatibly. A resume that finds a
#: different version refuses rather than guessing.
FORMAT_VERSION = 1

#: Written last; a checkpoint without it is a crashed write, not a checkpoint.
MANIFEST = "manifest.json"


@dataclass
class TrainingState:
    """Everything a resumed run needs to be indistinguishable from a fresh one.

    Attributes:
        generation: The generation about to be run, 0-based.
        last_gated: The generation at which the evaluator gate last ran, or
            ``-1`` if it never has.
        challenger: ``state_dict`` of the network being trained.
        champion: ``state_dict`` of the network generating self-play.
        optimiser: ``state_dict`` of the optimiser.
        buffer: The replay buffer, which carries its own sampling RNG.
        python_rng: ``random.Random.getstate()`` for the self-play stream.
        torch_rng: ``torch.get_rng_state()`` for initialisation and dropout.
        gate_wins: Challenger wins so far in a part-finished gate.
        gate_games: Games played so far in a part-finished gate.
        meta: Free-form run metadata — seed, variant name, schedule. Recorded so
            an artefact can be traced to the run that produced it.
    """

    generation: int
    last_gated: int
    challenger: dict[str, Any]
    champion: dict[str, Any]
    optimiser: dict[str, Any]
    buffer: ReplayBuffer
    python_rng: tuple
    torch_rng: torch.Tensor
    gate_wins: int = 0
    gate_games: int = 0
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Checkpoint:
    """A directory holding the newest complete training state.

    Only one checkpoint is kept. Unlike the solver's layer ladder — where every
    completed layer must survive so the verification checksum can be replayed in
    order — a training state is self-contained: the newest one is a complete
    resume point on its own, and older ones answer no question.

    Args:
        root: Directory to write into. Created on first save.
    """

    root: Path

    PAYLOAD = "state.pt"
    BUFFER = "buffer.pkl"

    def __post_init__(self) -> None:
        self.root = Path(self.root)

    # -- reading --------------------------------------------------------------

    def manifest(self) -> dict | None:
        """Return the manifest, or ``None`` if there is no complete checkpoint."""
        path = self.root / MANIFEST
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def resume_point(self) -> int | None:
        """The generation a resumed run should start at, or ``None`` if fresh.

        Raises:
            ValueError: If the checkpoint was written by an incompatible format
                version. Guessing at a layout change is how a resume silently
                becomes a different experiment.
        """
        found = self.manifest()
        if found is None:
            return None
        if found["format_version"] != FORMAT_VERSION:
            raise ValueError(
                f"checkpoint at {self.root} is format version "
                f"{found['format_version']}, this build writes {FORMAT_VERSION}"
            )
        return found["generation"]

    def load(self) -> TrainingState:
        """Read the checkpoint back.

        Raises:
            FileNotFoundError: If no complete checkpoint exists.
        """
        if self.resume_point() is None:
            raise FileNotFoundError(f"no complete checkpoint in {self.root}")

        blob = torch.load(self.root / self.PAYLOAD, weights_only=False)
        buffer = ReplayBuffer.from_bytes((self.root / self.BUFFER).read_bytes())
        return TrainingState(buffer=buffer, **blob)

    # -- writing --------------------------------------------------------------

    def save(self, state: TrainingState) -> None:
        """Write ``state`` atomically, manifest last.

        Raises:
            ValueError: If either RNG state is missing. A checkpoint without
                them resumes into a run that cannot reproduce its own seed, and
                that failure is invisible until the seeds are compared.
        """
        if state.python_rng is None or state.torch_rng is None:
            raise ValueError(
                "both RNG states are required: a resume must be "
                "indistinguishable from an uninterrupted run, not merely a "
                "correct continuation of one"
            )

        self.root.mkdir(parents=True, exist_ok=True)

        atomic_write(self.root / self.BUFFER, state.buffer.to_bytes())

        payload = {
            "generation": state.generation,
            "last_gated": state.last_gated,
            "challenger": state.challenger,
            "champion": state.champion,
            "optimiser": state.optimiser,
            "python_rng": state.python_rng,
            "torch_rng": state.torch_rng,
            "gate_wins": state.gate_wins,
            "gate_games": state.gate_games,
            "meta": state.meta,
        }
        buffer_path = self.root / f".{self.PAYLOAD}.tmp"
        torch.save(payload, buffer_path)
        os.replace(buffer_path, self.root / self.PAYLOAD)

        # Manifest last: until it names them, the payloads above are not trusted.
        atomic_write(
            self.root / MANIFEST,
            json.dumps(
                {
                    "format_version": FORMAT_VERSION,
                    "generation": state.generation,
                    "last_gated": state.last_gated,
                    "buffer_size": len(state.buffer),
                    "gate_wins": state.gate_wins,
                    "gate_games": state.gate_games,
                    "meta": state.meta,
                },
                indent=2,
            ).encode(),
        )


def capture_rng() -> tuple[tuple, torch.Tensor]:
    """Return ``(python_rng, torch_rng)`` as the checkpoint wants them.

    **Call this at the checkpoint boundary, before assembling anything else.**
    Gathering the rest of a :class:`TrainingState` can itself draw from the
    generators — constructing a network initialises its weights from the torch
    stream — and a state captured afterwards records a point the uninterrupted
    run never passed through. The resumed run then continues correctly and
    diverges anyway, which is precisely the failure this module exists to
    prevent and the one that leaves no trace.
    """
    return random.getstate(), torch.get_rng_state()


def restore_rng(python_rng: tuple, torch_rng: torch.Tensor) -> None:
    """Put both global generators back where a checkpoint found them."""
    random.setstate(python_rng)
    torch.set_rng_state(torch_rng)


def atomic_write(path: Path, payload: bytes) -> None:
    """Write ``payload`` to ``path`` via a temporary file in the same directory.

    Same directory, because ``os.replace`` is only atomic within one filesystem.
    """
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_bytes(payload)
    os.replace(tmp, path)
