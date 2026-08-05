# Reading companion — Silver et al. 2018, AlphaZero

**Citation.** Silver, D., Hubert, T., Schrittwieser, J., Antonoglou, I., Lai, M.,
Guez, A., et al. (2018). *A general reinforcement learning algorithm that masters
chess, shogi, and Go through self-play.* **Science** 362(6419), 1140–1144.
Read from the arXiv preprint 1712.01815 (`refs/silver-2018-alphazero.pdf`).

**Why this source, and where it sits.** Read **after**
[Silver 2017 (AlphaGo Zero)](notes/silver-2017-alphago-zero.md) — this paper is
essentially a *diff* against it, and assumes its notation. Its importance for
FLIPHEX is specific and large: AlphaZero generalises the AGZ recipe to **chess
and shogi**, two games that — like FLIPHEX and unlike Go — have **no exploitable
board symmetry**. So where AGZ treated symmetry as a free gift we cannot inherit,
**AlphaZero is the closer template for FLIPHEX**: it shows the recipe working in
the no-symmetry regime, with a *structured* (factored-like) policy head. Focus
only on the deltas; do not re-derive what the AGZ note already covers.

**Cross-refs this reading feeds:**
- [adr-005](docs/adr/adr-005-alphazero-scope-and-network.md) — R5: chess/shogi
  use a **structured** action encoding (a plane-factored policy head), the
  closest empirical precedent for FLIPHEX's (cell × tile × rotation) factoring.
- [board-geometry.md](docs/board-geometry.md) — FLIPHEX's trivial symmetry group;
  AlphaZero drops symmetry augmentation entirely, matching our situation.
- [notes/phase2-synthesis.md](notes/phase2-synthesis.md) — resolves **S2**
  (evaluator gate removed) and feeds **S3/S4**.
- [exercises/ex04_alphazero_math.md](exercises/ex04_alphazero_math.md) — the
  outcome-with-draws value target and the noise-scaling rule.
- [notes/silver-2017-alphago-zero.md](notes/silver-2017-alphago-zero.md) — the
  baseline this paper is a diff against.

**Legend.** Prompts marked 🔄 need synthesis with another source — answer them in
[phase2-synthesis.md](notes/phase2-synthesis.md), not here.

**Reading material** (extracted via `paper-study`, gitignored under
`notes/sources/`): [manifest](sources/silver-2018-alphazero/manifest.json) ·
[§1 main text](sources/silver-2018-alphazero/sections/01-mastering-chess-and-shogi-by-self-play-with-a-ge.md)
+ [Nível-1 companion](sources/silver-2018-alphazero/study/01-main-text.md) ·
[§5 MCTS vs αβ](sources/silver-2018-alphazero/sections/05-mcts-and-alpha-beta-search.md) ·
[§6 Domain Knowledge](sources/silver-2018-alphazero/sections/06-domain-knowledge.md) ·
[§7 Representation](sources/silver-2018-alphazero/sections/07-representation.md)
+ [Nível-1 companion](sources/silver-2018-alphazero/study/07-representation.md) ·
[§8 Configuration](sources/silver-2018-alphazero/sections/08-configuration.md) ·
[§9 Evaluation](sources/silver-2018-alphazero/sections/09-evaluation.md).
Level-1 companions for other sections on request.

---

## §1 — The general algorithm and its deltas from AlphaGo Zero

### 1.1 — What generalises: one algorithm, three games
**Prompt.** What does AlphaZero claim to hold *fixed* across chess, shogi, and Go
(same network, same hyperparameters, same algorithm)? What is the single headline
result and its caveat (compute, opponent used, single vs multiple runs)? Predict
before reading: does the paper argue generality by *removing* Go-specific
machinery, or by adding chess-specific machinery?

**My take.**

Before reading, I expected AlphaZero to extend AlphaGo Zero by introducing chess- or shogi-specific components. Instead, the paper argues for generality by removing Go-specific assumptions while keeping the learning algorithm essentially unchanged.

Across chess, shogi, and Go, AlphaZero uses the same reinforcement learning framework, neural network architecture, Monte Carlo Tree Search procedure, and nearly identical training hyperparameters. The only game-dependent components are those that are unavoidable: the game rules, legal move generation, and the policy output representation required by each action space.

