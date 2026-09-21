# FLIPHEX: from a game I designed to a game I could not completely solve

In 2017, I helped design FLIPHEX as part of MAP 2001, a course at IME-USP and FAU-USP called Matemática, Arquitetura e Design. The game was built as a physical object: a laser-cut wooden board, 25 hexagonal cells, and a set of two-sided coloured tiles. Eight years later, I came back to it for a very different reason. I was studying reinforcement learning and wanted to use FLIPHEX as a small game-playing problem, with the initial goal of training an agent to play it from scratch.

That was the original plan. It did not survive contact with the game. As I read about game-playing systems and the distinction between weakly and strongly solved games, I started asking questions that were more fundamental than whether I could train a good player. Does the first player have an advantage? Was the original deck of pieces a sensible design choice? Could the game be weakly solved? Could it be strongly solved? How large is the full game compared with games that have already been solved? Those questions changed the project from an attempt to build a reinforcement-learning player into an investigation of the game itself. The first thing I had to do was determine exactly what game I was actually solving.


## 1. The game, and where it came from

FLIPHEX was designed in 2017 by students from IME-USP and FAU-USP as part of MAP 2001, Matemática, Arquitetura e Design. The physical game is a laser-cut wooden board with 25 hexagonal cells and a set of two-sided tiles. One face of a tile is purple and the other is green. The board is small enough to fit comfortably on a table, but the rules produce a surprisingly large combinatorial game.

Each player has twelve tiles. The tiles contain between one and six arrows pointing outward from the hexagon. Player 1 also has the joker, an arrowless tile, so the two hands plus the joker account for all 25 cells:

12 + 12 + 1 = 25.

On a turn, a player places one of the tiles in any empty cell and may choose its rotation. Every arrow pointing toward an occupied neighbouring cell flips that neighbour to the player's colour. Flips do not chain. Once the move has resolved, the newly flipped pieces do not immediately trigger further flips.

There are 25 cells, so the board has an odd number of positions. Because of the way the hands are constructed, both players exhaust their tiles exactly, with Player 1 receiving the additional move supplied by the joker. The canonical game therefore has no draws.

The physical object matters to this project. It was not a game invented to provide a convenient benchmark for an algorithm. It was designed as part of a course that brought mathematics, architecture, and design into the same room. The board, the pieces, their visual identity, and their physical constraints were part of the original problem.

I ignored most of that when I came back. Formalising the game is where it caught up with me.

## 2. Formalising a game that was never written down

The first problem was that FLIPHEX had never been written down as a formal computational specification. The 2017 poster contains both photographs and prose rules, but the two do not always agree. I therefore established an explicit precedence order before implementing the game: photographs first, then the author's decisions, then the poster prose. Divergences were recorded rather than silently resolved.

That decision mattered immediately. The project plan I had written before any of this ran described a "5-row zigzag", while the photographs show flat-top hexagons arranged in five columns. The board still contains 25 cells, but the geometry changes the direction indexing and therefore the implementation of moves. Reading the prose alone would have produced an engine that looked plausible and passed every test written against its own assumptions, while representing the wrong board.

There was also an uncomfortable detail in this process: I was both one of the original sources and the person deciding how those sources should be ranked. In effect, I had to decide which version of my own past decisions should count as canonical. I deliberately ranked the physical evidence above my recollection and the old prose.

The deck produced the first result that went beyond formalisation.

I initially thought the twelve pieces represented a selection of arrow patterns made by the original designers. Counting the possible patterns showed something different. Because the tiles have two faces, their arrow patterns are equivalence classes under both rotation and reflection. The numbers of distinct classes with one through six arrows are exactly 1, 3, 3, 3, 1, and 1.

Those classes add up to twelve.

The original deck is therefore not a selection from a larger set of possible pieces. It is the complete enumeration of the physically distinct arrow patterns. The reflection is essential: turning a tile over changes its colour and mirrors its arrows. If I considered rotations but not reflections, there would be thirteen classes and the original deck would require an arbitrary omission.

