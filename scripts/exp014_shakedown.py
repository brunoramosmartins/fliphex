"""EXP-014 — pipeline shakedown on the adopted architecture.

Registered in ``experiments/registry.md`` on 2026-09-04, before this file
existed. Read the entry first.

**This is a pre-flight check on the instrument, not evidence about the game.** No
number it produces may be quoted about H1, H2 or H3, and no architecture or
hyperparameter decision may be taken from it. It exists because ``az/loop.py``
was written on 2026-09-04, the head it runs was adopted on 2026-09-04, and the
alternative to running it is committing ≈60 hours to a pipeline whose first
end-to-end execution would be that run.

The four checks
---------------
============ ============================================================
C1           three generations complete, with a checkpoint and three
             history rows
C2           eight spawned workers produce a full generation with the
             conditioned head, which was impossible before 2026-09-04
C3           both gates return a decision with an interval and a seat split
C4           a run killed with ``SIGKILL`` mid-gate resumes to **byte-equal**
             final weights
============ ============================================================

Any failure stops the 60-hour run. The rule is one-directional: passing removes
an objection, it does not license anything.

Why C4 needs a real kill
------------------------
``tests/test_az_loop.py`` simulates interruption by calling ``run`` twice. That
cannot reach a **torn write** — a process killed between writing the payload and
writing the manifest, or partway through either. ``atomic_write`` and
"manifest last" exist for precisely that and have never been exercised by an
actual kill.

So the child runs in its own process and the parent kills it with signal 9 while
the first gate is in flight. The parent knows when that is by polling the
checkpoint manifest for a non-zero ``gate_games``, which is also, incidentally,
the only positive confirmation that the mid-gate checkpoint path runs at all.

Registered caveat, repeated here: **C4 tests durability, not determinism.** It
compares two runs of the same code, so a defect present in both cancels out —
the loop's unit tests have that weakness and it was measured, not assumed.

The one measurement
-------------------
Composed throughput, with the network in the loop. R8 records that its 4.31×
speedup and the ~705 games/hour behind the 59.6-hour budget were measured
**engine-only, with torch not competing for those cores**. This closes that
residual with the real number.

Acting on it is not circular — it is cost, not strength — but the entry fixes the
boundary: workers, games and generations may change by amendment; **the five
seeds may not**, except in an amendment that states the power consequence.

Usage::

    .venv/bin/python scripts/exp014_shakedown.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch  # noqa: E402

from az.checkpoint import Checkpoint  # noqa: E402
from az.loop import LoopConfig, run  # noqa: E402
from az.network import ConvRotationNet  # noqa: E402
from fliphex.variant import Arm, Variant  # noqa: E402

# -- pinned by the registry ---------------------------------------------------
#
# These are argparse defaults rather than constants, and the parent forwards
# whatever it was given to the child verbatim. The scale has to reach the child
# process somehow, and module globals do not: a child is a fresh interpreter and
# sees the defaults, so a "smaller run for debugging" would silently be the full
# one. Making the scale explicit is also what lets this be smoked at toy size.

BOARDS = {"5x5": Variant(5, 5, Arm("h1")), "3x3": Variant(3, 3, Arm("h1"))}

REGISTERED = {
    "board": "5x5",
    "seed": 1,
    "generations": 3,
    "games": 20,
    "simulations": 400,
    "steps": 400,
    "batch_size": 64,
    "buffer_capacity": 20_000,
    "gate_every": 2,
    "gate_games": 20,
    "gate_threshold": 0.55,
    # Not in the registered table, because building the instrument is what
    # exposed it: with a 20-game gate the loop's default cadence of 25 would
    # write no mid-gate checkpoint at all, so C4 would kill the run at a point
    # the checkpoint path had never reached and would be testing nothing.
    # LoopConfig now refuses a cadence longer than the match.
    "gate_checkpoint_every": 5,
    "workers": 8,
}

#: How long the parent waits for the child to reach the first gate before giving
#: up. Generously above the expected time so a slow machine does not fail C4 for
#: being slow.
KILL_TIMEOUT_S = 3600
POLL_S = 2.0

ENGINE_ONLY_REFERENCE = 705


def add_scale_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--board", choices=sorted(BOARDS), default=REGISTERED["board"])
    for key in (
        "seed",
        "generations",
        "games",
        "simulations",
        "steps",
        "batch_size",
        "buffer_capacity",
        "gate_every",
        "gate_games",
        "gate_checkpoint_every",
        "workers",
    ):
        parser.add_argument(
            f"--{key.replace('_', '-')}", type=int, default=REGISTERED[key]
        )
    parser.add_argument(
        "--gate-threshold", type=float, default=REGISTERED["gate_threshold"]
    )


def scale_from(args: argparse.Namespace) -> dict:
    return {key: getattr(args, key) for key in REGISTERED}


def scale_argv(scale: dict) -> list[str]:
    """The scale as flags, so the child runs the run the parent intended."""
    argv = []
    for key, value in scale.items():
        argv += [f"--{key.replace('_', '-')}", str(value)]
    return argv


def config_for(root: Path, scale: dict) -> LoopConfig:
    variant = BOARDS[scale["board"]]
    return LoopConfig(
        variant=variant,
        seed=scale["seed"],
        generations=scale["generations"],
        games=scale["games"],
        simulations=scale["simulations"],
        steps=scale["steps"],
        batch_size=scale["batch_size"],
        buffer_capacity=scale["buffer_capacity"],
        gate_every=scale["gate_every"],
        gate_games=scale["gate_games"],
        gate_threshold=scale["gate_threshold"],
        gate_simulations=scale["simulations"],
        gate_checkpoint_every=scale["gate_checkpoint_every"],
        workers=scale["workers"],
        root=root,
    )


def digest(state_dict: dict) -> str:
    """SHA-256 over the weights, in a fixed key order.

    Byte-equality, not "close": C4 asks whether a killed run resumes into the
    same run, and a tolerance would turn that into a question about how much
    drift is acceptable, which is a different and much weaker question.
    """
    hasher = hashlib.sha256()
    for key in sorted(state_dict):
        value = state_dict[key]
        hasher.update(key.encode())
        hasher.update(value.detach().cpu().contiguous().numpy().tobytes())
    return hasher.hexdigest()


def digests(root: Path) -> dict:
    state = Checkpoint(root).load()
    return {
        "generation": state.generation,
        "challenger": digest(state.challenger),
        "champion": digest(state.champion),
        "buffer": len(state.buffer),
    }


# -- child mode ---------------------------------------------------------------


def child(root: Path, scale: dict) -> int:
    """Run the loop to completion, or until something kills this process."""
    config = config_for(root, scale)
    variant = BOARDS[scale["board"]]
    fresh = Checkpoint(root).resume_point() is None
    run(
        config,
        (lambda: ConvRotationNet(variant.n_cols, variant.n_rows)) if fresh else None,
    )
    return 0


def spawn(root: Path, scale: dict) -> subprocess.Popen:
    """Start a child running ``scale``. The flags are how the scale gets there."""
    return subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--child", "--root", str(root)]
        + scale_argv(scale),
        cwd=str(Path(__file__).resolve().parent.parent),
    )


def child_rss_kb() -> int:
    """Peak resident set size of reaped children, in KB (Linux ru_maxrss)."""
    return resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss


# -- the checks ---------------------------------------------------------------


def straight_run(root: Path, scale: dict) -> dict:
    """C1, C2, C3 and the throughput measurement."""
    if root.exists():
        shutil.rmtree(root)
    print(f"phase A: straight run into {root}", flush=True)

    started = time.monotonic()
    process = spawn(root, scale)
    code = process.wait()
    elapsed = time.monotonic() - started
    if code != 0:
        raise SystemExit(f"the straight run exited {code}; C1 fails")

    config = config_for(root, scale)
    rows = [json.loads(line) for line in config.history_path.read_text().splitlines()]
    games_played = scale["generations"] * scale["games"]
    return {
        "seconds": elapsed,
        "rows": rows,
        "digests": digests(root),
        "self_play_games": games_played,
        "composed_games_per_hour": games_played / elapsed * 3600,
        "peak_child_rss_kb": child_rss_kb(),
    }


def killed_run(root: Path, scale: dict) -> dict:
    """C4: kill during the first gate, resume, and require byte-equal weights."""
    if root.exists():
        shutil.rmtree(root)
    print(f"phase B: killed run into {root}", flush=True)

    process = spawn(root, scale)
    checkpoint = Checkpoint(root)
    deadline = time.monotonic() + KILL_TIMEOUT_S
    killed_at = None

    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise SystemExit(
                f"the child finished (exit {process.returncode}) before the first "
                "gate wrote a mid-gate checkpoint. Either the gate never ran or "
                "the mid-gate path did not fire, and C4 tested nothing."
            )
        found = checkpoint.manifest()
        if found and found.get("gate_games", 0) > 0:
            killed_at = dict(found)
            os.kill(process.pid, signal.SIGKILL)
            process.wait()
            break
        time.sleep(POLL_S)

    if killed_at is None:
        process.kill()
        process.wait()
        raise SystemExit(
            f"no mid-gate checkpoint appeared within {KILL_TIMEOUT_S}s; C4 cannot "
            "test what it exists to test"
        )

    print(
        f"  killed with SIGKILL at gate game {killed_at['gate_games']} "
        f"of generation {killed_at['generation']}",
        flush=True,
    )

    # The checkpoint must still be readable after a kill. If manifest-last and
    # atomic_write do their job, a torn write leaves the previous complete state.
    try:
        checkpoint.load()
    except Exception as error:  # noqa: BLE001 - the point is that nothing survives
        raise SystemExit(
            f"the checkpoint is unreadable after SIGKILL: {error}. atomic_write "
            "and manifest-last did not hold, and no resume is possible."
        ) from error

    print("  resuming", flush=True)
    resume = spawn(root, scale)
    code = resume.wait()
    if code != 0:
        raise SystemExit(f"the resumed run exited {code}; C4 fails")

    return {"killed_at": killed_at, "digests": digests(root)}


def evaluate(straight: dict, killed: dict, scale: dict) -> list[dict]:
    rows = straight["rows"]
    gated = [r for r in rows if r["gated"]]

    checks = [
        {
            "id": "C1",
            "what": "the loop closes",
            "passed": len(rows) == scale["generations"]
            and straight["digests"]["generation"] == scale["generations"],
            "detail": f"{len(rows)} history rows, checkpoint at generation "
            f"{straight['digests']['generation']}",
        },
        {
            "id": "C2",
            "what": f"{scale['workers']} spawned workers run the adopted head",
            "passed": all(r["samples"] > 0 for r in rows),
            "detail": f"samples per generation: {[r['samples'] for r in rows]}",
        },
        {
            "id": "C3",
            "what": "the gate decides, with an interval and a seat split",
            "passed": len(gated) == scale["generations"] // scale["gate_every"]
            and all(
                "gate_ci" in r and "gate_as_first" in r and "gate_as_second" in r
                for r in gated
            ),
            "detail": "; ".join(
                f"gen {r['generation']}: {r['gate_win_rate']:.1%} "
                f"[{r['gate_ci'][0]:.1%}, {r['gate_ci'][1]:.1%}] "
                f"seats {r['gate_as_first']}/{r['gate_as_second']} "
                f"promoted={r['promoted']}"
                for r in gated
            )
            or "no gate ran",
        },
        {
            "id": "C4",
            "what": "a SIGKILL mid-gate resumes to byte-equal weights",
            "passed": killed["digests"]["challenger"]
            == straight["digests"]["challenger"]
            and killed["digests"]["champion"] == straight["digests"]["champion"]
            and killed["digests"]["generation"] == straight["digests"]["generation"],
            "detail": (
                f"straight challenger {straight['digests']['challenger'][:12]}, "
                f"killed {killed['digests']['challenger'][:12]}"
            ),
        },
    ]
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--root", default=None)
    parser.add_argument("--out", default="results/exp014-shakedown-5x5.json")
    parser.add_argument("--base", default="data/az-runs")
    add_scale_args(parser)
    args = parser.parse_args()
    scale = scale_from(args)

    if args.child:
        return child(Path(args.root), scale)

    if scale != REGISTERED:
        differs = {k: v for k, v in scale.items() if REGISTERED[k] != v}
        print(
            f"NOTE: running off the registered scale ({differs}). This is a "
            "debugging run and its artefact is not the registered one.",
            flush=True,
        )

    base = Path(args.base)
    started = time.monotonic()
    straight = straight_run(base / "shakedown", scale)
    killed = killed_run(base / "shakedown-killed", scale)
    checks = evaluate(straight, killed, scale)

    payload = {
        "experiment": "EXP-014",
        "registered": "experiments/registry.md",
        "kind": "instrument shakedown -- not evidence about the game",
        "variant": BOARDS[scale["board"]].name,
        "architecture": "ConvRotationNet",
        "torch": torch.__version__,
        "config": scale,
        "is_registered_scale": scale == REGISTERED,
        "checks": checks,
        "all_passed": all(c["passed"] for c in checks),
        "throughput": {
            "composed_games_per_hour": straight["composed_games_per_hour"],
            "seconds_total": straight["seconds"],
            "seconds_per_generation": [r["seconds"] for r in straight["rows"]],
            "peak_child_rss_kb": straight["peak_child_rss_kb"],
            "engine_only_reference": ENGINE_ONLY_REFERENCE,
            "note": (
                "Composed, with the network in the loop. R8's 705 games/hour was "
                "measured engine-only with torch not competing for the cores. "
                "This is a cost measurement: workers, games and generations may "
                "change by amendment, the five seeds may not."
            ),
        },
        "history": straight["rows"],
        "kill": killed["killed_at"],
        "digests": {"straight": straight["digests"], "killed": killed["digests"]},
        "elapsed_seconds": time.monotonic() - started,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))

    print()
    for check in checks:
        print(
            f"  {check['id']}  {'PASS' if check['passed'] else 'FAIL'}  {check['what']}"
        )
        print(f"        {check['detail']}")
    rate = payload["throughput"]["composed_games_per_hour"]
    print()
    print(
        f"throughput  {rate:.0f} games/hour composed "
        f"({rate / ENGINE_ONLY_REFERENCE:.2f}x the engine-only "
        f"{ENGINE_ONLY_REFERENCE}), peak child RSS "
        f"{straight['peak_child_rss_kb'] / 1024:.0f} MB"
    )
    registered_games = 30 * 200 * 5
    print(
        f"the registered run (30 gen x 200 games x 5 seeds = {registered_games:,} "
        f"games) projects to {registered_games / rate:.1f} h of self-play at this "
        "rate, gates excluded"
    )
    print(f"written  {out}  ({payload['elapsed_seconds']:.1f}s)")
    print()
    if payload["all_passed"]:
        print("all four checks pass: the objection to starting the run is removed")
        print("(passing licenses nothing else -- this is not evidence about the game)")
        return 0
    print("a check FAILED: the registered run does not start")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
