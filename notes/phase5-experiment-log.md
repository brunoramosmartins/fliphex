# Phase 5 — Hypothesis Testing & Cross-Axis Verification (experiment log)

**Objective.** With the exact solver (Axis 1) and the learned agent (Axis 2)
both in hand, run controlled experiments that decide H1, H2, H3 and H5. This is
where the two axes cross-check each other, and a disagreement between solver
ground truth and learned behaviour is a first-order finding rather than a bug to
be explained away.

**Dates.** None. The roadmap is a living document sequenced by dependency, not
by calendar, and this phase carries no external deadline.

**What the phase must end with.** A verdict — supported, rejected or
inconclusive — written into `docs/research.md` for every hypothesis it owns,
each with the interval or exact computation that justifies it. The verdicts
table has been empty since the hypotheses locked at `v0.3-hypotheses`; this is
the phase that fills it.

**What it inherits.** Two hypotheses already have negative readings from Phase 4
that no Phase 5 work can convert: H3's stability clause (EXP-015) and H3's
shipped-5×5 agreement member (EXP-006). Phase 5 adds the two remaining
comparison-set members and writes the verdict; it does not re-run the training.

**The gates are in force.** No experiment below is registered until its eight
measurement-gate answers are written into its registry entry —
[`docs/measurement-gates.md`](../docs/measurement-gates.md). Two planned
comparisons already fail a gate as sketched and are re-scoped before they run.

---

## The measurement gates, answered per experiment

<!--
One subsection per registered experiment, with its eight answers. The two known
failures, from the gates document:

- H1's "20 seeds x 1000 games" resolves +/- 3.42% at EXP-015's measured
  between-seed sd of 7.3%, so it cannot see a 2-point first-player advantage;
  and "20 seeds" is ambiguous between 540 h (training seeds) and 57 h (match
  seeds over the five existing champions), which answer different questions.
- H2's joker-less test is an equivalence claim and needs a margin declared in
  advance.

Gate 8 applies to both: if the honest sizing exceeds the budget, the entry says
the comparison is not affordable rather than running a study that cannot see its
own effect.
-->

## `stats/` — the module the phase's claims are computed by

<!--
It does not exist yet; the directory is empty. Wilson intervals, paired
bootstrap, McNemar, Bonferroni.

Two things to decide before writing it, both learned the hard way in Phase 4:

- Several instruments already compute Wilson inline (az/gate.py,
  scripts/exp015_analysis.py, scripts/exp006_agreement.py). Some of that
  duplication is deliberate — an analysis script that checks a gate must not
  import the gate's own implementation, and there is a test asserting the two
  agree. Decide per call site which duplications are load-bearing and which are
  accidents, rather than collapsing all of them.
- Gate 7: no instrument produces a number before it is run against a known
  answer. Each estimator needs a closed-form or published case it reproduces.
-->

## H1 — does the first player win?

<!--
Statement: with perfect play the first player wins (strictly; draws are
impossible).

What already exists, and it is decisive in direction: 3x3 and 5x3 both return
P1, on both deck arms, at termination: exhausted. What is missing is a magnitude
on the shipped 5x5, where no exact answer is reachable.

Open before registration: what magnitude would change the verdict (gate 1), what
the clustering unit is (gate 3 -- EXP-015 showed the training seed is one), and
what happens if the sizing exceeds the budget (gate 8).

Recorded here because it will be tempting later: the seat splits in EXP-015's
floor matches are large and consistent, and they are confounded -- the two seats
are held by different agents. They are not H1 evidence.
-->

## H2 — does removing the joker change who holds the advantage?

<!--
This is an equivalence claim, not a superiority test. A non-significant
difference is not evidence for it.

Note what adr-011 already settled: on a reduced board P2 draws a = (N-1)/2
archetypes and P1 draws the same a plus the joker, so the contrast is *what P1's
extra tile is*, not joker presence. The exact arms on 3x3 and 5x3 are available.

The equivalence design is needed only for the shipped-5x5 self-play arm.
-->

## H3 — the two remaining comparison-set members

<!--
Scope decision taken at the phase open: Phase 5 measures agreement against the
3x3 and 5x3 exact solutions only. The training is not repeated -- EXP-015 ran
five seeds and EXP-006 read the shipped-5x5 member, and re-running either after
seeing the result would select on the outcome.

Both solutions exist with termination: exhausted, so the adr-004 R1 filter
passes. The measure is the one EXP-006 registered: value preservation, never
identity with the solver's move, on the positions the mover wins.

The verdict this phase writes is for H3 as a whole, and two of its three parts
are already negative.
-->

## H5 — is any archetype dominant?

<!--
Frequency and win-contribution over the self-play database. The database exists:
EXP-015 generated 150,000 positions per seed across five seeds.

Gate 1 applies and is not obvious here: "no archetype dominates" needs a
dominance threshold declared before looking. Gate 2 also applies -- the endpoint
is a frequency over a database whose size is a choice, not a given.
-->

## Sensitivity — simulations, `c_puct`, temperature

<!--
Auxiliary. A sweep with no declared threshold reports whichever setting won,
which is gate 1's failure mode with extra steps.

Decide before running whether this is exploratory (report the surface, decide
nothing) or confirmatory (one pre-declared comparison with a margin). Both are
legitimate; the mistake is running the first and writing up the second.
-->

## Figures — one canonical figure per hypothesis

<!--
Replaces the notebook deliverables, dropped at the phase open: three notebooks
were planned across Phases 3-5 and one exists. Scripts in figures/ instead,
producing the canonical plot for each hypothesis from the tracked artefacts, so
a figure is reproducible the same way every other number in this project is.
-->

## TIL #4 — retrograde analysis, when backwards beats forwards

<!--
Skeleton with prompts, like TILs #2, #3 and #5. The content is first person and
is not ghost-written.

Material exists: EXP-005's counting identity, the 580x sweep speedup already
written up in TIL #6, and EXP-003's measurement that searching beat storing --
which is the answer to "when does backwards beat forwards" being *not here*.
-->

## Lessons Learned

## Failed Attempts