The deck that had looked like an empirical design choice had turned out to be a combinatorial consequence of the physical construction.

The next simplification came from the move rules. Placed tiles are inert. A tile's arrows act when the tile is played, but flips do not chain, so the orientation of a placed tile has no effect on any later move. The future state therefore does not need to store the orientation of already placed pieces.

That changes the size of the state representation substantially. A representation that retains orientation gives a bound of 1.389 × 10³⁷ configurations. Removing the irrelevant orientation information reduces that to 4.887 × 10¹⁷, a reduction of about 19.5 orders of magnitude.

This is more than a storage optimisation. It changes the nature of the search. With orientation retained, transpositions between strategically identical states would be almost impossible to exploit. Once orientation is removed, transposition tables become essential rather than decorative.

The formalisation also exposed one of my own mistakes. I initially recorded that the board had no symmetry. It does have a mirror symmetry across the central column, mapping A to E, B to D, and the corresponding diagonal directions. It does not have 180-degree rotational symmetry.

The correction did not produce the strategy-stealing argument I had originally hoped for. The chiral P3-y tile breaks the mirror symmetry while it remains in hand, so the symmetry is only partial and becomes relevant only in restricted endgames. It also preserves the mover, so it does not establish a first-player strategy-stealing argument.

That sequence was a useful introduction to the rest of the project. Before asking whether a game can be solved or learned, I had to make sure I knew which states were actually different, which rules were authoritative, and which apparent degrees of freedom were real.

## 3. The research question, and why it has three axes

By the time the formalisation was stable, the original question had changed.

The project was no longer simply "Can I train an agent to play FLIPHEX?"

The central question became:

> Does the first player have a provable advantage, does the joker break game balance, and does the game admit an efficient learned policy that approaches optimal play?

Those questions require different instruments.

The first axis is the exact solver. It asks for the truth on boards small enough to exhaust. If every relevant state can be evaluated, the result does not depend on the quality of a learned policy.

The second axis is the AlphaZero-style learner. It asks whether a system can discover strong play without being given a database of optimal moves.

The third axis is complexity analysis. It asks where the boundary lies between these two approaches. A game can be small enough to learn but too large to solve exhaustively. Conversely, a position can be easy to prove by search even when enumerating the entire state space would be impractical.

This distinction became increasingly important as I read about solved games.

The terms weakly solved and strongly solved are not interchangeable.

A weak solution establishes the result of the initial position under optimal play. A strong solution determines the value of every reachable position. A system that plays well against other players is not automatically either of these.

For FLIPHEX, this distinction became central because the full 5×5 board is much larger than the reduced boards that can be exhaustively solved.

I also decided to pre-register the hypotheses before running the main experiments.

Six hypotheses were locked at tag `v0.3-hypotheses` on August 5, 2026. After that point, the research document could gain verdicts but not be rewritten to make a result fit the original expectation.

That decision had a practical cost.

Some of the assumptions I had frozen turned out to be wrong. A `6^25` factor was wrong. One complexity estimate was wrong by a factor of 236. One experiment was registered and later withdrawn before being run. Another hypothesis turned out to rely on a perturbation set that could not actually falsify it.

Without the pre-registration, these problems would have been easy to clean up retrospectively.

With it, they remained visible.

That was one of the most valuable methodological consequences of the project. The point of freezing the hypotheses was not to make the experiment look more rigorous after the fact. It was to force the project to preserve the distinction between what I believed before running the experiment and what I learned afterward.

## 4. Axis 1: how much of FLIPHEX can be solved exactly

Before running the solver, I had to decide what "solved" meant.

For finite deterministic games, there is a useful distinction between ultra-weak, weak, and strong solutions.

A weak solution establishes the result of the initial position under perfect play. A strong solution determines the value of every reachable position. In practical terms, an exhaustive forward alpha-beta search from the opening can establish a weak solution, while a complete retrograde sweep can establish a strong solution.

The difference matters because a strong solver can answer questions about positions that were not part of the opening sequence.

Two reduced boards were solved completely.

