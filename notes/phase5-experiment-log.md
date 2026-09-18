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

**The gates are in force.** No experiment below is registered until its nine
measurement-gate answers are written into its registry entry —
[`docs/measurement-gates.md`](../docs/measurement-gates.md). Two planned
comparisons already fail a gate as sketched. Neither survived to be re-scoped:
H1's shipped-board arm was registered and withdrawn the same day, and H2's
shipped-board arm turned out not to be constructible at all. A ninth gate was
added at the close, after the first eight let the same defect through three
times.

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

### 1. A measurement gate can be correct and still be incomplete

Phase 5 exposed a limitation in the measurement-gate framework itself. Three experiments reached quantities that were already fixed by the rules or construction: the move-preservation measure on losing positions in EXP-006, root coverage in EXP-016, and the archetype-count vector in H5.

The first eight gates allowed all three through.

The ninth gate did not exist while those three were designed. It was written at the end of the phase, on the day the gates were first used in anger, and it asks what a quantity is free to be before the measure is registered: its floor, its ceiling, and how much of its nominal range is actually reachable. The lesson was not that the gates were wrong. It was that a measurement can be statistically well-defined and computationally executable while still measuring no variable quantity, and that eight independently sensible checks can all miss exactly that.

### 2. Some experimental questions are answered by construction

H5 was initially framed as a question about archetype dominance. The subsequent audit showed that the archetype frequencies cannot vary under the game's fixed inventory: 25 cells are filled without passes, with exactly 12 archetypes appearing twice and the joker once.

The resulting count vector is `[2] × 12 + [1]` in every one of the 500 recorded games checked from EXP-017.

The hypothesis was therefore true by construction, but the result provided no empirical evidence about play. Phase 5 exposed the need for a vocabulary stronger than simply “supported” or “rejected”: a proposition can be true while being experimentally uninformative. Only the frequency half is settled this way; the half of H5 that can still vary — win contribution — carries to Phase 6.

### 3. An experiment can fail before collecting a single observation

EXP-016 was registered and withdrawn on the same day after seven blocking findings. It collected zero data and avoided approximately 20.5 hours of compute.

The failure was substantive, not administrative. Prior-free UCT at 400 simulations visited only 10–18 of the 325 possible root children, approximately 4%, and the coverage depended on seat. The proposed measurement was therefore primarily measuring cell-enumeration order rather than the intended coverage property. In addition, 975 of 5,000 seeds collided.

Changing the agent changed the quantity being measured, so the experiment received a new ID rather than an amendment.

The failed experiment was therefore useful precisely because it failed before producing a misleading dataset.

### 4. A failed experiment can save more evidence than a successful one

EXP-016 changed the project's notion of experimental cost. The relevant cost of a design failure is not only the compute already spent. It includes the data that would have been collected under an invalid measurement and the downstream analysis that would then have treated those data as evidence.

The 20.5 hours not spent were therefore not merely saved compute. They were avoided contamination of the evidence chain.

### 5. The strongest experimental designs can be built from adversarial review

EXP-017 was the first experiment in the project whose three registered predictions were all confirmed.

That result was preceded by a different kind of success: the predecessor experiment had been red-teamed until each prediction had a measurable operational basis. In particular, the 7.95 seconds/game runtime under PyPy was measured before the instrument that depended on it was built.

The important lesson was procedural. The experiment became robust not because the final instrument was complicated, but because its assumptions had been attacked before execution.

### 6. A reported rate can be meaningless without its conditioning variable

The 54.2% rate from the phase cannot be interpreted on its own. It is meaningful only together with the `proved_rate` of 32.0%.

The underlying protocol was heterogeneous: the heuristic handled approximately the first 17 plies, while the exact procedure handled the final eight. Reporting only the aggregate rate would hide that division of labour.

The conditioning quantity therefore became part of the result, not an implementation detail to be appended later.

### 7. A planned endpoint can be structurally unreachable

The roadmap required a Phase 5 comparison in which the solver and AlphaZero agent agreed on the value of the 3×3 game.

