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

## Amendment, 2026-09-21 — clause 7 splits: a measurement harness stays out, a test of shipped code comes in

Clause 7 kept the Node toolchain outside the repository, on the grounds that it
needs `npm install` and the repository is self-contained. That was written about
the **Pyodide benchmark harness**, and for that it still holds: EXP-018's runner
is not tracked, and the half that must be identical on both sides —
`scripts/bench_engine.py` — is.

A **test of shipped code** is a different thing, and the case turned concrete
rather than hypothetical. The JavaScript half of this interface had no automated
check of any kind, and two defects came out of that gap in one sitting: a
`GameSession` subclass living inside a Python string in `app.js`, and a null
dereference in `startGame` that stopped the page booting at all. Both were in
code the Python suite structurally could not reach. Neither was caught by
1,164 passing tests, because none of them could see the file.

**So `web/package.json` and `web/test/` are tracked**, with `jsdom` and
`pyodide` as dev dependencies and `web/node_modules/` ignored.

Three things bound it:

- **It is not part of `pytest`.** `cd web && npm test` is its own command. A
  Python contributor who never installs Node loses nothing but this check.
- **It does not touch the page's delivery.** The published artifact is still
  four static files and a CDN. Nothing in `npm` is a build step.
- **`web/app.js` is imported unmodified.** The only seam is
  `globalThis.FLIPHEX_PYODIDE_URL`, read before the CDN is chosen, so the test
  can point at a local package. A test that rewrites its subject is testing
  something else, and the first version of this harness did exactly that.

`web/package-lock.json` is **not** tracked. The one version that must agree with
the page is `pyodide`, pinned exactly in `package.json` because `app.js` loads
that same version from the CDN; jsdom's minor version is not load-bearing.

**What it cannot do, stated so nobody mistakes a green run for a working page.**
jsdom implements the DOM, not a browser: no rendering, no layout, no CSS. It
catches a wrong selector, an unwired handler, a state machine in the wrong
order. It cannot see an overlapping hexagon, an unreadable colour or a broken
phone layout, and it is not a substitute for EXP-019, which still needs a real
browser.

## Amendment, 2026-09-21 — the deployed page carries no agent stronger than the heuristic

**Author's decision, not a measurement.** Clause 4 shipped the solver seats to
the browser subject to EXP-019's third rule. They are now withdrawn from the
**deployed** page: what the public link offers is human-versus-human and
human-versus-heuristic, and nothing above that.

The seats are not deleted. `ui/seats.py` builds all six and the local page
serves them, so anyone running the repository plays the exhaustive 3×3 solver in
a browser. The withdrawal is about what is published, not about what exists.

**This makes EXP-019's third rule moot**, and the entry records it that way
rather than repointing it at some other decision — the same status EXP-004 and
EXP-005 carry, and for the same reason: the decision the rule fed has been taken
on other grounds. The 3×3 browser solve may still be timed, and its number is now
descriptive rather than decisive.

Two reasons the decision is sound independent of any timing. A page that offers
perfect play on one board and heuristic play on another invites the comparison
its own verdicts refuse — H1 is `exact` on the 3×3 and `not decidable` on the
5×5, and a visitor losing to both would reasonably conclude they are the same
kind of opponent. And a solver seat is the one thing on the page that can hang a
tab, which no first impression should risk.

## Amendment, 2026-09-20 — the local/deployed split is enforced by the page, and it fails closed

The amendment above said the seats were not deleted and that "`ui/seats.py`
builds all six and **the local page serves them**". It did not. There was one
`index.html`, its `<select>` held two hard-coded options, and GitHub Pages and
`localhost` were served the same file — so the sentence describing the local
page was aspirational, and the exact solver was reachable only from the pygame
window. A document and its code disagreed, which in this project means the code
was wrong.

**The seat list is now a function of the origin**, in `web/app.js`:

| origin | seats |
|---|---|
| `localhost`, `127.0.0.0/8`, `10/8`, `192.168/16`, `172.16/12`, `*.local`, `file://` | human, random, heuristic, **solver** |
| anything else | human, heuristic |

Three properties, in the order they matter:

**It fails closed.** The rule enumerates what is *local*, not what is
published, so a host nobody anticipated — a custom domain, a preview URL, a
fork — gets the restricted list by default. Getting this backwards would mean a
new deployment target ships the solver until someone remembers it exists.

**Private LAN addresses count as local.** The page is reached from a phone by
its host's `192.168.x` or `172.x` address (EXP-019's phone cell used
`172.25.201.155`), and that is still a checkout being served by its own author
over their own wifi. It is not a published artifact and there is no first
impression to protect.

