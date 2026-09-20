# Phase 7 — Interface, Portfolio Writeup, Public Release (release log)

**Objective.** Turn seven phases of analysis into something a reader can pick
up: three interfaces, the long-form article, the TIL series, and a `v1.0.0`
release. Then present to the professor who set the original brief in MAP 2001.

**Dates.** None. The roadmap is sequenced by dependency, not by calendar, and
this phase carries no external deadline. The author holds ~10–28 h/week across
projects and FLIPHEX shares that budget.

**What the phase must end with.** A tagged public release — `v0.9-writeup-draft`
then `v1.0.0` — and `writeup/main-writeup.md` complete. This is the only phase
whose deliverable is read by someone other than the author.

**What it inherits.** `exercises/ex05_complexity_analysis.md` and **TIL #4**,
carried out of Phase 5 and again out of Phase 6, untouched in both: this is the
third phase to own them. `ui/cli.py` already exists at 380 lines from the Phase 1
rule-validation work, with 35 lines of test — it covers hotseat, human-vs-
heuristic and heuristic-vs-heuristic, and wires **neither** the AZ agent nor the
solver agent, which is what the roadmap's task actually asks for. `README.md`'s
status section still says *"The engine (Phase 1) is not implemented yet"*.
`writeup/outline.md` still scopes the verdicts as H1–H5 and assigns Phase 6
"H4–H5"; H6 was adopted at the Phase 6 open and has a verdict.

**OPEN-1 is still open, and this is the phase that can close it.**
`docs/rules-canonical.md` has carried it since Phase 0: confirm all five columns
hold five cells, against the physical board. It is blocked on the artifact, not
on code, and the professor presentation is the occasion that unblocks it. If it
resolves the other way, `docs/board-geometry.md` and every count downstream of it
move — which is why it is named here rather than left in the issue tracker.

**This is the first phase that measures nothing**, and that is the risk it
carries rather than a relief. The nine gates in
[`docs/measurement-gates.md`](../docs/measurement-gates.md) are in force and have
nothing to catch; what replaces them is the discipline of not letting the
narrative overstate the result. Three of six verdicts are `structural` — the
rules answered them and no experiment could have — two of six are rejections, and
H4 records a locked figure that is 236× wrong. A writeup that reads as a clean
sweep would be a worse artifact than the phases it summarises.

---

## `ui/cli.py` — human-vs-human, human-vs-AZ, watch-AZ-self-play

**Six seats, named per colour.** `--purple` and `--green` each take one of
`human`, `random`, `heuristic`, `solver`, `uct`, `az`, so every pairing the
roadmap asked for exists and so do the ones it did not think to ask for. The
old `--mode` spellings map onto seats and still work.

Seat construction moved to **`ui/seats.py`**, separate from the CLI because it
is what every interface needs and none should reimplement. It carries three
judgements that would otherwise be copied three times: the solver's budget
depends on board size, the champion is shape-locked to one board, and the AZ
import costs a second or two.

### The reduced-deck bug the flag exposed

The CLI built its opening with `GameState.initial(board.n_cells, first)`, which
deals the **full 13 + 12 deck regardless of board size**. It was never wrong
before because there was no `--variant`: every game was the 5×5. On nine cells
it would have been playable and wrong — the hands never exhaust, so it is not
the game adr-011 defines and not the one the solved artefacts describe. Now it
goes through `Variant.initial_state()`, and a regression test asserts the 3×3
is dealt 5 + 4.

### The solver seat reports its proved rate

Measured on a full game, as a check rather than a claim:

| board | regime | proved |
|---|---|---|
| 3×3 | exhaustive from ply 1 | **5/5, 100%** |
| 5×3 | endgame-exact, `k ≤ 8` | 4/8, 50% |
| 5×5 | endgame-exact, `k ≤ 8` | 4/13, **31%** |

The 5×5's 31% lands on EXP-017's measured 32% from a completely different code
path, which is the kind of agreement worth recording. The 3×3 run takes 2.9 s
end to end including interpreter start, and returns **P1** — H1 and H2 again,
this time through the interface rather than through a sweep.

The rate is printed at the end of every game with a solver in it. A solver that
fell back to its heuristic for most of a game played mostly heuristic moves,
and the win says correspondingly little; EXP-017 carries the same number for
the same reason.

### The champion loads without its buffer

`Checkpoint.load` pulls a 29 MB replay-buffer pickle the interface has no use
for. `load_champion` reads `manifest.json` for the architecture and lifts the
champion `state_dict` out of `state.pt` instead — about 1.4 MB of weights. The
architecture is **read, never assumed**: a `state_dict` says what the parameters
are and nothing about the shape of network they belong to, which is what once
left the deployment path unable to play the adopted head.

