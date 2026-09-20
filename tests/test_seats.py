"""Tests for ui.seats — seat construction, budgets, and the cost of importing."""

import json
import subprocess
import sys

import pytest

from agents.heuristic_agent import HeuristicAgent
from agents.random_agent import RandomAgent
from agents.solver_agent import SolverAgent
from fliphex.variant import FIVE_BY_THREE, FULL_GAME, THREE_BY_THREE
from ui.seats import (
    DEFAULT_SEARCH_BELOW_K,
    DEFAULT_SOLVER_NODES,
    SEAT_KINDS,
    ChampionUnavailableError,
    build_seat,
    describe_seat,
    load_champion,
    solver_budget,
)

# -- the seat registry ---------------------------------------------------------


def test_every_seat_the_cli_offers_is_buildable_or_explains_itself():
    assert set(SEAT_KINDS) == {"human", "random", "heuristic", "solver", "uct", "az"}


def test_human_is_the_absence_of_an_agent():
    assert build_seat("human", variant=FULL_GAME) is None


@pytest.mark.parametrize(
    ("kind", "expected"),
    [("random", RandomAgent), ("heuristic", HeuristicAgent), ("solver", SolverAgent)],
)
def test_the_stdlib_seats_build(kind, expected):
    assert isinstance(build_seat(kind, variant=FULL_GAME, seed=0), expected)


def test_an_unknown_seat_names_the_ones_that_exist():
    with pytest.raises(ValueError, match="unknown seat"):
        build_seat("grandmaster", variant=FULL_GAME)


def test_a_seed_is_injected_at_construction_so_a_game_replays():
    board, state = FULL_GAME.board(), FULL_GAME.initial_state()
    first = build_seat("random", variant=FULL_GAME, seed=7).select(board, state)
    second = build_seat("random", variant=FULL_GAME, seed=7).select(board, state)
    assert first == second


# -- budgets -------------------------------------------------------------------


def test_the_3x3_is_searched_exhaustively_from_the_opening():
    nodes, below_k = solver_budget(THREE_BY_THREE)
    assert below_k is None, "9 cells is solvable outright; declining plies wastes it"
    assert nodes == DEFAULT_SOLVER_NODES


@pytest.mark.parametrize("variant", [FIVE_BY_THREE, FULL_GAME])
def test_larger_boards_decline_the_plies_they_cannot_prove(variant):
    nodes, below_k = solver_budget(variant)
    assert (nodes, below_k) == (DEFAULT_SOLVER_NODES, DEFAULT_SEARCH_BELOW_K)


def test_the_solver_seat_takes_the_budget_for_its_board():
    small = build_seat("solver", variant=THREE_BY_THREE)
    large = build_seat("solver", variant=FULL_GAME)
    assert small.search_below_k is None
    assert large.search_below_k == DEFAULT_SEARCH_BELOW_K


def test_an_explicit_budget_overrides_the_per_board_default():
    agent = build_seat("solver", variant=FULL_GAME, max_nodes=99, search_below_k=3)
    assert (agent.max_nodes, agent.search_below_k) == (99, 3)


def test_the_solver_seat_plays_the_3x3_perfectly_and_says_so():
    """The 3x3 is the one board a CLI game can prove every move on."""
    from fliphex.moves import apply_move
    from fliphex.rules import winner
    from fliphex.state import Colour

    board = THREE_BY_THREE.board()
    agent = build_seat("solver", variant=THREE_BY_THREE, seed=0)
    opponent = build_seat("heuristic", variant=THREE_BY_THREE, seed=0)
    state = THREE_BY_THREE.initial_state()
    while not state.is_terminal():
        mover = agent if state.to_move == Colour.PURPLE else opponent
        state = apply_move(board, state, mover.select(board, state))

    assert agent.stats()["proved_rate"] == 1.0
    assert agent.delegated == 0
    assert winner(state) == Colour.PURPLE  # H1 and H2, on every 3x3 solve


# -- the champion --------------------------------------------------------------


def test_a_missing_champion_names_the_path_and_the_remedy(tmp_path):
    with pytest.raises(ChampionUnavailableError) as caught:
        load_champion(tmp_path / "absent", FULL_GAME)
    message = str(caught.value)
    assert "absent" in message
    assert "gitignored" in message, "a clone has none, and that is not a bug"
    assert "exp015_h3_run.py" in message, "an error with no remedy is half an error"


def test_a_champion_for_another_board_is_refused_before_torch_sees_it(tmp_path):
    """Shape-locked heads raise deep inside ``load_state_dict`` otherwise.

    The message has to explain the architecture, not relay a tensor mismatch.
    """
    spec = {"class": "ConvRotationNet", "n_cols": 5, "n_rows": 5}
    (tmp_path / "manifest.json").write_text(json.dumps({"meta": {"net_spec": spec}}))
    (tmp_path / "state.pt").write_bytes(b"never read")

    with pytest.raises(ChampionUnavailableError, match="shape-locked"):
        load_champion(tmp_path, THREE_BY_THREE)


def test_a_manifest_without_an_architecture_is_refused(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"meta": {}}))
    (tmp_path / "state.pt").write_bytes(b"never read")
    with pytest.raises(ChampionUnavailableError, match="net_spec"):
        load_champion(tmp_path, FULL_GAME)


# -- import cost ---------------------------------------------------------------

_PROBE = """
import sys
import ui.seats
from fliphex.variant import FULL_GAME
ui.seats.build_seat({kind!r}, variant=FULL_GAME, seed=0)
print("torch" in sys.modules)
"""


@pytest.mark.parametrize("kind", ["human", "random", "heuristic", "solver"])
def test_a_seat_that_is_not_the_learner_never_pays_for_torch(kind):
    """The property the module's structure exists to hold.

    ``agents/__init__.py`` omits :class:`AZAgent` for this reason: importing it
    costs a second or two and fails outright under the interpreter the exact
    solver runs on. A module-level import here would put that cost back, and
    nothing inside this process could observe it once another test has already
    imported torch — hence the subprocess.
    """
    result = subprocess.run(
        [sys.executable, "-c", _PROBE.format(kind=kind)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "False", result.stdout


# -- descriptions --------------------------------------------------------------


def test_a_human_seat_is_described_as_one():
    assert describe_seat(None) == "human"


def test_the_solver_description_distinguishes_its_two_regimes():
    assert "exhaustive" in describe_seat(build_seat("solver", variant=THREE_BY_THREE))
    assert "endgame-exact" in describe_seat(build_seat("solver", variant=FULL_GAME))


def test_a_search_agent_is_described_with_its_budget():
    pytest.importorskip("torch")
    agent = build_seat("uct", variant=FULL_GAME, simulations=17, seed=0)
    assert "17 simulations/move" in describe_seat(agent)


def test_the_plain_agents_are_described_by_name():
    assert describe_seat(build_seat("heuristic", variant=FULL_GAME)) == "heuristic"
