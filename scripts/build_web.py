"""Bundle the Python the browser needs into one file. Generated — do not edit.

The browser build runs the **real** engine (adr-013 clause 2), which means the
engine's source has to reach the page. This writes every module it needs into a
single ``web/payload.json`` so the page makes one request rather than twenty,
and so a static host with no build step can serve it.

    python scripts/build_web.py            # write web/payload.json
    python scripts/build_web.py --check    # fail if it is stale

``--check`` is the same contract ``scripts/build_docs.py`` has: the file is
generated, so CI verifies the working tree is clean after a rebuild rather than
trusting that someone remembered.

Why a manifest rather than a wildcard
-------------------------------------
Every module is listed by name. A wildcard over ``fliphex/`` would work today
and would silently start shipping whatever lands there tomorrow — including, one
day, something that imports torch, which has no WebAssembly build and would fail
in the browser and nowhere else. :func:`verify` asserts the listed set is
closed under import and free of third-party dependencies, so the manifest is
checked rather than merely declared.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

# Run as `python scripts/build_web.py`, so sys.path[0] is scripts/ rather than
# the repository root. The convention the other scripts here use.
sys.path.insert(0, str(ROOT))

from ui.theme import LIGHT, stylesheet  # noqa: E402  (after the sys.path insert)

OUT = ROOT / "web" / "payload.json"

#: The boards the page's selector offers, and the file it reads them from
#: *before* Pyodide starts. EXP-019 measured boot at ~3.9 s and found it
#: compute-bound, so the board can be drawn from this in ~100 ms and made live
#: later — the split render adr-013 asked for and EXP-019's rule 1 decided.
GEOMETRY_OUT = ROOT / "web" / "geometry.json"
PAGE_BOARDS = ((5, 5), (5, 3), (3, 3))

#: The colour tokens, generated from ``ui/theme.py`` — the same module the
#: pygame window reads. The palette used to be hand-copied into both
#: interfaces under comments claiming they matched; generating it is what makes
#: the claim checkable, exactly as ``geometry.json`` does for the layout.
THEME_OUT = ROOT / "web" / "theme.css"

#: Packages shipped whole. All three are pure standard library — the property
#: adr-013 rests on, and the one :func:`verify` re-checks on every build.
PACKAGES = ("fliphex", "agents", "solver")

#: Individual modules, where shipping the package would pull in more than the
#: page needs. ``ui/cli.py`` is deliberately absent: it reads stdin.
MODULES = ("ui/__init__.py", "ui/seats.py", "ui/session.py")

#: Shipped by the glob above but excluded by name. ``agents/az_agent.py`` needs
#: torch, which has no WebAssembly build; adr-013 clause 4 refuses the learner
#: seat in the browser at the trained budget anyway, and no numpy forward pass
#: exists yet. Note that ``agents/__init__.py`` does **not** import it, which is
#: what makes excluding one file from a package safe here.
EXCLUDE = frozenset({"agents/az_agent.py"})

#: Imports allowed to appear inside a function body or under ``TYPE_CHECKING``,
#: because they are never executed in the browser. ``ui.seats.build_seat`` holds
#: exactly one, and it fires only for a seat the page does not offer. A test in
#: ``tests/test_seats.py`` asserts the deferral holds at runtime; this asserts
#: the set of deferrals does not quietly grow.
DEFERRED_ROOTS = frozenset({"az", "torch"})

#: Import roots the page may rely on. Anything else is a bug in the manifest.
ALLOWED_ROOTS = frozenset(
    {
        "__future__",
        "abc",
        "argparse",
        "array",
        "collections",
        "dataclasses",
        "enum",
        "itertools",
        "json",
        "math",
        "os",
        "pathlib",
        "pickle",
        "random",
        "statistics",
        "sys",
        "time",
        "typing",
        "warnings",
        *PACKAGES,
        "ui",
    }
)


def sources() -> dict[str, str]:
    """Return ``{repository-relative path: source}`` for everything shipped."""
    payload: dict[str, str] = {}
    for package in PACKAGES:
        for path in sorted((ROOT / package).glob("*.py")):
            relative = f"{package}/{path.name}"
            if relative not in EXCLUDE:
                payload[relative] = path.read_text()
    for relative in MODULES:
        payload[relative] = (ROOT / relative).read_text()
    return payload


def _roots(node: ast.Import | ast.ImportFrom) -> set[str]:
    if isinstance(node, ast.Import):
        return {alias.name.split(".")[0] for alias in node.names}
    if node.level == 0 and node.module:
        return {node.module.split(".")[0]}
    return set()


def _is_type_checking_guard(node: ast.AST) -> bool:
    """Whether ``node`` is ``if TYPE_CHECKING:`` — true to the checker, false at run."""
    if not isinstance(node, ast.If):
        return False
    test = node.test
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


def imports_of(source: str) -> tuple[set[str], set[str]]:
    """Return ``(executed, deferred)`` import roots, read from the AST.

    An import inside a function body, or under a ``TYPE_CHECKING`` guard, does
    not run when the module is imported — so the browser does not have to carry
    it. Treating the two alike would either ban a legitimate deferral or wave
    through a real dependency, and this bundle depends on telling them apart:
    ``ui/seats.py`` defers torch *on purpose*, and that deferral is the reason a
    page can import it at all.
    """
    executed: set[str] = set()
    deferred: set[str] = set()

    def walk(node: ast.AST, *, live: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Import | ast.ImportFrom):
                (executed if live else deferred).update(_roots(child))
            elif isinstance(
                child, ast.FunctionDef | ast.AsyncFunctionDef
            ) or _is_type_checking_guard(child):
                walk(child, live=False)
            else:
                walk(child, live=live)

    walk(ast.parse(source), live=True)
    return executed, deferred - executed


def verify(payload: dict[str, str]) -> list[str]:
    """Check the bundle is closed and third-party free. Returns the problems."""
    problems: list[str] = []
    for relative, source in sorted(payload.items()):
        executed, deferred = imports_of(source)
        for root in sorted(executed - ALLOWED_ROOTS):
            problems.append(
                f"{relative}: imports {root!r} at module level, which the browser "
                f"bundle does not carry — add it to ALLOWED_ROOTS only if it is "
                f"standard library"
            )
        for root in sorted(deferred - ALLOWED_ROOTS - DEFERRED_ROOTS):
            problems.append(
                f"{relative}: defers an import of {root!r} that nothing declares. "
                f"A deferred import still runs if its code path runs — list it in "
                f"DEFERRED_ROOTS and say why, or remove it"
            )
    for package in PACKAGES:
        if f"{package}/__init__.py" not in payload:
            problems.append(f"{package}: no __init__.py, so it is not importable")
    return problems


def build() -> dict[str, str]:
    """The payload, verified. Raises rather than writing a broken bundle."""
    payload = sources()
    problems = verify(payload)
    if problems:
        raise SystemExit("  BUNDLE REFUSED\n" + "\n".join(f"    {p}" for p in problems))
    return payload


def geometry() -> dict[str, Any]:
    """Cell centres per board, generated from the engine.

    The page must not invent a second geometry (adr-013), and drawing before
    Python starts would otherwise force exactly that. This writes what
    :func:`ui.session.layout` returns, so the early board and the live board are
    the same numbers — and ``tests/test_build_web.py`` asserts that rather than
    trusting it.
    """
    from fliphex.variant import Variant
    from ui.session import layout

    return {
        f"{cols}x{rows}": {
            "n_cols": cols,
            "n_rows": rows,
            "n_cells": cols * rows,
            "cells": layout(Variant(cols, rows).board()),
        }
        for cols, rows in PAGE_BOARDS
    }


def rendered(payload: dict[str, str]) -> str:
    """Serialised deterministically, so ``--check`` compares content not order."""
    return json.dumps(payload, sort_keys=True, indent=1, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="verify the bundle is current and stop"
    )
    args = parser.parse_args(argv)

    payload = build()
    text = rendered(payload)
    total = sum(len(s) for s in payload.values())

    shapes = json.dumps(geometry(), sort_keys=True, indent=1) + "\n"
    theme = stylesheet()

    if args.check:
        stale = [
            path.name
            for path, wanted in (
                (OUT, text),
                (GEOMETRY_OUT, shapes),
                (THEME_OUT, theme),
            )
            if not path.exists() or path.read_text() != wanted
        ]
        if stale:
            print(f"  stale: {', '.join(stale)} — run python scripts/build_web.py")
            return 1
        print(f"  payload current — {len(payload)} modules, {total:,} bytes")
        print(f"  geometry current — {len(geometry())} boards")
        print(f"  theme current — {len(LIGHT)} colour tokens")
        return 0

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(text)
    GEOMETRY_OUT.write_text(shapes)
    THEME_OUT.write_text(theme)
    print(f"  wrote {OUT.relative_to(ROOT)} — {len(payload)} modules, {total:,} bytes")
    print(f"  wrote {GEOMETRY_OUT.relative_to(ROOT)} — {len(geometry())} boards")
    print(f"  wrote {THEME_OUT.relative_to(ROOT)} — {len(LIGHT)} colour tokens")
    return 0


if __name__ == "__main__":
    sys.exit(main())
