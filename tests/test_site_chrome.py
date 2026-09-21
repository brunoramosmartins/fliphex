"""The page wears the portfolio's chrome, and the copy is pinned.

``web/site.css`` transcribes design tokens from a *different repository* —
brunoramosmartins.github.io, design system v0.2. This repository cannot import
them, so what it can do instead is refuse to let the copy be edited quietly.

These tests do **not** check that the portfolio still uses these values; nothing
here can know that. They check that this file has not drifted from the numbers
its own header comment records, which is the difference between a copy with a
provenance and a copy without one. The review trigger is stated in
``web/site.css``: a design system above v0.2 means re-reading its ``design.md``
and updating this file and that one together.

The separation the tests exist to protect is the one in ``site.css``'s opening
paragraph — **the frame matches the building, the canvas does not.** The game's
colours answer to :mod:`ui.theme` and appear nowhere below.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
SITE_CSS = (WEB / "site.css").read_text()
INDEX = (WEB / "index.html").read_text()

#: Portfolio design system v0.2, transcribed from its ``docs/design.md`` and
#: ``assets/css/base.css``. The token name here is the one ``site.css`` uses;
#: the comment is the name it carries over there.
PORTFOLIO_TOKENS: dict[str, str] = {
    "--site-bg": "#ffffff",  # --color-bg
    "--site-border": "#e2dfd9",  # --color-border
    "--site-text": "#1c1c1c",  # --color-text-primary
    "--site-text-secondary": "#5c5c5c",  # --color-text-secondary
    "--site-accent": "#1d3557",  # --color-accent
    "--site-accent-hover": "#457b9d",  # --color-accent-hover
    "--site-header-height": "64px",  # --header-height
    "--site-container-wide": "1100px",  # --container-wide
    "--site-gutter": "1.5rem",  # --space-6
    "--site-nav-gap": "2rem",  # --space-8
    "--site-footer-pad": "3rem",  # --space-12
}


def _light_root() -> str:
    """The first ``:root`` block, which is the light one."""
    return SITE_CSS.split(":root {", 1)[1].split("}", 1)[0]


@pytest.mark.parametrize(("token", "value"), sorted(PORTFOLIO_TOKENS.items()))
def test_the_transcribed_token_still_says_what_it_was_transcribed_as(token, value):
    assert f"{token}: {value};" in _light_root(), f"{token} drifted from {value}"


def test_the_game_palette_does_not_leak_into_the_chrome():
    """The canvas is not repainted to match the frame.

    Purple and green are the physical tiles this project is a counterpart of.
    If either ever appears as a literal in the chrome layer, somebody has
    started designing the game to match a website.
    """
    from ui.theme import LIGHT

    for name in ("purple", "green", "purple-soft", "green-soft"):
        assert LIGHT[name] not in SITE_CSS, f"{name} leaked into site.css"


def test_the_chrome_does_not_redeclare_a_generated_theme_token():
    """``theme.css`` is generated; a second declaration of one of its tokens
    would be the hand-copied palette all over again, one file to the right."""
    from ui.theme import DARK, LIGHT, WEB_ONLY

    owned = {f"--{name}" for name in (*LIGHT, *DARK, *WEB_ONLY)}
    declared = set(re.findall(r"^\s*(--[a-z0-9-]+):", SITE_CSS, re.MULTILINE))
    # Referencing them is the point (the dark chrome borrows the game's dark
    # ground); declaring them is not.
    assert not (declared & owned), f"site.css redeclares {sorted(declared & owned)}"


def test_every_chrome_token_is_given_a_dark_value_or_is_a_metric():
    """The portfolio has no dark mode and this page does.

    A colour left at its light value would be white-on-white for a visitor whose
    system is dark. Metrics are exempt: 64px is 64px in either scheme.
    """
    explicit = SITE_CSS.split(':root[data-theme="dark"]', 1)[1]
    scheme = SITE_CSS.split(':root:not([data-theme="light"])', 1)[1]
    scheme = scheme.split(":root[", 1)[0]
    for token, value in PORTFOLIO_TOKENS.items():
        if not value.startswith("#"):
            continue  # a metric is the same length in either scheme
        assert f"{token}:" in explicit, f"{token} has no explicit dark value"
        assert f"{token}:" in scheme, f"{token} is missing from prefers-color-scheme"


def test_the_navigation_marks_the_page_the_visitor_is_on():
    """A site nav that highlights nothing reads as a copy of a site nav."""
    nav = INDEX.split('id="site-nav"', 1)[1].split("</nav>", 1)[0]
    active = re.findall(r'<a href="([^"]+)"[^>]*class="active"', nav)
    assert active == ["/projects.html"], active
    assert 'aria-current="page"' in nav


def test_the_site_links_are_absolute_so_they_work_from_a_subdirectory():
    """The page is served from ``/fliphex/``. A relative ``index.html`` there
    points at this page, not at the site's home, which is the single easiest way
    to make a deployment look broken."""
    nav = INDEX.split('id="site-nav"', 1)[1].split("</nav>", 1)[0]
    hrefs = re.findall(r'<a href="([^"]+)"', nav)
    assert hrefs, "no navigation links found"
    assert all(h.startswith("/") for h in hrefs), hrefs


def test_there_is_exactly_one_footer():
    """Two stacked footers is the lean-to this whole layer exists to avoid."""
    assert INDEX.count("<footer") == 1
    assert INDEX.count("</footer>") == 1


def test_the_footer_still_carries_the_engine_status_it_carried_before():
    """The chrome joined the game's footer; it did not replace it."""
    footer = INDEX.split("<footer", 1)[1].split("</footer>", 1)[0]
    assert 'id="engine-badge"' in footer
    assert 'id="origin-note"' in footer
    assert "footer-copy" in footer


