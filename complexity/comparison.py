"""Where FLIPHEX sits among games whose complexity has been published.

Every external number in this module carries a source, a provenance grade and,
where the text was read locally, a quote; and where the ingested text is present
:func:`self_check` **opens the file and looks for that quote**, so a citation
that stops resolving fails a check rather than sitting in a docstring being
decorative. Numbers this project computed itself are graded separately again,
because an exact count and a sampled estimate should not look alike in a table.

``notes/sources/`` is gitignored, so a fresh clone has the bibliography and not
the texts. The bibliography is what is cited and it is complete on its own; the
quote check reports itself as unperformed there rather than passing silently.
See :data:`SOURCES_PRESENT`.

The definitions, and they are Allis's
-------------------------------------
Not van den Herik et al. (2002), which is the table most people cite: the terms
originate in the 1994 thesis, and the copy in ``notes/sources`` has them.

*State-space complexity* is "the number of legal game positions reachable from
the initial position of the game" -- and Allis adds, of symmetry, "We refrain
from such a refinement." So the shipped board's headline figure here is the
**reachability-corrected 4.886 x 10^17**, not the raw configuration count, and
the Z/2 mirror of adr-008 is *not* quotiented out. Note the tension: Allis's
*definition* is the reachable set, but his *computed numbers* are supersets
refined by Monte Carlo legality sampling, which is the uncorrected quantity. At
0.0079% apart it changes nothing here; it is recorded because on another game it
would.

*Game-tree complexity* is Definition 6.4: the size of the solution search tree
of the initial position, where the solution depth is the minimal full-width
depth that determines the game-theoretic value. Allis writes "number of nodes"
and then counts leaves in both his worked examples -- 600 grandchildren for the
chess sketch, "9! = 362880 terminal nodes" for tic-tac-toe. This module reports
**leaves** as the headline, to match the practice and the figures other papers
quote, and carries the node total beside it. They differ by a factor of 1.399 on
the shipped board.

Why FLIPHEX's exact count belongs in the same column
----------------------------------------------------
**FLIPHEX's solution depth is exactly 25**, and the argument has to be written
down because everything else rests on it. It is at most 25 because the board is
then full and the game over. It is not less: at ply 24 one cell is empty and the
mover holds one tile, and that tile's rotation decides which neighbours flip and
therefore the final colour count, which is the outcome. A full-width search to
depth 24 leaves that undetermined. So the solution search tree is the full-width
depth-25 tree, and its leaves are the distinct complete games -- which
``complexity.game_tree.games`` counts exactly rather than estimating.

So the exact figure is not a different quantity from the literature's. It is the
*same* quantity, computed instead of sampled. The asymmetry runs one way and the
table marks it: every external cell is an estimate that may be off by orders of
magnitude, and Connect Four is the proof -- Allis and Schaeffer both cite 10^14
where the exact enumeration is 4.53 x 10^12, a factor of 22.

What this table does not contain
--------------------------------
van den Herik et al. (2002) Table 1 is the canonical cross-game table and the
right thing to reproduce. It is **not reproduced here**, because two secondary
reproductions of it disagree by one to two in the exponent on four separate rows
-- Connect Four, checkers, chess and Go -- and that is not rounding. Those cells
are graded :data:`Provenance.ABSENT` with the disagreement recorded. Closing
them means opening the PDF; until then the table is short and true rather than
long and borrowed.

    python -m complexity.comparison
    python -m complexity.comparison --json
    python -m complexity.comparison --gaps
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from enum import StrEnum
from math import log10
from pathlib import Path

from complexity.game_tree import games, prefixes
from complexity.state_space import profile
from fliphex.variant import Arm, Variant

_ROOT = Path(__file__).resolve().parent.parent
_SOURCES = _ROOT / "notes" / "sources"


class Provenance(StrEnum):
    """How much weight a figure can carry."""

    #: Computed in this repository, in closed form, with tests.
    EXACT = "exact"
    #: Quoted from a primary source held in ``notes/sources``, checked by
    #: :func:`self_check` against the file.
    VERIFIED = "verified"
    #: From a named secondary source that is not held here and was not opened.
    REPORTED = "reported"
    #: A widely repeated figure this project believes is wrong, with the
    #: disproof attached.
    REFUTED = "refuted"
    #: No figure this project is willing to print.
    ABSENT = "absent"


@dataclass(frozen=True, slots=True)
class Figure:
    """One cell of the table."""

    provenance: Provenance
    #: Base-10 logarithm. ``None`` for ABSENT and REFUTED.
    log10: float | None = None
    #: The exact integer, when there is one.
    exact: int | None = None
    source: str = ""
    #: For VERIFIED: a path under ``notes/sources``. Otherwise free text.
    locator: str = ""
    #: For VERIFIED: text that must occur in the file at ``locator``.
    quote: str = ""
    note: str = ""

    @property
    def printable(self) -> str:
        if self.log10 is None:
            return "—"
        return f"10^{self.log10:.2f}"

    def as_dict(self) -> dict[str, object]:
        return {
            "provenance": self.provenance.value,
            "log10": self.log10,
            "exact": self.exact,
            "source": self.source,
            "locator": self.locator,
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class Row:
    """One game."""

    game: str
    state_space: Figure
    game_tree: Figure
    #: One of Allis's three terms, or "unsolved".
    solved: str
    solved_source: str = ""
    solved_note: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "game": self.game,
            "state_space": self.state_space.as_dict(),
            "game_tree": self.game_tree.as_dict(),
            "solved": self.solved,
            "solved_source": self.solved_source,
            "solved_note": self.solved_note,
        }


# -- sources ----------------------------------------------------------------

#: Full bibliographic entries, keyed by the short form used in the table.
SOURCES: dict[str, str] = {
    "Allis 1994": (
        "V. Allis, *Searching for Solutions in Games and Artificial "
        "Intelligence*, PhD thesis, University of Limburg, Maastricht, 1994. "
        "ISBN 90-900748-8-0. Sections 1.5 (solved-game taxonomy) and 6.2 "
        "(complexity definitions). Held in notes/sources."
    ),
    "Takizawa 2023": (
        "H. Takizawa, *Othello is Solved*, arXiv:2310.19387, 2023. "
        "Held in notes/sources."
    ),
    "Schaeffer 2007": (
        "J. Schaeffer, N. Burch, Y. Björnsson, A. Kishimoto, M. Müller, "
        "R. Lake, P. Lu, S. Sutphen, 'Checkers Is Solved', *Science* "
        "317(5844):1518–1522, 2007. Held in notes/sources."
    ),
    "van den Herik 2002": (
        "H.J. van den Herik, J.W.H.M. Uiterwijk, J. van Rijswijck, 'Games "
        "solved: Now and in the future', *Artificial Intelligence* "
        "134(1–2):277–311, 2002. DOI 10.1016/S0004-3702(01)00152-7. "
        "**Not held here.** Table 1 is the canonical cross-game table; this "
        "module cites no figure from it, because the reproductions disagree."
    ),
    "Feinstein 1993": (
        "J.F. Feinstein, '6x6 Othello', Usenet posting, 8 June 1993, archived "
        "by D. Eppstein at ics.uci.edu/~eppstein/cgt/othello.html. **Not held "
        "here**, and not peer-reviewed."
    ),
    "Tromp": (
        "J. Tromp, 'John's Connect Four Playground', tromp.github.io/c4/c4.html; "
        "count independently confirmed by S. Edelkamp & P. Kissmann, 'Symbolic "
        "Classification of General Two-Player Games', KI 2008. **Not held here.**"
    ),
    "Henderson 2009": (
        "P. Henderson, B. Arneson, R.B. Hayward, 'Solving 8×8 Hex', IJCAI 2009. "
        "**Not held here.**"
    ),
    "this project": (
        "Computed by complexity/state_space.py and complexity/game_tree.py, "
        "verified against the engine's own move generator. See "
        "notes/phase6-complexity-log.md."
    ),
}

_ALLIS_COMPLEXITY = (
    "allis-1994-searching-for-solutions/sections/11-which-games-will-survive.md"
)
_ALLIS_TAXONOMY = "allis-1994-searching-for-solutions/sections/06-introduction.md"
_TAKIZAWA_INTRO = "takizawa-2023-othello-is-solved/sections/02-1-introduction.md"
_SCHAEFFER_BODY = "schaeffer-2007-checkers-is-solved/sections/02-checkers-is-solved.md"


#: Allis's three terms, quoted so the table uses them correctly.
TAXONOMY: dict[str, str] = {
    "ultra-weakly solved": (
        "For the initial position(s), the game-theoretic value has been determined."
    ),
    "weakly solved": (
        "For the initial position(s), a strategy has been determined to obtain "
        "at least the game-theoretic value of the game, for both players, "
        "under reasonable resources."
    ),
    "strongly solved": (
        "For all legal positions, a strategy has been determined to obtain the "
        "game-theoretic value of the position, for both players, under "
        "reasonable resources."
    ),
}


# -- the disproof, executable rather than asserted --------------------------


def reversi_6x6_ceiling() -> tuple[int, float]:
    """A hard upper bound on 6×6 Reversi configurations, and its log.

    Thirty-six cells, three states each -- black, white, empty -- before any
    legality constraint. Nothing about Reversi can exceed it.
    """
    ceiling = 3**36
    return ceiling, log10(ceiling)


#: The figure this module refuses to print, and by how much it fails.
REVERSI_6X6_CLAIM = 1e20


def reversi_6x6_overshoot() -> float:
    """How many times the commonly repeated 10^20 exceeds what is possible."""
    ceiling, _ = reversi_6x6_ceiling()
    return REVERSI_6X6_CLAIM / ceiling


# -- FLIPHEX's own rows -----------------------------------------------------


#: Boards this project solved exhaustively, keyed by ``(n_cols, n_rows)``, with
#: Allis's term and what earned it. A board absent from this map is unsolved.
#:
#: **Declared, not derived.** The layer files carrying these solutions live in
#: ``data/checkpoints/``, which is gitignored, so reading the status off disk
#: would make a fresh clone print a different table from the machine that ran
#: the sweeps. The table is the artifact; the bytes are not.
#:
#: Both boards earn *strongly* rather than *weakly*: a retrograde sweep computes
#: the value of every configuration in every layer, and
#: ``agents.solver_agent.SolverAgent`` turns that into a strategy for any
#: position by lookup — which is exactly Allis's condition, "for all legal
#: positions".
SOLVED_BOARDS: dict[tuple[int, int], tuple[str, str]] = {
    (3, 3): (
        "strongly solved",
        "EXP-001, both arms, termination: exhausted. 711,963 configurations by "
        "retrograde sweep and independently by unpruned forward alpha-beta. The "
        "two agree on 604,347 positions, which is every position the forward "
        "method reaches — the other 15.1% are configurations no game reaches at "
        "all. The only board here with two independent witnesses. P1 wins.",
    ),
    (5, 3): (
        "strongly solved",
        "EXP-002, both arms, termination: exhausted. 1.75e10 configurations by "
        "retrograde sweep, adr-010 V0–V6 with coverage stated rather than "
        "assumed (V4 has no search evidence at t = 0..5, V6 covers t >= 2). One "
        "method, not two. P1 wins.",
    ),
}


def solved_status(variant: Variant) -> tuple[str, str]:
    """Allis's term for this board, and the note recording what earned it."""
    return SOLVED_BOARDS.get(
        (variant.n_cols, variant.n_rows),
        ("unsolved", "not solved on any axis; no exhaustive solve is reachable"),
    )


