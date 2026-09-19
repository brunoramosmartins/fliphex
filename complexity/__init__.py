"""Axis 3 — how large FLIPHEX is, and where that puts it among known games.

This package imports ``fliphex`` and nothing else from the project. It never
imports ``solver`` or ``az``: the complexity of a game is a property of its
rules, and a bound that depended on how well either axis happened to search
would not be one.
"""

from complexity.game_tree import (
    ORBITS,
    RolloutEstimate,
    effective_branching,
    elementary_symmetric,
    games,
    minimal_tree,
    prefixes,
    rollout_estimate,
)
from complexity.state_space import (
    LayerCount,
    SpaceProfile,
    configurations,
    orientation_inflated,
    orphans,
    profile,
)

__all__ = [
    "ORBITS",
    "LayerCount",
    "RolloutEstimate",
    "SpaceProfile",
    "configurations",
    "effective_branching",
    "elementary_symmetric",
    "games",
    "minimal_tree",
    "orientation_inflated",
    "orphans",
    "prefixes",
    "profile",
    "rollout_estimate",
]
