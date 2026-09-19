"""Axis 3 — how large FLIPHEX is, and where that puts it among known games.

This package imports ``fliphex`` and nothing else from the project. It never
imports ``solver`` or ``az``: the complexity of a game is a property of its
rules, and a bound that depended on how well either axis happened to search
would not be one.
"""

from complexity.state_space import (
    KNOWN,
    LayerCount,
    SpaceProfile,
    configurations,
    orientation_inflated,
    orphans,
    profile,
    self_check,
)

__all__ = [
    "KNOWN",
    "LayerCount",
    "SpaceProfile",
    "configurations",
    "orientation_inflated",
    "orphans",
    "profile",
    "self_check",
]
