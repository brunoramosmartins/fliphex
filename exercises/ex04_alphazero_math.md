# ex04 — The AlphaZero objective, the buffer, and what a measurement licenses

**Phase 4 problem set.** Six problems. The topics were fixed at the end of Phase 2
in [phase2-alphazero-paper-notes.md](../notes/phase2-alphazero-paper-notes.md) —
derive the loss, work out the buffer arithmetic at ~25 positions per game, and
explain the temperature schedule against FLIPHEX's missing symmetry. They are
restated here against what Phase 4 actually built and measured, so that every
answer lands on a number this project owns rather than on a textbook's.

**How to use this file.** Write **Answer** in first person, showing the work
including the wrong turns. **Refined** is written afterwards: corrections,
completed algebra, and the link back to the ADR or experiment each result feeds.
Same loop as the lit-notes, ex02 and ex03.

**Feeds:** [adr-005](../docs/adr/adr-005-alphazero-scope-and-network.md) (Q1, Q3,
Q4) · [adr-004](../docs/adr/adr-004-solver-approach.md) R1 (Q6) ·
[risk-register.md](../docs/risk-register.md) R6, R7, R13, R14 (Q2, Q3, Q4, Q6) ·
[experiments/registry.md](../experiments/registry.md) EXP-006, EXP-010, EXP-011,
EXP-015

**Reading:** [Silver 2018](../notes/silver-2018-alphazero.md) ·
[Silver 2017](../notes/silver-2017-alphago-zero.md) ·
[Takizawa 2023](../notes/takizawa-2023-othello-is-solved.md) §5 (Q6) ·
[phase4-network-design-log.md](../notes/phase4-network-design-log.md)

**Code under discussion:** [`az/train.py`](../az/train.py) ·
[`az/replay_buffer.py`](../az/replay_buffer.py) ·
[`az/loop.py`](../az/loop.py) · [`az/mcts.py`](../az/mcts.py) ·
[`az/player.py`](../az/player.py)

> **Two things to keep straight before starting**, both established during
> Phase 4 and both easy to get backwards.
>
> 1. **Every FLIPHEX game is exactly 25 plies.** The board fills, there are no
>    passes, and draws are impossible on an odd cell count. So quantities that
>    are averages in Go or chess — positions per game, samples per generation —
>    are *exact* here. Several questions below turn on that.
> 2. **Both of H3's clauses came back negative.** The exercises are not a
>    post-hoc rationalisation of a success. Where a question asks what a
>    measurement licenses, the honest answer is often "less than it looks like",
>    and that is the point.

---

## Q1 — The loss, derived rather than quoted

**Problem.**

(a) **Derive** `L = (z − v)² − πᵀ log p + c‖θ‖²` from the two estimation problems
it combines. For each of the first two terms, name the probability model it is
the negative log-likelihood of, and state the assumption that makes it so.

(b) The value term is **squared error**, but on FLIPHEX `z ∈ {−1, +1}` exactly —
draws are impossible, so the target is genuinely two-valued rather than
two-valued-in-practice. Under that constraint, is squared error still the right
choice against a Bernoulli cross-entropy on `(1+v)/2`? Argue it from the
gradients, not from convention, and say what would change in training if the
other were used.

(c) `−πᵀ log p` is cross-entropy against the **visit counts**, not against the
game outcome `z`. Silver's papers assert that `π` is the stronger target. **Prove
it, or find the assumption it rests on.** (Hint: compare the variance of the two
targets at a fixed position, and then ask what is true of `π` that is not true of
a single sampled outcome. `notes/silver-2017-alphago-zero.md` flags this as the
question worth answering.)

(d) `c‖θ‖²` appears in the paper as an explicit term; Phase 4 realises it as
**weight decay in Adam** (`az/loop.py::optimiser_for`), with the rotation head in
a decay-free group. Two parts. Are an explicit `L2` term and optimiser weight
decay the same thing? State the optimiser under which the equivalence is exact
and the one under which it is not, and which of the two this project uses. Then:
the decay-free group was carried over from EXP-012/EXP-013, where it was
load-bearing — reconstruct why, given that one rotation head has 43,290
parameters and the other 198.

