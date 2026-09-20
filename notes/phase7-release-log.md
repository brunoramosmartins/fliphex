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
