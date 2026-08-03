# Reading companion — Silver et al. 2017, AlphaGo Zero

**Citation.** Silver, D., Schrittwieser, J., Simonyan, K., Antonoglou, I.,
Huang, A., Guez, A., et al. (2017). *Mastering the game of Go without human
knowledge.* **Nature** 550, 354–359. doi:10.1038/nature24270. Read from the
UCL open-access accepted manuscript (`refs/silver-2017-alphago-zero.pdf`).

**Why this source, and where it sits.** This is the *foundational* paper for
Axis 2 — the first system to reach superhuman Go by self-play alone, with **one
network** `f_θ(s) = (p, v)` guiding MCTS and trained on MCTS's own improved
policy. Read it **before** Silver 2018 (which generalises the same recipe and
*removes* pieces of it — the evaluator gate, the symmetry augmentation), and
ideally after R&N Ch.5 (MCTS/minimax vocabulary). Everything FLIPHEX's Phase 4
pipeline does is a scaled-down version of what is described here.

**Cross-refs this reading feeds:**
- [adr-005](docs/adr/adr-005-alphazero-scope-and-network.md) — network + the
  factored (cell × tile × rotation) policy head (R5, the least-evidenced Phase 0
  decision). This paper is the primary evidence for/against it.
- [adr-003](docs/adr/adr-003-piece-representation.md) — placed tiles are inert;
  bears on what the input tensor must (not) encode.
- [board-geometry.md](docs/board-geometry.md) — FLIPHEX has a **trivial symmetry
  group**; AlphaGo Zero leans on Go's 8-fold dihedral symmetry. Direct conflict,
  see §8.
- [exercises/ex04_alphazero_math.md](exercises/ex04_alphazero_math.md) — the loss
  and PUCT derivations land here.
- [notes/phase2-alphazero-paper-notes.md](notes/phase2-alphazero-paper-notes.md)
  — the phase note; this companion is the detailed instrument behind it.
- TIL #5 ("AlphaZero in 500 lines") — one-liner insights get parked for it.

**Legend.** Prompts marked 🔄 need synthesis with another source — answer them
in [notes/phase2-synthesis.md](notes/phase2-synthesis.md), not here.

**Reading material** (extracted via `paper-study`, gitignored under
`notes/sources/`): [manifest](sources/silver-2017-alphago-zero/manifest.json) ·
[§2 text](sources/silver-2017-alphago-zero/sections/02-1-reinforcement-learning-in-alphago-zero.md)
+ [Nível-1 companion](sources/silver-2017-alphago-zero/study/02-reinforcement-learning.md) ·
[§11 Methods](sources/silver-2017-alphago-zero/sections/11-methods.md)
+ [Nível-1 companion](sources/silver-2017-alphago-zero/study/11-methods.md).
Note: Equation 1 (the loss) and Figures 1–2 are images and did not extract — the
loss is transcribed in the §2 companion.

---

## §1 — The core idea: tabula rasa self-play

### 1.1 — What "without human knowledge" actually means
**Prompt.** List precisely what AlphaGo Zero removes versus prior AlphaGo (human
games, handcrafted features, rollout policy). What *domain knowledge* do the
authors admit they keep (rules, board symmetry, Tromp-Taylor scoring)? For
FLIPHEX, which of those retained items has an analogue and which does not?

**My take.**

AlphaGo Zero represents a shift in philosophy rather than only a simplification of the architecture. Instead of relying on expert demonstrations and multiple independently trained components, the system learns entirely through self-play, starting from a randomly initialized neural network. Strategic knowledge is not transferred from human experts but emerges through reinforcement learning guided by Monte Carlo Tree Search (MCTS).

Compared with previous AlphaGo systems, AlphaGo Zero removes three major sources of human expertise:

- **Human expert games:** no supervised pre-training from professional Go games. All training data is generated through self-play.
- **Handcrafted features:** the input consists only of the raw board state and player information, without manually engineered tactical features.
- **Rollout policy:** leaf evaluation no longer depends on fast rollout simulations. Instead, a single neural network estimates both the policy and the value of a position.

The authors nevertheless retain several forms of domain knowledge. The game rules are provided explicitly so that legal moves and game outcomes can be computed. The implementation also exploits Go's eight-fold board symmetry as a data augmentation technique and uses Tromp-Taylor scoring to determine game results. Therefore, "without human knowledge" should be interpreted as removing human strategic expertise rather than eliminating all domain-specific assumptions.

For FLIPHEX, some of these retained elements have direct analogues. The game rules and legal move generation are intrinsic components of the environment, just as they are in Go. However, board symmetry differs substantially. Whereas Go benefits from an eight-fold dihedral symmetry that can be exploited during training, FLIPHEX has only trivial symmetry, making the augmentation strategy used by AlphaGo Zero largely inapplicable.

**Refined write-up.**

