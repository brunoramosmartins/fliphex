# Reading companion — Russell & Norvig, AIMA §6: Adversarial Search and Games

**Citation.** Russell, S. & Norvig, P. (2021). *Artificial Intelligence: A
Modern Approach*, 4th ed. (Global Edition), **Chapter 6 — Adversarial Search and
Games**, pp. 192–225. Pearson. Read from the sliced local copy
(`refs/russell-norvig-ch6-adversarial-search.pdf`, 32 pp).

> **Edition note.** In the 3rd edition (and its PT-BR translation) adversarial
> search is **Chapter 5, "Busca Competitiva"**; the 4th edition renumbered it to
> **Chapter 6** (Chapter 5 there is Constraint Satisfaction). Same material,
> plus a new §6.4 on Monte Carlo Tree Search that did not exist in the 3rd ed.

**Why this source, and where it sits.** This is the **textbook foundation for
Axis 1** — the vocabulary and algorithms behind [adr-004](docs/adr/adr-004-solver-approach.md):
minimax, the game-theoretic value, **alpha-beta pruning** with move ordering and
transposition tables, and — critically — **Monte Carlo Tree Search** (§6.4),
which is the bridge to Axis 2's AlphaZero ([adr-005](docs/adr/adr-005-alphazero-scope-and-network.md)).
Read it **after** Silver 2018 (you already have PUCT/MCTS in mind, so §6.4 reads
as "the generic MCTS that AlphaZero specialises") and alongside Allis 1994 (which
gave the *solving* taxonomy; this gives the *search* that realises it). It closes
the exact-solving loop the Allis note opened.

**Directed reading.** The FLIPHEX-relevant core is **§6.1–6.4** and **§6.7**.
FLIPHEX is deterministic and perfect-information ([adr-001](docs/adr/adr-001-perfect-information-scope.md)),
so **§6.5 (Stochastic Games)** and **§6.6 (Partially Observable Games)** are
*out of scope* — skim for one paragraph each and move on. Do not write My-takes
for 6.5/6.6 unless something jumps out.

**Cross-refs this reading feeds:**
- [adr-004](docs/adr/adr-004-solver-approach.md) — minimax, alpha-beta + TT, move
  ordering. This chapter is the primary reference behind the whole decision; any
  slip in the ADR's search vocabulary gets corrected here.
- [adr-005](docs/adr/adr-005-alphazero-scope-and-network.md) — §6.4 MCTS is what
  AlphaZero's PUCT search is a variant of.
- [adr-001](docs/adr/adr-001-perfect-information-scope.md) — the reason §6.5/§6.6
  are out of scope.
- [research.md](docs/research.md) — H1 (game-theoretic value / first-player win),
  H3 (solver as the oracle the learned agent is checked against).
- [allis-1994 note](notes/allis-1994-searching-for-solutions.md) — the "solved"
  taxonomy this chapter's algorithms *produce*.
- [silver-2018 note](notes/silver-2018-alphazero.md) — PUCT as a specialisation
  of §6.4's UCT.
- `exercises/` — the alpha-beta move-ordering and TT derivations land here.

**Legend.** Prompts marked 🔄 need synthesis with another source — answer them in
[phase2-synthesis.md](notes/phase2-synthesis.md) (esp. **S4**: exact solving vs
learned play), not here.

**Reading material** (extracted via `paper-study`, gitignored under
`notes/sources/`).
[manifest](sources/russell-norvig-ch6-adversarial-search/manifest.json) ·
sections under
[`sources/russell-norvig-ch6-adversarial-search/sections/`](sources/russell-norvig-ch6-adversarial-search/sections/).
**Section ↔ prompt map** (the book's 4th-ed numbering differs from this note's §):

| This note's prompt | Extracted section(s) |
|---|---|
| §6.1 (formal setup, zero-sum, ply) | §1 `6.1.1 Two-player zero-sum games`; ply also in §2/§3 |
| §6.2 (minimax) | §2 `6.2`, §3 `6.2.1 minimax algorithm` |
| §6.3 (alpha-beta core) | §5 `6.2.3 Alpha–Beta`, §6 `6.2.4 Move ordering`, §7–8 `6.3/6.3.1 Eval`, §9 `6.3.2 Cutting off`, §10 `6.3.3 Forward pruning`, §11 `6.3.4 Search vs lookup` |
| §6.4 (MCTS) 🔄 | §12 `6.4 Monte Carlo Tree Search` |
| §6.5/§6.6 (out of scope) | §13–18 — skim only |
| §6.7 (limitations) | §19 `6.7 Limitations`, §20 `Summary`, §21 `Bibliographical Notes` (the checkers/AlphaGo citations feed prompt 6.7.2) |

> Note: alpha-beta is **§6.2.3** and move ordering **§6.2.4** in this edition
> (both under 6.2), not a separate 6.3 — the topics still match this note's §6.3.

---

## §6.1 — Game theory (the formal setup)

### 6.1.1 — The formal definition of a game, matched to FLIPHEX
**Prompt.** Write R&N's formal components of a game (S₀, TO-MOVE, ACTIONS,
RESULT, IS-TERMINAL, UTILITY). Map each onto FLIPHEX's engine: what are FLIPHEX's
`ACTIONS(s)` (recall 1450 on ply 1), its `RESULT` (place + one-shot flip), its
`IS-TERMINAL` (board full at ply 25), its `UTILITY` (±1, since draws are
impossible)? Predict before reading: does R&N define **zero-sum** and
**game-theoretic value** with the same words the Allis note used for "solved"?

**My take.**

The chapter models a deterministic, perfect-information, two-player game as a search problem defined by a small set of formal components:

- **Initial state (S₀):** the starting position from which play begins.
- **TO-MOVE(s):** a function specifying which player acts in state *s*.
- **ACTIONS(s):** the set of legal moves available in state *s*.
- **RESULT(s, a):** the successor state obtained after applying action *a* to state *s*.
- **IS-TERMINAL(s):** a predicate indicating whether no further actions are available because the game has ended.
- **UTILITY(s, p):** a numerical payoff assigned to terminal states, measured from the perspective of player *p*.

Russell and Norvig explicitly frame adversarial search around **two-player, deterministic, zero-sum games with perfect information**. Under these assumptions, one player's gain is exactly the other player's loss, allowing the game to be represented by a single utility function rather than independent objectives.

For FLIPHEX, the mapping is direct:

- **S₀:** the empty 5×5 board before any move.
- **TO-MOVE(s):** alternates deterministically between the two players.
- **ACTIONS(s):** every legal placement on an empty cell together with its associated one-shot flip decision. Consequently, the branching factor is state-dependent and reaches approximately 1,450 legal actions at the initial position.
- **RESULT(s, a):** produces the next board position by placing the chosen piece and immediately applying the selected one-shot flip, after which the resulting state is fixed.
- **IS-TERMINAL(s):** true once all 25 board positions have been filled, since no further legal actions remain.
- **UTILITY(s, p):** a terminal payoff of +1 for a win and −1 for a loss. Because draws are impossible under the game's rules, no zero-valued outcome is required.

The chapter defines **zero-sum** in essentially the same sense used in Allis's work: the interests of the two players are exactly opposed, so maximizing one player's utility necessarily minimizes the other's. However, the emphasis differs. Russell and Norvig use this property to justify the minimax formulation of adversarial search, whereas Allis employs the same game-theoretic assumptions to define what it means for a game to be *solved* and to characterize the game-theoretic value of the initial position. Thus, the underlying mathematical model is consistent across both sources, although their objectives differ: search versus solution.

**Refined write-up.**