Two failures are explained rather than raised. A missing run directory says that
`data/az-runs/` is gitignored, that a clone therefore has no champion, and how
to train one. A champion from another board says it is shape-locked and points
at the same limit `docs/research.md` records against H3's reduced-board members
— caught before `load_state_dict` can turn it into a tensor mismatch.

### Import cost, checked in a subprocess

`agents/__init__.py` omits `AZAgent` because importing it loads torch, which
costs a second or two and fails outright under the interpreter the exact solver
runs on. `ui/seats.py` keeps that property by importing torch **inside the
function that needs it** — and a test asserts it, in a subprocess, because
nothing inside the test process could observe it once another test has imported
torch.

**A game at 400 simulations takes 21 s against the champion**, about 1.6 s per
learned move. Recorded here because it is the number the browser build has to be
designed around, not because anything turns on it yet.

56 tests, up from 4.

## The browser build — what WebAssembly costs, measured before designing

**[EXP-018](../experiments/registry.md). Registered retrospectively, which is
the wrong order and is recorded as such.** The rule here is that an entry exists
before a run; EXP-003 and EXP-014 are both performance measurements feeding a
design decision and both were registered first. This one was run first. What the
entry would have forced is not the measurement but the *threshold* — nobody had
declared what slowdown would rule the learner out of the browser, and "we will
see" is precisely what a registration refuses.

**Pyodide costs ~3×, not the order of magnitude assumed.** The same tracked
instrument — `scripts/bench_engine.py`, pure stdlib — runs natively and
unmodified inside Emscripten, so the ratio is measured rather than extrapolated
across a boundary. Six workloads, spread **2.84× to 3.43×**.

| workload | native | pyodide | slowdown |
|---|---:|---:|---:|
| `legal_moves` at the opening | 1,558,544/s | 454,579/s | 3.43× |
| `apply_move` | 89,159/s | 29,987/s | 2.97× |
| random playout | 110.6 games/s | 33.5 games/s | 3.30× |
| heuristic game | 29.9 games/s | 10.1 games/s | 2.96× |
| UCT move, 100 sims | 1.0/s | 0.34/s | 2.93× |
| 3×3 opening solve | 2.6 s | 7.5 s | 2.84× |

The uniformity is the useful part. Those six stress different things — bit
manipulation, object construction, dictionary-heavy tree search, recursion — and
a slowdown that flat says the cost is the interpreter rather than one operation
hitting a WASM pathology, which means it transfers to code not measured here.

**What it decides.** A heuristic move costs **4 ms** in the browser and a whole
heuristic game 99 ms, so the planned web v1 has no performance question in it at
all. The 3×3 opening solve costs **7.5 s once**, after which the transposition
table carries the rest — a browser can play that board *perfectly* for the price
of one visible wait. And UCT at the trained 400-simulation budget costs **11.8 s
per move**, which is not interactive: the learner in a browser needs a smaller
budget or a worker thread, and a smaller budget makes it a different agent from
the one EXP-015 measured.

**What it does not decide.** The boot figure — ~1.9 s — is Node loading a package
from local disk, not a browser over a network, and one of three samples took
234 s under load. No browser-facing claim may quote it. Network inference is
unmeasured: only the tree search was timed, and no numpy forward pass exists yet.

The harness that loads Pyodide is deliberately **not** in the repository: it
needs `npm install` and a Node runtime. The half that must be identical on both
sides is the half that is tracked.

## `web/` — the board, in a browser, on the real engine

**[adr-013](../docs/adr/adr-013-interface-targets.md).** The browser build is a
scope addition — the roadmap named three interfaces and no way for a reader to
play. It does not replace `ui/pygame_ui.py`; both ship.

**The engine goes to the browser unported.** `fliphex/`, `solver/` and three of
four agents are pure standard library, so Pyodide runs them with no shim and no
second implementation. `scripts/build_web.py` bundles 24 modules into
`web/payload.json` — 163 KB of source, **50 KB gzipped** — and the page writes
them into the WebAssembly filesystem at boot.

The bundler is the interesting part. It reads each module's **AST** rather than
grepping, and separates imports that *execute* at module load from ones deferred
into a function body or a `TYPE_CHECKING` guard. That distinction is what makes
the bundle possible at all: `ui/seats.py` defers torch on purpose, and a checker
that could not tell the two apart would either ban the file or wave through a
real dependency. It refused the first build it was given, correctly, naming
`agents/az_agent.py` and the two deferrals — so the exclusion list is *checked*
rather than declared.

**The page draws and nothing else.** Every legality question, flip and score
comes back from `ui/session.py`. Cell positions come from
`session.layout`, and `tests/test_session.py` asserts each centre lands
exactly where `Board.neighbour` says the neighbour is — on all three boards, in
all six directions. A cell drawn in the wrong place is a test failure, not a
picture that looks slightly off.

