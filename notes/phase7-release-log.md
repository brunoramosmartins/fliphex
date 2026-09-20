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

## `ui/pygame_ui.py` — the physical palette, on screen

## `ui/replay_viewer.py` — play back saved games from `data/`

## `writeup/main-writeup.md` — the long-form article

## `exercises/ex05_complexity_analysis.md` — carried from Phases 5 and 6

## TIL #4 — retrograde analysis, when backwards beats forwards

## TILs #1–#6 — polish and publish

## `README.md` — the reproducibility pass, and the status section frozen at Phase 0

## OPEN-1 — five columns of five, confirmed against the board

## The presentation — back to MAP 2001

## The paper-track decision

## Lessons Learned

## Failed Attempts