def fliphex_row(variant: Variant) -> Row:
    """Build FLIPHEX's row from the modules that compute it.

    The state-space figure is the **reachable** one, because that is what
    Allis's definition says. The game-tree figure is leaves, because that is
    what his practice counts and what other papers quote.
    """
    space = profile(variant)
    leaves = games(variant)
    nodes = sum(prefixes(variant, t) for t in range(variant.n_cells + 1))
    solved, solved_note = solved_status(variant)
    return Row(
        game=f"FLIPHEX {variant.n_cols}×{variant.n_rows}",
        state_space=Figure(
            provenance=Provenance.EXACT,
            log10=log10(space.reachable),
            exact=space.reachable,
            source="this project",
            locator="complexity/state_space.py",
            note=(
                f"reachable; the invariant-consistent superset is "
                f"{space.configurations:.4g}, {space.orphan_fraction:.4%} larger"
            ),
        ),
        game_tree=Figure(
            provenance=Provenance.EXACT,
            log10=log10(leaves),
            exact=leaves,
            source="this project",
            locator="complexity/game_tree.py",
            note=(
                f"leaves of the full-width depth-{variant.n_cells} tree, "
                f"counted not estimated; all nodes would be 10^{log10(nodes):.2f}"
            ),
        ),
        solved=solved,
        solved_source="this project",
        solved_note=solved_note,
    )


