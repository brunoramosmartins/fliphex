# ex05 — State space, game tree, branching, and what a cross-game table can carry

**Phase 5 and Phase 6 problem set.** Six problems. The first five come from the
roadmap's *Exercises — After Phase 6*, restated against what Phase 6 actually
built and measured; Q6 is added, because the phase produced a question the
roadmap could not have asked and the interfaces made unavoidable.

The exercise was carried from Phase 5, carried again from Phase 6, and written
in Phase 7. That is not a scheduling detail: by now every quantity below is
computed, checked and recorded, so no answer has to be estimated and each one
can be marked right or wrong against an artefact in this repository. It makes
the problems harder rather than easier.

**How to use this file.** Write **Answer** in first person, showing the work
including the wrong turns. **Refined** is written afterwards: corrections,
completed algebra, and the link back to the ADR or verdict each result feeds.
Same loop as the lit-notes, ex02, ex03 and ex04.

**Feeds:** [docs/research.md](../docs/research.md) H4 (Q1–Q5), H5 (Q4) ·
[adr-003](../docs/adr/adr-003-piece-representation.md) and
[adr-006](../docs/adr/adr-006-no-chain-reaction.md) (Q1) ·
[adr-008](../docs/adr/adr-008-board-mirror-symmetry.md) (Q5) ·
[adr-010](../docs/adr/adr-010-solver-correctness.md) V1 (Q1, Q6) ·
[adr-011](../docs/adr/adr-011-reduced-variant-parity.md) (Q1, Q6) ·
[experiments/registry.md](../experiments/registry.md) EXP-001, EXP-002, EXP-005,
EXP-007

**Reading:** [Allis 1994](../notes/allis-1994-searching-for-solutions.md) §1.5,
§6.2 and Definition 6.4 · [Schaeffer 2007](../notes/schaeffer-2007-checkers-is-solved.md)
· [Takizawa 2023](../notes/takizawa-2023-othello-is-solved.md) ·
[phase6-complexity-log.md](../notes/phase6-complexity-log.md)

**Code under discussion:** [`complexity/state_space.py`](../complexity/state_space.py) ·
[`complexity/game_tree.py`](../complexity/game_tree.py) ·
[`complexity/branching.py`](../complexity/branching.py) ·
[`complexity/comparison.py`](../complexity/comparison.py) ·
[`scripts/layer_profile.py`](../scripts/layer_profile.py)

> **Four corrections to the roadmap's statements**, all established during
> Phase 6. They are kept visible rather than silently patched, because
> diagnosing them is part of the exercise — and two of them survived into the
> *locked* hypothesis text, where they cannot be edited at all and had to be
> answered in the verdict instead.
>
> 1. **Q1's cell alphabet has four symbols and the game has three.** "empty,
>    purple, green, joker" treats the joker as a cell state. It is not: the
>    joker is a tile in the first player's hand, and once placed it shows its
>    owner's colour like every other tile. Nothing on the board ever reads as
>    "joker". A cell is empty, purple or green.
> 2. **Q1's `× 6 orientations` is wrong by a factor of 2.8 × 10¹⁹.** adr-003
>    and adr-006 make a placed tile inert — its arrows fire once, on the ply it
>    is placed, and nothing downstream can read its rotation. The orientation is
>    therefore not part of the state. This factor is also in H4's locked text,
>    so it could not be corrected there and is recorded as a deviation in the
>    verdict.
> 3. **Q3 asks for a Monte Carlo estimate of a quantity with a closed form.**
>    The game-tree size is exactly `4.229 × 10⁵⁸` on the shipped board, in
>    microseconds. The estimator was built anyway, and Q3 is partly about what
>    it is *for* once the exact answer exists.
> 4. **Q4's "decreases monotonically after some peak" has no peak.** Mean
>    branching falls strictly from the first ply to the last, on both of its
>    factors at once. The hump the question is remembering belongs to the
>    *layer profile*, which is a different curve — and telling the two apart is
>    the point of Q4.

---

## Q1 — The state-space bound, derived and then corrected

Derive an upper bound on the number of FLIPHEX positions, from the rules rather
than from the roadmap's expression.

1. State the alphabet a single cell can show, and justify it against
   [adr-007](../docs/adr/adr-007-flip-toggles-colour.md) and the joker's role in
   the deck. Explain why the first player's extra tile does not add a symbol.
2. Give the count of configurations with exactly `t` cells filled as a product
   of three independent factors, and say what makes them independent. Name the
   hand sizes for the shipped 5×5, the 5×3 and the 3×3, and derive them from
   adr-011's parity rule rather than quoting them.
3. Sum over `t` and evaluate for all three boards. Then compute the
   orientation-inflated figure the roadmap asked for, and report the ratio.