One thing was caught by writing it down: the first version carried a `BrowserGame`
subclass **inside a Python string in `app.js`** — rules-adjacent code in a file
no test can reach. Both its methods moved to `session.py` and got tests.

### Verified in the target environment, not only natively

The whole page bootstrap was replayed under Pyodide in Node — same payload, same
filesystem writes, same import — and played a complete game:

| | |
|---|--:|
| board, decks | 25 cells, 13 + 12 ✓ |
| human move | **4 ms** |
| heuristic reply | 17 ms |
| complete 25-ply game | 109 ms |
| engine ready after boot | 128 ms |

The 4 ms is EXP-018's prediction arriving through the actual page code path
rather than through the benchmark, which is the confirmation worth having.

**Bug found this way:** the page wrote its modules to relative paths, and
Emscripten's working directory is not the filesystem root. It failed with a bare
`ErrnoError 44` naming nothing. Both sides now use an absolute `/app`.

### It failed on first contact with a browser, and the reason is the point

The page did not boot. The badge read `failed` and no board appeared.

**The server log is what located it.** `payload.json` returned 200 three seconds
after the page loaded — so Pyodide had started, the bundle had been fetched, and
the engine had imported. Everything measured above was working. The failure was
in the part *nothing had tested*: `startGame` called `resetSelection`, which
renders the hand, which reads `state.snapshot` — still `null` until the first
`refresh`. A null dereference, on the first line of the first game.

The Python half had 111 tests. The JavaScript half had **none**, and this is the
second defect to come out of that same gap in one sitting — the first was the
`BrowserGame` subclass living in a string inside `app.js`. Both are the same
shape: code that the test suite structurally cannot reach.

**Fixed, and then actually verified.** The snapshot is now installed before
anything can read it, `renderHand` returns early rather than dereferencing null,
and the whole page was booted headlessly under jsdom against the real Pyodide
and the real `index.html` — driven through the DOM the way a person drives it:

```
ok   the engine boots and the badge reads ready
ok   25 hexagons drawn, cell names A1 … E5
ok   13 pieces in purple's hand, each with a glyph
ok   choosing a piece marks every legal cell
ok   choosing a cell offers 6 distinct rotations with net values
ok   hovering a rotation previews it on the board
ok   the move lands and the heuristic agent replies
ok   placed tiles show the arrows they fired
ok   undo takes back both plies and returns to the opening
ok   switching to the 3x3 redraws 9 cells and deals 5 pieces
```

**That check is now in the repository** — `web/package.json` and
`web/test/page.test.mjs`, run with `cd web && npm test`, 30 checks. adr-013
clause 7 was amended to split the two cases it had conflated: the *benchmark*
harness stays outside, because the half that must be identical on both sides is
`scripts/bench_engine.py` and that is tracked; a *test of shipped code* comes
in, because the alternative is the only visible half of the product having no
automated check at all.

Three bounds on it. It is **not** part of `pytest` — a Python contributor who
never installs Node loses only this check. It touches nothing in delivery: the
published artifact is still four static files and a CDN. And `web/app.js` is
imported **unmodified**, the only seam being `globalThis.FLIPHEX_PYODIDE_URL`,
read before the CDN is chosen. The scratchpad version had rewritten the source
with a regular expression, which is testing something else.

It found a failure on its first tracked run, and **the failure was in the test**:
it asserted `aria-pressed` on a button that `renderHand` had already replaced,
and reported a page defect that did not exist. Fixed with the reason written
beside it, because a test that cries wolf is worse than no test.

### The browser cost is registered before it is measured — [EXP-019](../experiments/registry.md)

The first play session produced *"fast enough not to bother me"*. That is an
impression, it is not recorded as a measurement, and EXP-018's lesson is why:
the entry has to exist to fix the **decision rule** before the number is visible.

So EXP-019 was registered first, and it decides three pieces of pending work
rather than merely reporting a duration. **The split render** — adr-013 says the
board must draw before Python is ready, and it does not — is built only if warm
time-to-playable exceeds 1 s. **A byte-counting indicator** only if cold exceeds
10 s. **The exhaustive 3×3 solver seat** does not ship if its browser solve
exceeds 10 s. The two limits are adr-013's, from Nielsen, external and published
in 1993.

The page now times itself: four cumulative marks on `window.fliphexMarks`, and
`window.fliphexBench()` for the solver probe. A stopwatch cannot separate
`chrome`, `runtime`, `engine` and `playable`, and the distinction is the whole
point — a reader who cannot tell a slow runtime from a slow import learns
nothing about which one to fix.

Also fixed: the `favicon.ico` 404 in the server log. Inline SVG data URI, so the
page still needs exactly one request beyond its own four files.

### EXP-019 ran, and the falsifier fired for a reason I had not imagined