def test_the_page_asks_for_the_typeface_its_own_stack_nominates():
    """``ui/theme.py`` has led with IBM Plex Sans since it was written, and no
    machine in this project had it installed. The portfolio already loads the
    family, so the page asks for it rather than falling through to DejaVu."""
    from ui.theme import FONT_STACK

    assert FONT_STACK[0] == "IBM Plex Sans"
    assert "fonts.googleapis.com" in INDEX
    for family in ("IBM+Plex+Sans", "IBM+Plex+Serif", "IBM+Plex+Mono"):
        assert family in INDEX, f"{family} is not requested"


def test_the_hidden_attribute_outranks_the_stylesheet():
    """Three elements shipped ``hidden`` and three rules cancelled it.

    ``[hidden] { display: none }`` comes from the browser's own sheet at the
    weakest specificity there is, so any class or id rule setting ``display``
    on the same element wins and the attribute does nothing. ``.boot``,
    ``#board`` and ``.scoreline`` each did, and the visible result was the boot
    panel — spinner still turning — sitting under a game in progress.

    jsdom cannot catch this: it has no layout and no cascade, so
    ``element.hidden`` reads true there whatever the stylesheet says. The check
    is therefore static, and it asserts the ``!important`` as well, because
    outranking a class is the entire job of the rule.

    Comments are stripped first. The rule's own explanation quotes the browser's
    weak default verbatim, so the first version of this check found the prose and
    passed while the stylesheet said something else — the same way the stylesheet
    link-order test once matched the comment naming the two files.
    """
    style = re.sub(r"/\*.*?\*/", "", (WEB / "style.css").read_text(), flags=re.S)
    rule = re.search(r"\[hidden\]\s*\{([^}]*)\}", style)
    assert rule, "style.css has no [hidden] override"
    body = rule.group(1).replace(" ", "")
    assert "display:none!important" in body, rule.group(1)


def test_every_element_shipped_hidden_is_covered_by_that_rule():
    """The elements the page hides at boot, named so the rule has a reason.

    If this list grows, the new element is relying on the override above; if it
    shrinks to nothing, the override can go.
    """
    hidden = set(re.findall(r'<(\w+)[^>]*\bid="([^"]+)"[^>]*\bhidden', INDEX))
    ids = {i for _, i in hidden}
    assert ids == {"board", "scoreline", "rotation-panel"}, sorted(ids)
