"""Agents: a common interface and the Phase 1 baselines.

An agent picks a move given a board and a state. ``agents/`` may import the
engine (``fliphex``) but the engine never imports agents (docs/engineering.md).
"""

from agents.base import Agent
from agents.heuristic_agent import HeuristicAgent
from agents.random_agent import RandomAgent
from agents.solver_agent import SolverAgent

__all__ = ["Agent", "HeuristicAgent", "RandomAgent", "SolverAgent"]