4. `complexity/state_space.py` keeps the discarded expression in the shipped
   module under `orientation_inflated()`. Argue for or against keeping it.
5. This sum is also what [adr-010](../docs/adr/adr-010-solver-correctness.md)
   V1 checks the solver's enumerator against, layer by layer, with no tolerance.
   Explain why a *bound* can serve as an exactness gate — what would have to be
   true of the enumerator for the check to pass while the enumerator was wrong?

**Answer.**

**Refined.**

---

## Q2 — Tightening the bound, and where the tightening stops

The roadmap proposes removing unreachable states via "turn-parity constraint,
deck-composition constraints".

1. Show that both of those are **already in the Q1 expression**, so neither is a
   tightening. Where exactly does each one sit?
2. The real one-step correction is an orphan count. Prove the predecessor
   criterion: a configuration at layer `t ≥ 1` has no predecessor exactly when
   every occupied cell shows the colour of the player who did *not* just move.
   The load-bearing step is that a tile's own arrows never point at the cell it
   occupies — find that in the rules and cite it.
3. Show that this is **one colouring in `2^t`**, and that the `2^t` therefore
   cancels out of the sum, leaving a closed form. Evaluate it: the correction is
   3.28% on the 3×3, 0.343% on the 5×3, 0.0079% on the shipped 5×5. Explain the
   direction — why does the correction shrink by roughly an order of magnitude
   per board step?
4. Layer 0 satisfies the criterion and is reachable anyway. Explain why, what
   the unguarded sum reports on the 3×3, and why that discrepancy is invisible
   as a percentage and visible as a count.
5. The **transitive** closure — configurations no *game* reaches, rather than
   configurations no single *move* produces — is strictly smaller and has no
   closed form. EXP-007 measured six layers of it on the 5×3 and was stopped at
   429.8 seconds with both arms projected at ~100 hours each. Write the argument
   for stopping as a decision rule, in terms of what the number would have been
   used for. Then state the condition under which the same decision would be
   wrong.

**Answer.**

**Refined.**

---

## Q3 — An unbiased estimator of a quantity you can count exactly

1. Prove that Knuth's random-path estimator is unbiased: walk uniformly from the
   root to a leaf, multiplying the legal-move count at every node visited. Give
   the probability of reaching a particular leaf and show the product telescopes
   to 1 in expectation. State precisely which assumption about the tree the
   proof needs — and, importantly, which it does *not*.
2. State the variance behaviour in general, then specialise it. On the 3×3 the
   measured relative standard deviation of a single rollout is **4.0**, and on
   the shipped board about **5**. Explain where that skew comes from
   mechanically. How many rollouts for 1% standard error, and how does that
   compare with the cost of the exact count?
3. Derive the exact count. A move is (empty cell, tile in hand, distinct
   rotation) and **every such triple is legal** — no capture condition, no
   passing, no forbidden placement. Show that a complete game is three
   independent bijections and obtain

   ```
   games = n! × d1! × ∏ orbits(hand 1) × d2! × ∏ orbits(hand 2)
   ```

   Evaluate for all three boards.
4. Truncating at `k` plies replaces the orbit products with **elementary
   symmetric polynomials** over the orbit sizes: choosing `j` tiles in order
   contributes `j! · e_j(orbits)`. Show why the naive `sum(orbits)^j / j!` is
   wrong, and name the concrete over-count it commits.
5. The tree is genuinely unbalanced — orbits run from 1 (`P6`, `JOKER`) to 6 —
   so no single `b^d` is exact, and yet the leaf count is. Resolve the apparent
   contradiction.
6. Given 3–5, `rollout_estimate()` is kept in the module and its own numbers
   argue against using it. What is its status now, and what class of error would
   it still catch that a unit test on the closed form would not?

**Answer.**

**Refined.**

---

## Q4 — `b(t)`, and the two different curves it is confused with

1. Write the width of a node at ply `t` as a product of two factors. One is
   fixed by `t` alone; the other is not. Say precisely what the second depends
   on and why there is therefore a **distribution** at each ply rather than a
   number.
2. Two averages are available: uniform over the mover's possible spent sets, and
   weighted by how many prefixes reach each spent set. Show that the weight is
   proportional to `∏ orbits(S)`, and state which question each average answers.
   At ply 8 they are 628.7 and 682.6; at ply 24, 2.9 and 4.5. Explain why the
   gap runs the same direction at every ply and widens.
3. Prove the identity
   `node-weighted mean branching at t == prefixes(t + 1) / prefixes(t)`,
   exactly, as a ratio of integers — and show that these ratios **telescope** to
   the exact game-tree size of Q3, with no Jensen gap.
