# Decision Journal

Chronological record of decisions that were not obvious, and what they cost.
Distinct from the ADRs: ADRs record *what* was decided and are stable; this
journal records *why it was live at the time*, including things that turned out
to be wrong. Freely editable, append-only.

Raw material for `writeup/main-writeup.md`.

---

## 2026-09-20 — Phase 6 closing: every quantity it set out to estimate was a closed form, and the last three verdicts went in

The phase opened to estimate four things — state space, reachable correction,
game tree, branching distribution — and **not one of them needed a run**. Each
is a closed form, each verified against the engine's own move generator rather
than against itself. That is the phase's single largest fact and it is not a
happy accident: it is what a deck of fixed composition on a board whose hands
exhaust exactly *does* to the counting, and nothing in the Phase 0 plan noticed
that the structure was that rigid.

**Two decisions taken today that were not in the plan.**
`scripts/analyze_archetype_usage.py` is **dropped**. Both quantities it would
compute are fixed by the rules: placement frequency is `[2]×12 + [1]` in every
game, and each archetype is played once by the winner and once by the loser in
all 5,000 EXP-017 games. A script that computes a constant is not an analysis.
And H5's second half, **win contribution, is withdrawn** — registered as the
surviving measure when the frequency half fell on 2026-09-18, and gone two days
later for the same reason the first half went. Worse than vacuous for the
joker: only P1 holds it, so "the joker was played by the winner" is "P1 won",
and the count is 2,712/2,288 — EXP-017's first-player split under another name.
An **alias**, which is a fourth instance of gate 9 and the first one where the
quantity varied but measured something already named.

**Two published figures refused, and the refusals are the table's most useful
cells.** 6×6 Reversi's commonly cited ~10²⁰ state space is **666× above its own
`3^36` ceiling**, which holds before any legality constraint — so the comparison
uses the ceiling and grades the figure `refuted`. Every cell of van den Herik
Table 1 is graded `absent`, because the reproductions this project could reach
disagree by one to two in the exponent and none resolves to the text.
`complexity/comparison.py` carries provenance per cell rather than per table for
exactly this: nine cells are empty with a stated reason, and an empty cell that
says why is worth more than an interpolated one.

**H4's clause 2 is the phase's real finding, and it cost nothing to make.** The
locked ~10⁶¹ is **236× high**, and it is visible with no new measurement at all:
the same hypothesis locks a Knuth–Moore figure of ~10³⁰·⁵, and the two are
mutually inconsistent. Recover `b` from `10^30.5 = b^13` and the full tree comes
out at `10^58.65` — the exact answer, to two decimals, from the hypothesis's own
other number. The statement is **not edited**; hypotheses are locked at
`v0.3-hypotheses` and this is recorded as a deviation.

**`figures/` shipped, and the clause is what made it ship.** Phase 5 planned the
directory as a substitute for three dropped notebooks and produced nothing —
that phase's failed attempt 7. Phase 6 made it a named exit criterion with a
clause attached: *every figure regenerates from a tracked artefact.* The clause
is enforced by `tests/test_figures.py`, not trusted, and it caught a real
defect — `results/*.jsonl`, `data/` and `notes/sources/` are all gitignored, and
a figure drawn from any of them renders on this machine and nowhere else. Seven
figures, one per hypothesis with a verdict plus one support panel.

**Carried to Phase 7, for the second time:**
`exercises/ex05_complexity_analysis.md` and **TIL #4**, both carried out of
Phase 5 and both untouched here. They are author-written material and the phase
produced no hours for them. Phase 7 already owns the TIL pipeline
(*"Polish and publish TILs #1–#5"*), so #4 lands in a phase that was going to
open that file anyway; the exercise does not, and is carried explicitly rather
than dropped.

**Two registry index rows are stale, found in this sweep and not caused by this
phase.** EXP-006 and EXP-012 both ran — their artefacts are on disk and
`docs/research.md` quotes results from both — but their index rows still read
*"registered (blocked on Axis 2)"* and *"registered … not yet run"* with empty
Result columns. The detail entries below them are current. Recorded here rather
than backfilled silently, since a retrospective edit to an index that dates
itself would erase the fact that the rows went stale at all.

The verdict table now has **no empty row**. That is worth stating plainly and
worth not over-reading: three of the six verdicts are *structural* — H4's
bounds, H5 entirely, H6's scope — which means the game's rules answered them and
no experiment could have. A table with no gaps is not the same as a set of
hypotheses that were all well posed.

---

## 2026-09-18 — EXP-007 stopped after six layers: the closed form answered in a second what the run wanted four days for

Started the 5×3 closure the same day Phase 6 opened, and stopped it 429.8 s in,
six layers deep, 0.72% of the configuration space. Three things surfaced in that
window, in the order they mattered.

**The cost estimate I gave was wrong, and wrong in the project's signature way.**
I extrapolated the 3×3's runtime linearly over *number of configurations* and
got ~23 h per arm. The closure's work is not per configuration; it is
`reachable(t−1) × empty cells`, because every marked configuration is expanded
over every legal move. The 5×3 has more empty cells and larger hands, so the
branching enters as a multiplier that a count-based extrapolation cannot see.
Recalibrated on the layer-4 timing: ~89 h. Recalibrated again on layer 5, whose
prediction came in 3% high at 411.3 s against 422 s forecast: **~100 h per arm**,
with throughput already degrading from 335k to 296k expansions/s as the bitsets
grew. This is Phase 4's first lesson — *measure the composed system, not its
components* — recurring on a phase-6 instrument, which is worth recording
precisely because the lesson was already written down.

**The registered decision rule was dead before the run started.** EXP-007's rule
chooses whether don't-cares stay in the adr-012 design. adr-012 chose **Option
B**: no materialised database. There is no don't-care set to drop or keep. This
is the identical status EXP-004 already carries, recorded there as "rule moot"
rather than repointed at some other decision — and EXP-005's rule is moot for
the same reason, which also retires it, since its quantity was proved a counting
identity in August and its 5×3 figure is 0.3428% by closed form. Two of the
three debts Phase 6 opened with dissolve on inspection rather than on compute.

**The surviving reason was H4's bound, and the closed form settles it.** One-step
orphans are `layer(t)/2^t` summed over layers, computable in under a second on
any board: **3.2826%** on the 3×3, **0.3428%** on the 5×3, **0.0079%** on the
shipped 5×5. The fraction falls about two orders of magnitude per board step
because the mass sits at high `t` where `2^t` is enormous. So the shipped board's
state-space bound is 4.887 × 10¹⁷ with the correction and 4.887 × 10¹⁷ without
it, at the precision a table spanning 10¹¹ to 5 × 10²⁰ reports.

**That is the finding, and it is about the gates rather than about FLIPHEX.**
Gate 9 was answered for EXP-007 this morning, correctly: the entry has carried a
falsifier since 2026-08-07 saying the closure must not collapse onto the one-step
identity, which is the gate's question asked six weeks before the gate existed.
And the run was started anyway. The gate was applied to the *measure* and not to
the *decision the measure would inform*. The quantity was free to vary; the
conclusion was not. `docs/measurement-gates.md` is amended to ask both, and the
second question is cheap: compute the conclusion at the measure's floor and at
its ceiling, and check that they differ.

The six measured layers are kept. They are the first transitive-closure figures
on the 5×3 and they match the 3×3's shape, halving per layer from `t = 4`. The
artefact records `complete: false` and the instrument refused to apply the rule
to a partial run, which is the registration working as designed. Completing it
is not scheduled.

---

## 2026-09-18 — Phase 6 opened: H6 adopted because nothing else would own it, and two Phase 3 debts called in

Third entry today. Phase 5 opened, closed and shipped in one day, and Phase 6
opens on the same one.

**The gate check found more than the phase's own carry-overs.** Three Phase 5
deliverables were never started — `figures/`, TIL #4 and `ex05` — and the
roadmap marked all three `[~]`, which reads as partial. Nothing existed. The
marks were corrected to `[ ]` with "not started; carried to Phase 6", because a
tick that overstates is worse than no tick: it is the only record anyone will
read later, and the Phase 5 close was already the place where an unmet exit
criterion got written down honestly. It would be strange to do that for the
criterion and not for the checkbox.

