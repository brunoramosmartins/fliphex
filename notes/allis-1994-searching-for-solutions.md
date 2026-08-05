# Reading companion — Allis 1994, Searching for Solutions in Games and AI

**Citation.** Allis, L. V. (1994). *Searching for Solutions in Games and
Artificial Intelligence.* PhD thesis, University of Limburg (Maastricht), the
Netherlands. Read from the Maastricht CRIS open-access copy
(`refs/allis-1994-searching-for-solutions.pdf`).

**Why this source, and where it sits.** This is the **Axis 3 (complexity)**
foundation and part of the Axis 1 (solver) grounding. It gives (a) the standard
vocabulary for *what it means to solve a game* (ultra-weak / weak / strong), (b)
the two complexity measures — **state-space complexity** and **game-tree
complexity** — and the canonical **comparison table** across games that H4 needs,
and (c) **proof-number search**, an AND/OR solving technique relevant to adr-004.
Read after the AlphaZero papers (Axis 2) — this rounds out the *exact-solving*
side. **Directed reading:** the complexity framework and pn-search, not the
game-specific case studies in full.

**Cross-refs this reading feeds:**
- **H4** in [research.md](docs/research.md) — the complexity comparison; Allis is
  the reference for the metrics *and* the competitor numbers (Reversi, Hex,
  Connect-Four). Note H4 is already flagged as possibly-false against the
  corrected FLIPHEX bound (~4.9×10¹⁷); this reading sharpens the comparison.
- [adr-004](docs/adr/adr-004-solver-approach.md) — the solve-ability taxonomy and
  proof-number search as a possible complement to alpha-beta.
- `complexity/` package (Phase 6): `state_space.py`, `game_tree.py`,
  `comparison.py` implement Allis's measures directly.
- [exercises/ex05_complexity_analysis.md](exercises/ex05_complexity_analysis.md)
  — the state-space / game-tree derivations land here.
- research.md §"Amendments" — the corrected FLIPHEX state-space bound.

**Legend.** Prompts marked 🔄 need synthesis with another source — answer them in
[phase2-synthesis.md](notes/phase2-synthesis.md) (esp. **S4**: exact solving vs
learned play), not here.