(e) `az/train.py` computes the policy normaliser **in closed form**, without
enumerating legal moves. Read `legal_normaliser`, state the identity it exploits,
and prove the closed form equals the brute-force one. Then say what property of
the factored head the proof depends on, and whether it survives the conditioned
head adr-005 adopted.

**Answer.**

**Refined.**

---

## Q2 — The replay buffer, where the arithmetic has no slack

**Problem.**

(a) At 200 games per generation and a capacity of 20,000, derive: samples per
generation, buffer depth in generations, and the expected age in generations of a
sample drawn for training. State which of the three are **exact** on FLIPHEX and
which would be expectations on a game of variable length, and why.

(b) `ReplayBuffer.refresh_fraction` returns `min(1, incoming / capacity)` —
against **capacity**, not against the live buffer. Say when the two disagree,
compute both for generations 0 through 4, and state whether the reported figure
over- or under-states the staleness of what training actually sees during the
fill.

(c) The buffer **crosses generations** by design, so most of what a challenger
trains on was generated by older champions. Write the off-policy assumption
formally. Then: what would have to be true about how fast the policy changes for
this to be harmless, and is that condition checkable from the artefacts Phase 4
produced?

(d) EXP-015 measured a between-seed `sd` of **7.3%** where the 200-game samples
alone predict **3.4%** (`χ² = 18.52`, 4 df — a common rate is rejected). **Could
buffer staleness produce that?** Design the cheapest experiment that separates
"staleness drives seed variance" from "it does not", state what it would cost at
the measured 27 h/seed, and say whether it is affordable. R6 lists the mechanism
as unknown; this is the question of whether that is a funding problem or a design
problem.

**Answer.**

**Refined.**

---

## Q3 — Temperature, in two places, for two unrelated reasons

**Problem.**

(a) Self-play uses `τ = 1` for the opening plies and `τ → 0` afterwards. State
the exploration/exploitation argument. Then a sharper question: sampling from the
visit counts is **not** the same as ε-greedy over the same counts — characterise
the difference in terms of which moves get explored and how often, and say which
property makes the sampled version the right choice for generating *training
data* specifically.

(b) FLIPHEX has one mirror symmetry (adr-008), and the chiral `P3-y` tile breaks
it at the game level while it remains in hand — so there is no clean `2×`
augmentation, let alone Go's `8×`. **Quantify what that costs in this project's
units.** At exactly 5,000 samples per generation and 30 generations, what would a
valid `2×` have bought, expressed as generations of compute at the measured 27
h/seed? Then: the mirror *is* valid once both `P3-y` tiles are placed — can any
of the augmentation be recovered on that sub-population, and what would make it
unsafe to try?

(c) Evaluation uses `EVALUATION_TEMPERATURE_PLIES = 4` for a reason that has
nothing to do with exploration. State it. Then **derive the failure it prevents**:
show that a 400-game gate between two searchers at `τ = 0` with no root noise
reports `n = 400` while measuring a sample of size **one**, and explain why the
binomial interval computed on it is not merely wide but meaningless.

(d) The fix weakens both sides of the match identically. Argue that this does not
bias the comparison — and then find the condition under which it *would*. (Hint:
consider two agents whose relative strength depends on how far from the opening
book-line the position has drifted.)

**Answer.**

**Refined.**

---

## Q4 — PUCT on an aliased action space

**Problem.**

(a) Risk R13: 1,450 root actions reach only **325 distinct positions**. Two
distinct harms follow — one in how **prior mass** is distributed, one in how
**visit counts** are split. State each precisely. EXP-010 built a control that
keeps every alias and fixes only the priors, and it recovered the whole effect:
what does that establish about which harm was real, and what does it *not*
establish?