The heavier finding was outside Phase 5 entirely. **EXP-005 and EXP-007 have
stood at "registered; 3×3 pilot run" since 2026-08-05.** Their registered rule
runs on the 5×3 and never has. Three phase closes passed over them because the
close-mode audit walks the closing phase's checklist, and these belong to Phase
3. They surface now only because Phase 6's tightened state-space bound needs
EXP-007's exact reachable closure as an input — which is to say they surfaced by
luck, when a later phase happened to depend on them. Both are adopted as Phase 6
tasks. The procedural lesson is that a registry entry in a non-terminal state is
a debt no phase close is currently responsible for noticing.

**H6 is adopted, and the reason is unflattering.** It had no owning phase at
all. Phase 6's task list names H4 and H5; Phase 7 is interface, writeup and
release. H6 was marked *optional / stretch* when the hypotheses locked, and
"optional" quietly became "unassigned" — the row would have reached the writeup
as a dash with no explanation. Phase 6 is the last phase that can measure
anything, so it takes H6. The material is largely already in hand: four
exhaustive solves across three board configurations and two deck arms, plus the
planned mirror-optimality row that was already tagged H5 *and* H6. The
alternative was a formal withdrawal, and withdrawal is the right move for a
measure the rules have fixed — H5's frequency half — but not for one that was
simply never scheduled.

**The notebook class is closed.** `notebooks/05` is dropped at the open, with
the 02, 03 and 04 before it. One notebook exists out of five planned. The Phase
5 open dropped three of them in favour of scripts under `figures/`, and
`figures/` then delivered nothing, which is recorded as that phase's failed
attempt 7. Dropping the fifth is not the interesting half of this decision. The
interesting half is that `figures/` is now a **named exit criterion** — every
figure in it regenerates from a tracked artefact — rather than a substitution
offered in place of something else. Changing an artefact's format does not
establish a production path for it; only shipping it does.

**H4's wording is not the roadmap's.** The roadmap still says "complexity
comparable to small Reversi". That was reworded at the Phase 2 lock onto both
complexity axes, against a corrected reachable bound of ~4.9 × 10¹⁷ — the
roadmap's original expression carried a `6^25` orientation factor that adr-006
forbids, since placed tiles are inert. The corrected figure sits *below* Reversi
6×6's commonly cited ~10²⁰, so the original claim looks false in a direction
nobody intended when it was written. The locked version in `docs/research.md`
governs, and this phase measures against it.

**Gate 9 is available from the start**, for the first time. It is also the gate
this phase most needs: a complexity bound is a quantity the rules constrain by
construction, and the last measure withdrawn for exactly that reason was H5's
frequency half, on the day the gate was written.

---

## 2026-09-18 — Phase 5 closing: four verdicts, one exit criterion that cannot be met, and a ninth gate

The phase opened and closed the same day, so this entry is contemporaneous.
Everything below was decided today.

### Four verdicts, and the shape of them is the result

| | |
|---|---|
| **H1** | supported on every board where perfect play is computable; not decidable on the shipped 5×5 |
| **H2** | supported on the reduced boards; out of reach by construction on the shipped one |
| **H3** | **rejected**, on both clauses independently |
| **H5** | **true by construction on the measure it names**, and therefore evidence of nothing |

Two positive, one negative, one empty. The negative is the most informative of
the four — a bar fixed in August, an agent measured in September, 14 points
short — and the empty one was caught before it became a figure in a write-up.

**H1 and H2 needed no new computation.** Both rest on four exhaustive solves that
Phase 3 delivered, and the Phase 5 work was reading them honestly: stating the
adr-010 verification coverage rather than saying "V0–V6 passed" flat, and
recording that H1's registered self-play arm **was not performed as written**.

**H3 cost nothing because of one word in its own statement.** The clause says
agreement on *"every member"* of the comparison set. The shipped-5×5 member
already fails. So reading the 3×3 and 5×3 members cannot change the verdict —
which also settles whether to train networks for them: no.

That happens to be moot twice over. The champions are **shape-locked to the
5×5** — `ConvRotationNet` flattens 32 × 25 into a 25-logit head, so a 5×3 raises
a shape error — and the only reduced-board networks this project has were trained
**supervised on solver labels** (EXP-011/012/013), which adr-004 R1 forbids for
the comparison H3 *is*. Neither fact was known when the comparison set was
pre-declared in August 2026, and neither is a defect: the set was fixed before
Axis 2 existed, which is what made it a comparison set.

### The exit criterion that cannot be met, recorded rather than edited away

> *"Solver and AZ agree on the 3×3 game value."*

**Not met, and unreachable with any artefact this project has** — for the two
structural reasons above. Recorded as unmet with the demonstration attached,
which is the same treatment Phase 4's superseded criteria got. **No work is
scheduled to satisfy it**, because satisfying it would mean training self-play
networks on a board whose verdict is already decided by a different member.

The other two criteria: *"every hypothesis has a documented verdict"* is met for
the four this phase owns, with H4 and H6 belonging to Phase 6 by the roadmap's own
assignment; *"where solver and AZ disagree, the disagreement is analysed"* is met
on the only comparison that exists, in EXP-006's Result.

### Scope calls

**`stats/` is dropped.** The roadmap asked for a central module — Wilson, paired
bootstrap, McNemar, Bonferroni. Four phases produced every one of those inline,
and in at least one place the duplication is **deliberate and load-bearing**: an
analysis script that checks a gate must not import the gate's own implementation,
and `tests/test_exp015_analysis.py` asserts the two agree rather than sharing
code. A central module would undo that on purpose. Dropped with the reason, not
carried for a fifth phase.

**`figures/` is carried to Phase 6 as an explicit task.** Four verdicts are
written and not one canonical figure exists. It replaced the notebook
deliverables at the phase open and then went the same way they did, which is the
pattern that decision was meant to break.

**`scripts/eval_joker_impact.py` and `eval_az_vs_solver.py` are dropped**, both
because the phase showed they have nothing to compute: H2 needed no new run, and
AZ-vs-solver at matched depth caps is unreachable on any board where both exist.

**`exercises/ex05` stays unwritten** — the roadmap names the deliverable and
gives it no exercises block, flagged at the open. **TIL #4** joins the standing
standby with ex04 and TILs #2, #3 and #5.

### Gate 9, added the day the gates were first used

The eight measurement gates were adopted at the Phase 4 close and used for the
first time today on EXP-016 and EXP-017. They worked — EXP-016 was withdrawn
before running on a defect the author had not seen — and then **they let the same
class of defect through a third time** in H5.

Gates 1 and 3 ask whether the design can resolve an effect; gate 7 asks whether
the instrument computes what it claims. **None asked whether the quantity was
ever free to move.** Three instances: EXP-006's lost positions (a rule), EXP-016's
root coverage (a budget), H5's placement frequency (a counting identity). One
shape — a number that looked like evidence and could not have come out otherwise.

Added as **gate 9**, with a note in the file saying it was added late and why. A
list that grows without saying why looks designed.

---

## 2026-09-18 — Phase 5 opened, with the gates in force and the notebooks dropped

**Gate.** Phase 4's deliverables are present except the notebook, and the
divergences are documented where they happened: `data/models/az-v*.pt` became
five gitignored run directories reproduced from commit, config and seed
(`docs/submission-log.md` says so), and `ex04` plus TILs #2, #3 and #5 are
problem sets and skeletons held in standby by an explicit author decision —
develop the project end to end first, study the material afterwards.

**Scope call: the notebooks are dropped, all three.** Phases 3, 4 and 5 each
planned one; one exists. That is a pattern, not a delay, and carrying the
backlog forward a third time would be planning against two phases of evidence.
Replaced by scripts in `figures/` producing one canonical plot per hypothesis
from the tracked artefacts — which is how every other number in this project is
already reproduced. Nothing is lost that was being used: the training curves the
Phase 4 notebook would have carried are in `results/exp015-histories.json`,
tracked precisely so they are not trapped in a gitignored run directory, and the
design log quotes them.