That endpoint could not be satisfied by the available agents. The champions were fixed to the 5×5 architecture and failed on reduced boards with a shape mismatch (`1×480` against `800×25`). The reduced-board networks, meanwhile, had been supervised on solver labels, which adr-004 R1 explicitly excludes from the intended comparison.

The criterion was therefore recorded as not met and unreachable.

This was a planning failure: the phase contained an explicit exit condition that the experimental architecture could not satisfy.

### 8. Replacing a discarded deliverable does not make the underlying problem disappear

The notebooks planned across Phases 3–5 were dropped in favour of canonical scripts under `figures/`. The `figures/` directory ultimately remained empty.

The lesson was not that notebooks were the wrong artifact. The replacement reproduced the same outcome because the underlying deliverable had not been integrated into the execution path.

Changing the format of an artifact is not the same as establishing a production path for it.

### 9. Statistical infrastructure should be built around demonstrated need

The planned `stats/` module was also dropped.

Phase 5 reinforced a distinction already learned in Phase 4: duplicated statistical code is not automatically technical debt. Independent implementations can serve as cross-checks when their independence is deliberate and tested.

Creating a common abstraction merely because several places calculate Wilson intervals would have added structure without necessarily adding experimental assurance. The statistical module therefore remained unimplemented rather than becoming infrastructure without a demonstrated role.

### 10. Not every useful analysis belongs in a confirmatory phase

The sensitivity sweep over simulations, `c_puct`, and temperature was dropped rather than converted into a post-hoc search for a favourable configuration.

This preserved the distinction between describing a response surface and testing a registered hypothesis. The absence of the sweep was therefore preferable to turning an exploratory optimization into an apparently confirmatory result.

### 11. I learned to distinguish a failed hypothesis test from a failed experiment

Several Phase 5 items never reached the point at which the hypothesis itself could be evaluated. EXP-016 was invalid before data collection; H5 was fixed by construction; the H2 5×5 arm was unreachable by construction; and the planned solver/AZ reduced-board comparison was architecturally unreachable.

These are different states from “the hypothesis was rejected.”

The distinction became important enough that the research log needed to record not only what the result was, but whether the experiment had actually reached the inferential state required to produce that result.

### 12. The phase reinforced, rather than repeated, the statistical lessons of Phase 4

Phase 4 already established that statistical validity and experimental validity are separate properties, and that pre-registration does not guarantee a useful question.

Phase 5 added a narrower lesson: those principles must be enforced at the level of the actual measurement quantity. A formally specified estimator can still be attached to an invariant, a construction, or an unreachable endpoint.

The lesson carried forward from Phase 4 was therefore not repeated as a new discovery; Phase 5 showed where the earlier principle still had an implementation gap.

### 13. The most useful negative result may be a statement about what the experiment could not establish

Phase 5 ended with several claims that could not legitimately be converted into ordinary hypothesis verdicts.

That was itself informative. The phase demonstrated that experimental closure requires more than producing a number: the measured quantity must vary, the agent must match the intended population, the endpoint must be reachable, and the reported statistic must retain the conditions under which it was obtained.

The result was a narrower but more defensible boundary around what the project can claim.

## Failed Attempts

### 1. EXP-006: move preservation on losing positions

The registered value-preservation measure was applied to positions where the mover loses.

On a LOSS position, every legal move preserves the LOSS outcome. The metric therefore became vacuous for that stratum: it did not distinguish solver-preserving behaviour from arbitrary legal play.

The experiment had a formally defined endpoint, but the endpoint did not contain the variation the analysis assumed.

Recorded here because it is one of gate 9's three instances, not because Phase 5 discovered it: EXP-006 ran in Phase 4 and its denominator was corrected there, by the dated amendment of 2026-09-16. What Phase 5 added was the recognition that this failure and two others share one shape.

### 2. H2: a 5×5 joker-removal arm

The planned H2 comparison was found to be impossible on the shipped 5×5 configuration.

`Variant(5, 5, Arm.H2)` raises an exception because the capacity is already exhausted: there is no next archetype available for promotion, so the joker is the only piece capable of giving P1 the additional ply.

The H2 5×5 arm was therefore not re-scoped into an equivalence test. It was recorded as out of reach by construction, and the corresponding `variant.py` docstring and `ValueError` message were corrected.