# -- the external rows ------------------------------------------------------


def external_rows() -> list[Row]:
    """Games with published figures, graded by what this project checked."""
    return [
        Row(
            game="Othello 8×8",
            state_space=Figure(
                provenance=Provenance.VERIFIED,
                log10=28.0,
                source="Takizawa 2023",
                locator=_TAKIZAWA_INTRO,
                quote=(
                    "the total number of possible board positions was "
                    "also estimated to be around 10"
                ),
                note="Takizawa's §1, attributing the estimate to Allis 1994",
            ),
            game_tree=Figure(
                provenance=Provenance.VERIFIED,
                log10=58.0,
                source="Takizawa 2023",
                locator=_TAKIZAWA_INTRO,
                quote=(
                    "the total number of possible game records can be "
                    "estimated to be around 10"
                ),
                note="10 average moves over 58 ply; an estimate, and Takizawa "
                "reports the real search was 'far less than predicted'",
            ),
            solved="weakly solved",
            solved_source="Takizawa 2023",
            solved_note="draw",
        ),
        Row(
            game="Reversi 6×6",
            state_space=Figure(
                provenance=Provenance.REFUTED,
                source="—",
                locator="complexity/comparison.py:reversi_6x6_ceiling",
                note=(
                    "the widely repeated ~10^20 is impossible: 3^36 = 1.501e17 "
                    "bounds it before any legality constraint, so the claim "
                    "overshoots by 666×. No primary source for it was found"
                ),
            ),
            game_tree=Figure(
                provenance=Provenance.ABSENT,
                source="—",
                note="no sourced figure found",
            ),
            solved="strongly solved",
            solved_source="Feinstein 1993",
            solved_note=(
                "second player wins 20–16; weakly solved 1993 in ~1.5 weeks on "
                "a 1993 workstation, later strongly solved. The effort, not a "
                "10^x figure, is what 'comparable to small Reversi' should mean"
            ),
        ),
        Row(
            game="Checkers 8×8",
            state_space=Figure(
                provenance=Provenance.VERIFIED,
                log10=log10(5e20),
                source="Schaeffer 2007",
                locator=_SCHAEFFER_BODY,
                quote="moderate space complexity (5 × 10",
                note="the decisive comparison: solved despite a larger state "
                "space than FLIPHEX's",
            ),
            game_tree=Figure(
                provenance=Provenance.ABSENT,
                source="van den Herik 2002",
                note="10^40 is commonly cited to Table 1; reproductions disagree",
            ),
            solved="weakly solved",
            solved_source="Schaeffer 2007",
            solved_note="draw, 2007",
        ),
        Row(
            game="Connect Four",
            state_space=Figure(
                provenance=Provenance.REPORTED,
                log10=log10(4_531_985_219_092),
                exact=4_531_985_219_092,
                source="Tromp",
                locator="tromp.github.io/c4/c4.html",
                note=(
                    "exactly 4,531,985,219,092 by enumeration. Allis 1994 and "
                    "Schaeffer 2007 both cite 10^14 — the estimate is 22× high, "
                    "which is why this table separates exact from estimated"
                ),
            ),
            game_tree=Figure(
                provenance=Provenance.ABSENT,
                source="van den Herik 2002",
                note="10^21 is commonly cited to Table 1; reproductions disagree",
            ),
            solved="weakly solved",
            solved_source="Allis 1994",
            solved_note="first player wins; Allen and Allis independently, 1988",
        ),
        Row(
            game="Nine Men's Morris",
            state_space=Figure(
                provenance=Provenance.VERIFIED,
                log10=11.0,
                source="Schaeffer 2007",
                locator=_SCHAEFFER_BODY,
                quote="Nine Men's Morris, size 10",
                note="Schaeffer citing Gasser 1996",
            ),
            game_tree=Figure(
                provenance=Provenance.ABSENT,
                source="van den Herik 2002",
                note="10^50 is commonly cited; a striking contrast with the "
                "10^11 state space, and worth verifying before use",
            ),
            solved="strongly solved",
            solved_source="Schaeffer 2007",
            solved_note="draw; Gasser 1996",
        ),
        Row(
            game="Awari",
            state_space=Figure(
                provenance=Provenance.VERIFIED,
                log10=12.0,
                source="Schaeffer 2007",
                locator=_SCHAEFFER_BODY,
                quote="Awari, size 10",
                note="Schaeffer citing Romein & Bal 2003",
            ),
            game_tree=Figure(
                provenance=Provenance.ABSENT,
                source="van den Herik 2002",
                note="no verified figure",
            ),
            solved="strongly solved",
            solved_source="Schaeffer 2007",
            solved_note="draw; Romein & Bal 2003",
        ),
        Row(
            game="Chess",
            state_space=Figure(
                provenance=Provenance.VERIFIED,
                log10=45.0,
                source="Schaeffer 2007",
                locator=_SCHAEFFER_BODY,
                quote="the number of positions in chess (somewhere in the 10",
                note=(
                    "**the source gives a range, 10^40–10^50, not a point.** "
                    "The 10^45 printed here is this table's midpoint and is not "
                    "a figure anyone published; the range is the citable result"
                ),
            ),
            game_tree=Figure(
                provenance=Provenance.ABSENT,
                source="—",
                note="Shannon's 10^120 is a different construction; not cited here",
            ),
            solved="unsolved",
            solved_source="Schaeffer 2007",
            solved_note="'will remain unsolved for a long time'",
        ),
        Row(
            game="Hex 11×11",
            state_space=Figure(
                provenance=Provenance.ABSENT,
                source="van den Herik 2002",
                note="10^57 is commonly cited to Table 1; not verified",
            ),
            game_tree=Figure(
                provenance=Provenance.ABSENT,
                source="van den Herik 2002",
                note="10^98 is commonly cited to Table 1; not verified",
            ),
            solved="ultra-weakly solved",
            solved_source="Henderson 2009",
            solved_note=(
                "ultra-weakly for all n by strategy stealing (Nash); weakly "
                "solved to 8×8 in 2009. FLIPHEX has no such argument — its "
                "mirror preserves the mover (adr-008), which is why H1 had to "
                "be settled by computation"
            ),
        ),
    ]


