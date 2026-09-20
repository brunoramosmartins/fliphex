"""Tests for scripts/build_web.py — the bundle the browser runs.

``web/payload.json`` is generated, so it gets the contract
``docs/board-geometry.md`` has: a test asserts it is current rather than
trusting that someone reran the builder.
"""

import ast
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location(
    "build_web", ROOT / "scripts" / "build_web.py"
)
build_web = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_web)


def test_the_committed_payload_is_current():
    """The same contract the generated docs carry: regenerate, then compare."""
    assert build_web.OUT.exists(), "run python scripts/build_web.py"
    assert build_web.OUT.read_text() == build_web.rendered(build_web.build()), (
        "web/payload.json is stale — run python scripts/build_web.py"
    )


def test_the_bundle_carries_no_third_party_import():
    """The property adr-013 rests on. torch has no WebAssembly build."""
    assert build_web.verify(build_web.sources()) == []


def test_the_learner_agent_is_not_shipped():
    """It imports torch, and the glob over agents/ would otherwise catch it."""
    assert "agents/az_agent.py" not in build_web.sources()
    assert "agents/az_agent.py" in build_web.EXCLUDE


def test_the_bridge_and_the_seats_are_shipped():
    payload = build_web.sources()
    assert "ui/session.py" in payload
    assert "ui/seats.py" in payload


def test_the_cli_is_not_shipped_because_it_reads_stdin():
    assert "ui/cli.py" not in build_web.sources()


def test_every_shipped_package_is_importable():
    payload = build_web.sources()
    for package in build_web.PACKAGES:
        assert f"{package}/__init__.py" in payload


def test_every_shipped_module_parses():
    for relative, source in build_web.sources().items():
        ast.parse(source, filename=relative)


def test_the_payload_is_valid_json_and_keyed_by_path():
    payload = json.loads(build_web.OUT.read_text())
    assert all("/" in key and key.endswith(".py") for key in payload)
    assert payload == build_web.sources()


# -- the import classifier -----------------------------------------------------


def test_a_module_level_import_is_executed():
    executed, deferred = build_web.imports_of("import torch\n")
    assert executed == {"torch"} and deferred == set()


def test_a_function_local_import_is_deferred():
    executed, deferred = build_web.imports_of("def f():\n    import torch\n")
    assert executed == set() and deferred == {"torch"}


def test_a_type_checking_import_is_deferred():
    source = "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import torch\n"
    executed, deferred = build_web.imports_of(source)
    assert "torch" in deferred and "torch" not in executed


def test_an_import_that_is_both_counts_as_executed():
    """The strict reading: if any path runs it at import time, it is required."""
    executed, deferred = build_web.imports_of(
        "import torch\ndef f():\n    import torch\n"
    )
    assert executed == {"torch"} and deferred == set()


def test_seats_defers_torch_rather_than_executing_it():
    """The deferral the whole browser build depends on."""
    executed, deferred = build_web.imports_of((ROOT / "ui" / "seats.py").read_text())
    assert "torch" not in executed
    assert {"az", "torch"} <= deferred


def test_an_undeclared_deferral_is_refused():
    problems = build_web.verify({"x.py": "def f():\n    import pandas\n"})
    assert any("pandas" in p and "DEFERRED_ROOTS" in p for p in problems)


def test_an_undeclared_module_level_import_is_refused():
    problems = build_web.verify({"x.py": "import pandas\n"})
    assert any("pandas" in p and "module level" in p for p in problems)


def test_a_package_without_an_init_is_refused(monkeypatch):
    monkeypatch.setattr(build_web, "PACKAGES", ("nonesuch",))
    assert any("not importable" in p for p in build_web.verify({}))


def test_build_refuses_rather_than_writing_a_broken_bundle(monkeypatch):
    monkeypatch.setattr(build_web, "sources", lambda: {"x.py": "import pandas\n"})
    with pytest.raises(SystemExit, match="BUNDLE REFUSED"):
        build_web.build()
