# Measurement Gates

**Adopted 2026-09-18, at the close of Phase 4.** Eight questions that must be
answered **in writing and dated** before any Phase 5 or Phase 6 experiment is
registered in `experiments/registry.md`.

The gates exist because a project that plans `n` from what is affordable, rather
than from what must be detected, discovers its own resolution at the end. Phase 4
came close to doing exactly that twice, and the two near-misses are why this file
exists rather than a general commitment to rigour:

- **EXP-012's equivalence gate was unpassable.** Its forecast half-width was
  **2.43** against a margin `δ` of **2.00**, so no point estimate could have
  cleared it. The gate could be neither passed nor failed on evidence. The
  feasibility rule the project now uses — `δ` must exceed the forecast
  half-width, with the room tabulated — was derived *after* that failure.
- **EXP-006's threshold was never derived.** `0.90` was pre-declared on
  2026-08-05 with no argument from anything measurable. It did not matter at a
  14-point gap, by arithmetic rather than by design. The next entry that lands
  near its bar will not be so lucky.

**This file does not reopen anything.** Hypotheses are locked at
`v0.3-hypotheses`; `docs/research.md` may only gain verdicts. Phases 1–4 are
closed and are audited here only to show which gates were met by accident and
which were missed. What is prospective is Phases 5 and 6, where every comparison
is still unrun.

## The rule

> **No Phase 5 or Phase 6 experiment is registered until its eight gate answers
> are written into its registry entry.** A gate answered "not applicable" says
> why in one line. A gate that cannot be answered is itself the finding, and the
> experiment is not run until it is.

A gate answer is roadmap-grade content, not chat content: a number that decides
the scope has to be readable by someone who was not in the conversation.

---

## The eight gates

### 1. The decision before the architecture

*What decision does this experiment make, and what numeric difference would
change it? That number is the target MDE. **Fails if the answer is a metric
without a threshold.***

**Phase 4's record: failed twice, survived both by luck.** EXP-011 set a 5-point
threshold as a *detection* criterion; EXP-012 then reused the same constant as an
*adoption tolerance* without rejustifying it, and cleared it by **0.25 points**. A
margin of 4.7 would have reversed the decision. EXP-006's `0.90` had no
derivation at all.

**Phase 5 must answer it for H1, H2 and the sensitivity sweep.** For a hypothesis
verdict the "decision" is which verdict gets written, so the threshold is the
value the interval must exclude — and that has to be stated with the estimator it
will be computed under, not left as "a Wilson CI".

### 2. Enumerate every candidate endpoint and mark its labelling cost

*Which endpoints are deterministic and which need annotation. For each, the `n`
actually available.*

**Not applicable in the usual sense, and that is why this project is
affordable.** Every endpoint here is deterministic: exact solver values, win
counts, node counts, agreement against ground truth. Nothing needs a human
annotator or an LLM grader. The cost is **compute**, not labels, and the units
are the hours in gate 3.

Stated rather than skipped, because "no labelling cost" is the reason a five-seed
training run and a 750-position exact ground truth were possible at all.

### 3. Size under discordance scenarios, never a point estimate

*Publish the `n` required at several plausible variances. The variance of two
systems that do not exist yet is unknown.*

**Phase 4 supplies a measured variance, and it is large.** EXP-015 found a
between-seed `sd` of **7.3%** where the within-seed binomial predicted **3.4%**,
and a homogeneity `χ²` of **18.52** on 4 df rejected a single underlying rate.
**Training seeds are a clustering unit, not a nuisance.**

This is the gate that bites hardest on Phase 5 — see the H1 sizing below.

### 4. The grader's ceiling

*If the outcome is judged, what agreement can the judge reach, and is that
ceiling above the target MDE?*

**Not applicable.** The judge is `solver/minimax.py`, which proves or raises. Its
ceiling is exact, and adr-004 R1 makes the ceiling checkable rather than assumed:
H3's comparison set is defined by *filtering* on `termination: exhausted`.

The one residual worth naming: an artefact that hits its node budget carries no
value. EXP-006 excluded one position of 750 and reported it rather than replacing
it, and its header carries `excluded_at_budget` so a filter cannot read
"exhausted" over an unproved row.

### 5. Superiority or equivalence — choose now

*They are different designs. Equivalence needs a margin declared in advance and a
TOST-shaped test; testing superiority and reading the null as equivalence is not
available afterwards.*

**Phase 4's record: EXP-012 mixed them and paid for it.** Its primary was a
non-inferiority test and its validity precondition was an equivalence gate, and
the two carried different margins with only one of them feasible.

**Phase 5's H2 is an equivalence claim in disguise and must be registered as
one.** "Removing the joker does not change which player holds the theoretical
advantage" is a statement that two things are the *same*, and a non-significant
difference is not evidence for it. On the reduced boards the question is settled
exactly — every solved variant returns **P1**, on both arms, at
`termination: exhausted` — so the equivalence design is needed only for the
self-play arm on the shipped 5×5.

### 6. The pilot estimates noise, never effect

*Write, before running it, what the pilot can and cannot conclude. And the
confirmatory regime is chosen by mechanism, not by pilot outcome.*

**Phase 4 got this right, and it is the gate the project already passes.**
EXP-014 was a 48-minute shakedown that measured throughput, worker optima and
resume correctness, and its 20-game gate promoting at 70% [48.1%, 85.5%] was
recorded in the entry as **not a result**. Nothing about the full run's design
was chosen from EXP-014's win rates; only its *costs* were used.