Accurate — this is the right reading. Two sharpenings. First, the paper's own
list of *retained* domain knowledge is four items, not two: (1) the rules, for
legal-move and terminal detection; (2) Tromp–Taylor scoring; (3) the 8 board
symmetries, used both to augment data and to average evaluations; (4) the input
is the current position *plus a short stone-history*. It removes: human games,
handcrafted features, rollouts, and the *separate* policy/value networks (now
fused). Second — and this transfers cleanly to FLIPHEX — Go under its komi is a
**two-outcome** game (win/loss, no draw), which is why the value target is ±1.
FLIPHEX shares exactly this (25 cells, odd → draws impossible), so the ±1 value
head carries over unchanged. Of the retained items, FLIPHEX has: rules ✓ (the
engine), scoring ✓ (count colours). It does **not** have Go's symmetry — the one
structural gift AlphaGo Zero leans on that we cannot inherit (developed in §8.1).

### 1.2 — One network, two heads
**Prompt.** Write the signature `f_θ(s) = (p, v)` exactly: what is `p`, what is
`v`, what is the range of `v` and why `tanh`? This is the shape adr-005 commits
FLIPHEX to — does the paper give `p` as a flat distribution over moves?

**My take.**

AlphaGo Zero represents its neural network as `f_θ(s) = (p, v)`, where `s` is the current game state. The network jointly predicts:

- `p`: a probability distribution over the legal moves from state `s`, used as the prior policy that guides Monte Carlo Tree Search (MCTS).
- `v`: a scalar estimate of the expected game outcome from the perspective of the current player.

The value prediction is constrained to the interval `[-1, 1]`, matching the game outcomes (`-1` = loss, `0` = draw, `+1` = win). The value head therefore uses a `tanh` activation, whose output naturally lies in this range.

The paper defines `p` simply as a probability distribution over legal moves. It does not propose a factored or hierarchical policy representation. Consequently, FLIPHEX's factored policy head (cell × tile × rotation) is an architectural adaptation rather than a design prescribed by AlphaGo Zero.

**Refined write-up.**

Right on the shape and on the R5 verdict. Two precisions. (a) The target `z` is
in `{-1, +1}` (no draw in Go, and none in FLIPHEX); the *prediction* `v` is
continuous in `(-1, 1)` via `tanh`, read as an expected outcome ≈ `2·P(win) − 1`.
So drop the "0 = draw" case entirely — its absence is actually a point in favour
of reusing the value head unchanged. (b) `p` is defined over **all** moves
(19×19 + pass = 362 for Go), then illegal moves are masked out and the rest
renormalised — it is not a distribution over legal moves *a priori*. That masking
step is exactly what FLIPHEX's factored head will also do, over illegal
(cell, tile, rotation) triples. Net for [adr-005](docs/adr/adr-005-alphazero-scope-and-network.md):
the paper fixes `(p, v)` and the `tanh` value, and says **nothing** about
factoring `p` — the factorisation is ours to justify and test (R5).

---

## §2 — Reinforcement learning in AlphaGo Zero (the algorithm)

### 2.1 — MCTS as a policy-improvement operator
**Prompt.** The headline mechanism: the search produces a policy `π` (from visit
counts) *stronger* than the network's raw `p`, and the network is trained toward
`π`. State why this is a policy-improvement step. This is the single most
important idea in the paper — predict, before reading the proof sketch, why
searching then imitating the search beats imitating the network directly.

**My take.**

The neural network provides an initial policy `p`, but this prediction is only an estimate based on the current network parameters. MCTS refines this estimate by exploring many continuations of the game, combining the network's prior policy with search statistics. As a result, the search may discover that moves initially assigned low probability perform better than expected, while apparently promising moves prove weaker after deeper analysis.

The improved policy `π`, obtained from the MCTS visit counts, therefore represents a stronger decision than the network's raw prediction. Training the network to imitate `π` is a policy-improvement step because the learning target is generated after a more informed search rather than by the network itself. Over successive self-play iterations, the network learns to approximate the decisions it would reach after search, making both the network and the search progressively stronger.

**Refined write-up.**

Well captured — this is the heart of the paper. The formal name is worth fixing
in your head: it is **approximate policy iteration** (Sutton & Barto framing).
MCTS is the *policy-improvement* operator (it returns `π` provably no worse, and
usually much better, than the prior `p`), and playing the game to a terminal `z`
is the *policy-evaluation* operator; the algorithm just alternates the two. The
precise reason "search then imitate" beats "imitate `p`": the tree does bounded
lookahead and evaluates its leaves with the **same network's value head**, so `π`
aggregates many `v`-estimates into a single, lower-variance, deeper-informed
target than the raw prior could ever be. This is [ex04](exercises/ex04_alphazero_math.md)
Q2 (why `π` is the stronger target) and a strong TIL #5 seed.

### 2.2 — The loss function
**Prompt.** Copy the loss `l = (z − v)² − πᵀ log p + c‖θ‖²`. Identify each term
(value regression, policy cross-entropy, L2). What is `z`, and how is it labelled
for every position in a self-play game? Draft the term-by-term interpretation
here; it becomes ex04 Q1.

