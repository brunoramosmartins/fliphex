# FLIPHEX

**Computational analysis and self-play learning of an original hexagonal board
game.**

FLIPHEX is a 2-player, perfect-information, deterministic board game designed in
2017 by students of IME-USP and FAU-USP in the course *MAP 2001 — Matemática,
Arquitetura e Design*. It exists as a laser-cut wooden board with 25 hexagonal
tiles. This repository is its digital counterpart: a formalised rule engine and
three complementary technical analyses of the game's strategic structure.

The game is original, and the author is one of its designers.

## The game in one paragraph

25 hexagonal cells, 25 two-sided tiles (purple on one face, green on the other).
Each player holds 12 tiles carrying 1 to 6 outward-pointing arrows; Player 1 also
holds the arrowless joker. On your turn you place one tile on any empty cell at
any rotation, and every arrow pointing at an occupied neighbour flips that
neighbour to your colour. Flips do not chain. All 25 cells fill, and whoever
shows more of their colour wins — 25 is odd, so there are no draws.

![A full game of FLIPHEX played in the browser: tiles are placed on the hexagonal
board, arrows fire and flip neighbouring tiles between purple and green, and the
board fills to a final score.](docs/media/fliphex-demo.gif)

### ▶ [Play it in your browser](https://brunoramosmartins.github.io/fliphex/)

**No install, works on a phone.** On the 3×3 your opponent is the *exact solver* —
that board is strongly solved, so you are playing against the proven value of the
game rather than against an approximation. The page opens in Portuguese, for the
Matemateca; there is an **EN** switch in its header.

*The recording above is a whole game, sped up: the browser interface running this
project's real Python engine under WebAssembly, with the rules never
reimplemented in JavaScript. Each tile's arrows fire once, on the ply it is
placed.*

Full rules: [`docs/rules-canonical.md`](docs/rules-canonical.md).

## Research question

> Does the first player have a provable advantage, does the joker break game
> balance, and does the game admit an efficient learned policy that approaches
> optimal play?

Six hypotheses were **pre-registered and locked** before any experiment ran
(tag `v0.3-hypotheses`, 2026-08-05). After the lock, `docs/research.md` could
only gain verdicts — no statement was edited to fit a result.

---

## What was found

Every hypothesis has a verdict. Two were rejected, one turned out to be true by
construction, and one records a locked figure that is wrong by a factor of 236.
That shape is the result, not a blemish on it.

| | verdict | on what evidence |
|---|---|---|
| **H1** — the first player has an advantage | **supported** where perfect play is computable; **not decidable** on the shipped 5×5 | four exhaustive solves, all returning P1 |
| **H2** — removing the joker does not change who wins | **supported** where computable; **out of reach by construction** on the 5×5 | both arms, both reduced boards, same winner |
| **H3** — self-play converges and agrees with the solver | **rejected**, on both clauses independently | 5 seeds, 135 h; one seed fails the floor, `χ² = 18.52` rejects a common rate |
| **H4** — where FLIPHEX sits among known games | clause 1 **supported**; clause 2's magnitude is **236× wrong** | both complexity bounds in closed form |
| **H5** — no archetype dominates | **true by construction, and therefore not evidence of anything** | the rules force it; 5,000 games, zero exceptions |
| **H6** — the design is robust to perturbation | **supported on every perturbation that exists** — and the set cannot falsify it | two ratified ADRs forbid the rest |

Read the rows in full, with their intervals and their caveats, in
[`docs/research.md`](docs/research.md).

### Two boards are solved exactly

| | cells | configurations | result |
|---|--:|--:|---|
| **3×3** | 9 | 711,963 | **P1 wins**, both arms |
| **5×3** | 15 | 1.75 × 10¹⁰ | **P1 wins**, both arms |
| 5×5 (shipped) | 25 | 4.886 × 10¹⁷ | not decidable |

The 3×3 was solved **twice, by independent methods** — forward alpha-beta and a
retrograde sweep — which agree on 604,347 of 711,963 positions (84.9%). It is
the only board in this project with two witnesses to the same truth.

On the 5×3, uniformity breaks at exactly `t = 5`: every one of the 12,841,920
configurations at four tiles placed is a P1 win. An advantage that is total
rather than positional is what a structural cause looks like.

### The shipped game is larger than it looks