| Board | Cells | Configurations | Result  |
| ----- | ----: | -------------: | ------- |
| 3×3   |     9 |        711,963 | P1 wins |
| 5×3   |    15 | 17,506,580,337 | P1 wins |

All four solver arms terminated exhaustively.

The 3×3 board was solved twice using independent approaches: forward alpha-beta and retrograde analysis. The retrograde sweep assigns a value to all 711,963 configurations. The forward search independently proved 604,347 of them, or 84.9%, and on every one of those the two methods returned the same value. There were no disagreements.

The coverage is not 100% because forward alpha-beta deliberately prunes: a subtree that cannot change the root value is never visited, which is the entire point of the algorithm. So 84.9% measures how much of the state space received a second, independent witness. It is not a rate of agreement between the two witnesses, which was total. The retrograde solution supplies the complete value assignment, while the forward method supplies an independent route through the state space.

The agreement is important because an exact solver has a peculiar verification problem. It cannot simply be tested against itself. If the program says that a position is winning, running the same program again with the same assumptions does not independently establish that fact.

Independent enumeration, per-layer counts, checksums, and a second implementation are therefore more valuable than ordinary unit tests.

The reduced boards are also not arbitrary toy boards. They preserve an important structural property of the shipped game.

Every legal board in the family has an odd number of cells. Player 1 has the extra tile, so both hands exhaust exactly and Player 1 moves last. This means that the reduced boards preserve the same basic move-count structure as the 5×5 board.

The cost of that choice is important.

The property that most plausibly contributes to first-player advantage is held constant by construction. Because the reduced boards all preserve the odd-cell and extra-tile structure, solving them does not tell us how the game behaves when that structure is varied.

That limitation returns later in the analysis of the hypotheses.

The 4×4 board was not used as a reduced board because it violates the same structure. With an even number of cells, draws become possible, and the canonical rules do not define a tie-break mechanism. Including it would therefore introduce a different game rather than simply a smaller version of FLIPHEX.

### The database that was not built

The original project plan included the possibility of building an endgame database for the 5×5 board.

Before doing that, I asked a simpler question: is storing the positions actually cheaper than searching them?

The answer was not what the plan assumed.

For a representative set of 5×5 positions, the median number of nodes needed to prove a position increased sharply with the search parameter: from 480 at k = 5 to 806,474 at k = 8.

A database of approximately 1.2 × 10¹⁵ positions would require around 150 TB even at one bit per position.

That comparison initially suggested that the question was simply a choice between search and storage. A more careful analysis showed that there are actually two boundaries.

One is whether the positions are enumerable and storable.

The other is whether an individual position is solvable by search.

Between those boundaries, retrograde analysis can sometimes be preferable. For the 5×5 board, however, the two cuts do not meet. Across k = 3 through 8, the relevant positions are not enumerable at database scale, while the individual positions can still be proved quickly enough by search.

The interval in which a database would be the natural solution is therefore empty.

This was another case where the plan contained an assumption that looked reasonable before measurement and became unnecessary after it.

### A solver is only as useful as its verification

The 5×3 sweep provides a useful example.

An early implementation projected approximately 108 days of computation. The final implementation projected approximately 13 hours without changing the algorithm or the resulting values.

The improvement came from removing unnecessary work. In one particularly important case, a Zobrist hash was being computed seventeen times per configuration even though the index itself was already the key for the sweep. There was no lookup operation that required the hash.

The output was byte-identical across the implementations and was checked by checksum under two implementations and two interpreters.

The lesson is broader than the speedup itself.

Exact computation is not only about finding an algorithm that eventually terminates. It is about identifying which work carries information and which work exists because an implementation convention has been mistaken for a mathematical necessity.

For that reason, the solver was accompanied by multiple verification levels.

V1, for example, compares exact per-layer counts against an independent enumerator. It is not a tolerance-based check. Other verification levels cover different aspects of the computation, and the coverage itself is recorded. On the 5×3 board, some of the stronger search evidence does not cover the earliest layers, while another verification level begins only at t ≥ 2.

Those gaps remain in the research record.

