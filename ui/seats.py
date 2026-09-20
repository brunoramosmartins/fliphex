"""Which agent sits in which colour, and how each one is built.

Separated from :mod:`ui.cli` because seat construction is the part every
interface needs and none of them should reimplement. The CLI, the pygame window
and the browser build all ask the same question — *give me the agent the user
named, on this variant* — and the answer involves enough per-agent judgement
(budgets that depend on board size, a champion that is shape-locked to one
board, an import that costs a second) that three copies would drift.

Importing this module must stay cheap
-------------------------------------
``agents.az_agent`` pulls in ``torch``, which costs a second or two and is
absent entirely from the faster interpreter the exact-solver runs use — the
reason ``agents/__init__.py`` does not export it. So the AZ import here is
**local to the function that needs it**, and asking for any other seat never
pays for it. The same discipline is what will let a browser build load the
rules engine without the learner: ``fliphex``, ``solver`` and every seat below
except ``az`` are pure standard library.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from agents.base import Agent
from agents.heuristic_agent import HeuristicAgent
from agents.random_agent import RandomAgent
from agents.solver_agent import SolverAgent
from fliphex.variant import Variant

if TYPE_CHECKING:  # pragma: no cover - typing only, never imported at runtime
    from az.network import FlipHexNet

#: Seat names accepted on the command line. ``human`` is the absence of an
#: agent rather than a kind of one, and is spelled out here so the interfaces
#: can offer it in the same list.
SEAT_KINDS: tuple[str, ...] = (
    "human",
    "random",
    "heuristic",
    "solver",
    "uct",
    "az",
)

#: Where ``scripts/exp015_h3_run.py`` writes its runs. Gitignored — a clone has
#: no champion, which is why :func:`load_champion` explains rather than raises
#: a bare ``FileNotFoundError``.
DEFAULT_RUN_ROOT = Path("data/az-runs/h3-seed2")

#: EXP-017's budget, reused so a CLI game is played under the protocol the
#: shipped-board first-player figure was measured under.
DEFAULT_SOLVER_NODES = 2_000_000
DEFAULT_SEARCH_BELOW_K = 8

#: EXP-015's self-play budget. Strong enough to be worth playing, small enough
#: that a move lands in seconds rather than minutes.
DEFAULT_SIMULATIONS = 400


def solver_budget(variant: Variant) -> tuple[int | None, int | None]:
    """Return ``(max_nodes, search_below_k)`` suited to ``variant``.

    The 3x3 is solved outright from the opening — 711,963 configurations, which
    a transposition table walks in well under the default budget — so it gets
    no ``search_below_k`` and plays perfectly from ply one. Anything larger gets
    EXP-017's pair instead, because a search that will exceed its budget spends
    the whole budget before saying so: attempting all 25 plies at 2M nodes costs
    ~34M nodes per game and proves nothing. Declining the attempt is cheaper and
    is counted separately, so "we did not try" stays distinguishable from "we
    tried and could not".
    """
    if variant.n_cells <= 9:
        return DEFAULT_SOLVER_NODES, None
    return DEFAULT_SOLVER_NODES, DEFAULT_SEARCH_BELOW_K


class ChampionUnavailableError(RuntimeError):
    """No usable trained network at the path asked for.

    Carries its own remedy: a clone of this repository has no champion, because
    ``data/az-runs/`` is gitignored, and that is a fact about distribution
    rather than a bug to be reported.
    """


def load_champion(root: Path, variant: Variant) -> FlipHexNet:
    """Load the champion network from a training run directory.

    Reads the architecture from ``manifest.json`` rather than assuming it. A
    ``state_dict`` says what the parameters are and nothing about the shape of
    network they belong to; hard-coding the shape is what once left the
    deployment path unable to play the adopted head, and only under multiple
    workers, which no test exercised.

    The replay buffer is *not* read. ``Checkpoint.load`` would pull a 29 MB
    pickle this has no use for; the weights alone are about 1.4 MB.

    Raises:
        ChampionUnavailableError: If the directory, the manifest or the weights are
            missing, or if the network was trained on a different board.
    """
    manifest_path = root / "manifest.json"
    weights_path = root / "state.pt"
    if not manifest_path.exists() or not weights_path.exists():
        raise ChampionUnavailableError(
            f"no trained network in {root}/.\n"
            f"  data/az-runs/ is gitignored, so a fresh clone has no champion —\n"
            f"  the networks are 5.7 MB each and were never distributed.\n"
            f"  Train one with:  .venv/bin/python scripts/exp015_h3_run.py --seed 1\n"
            f"  Or play a seat that needs no training: "
            f"--green heuristic, --green solver, --green uct"
        )

    manifest = json.loads(manifest_path.read_text())
    spec = manifest.get("meta", {}).get("net_spec")
    if spec is None:
        raise ChampionUnavailableError(
            f"{manifest_path} carries no meta.net_spec, so the architecture "
            f"behind its weights is unknown and cannot be rebuilt safely"
        )

    trained_on = (spec.get("n_cols"), spec.get("n_rows"))
    if trained_on != (variant.n_cols, variant.n_rows):
        raise ChampionUnavailableError(
            f"that champion was trained on {trained_on[0]}x{trained_on[1]} and "
            f"you asked for {variant.n_cols}x{variant.n_rows}.\n"
            f"  The head flattens the board into a per-cell readout, so the "
            f"network is shape-locked to one board and cannot be transferred.\n"
            f"  This is the same limit docs/research.md records against H3's "
            f"reduced-board members."
        )

    import torch  # local: see the module docstring

    from az.network import build_net

    net = build_net(spec)
    blob = torch.load(weights_path, weights_only=False, map_location="cpu")
    if "champion" not in blob:
        raise ChampionUnavailableError(
            f"{weights_path} holds no champion weights (keys: {sorted(blob)})"
        )
    net.load_state_dict(blob["champion"])
    net.eval()
    return net


def build_seat(
    kind: str,
    *,
    variant: Variant,
    seed: int | None = None,
    run_root: Path = DEFAULT_RUN_ROOT,
    simulations: int = DEFAULT_SIMULATIONS,
    max_nodes: int | None = None,
    search_below_k: int | None = None,
) -> Agent | None:
    """Build the agent for one seat. ``None`` means a human plays it.

    Args:
        kind: One of :data:`SEAT_KINDS`.
        variant: The board and deck being played, which sets the solver's
            budget and which champion can load.
        seed: Injected at construction, per the :class:`~agents.base.Agent`
            contract, so a game replays.
        run_root: Training run directory, for the ``az`` seat only.
        simulations: PUCT simulations per move, for ``az`` and ``uct``.
        max_nodes: Overrides the solver budget from :func:`solver_budget`.
        search_below_k: Overrides the solver's attempt threshold. Passing it
            explicitly is how a caller asks the 5x3 to be searched from deeper
            than EXP-017's protocol allows.

    Raises:
        ValueError: If ``kind`` is not a seat.
        ChampionUnavailableError: If ``az`` was asked for and none can be loaded.
    """
    if kind not in SEAT_KINDS:
        raise ValueError(f"unknown seat {kind!r}; choose from {list(SEAT_KINDS)}")

    if kind == "human":
        return None
    if kind == "random":
        return RandomAgent(seed=seed)
    if kind == "heuristic":
        return HeuristicAgent(seed=seed)
    if kind == "solver":
        budget_nodes, budget_k = solver_budget(variant)
        return SolverAgent(
            max_nodes=budget_nodes if max_nodes is None else max_nodes,
            search_below_k=budget_k if search_below_k is None else search_below_k,
            fallback=HeuristicAgent(seed=seed),
            seed=seed,
        )

    from agents.az_agent import AZAgent, UCTAgent  # local: see the module docstring

    if kind == "uct":
        return UCTAgent(simulations=simulations, seed=seed)
    net = load_champion(run_root, variant)
    return AZAgent(net, simulations=simulations, seed=seed)


def describe_seat(agent: Agent | None) -> str:
    """One line naming who is playing a seat, for the game header."""
    if agent is None:
        return "human"
    if isinstance(agent, SolverAgent):
        budget = "exhaustive" if agent.search_below_k is None else "endgame-exact"
        return f"solver ({budget}, {agent.max_nodes:,} nodes)"
    simulations = getattr(agent, "simulations", None)
    if simulations is not None:
        return f"{agent.name} ({simulations} simulations/move)"
    return agent.name