Ten loads in Chrome 153, five cold and five warm, collected by the page itself.

| | cold | warm |
|---|--:|--:|
| median time to playable | 4,293 ms | 3,925 ms |
| spread (n=5) | 4,218–4,474 | 3,842–4,211 |
| bytes transferred | 5,775,367 | 300 |

**Ratio 1.09× against a registered 2× floor.** The falsifier says the rules are
not applied as written, and that is honoured. But its *reason* is wrong, and
that is the finding: it argued that a run which cannot tell its two conditions
apart decides nothing. This run separates them by a factor of **19,000** in
transferred bytes. What collapsed is not the distinction — it is the
distinction's relevance to time.

I wrote the falsifier using a time ratio as a proxy for condition separation,
and measured the conditions separately in the same instrument, and did not
notice the two could disagree. A pre-registered falsifier that fires for a
reason its author had not imagined is worth more than one that never fires.

**Boot is compute-bound.** The `runtime` step costs 3,881 ms cold and 3,458 ms
warm; the 423 ms difference *is* the download. So **10% of a cold boot is
transfer and 90% is WASM compilation and Python start** — and rule 2's
byte-counting indicator was designed around a bottleneck that does not exist.

**Three of four registered predictions are wrong.** Warm was predicted under 3 s
(it is 3.9); cold was predicted transfer-dominated (it is 10%); the page's own
bytes were predicted under 1% of the transfer (3.7%, because the runtime is
5.78 MB compressed rather than the 14 MB I read off disk, and
`python -m http.server` gzips nothing). The fourth is unrun.

### What follows

**No progress indicator.** Cold is 4.3 s against a 10 s limit, and not a near
miss.

**The split render is built — and it is a judgement made after seeing the
data**, recorded as such in the registry rather than presented as the plan
working. Rule 1's only input was ever the warm number, which is well measured
inside one cell; the collapse invalidates the comparison *between* cells. A
reader who thinks the falsifier should have stopped rule 1 as well is reading
the text as written, and the text was written badly.

It is also worth less than it looked: it cannot make the page playable sooner,
because Python must finish either way. It replaces 3.9 s of blank space with
3.9 s of visible board. That is the standard remedy for a wait, not a speed-up,
and must not be written up as one.

### The split render, built

`scripts/build_web.py` now also emits **`web/geometry.json`** — 8 KB, three
boards, generated from `ui.session.layout`. The page fetches it first, draws the
board, and only then starts Pyodide. A fifth mark, `board`, sits between
`chrome` and `runtime`, so the next measurement can report time-to-board
separately from time-to-playable.

The board is drawn **inert**: visible, dimmed, `pointer-events: none`, with the
boot strip beneath it saying *"This board is real; it is not playable until the
engine starts."* When Python is ready the dimming lifts and the strip goes.

**The one thing this could have broken is the one thing that is tested.**
adr-013 forbids a second geometry, and drawing before Python starts means the
page reads cell centres from a file rather than from the engine — exactly one
chance to diverge. `tests/test_build_web.py` asserts the file equals
`layout()` for every board, that every option in the page's own `<select>` has
geometry, and that the file is generated rather than edited. The jsdom suite
asserts the ordering that makes it a split render at all: `board` before
`runtime`, and the draw costing under a fifth of the runtime it precedes.

It buys a visible board during a ~3.9 s wait. It does not make the page
playable sooner, and the code says so where someone changing it will read it.

### A defect found by planning the phone test, not by running it

The rotation preview — the affordance this interface exists for — was wired to
`mouseenter`. **A touch screen never fires it.** On a phone, tapping a rotation
played it with no preview at all: the one thing a player most needs to see
before committing, invisible on the device most likely to be handed to somebody
else.

Fixed by reading `(hover: hover) and (pointer: fine)` live. With a mouse nothing
changes — hover previews, a click commits. Without one, the first tap previews
and arms the rotation, a second tap on the same one plays it, and tapping a
different one re-arms instead. The hint line says which mode you are in.

**Testing it needed the harness to grow a capability**, and that is worth
recording: jsdom implements **no** `matchMedia` at all, so the page's `canHover`
fell to its "assume a mouse" branch and the touch path could not be reached.
The harness now supplies a media query it can flip, and the suite drives the
touch path for one move and the mouse path for the next — both ship, so both
are checked.

Worth stating plainly: this was found by *thinking about* the phone cell of
EXP-019, before any phone ran the page. The measurement had not started and had
already paid for itself.

### What is not done

**One browser, one machine.** Chrome 153 on Windows x64 — one cell pair, not the
table. The second browser and the phone are unrun, and the phone is now the
interesting case precisely because boot is compute-bound.

**The ~235 s stall did not appear** in ten browser loads, against roughly one in
five under Node on WSL2. Evidence that it belongs to the Node path, not proof:
ten loads cannot rule out a one-in-twenty event.

