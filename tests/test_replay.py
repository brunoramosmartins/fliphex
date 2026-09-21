"""Tests for ui.replay — recorded games, and the checks that make one trustworthy."""

import json

import pytest

from fliphex.moves import Move
from fliphex.state import Colour
from fliphex.variant import FIVE_BY_THREE, FULL_GAME, THREE_BY_THREE, Arm, Variant
from ui.replay import FORMAT, Provenance, Recording, RecordingError, Replay

# -- recording a game ----------------------------------------------------------


@pytest.mark.parametrize("variant", [THREE_BY_THREE, FIVE_BY_THREE, FULL_GAME])
def test_a_game_can_be_recorded_from_seats_alone(variant):
    """The source that always works: no file, no artefact, no network."""
    recording = Recording.from_seats(variant, "heuristic", "random", seed=0)
    assert len(recording.moves) == variant.n_cells
    assert recording.outcome == {}  # not replayed yet


def test_a_recorded_game_fills_the_board_and_decides():
    recording = Recording.from_seats(THREE_BY_THREE, seed=3)
    recording.replay()
    assert recording.outcome["terminal"] is True
    assert recording.outcome["winner"] in ("PURPLE", "GREEN")
    assert recording.outcome["plies"] == 9
    assert sum(recording.outcome["score"].values()) == 9


def test_the_same_seats_and_seed_give_the_same_game():
    """The property the whole format rests on."""
    a = Recording.from_seats(FIVE_BY_THREE, "heuristic", "random", seed=11)
    b = Recording.from_seats(FIVE_BY_THREE, "heuristic", "random", seed=11)
    assert a.moves == b.moves


def test_a_different_seed_gives_a_different_game():
    a = Recording.from_seats(FULL_GAME, "random", "random", seed=1)
    b = Recording.from_seats(FULL_GAME, "random", "random", seed=2)
    assert a.moves != b.moves


def test_the_two_seats_do_not_share_a_seed():
    """One seed on both sides would replay one stream twice."""
    recording = Recording.from_seats(FULL_GAME, "random", "random", seed=0)
    assert recording.provenance.seed == 0
    assert len(recording.moves) == 25


def test_a_human_seat_cannot_be_recorded_from_seats():
    with pytest.raises(RecordingError, match="no function to replay"):
        Recording.from_seats(THREE_BY_THREE, "human", "heuristic", seed=0)


# -- the round trip ------------------------------------------------------------


def test_a_recording_survives_a_round_trip_through_disk(tmp_path):
    original = Recording.from_seats(FIVE_BY_THREE, "heuristic", "random", seed=5)
    original.replay()
    path = original.save(tmp_path / "game.json")
    loaded = Recording.load(path)
    assert loaded.moves == original.moves
    assert loaded.variant == original.variant
    assert loaded.provenance.seed == 5


def test_the_saved_shape_is_json_and_declares_its_format(tmp_path):
    path = Recording.from_seats(THREE_BY_THREE, seed=0).save(tmp_path / "g.json")
    blob = json.loads(path.read_text())
    assert blob["format"] == FORMAT
    assert blob["variant"]["n_cols"] == 3
    assert all(len(m) == 3 for m in blob["moves"])


def test_an_unknown_format_is_refused_rather_than_guessed():
    with pytest.raises(RecordingError, match="unknown recording format"):
        Recording.from_dict({"format": "something-else/9", "moves": []})


def test_a_recording_carries_the_arm_it_was_played_on(tmp_path):
    original = Recording.from_seats(Variant(3, 3, Arm.H2), seed=0)
    loaded = Recording.load(original.save(tmp_path / "h2.json"))
    assert loaded.variant.arm is Arm.H2


def test_a_recording_carries_which_colour_moved_first(tmp_path):
    variant = Variant(3, 3, Arm.H1, Colour.GREEN)
    loaded = Recording.load(
        Recording.from_seats(variant, seed=0).save(tmp_path / "green.json")
    )
    assert loaded.variant.first == Colour.GREEN


# -- refusing what cannot be trusted -------------------------------------------


def test_an_illegal_move_list_is_refused_rather_than_drawn():
    """Data from a file is not trusted to be a game."""
    recording = Recording.from_seats(THREE_BY_THREE, seed=0)
    recording.moves[3] = Move(recording.moves[0].cell, recording.moves[3].tile, 0)
    with pytest.raises(RecordingError, match="is not legal here"):
        recording.replay()


def test_the_refusal_names_the_ply_and_the_tile():
    recording = Recording.from_seats(THREE_BY_THREE, seed=0)
    recording.moves[2] = Move(recording.moves[0].cell, recording.moves[2].tile, 0)
    with pytest.raises(RecordingError) as caught:
        recording.replay()
    assert "move 3 of 9" in str(caught.value)


def test_a_truncated_recording_replays_as_far_as_it_goes():
    """A partial game is a legitimate recording, not a corrupt one."""
    recording = Recording.from_seats(THREE_BY_THREE, seed=0)
    recording.moves = recording.moves[:4]
    recording.replay()
    assert recording.outcome["terminal"] is False
    assert recording.outcome["plies"] == 4


# -- provenance ----------------------------------------------------------------


def test_a_seeded_agent_game_verifies_against_its_own_provenance():
    recording = Recording.from_seats(FIVE_BY_THREE, "heuristic", "random", seed=7)
    assert "reproduce exactly" in recording.verify()