**My take.**

AlphaGo Zero optimizes the following loss function:

`l = (z − v)² − πᵀ log p + c‖θ‖²`

Each term has a distinct purpose:

- **`(z − v)²` — Value regression.** This mean squared error trains the value head to predict the final game outcome. The target `z` is the actual result of the self-play game from the perspective of the player to move at state `s` (`-1` = loss, `0` = draw, `+1` = win).

- **`−πᵀ log p` — Policy cross-entropy.** This term trains the policy head to match the improved policy `π` produced by MCTS rather than the network's raw prediction. In this way, the network learns to approximate the stronger decisions obtained through search.

- **`c‖θ‖²` — L2 regularization.** This penalty discourages excessively large network weights, helping reduce overfitting and improving generalization.

The game outcome `z` is assigned to every position encountered during a self-play game. Thus, every state visited in a game becomes a supervised training example with target `(π, z)`: the improved policy from search and the final game result.

**Refined write-up.**

Correct on all three terms. Precisions: the cross-entropy `−πᵀ log p` uses the
**soft** distribution `π` (visit-count proportions), not a one-hot label — that
is what makes it *distillation of the search*, not classification. `z_t = ±r_T`
with the sign taken from the player to move at step `t` (you said this — good).
Note there is **no entropy bonus** in the loss; all exploration comes from MCTS
and the root Dirichlet noise (§6.3), not from the objective. For FLIPHEX the loss
is usable verbatim, with `z ∈ {-1, +1}`. This is [ex04](exercises/ex04_alphazero_math.md)
Q1 — transcribe your term-by-term breakdown there.

### 2.3 — The self-play → train loop
**Prompt.** Sketch the loop: self-play generates `(s, π, z)` triples → network
trains on them → improved network generates better self-play. Where does the
data come from and how much is reused (replay)? How does this differ from
classical minimax, which has no learning at all? 🔄 (with R&N Ch.5)

**My take.**

AlphaGo Zero follows an iterative reinforcement learning loop. First, the current neural network plays games against itself using MCTS guided by its policy and value predictions. During each self-play game, every visited state is stored together with the improved search policy `π` and, once the game ends, the final outcome `z`. This produces training examples of the form `(s, π, z)`.

The collected self-play data are stored in a replay buffer, from which mini-batches are sampled to train the neural network. As the network improves, it provides more accurate policy priors and value estimates, allowing MCTS to perform stronger searches. These stronger searches generate higher-quality training targets, creating a positive feedback loop between search and learning.

Unlike classical minimax or standard MCTS, which perform search independently for each game and discard all information afterward, AlphaGo Zero accumulates knowledge across games by updating the neural network. The search is therefore not only used to select moves, but also to generate training data that continually improves future searches.

**Refined write-up.**

Good. One concrete detail for our Phase-4 buffer sizing: AlphaGo Zero samples
each mini-batch **uniformly from the most recent ~500,000 self-play games** — a
sliding window, not an unbounded replay of all history. That bounded window is
what keeps the data on-policy enough to be a valid evaluation target.
Reminder: this prompt is 🔄 — its cross-source half (contrast with minimax/αβ,
which are search-only and stateless across games, learning nothing) belongs in
[phase2-synthesis.md](notes/phase2-synthesis.md) **S1**. Move that half there
when you read R&N Ch.5; the crisp one-liner is *"classical search recomputes;
AlphaZero's search compounds, because its output trains the prior."*

---

## §3 — Empirical analysis of training

### 3.1 — The learning curve and its rigor
**Prompt.** What is the x-axis and the Elo y-axis of the main training-curve
figure? Over what wall-clock/how many games? Is there any variance band or
single-run reporting — what would a statistician want that the paper does not
show? (Relevant to H3: our own convergence-across-seeds claim.)

**My take.**

The main training curve reports the strength of AlphaGo Zero as training progresses. The x-axis represents training time (wall-clock time, shown in days) together with the corresponding amount of self-play experience, while the y-axis reports playing strength in Elo rating. The paper shows that AlphaGo Zero reaches superhuman performance within a few days of training and continues improving over tens of millions of self-play games.

From a statistical perspective, however, the experimental reporting is limited. The figure presents a single training trajectory without variance bands, confidence intervals, or results across multiple random seeds. As a result, the paper demonstrates that the method can converge, but it does not quantify the variability or reproducibility of the learning process.

This observation is particularly relevant for FLIPHEX. If our project claims convergence or learning stability (H3), reporting results across multiple random seeds and summarizing their variability would provide stronger empirical evidence than a single training curve.

**Refined write-up.**

Exactly the H3 point, and correctly identified as a *presentation* weakness we
can beat. Concrete numbers to anchor it: the headline 3-day run used a 20-block
network and **4.9M** self-play games; the later 40-day, 40-block run used ~**29M**
and reaches the top Elo. x-axis = training steps/days, y = Elo. Your statistician's
objection stands: one trajectory, no seed variance, no confidence band. Our H3
does the opposite by design (≥5 seeds, Wilson/bootstrap bands per the roadmap's
Phase 5) — so "the paper shows it *can* converge; we show *how reliably*" is a
real, defensible contribution over the source, not just a critique.