This is important because a solver is precisely the program that cannot be tested simply by comparing its answer with itself. If there is no independent source of truth, "the program agrees with the program" is not verification.

The reduced-board results are therefore strong because they are accompanied by independent counts, alternative methods, and explicit coverage statements.

The full 5×5 game does not have the same status.

It remains unsolved.

## 5. Axis 2: learning FLIPHEX from scratch

The second axis returned to the question that started the project: could an AlphaZero-style system learn to play FLIPHEX?

The architecture itself contained an assumption that later proved consequential.

The initial policy head was factored into cell, tile, and rotation components rather than representing all legal action combinations with a single flat output.

The motivation was parameter efficiency. A flat head would require a much larger output space, while the factored representation could reuse parameters.

But the factorisation also assumes a form of conditional independence that is not actually true.

The best rotation of a tile depends on the cell in which the tile is placed. The best tile depends on the position. These choices interact.

I nevertheless used the factorised head because Monte Carlo Tree Search was expected to compensate for an imperfect policy prior. The risk was recorded explicitly, along with fallback architectures and a requirement to test the assumption.

The risk materialised.

On the 5×3 board, the flat policy head performed better than the factored one.

After 400 PUCT simulations, top-1 agreement with optimal play was 66.8% for the factored head and 73.7% for the flat head, a difference of about seven percentage points.

Supervised agreement showed the same direction: approximately 58.6–60.8% for the factored version against 65.6–68.6% for the flat version.

The five seeds also separated cleanly. Every factored seed was below every flat seed.

The important finding was not simply that one architecture "won".

The original mitigation assumed that MCTS would correct a poor prior. At the tested search budget, it was close to inert relative to the architectural deficit. Search did not recover the information that the policy representation had discarded.

The training losses pointed in the same direction. The final policy loss was 2.616 for the factored head and 2.375 for the flat head. The factored representation was therefore not merely failing because training had been stopped too early.

A fallback architecture then improved the situation, although the margin by which it cleared its tolerance was only 0.25 points. That threshold had itself changed role between experiments without sufficient rejustification, so the result should not be presented as a comfortable architectural decision.

A subsequent change replaced twenty-five unshared per-cell rotation maps, containing 43,290 parameters, with a 1×1 convolution using 198 parameters. The conditioned head fell from 467,839 to 347,887 parameters on the shipped board.

In other words, the more expressive representation became the smaller one.

The reason was parameter sharing. The convolution could express the same conditioning across all cells rather than maintaining separate maps.

But there was a methodological limitation that matters more than the parameter count.

These architecture decisions were made using 5×3 solver ground truth. They were not measured on the 5×5 board before the final training run.

That distinction matters whenever a reduced board is used as a proxy for the real problem.

### The 135-hour experiment

The final self-play training experiment used five seeds and thirty generations, for a total of 135 hours.

Four seeds cleared the pre-registered prior-free UCT floor.

One did not.

Seed 4 reached 56.0%, with a confidence interval of 49.1–62.7%, and fell two games short of the registered threshold.

The failing seed was not averaged away.

The between-seed standard deviation was 7.3%, compared with 3.4% expected from sampling alone, and a homogeneity test rejected the assumption of a single underlying rate.

The training therefore exhibited substantial seed dependence.

That is not enough to explain why the learner behaved as it did. Nothing in this experiment independently varied architecture, training budget, or search budget in a way that could identify a causal explanation for the failures.

The correct conclusion is narrower.

The training produced agents that learned meaningful play. Four of five seeds exceeded the chosen baseline. The learner also substantially outperformed a random mover.

But the experiment did not establish that the system had learned optimal play.

That question was tested separately against positions whose values were already known from the exact solver.

### Testing learned play against solved positions

The final test set contained 352 exactly solved 5×5 endgame positions at k ≤ 8.

The five trained champions scored between 74.4% and 77.0%.

The pre-registered threshold was 90%.

Even the upper confidence limit of the best seed reached only 81.1%.

The result therefore fell well short of the criterion that had been established before the experiment.

The context matters. A random mover scored 21.9%, while the raw policy head scored 53.5%. The trained system was therefore not behaving randomly.

