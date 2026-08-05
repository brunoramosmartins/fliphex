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

After reading these works together, I realized that I had initially framed AlphaZero too narrowly. My original goal was simply to build a strong agent capable of playing FLIPHEX. The literature changed that perspective: I now see AlphaZero less as a game-playing algorithm and more as a methodology for discovering knowledge about a game.

The most important conceptual shift is not the replacement of UCT by PUCT or the removal of rollouts. Those are implementation details of a broader idea. The real innovation is that search no longer exists only to choose the next move; it also generates the training signal that improves the neural network. Visit counts become the policy target, producing a feedback loop in which better search creates better training data, which in turn produces a better search procedure. Once I understood this loop, AlphaZero stopped looking like "MCTS with neural networks" and started looking like an integrated learning system.

Studying the role of the policy and value networks also clarified a distinction that I had initially overlooked. The policy network does not replace exploration; it biases exploration toward promising actions. Likewise, the value network does not merely accelerate search by avoiding expensive rollouts. More importantly, it replaces evaluations based on random play with evaluations that increasingly approximate the value of a position under strong play. Computational efficiency is therefore a consequence of this design, not its only motivation.

For FLIPHEX, the motivation extends beyond building a competitive agent. Because the game is original, there are no expert players, opening books, or historical games from which to derive heuristics. Self-play therefore becomes a way to investigate the game itself. Instead of asking only whether an agent can become strong, I can also ask whether the game appears balanced, whether the first player has an inherent advantage, whether stable strategic patterns emerge, or whether weak solutions seem plausible. In that sense, reinforcement learning becomes an experimental instrument for game design rather than only an optimization technique.

Finally, these readings changed how I interpret the progression from classical MCTS to AlphaZero. I no longer see it simply as replacing human knowledge with learned policies. I see it as progressively replacing handcrafted evaluation procedures with a closed learning loop in which search continuously improves the model that guides future search. For an unexplored game such as FLIPHEX, that methodology is arguably more valuable than any individual architectural component.

**Refined write-up.**

The headline is right and it is the one most summaries miss: the substitution
that makes AlphaZero *AlphaZero* is row four of the table — the search output is
not a move but a distribution, `π ∝ N^{1/τ}`, which becomes the policy target.
Without that row the system is guided MCTS. Keep it.

But "the exploration term and the rollout are implementation details of a broader
idea" is too generous, and at FLIPHEX's branching factor it is false for one of
the two.

**(a) PUCT is not a cosmetic change at b₀ = 1450.** UCB1's `√(ln N / n(a))` is
*infinite* at `n(a) = 0`, so plain UCT is obliged to visit every child once
before the formula distinguishes any of them. On ply 1 that is 1450 simulations
spent enumerating, and a second 1450 before any child has two samples. PUCT's
`√ΣN / (1 + N(a))` is finite at `N(a) = 0` and scaled by `P(a)`, so the prior
ranks all 1450 children *before* any of them is visited.

What is traded is the *kind* of guarantee. UCB1's term is a concentration bound —
it is derived from Hoeffding and its regret guarantee is distribution-free: it
holds whatever the game is, with no prior. PUCT's term is not a bound of
anything; it is a decay schedule (`1/n(a)` at fixed total, against UCB1's
`1/√n(a)`) whose only justification is that `P(a)` was roughly right. So you
trade a distribution-free guarantee for a prior-conditional one. That trade is
**necessary, not convenient**, because at b = 1450 a distribution-free guarantee
needs ≫ b samples before it says anything, and a laptop search will never run
≫ 1450 simulations per move. A guarantee you cannot afford to collect is not a
guarantee.

**(b) The rollout was the only unbiased estimator in the algorithm** — unbiased
for the value of the leaf *under the rollout policy*, which is exactly its
weakness and exactly why it was safe: it never claimed to know anything. Note
what does **not** replace it. Nothing inside the search keeps `v` honest; a
single AlphaZero search is entirely a function of a network that could be
arbitrarily wrong. The anchoring moved *out* of the search and into the training
loop: `v` is regressed on `z`, the actual game outcomes, so the estimates are
kept honest across the corpus rather than within one search. Your phrase
"increasingly approximate the value under strong play" is right; the point worth
adding is that "increasingly" is doing structural work — early in training the
search has no honesty mechanism at all.

**The FLIPHEX consequence the take skips.** The two changes have *different*
standing here, and conflating them would cost you a cheap baseline:

