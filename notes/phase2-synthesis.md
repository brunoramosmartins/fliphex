# Phase 2 — cross-source synthesis

Questions that only make sense *across* the phase's sources. Each source's
companion note forward-refs here with 🔄. Answer these after you have read the
relevant pair, in first person, then I refine.

**Sources:**
[R&N AIMA Ch.6](notes/russell-norvig-aima-ch6-adversarial-search.md) (adversarial
search) · [Silver 2017](notes/silver-2017-alphago-zero.md) (AlphaGo Zero) ·
[Silver 2018](notes/silver-2018-alphazero.md) (AlphaZero) ·
[Allis 1994](notes/allis-1994-searching-for-solutions.md) (solving taxonomy and
complexity) · [Schaeffer 2007](notes/schaeffer-2007-checkers-is-solved.md)
(retrograde at scale).

> **Scaffold note.** This file was drafted in Phase 0 and two of its premises
> were falsified during the reading: adversarial search is **Chapter 6** in the
> 4th edition (it was Ch.5 in the 3rd), and the board's symmetry group is **not
> trivial** — it is Z/2 ([adr-008](docs/adr/adr-008-board-mirror-symmetry.md)).
> S3 has been rewritten accordingly. **S5** and **S6** are new: they are the two
> questions the Phase 2 readings raised that no single note can settle.

---

## S1 — MCTS: classical UCT vs AlphaZero's PUCT (R&N §6.4 ↔ Silver 2017/2018) 🔄

**Prompt.** Line up the two search procedures term by term and be precise about
what is *substituted* versus what is *deleted*:

| | R&N §6.4 (generic UCT) | AlphaZero |
|---|---|---|
| selection | `Q(a) + c·√(ln N / n(a))` | `Q(a) + c·P(a)·√ΣN / (1 + N(a))` |
| leaf value | random playout to a terminal | one network call → `v` |
| phases | 4 | ? |
| search output | a move | ? |

Three things to settle. (a) The exploration terms are not the same *kind* of
object: UCB1's is a concentration bound (it answers "how wrong could `Q(a)`
be?"), PUCT's is not — it decays like `1/n` instead of `√(ln n / n)` and is
scaled by the policy prior. What is traded away, and why is that trade
*necessary* rather than merely convenient at FLIPHEX's b₀ = 1450? (b) The
simulation phase is **removed**, not replaced — MCTS drops to three phases. What
was the only unbiased estimator in the algorithm, and what replaces its role in
keeping the value estimates honest? (c) The substitution nobody lists: the visit
counts become the **policy training target** (`π ∝ N^{1/τ}`), closing the loop
between search and network. Without that row, AlphaZero is just guided MCTS.

Then the FLIPHEX-specific question. Perfect information is what makes a learned
value trustworthy enough to drop rollouts — the leaf's value is a function of the
state alone, with no belief to average over. State why an imperfect-information
game (your PTCG project) could not make the same move, and what it would have to
do instead.

**One thing FLIPHEX gets for free that is worth naming here:** R&N list two MCTS
disadvantages, and the second — positions that are "obviously" won but need many
playout moves to verify — is *void* for FLIPHEX. Playouts are ≤25 plies, always
terminate, always yield a decided winner. So R&N's *early playout termination*
machinery is unnecessary, and plain UCT is a cheap baseline. Does that change
whether AlphaZero's rollout-free design is a *requirement* here or merely an
inherited choice?

**My take.**

**Refined write-up.**

---

## S2 — The evaluator gate: kept then dropped (Silver 2017 ↔ 2018) 🔄

**Prompt.** AlphaGo Zero promotes a new network only if it beats the current best
in ≥55% of games; AlphaZero removes the gate and trains a single continuously
updated network. What changed to make the gate unnecessary — and be careful here,
the honest answer involves what the gate was *protecting against* and whether
that risk was ever measured or merely assumed.