The headline result is that a single algorithm, trained exclusively through self-play, achieves superhuman performance in all three games without handcrafted evaluation functions, opening books, endgame tablebases, or other domain-specific heuristics. This provides strong evidence that the AlphaGo Zero recipe is not limited to Go.

However, the claim should be interpreted together with its practical caveats. The reported results rely on enormous computational resources, including thousands of TPUs for self-play and training, and the evaluation compares AlphaZero against the strongest available engines (Stockfish for chess, Elmo for shogi, and AlphaGo Zero for Go). Furthermore, the paper reports results from a single training run rather than multiple independent runs, so it does not assess training variance or reproducibility.

For FLIPHEX, the most important takeaway is that AlphaZero validates the self-play + MCTS recipe in games where board symmetries are not assumed by the learning algorithm. Whether FLIPHEX possesses exploitable symmetries remains an open design question, but AlphaZero demonstrates that the framework does not depend on symmetry augmentation to achieve strong performance.

**Refined write-up.**

Your prediction-then-correction is exactly the paper's structure: generality by
**subtraction**, not addition. One precision — "same hyperparameters" has a named
exception the paper itself carves out: the Dirichlet α is scaled per game (you
handle this in §4.1). And keep the compute figures straight: self-play used
~5,000 first-generation TPUs; the "4 TPUs" is only the final single-machine
evaluation. Your single-run caveat is the right one, and it is precisely what
your H3 protocol will fix.

### 1.2 — The concrete deltas (the S2 resolution) 🔄
**Prompt.** Enumerate exactly what AlphaZero changes versus AlphaGo Zero. Cover at
least: (a) game **outcome** now includes **draws** (chess/shogi) — how does the
value target change? (b) the **evaluator gate** — is it kept or dropped, and what
replaces it? (c) **symmetry augmentation** — kept or dropped, and why? For each,
state the FLIPHEX consequence. This is synthesis **S2** — put the cross-paper
reasoning there and summarise the verdict here.

**My take.**

AlphaZero is best understood as a minimal modification of AlphaGo Zero rather than a new algorithm. The self-play → MCTS → neural network training loop is preserved almost unchanged, while only a few assumptions tied specifically to Go are removed.

The first change is the value target. AlphaGo Zero only considered terminal outcomes of win or loss, whereas AlphaZero extends the target to naturally include draws, which are common in chess. Instead of a binary outcome, the value target becomes {-1, 0, +1}, allowing the network to learn that forcing a draw can be preferable to pursuing a losing continuation. For FLIPHEX, however, this modification is not directly applicable because the game always produces a winner. The binary {-1, +1} outcome used by AlphaGo Zero already matches FLIPHEX's termination rules.

The second—and arguably most consequential—change is the removal of the evaluator gate. AlphaGo Zero promoted a newly trained network only if it consistently defeated the current best network in a head-to-head evaluation. AlphaZero eliminates this promotion mechanism entirely and continuously trains from the latest network parameters. This simplifies the training pipeline while relying on gradient-based optimization to improve performance over time. For FLIPHEX, this appears to be the most directly transferable design decision, as maintaining an evaluation league would introduce considerable engineering complexity without clear empirical evidence that it improves learning.

The third change is the complete removal of symmetry augmentation. AlphaGo Zero exploited the rotational and reflectional symmetries of the Go board to increase the effective training data. Chess and shogi lack comparable exploitable symmetries because piece movement and game semantics depend on orientation, making these transformations invalid. Consequently, AlphaZero trains directly on the original game positions without symmetry-based data augmentation. Whether FLIPHEX admits exploitable board symmetries remains an open question. However, AlphaZero demonstrates that symmetry augmentation is not a prerequisite for successful learning, making it a robust baseline regardless of the outcome of that future analysis.

Taken together, these changes strengthen the paper's central claim. Rather than introducing domain-specific machinery for chess or shogi, AlphaZero systematically removes assumptions that were specific to Go. The result is not a fundamentally new algorithm, but a cleaner and more general reinforcement learning framework whose applicability depends less on the structural properties of a particular game.

**Refined write-up.**