But "better than random" is not the same statement as "optimal".

The experiment also exposed a measurement problem that would have invalidated an earlier version of the metric.

The first implementation counted every move from a lost position as a successful agreement if it preserved the eventual outcome. From a position that is already lost, every move can preserve the fact that the position is lost. The metric could therefore score moves as correct without distinguishing optimal from inferior choices.

The measure was corrected to restrict the evaluation to positions where the current player had a winning move.

That correction illustrates a recurring lesson in the project: a numerical metric is only useful if the quantity being measured can actually vary under the strategies being compared.

The final result does not identify why the learner stopped at 74–77%.

It does not establish that the architecture was insufficient. It does not establish that the search budget was insufficient. It does not establish that the training duration was insufficient.

It establishes only that the tested training configuration did not meet the pre-registered agreement threshold.

That distinction is important.

The project also produced a less formal result that I found personally useful: the trained agent beat me.

I do not treat that as evidence about optimality. It may simply mean that the agent learned strategies that I do not play well against.

But it is a useful reminder that human intuition and computational optimality are different things. I can lose to a policy without knowing whether that policy is close to optimal.

## 6. Where FLIPHEX sits among known games

Once exact solving and learning were separated, the next question was scale.

How large is FLIPHEX?

The reachable state space of the 5×5 game is approximately:

4.886 × 10¹⁷ states.

The number of distinct complete games is approximately:

4.229 × 10⁵⁸.

These are exact counts under the formalised rules, rather than rough estimates based on an average branching factor.

The game tree has an exact depth of 25. At ply 24, the final tile's rotation can still determine the final colour count, so a depth-24 full-width search is insufficient to determine the game value.

Every combination of empty cell, tile in hand, and distinct legal rotation is available as a move. There are no captures, passes, or forbidden placements that would complicate that count.

The resulting game count can therefore be derived from the independent permutations involved in placing cells, tiles, and rotations.

The count was checked against the legal-move generator at full depth on the 5×1 board and to three plies on both reduced boards and both arms. Sixteen cases were checked and all sixteen matched exactly.

The comparison with other games produced two useful corrections to commonly repeated figures.

A widely repeated estimate for the 6×6 state space of Reversi is approximately 10²⁰. But a board with 36 cells and three possible cell states has an absolute upper bound of 3³⁶, which is approximately 1.501 × 10¹⁷.

The 10²⁰ figure therefore cannot represent the complete state space.

No primary source for that figure was found.

This mattered because one of the original FLIPHEX hypotheses used "complexity comparable to small Reversi" as part of its framing. The comparison was therefore anchored to a number that could not actually describe the claimed state space.

Connect Four provided another example.

A commonly cited figure of approximately 10¹⁴ differs from Tromp's exact enumeration of 4,531,985,219,092 by a factor of about 22.

The lesson was not that one should never use estimates. Estimates are useful when clearly identified as estimates.

The problem arises when estimates are copied into comparison tables and gradually become treated as exact values.

I therefore changed the comparison infrastructure to grade each figure as exact, verified, reported, refuted, or absent. A citation is treated as part of the data rather than as decoration.

This is also why some cells in the comparison remain empty.

A canonical cross-game table from van den Herik et al. (2002), for example, was not reproduced when secondary reproductions disagreed by one or two orders of magnitude on several rows. A shorter table with only claims that can be defended is preferable to a complete-looking table containing borrowed numbers whose provenance is unclear.

The comparison with Othello is particularly useful.

Othello 8×8 has a game tree of approximately 10^58.00 and was weakly solved in 2023.

FLIPHEX has a game tree of 10^58.63, about four times larger.

That is not an order-of-magnitude difference.

This creates a more nuanced picture than the original hypothesis suggested. FLIPHEX is not simply "far beyond solved games". It sits just beyond a frontier that another game crossed only a few years earlier.

At the same time, the comparison should not be interpreted as evidence that FLIPHEX will necessarily be solved next.

Different games distribute their complexity differently. A state-space count and a game-tree count describe size, not the structure of the search problem.