| | |
|---|--:|
| reachable state space | **4.886 × 10¹⁷** |
| game tree, exact count of distinct games | **4.229 × 10⁵⁸** |
| effective branching factor | 221.3 |
| legal opening moves | **1,450** |

The game tree is not a `b^d` estimate — it is an exact count,
`25! × 13! × ∏orbits × 12! × ∏orbits`, checked against the engine's own move
generator at full depth on the 5×1 and to three plies on both reduced boards.

That figure exceeds every strongly solved game this project could source, and is
**4.2× larger than Othello 8×8**, which was weakly solved in 2023. A factor, not
an order.

### What is not established

Nobody has solved FLIPHEX, and nothing here says it is solvable. The
shipped-board first-player figure — **54.2% [52.9%, 55.6%]** over 5,000 games —
comes from play that is heuristic for ~17 plies and exact only for the last 8
(`proved_rate` 32%). It corroborates a direction. It says nothing about perfect
play.

---

## Play it

Four interfaces, all driving the same engine.

**In a browser** — the rules are the real Python, compiled to WebAssembly:

```bash
cd web && python3 -m http.server 8765
```

Then open `http://localhost:8765` — or play the published page at
**[brunoramosmartins.github.io/fliphex](https://brunoramosmartins.github.io/fliphex/)**,
which is this directory deployed unchanged.

Served locally the page offers every seat that can run in a browser. The
published page offers the **exact solver on the 3×3**, where it plays perfectly
from the first move, and stops at the heuristic on the larger boards — per
[adr-013](docs/adr/adr-013-interface-targets.md), because there the same seat
would freeze the tab for longer and play heuristic moves anyway.

Board, the colour you hold and who you are playing are selectors — only changing
the board starts a new game, so you can hand a position you are losing straight
to the solver and watch what it does instead.

**In a window:**

```bash
python -m ui.pygame_ui --variant 3x3 --opponent solver --play green
```

The same three controls are chips in the panel (`b`, `c`, `o`), so the flags
only say where the first game starts.

**In the terminal:**

```bash
python -m ui.cli --variant 3x3 --green solver
```

**Watch a recorded game:**

```bash
python -m ui.replay_viewer --variant 5x3 --purple solver
```

On the **3×3 the solver plays perfectly from the first move** — you are playing
against the truth of the game, not an approximation. It takes about 8 s to
answer the opening there, and in the browser that freezes the tab, because
Pyodide has one thread; the page says so before it happens. On the 5×5 the
solver is exact only for the last 8 plies and reports its own proved rate,
because a solver that fell back to a heuristic for most of a game played mostly
heuristic moves.

**On the 5×3 you can play the database instead of the search.** Give the window
or the terminal `--sweep` and the solver seat reads the completed retrograde
sweep instead of searching, so
every move is a table lookup and `proved_rate` is 1.0 from the opening rather
than from the last eight cells — Allis's *strongly solved*, made playable:

```bash
python -m ui.pygame_ui --variant 5x3 --opponent solver --sweep
```

It costs what knowing costs: peak resident **3.0 GB**, a worst single move of
**4.9 s** (layer 9 alone is 1.2 GB), and 4.1 GB read from disk across sixteen
plies. `data/checkpoints/` is gitignored, so without the sweep the flag is a
*preference* rather than a requirement — the seat falls back to search and the
header says which backend it got.

Seats are `human`, `random`, `heuristic`, `solver`, `uct`, `az` — named per
colour in the terminal (`--purple`, `--green`), chosen in the interface
everywhere else. **Try both colours.** Purple moves first and holds the joker,
which is the side H1 says is favoured; playing green is the only way to feel
what four exhaustive solves concluded. Reduced boards are dealt reduced decks,
per [adr-011](docs/adr/adr-011-reduced-variant-parity.md).

---

## Where to read what

The documents are layered deliberately. Start at the top and stop when you have
what you came for.

| If you want | Read |
|---|---|
| the whole story, in one sitting | [`writeup/main-writeup.md`](writeup/main-writeup.md) |
| the verdicts, with intervals and caveats | [`docs/research.md`](docs/research.md) |
| why a decision was live at the time, including the wrong turns | [`writeup/decision-journal.md`](writeup/decision-journal.md) |
| what a phase actually did, in its own words | `notes/phase<N>-*.md` |
| an experiment's design, rule and result | [`experiments/registry.md`](experiments/registry.md) |
| why the code is shaped this way | [`docs/adr/`](docs/adr/) — thirteen decision records |
| how a number is allowed to become a claim | [`docs/measurement-gates.md`](docs/measurement-gates.md) |
| the rules, authoritatively | [`docs/rules-canonical.md`](docs/rules-canonical.md) |

Three of those are worth singling out. The **long-form article** is the one to
read if you are only going to read one thing: it carries the caveats beside the
verdicts rather than turning the record into a clean narrative. The **decision
journal** records what was believed on the day, including the parts that turned
out wrong. The **measurement gates** are nine questions every quantity has to
survive before it is reported, and the ninth — *what is this quantity free to
be?* — was added after the first eight let the same defect through three times.

---

## Layout

```
docs/          rules, geometry, archetypes, thirteen ADRs, the verdicts
fliphex/       the game engine — pure standard library      (Phase 1)
solver/        Axis 1 — exact analysis                      (Phase 3)
az/            Axis 2 — AlphaZero self-play                 (Phase 4)
complexity/    Axis 3 — structural analysis                 (Phase 6)
agents/        random, heuristic, solver, AZ
stats/         Wilson intervals, bootstrap, paired tests
ui/            CLI, pygame window, replay viewer, shared session and palette
web/           the browser build — the engine under Pyodide (Phase 7)
figures/       seven figure *scripts* — the PNGs are generated, not tracked
scripts/       experiment entry points and doc generators
experiments/   the experiment registry
writeup/       the long-form article and the decision journal
exercises/     five problem sets, from formalising the rules to complexity
tils/          six short pieces on techniques this project needed
notes/         one log per phase, plus the literature notes
```

`fliphex/` imports nothing from the project. `solver/`, `az/` and `complexity/`
import `fliphex/` and never each other — which is why the engine and the exact
solver run unmodified in a browser.

## Running it yourself

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev,ui,figures]"
```

`az` is a separate extra because it pulls in torch:
`pip install -e ".[az]"`.

```bash
pytest tests/ && ruff check . && ruff format --check .
```

1,257 tests. The browser build has its own suite, which needs Node — and CI does
not run it, so it is worth running before touching anything under `web/`:

```bash
cd web && npm install && npm test
```

### Generated files

`docs/board-geometry.md` and `docs/piece-archetypes.md` come from
`scripts/build_docs.py`; `web/payload.json`, `web/geometry.json` and
`web/theme.css` come from `scripts/build_web.py`. All of them refuse to be
edited by hand — CI fails if the tree is dirty after a rebuild.

The last two are the same idea applied twice. The board's cell positions come
from `ui/session.py` and the palette from `ui/theme.py`, so the window and the
page **cannot** draw a different board or a different purple from each other.
What they deliberately do not share is layout: a window and a web page owe each
other the same answers, not the same pixels.

```bash
python scripts/build_docs.py && python scripts/build_web.py
```

### What a clone does not get

`data/az-runs/`, `data/checkpoints/`, `results/*.jsonl` and `figures/*.png` are
gitignored, so a fresh clone has the solved reduced boards and the experiment
summaries but **no trained network, no recorded games, no endgame database and
no rendered figures**. Everything in this repository is built to work without
them: the AZ seat explains what is missing and how to train one, the solver seat
falls back to search and says which backend it got, and the replay viewer
records a game from a seed rather than reading a file nobody has.

Three of the four are gitignored for size — 5.7 MB per champion, 4.1 GB for one
5×3 sweep. The figures are 880 KB and are gitignored on a different principle:
a rendered figure needs only tracked inputs and a few seconds, so the generator
is the artefact and the PNG is not. Rebuild the gallery in under a minute:

```bash
pip install -e ".[figures]" && python -m figures.build
```

That principle is only legitimate while **every** input is tracked, so it is
asserted rather than assumed: `python -m figures.build --check` verifies the
manifest without importing a plotting library, and `tests/test_figures.py` runs
it, along with a test that pins the gitignore decision itself so it stays a
decision rather than becoming an accident.

## Credits

FLIPHEX was designed by students of IME-USP and FAU-USP under Prof. Dr. Artur
Simões Rozestraten (FAU), Profa. Dra. Deborah Raphael (IME), and Prof. Dr.
Eduardo Colli (IME) in MAP 2001, with technical support from LAME.

This analysis is by [Bruno Ramos Martins](https://github.com/brunoramosmartins).

## License

[MIT](LICENSE).