**`uct` and `az` are in neither list.** They are not withheld; they cannot run.
`scripts/build_web.py` excludes `agents/az_agent.py` from the payload because it
imports torch, which has no WebAssembly build. The consequence recorded above —
that the learner needs a numpy forward pass first — is what makes this true, and
stating it in the page keeps a missing option from reading as a withheld one.

`index.html` keeps the published pair as its static content, so the file on
disk is the published contract and JavaScript only ever widens it.

### A blocking seat is announced before it blocks

Pyodide runs on the page's only thread. A 3×3 exhaustive solve does not take a
while — it **freezes the tab**: no spinner turns, no click lands. Measured from
the page's own code path under Node, the opening takes **8.2 s** on the 3×3 and
0.1 s on the 5×3, the latter because `search_below_k = 8` declines the attempt
until eight cells remain. The 3×3 figure is consistent with the 7.5 s this ADR
already carried.

So the page names the freeze in the commentary *before* entering it, dims the
board, and reports the elapsed time afterwards. A progress animation was
rejected: it would visibly stall, and a stalled spinner reads as a crash rather
than as a wait. The reported number is descriptive — it is what a visitor can
check against the table above on their own machine, which is the measurement
this ADR's last consequence says is still owed.

### Changing who you play no longer discards the game

`GameSession` holds no agent and names a seat per move, documented as being
*"so a visitor can change their mind about who they are playing without
restarting"*. Both graphical interfaces restarted anyway: the page on every
`change` event, the pygame window by requiring a new process. Now only the
**board** restarts, because a different board is a different game. The opponent
and the colour you hold take effect on the position in front of you.

This is not only convenience. Handing a live position from the heuristic to the
exact solver, and watching what it does differently from the same board, is the
most instructive thing either interface can offer — and it is the interactive
form of the comparison the project spent three phases making numerically.

### The pygame window is configured in the window

The same three controls — board, the colour you hold, the opponent — are chips
in the panel, cycled by click or by `b`/`c`/`o`. The flags now only say where
the first game starts. Consequence, accepted: the two interfaces still share no
rendering code, so this is the same affordance built twice. What they share is
`ui/seats.py` and `ui/session.py`, which is where anything interesting can be
wrong.

The window offers all six seats because it is local by definition; a seat that
cannot be built — the learner, on a clone with no weights — puts the control
back and says why, rather than taking the window down mid-game.

## Amendment, 2026-09-20 — the solver returns to the deployed page, on one board

The second amendment withdrew every agent above the heuristic from the deployed
page, and the third enforced that split in `web/app.js` with a rule that fails
closed. Both stand. This narrows the withdrawal by one board.

**The deployed page offers the exact solver on the 3×3 and nowhere else.**

The rule is not "the small board". It is the board where
`ui.seats.solver_budget` returns no `search_below_k`, so the seat plays **exact
from ply 1** rather than heuristic until eight cells remain. That is the whole
justification for making a stranger wait: the wait buys perfect play. Its worst
case is the opening at about **8 s** and it falls monotonically from there,
because the tree shrinks with every tile placed.

On the 5×3 and the 5×5 the same seat would block for a *variable* time near the
end of the game and play heuristic moves before it — a longer freeze in exchange
for a weaker claim. The second amendment's reasoning applies there unchanged.

**What made this safe to do now** is the third amendment's machinery, not a new
tolerance for freezing. `BLOCKING_SEATS` already names the freeze before
entering it, and the footer's origin line now states the wait in seconds *before*
the visitor meets it. An 8 s stall that is announced is a slow opponent; the
same stall unannounced is a crash.

### The seat list gained a second axis, so it has to be recomputed

`seatsFor(hostname)` became `seatsFor(hostname, board)`, and the consequence is
that a list computed at load is no longer correct for the session — changing the
board can withdraw the seat the visitor is holding. `fillSeats` is therefore
re-run on every board change, and when it drops the current seat the page
**says so** rather than substituting quietly. Both directions are tested.

It still fails closed on both axes: an unknown host gets the published list, and
an unknown board gets the published list even on a known host.

### What this is for

The page is being published under the portfolio's own domain so that the game's
original designers — it was built in a course at IME and FAU and is going to the
Matemateca — can play it from a link. The thing worth showing them is not a
competent opponent. It is that one of these boards is *finished*: the value of
every position is known, and the seat opposite them is reading it.

## Related

- [adr-003](adr-003-piece-representation.md) — inert placed tiles; why the state
  is small enough for a browser to hold at all
- [adr-011](adr-011-reduced-variant-parity.md) — the odd-cell rule the browser's
  board selector must honour
- [EXP-018](../../experiments/registry.md) — the slowdown measurement, and its
  own record of being registered in the wrong order
- `docs/engineering.md` — the dependency rule that made `fliphex/` portable
  without anyone planning for it