**The 3.4 s runtime step was not profiled.** Whether it is wasm compilation,
stdlib unpacking or interpreter start is unknown, so anything trying to shorten
it would be guessing.

## `ui/pygame_ui.py` — the physical palette, on screen

## `ui/replay_viewer.py` — play back saved games from `data/`

## `ui/replay_viewer.py` — play back saved games

**There were no saved games.** The roadmap says *"play back saved games from
`data/`"*, so the first thing was to look for one. `results/*.json` is tracked,
but EXP-017's `games` field is the integer **5,000**, not five thousand move
lists; EXP-008's `moves` is a count; EXP-014's `history` is training
generations. `data/az-runs/` and `results/*.jsonl` are gitignored. **Not one
ordered game survives a clone of this repository.**

That is the third appearance of the defect the `figures/` clause was written to
catch, and this time it suggested the design rather than just blocking it.

### A game is cheaper than a file

Agents take their seed at construction — the `Agent` contract — so a game
between two of them is a **deterministic function of variant, seats and seed**.
A recording does not need a position per ply, or a file at all: `5x3-h1`,
`heuristic`, `random`, `seed 7` reproduce it exactly, anywhere.

So the viewer's default source is a game recorded **on the spot**. No file, no
artefact, no network; it works on a fresh clone with no arguments. `--load`
still reads a file when one exists.

### Two refusals, because a file is data and data is not trusted

`Recording.replay()` walks every move through `legal_moves` and refuses the
first illegal one **by ply and by tile** — a corrupted or hand-edited move list
fails there rather than being drawn as though it were a game:

```
✗ move 5 of 9 is not legal here: P1 at B1 rotation 0
```

`Recording.verify()` goes further: a recording that names seats and a seed is
*claiming* the game is a function of them, and that claim is checkable. It
re-derives the game and refuses one whose moves do not match. A recording
cannot carry a provenance it did not come from. Where a seat was human, or no
seed was kept, it says the game is not reproducible instead of pretending.

### The viewer

Arrow keys step, Home and End jump, space plays at 700 ms a ply, and the
scrubber seeks — one tick per ply, so the scale is visible rather than implied.
The tile just placed is rimmed white and the tiles it flipped are rimmed green,
because reading a replay means seeing cause and effect rather than a board that
changed.

Seeking rebuilds from ply zero every time rather than keeping an undo stack. A
game is at most 25 plies and the engine applies one in microseconds, so the
simple thing is also the fast thing, and a scrubber that can land anywhere needs
no special case.

`ui/pygame_ui.py`'s `draw_hex` and `draw_arrow` moved to module level so both
windows draw the same shapes from the same code. 34 tests for `ui/replay.py`,
plus scrubber arithmetic and a headless window smoke under SDL's dummy driver.

## Both graphical interfaces assumed you were purple

Raised by the author after play-testing: *"the first player is always me."*

**The solver was never the cause, and it is worth being precise about why.** It
is not trained — it is exact search — and `agents/solver_agent.py` contains no
reference to `PURPLE`, `GREEN` or `first` anywhere. It solves for whoever is to
move. `ui/cli.py` has taken `--purple`, `--green` and `--first` since it was
rewritten.

The two graphical interfaces hardcoded it. `ui/pygame_ui.py` offered only
`--green` and decided the human's turn with `to_move == "PURPLE"`; `web/app.js`
did the same. So a player could only ever experience **the side of the board H1
says is favoured**, on the interfaces whose whole subject is whether it is
favoured.

Both now derive the human's turn from the seats rather than assuming a colour.
The window takes `--play purple|green`, the page has a *You play* selector, and
when the person holds the second seat the agent **takes the opening unprompted**
— without that, the board waits for a move the player cannot make, which is a
deadlock rather than a preference.

`--play green` is now the way to feel, rather than read, the thing four
exhaustive solves say about this game.

## `README.md` — the high-level summary that did not exist

Also raised by the author: *which file do I read for a summary of what the
experiments concluded?* The honest answer was **none of them**.
`docs/research.md` holds all six verdicts but each row is a dense paragraph;
`experiments/registry.md` is 5,800 lines; the README had been frozen at Phase 0
through seven phases, still saying *"The engine (Phase 1) is not implemented
yet"*.

The README is now that file. It carries the six verdicts in one scannable
table, the two solved boards, the shipped board's complexity, an explicit
*what is not established*, how to play in all four interfaces, and a **Where to
read what** map that sends a reader to the right layer and no further.

Its shape is deliberate: two hypotheses rejected, one true by construction, and
one carrying a locked figure that is 236× wrong, stated as the result rather
than buried. A README that read as a clean sweep would misrepresent the
project's best work.

## The interfaces were configured once, and the ADR had already said otherwise

