# ADR-013 — Two interfaces, and the browser runs the real engine

**Status:** Accepted
**Date:** 2026-09-21
**Deciders:** Bruno Ramos Martins

## Context

The roadmap's Phase 7 names three interfaces — `ui/cli.py`, `ui/pygame_ui.py`,
`ui/replay_viewer.py` — and a `v1.0.0` public release. It says nothing about
where anyone would *play* the game, and that gap is load-bearing: this repository
is a portfolio artifact, the audience clicks a link, and a desktop application
written in pygame reaches approximately none of them. Seven phases of analysis
end in something nobody can try.

A browser build was not in the roadmap. It is a scope addition, which is why this
ADR exists rather than a quiet commit.

### What the repository already permits, measured rather than assumed

The decision turns on a fact about this codebase that nobody had checked:

| package | imports | runs unmodified in WebAssembly |
|---|---|---|
| `fliphex/` | `dataclasses`, `enum`, `random`, `typing` | yes |
| `solver/` | `array`, `collections`, `itertools`, `json`, `math` | yes |
| `az/mcts.py`, `az/encoding.py` | stdlib and `fliphex` | yes |
| `agents/` — random, heuristic, solver | stdlib and `fliphex` | yes |
| `az/network.py` and everything under it | `torch` | **no** |

The engine, the exact solver and the tree search are **pure standard library**.
Pyodide — CPython compiled to WebAssembly — runs them with no port, no shim and
no second implementation. Only the learned evaluator is out of reach, and only
because torch has no WebAssembly build.

### What it costs, measured — [EXP-018](../../experiments/registry.md)

The same tracked instrument, `scripts/bench_engine.py`, run natively and
unmodified under Emscripten. Six workloads, slowdown **2.84× to 3.43×**. The
spread is flat across bit manipulation, object construction, dictionary-heavy
tree search and recursion, which says the cost is the interpreter rather than one
operation hitting a pathology — so it transfers to code the benchmark did not
touch.

Per-interaction, in the browser:

| interaction | cost |
|---|--:|
| one heuristic move | 4 ms |
| one complete heuristic game | 99 ms |
| 3×3 opening solve, once per game | 7.5 s |
| UCT/PUCT move at the trained 400-simulation budget | 11.8 s |

## The threshold, and where it comes from

EXP-018's own entry records that it should have been registered *to force a
threshold* rather than to record a measurement, and that none had been declared.
This ADR repairs that, and the repair only counts if the threshold is not read
off the numbers it then judges.

So it is taken from outside: **Nielsen's three response-time limits** — 0.1 s
feels instantaneous, 1 s preserves uninterrupted flow of thought, 10 s is the
limit of held attention and anything beyond needs a progress indicator and an
escape. Published in *Usability Engineering* (1993), thirty-three years before
this measurement, and derived from human perception rather than from this
engine.

**Provenance: cited, not verified.** The book is not held in this repository and
the limits are quoted from their widespread secondary reporting. They are graded
the way `complexity/comparison.py` grades a figure nobody here opened, and the
decision is stated so that it survives the limits being somewhat different: the
three seats below sit at 4 ms, 7.5 s and 11.8 s, which straddle any plausible
version of the boundary rather than crowding it.

## Decision

**1. Both interfaces ship. The browser build is added, not substituted.**
`ui/pygame_ui.py` stays a Phase 7 deliverable. The browser build is the one the
portfolio links to; the pygame window is the one that runs with no network, which
is the case the professor presentation may actually need.

**2. The browser runs `fliphex/` itself, under Pyodide. The rules are never
reimplemented in JavaScript.** This is the clause the rest hangs on. A second
implementation of the rules would be a third artefact able to disagree with
`docs/rules-canonical.md` and with the engine, in a project whose stated
discipline is *if the code and the document disagree, the code is wrong* — and
unlike the two that exist, nothing would cross-check it. Every verdict in
`docs/research.md` was produced by the engine the browser will now run.

**3. Presentation is HTML and SVG, not a canvas.** 25 hexagons with names,
colours, arrows and hover states is a document-shaped problem: flat-top polygons
in SVG are crisp at any zoom, themeable from the physical palette with CSS
custom properties, responsive to phone width, and reachable by assistive
technology. `pygbag` — pygame compiled to WebAssembly — was considered and is
rejected under *Alternatives*.

**4. Seat availability in the browser is decided per seat, against the
threshold.**