4. The first implementation of `branching.py` left out three constant factors
   (the cell arrangement, the play orders, the other player's hand). **The
   means were unaffected** and every distributional claim still looked correct;
   the node count was out by twenty orders of magnitude. Explain why the means
   survived, and what that says about which tests are worth writing for a module
   whose output is mostly averages.
5. Settle the roadmap's premise. Mean width falls strictly at every ply, on both
   factors — so where does the hump in the layer profile come from? Name the
   factor, and say why "the game gets more complex in the middlegame" is the
   natural reading of one chart and false of the other.
6. Connect the spread to Q3: the 6× spread at ply 24, compounded over 25 plies,
   is the rollout estimator's variance. Make that argument quantitative enough
   to be wrong.

**Answer.**

**Refined.**

---

## Q5 — The cross-game comparison, including the parts it refuses to make

The roadmap asks for a comparison against **Reversi 6×6** and **Hex 5×5** on
three metrics. Neither comparator is available as asked, and the reasons differ.

1. The widely repeated 6×6 Reversi state space of ~10²⁰ is **impossible**.
   Give the ceiling argument in one line and the overshoot factor. Then explain
   why this is not a footnote for us specifically — trace it to H4's original
   Phase 0 wording.
2. Hex 5×5 is **absent** from the table rather than refuted, and Hex 11×11 sits
   there instead with an `ultra-weakly solved` status and no figures. Say what
   would be needed to fill the 5×5 row, and whether an ultra-weak solution of
   the 11×11 tells you anything at all about the 5×5.
3. `comparison.py` grades every cell — `exact`, `verified`, `reported`,
   `refuted`, `absent` — and `self_check()` opens the cited source file looking
   for each `verified` quote. Argue for the grade column against the obvious
   objection that a table with nine empty cells is less useful than a full one.
4. **The apples-to-apples question, which is the real content of Q5.** FLIPHEX's
   solution depth is exactly 25 and no move is ever illegal; Othello has passes,
   games that end early, and a capture condition that constrains legality.
   Allis's Definition 6.4 counts the solution search tree at minimal full-width
   depth, writes "number of nodes", and counts *leaves* in both of his worked
   examples. Work out what is and is not comparable across those differences,
   and state what our 10^58.63 may be set beside without qualification.
5. **The finding the verdict had to answer.** Othello 8×8's game tree is
   10^58.00 and it was weakly solved in 2023; FLIPHEX's is 10^58.63 — a factor
   of four. H4's locked clause 2 says the shipped board is "beyond the weak
   solution route that carried checkers". Read the clause against checkers, then
   against what has actually been weakly solved, and say what survives. Note
   that Takizawa is in this repository and was read in Phase 2.
6. Allis defines the state space as the **reachable** set and explicitly
   declines to quotient by symmetry — while his own computed figures are
   invariant-consistent supersets sampled for legality. We report the
   reachability-corrected number and leave adr-008's Z/2 mirror in. At 0.0079%
   this changes nothing on our board. Construct a game where it would change the
   ranking, and say what that implies about reading any such table.

**Answer.**

**Refined.**

---

## Q6 — What "solved" licenses, and the asterisk in our own row

Added in Phase 7, when the interfaces made the question concrete: the solver
seat can be backed either by a forward search or by a completed retrograde
sweep, and those are not the same kind of knowledge.

1. Quote Allis's three grades — **ultra-weakly**, **weakly**, **strongly**
   solved — and classify each of this project's Axis-1 artefacts. Be specific
   about which one the four exhaustive solves of EXP-001 and EXP-002 produce.
2. Explain why a **retrograde sweep** yields a *strong* solution while a forward
   alpha-beta from the initial position, exhausted and proved, yields only a
   *weak* one — even when both terminate and agree on the root value. What does
   the sweep hold that the search discards?
3. Until Phase 7 the table printed `unsolved (solved here)` for the 3×3 and the
   5×3 — a `solved` field contradicting its own note. It now prints
   `strongly solved *`, with the footnote "solved by this project's own runs,
   verified under adr-010 and not independently reimplemented." Say what the
   asterisk is doing that the grade column was not, and whether the other rows
   deserve one too.
4. A test asserts that the shipped 5×5's state space exceeds every **strongly**
   solved game in the table. Once our own boards became strongly solved, that
   test could pass trivially by self-comparison. It now filters rows whose
   `solved_source` is this project. Generalise: name the class of regression
   this belongs to, and give one other place in this repository where the same
   failure mode is available.
5. What would have to happen for the asterisk to come off the 5×3 row? Answer in
   terms of adr-010's verification levels and what a second party would have to
   do — not in terms of more compute.
6. Finally, the honest version of the headline. The 5×3 database is 4.1 GB, is
   gitignored, and a clone has none; the interfaces fall back to search and say
   so. In one paragraph, state what this project has actually solved, in a form
   you would be willing to defend to someone who has read Schaeffer.

**Answer.**

**Refined.**