All three deltas correct. Two connections. (a) The no-draw match for FLIPHEX is
not merely convenient — it is *guaranteed* (25 cells, odd → draws impossible), so
the `tanh` value head with `z ∈ {−1, +1}` transfers verbatim; drop the 0 case
entirely. (b) You wrote that whether FLIPHEX has exploitable symmetries "remains
an open question" — I computed the answer while reviewing this (see the chat
note): the board graph has exactly one non-trivial automorphism, a **left-right
mirror** (|Aut| = 2), and 180° is *not* one. So this paragraph's conclusion
shifts: FLIPHEX is not symmetry-free like chess — it sits **between** chess (1×)
and Go (8×), with a potential **2× mirror augmentation**, conditional on the
chiral tile (OPEN-2) not breaking it. This is a genuine upgrade to the take.

---

## §2 — MCTS vs alpha-beta (§5)

### 2.1 — Why the "slower" search wins 🔄
**Prompt.** Chess engines were historically dominated by alpha-beta. What is the
paper's argument for why MCTS + a learned evaluator beats a hand-tuned alpha-beta
engine (Stockfish) here — think about evaluation error and how the two searches
propagate it. Connect to FLIPHEX: this is the Axis 1 (exact/αβ) vs Axis 2 (MCTS)
tension — answer the cross-source part in synthesis **S1/S4**.

**My take.**

The paper does not argue that Monte Carlo Tree Search is intrinsically superior to alpha-beta search. Instead, it argues that the effectiveness of a search algorithm depends on the quality of the evaluation function it propagates.

Classical alpha-beta engines such as Stockfish compensate for imperfect evaluation functions by searching an enormous number of positions. Their strength comes from minimizing evaluation error through exhaustive search, carefully engineered heuristics, and decades of accumulated domain knowledge. In contrast, AlphaZero relies on a neural network that produces substantially more informative policy priors and value estimates. Because each evaluation is more accurate, MCTS can afford to explore only a tiny fraction of the positions considered by alpha-beta while still identifying stronger moves.

The key insight is therefore not that MCTS searches deeper or faster, but that it allocates computation differently. Rather than attempting to reduce uncertainty through brute-force expansion, MCTS uses the learned policy to focus on promising continuations and the learned value function to estimate the quality of non-terminal positions. Search effort is concentrated where the network predicts it is most valuable, instead of being distributed according to handcrafted search heuristics.

Importantly, this result should not be interpreted as evidence that MCTS universally dominates alpha-beta. The comparison is between complete systems rather than isolated search algorithms. AlphaZero combines MCTS with a powerful learned evaluator trained through self-play, whereas Stockfish combines alpha-beta with handcrafted evaluation, extensive domain knowledge, and decades of human refinement. The paper therefore demonstrates that a learned evaluation coupled with MCTS can outperform a highly optimized alpha-beta engine, not that MCTS alone is inherently superior.

For FLIPHEX, this distinction is even more significant. Unlike chess, FLIPHEX has almost no accumulated strategic knowledge, no established evaluation heuristics, and only limited human play experience. Fundamental properties of the game remain unknown, including whether the first player has a forced win, whether the current board configuration is well balanced, and how alternative board sizes or tile distributions would affect strategic depth. Under these conditions, designing a strong alpha-beta evaluation function would require assumptions that cannot yet be justified empirically.

From this perspective, AlphaZero is compelling not simply because it replaces alpha-beta with MCTS, but because it provides a framework for acquiring strategic knowledge directly through self-play instead of encoding that knowledge manually. More importantly, the same framework can be used not only to learn how to play FLIPHEX, but also to investigate the game itself by measuring first-player advantage, comparing alternative board designs, evaluating different tile layouts, and exploring whether the current rules produce a strategically rich and balanced game.

**Refined write-up.**

The sharpest thing in the note — you avoided the near-universal misreading
("MCTS beats alpha-beta") and landed the paper's actual claim: **complete
systems**, learned-eval + MCTS versus handcrafted-eval + αβ. One sharpening for
the Axis-1 ↔ Axis-2 tension (synthesis **S4**): the AZ-beats-Stockfish result
does **not** shrink your solver's role. Stockfish's evaluation is a heuristic;
your Phase-3 solver on small variants produces the **exact game value** — ground
truth no learned evaluator can claim. So the two axes are not "αβ vs MCTS"; they
are "exact truth on small boards" cross-checking "strong approximate policy on
the full board." That cross-check is the project's real contribution, and this
reading strengthens it rather than blurring it.