def table() -> list[Row]:
    """FLIPHEX's boards followed by the published games, smallest first."""
    fliphex = [
        fliphex_row(Variant(cols, rows, Arm.H1))
        for cols, rows in ((3, 3), (5, 3), (5, 5))
    ]
    rows = fliphex + external_rows()
    return sorted(
        rows,
        key=lambda row: (
            row.state_space.log10 if row.state_space.log10 is not None else 1e9
        ),
    )


# -- checks -----------------------------------------------------------------


#: Whether the ingested source texts are present in this working copy.
#:
#: ``notes/sources/`` is **gitignored**: it holds extracted text of papers this
#: project does not own, so it never leaves the machine it was ingested on. A
#: fresh clone and CI therefore have the bibliography and not the texts.
#:
#: The bibliography in :data:`SOURCES` is what this module actually cites --
#: author, year, title, DOI -- and it is tracked and complete on its own. The
#: local path in each figure's ``locator`` is an *extra*: where the text
#: happens to be present, :func:`self_check` opens it and confirms the quote.
#: Where it is not, the citation stands on the bibliography and the check
#: reports itself as unperformed rather than passing silently.
SOURCES_PRESENT: bool = _SOURCES.is_dir()


def citation_status() -> tuple[int, int]:
    """``(checked, unchecked)`` quotes, given what this machine holds."""
    verified = sum(
        1
        for row in table()
        for figure in (row.state_space, row.game_tree)
        if figure.provenance is Provenance.VERIFIED
    )
    return (verified, 0) if SOURCES_PRESENT else (0, verified)