### 3.2 — Beating the supervised-learning baseline
**Prompt.** AGZ (pure RL) is compared against a network trained on human games.
Which wins, and what does the crossover tell you about whether human priors help
or hurt? What is the FLIPHEX analogue (we have *no* human games at all)?

**My take.**

AlphaGo Zero ultimately outperforms the supervised-learning baseline trained on human expert games. Although the supervised model begins with stronger prior knowledge, its performance eventually plateaus because it is constrained by the strategies present in the human training data. In contrast, AlphaGo Zero starts without strategic knowledge but continues to improve through self-play, eventually surpassing the human-trained network.

The crossover between the two learning curves suggests that human priors are beneficial for accelerating initial learning, but they are not necessary to achieve the highest level of performance. By relying solely on reinforcement learning, AlphaGo Zero is free to discover strategies that extend beyond established human play.

For FLIPHEX, there is no supervised-learning baseline because no expert game database exists. This makes self-play not only an attractive alternative but the natural training paradigm. Rather than reproducing human strategies, the objective is to allow strong strategies to emerge directly from interaction with the game environment.

**Refined write-up.**

Correct. Sharpen the lesson: the supervised network learned faster *and* was
initially stronger, but **plateaued** — because it is capped by the ceiling of
the human games it imitated. Pure RL starts weaker and keeps climbing past that
ceiling. So the takeaway is not "human priors hurt" but "human priors cap you at
the data's quality." The FLIPHEX case is even cleaner than Go's: no human corpus
exists at all, so self-play is not a *choice over* supervised learning — it is
the only route, and there is no inherited ceiling to escape. That is a genuine
point in favour of Axis 2 for this game (relevant to H1/H3).

---

## §4 — Knowledge learned by AlphaGo Zero

### 4.1 — Rediscovery vs novelty
**Prompt.** The paper claims AGZ rediscovered known joseki and then discarded
some for novel play. What is the evidence, and how would you design the FLIPHEX
analogue — detecting whether the agent finds openings the designers did not
anticipate? (Ties to H5, archetype usage.)

**My take.**

The authors report that AlphaGo Zero initially rediscovered well-established joseki despite receiving no human demonstrations during training. As learning progressed, however, it increasingly deviated from conventional human opening theory and adopted novel sequences that were later recognized as strong by expert players. This serves as qualitative evidence that self-play can first recover known strategic principles and then move beyond them.

The evidence is primarily observational rather than statistical. The paper compares representative opening sequences and discusses expert analyses of AlphaGo Zero's games, but it does not define a quantitative metric for measuring strategic novelty.

For FLIPHEX, an analogous evaluation would be to analyze whether the trained agent consistently develops opening patterns or strategic archetypes that were not anticipated by the game's designers. Such an analysis could compare opening frequencies, board-control patterns, or archetype usage across training, helping determine whether the agent merely converges to expected play or discovers genuinely novel strategies. This directly supports H5 by measuring the emergence and diversity of strategic archetypes rather than only final playing strength.

**Refined write-up.**

Accurate, and the H5 operationalisation is the valuable part. The paper's novelty
evidence is purely **qualitative** (expert commentary, joseki-over-time vignettes)
— no novelty metric, as you note. FLIPHEX can do strictly better because the deck
*is* a finite, labelled vocabulary: track (i) per-archetype placement frequency
and (ii) win-correlation across training, plus (iii) opening-move entropy over
time. That turns "did it find openings the designers didn't expect?" into three
measurable curves — which is exactly the H5 test named in the roadmap. Worth a
line in the H5 statement when you lock hypotheses.

---

## §5 — Methods: neural network architecture

### 5.1 — The residual tower and the two heads
**Prompt.** Describe the body (conv → residual blocks) and the two heads. How is
the **policy head** shaped for Go (19×19 + 1 pass)? This is *flat*. adr-005
chose a **factored** head for FLIPHEX (cell × tile × rotation). Does AGZ offer
any evidence that a flat head over the full action set is fine at this scale, or
is Go's action space just small enough that the question never arises? Record
the honest verdict for R5.

**My take.**

AlphaGo Zero employs a deep convolutional neural network composed of an initial convolutional layer followed by a tower of residual blocks. This shared feature extractor feeds two output heads: a policy head, which predicts move probabilities, and a value head, which estimates the expected game outcome.

For Go, the policy head is represented as a flat probability distribution over all legal actions. On a 19×19 board, this corresponds to one output for each board intersection plus an additional output for the pass move, yielding a single flat action distribution.

The paper does not investigate alternative policy parameterizations. It neither compares flat and factored policy heads nor discusses whether the action space size influenced this architectural choice. Therefore, AlphaGo Zero provides evidence that a flat policy head is sufficient for Go, but it does not establish that this representation is optimal or generally applicable to games with more structured action spaces.