| change | status for FLIPHEX |
|---|---|
| UCT → PUCT (prior) | **required** — b₀ = 1450 makes prior-free selection useless |
| rollout → network `v` | **inherited**, defensible, not forced |

Rollouts in FLIPHEX are ≤ 25 plies, always terminate, and always yield a decided
winner (no draws, fixed length). R&N's second MCTS disadvantage — positions
"obviously" won but needing many playout moves to verify — is void, and their
early-playout-termination machinery is unnecessary. So **plain UCT with random
playouts is a legitimate Axis-2 baseline**, costs almost nothing to build, and
gives an absolute floor that does not depend on any network being trained
correctly. Recommend adr-005 name it as the baseline the learned agent must beat.

**Imperfect information.** The reason FLIPHEX may drop rollouts is that perfect
information makes `v` a function of the state alone — there is no belief to
average over. In your PTCG project a leaf is an *information set*, and a scalar
`v(s)` evaluated at the true state is an oracle the player does not have:
averaging it over determinizations gives strategy fusion (the search silently
plays a different move in each world) and non-locality. The substitute is not a
better evaluator but a different solution concept — ISMCTS over information sets,
or a CFR-family method whose values are defined on information sets and whose
target is an ε-Nash strategy rather than a state value. Worth recording that the
FLIPHEX hidden-hand variant was rejected for a different reason
([R&N note §6.5.1](notes/russell-norvig-aima-ch6-adversarial-search.md)): the
deck is public and placements are public, so the belief state is a point mass and
the variant is not imperfect-information at all.

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

After comparing AlphaGo Zero and AlphaZero, I do not interpret the removal of the evaluator gate as evidence that it became unnecessary. The papers show that AlphaZero succeeds without the gate, but they do not present an explicit experimental justification that the gate itself no longer provides value. To me, this makes its removal an engineering decision rather than a demonstrated scientific conclusion.

The evaluator gate serves a clear purpose: it establishes the strongest accepted network as a moving benchmark and only promotes a challenger after it demonstrates a meaningful improvement through direct competition. This does not guarantee monotonic improvement, but it significantly reduces the risk of promoting a weaker policy and propagating that regression into future self-play data. Since reinforcement learning continually trains on data generated by the current policy, accepting a poor network affects not only one generation but also the distribution of future training examples.

AlphaZero abandons this protection in favor of a simpler and more compute-efficient training pipeline. At DeepMind's scale, where thousands of TPUs, extensive experimentation, and repeated runs make occasional regressions relatively inexpensive, that trade-off is reasonable. However, I do not believe the same reasoning transfers directly to a single-laptop research project.

For FLIPHEX, I would keep the evaluator gate. The game has no established human expertise, historical datasets, or external benchmark against which to measure progress. The strongest accepted network therefore becomes the only reliable reference available. Although evaluation games consume compute that could otherwise be spent on self-play, they provide confidence that apparent improvements correspond to genuine progress rather than fluctuations in training. In a setting where a failed training run may cost several days, sacrificing some compute for greater experimental stability is a worthwhile trade-off.

My recommendation for ADR-005 is therefore to retain the evaluator gate during the initial stages of the project. Once the implementation, training pipeline, and evaluation methodology become well understood, its removal can be investigated as an optimization, but it should not be treated as a default inheritance from AlphaZero simply because the published system omitted it.

**Refined write-up.**

"The papers show that AlphaZero succeeds without the gate, but they do not
present an explicit experimental justification" is correct, and it can be made
stronger. The removal is **bundled**: AlphaZero simultaneously drops the gate,
maintains a single continuously-updated network, generates self-play from that
network rather than from a frozen best player, and reuses hyper-parameters
instead of re-tuning them. No experiment in either paper isolates the gate. So
the evidence available is "a system without the gate works", never "the gate was
unnecessary" — those are different claims, and only the first is demonstrated.

One correction to the framing, though. The gate was not simply *abandoned*; part
of its function was **absorbed elsewhere**, and this matters for your
recommendation. The gate is a coarse guard: it acts at generation granularity and
its decision is binary. AlphaZero's continuous updating with a large replay
buffer and a small learning rate makes each update a small perturbation of a
policy that is already a mixture over many recent generations — a single bad
gradient step cannot move the self-play distribution far, because most of the
buffer predates it. So the honest statement is that AlphaZero replaced a
**discrete, measured** guard with a **continuous, unmeasured** one. Your argument
survives — an unmeasured guard is still unmeasured — but it is no longer "they
removed the protection", it is "they replaced it with something whose adequacy
they did not test".