def self_check() -> list[str]:
    """Check the table's internal consistency, and its quotes where possible.

    Always:

    1. every ``source`` key appears in :data:`SOURCES`, every solved status is
       one of Allis's three terms or "unsolved", and a cell's grade matches
       whether it carries a figure;
    2. the refutation of the 6×6 Reversi figure actually holds.

    And where ``notes/sources`` is present, which is not a fresh clone or CI:

    3. every :data:`Provenance.VERIFIED` figure's quote occurs in the file its
       ``locator`` names. See :data:`SOURCES_PRESENT` for why this one is
       conditional; a missing text is not a failure, but a text that is present
       and no longer contains the quote is.
    """
    problems: list[str] = []
    for row in table():
        for axis, figure in (
            ("state space", row.state_space),
            ("game tree", row.game_tree),
        ):
            if figure.source and figure.source not in SOURCES and figure.source != "—":
                problems.append(f"{row.game} {axis}: unknown source {figure.source!r}")
            if figure.provenance is Provenance.VERIFIED:
                if not figure.quote:
                    problems.append(f"{row.game} {axis}: verified with no quote")
                path = _SOURCES / figure.locator
                if path.exists() and figure.quote not in path.read_text():
                    problems.append(
                        f"{row.game} {axis}: quote not found in {figure.locator}"
                    )
                elif SOURCES_PRESENT and not path.exists():
                    problems.append(f"{row.game} {axis}: missing source {path}")
            graded = figure.provenance in (Provenance.EXACT, Provenance.VERIFIED)
            if graded and figure.log10 is None:
                problems.append(f"{row.game} {axis}: graded but has no figure")
            ungraded = figure.provenance in (Provenance.ABSENT, Provenance.REFUTED)
            if ungraded and figure.log10 is not None:
                problems.append(f"{row.game} {axis}: ungraded but prints a figure")
        if row.solved not in TAXONOMY and row.solved != "unsolved":
            problems.append(f"{row.game}: {row.solved!r} is not one of Allis's terms")
        if row.solved_source and row.solved_source not in SOURCES:
            problems.append(f"{row.game}: unknown solved source {row.solved_source!r}")

    ceiling, _ = reversi_6x6_ceiling()
    if ceiling >= REVERSI_6X6_CLAIM:
        problems.append("the 6×6 Reversi refutation no longer holds")

    taxonomy_file = _SOURCES / _ALLIS_TAXONOMY
    if taxonomy_file.exists():
        text = taxonomy_file.read_text()
        problems += [
            f"taxonomy: {term!r} not found in Allis §1.5"
            for term, quote in TAXONOMY.items()
            if quote not in text
        ]

    definitions = _SOURCES / _ALLIS_COMPLEXITY
    if definitions.exists():
        text = definitions.read_text()
        problems += [
            f"definitions: {quote!r} not found in Allis §6.2"
            for quote in (
                "game positions reachable from the initial position of the game",
                "We refrain from such a refinement.",
                "its game-tree complexity would be 600",
            )
            if quote not in text
        ]
    return problems


