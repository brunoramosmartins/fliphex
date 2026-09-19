"""Axis 3 — how large FLIPHEX is, and where that puts it among known games.

This package imports ``fliphex`` and nothing else from the project. It never
imports ``solver`` or ``az``: the complexity of a game is a property of its
rules, and a bound that depended on how well either axis happened to search
would not be one.

``profile`` is deliberately **not** re-exported: both ``state_space`` and
``branching`` define one, over different things. Import them from their module.
"""

from complexity.branching import Branching, branching_at, cross_check
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
)

__all__ = [
    "ORBITS",
    "Branching",
    "LayerCount",
    "RolloutEstimate",
    "SpaceProfile",
    "branching_at",
    "configurations",
    "cross_check",
    "effective_branching",
    "elementary_symmetric",
    "games",
    "minimal_tree",
    "orientation_inflated",
    "orphans",
    "prefixes",
    "rollout_estimate",
]