The six components and the search-vs-solution reading are right. One mapping is
wrong, and it is the load-bearing one.

**`ACTIONS(s)` contains no flip decision.** You wrote "every legal placement on
an empty cell together with its associated one-shot flip decision." There is no
flip decision in FLIPHEX. An action is exactly a triple **(cell, tile, rotation)**;
the arrows then fire *deterministically* on placement ([adr-003](docs/adr/adr-003-piece-representation.md),
[adr-006](docs/adr/adr-006-no-chain-reaction.md)). That is precisely where the
1450 comes from: 25 cells × 58 distinct (tile, rotation) pairs — not 25 × 58 × 2.
The experiment you described earlier — placing a tile far from the others so that
nothing flips — is a *placement* choice, not a flip choice: you steer the flips by
choosing **where and at what rotation**, never by opting out. This matters beyond
bookkeeping. If a flip were a free choice, it would sit in `ACTIONS`; because it
is a consequence, it sits in `RESULT`, and `RESULT` stays a total deterministic
function — which is the precondition for both the Zobrist TT (§6.3.2) and the
retrograde databases (§6.3.3).

Two smaller precisions. (1) R&N's `UTILITY(s, p)` is indexed by player, and
zero-sum is the *statement* `UTILITY(s, MAX) = −UTILITY(s, MIN)`; that identity is
what licenses collapsing two objectives into one minimax recursion. (2) The state
FLIPHEX must carry is not only the board — it is (colouring, both hands), because
flips detach a cell's colour from whoever placed it. R&N's `S₀`/`RESULT` covers
this implicitly, and it is exactly the term that pushes the reachable bound from
3²⁵ ≈ 8.5 × 10¹¹ up to 4.9 × 10¹⁷ ([research.md](docs/research.md)).

Your prediction was half-right in an interesting way. R&N and Allis share the
model (deterministic, perfect-information, zero-sum) and R&N's minimax value *is*
Allis's game-theoretic value. But R&N have **no ultra-weak / weak / strong
vocabulary at all** — that taxonomy is Allis's contribution and does not appear in
this chapter. So the two sources are not redundant: R&N supply the algorithm,
Allis supplies the standard by which its output is graded. That division is worth
keeping explicit when H1's verdict is finally worded.

### 6.1.2 — Ply, and the fixed-depth peculiarity
**Prompt.** R&N define *ply* and discuss game length. FLIPHEX has a **fixed**
depth of 25. Which of the chapter's later complications (iterative deepening,
horizon effects, quiescence) are *dissolved* by a fixed, shallow depth, and which
still bite? Note the ones to raise in the adr-004 context.

**My take.**

I understand *ply* as a single move made by one player. Consequently, the depth of a game tree is naturally measured in plies rather than complete turns. Russell and Norvig emphasize this distinction because search algorithms reason about individual decision points, regardless of which player is to move.

For FLIPHEX, the game has a fixed maximum depth of 25 plies because exactly one board position is filled on each move and the game ends when the 5×5 board is full. Unlike games such as chess or Go, the search depth is therefore known a priori and does not vary across games.

This fixed and relatively shallow depth eliminates some of the challenges that motivate approximation techniques in larger games. In particular, iterative deepening is no longer required to progressively approach the true game-theoretic value simply because the full game tree exceeds the search horizon; if sufficient computational resources are available, the complete game can, in principle, be searched directly. Likewise, classical horizon effects arising solely from arbitrary depth cutoffs disappear when the search reaches the true terminal states rather than relying on truncated evaluation. For the same reason, quiescence search—which extends unstable leaf positions beyond a cutoff to avoid misleading evaluations—is not inherently necessary in an exact search of the complete 25-ply game.

However, a fixed depth does not eliminate the combinatorial explosion caused by the branching factor. With approximately 1,450 legal actions at the initial position, exhaustive minimax remains computationally infeasible despite the shallow depth. Therefore, techniques that reduce the effective search effort—particularly alpha-beta pruning, high-quality move ordering, and transposition tables—remain essential. These techniques address the width of the search tree rather than its depth.

In the context of ADR-004, I therefore distinguish between depth-management techniques and search-efficiency techniques. The former become largely unnecessary when performing complete search over a fixed-depth game, whereas the latter remain central because the dominant challenge is the enormous branching factor rather than an unbounded search horizon.

**Refined write-up.**

The depth-vs-width framing is the right axis, and "FLIPHEX is a width problem, not
a depth problem" is the sentence to keep. Three corrections, one of which reverses
your conclusion.

**Iterative deepening is not dissolved — it is repurposed, and R&N say so in this
very chapter.** You treated ID as a device for approaching the game value when the
tree exceeds the horizon. That is its §3 role. In §6.2.4 R&N give it a second,
independent job: *"it could come from previous exploration of the current move
through a process of iterative deepening. First, search one ply deep and record
the ranking of moves based on their evaluations. Then search one ply deeper, using
the previous ranking to inform move ordering… The increased search time from
iterative deepening can be more than made up from better move ordering."* So ID is
the standard *engine* of move ordering, and by §6.3.1 move ordering is the whole
game. On a fixed-depth game ID loses its time-management justification and keeps
its ordering justification entirely. adr-004 lists "iterative deepening and move
ordering" side by side; after this reading they should be listed as *one*
mechanism, not two.

**Horizon effects are dissolved only where the search is complete.** True for the
3×3/4×4 exact solves. But adr-004 part 2 is explicitly a *depth-limited* alpha-beta
agent on the full 5×5 — there the search never reaches ply 25, so horizon effects
bite at full strength. Your paragraph reads as though the fixed depth protects the
whole project; it protects exactly the part that was never at risk.

**Quiescence is the one that should worry you.** The standard fix is to extend
search until the position is "quiet". FLIPHEX has no quiet positions: *every*
placement fires arrows, so the cell count can swing on every single ply, right up
to ply 25. There is no fixed point for a quiescence extension to terminate at.
That is the Othello profile again (Allis's fixed-termination class), and it says
the depth-limited 5×5 agent's cut-off evaluation is *structurally* unreliable, not
merely untuned. Worth raising against adr-004 part 2 as an open design item — and
it is a further argument for the endgame databases, which are the only way to make
the last plies exact instead of guessed.

---

## §6.2 — Optimal decisions in games (minimax)

### 6.2.1 — The minimax value and algorithm
**Prompt.** State the `MINIMAX(s)` recurrence exactly (the max/min alternation
over UTILITY at terminals). This *is* the game-theoretic value — connect it to
the Allis note's "who wins with perfect play" (H1). For FLIPHEX 3×3/4×4, minimax
to the fixed depth 25/16 *is* the exact solve — is that a **weak** or **strong**
solution in Allis's terms, and does running it from every position (not just the
root) change the answer?

**My take.**

I understand the minimax algorithm as a recursive definition of the game-theoretic value of every reachable state. Russell and Norvig define `MINIMAX(s)` as follows:

- If `IS-TERMINAL(s)`, then `MINIMAX(s) = UTILITY(s)`.
- If `TO-MOVE(s) = MAX`, then `MINIMAX(s) = max_{a ∈ ACTIONS(s)} MINIMAX(RESULT(s, a))`.
- If `TO-MOVE(s) = MIN`, then `MINIMAX(s) = min_{a ∈ ACTIONS(s)} MINIMAX(RESULT(s, a))`.

The alternating maximization and minimization reflects the assumption that both players act rationally and play optimally. Consequently, the value computed at the initial state is not merely an evaluation of the current position but the game-theoretic value of that position under perfect play.