---

## §3 — Domain knowledge and representation (§6, §7)

### 3.1 — What AlphaZero still keeps
**Prompt.** §6 lists the domain knowledge AlphaZero retains. How does this list
differ from AGZ's four items (§8 of the AGZ note)? Specifically: what happens to
the **symmetry** item, and what is added to handle chess's rules (castling, draws,
repetition)? Which retained items does FLIPHEX also need?

**My take.**

Like AlphaGo Zero, AlphaZero deliberately minimizes domain-specific knowledge, but it updates the list to reflect the requirements of chess and shogi rather than Go. The retained knowledge consists only of information necessary to represent the game's rules and legal state, not handcrafted strategic expertise.

Compared with AlphaGo Zero, the most notable change is the removal of symmetry augmentation. Go naturally admits rotational and reflectional symmetries that preserve game semantics, whereas chess and shogi do not because piece movement, promotion, and player orientation make these transformations invalid. Consequently, AlphaZero no longer assumes that symmetric board positions should be treated as equivalent.

At the same time, AlphaZero extends the state representation to include rule-dependent information required by chess and shogi. This includes castling rights, repetition history, move counters, and other state variables needed to determine legal moves and game termination. These additions do not inject strategic knowledge; they simply ensure that the network observes the complete game state.

This distinction is important. AlphaZero removes assumptions that are specific to Go while retaining only those aspects of domain knowledge that are logically required to define the game itself. The algorithm therefore depends on an accurate representation of the rules, but not on handcrafted evaluation functions or expert strategic concepts.

For FLIPHEX, the same principle should apply. The input representation should encode every variable necessary to reconstruct the legal game state, while avoiding features that embed human strategic intuition. Any rule-specific state—such as tile orientation, remaining legal actions, or other game-dependent variables—belongs in the representation, whereas handcrafted notions of "good positions" should instead emerge through self-play.

**Refined write-up.**

Right principle: encode the rules completely, let strategy emerge. The one place
to revise is your symmetry sentence — you say chess/shogi "lack comparable
exploitable symmetries," implying FLIPHEX patterns with them. It does **not**:
the computed board automorphism group is Z/2 (a mirror), so in this paragraph's
taxonomy FLIPHEX sits between Go and chess, not alongside chess. See the chat
note — an upgrade to the take, not a correction of the principle.

### 3.2 — The input tensor and the structured policy head (R5 evidence)
**Prompt.** This is the most FLIPHEX-relevant section. Describe: (a) the input
plane stack for chess (piece planes, repetition, castling, move count) — how does
it compare to AGZ's 17 Go planes and to your FLIPHEX plane list (§5.2 of the AGZ
note)? (b) The **policy head**: chess uses **8×8×73** planes (a *from-square* ×
*move-type* factoring), shogi similar. Is this the empirical precedent adr-005's
(cell × tile × rotation) factoring was missing? State the honest verdict for R5
now that a real factored head exists in the literature.

**My take.**

This section is the strongest empirical support for ADR-005. Before reading AlphaZero, the proposed FLIPHEX policy representation—factoring actions into (cell × tile × rotation)—was motivated primarily by engineering intuition. AlphaZero demonstrates that this design principle has already been successfully applied in large action spaces.

Like AlphaGo Zero, AlphaZero represents the game state as a stack of feature planes. However, the chess representation is considerably richer because the rules require additional state variables beyond piece locations. Besides encoding piece positions over a history of previous states, the input includes information such as repetition history, castling rights, side to move, and move counters. These features do not express strategic knowledge; they simply provide the network with a complete description of the legal game state. The underlying design principle therefore remains unchanged: encode rules completely, but allow strategy to emerge through learning.

The most important contribution, however, is the policy head. Instead of treating every legal move as an independent output class, AlphaZero represents chess moves as an 8×8×73 tensor. Each prediction is factored into a source square and a move type, allowing the network to exploit the inherent structure of the action space while still producing a fixed-size policy output. Shogi adopts the same idea with a different factorization appropriate for its own move representation.

