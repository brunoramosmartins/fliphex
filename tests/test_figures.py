"""Tests for ``figures/``.

**None of these imports matplotlib.** The plotting library lives in the
``figures`` extra, not in ``dev``, so CI does not have it — and the thing worth
checking in CI is not whether a chart renders but whether the promise attached
to this directory is being kept.

That promise is Phase 6's exit criterion: *every figure regenerates from a
tracked artefact*. Phase 5 planned ``figures/`` as a replacement for three
dropped notebooks and shipped nothing, which is recorded as that phase's failed
attempt 7. A criterion nobody checks is how that happens twice, so
``test_every_source_is_tracked_by_git`` is the one with teeth: this project
gitignores ``results/*.jsonl``, ``data/`` and ``notes/sources/``, and a figure
drawn from any of them would render on one machine and nowhere else.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from figures.build import check, tracked
from figures.manifest import (
    FIGURES,
    HYPOTHESES_WITH_VERDICTS,
    by_name,
    covered,
    uncovered,
)

ROOT = Path(__file__).resolve().parent.parent
FIGURES_DIR = ROOT / "figures"


# -- the promise ------------------------------------------------------------


def test_the_manifest_check_is_clean():
    assert check() == []


@pytest.mark.parametrize("figure", FIGURES, ids=[f.name for f in FIGURES])
def test_every_source_is_tracked_by_git(figure):
    """The criterion with teeth: a gitignored source renders nowhere else."""
    for source in figure.sources + figure.computed_from:
        assert (ROOT / source).exists(), f"{figure.name}: {source} is missing"
        assert tracked(source), f"{figure.name}: {source} is not tracked by git"


@pytest.mark.parametrize("figure", FIGURES, ids=[f.name for f in FIGURES])
def test_every_figure_declares_where_its_numbers_come_from(figure):
    assert figure.sources or figure.computed_from, figure.name


def test_no_figure_reads_a_gitignored_path():
    """Belt and braces: name the three trees this project ignores."""
    ignored = ("results/exp017-first-player-5x5.jsonl", "data/", "notes/sources/")
    for figure in FIGURES:
        for source in figure.sources + figure.computed_from:
            for prefix in ignored:
                assert not source.startswith(prefix), f"{figure.name}: {source}"


# -- coverage ---------------------------------------------------------------


def test_every_hypothesis_with_a_verdict_has_a_canonical_figure():
    assert uncovered() == []
    assert covered() == set(HYPOTHESES_WITH_VERDICTS)


def test_the_hypothesis_list_matches_the_verdict_table():
    """If ``docs/research.md`` gains or loses a verdict, this fails first."""
    import re

    research = (ROOT / "docs" / "research.md").read_text()
    table = research[research.index("| ID | Verdict |") :]
    written = {
        m.group(1)
        for m in re.finditer(r"^\| (H\d) \| (?!—)", table, flags=re.MULTILINE)
    }
    assert written == set(HYPOTHESES_WITH_VERDICTS)


@pytest.mark.parametrize("figure", FIGURES, ids=[f.name for f in FIGURES])
def test_every_figure_has_a_caption_for_the_writeup(figure):
    assert len(figure.caption.strip()) > 40, figure.name


# -- the files themselves ---------------------------------------------------


@pytest.mark.parametrize("figure", FIGURES, ids=[f.name for f in FIGURES])
def test_the_rendered_file_exists(figure):
    """The Phase 5 failure was an empty directory, so check the output too."""
    path = FIGURES_DIR / figure.name
    assert path.exists(), f"{figure.name} has never been built"
    assert path.stat().st_size > 20_000, f"{figure.name} looks empty"


@pytest.mark.parametrize("figure", FIGURES, ids=[f.name for f in FIGURES])
def test_the_rendered_file_is_in_the_repository(figure):
    """Enforced where it matters, advisory where it does not.

    On a fresh clone and in CI the file is either committed or absent, and
    absent must fail — that is the Phase 5 failure mode. On the machine that
    just rebuilt it, the file exists but is not yet staged, and failing there
    would only be telling the author to run ``git add``. So that case skips
    with the instruction instead.
    """
    path = f"figures/{figure.name}"
    if not tracked(path):
        if (FIGURES_DIR / figure.name).exists():
            pytest.skip(f"rebuilt but not staged — run `git add {path}`")
        pytest.fail(f"{figure.name} is neither built nor in the repository")


def test_the_gallery_is_current():
    """Generated like docs/board-geometry.md — regenerate, never hand-edit."""
    from figures.build import GALLERY, gallery

    assert GALLERY.exists(), "run `python -m figures.build --gallery`"
    assert GALLERY.read_text() == gallery(), (
        "figures/README.md is stale — run `python -m figures.build --gallery`"
    )


def test_the_directory_holds_no_stray_images():
    """Every PNG in figures/ is in the manifest, or it is not canonical."""
    rendered = {p.name for p in FIGURES_DIR.glob("*.png")}
    assert rendered == {f.name for f in FIGURES}


@pytest.mark.parametrize("figure", FIGURES, ids=[f.name for f in FIGURES])
def test_every_builder_module_exists(figure):
    path = ROOT / Path(figure.builder.replace(".", "/")).with_suffix(".py")
    assert path.exists(), f"{figure.name}: no builder at {path}"
    relative = str(path.relative_to(ROOT))
    if not tracked(relative):
        pytest.skip(f"builder not staged — run `git add {relative}`")


# -- the manifest module's own contract -------------------------------------


def test_manifest_imports_only_the_standard_library():
    """It has to be readable by CI, which has no plotting library.

    Parsed rather than grepped: the module's docstring discusses matplotlib at
    length, and a substring search would call that an import.
    """
    import ast
    import sys

    tree = ast.parse((FIGURES_DIR / "manifest.py").read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported <= set(sys.stdlib_module_names), imported


def test_by_name_raises_rather_than_returning_none():
    assert by_name(FIGURES[0].name) is FIGURES[0]
    with pytest.raises(KeyError, match="no figure named"):
        by_name("not-a-figure.png")


def test_tracked_says_no_for_a_gitignored_path():
    """The guard would be worthless if it returned True for everything."""
    assert not tracked("results/exp017-first-player-5x5.jsonl")
    assert tracked("docs/research.md")


def test_check_catches_an_untracked_source(tmp_path, monkeypatch):
    """Probe the probe: a manifest entry pointing at nothing must fail."""
    import figures.build as build
    import figures.manifest as manifest

    broken = manifest.Figure(
        name="nope.png",
        hypothesis=None,
        builder="figures.nope",
        caption="a caption long enough to pass the caption check on its own",
        sources=("results/does-not-exist.json",),
    )
    monkeypatch.setattr(build, "FIGURES", (*manifest.FIGURES, broken))
    problems = build.check()
    assert any("nope.png" in p and "missing" in p for p in problems)


def test_git_is_available_so_the_tracking_check_is_real():
    """If git were absent, ``tracked`` would silently return False for all."""
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, "not a git work tree; tracking checks are void"