For ADR-005 (R5), the honest conclusion is that the paper supports learning a policy over actions but provides no direct evidence for or against a factored policy representation. The decision to factor the FLIPHEX policy into (cell × tile × rotation) is therefore an architectural adaptation motivated by the structure of the game's action space rather than by empirical evidence from AlphaGo Zero.

**Refined write-up.**

Correct, and the R5 verdict is the honest one. Concrete architecture, to make it
tangible: body = one conv block + **19 (or 39) residual blocks** of 256 filters;
**policy head** = 1×1 conv → fully-connected → 362 logits (flat); **value head**
= 1×1 conv → FC(256) → scalar `tanh`. So "flat head" literally means one dense
layer over the whole action set. Go's 362 actions are small enough that factoring
never *needs* to arise. FLIPHEX's raw action set is larger (≈1,450 on ply 1) but
still not huge, so adr-005's factoring is an **efficiency / generalisation bet**,
not a necessity — and, as you conclude, unsupported either way by this paper.
That is precisely why adr-005 flags it as R5 *to be tested empirically in
Phase 4*, e.g. flat-vs-factored head as an ablation.

### 5.2 — The input tensor
**Prompt.** AGZ stacks 17 binary planes: 8 of own-stone history, 8 of opponent
history, 1 for colour to play. *Why history planes* (ko, repetition)? FLIPHEX is
fully observable and — adr-003 — **placed tiles are inert with no stored
rotation**. Argue whether FLIPHEX needs any history planes at all, and list the
planes you would actually use (own / opp / empty / joker / hand bitmasks).

**My take.**

AlphaGo Zero represents each board state as a stack of 17 binary feature planes: eight planes encoding the recent history of the current player's stones, eight planes for the opponent's stones, and one plane indicating which player is to move. The history planes are included because the legality and strategic interpretation of some moves depend on previous board states, particularly due to the ko rule, which prevents immediate repetition of positions.

FLIPHEX differs fundamentally in this regard. According to ADR-003, the game is fully observable, placed tiles become inert, and their rotations are not stored after placement. Assuming no game rule depends on previous board configurations, the current state is sufficient to determine all legal actions and future transitions. Therefore, history planes appear unnecessary.

Instead, the input tensor should encode only the current game state. A suitable representation could include separate planes for the current player's tiles, the opponent's tiles, empty cells, joker locations (if represented on the board), and additional binary feature planes describing the tiles currently available in each player's hand. This representation preserves the Markov property while providing all information required for decision making.

**Refined write-up.**

The Markov argument is right, and it hangs directly on
[adr-003](docs/adr/adr-003-piece-representation.md): FLIPHEX is Markov in
`(colours, hands, to_move)` *precisely because placed tiles are inert* — there is
no ko, no repetition rule, and no hidden information, so **zero history planes**
are needed (Go needs them only for ko/superko). One correction to your plane
list: the **joker needs no board plane.** Once placed it is just an inert,
coloured token that scores by colour like any other tile — its identity never
affects future dynamics or scoring. It only needs representation as a distinct
*playable tile in hand* (a hand bit for Player 1), because it is a legal
zero-arrow action. So the encoding simplifies to: own-colour, opponent-colour,
empty, per-player hand bitmask planes, and a to-move scalar — no per-tile
rotation, no history, no joker-location plane. That simplification is a nice,
recordable consequence of adr-003.

---

## §6 — Methods: MCTS (the PUCT search)

### 6.1 — The four phases and the PUCT rule
**Prompt.** Write the select/expand+evaluate/backup cycle and the selection
formula
`a* = argmax_a [ Q(s,a) + c_puct · P(s,a) · √(Σ_b N(s,b)) / (1 + N(s,a)) ]`.
Label exploitation / prior / exploration. How does `P(s,a)` (network prior) enter
expansion? This becomes ex04 and TIL #2.

**My take.**

Each MCTS simulation consists of four phases:

1. **Selection:** Starting from the root, repeatedly choose the action that maximizes

\[
a^* = \arg\max_a \left[
Q(s,a)
+
c_{\text{puct}}
P(s,a)
\frac{\sqrt{\sum_b N(s,b)}}{1+N(s,a)}
\right].
\]

2. **Expansion and evaluation:** When a leaf node is reached, it is expanded. The neural network evaluates the state, producing a policy prior \(P(s,\cdot)\) over legal actions and a value estimate \(v\). The prior initializes the outgoing edges of the new node and biases future exploration toward actions the network considers promising.

3. **Backup:** The predicted value is propagated back through every edge visited during the simulation, updating the action-value estimates \(Q(s,a)\) and visit counts \(N(s,a)\).

After many simulations, the action with the highest visit count is selected.

In the PUCT equation, the two terms have distinct roles. The value estimate \(Q(s,a)\) represents **exploitation**, favoring actions that have performed well during previous simulations. The exploration term combines the network prior \(P(s,a)\), the exploration constant \(c_{\text{puct}}\), and the visit counts. The prior biases exploration toward actions that the neural network predicts to be promising, while the visit-count ratio gradually shifts search effort toward less explored actions.