One useful structural observation came from the layer profiles.

The number of states forms a hump on all three analysed boards: it increases to an interior maximum and then decreases. The peak occurs at different plies depending on board size.

The branching factor behaves differently. It decreases strictly from the opening.

These two facts are easy to conflate if one simply says that "the game gets more complex in the middlegame". One measure rises and falls, while the other decreases from the beginning.

The game therefore does not have a single scalar notion of complexity.

That was another reason the complexity axis became necessary.

## 7. The six hypotheses and what they actually established

The six pre-registered hypotheses did not produce six clean yes-or-no answers.

That is itself one of the main results of the project.

### H1: the first player has an advantage

The hypothesis is supported where perfect computation is available, but it is not decidable for the full 5×5 board.

All four exhaustive solves returned Player 1 as the winner.

That includes both the forward and retrograde approaches on the reduced boards.

The original hypothesis also included a self-play component intended to measure a first-player win rate on the full board. That experiment was not run as originally written.

It was registered and then withdrawn before execution because prior-free UCT with the selected simulation budget visited only 10–18 of the 325 root children, in board-cell order.

A replacement experiment produced a 54.2% first-player win rate over 5,000 games, with a confidence interval of 52.9–55.6%. The play was heuristic for approximately seventeen plies and exact for the last eight, with a proved-rate of 32.0%.

That result corroborates a first-player advantage under the tested policy.

It does not establish a perfect-play advantage.

The distinction matters because a heuristic game-playing policy can have systematic biases that have nothing to do with the minimax value of the game.

The strongest conclusion remains the exact one: Player 1 wins the reduced boards that were exhaustively solved. The corresponding statement for the 5×5 board remains open.

### H2: removing the joker does not change who wins

The two reduced boards again return Player 1.

But the 5×5 version of the hypothesis cannot be tested because the proposed variant cannot be constructed under the capacity constraints.

The joker is the only tile that gives Player 1 the additional move. There is no next archetype available to replace it while preserving the same twelve-tile capacity.

The result is therefore not a statement that the joker does or does not affect the full game.

It is a statement about what can and cannot be varied within the formalised design space.

### H3: self-play converges and agrees with the solver

This hypothesis was rejected on both clauses.

The first clause failed because of the seed variation. The five training seeds did not behave as if they were samples from a single stable underlying performance rate.

The second clause failed because the trained systems reached only 74.4–77.0% agreement on the solved-position test, against a threshold of 90%.

The reduced-board networks cannot rescue the hypothesis. The available reduced-board networks were supervised on solver labels, which is a different training procedure from the self-play system being evaluated.

The fact that a trained network cannot be directly evaluated on the reduced boards without changing its input/output geometry is itself a reminder that the architecture was designed around the 5×5 board.

The hypothesis therefore failed for reasons that are independently visible in both parts of the claim.

### H4: where FLIPHEX sits in complexity

One of the locked estimates in H4 was wrong by a factor of 236.

The originally recorded figure was approximately 10⁶¹, while the exact count is 10^58.63.

The mistake was not a failure of arithmetic in the final exact count. The two locked estimates were internally inconsistent.

Starting from the minimal-tree relation,

10^30.5 = b^13,

gives a branching factor of approximately 222. Extending that value to depth 25 gives 10^58.65, which agrees with the exact game-tree count to two decimal places.

The surviving derivation was therefore essentially correct.

The problem was that the other locked number did not follow from the same assumptions.

This is a useful example of why pre-registration is not the same as correctness.

Freezing a number before the result protects the experiment against hindsight, but it does not make the number true.

A pre-registered mistake remains a mistake.

The same section also exposed a conceptual error in the original claim that the full game was beyond routes that had already produced weak solutions for other games.

Against checkers, that statement may have been reasonable.

Against games actually weakly solved, such as Othello, the picture is different. Othello's game tree is approximately 10^58.00, while FLIPHEX is 10^58.63.

The full board is therefore somewhat larger, not categorically beyond the frontier.

### H5: no archetype dominates