This provides exactly the kind of empirical precedent that ADR-005 was missing. Although the specific factors differ, the underlying principle is identical: represent actions as the Cartesian product of semantically meaningful components instead of enumerating every possible move independently. FLIPHEX's proposed (cell × tile × rotation) representation follows the same philosophy, adapting the factorization to the structure of its action space rather than copying the chess encoding itself.

The evidence therefore strengthens R5 considerably. AlphaZero does not merely show that structured policy heads are possible; it demonstrates that they scale successfully to complex board games with large action spaces. While this does not prove that FLIPHEX's particular factorization is optimal, it provides a strong empirical justification for treating structured action representations as a sound architectural design principle rather than an ad hoc engineering decision.

**Refined write-up.**

Strong — and this is where you asked me to be critical, so: you slightly
overstate. The same §7 reports an ablation you did not cite: *"We also tried
using a flat distribution over moves for chess and shogi; the final result was
almost identical although training was slightly slower."* So the honest R5
verdict is two-sided: (1) structured heads are validated and shown to scale
(supports adr-005), **but** (2) the paper's own test shows a flat head reaches
nearly the same final strength — so factoring is a training-efficiency
optimization, not a correctness requirement. That is the best possible R5
outcome: your factored head is well-precedented *and* has a documented safe
fallback (flat) if it ever complicates. Citing the ablation makes the case more
credible, not less — it turns "strongest empirical support" into "well-precedented
choice with a known escape hatch," which is what an ADR wants.

---

## §4 — Configuration and evaluation (§8, §9)

### 4.1 — Hyperparameters, and Dirichlet noise scaled to legal moves
**Prompt.** §8 gives the search/training configuration. Find how the **Dirichlet
noise α** is set for each game — the paper scales it to the typical number of
legal moves (α ≈ 0.3 for chess, 0.15 shogi, 0.03 Go). Why does α shrink as the
branching factor grows, and what α would that rule imply for FLIPHEX? (This is the
concrete fix flagged in the AGZ §6.3 refinement — bank the rule, not the constant.)

**My take.**

Rather than treating the Dirichlet noise parameter as a game-specific constant, AlphaZero presents it as a quantity that should scale with the typical number of legal moves. The reported values follow a clear pattern: approximately α = 0.30 for chess, α = 0.15 for shogi, and α = 0.03 for Go. Since Go has by far the largest branching factor, it receives the smallest concentration parameter.

The rationale becomes clearer when considering the role of the Dirichlet distribution. At the root node, exploration noise is added to the policy prior to encourage self-play to sample moves beyond those currently preferred by the network. As the number of legal actions increases, the same total amount of exploratory probability must be distributed across more candidates. Reducing α makes the injected noise remain appropriately sparse, preventing exploration from becoming nearly uniform over an excessively large action space. Conversely, games with fewer legal moves can use a larger α without overwhelming the learned policy.

The important lesson is therefore the scaling rule rather than the numerical constants themselves. AlphaZero suggests that the concentration parameter should be chosen relative to the typical branching factor of the game, ensuring that root exploration has a comparable qualitative effect across domains.

For FLIPHEX, this implies that α should not be copied directly from either AlphaGo Zero or AlphaZero. Instead, it should be estimated from the game's average number of legal moves. Since the current FLIPHEX implementation has approximately 1,450 legal opening actions, substantially more than the games studied in the paper, the corresponding α would likely need to be smaller than Go's 0.03 to preserve a similar exploration profile. The exact value should ultimately be treated as a tunable hyperparameter, but the paper provides a principled initialization rule based on branching factor rather than an arbitrary constant.

**Refined write-up.**

Scaling reasoning correct. Two sharpenings. (1) A common way to interpolate the
paper's three points is α ≈ 10 / (typical legal moves) — but flag it as a
**community heuristic** (KataGo and others), *not* stated in the paper; the paper
gives only {0.3, 0.15, 0.03} scaled inversely to legal moves. (2) Critical catch:
you plugged in **1,450**, but that is the *first-ply* count. AZ scales α to the
*typical* branching over a whole game, not the opening peak — and FLIPHEX's
branching collapses fast as the 25 cells fill. Using 1,450 would set α far too
small and starve mid-game exploration. Measure the **average** legal-move count
across a self-play game first (a quick histogram — the smoke script already walks
random games), then set α from that average, not from the opening.