Unlike classical UCT, where all unexplored actions are initially treated equally, PUCT injects learned knowledge directly into the search through the policy prior, allowing the search to focus on more promising branches from the very beginning.

**Refined write-up.**

Correct — phases and term-roles all right. Small precisions: a freshly expanded
node's edges initialise `N = 0`, `Q = 0`, `P = ` network prior; selection
maximises `Q + U` at every level down to a leaf; the value backed up is the
leaf's network `v`, sign-flipped per level for the alternating player. And you
nailed the easy-to-miss point — the move actually played from the root is
`argmax N` (robustness), **not** `argmax Q`. This is [ex04](exercises/ex04_alphazero_math.md)
Q5 and the core of TIL #2. The UCT→PUCT contrast is also 🔄 **S1** in the
synthesis (UCB1's `√(ln N / n)` exploration vs PUCT's prior-weighted
`P·√ΣN/(1+N)`).

### 6.2 — No rollouts
**Prompt.** Classic MCTS ends a simulation with a random rollout; AGZ replaces it
with the value head `v`. Why is that both faster and stronger, and why does a
*perfect-information* game make the value estimate trustworthy in a way an
imperfect-information game (your PTCG) would not? 🔄 (with R&N Ch.5)

**My take.**

Traditional MCTS estimates the value of a leaf node by performing a random rollout until the end of the game. AlphaGo Zero replaces this expensive simulation with the neural network's value prediction \(v\), which directly estimates the expected outcome from the current position. This makes search substantially faster because each simulation avoids playing dozens or hundreds of additional random moves. It is also stronger because the learned value function provides a much more informed estimate than a random rollout, whose outcome is often noisy and unrealistic.

This approach works particularly well in Go because it is a perfect-information game. The complete game state is fully observable, so the value network receives all information needed to estimate the probability of winning from that position. As training progresses, the network learns an increasingly accurate mapping from board states to expected outcomes.

In an imperfect-information game such as Pokémon TCG, the same observed game state may correspond to many different hidden states due to unknown cards in the opponent's hand, deck, or prize cards. Consequently, the value network must estimate an expectation over hidden information rather than over a fully observed state, making accurate value prediction significantly more difficult. This is one reason why directly applying AlphaGo Zero's search algorithm to imperfect-information games is considerably more challenging.

**Refined write-up.**

Correct, and the perfect-information point is the one that matters. Sharpen it: a
random rollout is a *single* Monte-Carlo sample of one arbitrary continuation —
high-variance, often unrealistic — whereas the value head `v` is a *learned,
low-variance* estimate of the same quantity. So swapping rollouts for `v` is both
faster (no dozens of extra moves per simulation) and stronger (better signal per
simulation). The perfect- vs imperfect-information split you drew is exactly the
crux: in Go/FLIPHEX `v` is a function of the **true** state, so with training it
can be accurate; in PTCG the same *observation* maps to many hidden states, so
`v` would have to estimate an **expectation over an information set** — which is
why perfect-info MCTS uses the value net directly while imperfect-info needs
determinization / IS-MCTS. This 🔄 belongs in synthesis **S1**, and it is a clean
**TIL #1** hook — arguably the single biggest thing FLIPHEX gains over your PTCG
work.

### 6.3 — Exploration: Dirichlet noise and temperature
**Prompt.** At the root, AGZ adds Dirichlet noise to the prior; the move is
sampled with temperature `τ = 1` for the first 30 moves then `τ → 0`. Why noise
*only* at the root? For FLIPHEX (25 plies total), what "first 30 moves" scales
to, and how the τ schedule interacts with our short game.

**My take.**

AlphaGo Zero injects Dirichlet noise only into the root node's prior probabilities before each MCTS search. This encourages different self-play games to explore alternative opening moves while leaving the remainder of the search tree guided by the learned policy and accumulated search statistics. If noise were added throughout the tree, every simulation would become unnecessarily noisy, reducing the effectiveness of MCTS rather than simply encouraging exploration.

Action selection also depends on the temperature parameter \( \tau \). During the first 30 moves, actions are sampled according to the MCTS visit counts (\( \tau = 1 \)), promoting exploration and generating diverse self-play data. After move 30, the temperature is effectively reduced to zero, so the move with the highest visit count is selected almost deterministically, emphasizing strong play over exploration.

This schedule does not transfer directly to FLIPHEX because games are much shorter (approximately 25 plies). Keeping a high temperature for the first 30 plies would mean exploring throughout the entire game. A more appropriate strategy is to scale the exploration period to the game's length, using a positive temperature only during the opening portion before switching to deterministic action selection for the remainder of the game. The exact cutoff should be treated as a tunable hyperparameter rather than copied directly from AlphaGo Zero.

**Refined write-up.**