Two complaints, and they turned out to be one finding.

The first: the pygame window is configured on the command line and nowhere
else, so trying a different opponent means quitting and losing the position.
The second: the exact solver — the thing this project actually built — is
reachable *only* from that window, because the browser page offers human and
heuristic and nothing more.

The second half is the interesting one. adr-013's second amendment withdrew the
stronger seats from the **deployed** page and wrote, in the same paragraph, that
"`ui/seats.py` builds all six and the local page serves them". It did not.
There was one `index.html` with two hard-coded `<option>`s, and GitHub Pages and
`localhost` were served the same bytes. The sentence describing the local page
was aspirational when it was written, and nothing since had made it true.

That is the fourth time this phase a deliverable was specified against something
that does not exist — after `figures/`, the browser champion and the replay
viewer's saved games. The pattern is not carelessness about files. It is that a
*restriction* and an *implementation of that restriction* are different
artefacts, and writing the first feels like having done the second.

**The seat list is now a function of `location.hostname`**, and it fails closed:
the rule enumerates local hosts, so an origin nobody anticipated gets the
published list rather than the local one. Private LAN addresses count as local,
because that is how a phone reaches this laptop and EXP-019's phone cell used
`172.25.201.155`. `uct` and `az` are in neither list and that is stated in the
code, because they cannot run at all — `scripts/build_web.py` excludes
`agents/az_agent.py` for importing torch, which has no WebAssembly build. A
missing option that reads as a withheld one is its own small lie.

**Measured before claiming it works.** Driving the page's own code path under
Node, the solver opening costs **8.2 s on the 3×3** and 0.1 s on the 5×3 — the
latter because `search_below_k = 8` declines the attempt until eight cells
remain, so most of a 5×3 game is heuristic and the page should not pretend
otherwise. The 3×3 figure sits beside the 7.5 s adr-013 already carried.

Pyodide has one thread, so those 8 seconds are not a wait, they are a **frozen
tab**. The page therefore says so in the commentary before entering the search,
dims the board, and prints the elapsed time after. A spinner was rejected on
purpose: it would stall visibly, and a stalled spinner reads as a crash.

**And then the smaller finding underneath.** `GameSession` holds no agent and
names a seat per move, with a docstring saying that exists *"so a visitor can
change their mind about who they are playing without restarting"*. Both
graphical interfaces restarted anyway — the page on every `change` event, the
window by requiring a new process. The capability had been built, documented,
and then not used by either caller.

Now only the board restarts. Changing the opponent or the colour you hold acts
on the position in front of you, which makes the best thing either interface can
do possible for the first time: play the heuristic into a position you do not
like, hand it to the exact solver, and watch the difference. That is the
interactive form of a comparison the project otherwise only ever made in a
table.

The pygame window got the same three controls as chips in its panel. It offers
all six seats, because a local window is local by definition; a seat that cannot
be built — the learner, on a clone with no weights — puts the control back and
says why instead of taking the window down. `ChampionUnavailableError` carrying
its own remedy paid for itself here: the status bar gets a usable sentence for
free.

Recorded as adr-013's third amendment. 56 checks now run under jsdom, and the
negative ones are the ones that matter — `example.com`, `172.32.0.1` and
`notlocalhost.com` all have to come back restricted.

## An outside design review, and what I took from it

A reviewer read three screenshots and wrote a long critique. Its central claim:
*the problem is not a lack of beauty, it is that the interface still communicates
"development tool" rather than "finished project"* — most visibly in pygame.
That is right, and the useful part is that it is a claim about **communication**
rather than taste, so it can be argued with rather than only agreed with.

Taken, in the order the argument is strongest:

**"A shortcut is acceleration, not discovery."** The footer read `n new game ·
b board, c colour, o opponent (right-click or shift for back)` — a shortcut list
pretending to be an interface. Someone seeing the window for the first time had
to read a 12px line to learn that a new game was possible at all. The keys now
live **on** the controls they trigger, New game and Undo are chips rather than
keystrokes, and the footer is down to the two gestures that have no button
because they act on a move you are part-way through.

**Undo has to be disabled when there is nothing to undo, in the hit test and not
only in the drawing.** A control that looks unavailable and still fires says one
thing and does another. `button_at` refuses disabled buttons; the test asserts
the refusal, not the colour.

**The score was 26px bold and the turn indicator was 15px, and that is
backwards.** The score is the board's own arithmetic and the board is right
there. What a player cannot read off the board is whether the window is waiting
for *them*. So the headline is now the large line and it is in the second
person: **"Your turn"**, or **"Solver is thinking…"**, or "You win". "Purple to
move" asked the player to remember which colour they held, every turn, in a
window whose entire recent change was making that colour a choice.

