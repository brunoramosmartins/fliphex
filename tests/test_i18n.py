"""The page ships in two languages, and the failure mode is being half in each.

The game is going on display at the Matemateca, IME-USP's mathematics exhibition
space, so ``web/index.html`` is authored in Portuguese and offers English from a
control in the game's own bar. ``web/i18n.js`` carries both dictionaries.

WHY THIS IS IN PYTEST AND NOT ONLY IN THE JSDOM SUITE
-----------------------------------------------------
``web/test/page.test.mjs`` checks all of this and more, against the page as it
actually runs — and **CI does not run it**. ``.github/workflows/ci.yml`` installs
Python and runs ``pytest``; there is no npm step anywhere in it. So every
guarantee that lives only in the JavaScript suite holds exactly as often as
somebody remembers to type ``npm test`` in ``web/``.

That is the same shape as the two defects that closed Phase 7: a CI job that
existed for the exact configuration that broke and had never run, and a
generated artifact with a staleness guard on one half and none on the other.
The verification existed and was not in the path. These checks are therefore
duplicated here, deliberately, in the suite CI does run — parsed out of the
JavaScript as text, which is enough for questions about *which keys exist*.

What cannot be checked anywhere: whether a translation is any good. Nothing
mechanical judges that, and no test below pretends to.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
INDEX = (WEB / "index.html").read_text()
I18N = (WEB / "i18n.js").read_text()
APP = (WEB / "app.js").read_text()

LANGS = ("pt", "en")


def _strip_comments(source: str) -> str:
    """Block comments out, so prose that looks like a key is not read as one.

    The stylesheet link-order check and the ``[hidden]`` check were both written
    twice for want of this: the first version of each matched the comment that
    explained the rule and passed while the code said something else.
    """
    return re.sub(r"/\*.*?\*/", "", source, flags=re.S)


def _dictionary(lang: str) -> dict[str, str]:
    """The keys and values of one dictionary in ``web/i18n.js``.

    Textual, not a parse. ``STRINGS`` is an object literal of two flat
    string-to-string maps, and the entry shape is fixed enough that a regex over
    the block between ``<lang>: {`` and the closing brace is honest. A nested
    object would break this, which is the point at which this file should stop
    reading JavaScript with a regular expression and the dictionaries should
    move to JSON.
    """
    body = _strip_comments(I18N)
    start = body.index(f"\n  {lang}: {{")
    end = body.index("\n  },", start)
    block = body[start:end]
    return dict(re.findall(r'"([\w.]+)":\s*\n?\s*"((?:[^"\\]|\\.)*)"', block))


PT = _dictionary("pt")
EN = _dictionary("en")


def _markup_keys() -> set[str]:
    """Every key ``index.html`` names, through any of the three markers."""
    keys = set(re.findall(r'data-i18n(?:-html)?="([\w.]+)"', INDEX))
    for group in re.findall(r'data-i18n-attr="([^"]+)"', INDEX):
        for pair in group.split(","):
            keys.add(pair.split(":")[1].strip())
    return keys


def _code_keys() -> set[str]:
    """Every key ``app.js`` looks up as a literal, plus the two it builds.

    ``t(f"seat.{seat}")`` and ``t(f"colour.{colour}")`` are assembled at runtime
    and cannot be scanned. They are listed explicitly rather than skipped: a
    scan that quietly ignored them would report a clean sweep over the very
    keys most likely to be missing, since they are the ones no grep finds.
    """
    keys = set(re.findall(r'\b(?:t|setBadge)\("([\w.]+)"', _strip_comments(APP)))
    keys |= {f"seat.{seat}" for seat in ("human", "random", "heuristic", "solver")}
    keys |= {f"colour.{colour}" for colour in ("PURPLE", "GREEN")}
    return keys


# -- the dictionaries ---------------------------------------------------------


def test_both_dictionaries_were_found_at_all():
    """A regex that matched nothing would make every check below vacuous."""
    assert len(PT) > 40, len(PT)
    assert len(EN) > 40, len(EN)


def test_the_two_dictionaries_carry_exactly_the_same_keys():
    """The half-translated page, caught at its only mechanical symptom.

    A key present in one dictionary and absent from the other renders as the key
    itself — ``hint.pick`` sitting in the interface — because ``t`` deliberately
    does not fall back to the other language. Falling back would produce a page
    that is quietly bilingual in the wrong places and looks deliberate.
    """
    assert set(PT) == set(EN), {
        "only in pt": sorted(set(PT) - set(EN)),
        "only in en": sorted(set(EN) - set(PT)),
    }


def test_no_value_is_empty():
    for lang, table in zip(LANGS, (PT, EN), strict=True):
        blank = [key for key, value in table.items() if not value.strip()]
        assert not blank, f"{lang}: {blank}"


def test_the_two_languages_actually_differ():
    """A dictionary copied and not translated would pass every other check here.

    Not every entry differs, and the ones that do not are named: the language
    control labels each other's language on purpose, so a visitor who cannot
    read the current one can still find the way out.
    """
    same = {key for key in PT if PT[key] == EN[key]}
    assert same <= {"lang.pt", "lang.en"}, sorted(same - {"lang.pt", "lang.en"})


# -- the keys the page asks for ------------------------------------------------


@pytest.mark.parametrize("lang", LANGS)
def test_every_key_the_markup_names_exists(lang: str):
    table = PT if lang == "pt" else EN
    keys = _markup_keys()
    assert keys, "index.html names no keys at all"
    assert not (keys - set(table)), sorted(keys - set(table))


@pytest.mark.parametrize("lang", LANGS)
def test_every_key_the_code_asks_for_exists(lang: str):
    table = PT if lang == "pt" else EN
    missing = _code_keys() - set(table)
    assert not missing, sorted(missing)


def test_no_dictionary_entry_is_unreachable():
    """An entry nothing names is a translation of something that was deleted."""
    reachable = _markup_keys() | _code_keys() | {"html.lang"}
    assert not (set(PT) - reachable), sorted(set(PT) - reachable)


# -- what the page ships as ----------------------------------------------------


def test_portuguese_is_the_default_and_the_markup_is_written_in_it():
    """The static file is authored in the default language, not rewritten to it.

    A module script is deferred, so a page that shipped English and swapped on
    load would show every Portuguese-speaking visitor — the audience the
    exhibition is for — a flash of English on the path that has to be right.
    The declared ``lang`` is what proves which way round it is.
    """
    assert 'export const DEFAULT_LANG = "pt";' in I18N
    assert '<html lang="pt-BR">' in INDEX, "the document does not declare pt-BR"
    assert PT["html.lang"] == "pt-BR"
    assert EN["html.lang"] == "en"


def test_the_site_chrome_is_not_translated():
    """The boundary from ``i18n.js``'s header comment, pinned.

    Every link in the site navigation leads to a page of
    brunoramosmartins.github.io that exists only in English. A Portuguese label
    on it would promise something the destination does not keep. The same
    reasoning as ``site.css``'s opening paragraph, one layer up: the frame
    belongs to the building and the canvas to the game.
    """
    nav = INDEX.split('id="site-nav"', 1)[1].split("</nav>", 1)[0]
    assert "data-i18n" not in nav, nav
    assert ">Projects<" in nav and ">About<" in nav

    footer_links = INDEX.split('class="footer-links"', 1)[1].split("</nav>", 1)[0]
    assert "data-i18n" not in footer_links, footer_links


def test_the_language_control_is_in_the_game_bar_not_the_site_header():
    """No other page of the portfolio has one, so the shared header cannot.

    Putting it in the site header would mean this page's copy of that header is
    no longer the site's header — which is the lean-to ``site.css`` exists to
    avoid, arrived at from the other direction.
    """
    site_header = INDEX.split('class="site-header"', 1)[1].split("</header>", 1)[0]
    assert "lang-switch" not in site_header

    bar = INDEX.split('<header class="bar">', 1)[1].split("</header>", 1)[0]
    assert 'class="lang-switch"' in bar
    offered = bar.count('data-lang="')
    assert offered == 2, f"the switch offers {offered} languages, not two"


@pytest.mark.parametrize("lang", LANGS)
def test_the_full_board_hint_takes_its_cell_count_as_a_variable(lang: str):
    """It read "25 is odd" on every board, and two of the three are not 25.

    25 is right on the shipped 5x5 and wrong on both boards this project
    actually solved: the 5x3 has 15 cells and the 3x3 has 9. On a full board the
    two scores account for every cell, so ``app.js`` passes their sum; adr-011
    is why it is always odd. Without the placeholder the sentence cannot say it,
    and every other check in this file would still pass.
    """
    table = PT if lang == "pt" else EN
    assert "{cells}" in table["hint.full"], table["hint.full"]
    assert "25" not in table["hint.full"], table["hint.full"]


def test_no_user_facing_literal_was_left_behind_in_the_badge_path():
    """The badge is the one element the markup and the code both write.

    ``index.html`` marks it ``data-i18n="badge.booting"`` so it reads correctly
    before the module loads, which means re-applying the static pass to a booted
    page would tell it that it is booting again. ``setBadge`` records the key so
    the language switch can render the badge's *current* state instead.
    """
    assert 'data-i18n="badge.booting"' in INDEX
    assert "function setBadge(" in APP
    assert "if (state.badge) setBadge(" in APP