This interpretation is consistent with Allis's notion of determining "who wins with perfect play." In Russell and Norvig, minimax is the algorithm that computes this value; in Allis, the same value serves as the criterion for classifying whether a game has been solved. Thus, minimax provides the computational mechanism, while Allis provides the terminology for interpreting the result.

For FLIPHEX, assuming exhaustive minimax can be performed over the complete game tree (16 plies on a 4×4 board or 25 plies on a 5×5 board), the value obtained at the initial state constitutes an exact solution of the game from its starting position. According to Allis's taxonomy, this corresponds to a **weak solution**, because it establishes the game-theoretic value and an optimal strategy from the initial position only.

If minimax is computed for every reachable position, rather than only the initial state, the result becomes a **strong solution**. In that case, the solver knows the game-theoretic value and an optimal move for every reachable state, allowing perfect play regardless of how the current position was reached, including positions arising from earlier mistakes by either player.

This distinction is important for H1. The hypothesis concerns determining the game-theoretic value of the initial FLIPHEX position—whether the first or second player has a forced win under perfect play—which is sufficient for a weak solution. Extending the computation to all reachable states would strengthen the result by constructing a complete oracle for the game, which is more closely aligned with the role envisioned for the solver in H3.

**Refined write-up.**

The recurrence is stated correctly, and the weak/strong distinction plus its
mapping onto H1/H3 is the most valuable thing in this note. Two sharpenings, the
second of which is a real trap.

**Allis's strong solution quantifies over *legal* positions, not reachable ones.**
He defines it as a strategy achieving the game-theoretic value "for all legal
positions". The distinction is not pedantic here: FLIPHEX positions reachable only
through a blunder are still legal, and those are exactly the positions H3 needs
the oracle to answer, since the learned agent will visit them.