**The recommendation needs a number.** "Keep the gate" is under-specified,
because the gate's value is entirely a function of how many evaluation games it
runs. AGZ's 400 games are what make a 55 % threshold mean anything: at n = 400,
two equal networks clear 55 % about 2 % of the time. At n = 100 they clear it
**16 %** of the time — a gate that promotes noise one time in six is worse than
no gate, because it costs compute *and* creates false confidence. So adr-005
should say either 400 games, or an explicit relaxation (gate every k
generations, or a lower threshold with a stated false-promotion rate) — never
"keep the gate" with the budget left implicit.

**And one trap to close now.** The cheapest imaginable gate for FLIPHEX is
absolute rather than relative: score candidate networks against the exact values
from the 4×4 solved database. Near-zero compute, no opponent needed, an
objective yardstick where none otherwise exists. **Do not do it.** Selecting
networks by agreement with the solver and then reporting agreement with the
solver as H3's evidence is circular — the metric would be optimised directly by
the selection procedure. This is the same boundary S6 reaches from the other
direction (Axis 2 may not supply Axis 1's values; Axis 1 may not supply Axis 2's
selection criterion), and it is worth stating in adr-005 explicitly, because the
temptation is real and the flaw is invisible once the pipeline is written.

Solver positions may be used freely as a *reported diagnostic* — logged, plotted,
watched — provided no promotion, early-stopping, or checkpoint-selection decision
reads them.

---

## S3 — Symmetry: what FLIPHEX actually has, and what it is worth 🔄

*(Rewritten — the original premise, "FLIPHEX's board symmetry group is trivial",
is false.)*

> **Verification.** `scripts/check_mirror_game_symmetry.py` proves the claims used
> below (only `P3-y` is chiral; 150/1450 opening moves have no legal mirror; the
> mirror becomes a full game symmetry once both copies are placed).
> `scripts/show_mirror_break.py` renders the same three facts on the board.

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

After revisiting FLIPHEX through the lens of AlphaGo Zero, AlphaZero, and the symmetry analysis in ADR-008, I realized that I had initially been asking the wrong question. The relevant question is not whether the board is symmetric, but whether the game state preserves that symmetry throughout play.

FLIPHEX illustrates this distinction particularly well. The board itself admits a left-right mirror, yet the game does not because the chiral P3-y tile breaks that correspondence while either copy remains in a player's hand. As a result, mirroring a position generally does not produce another legally equivalent game state. The board possesses a geometric symmetry, but the game temporarily does not.

This changes how I interpret AlphaGo Zero's data augmentation strategy. Data augmentation is only valid when the transformation preserves the entire game dynamics, including legal actions, state transitions, and outcomes. A board automorphism alone is insufficient. Since the P3-y tile remains unplayed during much of a typical FLIPHEX game, only a small fraction of self-play positions satisfy this condition. Consequently, I do not expect symmetry augmentation to provide a meaningful increase in training data, making AlphaZero's decision to omit augmentation the more appropriate design choice for Axis 2.

Interestingly, the same symmetry becomes fully available once both P3-y tiles have been placed. At that point, the remaining game state regains mirror equivalence, exactly where exhaustive endgame methods operate. This explains why the symmetry is almost irrelevant for self-play learning but still valuable for exact retrograde analysis. The distinction is therefore not between learning and solving themselves, but between the portions of the state space on which they operate.

Perhaps the most interesting outcome of this analysis is that it changed how I evaluate the design of FLIPHEX itself. When the game was created, the objective was to obtain an elegant and strategically interesting piece set, not to maximize exploitable symmetries. Knowing what I know today, I would likely redesign the P3-y tile to preserve the mirror symmetry throughout the game. Not because symmetry is aesthetically desirable, but because the literature made me realize that seemingly small design decisions can directly affect the algorithms available for analyzing and learning the game.

**Refined write-up.**

The reframing is exactly right and it is the load-bearing sentence of the whole
section: *the question is not whether the board is symmetric but whether the game
preserves that symmetry*. Everything below either sharpens it or puts a number on
it.