This hypothesis was true by construction and therefore did not establish what it was intended to establish.

Every game uses every archetype exactly once for each player.

The per-archetype count vector is therefore fixed:

[2] × 12 + [1],

with the joker appearing only once because only Player 1 holds it.

Across the recorded games, there is consequently no variation in how often an archetype is played.

The experiment cannot distinguish a dominant piece from a weak piece by counting usage frequency because the rules already determine the frequency.

The correction went further.

Each player holds each archetype once. Therefore every archetype is played once by the winner and once by the loser in the relevant recorded games.

The joker is different because it belongs only to Player 1. Measuring whether the joker was played by the winner is effectively measuring whether Player 1 won.

The observed 2,712 / 2,288 split therefore reproduces the first-player split rather than isolating a causal contribution from the joker.

This was perhaps the clearest example of an experiment that produced a perfectly stable number that answered the wrong question.

The result is not evidence that the deck is balanced.

It is evidence that the rules force the measurement.

### H6: robust to bounded design perturbation

This hypothesis was supported across every perturbation that actually existed in the experiment.

But the perturbation set could not falsify the hypothesis.

Every reduced board returned Player 1.

On one of the 5×3 variants, all 12,841,920 configurations at t = 4 were Player 1 wins, and all 713,440 configurations at t = 3 were Player 2 losses.

That looks like a strong structural signal.

The problem is that the experimental design did not vary the structural feature most relevant to the hypothesis.

The reduced-board construction requires an odd number of cells and preserves Player 1's extra tile. The feature that could plausibly generate the first-player advantage is therefore held constant.

The named deck perturbation, removing the chiral P3-y tile, was also forbidden by an earlier design restriction.

The only remaining deck perturbation available to the engine was the arm swap, which overlaps with H2.

A hypothesis cannot be meaningfully falsified by a perturbation set that does not contain a configuration capable of changing the relevant cause.

The experiment therefore supports the observed result within its restricted domain, but it does not establish robustness in the broader sense suggested by the hypothesis.

### What the six hypotheses taught me

Four of the six verdicts depended on something other than the measurement itself.

One experiment was withdrawn before execution.

One variant could not be built.

One hypothesis measured a quantity forced by the rules.

One hypothesis relied on a perturbation set that could not falsify it.

Pre-registration did not prevent these problems.

It made them visible and dated.

That distinction matters.

The most useful outcome of pre-registration in this project was not that it guaranteed clean experiments. It made it difficult to rewrite the history of a dirty one.

A project can fail because its hypothesis is false. It can also fail because its denominator is vacuous, its variant is unbuildable, its universal is untestable, or its measurement does not vary under the allowed strategies.

Those are different failure modes.

FLIPHEX encountered several of them.

## 8. What exists now, and what I would do differently

The project now has four interfaces around the same game engine: a command-line interface, a pygame window, a browser implementation, and a viewer for stepping back and forth through a finished game.