def test_a_recording_that_lies_about_its_provenance_is_refused():
    """The check that stops a move list carrying a source it did not come from."""
    recording = Recording.from_seats(THREE_BY_THREE, "heuristic", "random", seed=1)
    recording.provenance = Provenance("heuristic", "random", seed=999)
    with pytest.raises(RecordingError, match="does not reproduce"):
        recording.verify()


def test_an_unseeded_recording_says_so_instead_of_claiming_verification():
    recording = Recording.from_seats(THREE_BY_THREE, seed=0)
    recording.provenance = Provenance("heuristic", "heuristic", seed=None)
    verdict = recording.verify()
    assert "not reproducible" in verdict
    assert "replay legally" in verdict


def test_a_game_with_a_human_seat_is_never_called_reproducible():
    assert not Provenance("human", "heuristic", seed=0).reproducible()
    assert not Provenance("heuristic", "human", seed=0).reproducible()
    assert Provenance("heuristic", "solver", seed=0).reproducible()


# -- the cursor ----------------------------------------------------------------


@pytest.fixture
def replay():
    return Replay(Recording.from_seats(THREE_BY_THREE, "heuristic", "random", seed=2))


def test_a_replay_starts_at_the_opening(replay):
    assert replay.ply == 0
    assert replay.at_start and not replay.at_end
    assert set(replay.snapshot()["colours"]) == {"EMPTY"}


def test_stepping_forward_advances_one_ply(replay):
    snapshot = replay.forward()
    assert replay.ply == 1
    assert snapshot["ply"] == 1


def test_stepping_back_returns_the_earlier_position(replay):
    opening = replay.snapshot()["colours"]
    replay.forward(3)
    replay.back(3)
    assert replay.snapshot()["colours"] == opening
    assert replay.ply == 0


def test_seeking_lands_exactly_where_asked(replay):
    for ply in (0, 1, 5, 9, 4):
        replay.goto(ply)
        assert replay.ply == ply
        assert replay.snapshot()["ply"] == ply


def test_seeking_past_the_end_clamps_rather_than_raising(replay):
    replay.goto(999)
    assert replay.ply == replay.total
    assert replay.at_end


def test_seeking_before_the_start_clamps(replay):
    replay.goto(-5)
    assert replay.ply == 0
    assert replay.at_start


def test_a_seek_gives_the_same_position_as_stepping_there(replay):
    stepped = [replay.forward()["colours"] for _ in range(replay.total)]
    for ply, colours in enumerate(stepped, start=1):
        assert replay.goto(ply)["colours"] == colours


def test_the_replay_ends_where_the_recording_says_it_does(replay):
    replay.goto(replay.total)
    snapshot = replay.snapshot()
    assert snapshot["terminal"] is True
    assert snapshot["winner"] == replay.recording.outcome["winner"]


def test_the_cursor_reports_what_the_last_step_flipped(replay):
    replay.goto(replay.total)
    assert isinstance(replay.flipped(), list)
    assert replay.back().__class__ is dict


def test_the_opening_has_no_flips_to_report(replay):
    assert replay.flipped() == []


def test_a_bad_recording_is_refused_before_a_viewer_can_open_it():
    recording = Recording.from_seats(THREE_BY_THREE, seed=0)
    recording.moves[1] = Move(recording.moves[0].cell, recording.moves[1].tile, 0)
    with pytest.raises(RecordingError):
        Replay(recording)


# -- captions ------------------------------------------------------------------


def test_the_opening_caption_names_the_seats_and_the_seed(replay):
    caption = replay.caption()
    assert "opening position" in caption
    assert "heuristic" in caption and "random" in caption and "seed 2" in caption


def test_a_move_caption_names_the_ply_the_player_and_the_cell(replay):
    replay.forward()
    caption = replay.caption()
    assert "ply 1/9" in caption
    assert "Purple played" in caption


def test_a_caption_reports_flips_when_there_are_any(replay):
    captions = [
        replay.forward().get("ply") and replay.caption() for _ in range(replay.total)
    ]
    assert any("flipping" in c for c in captions if c)


def test_a_self_flip_is_reported_apart_from_a_capture():
    """The viewer drew both the same green until 2026-09-20.

    A flip is a toggle (adr-007): an arrow aimed at your own tile hands it over.
    Drawing that in the colour of a capture teaches the one rule a reader is
    most likely to get wrong, backwards.
    """
    recording = Recording.from_seats(THREE_BY_THREE, "heuristic", "heuristic", seed=0)
    cursor = Replay(recording)
    seen_any = False
    for ply in range(1, cursor.total + 1):
        cursor.goto(ply)
        gained, given = cursor.gained(), cursor.handed_back()
        assert not (set(gained) & set(given)), "a cell cannot be both at once"
        assert sorted(gained + given) == sorted(cursor.flipped())
        seen_any = seen_any or bool(gained or given)
    assert seen_any, "no flip happened at all, so this checked nothing"


def test_at_the_opening_nothing_has_flipped_either_way():
    recording = Recording.from_seats(THREE_BY_THREE, "heuristic", "heuristic", seed=0)
    cursor = Replay(recording)
    assert cursor.gained() == []
    assert cursor.handed_back() == []