Correct, and well reasoned — you got both the "why root-only" and the FLIPHEX
scaling right. Three precisions worth banking. (1) The exact noise mix is
`P(s,a) = (1−ε)·p_a + ε·η_a` with `η ~ Dir(0.03)` and `ε = 0.25` — so a full
**quarter** of the root prior mass is replaced by noise, which is a lot.
(2) **Do not copy `α = 0.03`.** That value is tuned to Go's ~250 legal moves; the
Dirichlet concentration is scaled to the branching factor (fewer legal moves →
larger α). FLIPHEX has far fewer moves per ply, so its α must be re-tuned — a
wrong α here silently either floods the search with noise or fails to explore.
(3) A sharper reason for root-only: noise at *internal* nodes would corrupt the
very `Q`/value estimates MCTS is trying to compute, degrading the search; the
root is the one place we *want* an exploratory visit distribution, because that
distribution becomes the training target `π`. Your temperature point stands:
`τ = 1` ⇒ sample ∝ `N`, `τ → 0` ⇒ argmax `N`; "first 30 moves" is ~12% of a
~250-move Go game, so proportionally ~3 plies of FLIPHEX — but treat the opening
cutoff (say the first 6–10 plies) as a tunable hyperparameter, exactly as you
said. Good material for [ex04](exercises/ex04_alphazero_math.md) Q5 and TIL #2.

---

## §7 — Methods: self-play pipeline and optimisation

### 7.1 — The evaluator gate
**Prompt.** AGZ only promotes a new network to generate self-play if it beats the
current best in ≥ 55% of games. State the mechanism. Note for §8: Silver 2018
*removes* this gate — flag the disagreement now and resolve it there. 🔄
Does a laptop-scale FLIPHEX run need the gate, or is it complexity we can drop?

**My take.**

After each training iteration, AlphaGo Zero evaluates the newly trained neural network against the current best network. The candidate is promoted only if it wins at least 55% of the evaluation games; otherwise, the previous best model continues generating self-play data. This mechanism acts as a quality-control gate, preventing weaker networks from degrading the training process through poor self-play games.

It is important to note that this design changes in AlphaZero (Silver et al., 2018), where the evaluation gate is removed. The reason for this change should be discussed when comparing the two papers.

For a laptop-scale implementation such as FLIPHEX, the evaluation gate is probably unnecessary. Running evaluation matches after every training iteration increases computational cost and implementation complexity. Since training occurs sequentially on a single machine rather than on a large distributed system, simply continuing from the latest checkpoint is a reasonable engineering choice. If training later proves unstable, the gate can be introduced as an optional safeguard rather than as a mandatory component.

**Refined write-up.**

Correct. Concrete detail: the gate runs a **400-game** evaluation match and
promotes the candidate only on **> 55%** — a threshold set high enough to filter
noise, not just any edge. Its purpose is to guarantee that self-play data always
comes from the strongest network so far, so a single bad gradient update cannot
poison the data stream. Flag for §8 / synthesis **S2**: AlphaZero (2018) *drops*
this gate and trains one continuously-updated network — resolve *why* there. Your
laptop-scale reasoning is sound: skip the gate initially, keep it as an optional
safeguard if training proves unstable.

### 7.2 — Compute and simulation budget
**Prompt.** Extract the concrete numbers: MCTS simulations per move (~1600),
games generated, hardware (TPUs), training days. Then estimate the *ratio* to
FLIPHEX: ~1450 legal first-ply moves, 25-ply games, a single laptop GPU. What
sim-count per move is plausible for us, and does adr-005's "compact network"
assumption survive this comparison?

**My take.**

AlphaGo Zero performs approximately 1,600 MCTS simulations per move, generates millions of self-play games, trains for several days on large TPU clusters, and relies on computational resources that are far beyond what is available on consumer hardware. These numbers demonstrate that the reported performance depends not only on the learning algorithm but also on an enormous search budget.

FLIPHEX operates under very different constraints. Although its opening branching factor is large (approximately 1,450 legal first-ply actions), games are much shorter (around 25 plies instead of hundreds of moves in Go), and training is intended to run on a single laptop GPU. Under these conditions, performing 1,600 simulations per move would likely be impractical.

A search budget on the order of tens to a few hundred simulations per move appears substantially more realistic for a laptop-scale implementation. The exact value should be selected empirically by balancing playing strength against training time.

This comparison also supports ADR-005's decision to use a compact neural network. With a limited simulation budget, network evaluation becomes the dominant computational cost inside MCTS. A smaller network reduces inference latency, allowing more simulations within the same compute budget. Thus, the compact-network assumption is strengthened rather than weakened by the hardware constraints of the project.

**Refined write-up.**