The browser version runs the real Python engine under Pyodide rather than reimplementing the rules in JavaScript. This matters because the game logic should have one source of truth. You can play it at [brunoramosmartins.github.io/fliphex](https://brunoramosmartins.github.io/fliphex/).

Two of those interfaces — the window and the command line — can seat the exact solver on the completed 5×3 sweep, and then every move is a table lookup instead of a search. The proved rate is 1.0 from the opening. That is a strong solution made playable.

Perfect play has a computational cost.

The solver can require around 3.0 GB of resident memory, and the worst move can take approximately 4.9 seconds because one of the middle layers alone reaches about 1.2 GB.

The browser cannot do this, and the reason is not a limitation of the browser. The sweep is 4.1 GB on disk and was never distributed, so no page can read it. What the published page does offer is the 3×3, where the solver needs no database at all: the board is small enough to prove outright, so it plays perfectly from the first move and takes about eight seconds to answer the opening.

The practical bottleneck is therefore not only the number of operations. It is memory bandwidth and the amount of information that must remain available while the exact computation runs.

The large trained model and database are not included in a normal repository clone. The interface detects their absence and falls back to search rather than silently pretending that the exact artefact exists.

That is important for reproducibility.

The browser game is therefore not simply a demonstration layer placed on top of a research project. It is also a way of exposing the distinction between what has actually been solved and what has merely been learned.

### What I would do differently

The first change would be simple:

**Check that the quantity varies before registering the experiment.**

H5 is the clearest example. But the same defect appeared elsewhere: orphan counts and an early version of the solved-position metric also contained quantities that the rules or the evaluation setup had already fixed.

A cheap pre-experiment check would have been to ask:

> What would this measurement look like under a genuinely different strategy?

If the answer is "exactly the same", the measurement is not measuring strategy.

The second lesson is that a comment is not a constraint.

The project had duplicated visual conventions in different interfaces. Comments claimed that the implementations agreed, but nothing automatically checked that agreement.

One implementation had an opacity mismatch: pygame ignored the alpha channel and rendered arrows at full opacity while CSS honoured the intended value.

The fix is not a better comment.

It is a single source of truth, generated representations where possible, and CI that fails when the generated artefacts drift.

The third lesson is that writing a restriction and implementing a restriction are different things.

A statement in an ADR or research document can feel like an implementation constraint even when the program does nothing to enforce it.

This happened repeatedly during the later phases.

The fourth lesson is about thresholds.

A threshold should be derived when it is introduced, not justified later when the result is already known.

One experiment cleared a tolerance by only 0.25 points, and the same constant had changed from a detection threshold to an adoption tolerance without being rejustified. Another threshold was used without a sufficiently explicit derivation.

The number may still be usable.

The problem is that its interpretation becomes ambiguous after the fact.

The fifth lesson is that the plan itself is a hypothesis.

The plan I started from contained assumptions such as `6^25`, "8 archetypes", "5-row zigzag", an average branching factor, a complexity estimate near 10⁶¹, and the expectation that a large endgame database should be built.

Several of these were wrong.

Others were technically possible but unnecessary.

Almost all were caught by computing rather than by reading.

If I were starting the project again, I would therefore spend more time turning the plan's assumptions into small executable checks before committing to the corresponding experiment.

That is a very different workflow from writing a long research plan and then implementing it.

## Closing

FLIPHEX was designed in 2017 to be played.

I returned to it in 2026 intending to teach a machine to play it.

The machine did learn to play. It did not establish optimal play.

The exact solver did more than I initially expected on the reduced boards and less than I wanted on the full board. It established strong solutions for 3×3 and 5×3, but the 5×5 remains unsolved.

The complexity analysis produced exact counts, corrected several external figures, and placed FLIPHEX closer to known solved games than my original assumptions suggested.

The investigation of the deck showed that what looked like an empirical design choice was actually a complete enumeration.

The investigation of balance showed that one of my hypotheses was not an empirical question at all. The rules had already fixed the quantity I wanted to measure.

The project therefore ended with fewer definitive answers about the 5×5 game than I initially hoped for.

It also ended with a much clearer understanding of what those unanswered questions actually are.

That distinction is important.

A computational project can produce a number without producing an answer. It can produce a trained model without producing a solution. It can produce a statistically stable measurement without measuring the quantity that motivated the experiment.

The useful part is learning to distinguish these cases.

That is why the six hypotheses were frozen before the experiments. The pre-registration did not make the study immune to bad assumptions. It made the assumptions visible.

The project contains two rejected hypotheses, one hypothesis that was true by construction, a locked figure that was wrong by a factor of 236, a 135-hour training run that came fourteen percentage points short of its target, and an endgame database that was never built because the computation showed that searching was cheaper.

Those are not footnotes to the result.

They are the result.

FLIPHEX began as a physical game designed in a mathematics, architecture, and design course. Eight years later, turning it into a computational object exposed questions about symmetry, enumeration, exact search, complexity, reinforcement learning, and experimental design that were not visible on the wooden board.

The game was designed to be played.

The project became an attempt to understand what it would take to prove something about it.

For the full 5×5 game, that proof is still unfinished.

And that is a more precise result than pretending otherwise.