### 7. No instrument produces a number before it is run against a known answer

*The most expensive defects are in measuring code, not in designs.*

**This is the gate Phase 4 failed most often, and every instance cost real
time.** The pattern is uniform: none of them raised.

| defect | how it presented | caught by |
|---|---|---|
| Agreement measure vacuous on lost positions | a plausible rate, inflated by the sample's loss fraction | reasoning about the rule before the run |
| Evaluator gate between two deterministic searchers | `n = 400` reported over a sample of size **one** | reading what temperature zero implies |
| Mid-gate resume replaying a finished generation | weights diverge silently | byte comparison against an uninterrupted run |
| Fabricated gate seat split on resume | a correct total with an invented breakdown | reading the function's own docstring |
| Workers rebuilding every net as the wrong class | unreachable at `workers = 1` | a parallel run of the adopted head |
| A resume test that passed on broken code | green | **probing the test** — deleting `restore_rng`, pinning the generation counter, and finding it still green |

**The operational form of this gate: every instrument is probed by breaking it.**
A test that stays green when the thing it guards is removed is decoration. Phase 4
adopted this late; Phases 5 and 6 adopt it from the first instrument.

### 8. The abort criterion

*If sizing demands more than the author has, what happens — written before the
answer is known.*

**Phase 4 got this right once and should repeat it.** EXP-015 registered a
floor-only go/no-go after seed 1, explicitly scoped so it could not become
optional stopping: the run stops if seed 1 fails the floor, and stopping for any
*other* unfavourable reason is not licensed. It also forbade restarting with
different hyperparameters without a new registered entry.

---

## Applied to Phase 5, before anything is registered

### H1's self-play arm cannot see a small advantage, and the design does not say so

H1 is tested on the full 5×5 by a **20-seed self-play win rate with a Wilson 95%
CI**. Gate 3, applied with Phase 4's measured variance, says what that can
resolve.

| estimator | half-width | what it means |
|---|--:|---|
| 20,000 games pooled, Wilson | **0.69%** | fiction — it prices the seed as if it were not a clustering unit |
| 20 seeds, `t(19)`, at EXP-015's measured `sd` of 7.3% | **3.42%** | the design detects a departure from 50% only if it exceeds ~3.4 points |
| 20 seeds, `t(19)`, if `sd` were 3.4% (binomial only) | 1.59% | the optimistic case, which EXP-015 rejected on this pipeline |

**So the registered design cannot detect a 2-point first-player advantage**, and
the pooled interval — the one a reader would expect from "Wilson 95% CI" — would
report ±0.69% and be wrong by a factor of five.

Seeds needed to reach a 2-point resolution at `sd = 7.3%`, same `t` estimator
throughout:

| seeds | 20 | 40 | 60 | 100 |
|---|--:|--:|--:|--:|
| half-width | 3.42% | 2.33% | **1.89%** | 1.45% |

**None of this makes H1 untestable.** The exact arm is already decisive in
direction: the 3×3 and 5×3 both return **P1** with perfect play, on both deck
arms, at `termination: exhausted`. What the self-play arm adds is a *magnitude on
the shipped board*, and gate 1 has to say what magnitude would change the verdict
before `n` is chosen.

### "20 seeds" is ambiguous and the two readings differ by 10×

| reading | cost |
|---|--:|
| 20 **training** seeds, at EXP-015's measured 27.0 h/seed | **540 h** |
| 20 **match** seeds over the 5 existing champions, at 352 games/h | **57 h** |

540 hours is not affordable; 57 is. **But they answer different questions.** Match
seeds measure the first-player advantage *of the agents that exist*, with five
training seeds' worth of independence, not twenty. Training seeds measure it
across the learner's own variability — which is the quantity EXP-015 showed is
large.

This must be resolved in the registry entry, with gate 8's abort branch attached:
if the honest answer needs 60 training seeds, the entry says so and reports that
the comparison is not affordable, rather than running 20 and quoting an interval
that cannot see its own effect.

### What each planned Phase 5 experiment must answer

| planned experiment | gates that block it |
|---|---|
| First-player win rate, H1 | **1, 3, 8** — MDE, the clustering unit, and what happens if sizing exceeds the budget |
| Joker-less variant, H2 | **1, 5** — it is an equivalence claim and needs a margin declared in advance |
| AZ vs solver at matched depth caps | **1, 7** — the depth cap is an instrument and must be probed before it produces a number |
| Sensitivity: simulations, `c_puct`, temperature | **1, 3, 5** — a sweep with no declared threshold reports whichever setting won |
| Archetype placement frequency, H5 | **1, 2** — "no archetype dominates" needs a dominance threshold, and the endpoint is a frequency over a self-play database whose size is a choice |

---

## What this file does not do

**It does not reopen a locked hypothesis.** H1–H6 are fixed at
`v0.3-hypotheses`. The gates constrain how they are *tested*, never what they
say.

**It does not retrofit Phase 4.** EXP-006 and EXP-015 are reported as they were
registered, thresholds and all. Where a gate would have changed a design, that is
recorded in the entry and in the risk register — see R14, which exists because
this register had no row for a hypothesis simply failing — and not by restating
the result under a rule written afterwards.

**It does not replace the red-team pass.** The gates are answered by the author
before registration; an adversarial read of the entry is a separate step and
catches different things. Phase 4's evidence: the EXP-013 secondary was broken in
two independent ways and was found while *building the instrument*, not while
sizing it.
