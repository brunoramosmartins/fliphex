"""The palette is one dict, and both interfaces have to be reading it.

``ui/pygame_ui.py`` used to carry twelve hand-copied RGB tuples under a comment
saying "matching web/style.css", and the stylesheet carried twelve hex strings
under one saying the same thing in the other direction. Two declarations and a
pair of comments asserting they agreed. These tests are what turns the assertion
into a constraint.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ui.theme import DARK, LIGHT, WEB_ONLY, rgb, stylesheet

THEME_CSS = Path(__file__).resolve().parent.parent / "web" / "theme.css"


# -- the tokens themselves -----------------------------------------------------


def test_every_colour_is_a_six_digit_hex_triple():
    for name, value in {**LIGHT, **DARK}.items():
        assert re.fullmatch(r"#[0-9a-f]{6}", value), f"{name} = {value!r}"


def test_the_dark_scheme_only_overrides_tokens_that_exist():
    unknown = set(DARK) - set(LIGHT)
    assert not unknown, f"dark defines tokens the light palette has not: {unknown}"


def test_the_player_colours_survive_the_dark_scheme():
    """Chrome may inverate; the game's two colours are its identity.

    A purple that is one purple in daylight and another at night would make two
    screenshots of the same position look like two different games.
    """
    assert "purple" not in DARK
    assert "green" not in DARK


def test_rgb_converts_to_the_triple_pygame_wants():
    assert rgb("purple") == (107, 63, 160)
    assert rgb("green") == (61, 143, 92)
    assert rgb("wood") == (243, 236, 226)


def test_rgb_reads_the_dark_palette_when_asked():
    assert rgb("wood", DARK) == (27, 25, 23)


def test_an_unknown_token_raises_rather_than_drawing_black():
    """Forgiving this would be a drawing bug found by looking, not by testing."""
    with pytest.raises(KeyError):
        rgb("chartreuse")


# -- what pygame reads ---------------------------------------------------------


def test_the_window_draws_from_the_same_dict():
    from ui import pygame_ui

    for token, constant in (
        ("purple", pygame_ui.PURPLE),
        ("purple-soft", pygame_ui.PURPLE_SOFT),
        ("green", pygame_ui.GREEN),
        ("green-soft", pygame_ui.GREEN_SOFT),
        ("wood", pygame_ui.WOOD),
        ("wood-deep", pygame_ui.WOOD_DEEP),
        ("ink", pygame_ui.INK),
        ("ink-soft", pygame_ui.INK_SOFT),
        ("line", pygame_ui.LINE),
        ("empty", pygame_ui.EMPTY),
        ("danger", pygame_ui.DANGER),
    ):
        assert constant == rgb(token), token


# -- what the page reads -------------------------------------------------------


def _declarations(text: str) -> dict[str, str]:
    """Every ``--token: value`` in the file, last declaration winning."""
    return {
        name: value.strip()
        for name, value in re.findall(r"--([a-z-]+):\s*([^;]+);", text)
    }


def test_the_generated_stylesheet_carries_every_token():
    declared = _declarations(stylesheet())
    for name in {**LIGHT, **WEB_ONLY}:
        assert name in declared, name


def test_the_checked_in_theme_is_current():
    """CI fails on a dirty tree after a rebuild; this fails earlier and louder."""
    assert THEME_CSS.exists(), "run python scripts/build_web.py"
    assert THEME_CSS.read_text() == stylesheet(), (
        "web/theme.css is stale — run python scripts/build_web.py"
    )


def test_the_stylesheet_says_it_is_generated():
    assert "do not edit" in stylesheet().splitlines()[0].lower()


def test_the_page_stylesheet_no_longer_declares_its_own_palette():
    """The defect this module exists to prevent, asserted directly.

    A second `:root` block in `style.css` would silently win or lose by source
    order, and the two interfaces would drift apart again with both files still
    carrying comments claiming they agreed.
    """
    style = (THEME_CSS.parent / "style.css").read_text()
    declared = _declarations(style)
    assert not declared, f"style.css re-declares tokens: {sorted(declared)}"


def test_the_page_links_its_three_stylesheets_in_the_one_order_that_works():
    """Order is load-bearing twice over, in opposite directions.

    ``theme.css`` first because ``style.css`` *uses* tokens it declares, and a
    custom property read before it is declared resolves to nothing. ``site.css``
    last because it is the portfolio's chrome and has to *win* where the two
    disagree — the page width and the footer are both declared in both.

    Matched against the ``<link>`` tags rather than the raw text, because the
    comment above them names the files and the first version of this check found
    the comment.
    """
    html = (THEME_CSS.parent / "index.html").read_text()
    linked = re.findall(r'<link rel="stylesheet" href="([^"]+)"', html)
    assert linked == ["theme.css", "style.css", "site.css"], linked