**The window wore pygame's logo.** The cheapest possible signal that an
application was assembled rather than designed. It now carries the split
hexagon the page uses as its favicon, built from the same two colours.

**"One geometry, two renderers" should extend to the palette.** This was the
best idea in the review and it is the one with teeth. `ui/session.py` already
held the one geometry and both interfaces scale it. The palette had no such
rule: `ui/pygame_ui.py` carried twelve hand-copied RGB tuples under a comment
reading *"matching web/style.css"*, and `web/style.css` carried twelve hex
strings under a comment saying the same thing back. Two declarations and a pair
of comments asserting they agreed.

A comment is not a constraint. `ui/theme.py` now holds the palette, the window
reads it directly, and `scripts/build_web.py` generates `web/theme.css` from it
— the same arrangement, for the same reason, as `web/geometry.json`. It also
removed a duplication nobody had noticed: the dark scheme was written out twice
in the stylesheet, once under `prefers-color-scheme` and once under
`[data-theme]`. Both now come from one dict. A drifting colour is a dirty
working tree in CI.

### What I declined, and why

**A two-column pygame layout, board left and panel right.** The sketch claims it
would give the board more prominence; it would give it *less*. `fit_board`
already maximises the board inside the space it has, and the vertical margin the
review read as wasted space is the aspect ratio of five columns of flat-top
hexagons, not a design choice. Taking 300px for a sidebar shrinks the only
object on screen that matters.

**Splitting "Game" from "Research" modes.** This is the one I'd push back on
hardest. The proposal is that a player mode and a researcher mode should be
separate surfaces — but the whole claim of this repository is that they are the
*same artifact*: the thing you play is the thing that produced the verdicts, and
the opponent selector is the research control. Hiding the solver behind a
"Research" tab would make the page look tidier and say something false about the
project. It also contradicts the review's own best advice, which was to add
hierarchy rather than surface.

**A coordinates toggle.** More configuration, to solve a problem better solved
by weight. The cell names are already the quietest thing on the board.

**Microanimations, an About dialog, a How-to-play modal.** The page has a "How
it works" `<details>` and both interfaces now name what they are waiting for.
Everything else here is P4 in the review's own ordering and would be surface
added before the structure is finished.

**The boot note "is architecture text in the player's space".** Read off a
screenshot of a loading state. It is hidden the moment the engine is ready —
about four seconds — and while it is showing, explaining the wait *is* the job.

## A third design pass, and the review that was reading stale code

The reviewer quoted `radius * 0.075` for the arrow shaft, `radius * 0.15` for
its head, `SysFont("dejavusans,arial", 15)` for the type and `big` for the net
badge — all four already changed in the previous commit. Their recommended
range for the shaft was **0.045–0.055R** and for the wing **0.09–0.11R**; the
code was sitting at 0.05 and 0.105.

That is worth recording rather than scoring a point on, because the *diagnosis
still held against the current prints*. The screenshots were rendered after the
change and the arrows still read heavy. So the cause was somewhere else, and
looking for it found the actual defect.

**`pygame.draw` ignores the alpha channel.** The board drew every placed tile's
arrows with `(255, 255, 255, 190)` — an intent to draw them at 75% opacity. On a
surface without `SRCALPHA` the draw functions do not blend, so that alpha had
never done anything and the arrows had been fully opaque white since the file
was written. Verified directly: drawing that colour over the purple and reading
the pixel back gives `(255, 255, 255)`.

The page had it right all along — `.arrow-placed { stroke: rgba(255,255,255,.75) }`
and CSS *does* honour it. So the two interfaces had disagreed about this from
the start, with the window silently losing. Fixed by mixing towards the colour
the cell currently shows, at `ARROW_PLACED_MIX = 0.25`, which is the same
number the stylesheet has always used.

**The better catch was the second one, and it is about information rather than
weight.** Selecting a piece ringed *every* legal cell in purple with a dot in
the middle. `playable_cells` returns the empty cells — any tile may go on any of
them — so on an opening board that lit 24 of 25 hexagons to tell the player
something the colours already told them. It also buried the only moment that
carries information: **this one, if you click**. The ring now appears under the
cursor and on the selected cell, nowhere else, in both interfaces. The window
gained a hover state to do it; the page had `:hover` already and needed a
`@media (hover: none)` fallback so a phone keeps a faint mark.

**And a grammar inconsistency between the three renderers.** The playing
window's preview draws a cell you are about to capture in green and one you are
about to hand back in red. The replay viewer drew **both green**, because
`Replay.flipped()` returns one list. A flip is a toggle (adr-007) and handing a
tile to your opponent is the rule a reader is most likely to get wrong — so the
one interface built for reading a game was teaching it backwards. Split into
`gained()` and `handed_back()`, with a test that asserts they partition
`flipped()` and that at least one of each actually occurred.

### Declined