**Scope call: H3's training is not repeated.** The roadmap's Phase 5 task says
"repeat AZ training with 5 seeds". EXP-015 did that, and EXP-006 read the
shipped-5×5 member of the comparison set. What remains is the 3×3 and 5×3
members, whose exact solutions already exist at `termination: exhausted`. Phase 5
measures those and writes the verdict. **Re-running the training now would select
on the outcome** — both of H3's clauses came back negative, and a retrain after
seeing that is exactly what the pre-registration exists to prevent. A different
configuration needs a new registered entry and a reason that is not the result.

**The measurement gates are in force from today.** `docs/measurement-gates.md`,
adopted at the Phase 4 close: no Phase 5 or 6 experiment is registered until its
eight answers are written into its registry entry. Two planned comparisons
already fail a gate as sketched, and both are re-scoped before they run rather
than after — H1's twenty seeds cannot resolve a two-point effect at the measured
between-seed variance, and H2's joker-less test is an equivalence claim with no
margin declared.

**Carried from the close, unrepaired by choice:** `v0.7` is double-booked between
Phase 4's `v0.7-az-tuned` and Phase 5's `v0.7-hypotheses-verdicts`, and
`v0.7-az-tuned` names a tuning cycle that never happened. Phase 4 shipped as
`v0.6-az`. Both are `/project-roadmap revise` items and neither blocks this
phase.

**One gap in the roadmap itself, found at the open.** Phase 5's deliverables name
`exercises/ex05_complexity_analysis.md`, and the phase has **no exercises block**
— Phases 2, 3 and 4 each carry one with the actual mathematical prompts. So the
deliverable exists without its content brief. Recorded rather than invented: the
prompts are written when the phase's measurements are known, not now.

---

## 2026-09-18 — Phase 4 closing: three exit criteria unmet, and nineteen days this journal did not record

> **Retrospective entry.** Written at the phase close, not on the days the
> decisions were made. Everything below is reconstructed from
> `experiments/registry.md`, the risk register and the artefacts; nothing in it
> is presented as contemporaneous. The gap it reconstructs is the first item.

**This journal has no entry between 2026-08-30 and today.** Phase 4 opened on
2026-08-30 and ran nineteen days, in which EXP-011, EXP-012, EXP-013, EXP-014,
EXP-015 and EXP-006 were all registered and run, adr-005 was amended twice, four
risk rows were rewritten and one was created. **None of that is in here.**

The decisions were recorded — in registry entries, ADR amendments and risk rows,
all dated the day they were taken, which is why this entry can be reconstructed
at all. What was lost is the thing the journal exists for and the ADRs
deliberately do not carry: *why a decision was live at the time*, including the
options that were not taken. Two examples that are now unrecoverable in their
original form: the choice to let the replay buffer cross generations, and the
choice of equal-simulations as the primary floor with equal-time as secondary.
Both were live decisions with real alternatives; both survive only as settled
facts in a registration.

Recorded as a process failure rather than patched. **A backfilled journal is not
a journal** — writing twelve entries today, dated to September, would produce
exactly the artefact this project exists to avoid.

**The corrective is a habit, not a document:** the journal entry is written the
day the decision is taken, before the registry entry that formalises it. Phase 5
starts with that rule in force.

### All three exit criteria are unmet, and two of them measure something the phase deliberately stopped using

| criterion | status |
|---|---|
| "stable to at least 1M self-play positions" | **unmet.** 150,000 positions per seed, 750,000 across five. 15% of the figure per run. |
| "monotonically improving strength vs `heuristic_agent`" | **not measured.** The gate compares challenger against champion; no run was ever played against the heuristic. |
| "beats heuristic ≥ 90% and beats the depth-capped solver ≥ 50%" | **not measured.** Neither match was run. |
| "two independent runs converge to comparable strength" | **unmet, and the failure is the result.** Five runs converged — policy loss fell 5.05–5.20 → 3.74–3.88 on every seed — and did **not** reach comparable strength: 56.0% to 76.0% against the floor, `χ² = 18.52` on 4 df rejecting a common rate. |

**The first three name opponents the phase replaced on purpose.** `heuristic_agent`
and a depth-capped solver were the Phase 0 sketch of "is it any good". What
Phase 4 registered instead is **prior-free UCT** — which depends on no training,
so a bad run cannot flatter it — and **exact solver ground truth** on 750
positions. Those are stronger opponents and they were chosen for a reason adr-004
R1 requires: the floor had to contain no solver information, or the training run
would have terminated Axis 2 on the dimension of H3's own comparison.

So the criteria are not merely unmet; measuring them now would answer a weaker
question than the one the phase answered. **Unmet-and-superseded**, with the
substitution registered before the run — not dropped.

The fourth is different. It is unmet on its own terms, it was the right criterion,
and the failure is reported as the finding: R6 materialised, H3's stability clause
is not satisfied, and the five rates are in the artefact rather than averaged.

### Deliverables: two diverge, one is missing, four are deferred by choice

**`data/models/az-v*.pt` — diverged, documented.** The checkpoints are at
`data/az-runs/h3-seed{1..5}/`, which is gitignored. They are 27 hours each and
are reproduced from the commit, config and seed rather than restored from the
repository; `docs/submission-log.md` says so in the column meanings. The roadmap's
path assumed a version series and the phase produced five replicates.

**`notebooks/03_az_training_curves.ipynb` — missing.** Not started. The curves it
would carry are in `results/exp015-histories.json`, which is tracked precisely so
they are not trapped in a gitignored run directory, and the design log quotes
them. **Carried to Phase 5 or dropped — author's call**, and the honest note is
that Phase 3's notebook deliverable was deferred the same way and also has not
been written.

**`ex04`, TIL #2, TIL #3, TIL #5 — deferred, deliberately.** All four exist as
problem sets and skeletons with prompts; the content is first-person and is not
being ghost-written. The author's decision at this close was explicit: develop the
project end to end first, study the material afterwards. Recorded so it is a
choice with a date on it rather than four files that quietly never got written.

### Two roadmap defects found at the close

**`v0.7` is double-booked.** Phase 4's GitHub table names `v0.6-az-mvp` **and**
`v0.7-az-tuned`; Phase 5's names `v0.7-hypotheses-verdicts`. Both cannot exist.

**And `v0.7-az-tuned` was never earned.** It presupposes a tuning cycle. There was
none: EXP-015 ran one registered configuration, and the sensitivity sweep over
simulations, `c_puct` and the temperature schedule is a **Phase 5** task that has
not run. Tagging "tuned" here would name work that does not exist.

Both are `/project-roadmap revise` items rather than in-place edits. The tag
proposed for this close is `v0.6-az` alone.

---

## 2026-08-30 — Two registrations red-teamed before a line of code existed, and three failures that had happened here before

EXP-010 and EXP-011 were registered and then red-teamed the same afternoon. Both
were rewritten. Nothing was lost, because no instrument existed yet — the total
cost of the error was drafting two sections of markdown. Recording the defects
because three of them are **recurrences**, and a failure that recurs is about
process rather than about the day it happened on.

**The first: a metric that is a constant on part of its own sample, with the
share unreported.** Both entries scored a move as optimal if the resulting
position is a loss for the opponent. In a position that is *itself* a loss for
the mover, no such move exists, so every arm scores zero deterministically. Worse,
the random-move floor is not a constant either: a parent at `t = 6` moves into
`t = 7`, where EXP-009 measured 75% of configurations as losses for the mover —
so about three quarters of legal moves are optimal and **a random move scores 75%
with no search at all**. At `t = 5` the floor is near zero. A pooled "66% against
64%" would have been a parity-weighted mixture of two floors, with neither number
moved by the thing under test.

This is the third time. V3 reported agreement "on every position compared" and
the comparison was 2–3% of the space. V4 dropped terminal samples with a bare
`continue` and its own numbers stopped adding up to its own sample size. Now a
metric whose floor swings by 75 points across layers, pooled. The pattern is
always the same shape: **the instrument reports a verdict without reporting how
much of its own sample produced it.** Both entries now carry a measured floor, a
stated ceiling, and a per-layer table, and forbid quoting the headline without
them.