**One phrase to correct, and it is the same one that made the diagrams confusing.**
"Mirroring a position generally does not produce another legally equivalent game
state" — it does. `M(s)` is always a perfectly legal, perfectly ordinary
position, and the flip rule itself commutes with `M` in every case tested
(`scripts/check_mirror_game_symmetry.py`, part C: `M(RESULT(s,a)) ==
RESULT(M(s),M(a))` holds wherever `M(a)` exists, with and without `P3-y` in
hand). What fails is not the position but the **move set**. `M` reflects an arrow
pattern, and `P3-y`'s reflection `{N,S,NW}` is not among its six rotations and is
not produced by any other tile at any rotation — a hex tile may be rotated but
never turned face-down, so a tile's achievable patterns are its rotation orbit,
not its full symmetry orbit. Part B measures the cost: **150 of the 1450 opening
moves have no legal mirror image**, exactly 25 cells × 6 rotations, every one of
them `P3-y`. The break lives in `ACTIONS(s)`, not in `s`.

**"A small fraction" can be quantified.** Purple holds 13 tiles (the 12-tile deck
plus the joker) and plays all 13 on the odd plies; green holds 12 and plays all
12 on the even plies ([rules-canonical.md](docs/rules-canonical.md) §2, I3/I5).
Every tile reaches the board, so both `P3-y` copies are *always* placed — the
mirror always becomes a game symmetry eventually, the only question is when.
Under a uniform-random play order:

| quantity | value |
|---|--:|
| E[fraction of plies where the mirror is a valid game symmetry] | **0.31** |
| E[ply on which the second `P3-y` lands] | 17.2 |
| P(both placed by ply 16) | 0.41 |
| P(both placed by ply 20) | 0.64 |

(Random-order estimate — the distribution under optimal play is unknown and could
move in either direction. It is the right order of magnitude for a design
decision, not a measurement.)