### 3. H5: archetype dominance

The initial H5 analysis treated archetype frequency as an empirical quantity.

Inspection of the game construction showed that the count vector is invariant: 12 archetypes occur twice and the joker once, producing `[2] × 12 + [1]` in every completed game.

The planned dominance analysis was therefore dropped for the frequency half: there was no distribution to estimate and no meaningful dominance threshold to declare. The half of H5 that can still vary — an archetype's contribution to winning rather than its rate of appearance — was withdrawn to Phase 6 rather than dropped, since nothing in the rules forces it.

### 4. EXP-016: prior-free UCT root coverage

EXP-016 was registered and withdrawn on the same day.

Seven blocking findings showed that the proposed measurement did not test the intended property. At 400 simulations, prior-free UCT visited only 10–18 of 325 possible root children, and the observed coverage depended on seat. The design was therefore sensitive to cell-enumeration order rather than the intended coverage question.

A second issue was seed collision: 975 of 5,000 generated seeds collided.

The experiment collected zero data and approximately 20.5 hours of planned compute were avoided. Because the corrected design changes the agent and therefore the measured quantity, the experiment received a new ID rather than being amended.

### 5. Sensitivity sweep over MCTS settings

The planned sweep over simulations, `c_puct`, and temperature was dropped before execution.

The original formulation did not specify whether the sweep was exploratory or confirmatory. Running it first and selecting a preferred configuration afterward would have created a post-hoc decision rule.

No confirmatory result was therefore claimed from the sweep.

### 6. The planned `stats/` module

The planned statistical module was not implemented.

Existing Wilson-interval calculations remained in their respective instruments where independent duplication served as a validation mechanism. No central module was introduced merely to remove syntactic duplication.

The planned directory therefore remained empty.

### 7. Canonical figure scripts

The planned `figures/` deliverables were not completed.

The roadmap had originally specified notebooks; those were replaced by scripts intended to generate canonical figures from tracked artifacts. The scripts were not subsequently integrated, and the directory remained empty.

The replacement therefore did not deliver the intended reproducibility artifact. It is carried into Phase 6 as an explicit task rather than dropped, which is the only reason this is a failed attempt and not a second abandonment.

### 8. Solver–AlphaZero reduced-board comparison

The planned exit criterion requiring solver/AZ agreement on 3×3 could not be evaluated.

The Phase 4 champions were fixed to the 5×5 architecture and failed on reduced boards with a tensor-shape mismatch (`1×480` versus `800×25`). The reduced-board networks available in the project were supervised on solver labels, which adr-004 R1 excludes from the intended comparison.

The criterion was consequently recorded as unmet and structurally unreachable.

### 9. The unqualified 54.2% rate

The aggregate 54.2% rate was not retained as a standalone result.

Its interpretation depends on the accompanying `proved_rate` of 32.0%, because the protocol divided the game between approximately 17 plies handled by the heuristic and the final eight handled exactly.

The result was therefore registered with its conditioning quantity rather than reconstructed or qualified after the fact.

### 10. `git add A B && git commit`

The command was used twice during the phase with one of the requested files ignored by Git.

`git add` returned a non-zero status, causing `&&` to short-circuit. The commit therefore did not run.

The failure occurred once with the EXP-006 `.jsonl` artifacts and again with the EXP-017 `.jsonl` artifacts. The command appeared to be a commit workflow but did not actually reach the commit step.

### 11. Reading the 17.07% extra-tile criticality as a verdict

H2's registered measure was extra-tile criticality: the fraction of positions in which P1's additional tile is still in hand. It came out at 17.07% — 1,237,229,498 of 7,248,350,863 positions — and the temptation was to read that number as the answer to H2.

It is not. H2 asserts a property of the root, while criticality measures positional sensitivity across the tree, and no threshold for it was ever registered. A magnitude with no decision rule attached cannot decide anything.

The measure was kept and its interpretation was deferred, by the EXP-002 amendment of 2026-09-18. H2's verdict rests instead on the four exhaustive solves, which return P1 on both arms of both reduced boards. The reference distribution that would make 17.07% interpretable — per-archetype tile criticality — is Phase 6 work.