**The second: predicting a band from a regime the design excludes.** EXP-010's
first draft predicted 60–80% aliased policy mass, derived as `1 − 1/4.46` from
the collapse at the **5×5 root** — and then sampled `t ≥ 5` on the 5×3, which
corresponds to the 5×5 around ply 8, where the collapse is ~1.8× and the honest
prediction is 20–45%. The prediction would have failed, and the failure would
have read as *"R13 was overstated"* rather than as a regime mismatch. This is the
same reflex as the three wrong explanations of the parity split in Phase 3:
reasoning about a quantity from the side instead of measuring it in the place it
will be measured. EXP-011's cheap no-training number is the antidote and I had
already written it into one entry without applying the idea to the other.

**The third: declaring a threshold with no power to detect it.** The falsifier was
"worse by more than 2 points" at N = 1,000, where McNemar's 80%-power floor is
~3.4 points. So the only branch that could change anything was the one the design
could not see — in an entry whose second line says an experiment that cannot
change the decision is legitimate *only if it is not dressed up as a test*.
adr-005's Phase 2 amendment had already done exactly this arithmetic for the
evaluator gate, and concluded that a gate promoting noise one time in six is
worse than no gate. I read that when writing it and repeated the error anyway,
five weeks later, in a document that cites it.

**Two substantive design changes came out of it, both costing compute, both
worth it.** EXP-010 gains a third arm — children indexed by action but priors
divided by alias multiplicity — because without it a win for deduplication at a
small budget is fully explained by "fewer children", an effect obtainable by
deleting three quarters of the naive arm's children at random. EXP-011 goes from
one seed per arm to five, because the dominant noise there is training-run
variance and no number of positions touches it.

**And one repair I first argued against and then found I was wrong about.** The
red-team suggested moving both entries from the h1 arm to h2, which has the
principal-variation audit and the recurrence check. I objected that h2 has no
joker, and the joker is the inert tile par excellence — the thing EXP-011's
rotation number is about. That was backwards. The joker's rotation orbit is 1, so
it changes nothing *by orbit*, which is a definitional artefact and not the
inertness mechanism adr-005 describes. The mechanism only shows up in tiles with
orbit > 1. Counting: h1's P1 deck holds two single-orbit tiles in eight, h2's
holds one. h2 is both better verified **and** less contaminated, and my objection
had the sign inverted.

**The last one is not a recurrence, and it is the one worth keeping.** EXP-011's
first draft argued anti-circularity compliance because "every network trained
here is discarded". Weights were never the thing at risk. What survives an
experiment is its **decision** — and an architecture chosen by agreement with the
solver on the 5×3 is selected on 5×3 solver agreement, which H3 later reports as
evidence, because the 5×3 is in H3's comparison set. adr-005 point 4 names
checkpoints; adr-004's general form names the dimension, and it is the general
form that binds. The leak was one ternary choice among fallbacks the ADR had
already enumerated — small, and repairable only by saying so, which both entries
now do.

---

## 2026-08-30 — Phase 4 opened, and the axis changes character

**Two carry-overs from the Phase 3 gate, both deliberate.**

TIL #2 and TIL #3 stay unwritten and move into Phase 4. TIL #2 is *MCTS in
perfect-information games*, and Phase 4 is where MCTS gets built — writing it
from Phase 3's reading would have produced a summary of Silver 2017 instead of
something learned. TIL #3 rides along rather than being written alone. This is
the second time a TIL has been deferred for material rather than for time, and
both times the deferral was right; noting it because a third would be a pattern
worth distrusting.

`v0.4-solver-mvp` is being backfilled onto `ac6e571`, the commit at which the
3×3 was solved and double-solved with V0/V1/V2/V3/V5. The tag was never made at
the time because there was no moment that felt like an MVP — the 3×3 and the 5×3
landed in one continuous stretch and the 3×3 read as a fixture, not a
deliverable. That reading was wrong on the roadmap's own terms: the 3×3 solve
*is* the exit criterion Phase 3 was written around. The tag is marked
retrospective in the release notes rather than presented as contemporaneous.

**The measurement problem inverts.** Axis 1 could be wrong without crashing, so
Phase 3 spent most of its apparatus on verification — V0–V6, double-solves,
digest replays, cross-arm comparison. Axis 2 cannot be verified that way: there
is no exact answer to check a learned policy against on the shipped 5×5, which
is the entire reason H3 exists and the entire reason its comparison set had to be
enumerated in advance. The discipline that replaces verification is
**pre-registration plus the anti-circularity rule** — checkpoint selection may
not read Axis 1 (adr-005 Phase 2 amendment, point 4). That rule costs something
real: the exact 5×3 database is sitting right there, free to query, and it is the
one yardstick that would make training decisions easy. It stays unused for
selection and is logged as a diagnostic only.

**Phase 4 inherits one open risk at the top of the register.** R13 — the action
space is 4.46× aliased at the root — was measured at the end of Phase 3 and is
entirely a Phase 4 problem. It is worth stating plainly what makes it a risk
rather than an inefficiency: the aliasing does not merely waste simulations, it
*biases* them, and then the training target is read off the biased counts. A
position reachable by six rotations collects six priors and six under-explored
children. The naive implementation would train the network to spread policy mass
across labels that denote the same board. Deduplicated expansion is therefore not
an optimisation to schedule later; it changes what the pipeline learns.

**One thing the roadmap assumed and reality has not yet supplied.** Phase 4 was
written around "the author's laptop GPU", and the ADR sized the network so that
two independent seeds would be "realistic rather than aspirational". Neither
`torch` nor a visible CUDA device exists in the working environment today. That
is the first task of the phase and it is a genuine fork: if training runs on CPU,
the ≥5-seed requirement in H3 is the constraint that breaks first, and it breaks
a *pre-registered* quantity — so any relaxation has to be argued in the registry,
not absorbed silently into a smaller run.

---

## 2026-08-30 — Phase 3 closing: three exit criteria the phase outgrew

**The roadmap asked for H1/H2 partial verdicts; they are not being written.**
`docs/research.md` says the Verdicts table stays empty until Phase 5, and
`experiments/registry.md` says H2 is reported from criticality rather than from
two roots agreeing. Both were written before any 5×3 arm ran; the roadmap's
request was written in Phase 0, before the hypotheses locked. **The earlier and
more specific rule wins** — that is the whole point of pre-registration, and a
verdict entered now would be entered by someone who already knows the answer.
What Phase 3 delivers instead is the *inputs*: an exact value on a 15-cell board
verified six ways, a criticality of 17.07%, and 10.26 × 10⁹ cross-arm positions
agreeing. Phase 5 reads them.

**Two exit criteria named an artefact that adr-012 deliberately did not build.**
"Retrograde database covers at least positions with ≤ 5 pieces remaining on 5×5"
and "alpha-beta agent + endgame database beats random and heuristic ≥ 90%" both
assume the endgame database. `EXP-003` measured the cost of searching instead of
storing — 480 nodes at `k = 5`, against a database of ~1.2 × 10¹⁵ positions and
~150 TB — and adr-012 took Option B. The first criterion is therefore
**consciously dropped**, with a measurement behind it rather than a shrug.

The second is not dropped, because the half of it that survives is worth
knowing: how strong *is* an exact agent with no database? That is `EXP-008`,
registered at this close and run. Recording it as unmet-and-measured is more
useful than recording it as inapplicable.

**Three deliverables are deferred rather than dropped**: TIL #2 and #3, and
`notebooks/02_solver_debugging.ipynb`. Skeletons exist; the content is
first-person and is not being ghost-written.

**`EXP-004` ran, and its decision rule is moot.** It was registered to choose
between adr-012's Options A and C. adr-012 chose **B**, so there is no longer a
decision for it to inform. It is kept as a measurement — 2.00 bits/position raw,
3.04× under block-RLE, 9.10× under a general-purpose block coder — and reported
as descriptive, with the dead rule stated rather than quietly reinterpreted into
something the numbers could satisfy.

---

## 2026-08-28 — Interim peek at the h1 re-run, and what the clock is made of

