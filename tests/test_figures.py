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
def test_the_rendered_file_is_not_empty_when_present(figure):
    """A fresh clone has no PNGs, by design — see the next test.

    So absence is not a failure here; a rendered file that is a stub would be.
    """
    path = FIGURES_DIR / figure.name
    if not path.exists():
        pytest.skip("not rendered here — run `python -m figures.build`")
    assert path.stat().st_size > 20_000, f"{figure.name} looks empty"


def test_the_figures_are_ignored_because_their_inputs_are_tracked():
    """The .gitignore rule, encoded so it stays a decision rather than a habit.

    ``figures/*.png`` is gitignored, and the rule written above it in
    ``.gitignore`` says why: *track the per-item record when regenerating it
    needs something the repository does not have. Reproducibility is the test,
    not size.* A rendered figure needs only tracked inputs and a few seconds, so
    it stays out.

    That is legitimate **exactly as long as every input is tracked**, which
    ``test_every_source_is_tracked_by_git`` asserts. This test pins the other
    half: that the outputs really are ignored on purpose. If someone starts
    committing PNGs, or stops ignoring them, that is a decision worth making
    deliberately rather than discovering.
    """
    ignored = subprocess.run(
        ["git", "check-ignore", "figures/complexity-landscape.png"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert ignored.returncode == 0, (
        "figures/*.png is no longer gitignored. That may be right, but it "
        "reverses the rule written in .gitignore and should be a deliberate "
        "change with the rationale updated."
    )
    assert not any(
        name.endswith(".png")
        for name in subprocess.run(
            ["git", "ls-files", "figures/"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.split()
    )


def test_a_builder_really_produces_a_file():
    """The actual guard against Phase 5's empty directory.

    Needs the ``figures`` extra, so it skips in CI and runs for whoever has it.
    Everything else here checks declarations; this one checks that a declaration
    turns into a PNG.

    It **writes into ``figures/``**, which is unusual for a test and is fine
    here: that directory is gitignored output, the file it writes is the one the
    builder would write anyway, and a build that cannot run is the failure this
    is looking for.
    """
    pytest.importorskip("matplotlib", reason="figures extra not installed")
    from figures.build import render

    figure = by_name("h6-perturbation-lattice.png")
    written = ROOT / render(figure)
    assert written.exists()
    assert written.stat().st_size > 20_000


def test_the_gallery_is_current():
    """Generated like docs/board-geometry.md — regenerate, never hand-edit."""
    from figures.build import GALLERY, gallery

    assert GALLERY.exists(), "run `python -m figures.build --gallery`"
    assert GALLERY.read_text() == gallery(), (
        "figures/README.md is stale — run `python -m figures.build --gallery`"
    )


def test_the_directory_holds_no_stray_images():
    """Every PNG present is in the manifest — a *subset*, never an equality.

    A fresh clone has none of them, because ``figures/*.png`` is gitignored and
    nothing has run the builders yet. Requiring equality would fail there and
    say nothing true. What must not happen is a rendered file nobody declared:
    an unlisted PNG has no recorded source and no caption, which is the state
    this directory's manifest exists to prevent.
    """
    rendered = {path.name for path in FIGURES_DIR.glob("*.png")}
    declared = {figure.name for figure in FIGURES}
    assert rendered <= declared, f"undeclared figures: {sorted(rendered - declared)}"


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
