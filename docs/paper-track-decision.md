# Paper-track decision

**Status: open.** The decision is gated on an event that has not happened — the
presentation to the original professor — and this file exists so that the gate
is visible rather than implicit. It closes with either **"not pursued"** and a
date, or a link to the fork.

Written 2026-09-20, at the Phase 7 close. Everything below the policy is an
assessment of what the repository actually holds, not an argument for a verdict.

---

## 1. The policy this file closes

Publication was never a v1 deliverable. The project was built to be
*paper-ready* rather than *paper-bound*, and the rule adopted at the outset is:

- If publication is pursued, a **new repository** is created, forked from this
  one at that moment.
- The fork adopts stricter rigour: **~10 seeds per experiment**, a formal
  statistical protocol, a LaTeX manuscript, and a target venue's submission
  format.
- **This repository is untouched by that decision** and remains self-contained.
- This file closes with "not pursued" or with the fork's link. It does not
  close with "maybe".

The separation is the point. A portfolio repository and a submission are
different artefacts with different failure modes, and trying to make one
document serve both is how a portfolio acquires the hedged, provisional voice
that makes it unreadable.

## 2. What is already at publication standard

Four things, graded by how much work stands between them and a submission.

**(a) Two corrections to repeatedly cited complexity figures.** *Closest to
ready, and the only item here that is not about FLIPHEX.*

- **Reversi 6×6's widely repeated state space of ~10²⁰ cannot exist.**
  `3^36 = 1.501 × 10¹⁷` bounds it before any legality constraint is applied, so
  the claim overshoots by **666×**, and no primary source for it was found.
- **Connect Four's cited 10¹⁴ is 22× the exact count.** Tromp's enumeration
  gives 4,531,985,219,092, independently confirmed; both Allis and Schaeffer
  cite the estimate.

Both are one-line checkable, both are negative results about numbers that
circulate in secondary literature, and neither depends on anyone accepting a
claim about an unpublished game. `complexity/comparison.py` already grades every
cell by provenance and `self_check()` opens the cited source and looks for the
quote, so the apparatus for stating this carefully exists. The natural home is a
note in the ICGA-Journal family of venues rather than a full paper.

**(b) A measured limit on "MCTS will fix a bad prior".** *Strong, and
methodological rather than game-specific.*

adr-005 adopted a factored (cell × tile × rotation) policy head whose
independence assumption is **known to be false**, on the stated grounds that
search corrects a bad prior — which is the standard justification for that
shortcut. EXP-011 measured it against exact solver ground truth on the 5×3:

| | factored | flat | gap |
|---|--:|--:|--:|
| supervised top-1 agreement | 58.6–60.8% | 65.6–68.6% | **+8.0** |
| top-1 optimality after 400 PUCT simulations | 66.8% | 73.7% | **+7.0** |

**400 simulations closed about an eighth of the deficit**, and the final
*training* policy loss (2.616 factored against 2.375 flat) shows an
expressiveness ceiling rather than an early-stopping artefact. Every factored
seed sits below every flat seed; paired *t* = +6.96 [+4.81, +9.11].

What makes it publishable is the ground truth: the comparison is against exact
values, not against each other. What limits it is scope — one board, one budget,
one game.

**(c) Two boards of an original game solved exactly.** 3×3 (711,963
configurations) and 5×3 (17,506,580,337), both arms, all four runs
`termination: exhausted`, both **strongly solved** by retrograde sweep. The 3×3
is solved twice by independent methods, agreeing on 604,347 of 711,963 positions.

The result is real and the verification is unusually well documented — adr-010's
V0–V6 with coverage stated rather than assumed, including where it is partial.
The obstacle is not rigour, it is **audience**: a reviewer cannot check a game
they have never seen, and "we solved the 5×3 variant of a game we designed" has
a novelty problem that no amount of care fixes. If this is the paper, the game
itself has to be the contribution and the solve is the evidence.

**(d) The pre-registration record.** Six hypotheses locked at `v0.3-hypotheses`
on 2026-08-05, before any experiment ran, with thresholds dated earlier than the
results that judge them. Two rejected, one true by construction, one carrying a
locked figure 236× wrong that was answered in the verdict rather than edited in
the text. Nine measurement gates, the ninth added after the first eight let the
same defect through three times.

This is the most *unusual* thing the project has and the hardest to place. It is
a methods contribution in a field that does not usually publish methods
contributions about itself.

## 3. What is not at publication standard, and why

1. **Seed count.** EXP-015 ran 5 seeds × 30 generations in **135.0 hours**. The
   fork policy asks for ~10, which is ~270 h on the same hardware, and the H3
   verdict is the one that most needs it: the rejection rests on one seed
   failing the floor by two games, with between-seed `sd` 7.3% against the 3.4%
   sampling predicts.
2. **No cause is established for either H3 failure.** Nothing in this project
   varies architecture, budget or training length against the training run. The
   verdict says the learner did not clear the bar; it does not say why, and a
   reviewer will ask.
3. **The headline question is open on the board that matters.** H1 is *not
   decidable* on the shipped 5×5. The corroborating 54.2% [52.9%, 55.6%] comes
   from play that is heuristic for ~17 plies and exact for the last 8, and says
   nothing about perfect play.
4. **Three architecture decisions were taken against 5×3 ground truth and
   never re-measured on the 5×5.** The 3.3-point head deficit is a 5×3 number
   quoted over a 5×5 design, and no alternative head has ever been trained on
   the shipped board.
5. **Nothing here was independently reimplemented.** The comparison table marks
   this project's own solved rows with an asterisk for exactly this reason. A
   second party running a second implementation is what removes it, and no
   amount of additional compute substitutes.
6. **One author, one machine, no external replication.** Which is fine for a
   portfolio and is the first thing a venue will notice.

## 4. What the fork would have to do, concretely

Not a plan — a cost estimate, so the decision is taken against a number.

| | |
|---|---|
| re-run EXP-015 at 10 seeds | ~270 h wall clock, single machine |
| re-read EXP-006 against the new champions | hours, not days |
| an ablation that isolates *a* cause for the H3 failure | at least one more training axis, so ~270 h again per axis |
| an independent reimplementation of the 5×3 sweep | the only thing that removes the asterisk; not compute-bound, people-bound |
| LaTeX manuscript and venue formatting | the smallest item on this list |

The two 270-hour entries are the decision. Everything else is weeks of writing;
those are months of compute on hardware that is also the author's workstation.

## 5. A reading, offered and not binding

If the decision is yes, the strongest submission is **not** "we solved FLIPHEX".
It is (a) — the two literature corrections — possibly carrying (b) as the
second result, with FLIPHEX as the instrument that produced both rather than as
the subject. That version needs no additional compute, no additional seeds, and
no reviewer to care about an unpublished game. It is also, honestly, a much
smaller paper than the one the project looks like it should produce.

The version that uses (c) — the solve as the contribution — needs the game to be
the contribution too, which makes the original designers co-authors and the 2017
course part of the story. That is a different kind of decision and not one this
file can cost.

## 6. How this closes

One of two edits, made after the presentation, dated, and paired with a journal
entry:

- **Not pursued.** Add the date and the reason in one paragraph. This file stops
  being open and the milestone closes.
- **Pursued.** Add the fork's URL and the date. This repository is not modified
  further on account of it — that is the policy's whole point.

Until then the honest status is the one at the top: open, gated on an event, and
written down so it cannot quietly become "we never decided".