### 4.2 — Evaluation and its rigor
**Prompt.** How is AlphaZero evaluated (opponent, time controls, number of games,
Elo method)? What are the acknowledged threats to a fair comparison with Stockfish
(hardware, opening books, time)? What would you replicate — and what would you do
*differently* — for FLIPHEX's H3, given the AGZ single-run critique still applies?

**My take.**

AlphaZero evaluates its playing strength by competing against the strongest available conventional engines for each game: Stockfish for chess, Elmo for shogi, and AlphaGo Zero for Go. Matches are played under fixed time controls, and player strength is estimated using Elo ratings derived from the game results. The evaluation is therefore practical rather than theoretical: the question is whether the trained system consistently wins against state-of-the-art opponents.

The paper also acknowledges that achieving a perfectly fair comparison is difficult. AlphaZero and Stockfish run on fundamentally different hardware, with AlphaZero relying on large TPU infrastructure while Stockfish runs on conventional CPUs. In addition, Stockfish's opening book and endgame tablebases are disabled to compare search algorithms rather than accumulated human knowledge. Time controls are equalized as much as possible, but computational resources remain inherently asymmetric because the two systems perform very different types of computation.

Despite these precautions, the evaluation has important methodological limitations. Like AlphaGo Zero, AlphaZero reports the outcome of a single successful training run rather than multiple independent replications. As a result, the paper demonstrates that the algorithm can achieve superhuman performance, but provides little evidence about training variance, reproducibility, or sensitivity to initialization and hyperparameter choices.

For FLIPHEX, I would replicate the general evaluation philosophy while strengthening its experimental rigor. A fixed benchmark opponent, standardized search budgets, and Elo-style ratings remain appropriate for measuring playing strength. However, I would additionally train multiple independent agents with different random seeds, report confidence intervals over match results, and measure variability across training runs. Since FLIPHEX is itself an evolving game, I would also extend the evaluation beyond playing strength by comparing different board layouts, tile distributions, and rule variants under the same evaluation protocol. In this setting, self-play becomes not only a way to evaluate agents, but also a methodology for evaluating the game design itself.

**Refined write-up.**

Excellent, and the multi-seed + design-evaluation extension is exactly right. One
precision: the multi-seed/CI rigor is not really an *extension* of H3 — it is
already latent in H3's original wording ("a stable win-rate distribution across
independent training runs … agrees within Wilson CI"). You are making H3 honest,
not enlarging it. The "compare board layouts / tile distributions / rule variants"
half is bigger than H3 and belongs with H1/H2/H5 under the motivation reframe —
see the TODO verdict in chat, where I argue it is the strongest of your three
notes but needs scoping so it does not blow the compute budget.

---

## §5 — Limitations and what does not transfer

### 5.1 — The authors' concessions
**Prompt.** What does the paper concede about generality, compute, and the
fairness of the Stockfish match? Which limitation is *load-bearing* for FLIPHEX —
and does anything here change the transfer verdict you reached in §8.2 of the AGZ
note (that assumptions, not compute, are what matter)?

**My take.**

Although AlphaZero presents a remarkably general reinforcement learning framework, the paper is careful not to claim unlimited generality. Its conclusions are supported only for deterministic, perfect-information, two-player zero-sum board games. Whether the same approach transfers to games with hidden information, stochastic dynamics, or multiplayer interactions remains outside the scope of the work.

The paper also makes clear that its results rely on extraordinary computational resources. Large-scale TPU infrastructure enables millions of self-play games and repeated neural network updates within practical time. This level of compute is clearly inaccessible to most researchers and should be viewed as an experimental condition rather than an assumption of the algorithm itself.

The comparison against Stockfish is likewise presented with appropriate caveats. Although opening books and endgame tablebases are disabled to isolate the search algorithms, the two systems run on fundamentally different hardware and implement different computational strategies. Consequently, the evaluation demonstrates competitive playing strength under a carefully designed experimental setup rather than proving the intrinsic superiority of one search algorithm over another.