**No decision is taken here.** The h1 sweep is 13.7 h in and unfinished; this
records what was looked at so a later reader can see the peek happened and that
nothing was conditioned on it. EXP-002's registered measures — the digest replay
and the H2 criticality — need the complete sweep and are untouched.

**What was read: wall-clock only.** Six layers done (15 down to 10) in 12,906 s,
against h2's 13,245 s at the same point — h1 running 2.6% ahead. Layer 9, the
largest at 5.02 × 10⁹ configurations, has been running 10.1 h; h2 spent 16.4 h
there. Process CPU time equals elapsed time to the second, so nothing has been
suspended. No outcome data was read: both arms' root values were published on
2026-08-09 and 2026-08-13, and criticality is not visible until the sweep ends.

**The timing profile is a parity signature, not noise.** h2's per-layer
throughput alternates violently — 785k cfg/s at `t = 10` against 84.9k at
`t = 9`, 1,055k at `t = 8` against 46.8k at `t = 7`, and the gap widens going up:
9.2×, 22.5×, 66.8×, then 166× between `t = 4` and `t = 3`. Every slow layer is
odd, every fast one even.

The mechanism is in `solver/packed_sweep.py:385` — the child scan is
`while remaining and slot == SLOT_LOSS`, breaking out of all three nested loops
the moment a losing child appears. A position that is a **win** stops at its
first winning move; a position that is a **loss** must enumerate every
(cell × tile × rotation) before it can say so. Cost per configuration is
therefore a direct read-out of the win/loss mix, and odd `t` is P2 to move.

**Measured 2026-08-30, and the guessing stops here.** This entry first said "the
sweep is slow exactly where the mover is mostly lost", then a same-day correction
replaced that with "odd layers are mixed". Both were inferences from side
effects. `EXP-009` counts the values directly:

| t | 0 | 1 | 2 | 3 | 4 | 5 | 7 | 9 | 11 | 13 | 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| WIN % for the mover | 100 | 0 | 100 | 0 | 100 | 4.75 | 24.92 | 46.36 | 57.01 | 59.57 | 50.00 |

**Layers 0 through 4 are uniform.** Not "mostly" — every one of the 12,841,920
configurations at `t = 4` is a win for P1, and every one of the 713,440 at
`t = 3` is a loss for P2. Uniformity breaks at `t = 5` and the two parities then
converge monotonically toward 50/50 as the board fills.

So the first version was right about the shallow layers and the correction was
right about the deep ones, and neither was right as stated. The lesson is not
about the game: **four instruments circled this for two days and the direct
measurement took 70 seconds.** Runtime, criticality, and compression ratios are
all downstream of the value mix, and reading a cause off three different
downstream effects produced two wrong statements before anyone counted.

Two things fall out for free. Criticality is exactly zero on layers 0–4 and first
becomes non-zero at `t = 5` — the same boundary, from an instrument that shares
no code with this one. And block-RLE gets 120× at `t = 3` and `t = 4` and 11.64×
at `t = 5`: compression tracks uniformity precisely, which is what it was
measuring all along.

Two things this is **not**. It is not evidence for H1: it describes the
enumerated configuration space, most of which is unreachable, not the game. And
it is not evidence for H2 — criticality is a position-by-position comparison
between the arms and the clock says nothing about it. The residual 18% gap
between the arms at `t = 11`, where both hands are identical, is the deck showing
through the *values* rather than through the branching, which is the same
mechanism seen from the other side.

Worth keeping because it makes the runtime predictable for the first time: the
5×3's cost is not "17.5 × 10⁹ configurations" but "however many of them are
losses", and that is a property of the game, not of the machine.

---

## 2026-08-05 — The endgame database is cancelled, and H3 comes out better

`EXP-003` ran the full registered sweep and the answer is not close. Median nodes
to prove one 5×5 endgame position exactly: **480** at `k = 5` — the layer whose
database would be ~1.2 × 10¹⁵ positions and ~150 TB — and 806,474 at `k = 8`.
`k* > 8`, the pre-registered prediction (`k* ≥ 6`) held, and adr-012 takes
**Option B**: no endgame database is built. Twelve orders of magnitude is not a
constant factor to engineer away.

**The consequence I had pre-recorded fired, and forced a better design.** adr-012
said in advance that if the crossover was out of reach, H3 would lose the "5×5
retrograde endgame layers" member of its comparison set — the member the Phase 2
amendment added specifically so H3 would not rest on toy boards. Writing the
re-scope, I noticed the member H3 loses and the member H3 *needs* are not the
same thing. What it needed was **exact ground truth on the shipped game**; the
database was only the assumed way to get it. EXP-003 supplies a cheaper way:
solve sampled endgame positions on demand.

So H3's set becomes 3×3, 5×3, and 500 shipped-5×5 positions at `k ≤ 8` solved at
query time (`EXP-006`). That is stronger than what it replaces. The retrograde
route would have delivered whatever `k` the disk allowed, discovered afterwards;
the sample is fixed in advance at a `k` already measured to be affordable. And
because `solver/minimax.py` proves or raises rather than approximating, every
value in the set satisfies adr-004 R1 by construction instead of by audit.

I registered EXP-006 **before Axis 2 exists**. A comparison set fixed after
seeing the learner is not a comparison set. Two choices inside it that could
easily have gone unexamined: it uses **seed 2**, not EXP-003's seed 1, because
evaluating the learner on the very positions whose cost justified the design
would be circular; and positions come from **random play, not the learner's own
play**, because sampling from self-play lets Axis 2 choose its own exam. The
learner-distribution version is a more interesting question and is a *different*
experiment — it needs its own ID and may not be substituted for this one.

**An instrument defect, found by the analysis rather than by the run.** The
experiment printed `cens 0` for every `k` while `k = 8`'s no-TT arm had one
sample pinned at the 20M budget: the column showed only the with-TT count. The
JSON recorded it correctly per arm, which is the only reason it was recoverable,
and the analysis script's validity guard caught it on first execution. No re-run
— the rule reads the with-TT median, that arm is uncensored everywhere, and one
censored sample in 200 cannot reach a median anyway.

I got it wrong in both directions on the way through. The display hid censoring;
then my first guard hard-failed on *any* censoring, which would have thrown away
a perfectly usable result. The right criterion is the producer's own
`median_is_lower_bound`, with the individually affected statistics named — `max`
here, not the median. Both are now pinned by regression tests.

**Secondary finding, exploratory and labelled as such.** The transposition
table's value grows with `k`: 1.03× at `k = 3` to 2.15× at `k = 8`. Inside a
single deep-endgame search there is almost no path re-convergence — the subgame
graph is nearly a tree — and it only appears as empty cells accumulate. This does
*not* settle the database case by itself: a database sells reuse across different
roots, which is a different quantity from re-convergence within one search. Worth
keeping the two apart.

---

## 2026-08-05 — The 4×4 was never a FLIPHEX board

A pre-run red-team of `EXP-001`/`EXP-002` — deliberately before either ran —
found that the exact-solve target Phase 2 had just promoted is not a variant of
this game.

**16 is even, so draws are possible, and there is no tie-break.** `rules-canonical.md`
derives the impossibility of draws entirely from 25 being odd; `adr-010` V2
asserts the invariant totally and even says any `N` used must be odd;
`fliphex/rules.py` raises on a tied terminal. And `C(16,8) = 12,870` of the
4×4's 65,536 terminal configurations are 8–8 ties, about 20%. Phase 2 shipped
that contradiction inside itself: `adr-009` set `a = 8` on a 16-cell board while
`adr-010` was being written two documents away requiring odd `N`. Nobody
introduced the bug; it existed in the gap between two ADRs written the same week.

**Worse, the 4×4 deletes the mechanism H1 names.** The rules say the joker is the
25th tile and 25 is odd, so *the joker is what gives P1 the extra ply*. With
8 + 8 and no joker, P1 has no extra ply and **P2 places the last tile** — on the
fullest board, where flip power is maximal. So H1 could not lose there: "P1 wins"
reads as support, "P2 wins" gets dismissed as a parity artefact. An experiment
that cannot fail is not an experiment.