**Alpha-beta does not hand you a strong solution as a by-product — this is the
trap.** Your paragraph moves from "compute minimax for every reachable position"
to "strong solution" as if it were a matter of running the same search more
widely. Plain minimax does compute a value at every node it visits. **Alpha-beta
does not.** Look at R&N's own pseudocode (Fig. 6.7): after `if v ≥ β then return
v`, the returned `v` is a *bound*, not the node's value — the loop was abandoned.
So the TT left behind by an alpha-beta solve is a mixture of exact values and
one-sided bounds, and querying it as an oracle would silently return wrong
answers. Real engines handle this by storing an EXACT/LOWER/UPPER flag with each
entry; a solver that intends to be an oracle must either store only EXACT entries
or re-search each query with a fresh (−∞, +∞) window.

The good news is that the route you are already committed to sidesteps this
entirely. **Retrograde analysis (§6.3.4) produces a strong solution natively** —
R&N describe its output as *"a policy, which is a mapping from every possible
state to the best move"*, which is Allis's strong solution in R&N's words. So the
right plan for 4×4 is not "alpha-beta harder"; it is retrograde enumeration, which
gives you (a) more than H1 needs — H1 only wants the root value, i.e. a weak
solution — and (b) exactly what H3 needs, an oracle answerable at arbitrary
positions. Bank that: the deliverable on 4×4 should be advertised as a **strong**
solution, which is a stronger claim than checkers ever achieved on its full board
(see §6.7.2).

### 6.2.2 — Complexity, and why raw minimax is hopeless on 5×5
**Prompt.** R&N give minimax as O(bᵈ) time. Plug in FLIPHEX's numbers
(b starts 1450, d = 25 — see adr-004). Why is unpruned minimax a non-starter on
5×5, and how does this motivate *both* pruning (§6.3, the classical route) *and*
the learned value function (Axis 2)? This is the fork in the road between the two
axes — state it in your own words.

**My take.**

Russell and Norvig show that the computational complexity of exhaustive minimax search is exponential in the depth of the game tree, requiring \(O(b^d)\) time, where \(b\) is the branching factor and \(d\) is the search depth. This complexity arises because every legal continuation must be explored under the assumption of perfect play.

For FLIPHEX, this complexity becomes prohibitive. The game has a fixed depth of 25 plies, but the initial branching factor is approximately 1,450 legal actions. Even though the branching factor decreases as the board fills, the search space remains astronomically large, making an unpruned exhaustive minimax search computationally infeasible on the 5×5 board.

I view this observation as the point where the project naturally splits into two complementary research directions.

The first direction seeks to preserve exactness while reducing the number of states that must be explored. Classical search techniques—including alpha-beta pruning, effective move ordering, and transposition tables—do not alter the game-theoretic value being computed. Instead, they exploit structural properties of the search tree to avoid evaluating positions whose values cannot influence the optimal decision. The objective is therefore to compute the exact minimax value more efficiently.

The second direction accepts that exhaustive search may remain impractical despite these optimizations. Instead of evaluating complete subtrees, it replaces exact recursive computation with a learned approximation of the value function. A neural network estimates the long-term utility of non-terminal positions, allowing search to terminate early while still producing strong decisions. This exchanges mathematical guarantees of optimality for computational tractability and empirical performance.

I therefore see the exponential complexity of minimax not merely as a limitation but as the motivation for the project's two research axes. Axis 1 investigates how far exact search can be pushed through algorithmic improvements without sacrificing correctness. Axis 2 investigates whether learned value estimation can provide sufficiently accurate guidance when exact search becomes computationally infeasible. Both approaches address the same combinatorial explosion, but they do so by fundamentally different means: one reduces the search required to compute the exact value, whereas the other approximates the value itself.

**Refined write-up.**

"Reduce the search needed to get the exact value" versus "approximate the value
itself" is a clean and correct statement of the fork. Two additions: the numbers
you left out, and a third road the chapter names that your dichotomy misses.

**Put the numbers in.** The crude figure is `1450²⁵ ≈ 10⁷⁹`. That over-counts,
because `b` collapses as cells fill and hands empty; carrying the collapse through
gives a 5×5 game tree of roughly **10⁶¹**. Either way the conclusion is the same,
but the honest number is worth stating — and it sets up the key comparison in
§6.3.1: the 5×5 *state space* is only 4.9 × 10¹⁷. A tree of 10⁶¹ over a state
space of 10¹⁷·⁷ means the tree is ~10⁴³× redundant. That gap is not a curiosity;
it is where the entire solver strategy lives.

**There is a third road: replace search with lookup.** Your fork is
exact-search-cheaper (§6.3) versus learned-approximation (Axis 2). R&N's §6.3.4
adds a route that is neither — *retrograde enumeration*, which is exact and is not
a tree search at all: it enumerates states, not paths, so the 10⁴³ redundancy
above simply never gets paid. adr-004 in fact uses all three (reduced-variant exact
solve, depth-limited alpha-beta on 5×5, retrograde endgame DBs), so the ADR is
already ahead of this dichotomy — but the note should say *trifurcation*, because
the third road is the one that actually delivers the 4×4 verdict (see §6.3.1).

---

## §6.3 — Heuristic alpha–beta tree search (the adr-004 core)

### 6.3.1 — Why pruning is sound, and the move-ordering payoff
**Prompt.** Explain *why* alpha-beta returns the exact minimax value despite
pruning (the α/β bounds and the cutoff condition). Then the load-bearing fact for
adr-004: with **optimal move ordering**, complexity drops from O(bᵈ) to
**O(b^{d/2})** — derive/justify the exponent halving. adr-004 stakes the whole
solver budget on ordering quality; does R&N's account support that emphasis?

**My take.**

Alpha-beta pruning is an optimization of minimax that preserves the exact game-theoretic value while reducing the number of states that must be evaluated. Its correctness follows from the observation that some branches can be proven incapable of influencing the final minimax decision.

During search, alpha-beta maintains two bounds. The value α represents the best score that the maximizing player (MAX) can already guarantee along the current search path, while β represents the best score that the minimizing player (MIN) can already guarantee. As search progresses, these bounds become increasingly restrictive.

A cutoff occurs whenever α ≥ β. At that point, the remaining unexplored successors of the current node cannot possibly change the value propagated to the parent. Regardless of their exact values, the parent node already has an alternative that is at least as good (for MAX) or at least as bad (for MIN). Consequently, omitting those branches does not alter the final minimax value. Alpha-beta therefore prunes search effort rather than changing the optimization objective.

The effectiveness of alpha-beta depends critically on the order in which moves are examined. If the strongest moves are explored first, the α and β bounds tighten earlier, allowing more branches to be eliminated before they are searched. Russell and Norvig show that, under optimal move ordering, the effective time complexity improves from O(b^d) to O(b^{d/2}).

The exponent is halved because effective pruning approximately doubles the search depth that can be reached for the same computational effort. Intuitively, instead of exploring nearly every branch at every level, alpha-beta rapidly establishes bounds that prevent large subtrees from being expanded. The search behaves approximately as though only every second level contributes the full branching factor, yielding an effective complexity proportional to the square root of the original search tree size.

For FLIPHEX, this result strongly supports the design adopted in ADR-004. Given the extremely large branching factor, the quality of move ordering is not a secondary optimization but a primary determinant of solver performance. Better ordering does not improve the theoretical minimax value—it is already exact—but it substantially increases the amount of the search tree that can be discarded without affecting correctness. Consequently, investment in move ordering directly translates into a larger feasible search horizon under a fixed computational budget.

**Refined write-up.**

The soundness argument is correct and well stated: α and β are *achievable*
guarantees already banked elsewhere in the tree, so a node whose value cannot
escape the (α, β) window cannot change what the parent propagates. Keep that.
The exponent argument needs the actual derivation, and then the FLIPHEX numbers
overturn your closing sentence.

**The halving, properly (Knuth–Moore minimal tree).** Your "the search behaves
approximately as though only every second level contributes the full branching
factor" is the right picture but stops before the mechanism. With perfect
ordering, at any node the best move is tried first. That first child must be
searched in full, because its value *becomes* the node's value. Every sibling
only has to be **refuted** — shown to be no better — and refuting a MIN node
requires exhibiting just *one* of its children that already falls outside the
window. So the levels alternate: `b` children, then 1, then `b`, then 1, …
Counting leaves gives

```
b^⌈d/2⌉ + b^⌊d/2⌋ − 1   ≈   O(b^{d/2})
```

Equivalently the effective branching factor is √b. R&N give the calibration
directly — *"for chess, about 6 instead of 35… alpha-beta with perfect move
ordering can solve a tree roughly twice as deep as minimax in the same amount of
time"* — plus the figure you omitted, which is the realistic one: with **random**
ordering it is `O(b^{3d/4})`, and a simple domain ordering gets within about a
factor of 2 of the best case. Perfect ordering is unattainable by definition (R&N:
*"in that case the ordering function could be used to play a perfect game"*).

**Now the numbers, and they do not support your conclusion.** Apply `b^{d/2}` to
FLIPHEX:

| | game tree | perfect-ordering αβ | state space |
|---|--:|--:|--:|
| 4×4, adr-009 deck (b₀ = 576, d = 16) | ~10³³ | **~10¹⁶·⁵** | **9.3 × 10¹⁰** |
| 5×5, full deck (b₀ = 1450, d = 25) | ~10⁶¹ | ~10³⁰·⁵ | 4.9 × 10¹⁷ |

Perfect move ordering — an unattainable upper limit — leaves the 4×4 exact solve
at ~10¹⁶·⁵ nodes. That is **not** solvable. Yet the 4×4 is solvable, because its
state space is only ~10¹¹. The five-and-a-half orders of magnitude between
10¹⁶·⁵ and 10¹¹ are *transpositions*, and they are recovered by the
transposition table, not by ordering. R&N flag the same effect for chess in the
same section — *"use of transposition tables is very effective, allowing us to
double the reachable search depth"* — i.e. a win of the same order as perfect
ordering; in FLIPHEX, where the tree is ~10²² times its own state space at 4×4,
it is far larger.

**So adr-004's emphasis is misallocated, and this note should say so.** The ADR
states that "move ordering quality drives everything" and puts the solver budget
there. The corrected reading splits it in two:

- For the **depth-limited 5×5 agent** (adr-004 part 2), ordering does drive
  everything — that agent's whole value is the depth it reaches per second.
- For the **4×4 exact solve** (adr-004 part 1, the one carrying H1/H2), ordering
  is secondary. What makes it tractable is that the state space is small enough
  to enumerate, so the binding constraint is **memory and state enumeration, not
  pruning**. 9.3 × 10¹⁰ states at 2 bits each is ~23 GB — a storage-and-I/O
  engineering problem, not a search-heuristic one.

That is a genuine ADR-level finding rather than a note-level detail, and it is the
one thing from this chapter that should go back into adr-004.

### 6.3.2 — Transposition tables and cut-off (heuristic) evaluation
**Prompt.** R&N introduce transposition tables and the `H-MINIMAX` cut-off with
an evaluation function + `CUTOFF-TEST`. Two FLIPHEX connections: (a) adr-004's
Zobrist TT keys only on `(cell,colour)` and `(player,tile)` — is that consistent
with R&N's notion of a transposition, given FLIPHEX's inert tiles (adr-003)?
(b) FLIPHEX has **no natural heuristic** (a student game, no expert eval) — how
much of §6.3's strength depends on a good `EVAL`, and what does its absence imply
for a *pure* alpha-beta agent on 5×5? (Ties to the Allis §5 Connect-Four lesson.)

**My take.**

Russell and Norvig present transposition tables as a mechanism for avoiding redundant search by storing the computed value of previously evaluated positions. Their effectiveness relies on the observation that the same game state may be reached through different sequences of moves. Once the minimax value of such a state has been computed, it can be reused whenever that state reappears, eliminating unnecessary recomputation without changing the exact result.

This interpretation is consistent with the transposition table proposed in ADR-004. The Zobrist hash is defined only over the board configuration `(cell, colour)` and the remaining resources `(player, tile)`. According to ADR-003, FLIPHEX tiles become inert after placement: they never move, change state, or acquire additional properties. Therefore, the future evolution of the game is completely determined by the current board position, the remaining tiles available to each player, and the player to move. The path used to reach that position is irrelevant. Consequently, two histories producing identical values for these state variables represent the same game state and may safely share a transposition-table entry.

Russell and Norvig then introduce heuristic minimax (H-MINIMAX), in which search is terminated before reaching terminal states according to a `CUTOFF-TEST`, and an evaluation function estimates the utility of the resulting frontier positions. Unlike transposition tables, this modification changes the nature of the computation: the algorithm no longer returns the exact game-theoretic value but an approximation whose quality depends directly on the evaluation function.

This distinction is particularly important for FLIPHEX. Unlike chess or other well-studied games, FLIPHEX has no established body of expert knowledge from which a reliable heuristic evaluation function can be derived. As a student-designed game, it lacks decades of accumulated strategic understanding. Consequently, the effectiveness of H-MINIMAX cannot be assumed. A weak evaluation function may produce poor move ordering and inaccurate frontier estimates, substantially reducing playing strength.

This observation reinforces the architectural separation between the project's two research axes. Transposition tables remain valuable because they improve computational efficiency without sacrificing correctness. In contrast, heuristic cutoff search depends on domain knowledge that FLIPHEX currently lacks. This limitation motivates investigating learned value functions in Axis 2, while simultaneously explaining why Axis 1 emphasizes exact search techniques such as alpha-beta pruning and transposition tables. The discussion is consistent with Allis's analysis of Connect Four, where successful search depended critically on domain-specific knowledge rather than brute-force minimax alone.

**Refined write-up.**

**(a) The transposition argument is correct, and it is worth having as a proof
rather than an appeal to intuition.** The claim needing support is that
`(board colouring, both hands)` is a *sufficient statistic* for the future. It is,
in two steps: placed tiles are inert (adr-003), so no placed tile contributes
anything to future dynamics beyond the colour it left behind; and flips never
chain (adr-006), so `RESULT` depends only on the current colouring and the action.
Hence any two histories agreeing on (colouring, hands) have identical futures.
That is Markov, and it is what licenses sharing a TT entry.

Two things fall out that the ADR should absorb:

- **Side-to-move needs no Zobrist key.** Exactly one cell fills per ply, so the
  mover is the parity of the filled-cell count — a function of the board, not
  independent state. Worth stating, because omitting side-to-move from a hash key
  is normally a bug, and here it is provably not one.
- **adr-004's key count looks wrong.** It says Zobrist keys on `(cell, colour)`
  *and* `(player, tile)` — "50 random words". But 50 = 25 cells × 2 colours; the
  hand component needs a further 13 tiles × 2 players = 26. The count should be
  **76**, or the sentence should say the 50 covers only the board. Small, but it
  is the kind of slip that ships.

One caveat you did not reach, and it connects to §6.2.1: R&N describe the TT as
caching *"the heuristic value of states"*. Under alpha-beta many stored entries
are **bounds**, not values. A TT built during an alpha-beta run is therefore not
directly usable as the exact-solve output; entries need an EXACT/LOWER/UPPER flag,
or the solve needs to be retrograde in the first place.

**(b) On the missing heuristic — right, and R&N make it quantitative.** §6.7 turns
"a weak `EVAL` hurts" into a number: with independent errors of standard deviation
σ = 5, minimax picks the *worse* branch 71% of the time in their two-ply example
(58% at σ = 2), and *"if errors in the evaluation function are not independent,
then the chance of a mistake rises"* — which is the FLIPHEX case, since sibling
positions differ by one placement and their evaluation errors would be strongly
correlated. So a pure depth-limited alpha-beta agent on 5×5 with a naive `EVAL`
is not merely "weaker than it could be"; its move choice is close to a coin flip
in the positions that matter.

Two pointers that strengthen the paragraph. First, R&N's own §6.3.3 evidence for
this comes from **Othello** (Buro's PROBCUT on LOGISTELLO) — the game whose
Allis-profile FLIPHEX shares. Second, the honest implication is not "avoid
heuristics" but "the heuristic must be *learned*, not authored" — which is the
cleanest single-sentence justification for Axis 2 in the whole chapter, and worth
lifting into adr-005's context section.

Finally, the Connect-Four attribution is right in substance (Allis's 1988 solution
was knowledge-based, with brute-force solutions coming later) but it comes from
the [Allis note](notes/allis-1994-searching-for-solutions.md), not from this
chapter — R&N mention Connect Four only in the bibliography. Keep the citation
pointing at Allis.

### 6.3.3 — Forward pruning, ordering heuristics, and the endgame
**Prompt.** Catalogue the practical accelerators R&N list (killer moves, history
heuristic, null-move, late-move reductions, beam/forward pruning). Which are
*safe* (value-preserving) versus *risky* (may miss the exact value)? For the
adr-004 retrograde endgame DBs, R&N discuss precomputed endgame tables — capture
how they frame table lookup as a perfect evaluator, and reconcile with adr-004's
`k ≤ 5` slice.

**My take.**

Russell and Norvig describe several practical techniques for accelerating game-tree search beyond basic alpha-beta pruning. These techniques differ fundamentally in whether they preserve the exact minimax value or intentionally trade correctness for additional speed.

Some accelerators are **value-preserving** because they affect only the order in which the search explores nodes. Examples include move ordering heuristics such as the killer-move heuristic, the history heuristic, and transposition-table move ordering. These methods attempt to examine promising moves earlier, increasing the effectiveness of alpha-beta pruning without changing the set of positions that are ultimately searched if no cutoffs occur. Consequently, they preserve the exact minimax value while improving computational efficiency.

Other techniques are **heuristic reductions** that deliberately avoid exploring parts of the search tree. These include null-move pruning, late-move reductions, beam search, and other forms of forward pruning. Their effectiveness depends on assumptions about which branches are unlikely to affect the final decision. Because these assumptions are heuristic rather than logically guaranteed, they may prune a branch that actually contains the optimal continuation. As a result, these methods sacrifice the guarantee of computing the exact minimax value in exchange for significantly faster search.

This distinction aligns naturally with the philosophy adopted in ADR-004. Since the objective of Axis 1 is to construct an exact solver, value-preserving optimizations are compatible with the architectural goals, whereas heuristic pruning techniques should be treated cautiously because they weaken the mathematical guarantees required for proving the game-theoretic value.

Russell and Norvig also discuss precomputed endgame databases as an alternative to heuristic evaluation. Rather than estimating the value of late-game positions, these databases store the exact game-theoretic values of previously solved states. A table lookup therefore functions as a perfect evaluation function: once a searched position falls within the database, no further search or heuristic estimation is required because the exact minimax value is already known.

This perspective is consistent with the retrograde endgame databases proposed in ADR-004. Restricting the database to positions with at most five remaining moves (k ≤ 5) represents a practical compromise between storage requirements and computational benefit. Within this slice, the database acts as an exact oracle rather than an approximation, replacing search with constant-time retrieval while preserving correctness. The limitation is not conceptual but practical: only a suffix of the complete state space is stored.

**Refined write-up.**

The safe/risky split is exactly R&N's own framing — alpha-beta prunes what *"can
have no effect on the final evaluation"*, forward pruning prunes what *"appear to
be poor moves, but might possibly be good ones… at the risk of making an error"*.
And "the database is a perfect evaluator, so the limitation is practical, not
conceptual" is the right reading of §6.3.4. Three corrections, and one number that
should change adr-004.

**The catalogue is partly imported.** What R&N actually name in this chapter:
killer moves, transposition tables and iterative-deepening ordering (§6.2.4); beam
search, PROBCUT and late move reduction (§6.3.3). **Null-move pruning is not in
this chapter**, and the *history heuristic* is not named either — §6.2.4 only
describes the general idea of "trying first the moves that were found to be best
in the past" and labels those killer moves. Both techniques are real, but citing
them to R&N §6 would be a miscitation.

**One wording slip.** You wrote that ordering heuristics preserve value "without
changing the set of positions that are ultimately searched if no cutoffs occur."
Ordering *does* change which positions get searched — that is the entire point of
it. What is preserved is the returned **value**, not the visited set. Say
value-preserving, not search-preserving.

**PROBCUT deserves promotion from the "risky" bin.** It is risky in the strict
sense, but Buro's result is that LOGISTELLO with PROBCUT *"beat the regular
version 64% of the time, even when the regular version was given twice as much
time"* — on Othello. For the depth-limited 5×5 agent, where exactness is already
abandoned, that is a strong candidate rather than a hazard. Keep it firmly out of
the 3×3/4×4 exact solves.

**And the number that matters: `k ≤ 5` may be too ambitious.** R&N calibrate the
industrial ceiling — chess tables are complete *"for all endings with seven or
fewer pieces. The tables contain 400 trillion positions"* (4 × 10¹⁴), with
eight-piece at 4 × 10¹⁶ and undone. Applying the adr-003 bound to FLIPHEX's
last-`k`-empty slice:

| k | positions with exactly k empty | cumulative ≤ k |
|--:|--:|--:|
| 3 | 9.0 × 10¹² | 9.4 × 10¹² |
| 4 | 1.4 × 10¹⁴ | 1.5 × 10¹⁴ |
| 5 | 1.1 × 10¹⁵ | **1.2 × 10¹⁵** |

So `k ≤ 5` is ~3× *larger* than the complete 7-piece chess tablebase — a
multi-institution effort — while `k ≤ 3` (10¹³) is comfortable on a laptop and
`k ≤ 4` (10¹⁴) is roughly at the chess ceiling. Two honest caveats before
rewriting the ADR: these are **upper** bounds (the `2^t` factor treats every
2-colouring as reachable, which it is not), so the true counts are lower by an
unknown factor; and endgame states compress well. But adr-004 currently presents
`k ≤ 5` as the target and `k ≤ 3` as a fallback, and the arithmetic says the
default expectation should be inverted: **`k ≤ 3` is the commitment, `k ≤ 4`
the stretch, `k = 5` only if the reachability gap turns out to be large.** Worth
an ADR amendment, and worth measuring the real reachable count on 3×3 first,
where it can be enumerated exactly and the bound's slack can be calibrated.

---

## §6.4 — Monte Carlo Tree Search (the bridge to Axis 2) 🔄

### 6.4.1 — The four MCTS phases and UCB1/UCT
**Prompt.** Write the four phases (selection, expansion, simulation/playout,
back-propagation) and the **UCB1** selection formula
`argmax( Q(a) + c·√(ln N / n(a)) )`. What problem does the exploration term
solve, and why does MCTS beat alpha-beta precisely where alpha-beta struggles —
high branching factor and **no reliable heuristic** (exactly FLIPHEX's situation
on 5×5)?

**My take.**

Russell and Norvig describe Monte Carlo Tree Search (MCTS) as an incremental search algorithm that estimates the value of actions through repeated sampling rather than exhaustive exploration. Each iteration consists of four phases:

1. **Selection:** Starting from the root, repeatedly select child nodes according to the UCT policy until reaching a node that is either terminal or not fully expanded.
2. **Expansion:** If the selected node is non-terminal and has unexplored legal actions, create one or more new child nodes corresponding to those actions.
3. **Simulation (playout):** From the newly expanded node, simulate a complete game—typically using a simple default policy—until reaching a terminal state.
4. **Back-propagation:** Propagate the simulation outcome back through every node visited during the iteration, updating the accumulated statistics used by future selections.

During the selection phase, MCTS applies the UCB1 rule to balance exploitation and exploration:

\[
\operatorname*{argmax}_{a}
\left(
Q(a)
+
c\sqrt{\frac{\ln N}{n(a)}}
\right),
\]

where \(Q(a)\) is the estimated value of action \(a\), \(N\) is the number of visits to the current node, \(n(a)\) is the number of times action \(a\) has been selected, and \(c\) controls the exploration–exploitation trade-off.

The exploration term addresses a fundamental limitation of purely greedy search. If action selection were based only on the current value estimate \(Q(a)\), the algorithm could prematurely commit to moves that appear promising because of limited evidence while neglecting alternatives that have been explored only a few times. The exploration bonus assigns higher priority to rarely visited actions, ensuring that uncertainty is gradually reduced rather than ignored.

I interpret MCTS as addressing a different computational bottleneck than alpha-beta. Alpha-beta remains an exact search algorithm whose efficiency depends on proving that large portions of the tree are irrelevant, making it most effective when good move ordering and reliable evaluation permit aggressive pruning. MCTS, by contrast, never attempts to evaluate the entire search tree. Instead, it concentrates computational effort on regions that appear statistically promising, allowing useful decisions to emerge from repeated sampling even when exhaustive search is impossible.

This distinction is particularly relevant for FLIPHEX on the 5×5 board. The game combines a very large branching factor with the absence of an established heuristic evaluation function. These are precisely the conditions under which exhaustive alpha-beta becomes difficult to scale, whereas MCTS remains practical because it requires neither complete tree expansion nor expert-crafted evaluation heuristics. This observation provides the conceptual bridge from the exact-search focus of Axis 1 to the learning-based methods developed in Axis 2.

**Refined write-up.**

The four phases, UCB1, and the exploration rationale are all correct. What the
take gestures at but does not name is R&N's actual *mechanism* for why MCTS wins
in this regime, and there are two FLIPHEX-specific consequences worth banking.

**The mechanism is error aggregation, not effort allocation.** You framed it as
"MCTS concentrates effort where it is statistically promising." True, but R&N's
argument is sharper: *"A miscalculation on a single node can lead alpha–beta to
erroneously choose (or avoid) a path to that node. But Monte Carlo search relies
on the aggregate of many playouts, and thus is not as vulnerable to a single
error."* Alpha-beta propagates one leaf's error straight to the root by
construction — the max/min chain has no averaging anywhere in it. MCTS averages.
That is why the eval-error result quoted in §6.3.2 (σ = 5 → wrong branch 71% of
the time) hits alpha-beta and not MCTS, and it is the *same* fact stated twice.

**R&N also name two MCTS disadvantages, and FLIPHEX dodges one of them for free.**
They are: (i) *"a single move can change the course of the game… a vital line of
play might not be explored at all"*; and (ii) positions that are obviously won
*"but where it will still take many moves in a playout to verify the winner."*
Disadvantage (ii) is essentially void for FLIPHEX — a playout is at most 25 plies,
always terminates, and always yields a decided winner (draws impossible). So the
whole *early playout termination* apparatus R&N describe is unnecessary here, and
playouts cost microseconds. Disadvantage (i) does apply and is the real risk, and
it is precisely what the exact solver is there to catch.

**Consequence worth flagging: plain UCT is a cheap, strong baseline for FLIPHEX
that the project currently has no slot for.** Given free playouts and no need for
an evaluation function, a no-network UCT agent can be built in an afternoon and
gives a strength yardstick between "random" and "AlphaZero". Note the tension
though: adr-004 rejects MCTS *as the Axis 1 method* on independence grounds, and
that rejection stands. A plain-UCT **baseline** is a third thing — neither ground
truth nor the learned agent — so if it is added, it must be labelled as a
yardstick and kept out of any H3 cross-check, or the axis independence adr-004
protects is quietly lost. Park it as an open idea rather than smuggling it into an
axis.

One constant to leave alone: R&N's `c = √2` is the theoretical UCB1 value for
rewards in [0, 1]; treat it as a starting point to tune, not a number to copy.

### 6.4.2 — From generic UCT to AlphaZero's PUCT 🔄
**Prompt.** R&N's MCTS uses *random* (or lightly-guided) playouts and UCB1.
AlphaZero (Silver 2018, your note) replaces playouts with a **learned value
head** and UCB1 with **PUCT** (prior P(a) from the policy head, no rollouts).
List the exact substitutions. This is the crux of **synthesis S4** — answer the
comparison in [phase2-synthesis.md](notes/phase2-synthesis.md), and here only
note the one-line mapping. Which of FLIPHEX's Axis-2 design choices (adr-005) are
already visible, in embryo, in R&N's generic MCTS?

**My take.**

Russell and Norvig present the generic Monte Carlo Tree Search framework based on UCT, in which node selection is guided by UCB1 and leaf evaluation is obtained through simulation (playout) to terminal states. AlphaZero can be understood as a specialization of this generic framework rather than a fundamentally different search algorithm.

At a high level, the mapping is:

- **UCT selection (UCB1)** → **PUCT selection** using policy-network priors.
- **Random or lightly guided playouts** → **Learned value network** for leaf evaluation.
- **Simulation-derived action preferences** → **Policy-network priors** that guide search from the outset.
- **Search statistics alone** → **Search statistics combined with neural-network predictions**.

This chapter therefore provides the conceptual foundation for the design adopted in ADR-005. The essential MCTS structure—selection, expansion, and back-propagation—remains unchanged, while AlphaZero modifies only how nodes are selected and evaluated. The detailed comparison between UCT and PUCT belongs in the synthesis note (S4).

**Refined write-up.**

Right to keep this short and push the comparison to S4. Three fixes to the mapping
before it gets carried into the synthesis.

**The playout is deleted, not replaced.** Your third row ("simulation-derived
action preferences → policy priors") blurs two distinct changes. AlphaZero removes
the simulation phase outright: the leaf is scored by one network call returning
`(p, v)`, so MCTS drops from four phases to three. That is not a swap of playout
policy — it is the removal of the only unbiased estimator in the algorithm, traded
for a learned one. Worth stating plainly, because it is also where AZ's failure
mode comes from.

**PUCT's exploration term is not a confidence bound.** UCB1's `c·√(ln N / n(a))`
is derived from a concentration inequality — it is a bound on how wrong `Q(a)`
could be. AlphaZero's `c·P(a)·√ΣN / (1 + N(a))` is not: it decays like `1/n`
rather than `√(ln n / n)`, and it is *scaled by the prior*, so a move the policy
head dislikes is explored less no matter how uncertain its value is. The
substitution therefore trades a regret guarantee for prior-guided focus. Given
FLIPHEX's b₀ = 1450, that trade is the whole reason AZ-style search is viable
here — but it is a trade, and S4 should say so rather than presenting PUCT as
"UCB1 with priors."

**The substitution you missed is the important one.** All four of your rows are
about how search *runs*. AlphaZero's defining move is what it does with the
search *output*: the visit counts become the **policy training target**
(`π ∝ N^{1/τ}`), so search improves the network which improves search. Without
that row, AZ is just guided MCTS; with it, it is a closed learning loop. That is
the row S4 should be built around.

For adr-005: what is already in embryo in R&N's generic MCTS is the tree policy,
the backup rule, and the visit-count-as-strength idea. What is *not* — and so must
be justified independently in the ADR rather than inherited — is the learned
evaluator, the prior-scaled exploration, and the training loop.

---

## §6.5 / §6.6 — Stochastic & partially observable games (OUT of scope — skim)

### 6.5.1 — Confirm the scope boundary
**Prompt.** One sentence each: R&N's expectiminimax (stochastic) and the
belief-state treatment (partially observable). Confirm *why* both are irrelevant
to FLIPHEX per adr-001 (deterministic, perfect information). If either suggests a
FLIPHEX *variant* worth parking (e.g. a hidden-hand variant), drop it in
`notes/open-ideas.md`, not here.

**My take.**

Russell and Norvig extend adversarial search to stochastic games through **expectiminimax**, which introduces chance nodes representing probabilistic events and computes expected utilities rather than deterministic minimax values.

For partially observable games, the chapter models decision making over **belief states**, where the agent maintains a probability distribution over possible underlying game states because the true state is not fully observable.

Neither extension is relevant to FLIPHEX. According to ADR-001, FLIPHEX is a deterministic, two-player, zero-sum game with perfect information: every action has a deterministic successor, and both players always observe the complete game state. Consequently, neither chance nodes nor belief-state reasoning are required for the search algorithms considered in this project.

**Refined write-up.**

Correct and appropriately brief — the scope boundary holds exactly as adr-001
draws it. One thing the skim surfaces that is worth parking rather than
discarding: FLIPHEX has a completely natural §6.6 variant, namely **concealed
hands**. The physical game is played with hands visible, but hiding them turns
the state into a belief state over the opponent's remaining tiles, and — unusually
— the belief is *exactly* computable, since the deck is a known 13-tile set and
every placement removes one publicly. That makes it a rare partially-observable
game with a tractable, finite, exactly-updatable belief state.

It is firmly out of scope for this project (adr-001, and H6 is already the stretch
slot). Log it in `notes/open-ideas.md` as a variant with a genuinely interesting
formal property, and leave it there.

---

## §6.7 — Limitations of game search algorithms

### 6.7.1 — Where alpha-beta and MCTS each break, and the honest headline
**Prompt.** R&N close by naming the failure modes (alpha-beta's sensitivity to
eval quality and horizon; MCTS's blind spots on traps/tactics requiring exact
lines; both on huge branching). Map each to a FLIPHEX risk: which limitation
threatens the *solver* (adr-004) and which the *learned agent* (adr-005)? This
should sharpen the "solved on 3×3/4×4, endgame-exact on 5×5, strong elsewhere"
honest-headline wording — does the chapter give you a reason to soften or harden
any part of it?

**My take.**

Russell and Norvig conclude the chapter by emphasizing that no game-search algorithm is universally effective. The limitations depend not only on the search algorithm itself but also on the characteristics of the game and the available computational resources.

For alpha-beta search, the principal limitations arise when complete search is impossible. In such cases, playing strength depends heavily on the quality of the evaluation function, and truncated search remains vulnerable to horizon effects. These limitations do not affect an exact search that reaches terminal states, but they become significant whenever heuristic cutoff evaluation is required.

For Monte Carlo Tree Search, the principal limitation is different. MCTS allocates search effort statistically rather than proving exact values. Consequently, it may overlook tactically critical variations or narrow forced sequences that require exhaustive analysis but receive insufficient sampling. Although MCTS performs well in domains with very large branching factors and weak heuristic knowledge, it does not provide guarantees of optimal play.

Applied to FLIPHEX, these limitations affect the project's two research axes differently. The primary risk for the exact solver (ADR-004) is not alpha-beta itself but the computational infeasibility of exhaustive search on the 5×5 game. As long as terminal states are reached or exact endgame databases are used, alpha-beta retains its correctness. Its practical limitation is computational scale rather than theoretical validity.

For the learning-based agent (ADR-005), the principal risk is the absence of correctness guarantees. Even with a strong learned value function and MCTS, the resulting policy may still miss tactically decisive continuations or fail to recover the exact game-theoretic value in difficult positions. Consequently, empirical playing strength should not be interpreted as evidence that the game has been solved.

Overall, this chapter reinforces rather than weakens the project's current research framing. It supports the distinction between proving the game-theoretic value (Axis 1) and approximating strong play (Axis 2), while emphasizing that these objectives require different algorithms because they optimize different criteria. I therefore see no reason to soften the project's headline. If anything, the chapter suggests making the distinction even more explicit: the 3×3 and 4×4 boards are targets for exact solution, the 5×5 endgame database provides exactness only within its stored region, and outside that region the learned agent should be presented as an approximation rather than a proof.

**Refined write-up.**

The conclusion is right and the three-tier headline you propose at the end is
sharper than what adr-004 currently says. But the section is misattributed, and
that is partly my fault — the prompt named "MCTS's blind spots on traps" as a §6.7
item and it is not one.

**What §6.7 actually lists** are four limitations, and only the first is
algorithm-specific:

1. **Alpha-beta's vulnerability to eval error** — with the σ argument (σ = 5 →
   the "worse" branch is actually better 71% of the time), plus the note that
   correlated errors make it worse. This is the one you got right.
2. **Neither algorithm does metareasoning** — both compute values for all legal
   moves even when the answer cannot change the decision. R&N: a better algorithm
   would weigh the *utility of a node expansion* against its cost.
3. **Both reason at the level of individual moves**, with no abstraction or
   goal-directed planning (a human's "trap the queen").
4. **Integrating machine learning** — R&N cite AlphaZero here as the early answer.

MCTS's "a vital line of play might not be explored at all" is real and you stated
it correctly, but it lives in **§6.4**, not §6.7. Cite it there.

**Limitation 2 is unexpectedly on-topic for FLIPHEX and worth keeping.** R&N
single out *"the case of symmetrical moves, for which no amount of search will
show that one move is better than another."* FLIPHEX has exactly that structure:
the Z/2 mirror ([adr-008](docs/adr/adr-008-board-mirror-symmetry.md)) makes
mirror-image moves provably equal — but only once **both** `P3-y` tiles are placed,
i.e. in the endgame. So the wasted-computation problem R&N describe is real here
and is concentrated precisely in the retrograde databases, where folding it away
is a clean ~2× win. That is the same conclusion adr-004's Phase 2 amendment
reached, now with a textbook rationale behind it.

**On the headline: harden it, don't soften it — but add the real risk.** Two
adjustments. (i) On 3×3/4×4 the retrograde route yields a **strong** solution
(§6.2.1), so "solved" understates it; say *strongly solved*. (ii) The threat to
the exact half is not what you wrote. You say the risk is "computational
infeasibility of exhaustive search" — but per §6.3.1 the 4×4 is not search-bound
at all, it is **storage-bound** (~10¹¹ states, ~23 GB packed). Naming the risk
correctly matters, because the mitigations are entirely different: better ordering
buys nothing, disk-backed enumeration and state packing buy everything.

So the honest headline becomes: *strongly solved on 3×3 and 4×4 (reduced deck,
adr-009), exact in the last k plies on 5×5, strong-but-unproven elsewhere* — with
the caveat that limitation 1 says the depth-limited 5×5 alpha-beta agent is the
weakest component in the project, not the learned one.

### 6.7.2 — The empirical claims (validation, adapted for a textbook)
**Prompt.** The chapter cites landmark results (Deep Blue, checkers solved,
AlphaGo/AlphaZero). Pick the two most relevant to FLIPHEX (checkers = exact
solving via endgame DBs → Schaeffer, your *next* read; AlphaGo = learned play →
Silver). Note how *rigorously* R&N state each (proof vs strong empirical
evidence) — this calibrates how H1/H3 should phrase their own verdicts.

**My take.**

I see two landmark results as particularly relevant to the FLIPHEX project because they represent the two complementary research directions developed throughout this chapter.

The first is the solution of checkers, which demonstrates that a sufficiently large game can be solved exactly through a combination of search, alpha-beta pruning, transposition tables, and extensive endgame databases. Russell and Norvig present this result as a mathematically established solution rather than merely a strong playing program. This example directly motivates the exact-solving objective of Axis 1 and provides the conceptual precedent for retrograde endgame databases, which I will study in greater detail through Schaeffer's work.

The second is AlphaGo and its successor AlphaZero, which demonstrate that learned search can achieve superhuman playing strength in domains where exhaustive search is infeasible. Russell and Norvig present these systems as empirical achievements supported by competitive performance rather than as proofs of game-theoretic optimality. Their success therefore establishes the practical effectiveness of learned search without implying that the underlying games have been solved.

This distinction is important for my own research framing. H1 should present conclusions about the game-theoretic value only when supported by exact search or mathematical proof. H3, by contrast, should evaluate the learned agent using empirical performance, agreement with the solver where available, and generalization to unseen positions, without implying that strong playing performance constitutes evidence of an exact solution.

More generally, I appreciate that the chapter consistently distinguishes between proven correctness and demonstrated performance. That distinction should also guide the language used throughout this project, ensuring that exact solutions, empirical results, and learned approximations are never presented as equivalent forms of evidence.

**Refined write-up.**

The proof-versus-performance calibration is exactly the right thing to take from
this section, and the H1/H3 split you draw from it is correct. One factual
correction, and it strengthens your position rather than weakening it.

**Checkers is weakly solved, not solved outright.** Schaeffer et al. (2007)
proved the game-theoretic value of the *initial position* — a draw — using a
10-piece endgame database plus a proof tree over the opening. They did not produce
a value for every legal position, so it is a **weak** solution in Allis's sense.
Your phrasing ("a mathematically established solution") is true but reads as
stronger than what was achieved. Getting this right matters for two reasons:

- **It is the right yardstick for H1.** H1 asks who wins from the initial
  position. That is a weak solution — the same class of claim as checkers. So H1
  is well-precedented and does not need to overreach.
- **It sets up a claim you can legitimately make that checkers could not.**
  Per §6.2.1, retrograde enumeration on 4×4 gives a value for *every* position —
  a **strong** solution. On a smaller board, obviously; but the *class* of result
  is stronger than the checkers headline, and that is worth stating precisely
  rather than vaguely.

Note also the asymmetry in how the two results are used in the chapter: checkers
appears in §6.3.4 and the bibliography as a completed mathematical fact, whereas
AlphaZero appears in §6.7 as an *open direction* ("we are just beginning to see
programs like ALPHAZERO") and in §6.2.4 as an empirical performance claim
("world-championlevel play"). R&N never assert that AlphaZero plays optimally.
That is the register H3 should copy: agreement-with-the-oracle where the oracle
exists, win-rate with confidence intervals where it does not, and no sentence
that lets the two blur.

Schaeffer 2007 is the right next read, and this section is the reason: it is the
only published account of the exact pipeline the 4×4 solve now looks like —
retrograde databases plus a proof over the remainder, and a storage problem rather
than a search one.

---

## Lessons Learned

This chapter reshaped how I think about adversarial search by separating the concepts of exact solving and strong play. I now see minimax as the recursive definition of the game-theoretic value of a state rather than simply a move-selection algorithm, with alpha-beta serving as an exact optimization that preserves this value through logical pruning.

A key insight was that not all search accelerations are equivalent. Move ordering, transposition tables, and endgame databases reduce computation while preserving correctness, whereas heuristic evaluation, forward pruning, and related techniques deliberately trade mathematical guarantees for speed. This distinction strengthened the architectural separation between Axis 1 (exact search) and Axis 2 (learned approximation).

The reading also clarified that a transposition table relies on a formally sufficient state representation rather than intuition. Correctness depends on demonstrating that all future evolution is determined solely by the encoded state variables, reinforcing the importance of the Markov assumption behind the ADR-004 state representation.

Finally, the chapter reinforced the distinction between proof and empirical evidence. Exact search supports claims about the game-theoretic value of FLIPHEX, while learned agents support claims about playing strength. Keeping these forms of evidence separate will be essential throughout the project.

## Failed Attempts

At the beginning of the reading, I tended to think of minimax primarily as a search algorithm for choosing moves rather than as the mechanism that defines the game-theoretic value of every reachable state.

I also implicitly associated exploring the complete game tree with obtaining a strong solution. Revisiting Allis's taxonomy clarified that the defining property of a strong solution is knowledge of the correct value and optimal move for every reachable position, not simply the amount of search performed.

Another misconception was treating all search optimizations as equivalent. The reading clarified that some techniques preserve the exact minimax value by reducing redundant computation, while others replace exact computation with heuristic approximation. This distinction became central to how I now think about the architectural split between the project's exact solver and its learning-based agent.

Finally, I initially accepted the FLIPHEX state representation as Markovian largely by intuition. The discussion around transposition tables highlighted that this is a formal assumption requiring justification from the game rules rather than an implementation convenience.