| seat | browser cost | verdict |
|---|--:|---|
| human, random, heuristic | ≤ 4 ms | **shipped**, no indicator needed |
| solver, 3×3 (exhaustive) | 7.5 s once, then fast | **shipped**, with a progress indicator and the wait named up front |
| solver, 5×3 / 5×5 (`k ≤ 8`) | bounded by the same budget | **shipped**, reporting its proved rate as the CLI does |
| learner at 400 simulations | 11.8 s per move | **refused at that budget** |

**5. A reduced-budget learner is a different agent and is labelled as one.**
Dropping simulations to fit the browser does not produce the agent EXP-015
measured, and no rate measured here may be quoted against H3. If the learner
ships at all, its budget is stated beside it.

**6. Hosting is GitHub Pages: static files only, Pyodide from a CDN.** No server,
no build step that the repository cannot reproduce. The Pyodide runtime is loaded
from `cdn.jsdelivr.net` rather than vendored, so it does not enter the repository
or its bandwidth.

**7. The web sources live in the repository; the Pyodide harness does not.**
Anything needed to *render* the page is tracked. The Node toolchain used to
benchmark Pyodide needs `npm install` and stays outside, consistent with the
repository being self-contained.

**8. First cut is human-versus-human and human-versus-heuristic.** Both are free
under clause 4. The solver and learner seats are added against a board that
already works, not designed around at the same time.

## Alternatives considered

**Reimplement the rules in JavaScript or TypeScript.** Fastest page, no runtime
download, no boot wait. Rejected under clause 2: it creates a second source of
truth for the rules with no cross-check, in the one project where that is the
central claim. The cost is not hypothetical — `fliphex/` encodes adr-003's inert
tiles, adr-006's non-chaining flips, adr-007's toggle semantics and adr-011's
parity, and a divergence in any of them would be silent.

**`pygbag` — compile the pygame interface to WebAssembly.** One codebase, two
targets, and it would have satisfied both deliverables at once. Rejected on
three counts: it still cannot run torch, so it buys nothing for the learner; it
loads Pyodide *and* SDL, so it is strictly more download than clause 3; and it
renders to a bitmap canvas, where responsive layout, text and accessibility are
all work that HTML does for free. The visual ceiling is lower precisely on the
deliverable whose purpose is to look good.

**Ship the browser build with no agents at all.** Human-versus-human only, which
removes every performance question. Rejected because the point of the page is to
let someone play *the thing that was analysed*, and at 4 ms the heuristic seat
costs nothing to include.

**Run inference server-side.** Would make the learner interactive at full budget.
Rejected: it requires hosting the repository does not have, and GitHub Pages
cannot provide it. A portfolio artifact that stops working when a server lapses
is worse than one that declines a feature.

## Consequences

**Two rendering targets with no shared rendering code.** The pygame window and
the SVG page will draw the same board twice, and they will drift. Accepted
deliberately. What they *do* share is `ui/seats.py`, which is where the
judgements live — solver budget by board size, the champion's shape lock, the
cost of importing torch — so the part that can be wrong in an interesting way is
written once.

**The page carries a boot wait the CLI does not.** Pyodide must download and
initialise before the first move is legal. The local figure is ~1.9 s and is
**not** a browser-over-network measurement; EXP-018 refuses to let it be quoted
as one. The page must therefore be designed to render the board *before* Python
is ready and enable interaction after, rather than blocking on a number nobody
has measured yet.

**The learner needs a numpy forward pass before it can ship at any budget.**
Six layer types — `Conv2d`, `BatchNorm2d`, `ReLU`, `Flatten`, `Linear`, `Tanh`
— and 347,887 parameters, about 1.4 MB. Pyodide carries numpy. That port does
not exist, and until it does clause 4's last row is moot rather than binding.

**A champion shipped to the web is a distribution decision, not a technical
one.** `data/az-runs/` is gitignored and the networks were never distributed.
Publishing weights to a static host is a choice about what the repository
releases, and it belongs with the `v1.0.0` release issue rather than here.

**This ADR can be falsified by one measurement.** If a real browser's boot and
first-move latency are materially worse than Node's — a different WASM engine, a
cold CDN, a phone — clause 8's first cut is still free but clause 4's solver rows
may not survive. The measurement is cheap once the page exists, and is owed
before the page is linked from anywhere.

## Related

- [adr-003](adr-003-piece-representation.md) — inert placed tiles; why the state
  is small enough for a browser to hold at all
- [adr-011](adr-011-reduced-variant-parity.md) — the odd-cell rule the browser's
  board selector must honour
- [EXP-018](../../experiments/registry.md) — the slowdown measurement, and its
  own record of being registered in the wrong order
- `docs/engineering.md` — the dependency rule that made `fliphex/` portable
  without anyone planning for it