**A correction to the red-team, which was worth making.** It predicted the
4-column board had no symmetry at all. `scripts/check_symmetry.py 4 4` says
`|Aut| = 2` — but the automorphism is a **180° rotation**, not a reflection, the
exact opposite of the 5×5. Rotations map a tile's arrow pattern to another
rotation of the same tile, so the chiral `P3-y` cannot break one. `adr-009` keeps
`P3-y` in every reduced deck to "keep the mirror question alive"; on the 4×4 that
reason is void, for a different reason than the one proposed.

**The fix is better than the thing it replaces.** `adr-011` (Accepted the same day): reduced
boards must be odd, and the hands mirror the shipped game — P2 draws `a`
archetypes, P1 draws the same `a` **plus the joker**. Then `(a+1) + a = N`, both
hands exhaust exactly, P1 moves last, and P1's extra tile *is* the joker. That is
the 5×5's own structure at smaller scale. The 5×3 (15 cells) becomes the primary
target: same Z/2 mirror as the 5×5 (A↔E, B↔D, C fixed), `P3-y` breaks it again,
and 1.75 × 10¹⁰ against the 4×4's 9.3 × 10¹⁰ — cheaper *and* faithful.

It also fixes H2, which I had registered without a second arm. The contrast is no
longer "joker present/absent" — on an odd board you cannot remove the joker
without leaving the board unfillable. It is **what P1's extra tile is**: the
zero-arrow joker, or the next archetype. Both arms have `a+1` and `a` tiles, so
the two state spaces are *exactly the same size*. That isolates the joker's
strategic content from the structural extra ply, which is the distinction the
rules draw and which the old design confounded.

**And a number that was right all along.** `adr-004` and `adr-010` both quote
7.1 × 10⁵ for the reduced 3×3 — reproducible only with hands 5 + 4, which
`adr-009`'s "identical decks, `a = ⌈N/2⌉`" rule does not produce (it gives 5 + 5
and 1.47 × 10⁶). The documented figures had always assumed the rule adr-011 now
writes down. The rule was wrong, not the numbers.

**Two errors of mine in the registered entries**, both caught before running:
EXP-001's terminal layer read 512, which is `2⁹` and only correct if the hands
are exhausted — the full-deck 3×3 terminal is **326,177,280**, and a solver that
dropped the hand dimension there would pass V0 against my wrong number. And I
gated both entries on adr-010 V1 without noticing V1 is not decidable as written:
the closed-form bound counts configurations, so a *correct* reachable-closure
enumerator disagrees with it by exactly 2× at layer 1. "V1 must pass" had no
truth value.

---

## 2026-08-05 — Maybe there should be no endgame database

A literature scout on the endgame storage format came back arguing the format is
the wrong question.

**Othello.** Takizawa (2023) weakly solved Othello 8×8 with forward alpha-beta
and transposition tables, resolving positions at 36 empty squares and referencing
them from shallower search — and **materialised no endgame database**, having
judged a strong solution intractable. Othello is FLIPHEX's structural twin:
diverging, fixed termination, cells only fill, `k` empty ≡ ply `N − k`, hump
profile. It is the only game with that shape that has been solved, and it did not
use the artefact I was about to spend Phase 3 designing. It was not on the Phase 2
reading list; it should have been.

The arithmetic agrees. `k ≤ 5` is ~1.2 × 10¹⁵ positions, ~150 TB at one bit, and
each extra `k` costs 8–15×. Meanwhile the subtree below a `k = 5` node is order
10⁵–10⁷ nodes. A tablebase pays by amortising probes; here the search that would
probe it may be cheaper than decompressing a block.

**Three techniques that do not transfer, and I would have imported all three.**
(1) Predecessor-driven propagation with successor counters exists because chess
and checkers slices contain *cycles*; FLIPHEX layers form a DAG, one sweep
suffices — and `adr-003` discards tile identity, so un-placing is not even
locally invertible. Pull, not push. (2) The don't-care trick works because
"broken" is an O(1) *local* predicate in chess; FLIPHEX unreachability is
**global**, needing a path from ply 0. (3) Folding the mirror saves 50% against
8–15× per `k` — less than half a ply of depth, at a cost on every probe.