For FLIPHEX, however, none of these limitations changes the central transfer argument established after studying AlphaGo Zero. The most valuable contribution of AlphaZero is not its computational scale but the architectural principles that remain valid under far smaller budgets: self-play reinforcement learning, neural-guided MCTS, structured policy representations, and learning strategic knowledge instead of encoding it manually.

In fact, the FLIPHEX context makes this distinction even more important. The primary challenge is not reproducing DeepMind's level of compute, but understanding a game whose strategic properties are still largely unexplored. Questions such as first-player advantage, board balance, action-space design, and strategic depth remain open regardless of available hardware. AlphaZero therefore transfers primarily as a research methodology rather than as a blueprint for reproducing DeepMind's computational scale. The assumptions behind the algorithm remain the load-bearing contribution; the compute budget determines only how efficiently those assumptions can be explored.

**Refined write-up.**

Correct, and it lands the AGZ §8.2 verdict cleanly: assumptions are load-bearing,
compute is not. One thing to add: the assumptions AZ needs (deterministic,
perfect-information, cheap to simulate, known terminal/scoring) are all satisfied
by FLIPHEX — *and*, unlike chess, FLIPHEX additionally has an **exact solver**
available on small variants. So you are strictly better off than the AZ setting
for *validation*: you can check the learned policy against ground truth, which
DeepMind could not. Compute limits how fast you explore; it does not threaten
correctness — and the solver gives you a correctness oracle chess never had.

---

## Lessons Learned

Reading AlphaZero fundamentally changed how I think about applying reinforcement learning to FLIPHEX.

The first change concerns **transferability**. AlphaZero demonstrates that the key ideas of the AlphaGo Zero framework are not tied to Go. Self-play reinforcement learning, neural-guided MCTS, and structured policy representations transfer successfully to games without exploitable board symmetries. This shifted my perspective from asking whether FLIPHEX "looks like Go" to asking whether it satisfies the algorithmic assumptions that actually matter.

The second change is the role of **structured policy heads**. Before this reading, the proposed (cell × tile × rotation) action representation in ADR-005 was primarily an engineering intuition. AlphaZero provides a concrete empirical precedent: chess and shogi both factor actions into semantically meaningful components rather than enumerating every legal move independently. This substantially strengthens the architectural justification for FLIPHEX's proposed policy representation.

Perhaps the most important insight, however, is that AlphaZero is valuable even beyond learning to play FLIPHEX. Since FLIPHEX has very limited accumulated strategic knowledge, many basic questions remain unanswered, including first-player advantage, board balance, action-space design, and the effect of alternative board geometries or tile distributions. This suggests a broader research direction: use self-play not only to train an agent, but also as a computational methodology for investigating and improving the game itself.

Finally, this paper reinforced a distinction established while reading AlphaGo Zero: the transferable contribution is the learning framework and its assumptions—not DeepMind's computational scale. Large-scale TPUs explain how quickly AlphaZero reached its results, but they are not the reason the underlying ideas transfer to new games.

## Failed Attempts

Several assumptions made before reading AlphaZero were revised.

Initially, I viewed the main architectural decision as choosing between alpha-beta search and MCTS. After studying the comparison with Stockfish, this framing appears incomplete. For FLIPHEX, the more fundamental question is whether enough strategic knowledge exists to engineer a strong evaluation function at all. Given the current state of the game, self-play appears more attractive because it acquires strategic knowledge rather than assuming it already exists.

I also initially treated the absence of board symmetries in FLIPHEX as an established fact. After revisiting the game's geometry, I realized this is still a hypothesis rather than a verified property. Whether exploitable symmetries exist remains an open research question, although AlphaZero demonstrates that the learning framework does not depend on symmetry augmentation.

Another revision concerns evaluation. My original focus was measuring agent strength, but AlphaZero suggests a broader role for evaluation. Since FLIPHEX itself is still being studied, the experimental protocol should also support comparing board layouts, tile distributions, rule variants, and training stability across independent runs.

Finally, I originally viewed AlphaZero as a target implementation. After completing this reading, it seems more appropriate to view it as a research methodology for computational game design, using reinforcement learning to understand the properties of FLIPHEX before treating its current rule set as fixed.