def gaps() -> list[tuple[str, str, str]]:
    """Every cell this module declines to fill, and why."""
    out = []
    for row in table():
        for axis, figure in (
            ("state space", row.state_space),
            ("game tree", row.game_tree),
        ):
            if figure.provenance in (Provenance.ABSENT, Provenance.REFUTED):
                out.append((row.game, axis, figure.note))
    return out


def _render() -> None:
    rows = table()
    print("\n  === Cross-game complexity, log10 ===\n")
    print("    game                  state space   game tree   grade       solved")
    own = False
    for row in rows:
        grade = f"{row.state_space.provenance.value}/{row.game_tree.provenance.value}"
        # A solution this project ran is not the same kind of fact as one the
        # literature reports, and the column would otherwise print them
        # identically. The asymmetry is in `solved_source`; the marker is what
        # makes it visible in the artifact people actually read.
        mark = row.solved_source == "this project" and row.solved != "unsolved"
        own = own or mark
        print(
            f"    {row.game:<21} {row.state_space.printable:>11} "
            f"{row.game_tree.printable:>11}   {grade:<19} "
            f"{row.solved}{'*' if mark else ''}"
        )
    print()
    print("    exact = counted here;  verified = quote resolved in notes/sources;")
    print("    reported = named source not held;  absent/refuted = not printed.")
    if own:
        print("    * solved by this project's own runs, verified under adr-010 and")
        print("      not independently reimplemented.")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--json", action="store_true")
    p.add_argument("--gaps", action="store_true", help="what is missing, and why")
    p.add_argument("--sources", action="store_true")
    args = p.parse_args()

    problems = self_check()
    if problems:
        print("  SELF-CHECK FAILED — a citation did not resolve")
        for problem in problems:
            print(f"    {problem}")
        return 1

    if args.json:
        print(json.dumps([row.as_dict() for row in table()], indent=2))
        return 0
    if args.gaps:
        print("\n  === Cells this table declines to fill ===\n")
        for game, axis, note in gaps():
            print(f"    {game} — {axis}")
            print(f"      {note}")
        return 0
    if args.sources:
        print()
        for key, entry in sorted(SOURCES.items()):
            print(f"    {key}\n      {entry}\n")
        return 0

    _render()
    checked, unchecked = citation_status()
    if unchecked:
        print(
            f"\n    self-check ............ ok, but {unchecked} quotes were NOT "
            f"opened:\n                            notes/sources/ is gitignored and "
            f"absent here.\n                            The bibliography stands; "
            f"--sources prints it."
        )
    else:
        print(f"\n    self-check ............ ok ({checked} quotes resolved in source)")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