**Reading material** (extracted via `paper-study`, gitignored under
`notes/sources/`). Chapter mapping (the thesis chapters, not this note's §):
[manifest](sources/allis-1994-searching-for-solutions/manifest.json) ·
[§6 Introduction](sources/allis-1994-searching-for-solutions/sections/06-introduction.md)
(the "solved" definitions → this note's §1) ·
[§11 "Which Games Will Survive?"](sources/allis-1994-searching-for-solutions/sections/11-which-games-will-survive.md)
+ [Nível-1 companion](sources/allis-1994-searching-for-solutions/study/11-which-games-will-survive.md)
(complexity + comparison + taxonomy → this note's §2/§3/§5/§6) ·
[§7 Proof-Number Search](sources/allis-1994-searching-for-solutions/sections/07-proof-number-search.md)
(→ this note's §4). Note: the Figure 6.1 complexity plot and the exponents in the
comparison numbers are images/superscripts and did **not** extract — canonical
published values are transcribed in the §11 companion.

---

## §1 — What "solving a game" means

### 1.1 — Ultra-weakly, weakly, strongly solved
**Prompt.** Write Allis's three definitions exactly. Which one requires only the
game-theoretic *value* of the initial position, which adds a *strategy* from the
start, and which demands the value of *every* legal position? Predict before
reading: which term matches "we know who wins 3×3 FLIPHEX with perfect play"?

**My take.**

Allis distinguishes three increasingly stronger notions of solving a deterministic, perfect-information game.

**Ultra-weakly solved**

A game is *ultra-weakly solved* when only the game-theoretic value of the initial position is known. In other words, we know whether perfect play from the starting position leads to a win, loss, or draw, but no explicit strategy is required.

**Weakly solved**

A game is *weakly solved* when the game-theoretic value of the initial position is known and an optimal strategy exists from the starting position. A weak solution therefore tells us both the outcome and how to achieve it from the beginning of the game.

**Strongly solved**

A game is *strongly solved* when the game-theoretic value is known for every legal position, together with an optimal strategy from each of those positions. This guarantees perfect play even if one or both players have previously deviated from the optimal line.

The three notions can be summarized as follows:

| Solution level | What is known? |
| --- | --- |
| Ultra-weak | Only the game-theoretic value of the initial position. |
| Weak | The value of the initial position and an optimal strategy from the start. |
| Strong | The value and optimal strategy for every legal position. |

The statement *"we know who wins 3×3 FLIPHEX with perfect play"* most naturally corresponds to an **ultra-weak solution**, since it only states the game-theoretic outcome of the initial position. It becomes a **weak solution** if an explicit winning strategy from the initial board is also known, and a **strong solution** only if every legal board position has been analyzed and solved.

**Refined write-up.**

Allis's three levels are nested by *how much is known*. **Ultra-weak** = the game-theoretic value of the *initial* position only (who wins under perfect play), with no strategy. **Weak** = that value *plus* a strategy that achieves it from the start. **Strong** = the value and an optimal move for *every* legal position, so play stays perfect even after a mistake. "We know who wins 3×3 FLIPHEX" is bare **ultra-weak**; add a constructive line from the opening and it is **weak**; solve every 3×3 position and it is **strong**. The FLIPHEX-specific point: unlike Hex — ultra-weakly solved by strategy-stealing — FLIPHEX's Z/2 mirror *preserves the mover* (adr-008), so there is no existence shortcut. Its who-wins question can only be answered by a **constructive** weak or strong solve, never by an argument.

### 1.2 — Which target does the FLIPHEX solver claim?
**Prompt.** Map each Phase 3 deliverable to a term: the exhaustive 3×3 solve, the
retrograde endgame database on 5×5, and the alpha-beta agent that "plays
optimally on solved variants." Which are weak, which are strong, and where does
the endgame DB sit? (This wording should end up in adr-004 and the Phase 3 note.)

**My take.**

The Phase 3 deliverables target different notions of solving as defined by Allis.

The **exhaustive 3×3 solver** aims for a **strong solution**. By exhaustively enumerating every legal position and determining its game-theoretic value together with the optimal move, it provides perfect play from any reachable state.

The **5×5 retrograde endgame database** is also a **strong solution**, but only over a restricted subspace of the game. Every position contained in the database is solved exactly, allowing optimal play whenever the search reaches one of those positions. It is therefore a *partial strong solution* rather than a solution of the complete game.

The **alpha-beta agent** is not itself a solution to the game. Instead, it is a search algorithm capable of exploiting solved information. When applied to a solved variant such as 3×3, it can reproduce the optimal strategy and therefore play perfectly. On unsolved variants, however, it performs exact search only within its search horizon and should be regarded as an optimal decision procedure rather than as a weak or strong solution.

Consequently, the project claims a **strong solution** for the fully solved 3×3 variant, a **partial strong solution** through retrograde analysis for selected 5×5 endgames, and an **exact search engine** that exploits these solved components rather than solving the general game itself.

**Refined write-up.**

Mapping the Phase 3 deliverables (adr-004, Phase 2 amendment): the exhaustive **3×3** solve is a *strong* solution but functions as a **calibration fixture** — it validates engine and search, not strategy. The **4×4** solve is now the *primary* exact target (~9 × 10¹⁰ reachable states with a reduced deck); it is the *strong* solution that carries the H1/H2 verdicts on a strategically non-trivial board. The **5×5 retrograde endgame database** is a *partial strong* solution — exact only over the `k ≤ 5` empty-cell slice. The **alpha-beta agent** is not itself a solution: it is the exact-search *engine* that consumes solved information (the endgame DB as a perfect evaluator) and, decisively, the **ground-truth oracle** against which the AlphaZero agent is checked (H3). It is not a weaker prototype of the learned agent but its *independent* verifier — the two axes must fail differently.

---

## §2 — State-space complexity

### 2.1 — Definition and how to count it
**Prompt.** Allis's state-space complexity = the number of *legal* positions
reachable from the initial position. How does he actually estimate it when exact
enumeration is infeasible (bounds, sampling)? What is the difference between the
*naïve* count and the *reachable* count, and why does it matter?

**My take.**

Allis defines **state-space complexity** as the number of **legal positions reachable from the initial position**. The emphasis on *reachable* is essential: many board configurations that satisfy the local rules of a game can never arise through a valid sequence of moves and therefore do not belong to the game's state space.

For small games, the state-space complexity can be obtained by exhaustive enumeration of all reachable positions. For larger games, however, exact enumeration quickly becomes computationally infeasible. In these cases, Allis advocates estimating the state space using mathematical upper and lower bounds, combinatorial analysis, and, when appropriate, statistical sampling techniques.

A naïve count simply considers every possible assignment of pieces to board locations while enforcing only basic occupancy constraints. This approach generally overestimates the true complexity because it ignores move legality, game dynamics, and unreachable configurations.

The reachable count instead includes only positions that can actually be generated from the initial position by a legal sequence of moves. This measure more accurately reflects the effective search space faced by a solver and provides a meaningful basis for comparing the complexity of different games.

Consequently, state-space complexity measures the size of the game's reachable configuration space rather than the total number of syntactically valid board arrangements.

**Refined write-up.**

State-space complexity counts **reachable legal** positions, not syntactically valid ones — and the gap is large, because move dynamics make most locally-valid boards unreachable. Small games: enumerate directly. Large games: bound from above, tighten with game-specific constraints, then estimate the *legal fraction* by Monte-Carlo — Allis's tic-tac-toe example samples the 3⁹ superset and recovers the true 5,478. The reachable count is what a solver actually faces; the naïve count systematically overstates it.

### 2.2 — FLIPHEX's number against the framework
**Prompt.** Our corrected reachable bound is ~4.9×10¹⁷ (adr-003 inertness drops
the 6²⁵ orientation factor; see research.md §Amendments). Is that a *state-space
complexity* in Allis's sense, or just an upper bound? What would Allis do to
tighten it, and does our number already use those ideas (turn-parity,
deck-composition constraints)?

**My take.**

The corrected FLIPHEX estimate of approximately **4.9×10¹⁷** should be interpreted as an **upper bound** on the state-space complexity rather than the state-space complexity itself.

According to Allis, the state-space complexity is the exact number of legal positions reachable from the initial position. Since exhaustive enumeration of all reachable FLIPHEX positions has not been performed, the exact value remains unknown. Our estimate therefore bounds the reachable state space instead of measuring it exactly.

The bound is nevertheless considerably tighter than a naïve combinatorial count because it incorporates game-specific constraints. In particular, it removes impossible tile orientations through the inertness result (ADR-003) and accounts for structural constraints such as turn parity and deck composition, thereby excluding large classes of impossible configurations.

Following Allis's methodology, the next step toward a more accurate estimate would be to introduce additional reachability constraints or, ideally, enumerate the reachable positions directly for tractable board sizes. Every valid constraint that eliminates unreachable configurations narrows the gap between the upper bound and the true state-space complexity.

Therefore, the current FLIPHEX estimate should be regarded as a progressively refined upper bound obtained by incorporating domain knowledge, rather than as the exact state-space complexity defined by Allis.

**Refined write-up.**

FLIPHEX's ~4.9 × 10¹⁷ is an **upper bound**, not the state-space complexity in Allis's exact sense. It already folds in domain constraints: inertness drops the `6²⁵` orientation factor (adr-003); turn-parity fixes the P1/P2 ply split; deck composition caps the two hand factors. What it does *not* do is subtract flip-unreachable colourings — the `2^t` term treats *every* 2-colouring of the occupied cells as reachable, which the flip dynamics do not guarantee. Allis's own next step would be exactly that subtraction: a Monte-Carlo estimate of the legal fraction. That is the open refinement earmarked for `complexity/state_space.py` (Phase 6), and it would move the number *down*, never up.

---

## §3 — Game-tree complexity

### 3.1 — Definition and estimation (b^d)
**Prompt.** Game-tree complexity = the number of leaf nodes of the *solution
search tree*, usually estimated as `b^d` with `b` = average branching factor and
`d` = game length. How does Allis obtain `b` and `d` in practice? For FLIPHEX,
`d = 25` (fixed!) — how does a fixed game length change the estimate versus games
where `d` varies?

**My take.**

Allis defines **game-tree complexity** as the number of leaf nodes in the solution search tree. Since exact enumeration is infeasible for most games, this quantity is typically approximated as \(b^d\), where \(b\) is the average branching factor and \(d\) is the average game length.

In practice, the average branching factor is obtained by analyzing representative games or by estimating the average number of legal moves available across the search tree. The game length is estimated from complete games, either by theoretical analysis or empirical observation, depending on the game.

Unlike state-space complexity, game-tree complexity measures the size of the search required to solve the game rather than the number of distinct reachable positions.

For FLIPHEX, the game length is fixed at **25 plies** on a 5×5 board because exactly one tile is placed per turn until the board is full. This removes one source of uncertainty from the estimate: the depth of the search tree is known exactly, leaving the average branching factor as the primary variable determining the game-tree complexity.

A fixed game length also makes comparisons across board sizes more straightforward, since changes in complexity arise primarily from variations in the branching factor rather than from fluctuations in game duration.

**Refined write-up.**

Game-tree complexity = leaves of the solution search tree, estimated as `bᵈ`, with `b` and `d` read off tournament games. FLIPHEX is unusual: `d = 25` is *fixed* (one tile per ply until the board fills), so all uncertainty leaves the depth and the estimate reduces to characterising `b` — which starts at **1450** and collapses to **1** at ply 25 (adr-004). Fixed depth also makes cross-board comparison clean: from 3×3 to 5×5, complexity moves with `b` alone, not with fluctuating game length.

### 3.2 — The comparison table (H4's reference data) 🔄
**Prompt.** Copy the rows Allis gives for the games H4 names or their neighbours:
Reversi/Othello, Connect-Four, and (if present) any Hex figures. Record both
state-space and game-tree complexity. **Do not import them as ours** — they are
reference points. Where does FLIPHEX's ~4.9×10¹⁷ fall relative to Reversi? (H4 as
worded may already be false — this is the data that decides it.)

**My take.**

Allis reports the following reference values for games closely related to H4:

| Game | State-space complexity | Game-tree complexity |
| --- | ---: | ---: |
| Connect-Four | ≈ 4.5 × 10¹² | ≈ 1 × 10²¹ |
| Reversi (Othello) | ≈ 1 × 10²⁸ | ≈ 1 × 10⁵⁸ |

No canonical Hex figures are provided in the comparison table used in this reading, so no Hex values are recorded here.

These numbers are reference points taken directly from Allis and should not be interpreted as measurements of FLIPHEX.

Using the current corrected estimate, FLIPHEX has a reachable state-space upper bound of approximately **4.9 × 10¹⁷**. This places it roughly **five orders of magnitude larger than Connect-Four** (≈10⁵ times) but still **about ten orders of magnitude smaller than Reversi** in terms of state-space complexity.

Therefore, the current evidence does **not** support claiming that FLIPHEX has a larger state-space complexity than Reversi. Whether H4 remains valid depends on its precise wording and should be revisited during the Phase 2 synthesis.

**Refined write-up.**

Reference points (Allis's, not ours): Connect-Four ≈ 10¹³ state / ≈ 10²¹ tree; Othello 8×8 ≈ 10²⁸ / ≈ 10⁵⁸. FLIPHEX's ~4.9 × 10¹⁷ upper bound sits well *above* Connect-Four and ~10 orders *below* Othello — and below Reversi 6×6's commonly cited ~10²⁰. So **H4 as worded ("comparable to Reversi 6×6") is likely false**: FLIPHEX looks smaller. The honest reformulation is a *placement prediction* — "lands near 10¹⁸, between Connect-Four and Othello" — not equivalence to a named game (research.md §Amendments). Reversi 6×6 and Hex are absent from Allis's table and need a second source before H4 can name them.

---

## §4 — Proof-number search (solver technique — directed)

### 4.1 — The idea, and when it beats alpha-beta
**Prompt.** Proof-number search is a best-first AND/OR search that expands the
node most likely to (dis)prove the root. What are *proof number* and *disproof
number*, and why does pn-search shine on trees with non-uniform branching and
clear terminal/goal structure? Would FLIPHEX (fixed depth 25, flip-driven
terminal-by-fullness) suit it, or is alpha-beta + TT (adr-004) the better fit?
This is an adr-004 input, not a commitment.

**My take.**

Proof-number search (PNS) is a best-first search algorithm for AND/OR trees designed to determine the game-theoretic value of a position. Rather than exploring the tree uniformly, it repeatedly expands the node that appears most promising for proving or disproving the value of the root.

Each node is assigned two measures:

- The **proof number (pn)** estimates the minimum amount of work required to prove that the node is a win for the player to move.
- The **disproof number (dn)** estimates the minimum amount of work required to refute that claim.

These values are propagated through the AND/OR tree according to the logical structure of the game, allowing the search to focus computational effort on the most critical parts of the tree.

Compared with alpha-beta search, PNS is particularly effective when the search tree is highly irregular, the branching factor varies substantially across positions, and terminal or goal states provide clear evidence for proving or disproving a position. Under these conditions, best-first expansion can avoid exploring large portions of the tree that alpha-beta might still need to visit.

FLIPHEX exhibits several characteristics that make PNS worth considering. The game has a fixed maximum depth of 25 plies and a well-defined terminal condition when the board becomes full. However, whether these properties outweigh the advantages of alpha-beta with transposition tables depends on the actual structure of the search space, the prevalence of transpositions, and the effectiveness of move ordering. At this stage, PNS should be regarded as a plausible alternative to investigate rather than a committed design choice.

**Refined write-up.**

Proof-number search is best-first AND/OR search on two counters — the **proof number** (minimum work to prove a win) and the **disproof number** (minimum to refute it) — always expanding the most-proving node. Its edge appears where the tree is irregular *and there is a goal to prove*: sudden-death games such as qubic and go-moku, where a forced threat sequence is the thing being demonstrated. FLIPHEX is diverging + fixed-termination with **no** sudden-death pattern (Allis's Othello class), so pn-search loses that structural advantage; alpha-beta + TT + shallow retrograde (adr-004) is the better fit. **Decision recorded:** this reading *confirms* adr-004 rather than reopening it — pn-search stays a parked alternative, revived only if the paper track activates. (adr-004 Phase 2 amendment.)

---

## §5 — Case study: weakly solving a real game

### 5.1 — Connect-Four, and the FLIPHEX analogue
**Prompt.** Allis weakly solved Connect-Four. What made it tractable (knowledge
rules, search, or both), and what was the game-theoretic result? What is the
transferable lesson for *weakly solving* small FLIPHEX variants — is brute-force
search enough, or did Allis need game-specific knowledge that FLIPHEX lacks?

**My take.**

Allis weakly solved Connect-Four by combining powerful search techniques with substantial game-specific knowledge. The solution was not obtained through brute-force search alone. Instead, knowledge rules were used to recognize strategically significant positions, reduce the effective search space, and guide the solver toward promising lines of play.

The search algorithm and the domain knowledge complemented each other. Search provided completeness, while the knowledge rules greatly improved efficiency by avoiding unnecessary exploration. This combination made the problem computationally tractable despite the enormous theoretical game-tree complexity.

The game-theoretic result was that **the first player has a forced win under perfect play**.

For FLIPHEX, the main lesson is that weakly solving even relatively small variants may require more than exhaustive search. If the search space remains small enough, brute-force enumeration may be sufficient. However, as board size increases, incorporating game-specific knowledge, pruning techniques, or other domain-dependent optimizations may become essential to achieve tractability.

Therefore, Allis's work suggests that successful game solving depends not only on search algorithms but also on exploiting the structural properties of the game itself.

**Refined write-up.**

Allis weakly solved Connect-Four — a **first-player win** — and crucially *not* by brute force alone: knowledge rules (the program VICTOR) carried much of it, and later pn-search cut the cost to under 25 CPU-hours. The lesson for FLIPHEX: brute force suffices only while the state space stays small (3×3, 4×4). FLIPHEX has *no* human-derived knowledge rules of Connect-Four's kind, so pushing the exact solve past 4×4 would demand domain knowledge we don't possess — which is precisely why the plan places strong 5×5 play on the **learned** axis (AlphaZero), not the solver. The solver owns the small boards where enumeration is honest; the learner owns the full game.

---

## §6 — Limitations and caveats of the numbers

### 6.1 — How much to trust a 1994 estimate
**Prompt.** Allis's complexities are *estimates* (bounds and heuristics), and the
thesis is from 1994 — several listed games have since been solved or re-measured.
Which numbers are firm and which are order-of-magnitude guesses? What does this
imply for how H4 should state its verdict (a precise ranking vs a
"FLIPHEX lands near here" band)?

**My take.**

The complexity values reported by Allis should primarily be interpreted as **order-of-magnitude estimates** rather than exact measurements. For many games, exact state-space or game-tree complexities were computationally infeasible to determine in 1994, so the reported values were derived from combinatorial arguments, upper and lower bounds, and heuristic estimates.

The definitions of **state-space complexity**, **game-tree complexity**, and the taxonomy of solved games remain fundamental contributions of the thesis. In contrast, some numerical values in the comparison table should be viewed as historical reference points, since subsequent research has refined the estimates or even solved games that were still open at the time.

Consequently, the comparison table is most reliable for identifying relative scales of complexity rather than establishing precise numerical rankings between games.

For H4, this implies that the conclusion should avoid claiming an exact ordering unless supported by rigorous analysis. Instead, the hypothesis should position FLIPHEX within the appropriate order of magnitude and discuss its complexity relative to established reference games while acknowledging the uncertainty inherent in both the historical estimates and the current FLIPHEX upper bound.

**Refined write-up.**

Allis's numbers are order-of-magnitude estimates (1994, before several of the listed games were solved), while the *definitions* — state-space complexity, game-tree complexity, and the solved taxonomy — are the durable contribution. H4 should therefore return a **band** verdict: "FLIPHEX lands near 10¹⁸, above Connect-Four and below Othello," not a precise ranking, and it should state the uncertainty in *both* the historical figures and our own upper bound. A ranking that hinges on one order of magnitude is not one the data can support.

---

## Lessons Learned

This reading fundamentally changed how I think about game solving. I now distinguish between **ultra-weak**, **weak**, and **strong** solutions and recognize that these terms describe progressively stronger levels of knowledge about a game rather than differences in playing strength.

I also learned that **state-space complexity** and **game-tree complexity** capture different aspects of computational difficulty. The former measures the number of reachable legal positions, whereas the latter estimates the size of the search required to solve the game. Before this reading, I tended to treat both as generic measures of "game complexity."

Another important realization was the distinction between a **combinatorial count** and the **state-space complexity** defined by Allis. The current FLIPHEX estimate (~4.9 × 10¹⁷) should be interpreted as a progressively refined **upper bound**, not as the exact reachable state space.

The Connect-Four case study also demonstrated that successful game solving is not purely a matter of computational power. Domain-specific **knowledge rules** can dramatically reduce the effective search space and are often as important as the search algorithm itself.

Finally, I came to view Proof-Number Search not simply as an alternative to alpha-beta, but as a fundamentally different approach aimed at constructing mathematical proofs efficiently. This broadened my perspective on the design space of exact game solvers.

## Failed Attempts

Initially, I interpreted the current FLIPHEX state-space estimate as if it were the game's actual state-space complexity. After studying Allis, I realized that it is only an **upper bound**, obtained by incorporating structural constraints while still potentially including unreachable positions.

I also assumed that solving a game was primarily a matter of exhaustive search and sufficient computational resources. The Connect-Four case study showed that this view is incomplete: domain-specific knowledge can be essential for making the search computationally tractable.

Another assumption I revised was treating Allis's comparison table as a collection of exact values. The thesis makes it clear that many of the reported complexities are order-of-magnitude estimates intended for comparison rather than precise measurements.

Finally, I recognized that architectural decisions for the FLIPHEX solver—such as choosing between alpha-beta, Proof-Number Search, or other approaches—should not be made while reading individual papers. These decisions should instead be revisited after completing the literature review and synthesizing the evidence across all research axes.
