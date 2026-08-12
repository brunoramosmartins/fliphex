"""Crash-resume for sweeps measured in days.

Why this exists
---------------
The 5×3 arms run for ~50 hours on a laptop that sleeps, throttles, and reboots.
Two runs were lost to that before this module: the h1 arm survived by luck, and
the h2 arm died inside ``t = 7`` after 20.8 hours with every completed layer
already computed and nowhere to put it. A retrograde sweep resolves high ``t``
first, so a stall leaves the *root* untouched — the registry's own rule is that
such a run carries **zero** information about the value. Losing it is total.

What makes resume cheap here is the shape of the sweep: layer ``t`` is computed
from layer ``t + 1`` and nothing else. One array on disk is a complete resume
point. The whole 5×3 ladder is 4.4 GB against 915 GB free, so every layer is
kept rather than only the newest — see :meth:`Checkpoint.replay` for the second
reason that matters.

What it deliberately does not change
------------------------------------
adr-010 **V5** is a single running SHA-256 fed one layer at a time, in sweep
order. ``hashlib`` objects cannot be serialised, and the tempting fix — store a
digest per layer and combine them at the end — would silently redefine what V5
*is* between the h1 and h2 arms. Instead the completed layers stay on disk and
:meth:`replay` re-feeds them in the original order on resume, so the checksum a
resumed run reports is **byte-identical** to the one an uninterrupted run would
have reported. The change is I/O only: no sampling, no RNG draw, no arithmetic.

Crash safety
------------
Every write is to a temporary file in the same directory followed by
``os.replace``, which is atomic on POSIX. A run killed mid-write leaves either
the previous complete state or the new complete state, never a half-written
layer that would resume into silent corruption. The manifest is written *after*
the layer it refers to, so a layer file is never trusted until the manifest
names it.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Checkpoint:
    """A directory holding completed layers and the observer's state.

    Attributes:
        root: Directory to write into. Created on first save.
        keep_all: Retain every completed layer. Required for :meth:`replay`,
            and therefore for V5 to survive a resume. Setting it ``False``
            keeps only the newest layer, which is enough to restart the
            arithmetic but **not** enough to reproduce the checksum.
    """

    root: Path
    keep_all: bool = True
    #: Layers named by the manifest, newest (lowest ``t``) last.
    _complete: list[int] = field(default_factory=list)

    MANIFEST = "manifest.json"

    def layer_path(self, t: int) -> Path:
        return self.root / f"layer-{t:02d}.bin"

    # -- reading ----------------------------------------------------------

    def load_manifest(self) -> dict | None:
        """Return the manifest, or ``None`` if there is nothing to resume."""
        path = self.root / self.MANIFEST
        if not path.exists():
            return None
        manifest = json.loads(path.read_text())
        self._complete = list(manifest["complete_layers"])
        return manifest

    def resume_point(self) -> int | None:
        """The lowest ``t`` whose layer is complete on disk, or ``None``.

        That layer is the input to the next one, so the sweep restarts at
        ``resume_point() - 1``.
        """
        manifest = self.load_manifest()
        if manifest is None or not manifest["complete_layers"]:
            return None
        return min(manifest["complete_layers"])

    def load_layer(self, t: int) -> bytearray:
        path = self.layer_path(t)
        if not path.exists():
            raise FileNotFoundError(
                f"layer {t} is named by the manifest but {path} is missing; "
                f"the checkpoint is inconsistent and must not be resumed"
            )
        return bytearray(path.read_bytes())

    def replay(self):
        """Yield ``(t, values)`` for completed layers **in sweep order**.

        This is what lets a resumed run reproduce V5 exactly: the observer
        re-feeds its digest from here before the sweep continues. Sweep order
        is descending ``t``, which is the order the digest was originally fed.
        """
        for t in sorted(self._complete, reverse=True):
            yield t, self.load_layer(t)

    # -- writing ----------------------------------------------------------

    def save(self, t: int, values: bytearray, state: dict) -> None:
        """Persist a completed layer and the state that goes with it.

        Order matters: the layer lands first, the manifest second. A crash
        between the two loses the layer, which is correct — an unnamed layer is
        simply not resumed from.
        """
        self.root.mkdir(parents=True, exist_ok=True)
        self._atomic_write(self.layer_path(t), bytes(values))

        if not self.keep_all:
            for old in list(self._complete):
                if old != t:
                    self.layer_path(old).unlink(missing_ok=True)
            self._complete = []

        if t not in self._complete:
            self._complete.append(t)

        self._atomic_write(
            self.root / self.MANIFEST,
            json.dumps(
                {"complete_layers": sorted(self._complete), "state": state},
                indent=1,
            ).encode(),
        )

    def load_state(self) -> dict:
        manifest = self.load_manifest()
        return {} if manifest is None else manifest["state"]

    @staticmethod
    def _atomic_write(path: Path, payload: bytes) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