Then the decision this actually drives: which regime is safer for a
**single-laptop** FLIPHEX run, where compute is scarce and a collapsed training
run costs days? Note the asymmetry — the gate costs evaluation games (compute you
do not have) but buys monotonicity (protection you cannot otherwise afford.)
State a recommendation for [adr-005](docs/adr/adr-005-alphazero-scope-and-network.md),
not just a comparison.

**My take.**

**Refined write-up.**

---

## S3 — Symmetry: what FLIPHEX actually has, and what it is worth 🔄

*(Rewritten — the original premise, "FLIPHEX's board symmetry group is trivial",
is false.)*

**Prompt.** Three positions on the same question, from three sources:

- **AlphaGo Zero** exploits Go's 8-fold dihedral group for data augmentation and
  evaluation averaging — 8× labelled data per game, free.
- **AlphaZero** drops symmetry augmentation entirely, because chess and shogi
  have none to exploit. Same recipe, no augmentation, still superhuman.
- **FLIPHEX** sits between: the board's automorphism group is **Z/2** (a
  left-right mirror across column C — [adr-008](docs/adr/adr-008-board-mirror-symmetry.md)),
  but the chiral `P3-y` tile breaks it at the *game* level for as long as either
  copy remains in a hand.

Settle four things. (a) Why does "the board has a mirror" not imply "self-play
gets 2× data"? Be precise about *when* the mirror is a valid game symmetry and
what fraction of a typical game satisfies that condition. (b) Given (a), is the
right Axis-2 design decision AGZ's (augment) or AlphaZero's (don't)? Argue it,
then write the one-line justification adr-005 should carry. (c) The mirror *is*
fully valid once both `P3-y` are placed — which is precisely where the retrograde
endgame databases live ([Schaeffer note](notes/schaeffer-2007-checkers-is-solved.md)
§2.3). So the symmetry is worth ~2× to **Axis 1** and ~0× to **Axis 2**. Is that
inversion an accident of this game, or a general pattern (symmetries that only
hold late help exact endgame methods, not learners)? (d) The original scaffold
asked whether this "strengthens the case for the exact solver as the cheaper
source of ground truth on small variants". Answer it with the corrected premise —
and note that the answer no longer rests on symmetry at all.

**My take.**

**Refined write-up.**

---

## S4 — Two routes to a game's value: where exactly is the boundary? (Allis ↔ Schaeffer ↔ Silver) 🔄

**Prompt.** This is the intellectual spine of H1/H3. Allis frames feasibility via
**two independent** complexity axes; the Phase 2 readings supplied the numbers to
place FLIPHEX on both.

| | state-space | game-tree | solved? |
|---|--:|--:|---|
| Connect Four | 10¹⁴ | — | yes |
| Nine Men's Morris | 10¹¹ | — | yes |
| Awari | 10¹² | — | yes |
| Checkers | 5 × 10²⁰ | small `b` (forced captures) | **weakly**, 2007 |
| **FLIPHEX 4×4** (adr-009 deck) | 9.3 × 10¹⁰ | ~10³³ | target: **strongly** |
| **FLIPHEX 5×5** | 4.9 × 10¹⁷ | ~10⁶¹ | no |

Answer four things. (a) Checkers has ~1000× *more* states than FLIPHEX 5×5 and
was solved; FLIPHEX 5×5 will not be. Explain why using both axes — the
resolution is that state-space and game-tree complexity are independent, and
checkers is easy on the one that governs a forward proof. Name the quantity that
actually binds FLIPHEX. (b) Draw the boundary concretely: for which variants does
Axis 1 give exact truth (and of which Allis class — weak or strong?), and where
must Axis 2 take over? Produce the honest headline sentence. (c) **"Draws are
impossible" is a trade, not a gift** — it collapses the backward pass to a single
stratified sweep (no cycles, no GHI, no fixpoint) *and* it destroys the forward
proof's main economy, because on a two-element value set a bound *is* the value,
so Schaeffer's "partially proven" category is empty by construction. Which side
of that trade dominates for FLIPHEX, and does it change the boundary you drew in
(b)? (d) H3 asks the learner to agree with the solver on shared variants. Given
(b), on which boards is that comparison actually available, and is that enough
evidence to carry H3?

**My take.**

**Refined write-up.**

---

## S5 — What does solving a game actually buy? (Allis §6 ↔ R&N §6.7 ↔ Schaeffer §7) 🔄

*(New — this is what the [Schaeffer note](notes/schaeffer-2007-checkers-is-solved.md)
§7.1 forward-refs.)*

**Prompt.** Three sources give three different answers, and this project's thesis
needs a fourth.

- **Schaeffer §7** is upbeat: the significance is AI plus parallel computing,
  with methods transferring to bioinformatics. The *game* is barely the point.
- **Allis §6** ("which games will survive") reads the same act differently: a
  solved game loses something. Solving is partly an act of *ending* a game.
- **R&N §6.7** limitation 3: both alpha-beta and MCTS "do all their reasoning at
  the level of individual moves", with no abstraction and no goal-directed
  planning. A solve returns the *value*; it does not return the *why*.

Now the tension this project has to face. [research.md](docs/research.md)'s thesis
is that FLIPHEX is "a design to understand" — it wants first-player balance, the
joker's effect, deck quality, design feedback. But a solve produces a
win/loss verdict at the root and a lookup table. Answer: (a) does an exact 4×4
verdict actually serve the design thesis, or does it serve a *different*, more
conventional thesis that happens to be easier to defend? (b) H5 (deck balance)
and H6 (counterfactual robustness) cannot be answered by a root value at all —
what *can* the solved database tell you about them, if you query it rather than
just read its root? (Think: distribution of values over positions, which tiles
appear in optimal lines, how often the mirror-equivalent move is also optimal.)
(c) Is there a version of the writeup where the exact solve is the *instrument*
and the design findings are the *result*, rather than the solve being the result?
Write that headline.

**My take.**

**Refined write-up.**

---

## S6 — May Axis 2 feed Axis 1? (Schaeffer §4 ↔ adr-004's independence principle) 🔄

*(New — raised by the Schaeffer reading and currently unresolved in any ADR.)*

**Prompt.** [adr-004](docs/adr/adr-004-solver-approach.md) rejects MCTS as the
Axis 1 method **on principle**: "using it for Axis 1 would destroy the
independence that makes cross-axis verification meaningful. The two axes must
fail differently." That principle is what gives H3 its force.

Schaeffer's proof tree, however, is bootstrapped by domain knowledge the project
does not have: *"From the human literature, a single 'best' line of play was
identified and used to guide the initial foray of the manager into the depths of
the search tree… Without it, the manager may spend unnecessary effort looking for
an important line to explore."* FLIPHEX has **no human literature** — no opening
book, no expert lines. The obvious substitute is a policy from Axis 2. The same
question arises for move ordering, on which
[R&N §6.2.4](notes/russell-norvig-aima-ch6-adversarial-search.md) says the
solver's whole efficiency depends.

Settle where the line is. (a) Distinguish two uses sharply: Axis 2 deciding
**what order to do exact work in** (ordering, scheduling, seeding) versus Axis 2
supplying **values** the proof relies on. Does the first affect *correctness*?
(Alpha-beta returns the same value under any ordering; retrograde enumeration is
order-independent by construction.) (b) If correctness is untouched, what exactly
*is* damaged — and is "independence" the right word for it, or is the real risk
narrower: that a solver tuned by the learner will be *fastest exactly where the
learner is strongest*, leaving the disagreement regions under-searched? (c)
Propose a rule adr-004 could adopt, precise enough to implement. A candidate to
argue for or against: *Axis 2 output may influence the order and scheduling of
Axis 1 work, never its values or termination conditions; and any Axis-1 result
used to validate Axis 2 must be reproducible from a run with ordering seeded
only by Axis-1-internal heuristics.* (d) Would adopting that rule cost anything
real, given that 4×4 is a full enumeration where ordering is irrelevant anyway?

**My take.**

**Refined write-up.**