`adr-012` (Accepted the same day) therefore decides *not to decide*: three cheap measurements
(EXP-003 subtree cost, EXP-004 real compressibility, EXP-005 don't-care yield)
choose between building, not building, and a symbolic representation. One thing
it does fix now because it cannot be retrofitted: **V1's reachability count is
taken before any don't-care filling**, or the distinction between "unreachable"
and "computed" is destroyed.

The risk I am accepting, recorded so it is not discovered later: if the crossover
turns out to be beyond any reachable `k`, Axis 1 ships no endgame database, and
H3 loses the "5×5 endgame layers" member of its comparison set — the member the
Phase 2 amendment added specifically to stop H3 resting on toy boards.

---

## 2026-08-05 — Phase 3 opened

**Gate.** Phase 2's deliverables are all present: the four lit-notes and the
synthesis, `research.md` with H1–H6 locked under the `v0.3-hypotheses` tag, and
the TIL #1 draft. One item is short of the roadmap's wording.

**Carry-over: the exercise answers stay open, with no phase owner.** `ex01` and
`ex02` exist as problem sets; the answers are empty. The roadmap's task says
"complete `ex02`". Deliberately *not* carried into Phase 3 as a task and
deliberately not dropped either — Phase 3 will produce `ex03`, and making three
open sets compete for the same hours is how all three stay open. What the lock
actually needed from `ex02` was the corrected state-space bound, and
`scripts/layer_profile.py` supplies that independently, so nothing downstream is
waiting on them.

**Divergence from the roadmap.** Phase 2 ran on `phase-2/solver-reframe`, not the
planned `phase-2/study-and-hypotheses`, and the PR title followed the branch. The
phase turned into a solver-scoping phase somewhere around the Allis note. Not
patched in place — it is a `/project-roadmap revise` item.

**Scope call: verification is a first-class deliverable, not a test file.**
adr-010's V0–V6 got its own issue rather than riding along inside the solve
issues. The reason is the failure mode: a 4×4 solve emits one verdict out of
~10¹¹ states, and a wrong one looks exactly like a right one. If verification is
a subtask of "solve the 4×4", it gets done by whoever is trying to finish the
4×4, which is the wrong incentive.

**Open decision, ADR-shaped.** The endgame database storage format. adr-004
commits to retrograde analysis but says nothing about indexing, compression, or
how mirror folding interacts with the two. `k ≤ 5` on the 5×5 is 1.2 × 10¹⁵
positions in the bound; the gap between that and reachability (adr-010 V1) is
what decides whether this is feasible at all. Flagged now so it is decided before
code, not around it.

---

## 2026-08-05 — Phase 2 closing: four corrections and a numeric erratum

*Written the same day as the merge, after the fact.* Writing the refined
write-ups for `notes/phase2-synthesis.md` turned into an audit, and four things
that were already in the repo turned out to be wrong.

**The state counts were computed with both hands at 13.** Player 1 holds 13
tiles (12-tile deck + joker); Player 2 holds **12**. Three documents had used
13/13. Corrected: 3×3 full deck 3.1 × 10⁹ → **2.3 × 10⁹**; 4×4 full deck
8.3 × 10¹³ → **4.8 × 10¹³**. The reduced-deck 9.3 × 10¹⁰ and the headline
5×5 4.9 × 10¹⁷ were right. Found by writing `scripts/layer_profile.py` and
running it — not by re-reading. The 2026-07-31 entry above still carries the old
figures; it is left as written, because this journal records what was live at the
time.

**The same error had inflated the mirror argument.** I had reasoned that one
player could finish holding an unplayed `P3-y`, giving P(the mirror is never a
valid game symmetry) = 1/13 ≈ 7.7%. Every tile reaches the board, so that case
does not exist. E[fraction of plies where the mirror is valid] 0.29 → **0.31**,
effective augmentation 1.29× → **1.31×**, P(never valid) = **0**. The conclusion
— no clean 2× augmentation for Axis 2 — did not move, but it was resting partly
on a case that cannot occur.

**`k ≤ 3` was mislabelled.** 9.0 × 10¹² is the *exactly*-k=3 layer; the
cumulative slice is 9.4 × 10¹². The R&N note had it right and the Schaeffer note
and S3 conflated them.

**I had the proof-number-search argument backwards.** adr-004 said FLIPHEX has no
sudden-death goal, therefore PN-search offers no edge. That inference is wrong:
PN-search exploits tree *shape*, and Schaeffer used Df-pn on checkers, which has
no sudden-death goal either. What actually parks PN-search here is that FLIPHEX
enumeration has no scheduling problem to solve. Corrected in the amendment rather
than quietly rewritten.

**Two circularity traps, closed with one rule.** Axis 2 must not gate checkpoint
selection on Axis 1's solved values, and Axis 1's proof-producing runs must not
be seeded by Axis 2. Both are instances of: *neither axis may be used to select
or terminate the other along the dimension on which they are later compared*
(adr-004 R1/R2/R3, adr-005 amendment). H3 is the hypothesis that would have been
silently destroyed.

**adr-010 exists because a wrong answer will not crash.** Six mechanisms, V0–V6,
and — drafted before any result exists — the strongest sentence a single
implementation run once is entitled to write. It ends: "It has not been
independently reimplemented."

**What the phase actually was.** Planned as a study week. It became a scoping
phase: 4×4 promoted over 3×3, the problem reclassified as storage-bound rather
than search-bound, and the verification apparatus specified before the thing it
verifies.

---

## 2026-07-31 — Allis reframes the solver: 4×4 is the real target, not 3×3

Filling in the Allis lit-note surfaced four questions from the co-designer, and
two of them moved ADRs.

**The state-space bound, verified on paper.** Reconstructed the ~4.9 × 10¹⁷
figure from scratch to answer "why isn't it just 3²⁵?". The answer: a FLIPHEX
state is *not* colour-per-cell — because flips detach a cell's colour from who
placed it, the hands (which tiles each player has spent) are independent state.
`3²⁵ ≈ 8.5 × 10¹¹` is only the board; the hand factor (~5.8 × 10⁵) lifts it to
`Σ_t C(25,t)·2^t·C(13,⌈t/2⌉)·C(12,⌊t/2⌋) = 4.89 × 10¹⁷`. The `2^t` is the
upper-bound step — it treats every 2-colouring as reachable, which flip dynamics
do not guarantee. So the number is an honest *upper bound*, not Allis's exact
state-space complexity; the true value would need his Monte-Carlo method.

**4×4 is the strategically meaningful exact solve.** Swept the bound across board
sizes and found the full-enumeration frontier at N ≈ 13–15. 3×3 (9 cells,
3.1 × 10⁹) is trivially solvable but too cramped for real tactics — it is a
correctness fixture, not a strategy microcosm, and I was previously letting it
carry more weight than it can bear. 4×4 (16 cells, 8.3 × 10¹³ full deck /
9.3 × 10¹⁰ reduced) is both enumerable and rich enough for spatial/tempo play.
Promoted 4×4 from "attempt" to the primary exact-solve target for H1/H2
(adr-004 Phase 2 amendment; research.md Phase 2 amendment).

**Allis confirms alpha-beta over pn-search.** FLIPHEX is diverging +
fixed-termination (the Othello profile). Proof-number search earns its keep on
sudden-death goal-proving (qubic, go-moku); FLIPHEX has no such goal, so the
reading *strengthens* adr-004 rather than reopening it. Also corrected adr-004's
stale "trivial symmetry group" line: the Z/2 mirror (adr-008) is usable for TT
folding precisely in the endgame DBs, where both P3-y are placed.

**The reduced-deck gap is now explicit (adr-009, Proposed).** "Proportionally
smaller decks" was hand-waved in adr-004. It swings the 4×4 bound by ~3 orders of
magnitude and decides whether a reduced solve is a faithful shrink — so it needed
an ADR, not a default buried in code. Proposed policy: always keep P6 (max flip)
and P3-y (the chiral symmetry-breaker), fill by ascending arrow count. Flagged
OPEN-3: is a reduced board a physical variant or a purely computational device?

**Variants promoted to an optional hypothesis (H6).** The co-designer's "what if
we change the pieces or grow the board?" is the design-space question that lifts
this above "an agent for my game". Turned it into H6 — a *robustness* claim
(does the balance keep its sign under bounded perturbation?), guard-railed:
tested only after H1–H5 settle on the shipped 5×5, shipped game as fixed
baseline, analyse-don't-redesign. Droppable at lock without touching the spine.

---

## 2026-07-29 — OPEN-2 resolved, and a correction to adr-008

Two things, same day, tightly linked.

**OPEN-2 is resolved.** The two decks were cut from the same mould, so their
chiral `P3-y` tiles are *identical* (same chirality), not mirror images — both
players hold `(0,1,3)` on their own face. Consequence: **no deck confound for
H1**; it is a clean first-move (plus joker) question and does not split into
H1a/H1b. This clears the last blocker to locking the Phase 2 hypotheses.

**Correction to adr-008.** Working out the OPEN-2 consequence exposed an error I
had made: I claimed the board's Z/2 mirror gives the *game* a 2× augmentation
"conditional on OPEN-2." Redoing the arrow algebra, the chiral `P3-y` breaks the
mirror at the dynamics level **whenever it is still in a hand**, independent of
OPEN-2 (its reflection {0,3,5} is not a rotation of {0,1,3}, and no player holds
the reflected tile). The mirror is only a *partial* symmetry — valid on the
sub-game after both `P3-y` are placed and inert. OPEN-2 governs *seat
equivalence* (H1), not the augmentation. adr-008, `research.md` (dropped the
symmetry hypothesis), and the geometry prose were corrected.

Caught it before the lock, which is the point of the discipline — but noting it
as a genuine over-claim I made and then had to walk back.

---

## 2026-07-29 — The board is not asymmetric: it has a mirror (Z/2)

Studying AlphaZero — which *drops* symmetry augmentation because chess and shogi
are asymmetric — I stopped trusting the Phase 0 prose and actually computed the
board's automorphism group (`scripts/check_symmetry.py`). Phase 0 said the
symmetry group was **trivial**; it is **Z/2**. There is a left-right mirror
across column C (A↔E, B↔D, C fixed; NE↔NW, SE↔SW). 180° is genuinely not a
symmetry (columns B/D are staggered half a cell; and 25 is odd, so an involution
must fix a cell — the mirror fixes column C).

The Phase 0 argument ("A/C/E and B/D have different vertical centres") only ruled
out symmetries that *mix* the two column groups. The mirror stays within each
group, so the argument never applied to it. The doc even lists the counterexample
unknowingly: A1 and E1 are the two degree-2 cells and are each other's mirror
image.

Recorded as **adr-008 (Proposed)**. The subtle, project-elevating part: the
board-level mirror is unconditional, but the **game-level** symmetry is
conditional on **OPEN-2** — the chiral P3-y tile is the one piece whose mirror
leaves the deck. So OPEN-2 now gates two things: the H1 seat-asymmetry confound
*and* whether we get the 2× self-play augmentation / mirror-canonical
transposition. If it holds, FLIPHEX sits between chess (1×) and Go (8×). H1 is
unaffected either way — the mirror preserves the player to move, so it gives no
strategy-stealing argument.

This is also the second time a Phase 0 "fact" fell to a concrete check (after the
flip-rule toggle, adr-007). Pattern noted: validate load-bearing claims by
computation, not prose.

---

## 2026-07-29 — Thesis reframe: self-play as a game-design instrument

Reading AlphaZero shifted the project's centre of gravity. The compelling story is
not "apply AlphaZero to my game" (a common exercise) but "use self-play and exact
search as instruments to *understand and validate the design* of an original,
un-analysed game" — its first-player balance, joker effect, board geometry, and
tile distribution. Strong play becomes the means; understanding the design is the
end. H1/H2/H5 (already design-balance questions) become the spine; H3 is the
cross-axis honesty check; H4 situates the game; a new optional H6 turns the
adr-008 mirror into a testable sample-efficiency claim.

Applied to `docs/research.md` as the pre-lock working version (added a Thesis
section, promoted H1/H2/H5, made H3's multi-seed/Wilson-CI rigour explicit, added
H6, and corrected the symmetry amendment for adr-008). Guardrails held: analyse,
do not redesign; the shipped 5×5 first, variants as a stretch; keep a fixed
benchmark. Not yet locked — the lock waits on `OPEN-2` and lands at
`v0.3-hypotheses`.

---

## 2026-07-25 — Phase 2 opened

Study phase. Gate check on Phase 1 passed: engine, both agents, and 71 tests
present; `smoke_selfplay.py` covers the 1000-games criterion. Two carry-overs,
neither blocking:

- The `01_rules_and_geometry` notebook stays deferred to Phase 7 (decided at
  Phase 1 close, above).
- The "heuristic beats random ≥60%" exit criterion was never measured — only
  random-vs-random invariants were checked. Added as a Phase 1 close item (a
  short win-rate check) rather than assumed.

No new technique decision enters Phase 2 that needs a `literature-scout`
dispatch up front — the ADRs already fix the design. Instead the phase's job is
the *reverse*: read the founding literature (R&N Ch.5, Silver 2017/2018, Allis
1994, Schaeffer 2007) with one `lit-note` per source, and let any source that
contradicts adr-004 or adr-005 trigger an ADR amendment. `literature-scout`
stays available for any ADR the author decides to actively re-litigate.

No experiment runs this phase, so nothing is registered in
`experiments/registry.md` — the first entries arrive with the Phase 3 solver.

**Blocking exit condition:** OPEN-2 (are the two decks' chiral `P3-y` tiles
mirror images?) must be resolved on the physical board before H1–H5 lock at
`v0.3-hypotheses`. It is a live confound for H1 and cannot be deferred past the
lock.

---

## 2026-07-25 — Phase 1 closing: scope calls

Engine, both baseline agents, and the full test suite are done, and the flip
rule was validated by hand-play (see the toggle entry below). Two closing
decisions:

- **CI landed now** (`.github/workflows/ci.yml`): ruff, pytest, and a
  generated-docs-clean check. Worth having before the Phase 2 study work so the
  branch stays honest.
- **The `01_rules_and_geometry` notebook (#12) is deferred to Phase 7.** The
  hotseat CLI already gives interactive visual inspection of geometry and the
  flip rule, so the notebook's value now is presentational, not correctness. It
  travels with the UI/portfolio work.
- The "1000 random games" exit criterion is covered by
  `scripts/smoke_selfplay.py` (run once: 1000 games, all invariants held, ~11s)
  rather than a slow pytest case, keeping the suite fast.

---

## 2026-07-25 — Play-testing caught a wrong core rule: flip is a toggle

Building the hotseat CLI before training any agent paid off on day one. Playing
a two-human game, the co-designer noticed the 6-arrow tile placed among his own
pieces changed nothing, and questioned whether an arrow should flip a same-colour
tile.

Investigation confirmed the engine did exactly what Phase 0's `rules-canonical.md`
§4 told it to: a flip was an **assignment** to the placing player's colour, so
aiming at your own tile was a no-op. That was my error. The tiles are two-sided;
the poster says the pointed tile is *"virada (flipada)"* — **turned over** —
which inverts its colour unconditionally. An arrow at your own tile therefore
hands it to the opponent.

Fixed as a **toggle** (adr-007): one line in `apply_move`, plus the rulebook,
`engineering.md`, the greedy heuristic (now maximises net swing = opponent flips
minus self-flips, or it would damage itself), and the flip tests. Nothing
structural moved — toggle only changes colours, so adr-003's representation and
the state-space bound are untouched.

The lesson is the whole reason the CLI came before the solver and the network: a
subtly wrong core rule would have been learned faithfully by every agent and
silently poisoned every hypothesis verdict. "Play the game by hand first" earned
its place in the plan.

---

## 2026-07-25 — Phase 1 opened

Phase 0 shipped (tag `v0.1-foundation`, clean linear history). Gate check for
Phase 1 passed with no carry-overs — all 16 Phase 0 deliverables present.

Scope decision: keep the roadmap, the local tooling config, and `FLIPHEX.pdf`
local only (gitignored, purged from remote history via force-push). The remote is
the public artifact; the project direction and tooling are not part of it.

No open technique decision enters Phase 1 — the six ADRs already fix the engine
design — so no `literature-scout` dispatch here. Literature grounding (and any
ADR rebuttal) is deferred to Phase 2, as recorded in the roadmap's Phase 1
`lit-note` note.

---

## 2026-07-23 — Phase 0

### The physical artifact outranks the written rules

The 2017 poster carries both photographs and a prose rulebook, and the author
flagged the prose as out of date. Set an explicit precedence order in
`rules-canonical.md`: photographs > author's decisions > poster prose. Every
divergence is tabulated in §9 of the rulebook rather than silently resolved.

This mattered immediately — the roadmap described a "5-row zigzag", but the
photographs show flat-top hexagons in five *columns*. Same 25 cells, transposed,
different direction indexing. Reading the rules text alone would have produced
a subtly wrong engine.

### The deck turned out to be a theorem

The roadmap deferred "3 distinct archetypes — TBD" for the 2-, 3-, and 4-arrow
pieces, and the plan was to pick them by inspecting the physical tiles.

Counting first was better. Arrow patterns on a *two-sided* hexagonal tile are
equivalence classes under rotation **and** reflection — binary bracelets of
length 6 — and there are exactly 1, 3, 3, 3, 1, 1 of them with 1 to 6 arrows.
That is the poster's deck composition, term for term. The deck is not a
selection; it is the complete enumeration. Nothing was left to choose.

The reflection step is what makes it work, and it is physically motivated: the
tiles are purple on one face and green on the other, so turning one over both
changes its colour and mirrors its arrows. Under rotation alone there would be
13 classes and the design would need an arbitrary omission.

Left one thing open (`OPEN-2`): if both decks are the *same* physical object,
the two players hold mirror-image versions of the single chiral tile, and the
seats are not equivalent. That is a confound for H1 and has to be settled with
a photograph before hypotheses lock.

### Noticing that placed tiles are inert

The largest decision of the phase, and it came from reading the poster's
*CUIDADOS!* section: flips do not chain. Therefore a placed tile's arrows fire
once and never again, so from the next ply onward it is just a coloured token —
its pattern and rotation cannot affect anything.

So the state does not need to store orientation. The reachable state-space bound
drops from ~1.4 × 10³⁷ to ~4.9 × 10¹⁷, about 19.5 orders of magnitude, and
transposition tables go from decorative to essential (with rotation stored,
almost nothing would ever transpose).

This contradicts the roadmap's own Phase 2 exercise, which puts a `6^25` factor
in the state-space bound. Left the exercise in place but reframed: derive the
naive bound, find the inertness argument, derive the corrected one. Better
exercise than the original.

### The roadmap says 8 archetypes; there are 12

The roadmap says "the 8 arrow archetypes" and then enumerates 1+3+3+3+1+1 = 12
in the same sentence. 12 is right — one per piece per player. Corrected in
`piece-archetypes.md` rather than silently.

### The board has no symmetry at all

Expected some symmetry to exploit for transposition-table canonicalisation and
for network data augmentation. There is none: columns A/C/E and B/D sit at
different vertical centres, so the symmetry group is trivial.

Two consequences, both accepted: no free 2–8× augmentation in Axis 2 (unlike Go
or Connect Four), and no strategy-stealing argument available for H1, which now
*must* be settled computationally. The second is arguably good news — it makes
H1 a real question rather than a formality.

### Deferred: chose a factored policy head without evidence

`adr-005` picks a factored (cell × tile × rotation) policy head over a flat
1950-logit one, on parameter-efficiency grounds. The factorisation assumes
conditional independence, which is *false* — the best rotation obviously depends
on the cell. Went with it anyway because MCTS exists to correct a bad prior, and
wrote both fallbacks into the ADR.

Flagging it here because it is the decision in Phase 0 with the least evidence
behind it. It is R5 in the risk register and must be tested in Phase 4, not
assumed.