**A separate `ui/fonts.py`, beside `ui/theme.py`.** The argument is that
typography has an asset component the palette does not. True — and the split
becomes right the moment `assets/fonts/` exists, because then there is loading,
fallback and licence handling to put somewhere. Today it would be three
constants in a module of their own. The module is called `theme`, not
`palette`.

**Vendoring IBM Plex Sans.** Not a disagreement, a blocker: `fc-list` shows only
DejaVu on this machine, and the stack in `ui/theme.py` already lists Plex, Source
Sans 3, Inter and Noto ahead of it, so all three renderers move together the day
the files land. It needs a download and a licence file in the repository, which
is the author's call and not a refactor.

## `writeup/main-writeup.md` — the long-form article

## `exercises/ex05_complexity_analysis.md` — carried from Phases 5 and 6

Carried from Phase 5, carried again from Phase 6, written here. The delay turned
out to work in the exercise's favour: by now every quantity it asks for is
computed, checked and recorded, so no answer has to be estimated and each one is
markable against an artefact in this repository. That makes the problems harder,
not easier — a wrong answer is wrong against a number, not against a textbook.

**Four of the roadmap's five statements needed correcting**, and they are kept
visible in a callout rather than silently patched, the way ex03's three were.

1. **The cell alphabet has four symbols and the game has three.** "empty,
   purple, green, joker" treats the joker as a cell state. It is a tile in P1's
   hand and shows its owner's colour once placed; nothing on the board ever
   reads as "joker".
2. **`× 6 orientations` is wrong by 2.8 × 10¹⁹**, per adr-003 and adr-006. This
   one is also in H4's *locked* text, where it could not be corrected and had to
   be answered in the verdict instead — so the exercise asks the reader to
   rediscover it rather than being told.
3. **Q3 asks for a Monte Carlo estimate of a closed form.** The game tree is
   exactly 4.229 × 10⁵⁸, in microseconds.
4. **Q4's "decreases monotonically after some peak" has no peak.** Mean
   branching falls strictly from ply 0 on both factors at once; the hump belongs
   to the layer profile, which is a different curve. Telling those two apart is
   now the point of Q4 rather than an aside.

**A sixth question was added**, because Phase 7 produced one the roadmap could
not have asked. The solver seat can sit on a forward search or on a completed
retrograde sweep, and those are different kinds of knowledge — so Q6 asks for
Allis's three grades applied to this project's own artefacts, why a sweep yields
a *strong* solution where an exhausted forward search yields only a *weak* one,
and what the `*` in the comparison table is doing that the grade column was not.
It closes on the honest version of the headline: the 5×3 database is 4.1 GB,
gitignored, and absent from a clone. Q6.4 also asks the reader to generalise the
self-comparison regression this phase found and fixed, which is the only
exercise question in the set that is really about testing.

The answers are left open, like ex02's. There is no phase owner for them and
there was never going to be one; what the repository owes is the problem set.

## TIL #4 — retrograde analysis, when backwards beats forwards

`tils/til-04-retrograde-analysis-backwards-vs-forwards.md`. A **skeleton with
prompts**, like #2, #3 and #5 — the content is first person and is deliberately
not ghost-written.

The piece has one structural problem and it is also its best feature: **the
title states a direction and this project measured the opposite on its own main
board.** EXP-003's medians are 480 nodes to prove a 5×5 position at `k = 5` and
806,474 at `k = 8`, under a second either way, against a 150 TB database. The
skeleton opens by telling the author not to write around that.

The section the piece exists for is the one Takizawa supplied: **the answer is
an interval, not a crossover.** Two cuts with different justifications —
enumerable above (storage), solvable below (search) — and backwards wins strictly
between them. On the shipped board the cuts do not meet, so the interval is
empty and adr-012 Option B is closed by arithmetic rather than by sampled
medians. That reframing is what EXP-003 got wrong the first time by looking for a
single `k*`, and it is more transferable than any number in the piece.

Two boundaries are written into the skeleton so the TIL series does not repeat
itself. **The 580× speedup is TIL #6 and gets one sentence and a link** — it is a
different lesson about what an exhaustive sweep pays for. And the EXP-005
counting identity is marked *optional, cut it if #6 already made that point*.
The one piece of Phase 7 material it does carry is the cost of knowing, measured
on a full 5×3 game through the window: peak resident 3.0 GB, worst move 4.9 s,
4.1 GB read across sixteen plies. "Solved" became something you can lose a game
to, and the price of perfect play turned out to be memory bandwidth.

## TILs #1–#6 — polish and publish

## `README.md` — the reproducibility pass, and the status section frozen at Phase 0

## OPEN-1 — five columns of five, confirmed against the board

## The presentation — back to MAP 2001

## The paper-track decision

## Lessons Learned

## Failed Attempts