Correct on every count, and your closing insight is the subtle one — worth
affirming strongly. Exact anchors to cite: **1,600 simulations/move** (~0.4 s
each), **25,000 self-play games per iteration**, training sampled from the most
recent **500,000** games; hardware is **4 TPUs** for the player plus 64 GPUs and
19 CPUs for optimisation; the two runs are **20-block / 3-day (4.9M games)** and
**40-block / 40-day (~29M games)**. The point you reached at the end is exactly
right and often missed: under a *small* simulation budget the per-node network
evaluation dominates MCTS cost, so a **compact network is strengthened, not
weakened** — a smaller net means lower inference latency means more simulations
per unit of compute. adr-005's compact-network bet survives cleanly. Two design
levers to carry into Phase 4: batch the leaf evaluations (AGZ evaluates in
mini-batches of 8 inside the search), and — with a net this small — CPU inference
may actually beat GPU once you count transfer overhead. A concrete laptop
starting point: ~**100–200 sims/move** and games in the thousands-to-tens-of-
thousands, tuned by the strength-vs-time trade-off you named.

---

## §8 — Domain knowledge, symmetry, and limitations

### 8.1 — Symmetry augmentation (the conflict to flag)
**Prompt.** AGZ exploits Go's 8-fold dihedral symmetry both to augment training
data and to average MCTS evaluations. **FLIPHEX's board has a trivial symmetry
group** ([board-geometry.md](docs/board-geometry.md)). State exactly what
capability FLIPHEX therefore *loses* (free 8× data augmentation, evaluation
averaging), and what that predicts about our sample-efficiency versus AGZ. This
is a genuine source-vs-project conflict — record it, do not smooth it over.

**My take.**

AlphaGo Zero exploits the eight symmetries of the Go board (the dihedral group D₄). Every board position can be rotated or reflected to produce seven equivalent states. The paper uses these symmetries in two ways: first, to augment the training set by generating additional equivalent examples; second, to average neural network evaluations across symmetric transformations during MCTS, reducing prediction variance.

FLIPHEX presents a genuine conflict with this design. According to the board geometry specification, its board has only the trivial symmetry group, meaning that non-identity rotations or reflections do not preserve the game's geometry. Consequently, neither symmetry-based data augmentation nor symmetry-based evaluation averaging can be applied.

The practical implication is a reduction in sample efficiency. AlphaGo Zero effectively extracts more supervised signal from every self-play position and obtains more stable value and policy estimates through symmetry averaging. FLIPHEX loses both advantages, so achieving comparable policy quality is likely to require more self-play games or additional training iterations. This is a fundamental consequence of the game's geometry rather than an implementation choice.

**Refined write-up.**

Correct, and this is the load-bearing conflict of the whole reading. Quantify it
so it bites: the 8-fold symmetry means each self-play position yields up to **8**
training examples, and each network evaluation is averaged over 8 orientations
(variance down by ≈ √8). FLIPHEX gets **1×** on both. Implication: to see each
distinct position-class as often, we need on the order of several times more
self-play games, and our per-position value/policy estimates are noisier. The
constructive flip side — and a genuine advantage Go did *not* have — is that
FLIPHEX has a tractable **exact solver** (Axis 1) to supply ground truth on small
variants, partly compensating for the lost sample-efficiency (synthesis **S3/S4**).
Record this in adr-005 as a known handicap, not a blocker.

### 8.2 — The authors' acknowledged limitations
**Prompt.** What does the paper itself concede (Go-specific choices, compute,
generality)? Which limitation is *load-bearing* for whether the AlphaZero recipe
transfers to a tiny original game like FLIPHEX at all?

**My take.**

Although AlphaGo Zero is presented as a general reinforcement learning framework, the paper acknowledges several practical limitations. The experiments are conducted exclusively on Go, they require massive computational resources, and they exploit domain-specific properties such as perfect information, deterministic dynamics, and board symmetries. Therefore, the paper demonstrates the method's effectiveness for Go rather than proving universal applicability.

Among these limitations, the most load-bearing for transferring the AlphaZero recipe to FLIPHEX is not computational scale but the assumptions about the game itself. AlphaGo Zero relies on a deterministic, perfect-information environment with fully known rules, allowing self-play, MCTS, and the value network to operate on complete game states. FLIPHEX satisfies these assumptions despite being much smaller than Go.

In contrast, computational scale primarily affects performance rather than correctness. A laptop implementation may converge more slowly or achieve a lower playing strength, but the learning algorithm itself remains applicable. Therefore, the strongest argument for transferring the AlphaZero methodology to FLIPHEX is that the underlying assumptions of the learning framework are preserved, even though the game's complexity and available compute differ substantially.

**Refined write-up.**

Correct, and a good place to close. State the transfer condition crisply: the
recipe transfers **iff** the environment is deterministic, perfect-information,
and cheap to simulate with known terminal + scoring rules. FLIPHEX satisfies all
three (fast engine, exact rules, no hidden state), so — as you argue — compute,
not applicability, is the only real risk. The single honest caveat to carry
forward: FLIPHEX does **not** inherit Go's symmetry advantage (§8.1), so
"transfers" does not mean "equally sample-efficient." That one asterisk is the
thread connecting this whole reading to Phase 4.

---

## Lessons Learned

_(filled at merge — what changed in how I think about Axis 2.)_

## Failed Attempts

_(filled at merge — revised assumptions, reading dead-ends.)_