(b) The registration predicted that deduplicating children would produce a
**DAG**, requiring a backup rule that is not pre-decided. It did not. Explain why
sibling-alias merging leaves every child with exactly one parent, and construct
the condition under which a real DAG *would* arise in this search.

(c) Expanding by position rather than by action changes what the training target
`π` means, because `π` is read off the visit counts. State the change precisely.
Is it a **fix** to a target that was wrong, or a **different target** that is also
defensible? Defend your answer against the other reading.

(d) EXP-010 measured **+4.77** points [+3.47, +6.06] on the 5×3, and +8.9 on
layers where a decision exists. R13 still reads "effect unmeasured on the 5×5",
because EXP-015 deployed deduplication throughout with no control arm. Price the
control at the measured 27 h/seed, and then make the argument either way: was
declining to run it the right call, and what is the honest way to quote +4.77 in
a write-up about the 5×5?

**Answer.**

**Refined.**

---

## Q5 — What a floor licenses, and what it does not

**Problem.**

(a) The criterion is that the Wilson 95% interval lies **entirely above 50%** at
`n = 200`. Compute the smallest clearing win count and show the effective bar is
**57.0%**, not 50%. Then compute the **power** of this test against a true 60%
agent, and say what that implies about reading a single failing seed.

(b) The generation-0 champion — randomly initialised, untrained — scored **3.0%
to 13.5%**, i.e. 36.5 to 47 points *below* the 50% an even match would give,
against an opponent identical except for having no network at all. Give the
mechanism. Then do the harder half: state what evidence would **establish** it
rather than assert it, and design the cheapest measurement that would.

(c) The equal-time arm was registered on the prediction that UCT would receive
"several times" the simulations. Measured: **0.98× to 1.17×**. Reconstruct the
reasoning error from first principles — identify exactly what was being compared
against what, and why the comparison omitted a term. Then state the general form
of the mistake, in a way that would catch it in a different experiment.

(d) Design a comparison that genuinely **charges the network for its compute**.
Say why wall-clock per move fails to do so on this hardware, and what your
alternative would cost to implement and run.

**Answer.**

**Refined.**

---

## Q6 — Agreement, and the denominator that was not a denominator

**Problem.**

(a) Draws are impossible on 25 cells. **Prove** that from a position the mover
loses, every legal move preserves the exact value. Then derive the consequence:
write the observed agreement rate over a mixed sample as a function of the lost
fraction and the learner's true accuracy, and state what a fixed threshold on the
observed rate demands of the accuracy at two different lost fractions.

(b) The measured lost fractions are **39.2%, 3.6%, 46.1%** at `k = 6, 7, 8`.
Explain the swing from board parity. Then the part that matters: "the first
player is to move" and "the mover places one more tile before the board fills"
are **perfectly confounded** on this board — show why, and design a board or
variant on which they would come apart. Is such a variant admissible under
adr-011?

(c) A random mover scores **21.9%** on the same positions; the champions scored
**75.7%**; the threshold was **90%**. Express the threshold as "how far from
random to perfect", and say whether that quantity is natural or an artefact of
where the random baseline happens to sit. Would your answer change if the
baseline had been 5% instead?

(d) The 0.90 was **pre-declared and never derived**. Propose a derivation from
something measurable that a future entry could pre-register *before* seeing any
result, and state what your derivation would have implied here. Then the
uncomfortable part: if your derived threshold comes out below 75.7%, has anything
been learned that the underived threshold did not already tell us?

(e) EXP-006's second stratum draws uniformly from the layer index instead of by
play, against Takizawa 2023 §5. The standardised gap is **−5.9** points. Under
adr-004 R1, explain why this measurement is allowed to read Axis 1 and Axis 2
together at all, and identify the one thing that would have made it circular.

**Answer.**

**Refined.**

---

## Lessons Learned

## Failed Attempts