**(b) The decision, with the arithmetic done.** 2× on 31 % of positions is an
effective **1.31×** in data. Against b₀ = 1450 and a laptop budget that is a
rounding error, and it is not free: every augmented sample needs a
validity check (is `P3-y` out of *both* hands?), and augmenting one invalid
position silently poisons the policy target with a move that does not exist.
AlphaZero's choice is correct here, for a reason AlphaZero never had to give.
The line adr-005 should carry, replacing the stale
`adr-005-alphazero-scope-and-network.md:56` justification ("the board's symmetry
group is trivial (adr-002)", which is **false** — adr-008 supersedes it):

> **No symmetry augmentation.** The board has a Z/2 mirror
> ([adr-008](docs/adr/adr-008-board-mirror-symmetry.md)), but the chiral `P3-y`
> tile makes it a *partial* game symmetry: it is valid only once both copies are
> placed, ≈31 % of plies under a random play order. The available gain is ≈1.31×
> in data, against a per-sample validity check and a silent-corruption risk if
> the check is wrong. Not worth it.

**(c) The inversion is a pattern, not an accident, and it has a mechanism.**
Symmetries in games are broken by state components that are *consumed*: hands,
castling rights, en passant, ko. Consumption is monotone toward the terminal, so
a symmetry broken by a consumable resource is **late-holding by construction**.
Retrograde analysis is indexed *from* the terminal end, so it lives precisely
where such symmetries hold; a learner sees whole trajectories, so it gets the
time-average. Chess tablebases are the standing example: with pawns on the board
only the file mirror is available, and the full 8-fold board symmetry is
recovered exactly in the pawnless endings — the same shape as FLIPHEX's `P3-y`.
So the honest generalisation is: *symmetries broken by consumable state help
exact endgame methods and not learners*, and that covers both games.

**But deflate the "~2× to Axis 1" in the prompt** — it is real and it is small.
The k-layer bounds are k ≤ 3: 9.0×10¹², k ≤ 4: 1.5×10¹⁴, k ≤ 5: 1.2×10¹⁵, i.e.
each extra empty cell costs ~8–17×. A 2× fold buys `log 2 / log 8 ≈` **one third
of one k level**. Worth taking, never worth designing around.

**(d) — unanswered above, and the answer no longer mentions symmetry.** Yes, the
exact solver is the cheaper source of ground truth on small variants, but because
its cost is *knowable in advance*: 4×4 reduced is 9.3 × 10¹⁰ states, a number you
can multiply by bytes and compare to a disk before writing any code. The learner's
cost to reach a given accuracy is unknown, and — this is the real argument —
unknowable without an oracle, which is the thing the solver is being asked to
provide. That asymmetry is what makes Axis 1 the reference, and it survives
adr-008 entirely. Symmetry was never part of it.

**On redesigning `P3-y` — I would argue against, and the section's own numbers
are the argument.** Removing chirality would make the mirror a full game symmetry
throughout, which buys: ≈2× data on Axis 2 (you just valued the partial version
at 1.31× and rejected it), and ~⅓ of a k level on Axis 1. Against that,
chirality is the **only** thing in the design that distinguishes a line of play
from its mirror image. Remove it and every opening acquires an exactly-as-good
twin — the strategically distinct opening set halves, and H1 becomes partly
trivial for the wrong reason. That is a real design cost paid for a training
convenience the section already valued at ≈0.

The better move is to record this as a *finding*: **`P3-y`'s chirality is
load-bearing game content, not an oversight.** And note that the instinct is
already pre-registered as an experiment —
[research.md](docs/research.md) H6 names the perturbation explicitly ("deck
swaps, e.g. removing the chiral `P3-y`"). You do not have to redesign the game to
find out; you have to run H6.

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

After reading Allis, Schaeffer, and Silver together, I realized that they are not proposing competing solutions to the same problem. Instead, they describe two fundamentally different ways of obtaining the value of a game. Exact solving computes the true value of positions whenever the state space is tractable, while reinforcement learning attempts to approximate that value when exact computation becomes infeasible. The interesting question is therefore not which approach is better, but where the boundary between them lies.

Before these readings, I was tempted to compare games only by the size of their state spaces. The comparison between Checkers and FLIPHEX made me realize why that intuition is misleading. Checkers contains orders of magnitude more states than FLIPHEX 5×5, yet it was weakly solved because the quantity that limits a forward proof is not the number of states alone, but the game-tree complexity induced by the branching factor. FLIPHEX's freedom to place any remaining piece on almost any empty square creates an enormous search tree despite having a comparatively smaller state space. The limiting factor is therefore not how many positions exist, but how many continuations must be explored.

This distinction naturally divides the project into two complementary regimes. Small FLIPHEX variants fall within the reach of exact methods and can provide ground truth, while larger variants require approximate methods such as AlphaZero. I no longer see this as choosing between two algorithms; I see it as choosing the appropriate methodology for each region of the complexity landscape.

The absence of draws reinforces this interpretation. Eliminating draws simplifies retrograde analysis because every terminal state belongs to only one of two outcomes, allowing values to propagate cleanly backward through the state graph. At the same time, it removes much of the pruning power available to forward proofs, since proving that a position cannot lose immediately determines its value. This trade-off does not change the boundary between solving and learning, but it clarifies why exact methods remain practical only for sufficiently small variants.

Perhaps the most important consequence of these readings is how they changed my interpretation of H3. I no longer see the exact solver as an alternative to reinforcement learning. Instead, I see it as the experimental reference against which the learned value function can be evaluated whenever both approaches are feasible. Once the exact solution is no longer computationally attainable, the solver has already fulfilled its role: it has validated the methodology before approximation becomes the only remaining option.

**Refined write-up.**

The two-axis resolution is right, and "the limiting factor is not how many
positions exist but how many continuations must be explored" is the correct
sentence. Three things need to be made precise before this can carry H1/H3.

**(a) Name the binding quantity — and notice it is *different* for the two
variants.** This is the finding of the section and the take stops just short of
it.

| | binds on | number | the rational method |
|---|---|--:|---|
| FLIPHEX 5×5 | game-tree complexity | ~10⁶¹, and ~10³⁰·⁵ even at the Knuth–Moore minimal tree `b^⌈d/2⌉ + b^⌊d/2⌋ − 1` | none — out of reach |
| FLIPHEX 4×4 (adr-009 deck) | state count | 9.3 × 10¹⁰ states, against a tree of ~10³³ | **enumerate, do not search** |

Two details make FLIPHEX's tree unusual and both are worth stating. Depth is not
a distribution, it is a **constant**: 25 cells, exactly one placement per ply, no
passes, no captures, so every game is exactly 25 plies. And `b` stays large
because it is `(25 − t)` empty cells × the distinct rotations of everything still
in hand — it decays slowly and from 1450.

The consequence for 4×4 is the sentence adr-004 does not yet contain: the tree is
10²² times larger than the table, so **4×4 is not a search problem, it is an
enumeration problem**. Perfect move ordering still leaves ~10¹⁶·⁵ nodes at the
Knuth–Moore limit, while the whole state space fits in ~10¹¹ entries. That
reframes adr-004's "move ordering drives everything": ordering matters for a
depth-limited 5×5 *agent*, and is irrelevant to the 4×4 *proof*, where the
binding resources are storage and enumeration throughput.

**Sharpen the checkers comparison.** "Small `b` because of forced captures" is
true but incomplete; the deeper property is the one your own Schaeffer *Lessons
Learned* already names — **convergence**. Captures are irreversible, so the state
graph funnels into a small endgame family that retrograde analysis can close
once, and the forward proof only has to *reach* it. FLIPHEX has no analogue. The
layer profile is a **hump**, not a funnel — it peaks at t = 15 filled
(1.09 × 10¹⁷, 22 % of all states) and collapses to 3.36 × 10⁷ at t = 25 — and
because `k` empty cells is rigidly equivalent to ply 25 − k, there is no *early*
convergence to exploit: you cannot reach the narrow region sooner by playing
well. That, not the state count, is the structural difference from checkers.

**(b) The headline sentence:**

> FLIPHEX 4×4 with the adr-009 reduced deck admits a **strong** solution by
> retrograde enumeration of its 9.3 × 10¹⁰ states; FLIPHEX 5×5 admits neither a
> strong nor a weak solution, because at b₀ = 1450 over a fixed depth of 25 even
> a perfectly ordered forward proof faces ~10³⁰ nodes. The 5×5 is Axis 2's
> exclusively, except for the endgame layers, which Axis 1 can reach from the
> terminal end.

**(c) Your answer is right; here is the sharper reason.** The no-draw trade only
bites where the method is a *forward proof* — that is where a two-element value
set collapses Schaeffer's "partially proven" category and destroys the partial-
proof economy. 4×4 is an enumeration and has no forward proof; 5×5 is out of
reach on branching whether or not the economy exists. So the trade lands entirely
in a regime FLIPHEX never enters. The boundary in (b) is unchanged — not because
the trade is minor, but because it is **inapplicable**. Worth recording in
adr-004 as a trade nonetheless, so the reasoning is not rediscovered later.

**(d) — and this is the one pre-lock action the section produces.** "The solver
is the reference whenever both are feasible" is right in principle. Ask where
that is actually true, and the answer today is: **one board**. H3's cross-axis
clause would rest on a single variant (4×4 reduced), n = 1. That is not enough to
carry a hypothesis, and the fix is available now:

- adr-009's reduced-deck policy is precisely what generates a *family* of
  comparison points — 3×3 full deck (3.1 × 10⁹, the correctness fixture), 4×4
  reduced, and 4×4 under alternative reduced decks.
- More importantly, the **endgame layers of the shipped 5×5** are solvable from
  the terminal end (k ≤ 4 at 1.5 × 10¹⁴ is a storage question, not a search one)
  and give solver-vs-learner comparison **on the real game**, not only on a toy.
  That is a qualitatively stronger datapoint than any reduced board, and H3 as
  currently worded does not claim it.

Recommend H3 be reworded before `v0.3-hypotheses` to name its comparison set
explicitly — the reduced boards *and* the 5×5 endgame layers — rather than
saying "shared variants" and leaving the count to be discovered in Phase 5.

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

After reading Allis, Russell & Norvig, and Schaeffer together, I realized that I had initially assigned the wrong role to the exact solver. My original goal was to solve FLIPHEX 4×4 and report whether the first player wins. The readings convinced me that this result, by itself, says surprisingly little about the quality of the game's design.

An exact solution provides the value of every position, but it does not explain why those values arise or what strategic principles they reveal. As Russell & Norvig point out, search algorithms reason at the level of individual moves rather than abstractions. The solved database therefore answers "what is optimal?" but not "what makes it optimal?". The interesting knowledge emerges only after querying the database, identifying recurring patterns, and constructing higher-level explanations from those observations.

This perspective also reconciles the apparently conflicting views of Allis and Schaeffer. Schaeffer is right that solving a game advances AI and produces techniques that transfer beyond games. Allis is also right that solving can diminish the game itself by replacing exploration with certainty. For FLIPHEX, however, neither outcome is the primary objective. The solved game is not the final product; it is an instrument for studying the game's design.

Seen this way, the exact solution becomes much more valuable than a single win/loss verdict at the initial position. It allows questions that directly support the project's hypotheses: How balanced is the deck? Which pieces appear most often in optimal lines? Which opening moves dominate? How sensitive are optimal strategies to small rule changes? How frequently do symmetric choices remain equally good? These questions cannot be answered by the root value alone, but they can be answered by systematically interrogating the solved state space.

This changed how I interpret the role of H5 and H6. Their purpose is not to prove that FLIPHEX is solved, but to use the solved variants as experimental laboratories for understanding the consequences of design decisions. The strongest contribution of the exact solver is therefore methodological rather than computational: it transforms intuition about game design into hypotheses that can be tested against complete, objective ground truth.

**Refined write-up.**

This is the strongest of the six, and the reconciliation of Allis against
Schaeffer is exactly right: they disagree about what solving *costs*, not about
what it *is*. Three additions.

**One asymmetry worth naming, because it works in your favour.** Allis §6's
argument that solving diminishes a game presupposes a game people play — the loss
is to a community of players, and it is real for checkers. FLIPHEX has no player
base, no opening theory, and no literature. There is nothing to diminish. That is
not a small point: it means the usual argument *against* solving a game does not
apply here, and it is a reason to solve FLIPHEX **now**, while the cost of
certainty is zero. Worth one sentence in the writeup, because a reader who knows
Allis will expect the objection.

**(c) The headline you were asked for:**

> The exact solve is the instrument, not the result. FLIPHEX 4×4 is solved in
> order to *measure* an original game's design — first-player advantage, deck
> balance, the joker's effect, and the robustness of all three under bounded
> perturbation — against complete ground truth rather than against play.

**(b) The queries have to be specified now, not in Phase 5.** This is the part
the take reaches conceptually and does not yet make actionable, and it has a
deadline: the database's *index* is determined by which queries it must answer.
If it is stored keyed only by position → value, several of these become a full
re-scan; if it carries ply and hand as index dimensions, they are lookups.
Concretely:

| hypothesis | what the root value gives | what the *database* gives |
|---|---|---|
| **H1** | one bit | the fraction of positions at each ply `t` won by the player to move — a **curve**. Answers whether first-player advantage is structural from ply 1 or is manufactured at some phase. |
| **H5** | nothing | **tile criticality**: for each archetype, the fraction of positions where removing it from the hand changes the game value. This is a far stronger notion of "well-balanced deck" than placement frequency in self-play, and it is unavailable to Axis 2 at any sample size. |
| **H6** | sign only | solve once per perturbed deck and compare the **curves**, not just whether the sign held. A design whose advantage curve keeps its shape under perturbation is robust in a way a preserved sign does not show. |
| **S3 ↔ S5** | — | on positions where the mirror *is* a valid game symmetry, the fraction of moves whose mirror image is equally optimal. That is a direct measurement of how much strategic content `P3-y`'s chirality actually buys — the empirical answer to the redesign question S3 argues about analytically. |

The last row is a genuine experiment and should be registered in
[`experiments/registry.md`](experiments/registry.md) before Phase 5 rather than
invented once the data exists.

**One consequence for [research.md](docs/research.md).** If different hypotheses
get different *kinds* of answer — exact value, statistical estimate with a CI,
structural argument — then the Verdicts table needs an **evidence class** column,
otherwise a reader cannot tell an enumerated fact from a 20-seed win rate. That
is precisely the distinction your R&N *Lessons Learned* identified as essential
("exact search supports claims about game-theoretic value; learned agents support
claims about playing strength"), and the table as it stands erases it. Also note
the table has rows H1–H5 only — **H6 has no row**, which should be fixed at the
lock whether or not H6 is kept.

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

After reading Schaeffer alongside the methodological principle established in ADR-004, I realized that the notion of "independence" between the two axes needs to be stated more precisely. The real distinction is not whether Axis 2 influences Axis 1, but *how* it does.

There is a fundamental difference between using a learned policy to prioritize work and using it to justify conclusions. If the policy only influences move ordering, task scheduling, or the order in which states are explored, the exact algorithm still performs the same proof and eventually reaches the same result. Correctness is unchanged; only computational efficiency is affected. In contrast, if learned values influence the proof itself—by replacing exact evaluations, pruning branches without proof, or terminating the search early—the correctness of the exact method becomes dependent on an approximate one. At that point, Axis 1 ceases to be an independent source of evidence.

This distinction also changed how I interpret H3. The value of cross-axis validation is not merely that two different algorithms agree, but that they agree despite relying on fundamentally different sources of evidence. If the exact solver has been optimized using information derived from the learner, agreement becomes less informative because the two methods are no longer entirely independent. The risk is therefore not incorrectness, but weaker experimental evidence.

For FLIPHEX, however, this concern is largely theoretical for the 4×4 variant. Since the solver performs a complete state-space enumeration, ordering has essentially no impact on the final result. Nevertheless, I believe ADR-004 should preserve the stricter methodological rule because it generalizes naturally to larger variants and makes the experimental design easier to defend. Axis 2 may accelerate the exact solver by influencing the order of computation, but it should never contribute values, proof obligations, or termination criteria. Any exact result used to validate the learner should remain reproducible using only Axis-1-internal heuristics.

More broadly, this discussion reinforced a principle that extends beyond FLIPHEX. Independent methods are valuable not because they avoid sharing ideas, but because they fail for different reasons. Preserving that difference makes agreement between them substantially stronger evidence than agreement between two systems built upon the same assumptions.

**Refined write-up.**

The ordering-versus-values distinction is the right cut and the closing line —
independent methods matter because they *fail differently*, not because they
share nothing — is the sentence adr-004 should quote. Two refinements, one of
which changes the rule you would adopt.

**(b) "Independence" is the wrong word, and naming the right one tells you when
the rule actually matters.** Correctness is untouched: alpha-beta returns the
same value under any ordering, and retrograde enumeration has no ordering to
corrupt. What is damaged is not independence of *methods* but independence of
**error**. And the concrete failure mode is narrower than "weaker evidence": a
solver whose search order is seeded by the learner finishes *fastest exactly on
the lines the learner already plays well*. If the Axis-1 run then stops on a
budget — a compute cap, a partial endgame database, a depth limit — the positions
that got resolved are a biased sample, over-representing precisely the region
where agreement was structurally guaranteed. The risk is **selection bias**, and
it exists **only when the Axis-1 run is incomplete**. A run that terminates by
exhaustion cannot be biased by its own order, because order does not survive into
the output.

That is a useful sharpening, because it means the blanket rule is stronger than
necessary and the conditional rule is exactly as strong as it needs to be.

**(c) The implementable version.** Three clauses, and the implementation is two
metadata fields plus a filter:

> **R1.** Any Axis-1 result cited as ground truth for H1, H2, or H3 must come
> from a run that terminated by **exhaustion**, not by a budget. Exhausted runs
> are order-invariant, so Axis-2 seeding of their order is harmless *by
> construction* and needs no prohibition.
>
> **R2.** Any Axis-1 run that terminates on a budget — the depth-limited 5×5
> agent, a partial endgame database, a capped proof — must use Axis-1-internal
> ordering only (iterative deepening, TT move, killer/history), and carries that
> restriction as a recorded property of the artefact.
>
> **R3.** Every Axis-1 artefact records `ordering: internal | az-seeded` and
> `termination: exhausted | budget`. H3's comparison set is defined as the
> artefacts satisfying R1, and that filter is applied *before* any comparison is
> computed, not after seeing the results.

R3 is what makes R1 and R2 auditable rather than aspirational: without the
recorded fields, "we did not seed it" is a claim in prose, and the point of
pre-registration is that it should be a claim in the artefact.

**(d) The cost — and one correction.** For 4×4, zero: enumeration has no ordering
degrees of freedom, so the rule is **vacuous today**, which is the best possible
time to adopt it (no result is affected, no habit has formed). But the blanket
version the take endorses — "Axis 2 may influence order but never values" applied
to *all* Axis-1 work — does cost something real: it would forbid the depth-limited
5×5 alpha-beta agent from using a learned policy for move ordering, where
[R&N §6.2.4](notes/russell-norvig-aima-ch6-adversarial-search.md) says almost all
of the speed lives. R2 permits it, because that agent is a **player, not a
proof** — it is never cited as ground truth, so nothing it produces enters H3.
Scoping the rule to proof-producing runs rather than to Axis 1 as a whole is the
one change I would make to the take's recommendation.

**Cross-ref, read backwards.** The same rule forbids the mirror-image
contamination: Axis 1's solved values may not be used as Axis 2's checkpoint
selection criterion (S2). The general form is one sentence, and it is what
adr-004 should carry: *neither axis may be used to select or terminate the other
along the dimension on which they are later compared.*
