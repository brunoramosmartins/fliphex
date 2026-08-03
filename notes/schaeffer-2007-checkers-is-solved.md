# Reading companion — Schaeffer et al. 2007, Checkers Is Solved

**Citation.** Schaeffer, J., Burch, N., Björnsson, Y., Kishimoto, A., Müller, M.,
Lake, R., Lu, P. & Sutphen, S. (2007). *Checkers Is Solved.* **Science**
317(5844), 1518–1522. DOI [10.1126/science.1144079](https://doi.org/10.1126/science.1144079).
Read from the Science Express version (`refs/schaeffer-2007-checkers-is-solved.pdf`,
9 pp).

**Why this source, and where it sits.** This is the **only published account of
the exact pipeline the FLIPHEX solver has turned into**. The R&N reading
established that the 4×4 exact solve is not a tree-search problem at all — the
perfect-ordering alpha-beta bound is ~10¹⁶·⁵ while the state space is ~10¹¹, so
what solves it is *enumeration plus lookup*, and the binding constraint is
storage and I/O ([adr-004](docs/adr/adr-004-solver-approach.md) §6.3.1 of the
[R&N note](notes/russell-norvig-aima-ch6-adversarial-search.md)). Schaeffer is
the reference implementation of exactly that idea at scale: retrograde endgame
databases from the bottom, a proof tree from the top, meeting in the middle, run
for 18 years and defended as a *proof*. Read it **last** in Phase 2 — it assumes
Allis's solved-taxonomy vocabulary and answers the engineering question R&N only
gestures at in §6.3.4.

**Directed reading.** The paper is short and every part earns its place; there is
no section to skip. Weight your time toward **Backward search**, **Correctness**,
and **Results** — those three carry everything that transfers. The *Supporting
Online Material* section (§4 of the extraction) has the database-construction
detail and is worth a skim if §2's account leaves the retrograde algorithm fuzzy.

**Cross-refs this reading feeds:**
- [adr-004](docs/adr/adr-004-solver-approach.md) — the whole exact-solve strategy:
  the retrograde databases, the `k` target, and (new) whether the 4×4/5×5 solve
  should be a *backward + forward hybrid* rather than either alone.
- [adr-009](docs/adr/adr-009-reduced-deck-policy.md) — the reduced deck exists to
  put 4×4 inside enumeration range; Schaeffer calibrates what "in range" means.
- [research.md](docs/research.md) — **H1** (what class of claim the verdict is),
  **H3** (the solver as oracle), **H4** (where FLIPHEX sits on the complexity
  ladder — checkers is a datapoint *above* it).
- [allis-1994 note](notes/allis-1994-searching-for-solutions.md) — the
  converging/diverging distinction, which is the crux of prompt 2.2 below.
- [russell-norvig note](notes/russell-norvig-aima-ch6-adversarial-search.md) —
  §6.3.4 (search versus lookup) is the textbook sketch of this paper.
- `exercises/` — the retrograde-analysis derivation belongs here.
- **New:** there is currently **no ADR covering solver correctness**. Prompt 5.1
  is likely to create one.

**Legend.** Prompts marked 🔄 need synthesis with another source — answer them in
[phase2-synthesis.md](notes/phase2-synthesis.md) (**S1**: what "solved" buys;
**S4**: exact solving vs learned play), not here.

**Reading material** (extracted via `paper-study`, gitignored under
`notes/sources/`).
[manifest](sources/schaeffer-2007-checkers-is-solved/manifest.json) ·
[§1 front matter](sources/schaeffer-2007-checkers-is-solved/sections/01-front-matter.md) ·
[§2 main text](sources/schaeffer-2007-checkers-is-solved/sections/02-checkers-is-solved.md) ·
[§3 references](sources/schaeffer-2007-checkers-is-solved/sections/03-references-and-notes.md) ·
[§4 supporting online material](sources/schaeffer-2007-checkers-is-solved/sections/04-supporting-online-material.md).

> **Extraction note.** The two-column Science Express layout defeated the
> heading splitter, so the whole body is one 4774-word file (§2). Navigate it by
> the paper's own bold run-in heads, which are intact:

| This note's prompt | Anchor in `02-checkers-is-solved.md` |
|---|---|
| §1 framing and result | opening paragraphs (before `**Backward search.**`) |
| §2 retrograde databases | `**Backward search.**` (line ~42) |
| §3 architecture | `**Solving checkers.**` (line ~54) |
| §4 proof tree | `**Forward search.**` (line ~79) |
| §5 correctness | `**Correctness.**` (line ~91) |
| §6 results and cost | `**Results.**` (line ~97) |
| §7 conclusion 🔄 | `**Conclusion.**` (line ~124) |

> Lines around 32 are garbled — the extractor interleaved the two columns there.
> If a sentence reads as nonsense, check the PDF rather than trusting the file.

---

## §1 — What was proved, and in what class

### 1.1 — The claim, stated precisely
**Prompt.** The abstract says "checkers is now solved: perfect play by both sides
leads to a draw." In Allis's taxonomy, which class is that — ultra-weak, weak, or
strong? Find the sentence in the paper that pins it down (the authors are explicit;
do not infer it). Then the FLIPHEX consequence: **H1** asks who wins from the
initial position, so which class does H1 need — and does the retrograde route
planned for 4×4 deliver *more* than H1 asks for? Predict before reading: do you
expect the strongest published game-solving result to be a strong solution?

**My take.**

The paper explicitly states that checkers has been **weakly solved**. According to Allis's taxonomy, this means that the game-theoretic value of the **initial position** has been established together with a strategy that achieves that value from the start of the game.

The opening section states:

> "This paper announces that checkers has been weakly solved."

The authors further explain that the computational proof consists of an explicit strategy that never loses from the standard starting position, thereby proving that perfect play by both sides leads to a draw.

This classification is important. Although the solution relies heavily on large retrograde endgame databases, those databases do not by themselves provide optimal play from every legal position. A strong solution would require the game-theoretic value and an optimal strategy for **every reachable position**, whereas the result presented here proves the value of the initial position through a combination of forward search and backward analysis.

For the FLIPHEX project, Hypothesis H1 asks only for the game-theoretic value of the initial position. Therefore, H1 requires only a **weak solution**. The planned retrograde-analysis pipeline may compute substantially more information than is strictly necessary for H1, particularly within the enumerated portion of the state space, but that additional coverage should not automatically be interpreted as a strong solution. Whether the final solver satisfies the stronger criterion depends on whether it can correctly determine optimal play from every reachable position, not merely from terminal or near-terminal configurations.

Before reading the remainder of the paper, one might expect the strongest published game-solving result to be a strong solution. Instead, the paper demonstrates that even an engineering effort spanning many years, combining large endgame databases with extensive forward search, was presented as a weak solution because the formal claim concerns the initial position rather than the entire reachable state space.

**Refined write-up.**

Quote, classification and the H1 mapping are all correct — and finding the
explicit sentence rather than inferring it was the right instinct, because the
paper's headline ("checkers is now solved") is looser than its actual claim.

One thing to add and one hedge to remove.

**The paper uses "strongly solved" too — for the database region.** Component 1
is described as *"a database of 3.9 × 10¹³ positions (all positions with ≤ 10
pieces on the board) for which the game-theoretic value has been computed
(**strongly solved**)"*. So checkers is weakly solved *overall* and strongly
solved *within the ≤10-piece region*. That two-tier structure is exactly what
FLIPHEX will produce on 5×5 — strongly solved for k ≤ 3, unproven above it — so
it is worth borrowing the paper's own phrasing when the results are written up.

**The hedge in your last-but-one paragraph is too cautious for 4×4.** You write
that the extra coverage "should not automatically be interpreted as a strong
solution," and that whether it qualifies "depends on whether it can correctly
determine optimal play from every reachable position, not merely from terminal
or near-terminal configurations." That caveat is right for **5×5**, where only a
`k`-slice is enumerated. It does not apply to **4×4**: the plan there is to
enumerate the *entire* state space (~9.3 × 10¹⁰ states), so every legal position
gets a value by construction. Completeness is not something to be checked
afterwards — it is what the algorithm does. So the 4×4 deliverable is a strong
solution, and that is a *stronger class of claim than the checkers headline*,
albeit on a much smaller game. Say it plainly; it is one of the few places the
project can legitimately outrank a Science paper on a formal axis.

Your prediction was the productive kind of wrong. The reason the strongest result
is only weak is not modesty — it is economy: §6.1's "least amount of work"
principle means you stop the moment the root value is proven. Strength beyond
that is a by-product, not a goal.

### 1.2 — The complexity comparison, and a number that should unsettle you
**Prompt.** The paper gives checkers ~5 × 10²⁰ positions and calls it "roughly one
million times more complex than Connect Four". Now put FLIPHEX 5×5 next to it:
the corrected reachable bound is **4.9 × 10¹⁷** ([research.md](docs/research.md)),
i.e. checkers is ~1000× *larger* than the full FLIPHEX game. Sit with that. If a
bigger game was solved in 2007, what stops FLIPHEX 5×5 from being solved now?
List every reason you can find in the paper before reading §2 — then check your
list against prompt 2.2, which contains the answer you probably missed. This
directly stress-tests **H4** and the adr-004 claim that "the full 5×5 game will
almost certainly not be solved."

**My take.**

The comparison is initially counterintuitive. The paper estimates the state-space complexity of checkers at approximately \(5 \times 10^{20}\) legal positions, whereas the current upper bound for reachable FLIPHEX 5×5 positions is approximately \(4.9 \times 10^{17}\). By state-space size alone, checkers is roughly three orders of magnitude larger.

Nevertheless, the paper does not suggest that state-space size alone determines whether a game can be solved. Even before the technical sections, several limiting factors are already apparent.

First, the solution required an exceptionally long engineering effort spanning approximately eighteen years, indicating that practical solvability depends on algorithmic advances, software engineering, and available computational resources rather than on state-space size alone.

Second, the proof combines multiple complementary techniques rather than relying on exhaustive search. Large retrograde endgame databases, forward proof search, and substantial computational infrastructure all contribute essential components of the final result.

Third, the paper emphasizes correctness as much as computation. Producing a result is insufficient; the computation must be organized so that the final claim constitutes a verifiable proof.

At this stage, there is no evidence that the complexity of solving a game is determined solely by the number of reachable positions. The paper instead suggests that the structure of the state space and the ability to decompose the problem into tractable subproblems are likely to be equally important.

For FLIPHEX, this observation weakens any argument based purely on state-space comparison. Although the estimated reachable state space is substantially smaller than that of checkers, this alone does not imply that a complete solution is practical. The decisive factors may instead lie in properties of the game graph and in the effectiveness of backward analysis and proof construction, topics developed in the following sections.

**Refined write-up.**

You correctly refused the trap ("smaller state space ⇒ easier") and correctly
identified that the paper never claims state count decides solvability. The three
reasons you list are real but they are all *engineering* reasons — effort, tooling,
verification. The structural reason is the one that actually settles it, and the
paper hands you both halves of it.

**The paper's own taxonomy places FLIPHEX awkwardly.** It says: *"Checkers is
considered to have high decision complexity … and moderate space complexity
(5 × 10²⁰). All the games solved thus far have either low decision complexity
(Qubic; Go-Moku), low space complexity (Nine Men's Morris, size 10¹¹; Awari, size
10¹²) or both (Connect Four, size 10¹⁴)."* Line FLIPHEX 5×5 up against that list:
4.9 × 10¹⁷ is **three orders above Connect Four and five above Awari** — so
FLIPHEX does not qualify as "low space complexity" by the standard of anything
solved before checkers. This is a direct, citable **H4** datapoint and it is
better than the vague "comparable to Reversi 6×6" wording H4 currently carries.

**The binding constraint is game-tree complexity, not state count.** The paper
gives the formula (*"A d-ply search with an average of b moves … results in a tree
with roughly bᵈ positions"*) and its own effort figures: the stored proof tree is
*10⁷ positions*, each costing ~10⁷ nodes of search, so *"10¹⁴ is a good ballpark
estimate of the forward search effort"*. That is the number to compare against.
Checkers' branching factor is tiny — the forced-capture rule keeps it near single
digits — which is why a 10⁷-node proof tree can span the whole game. FLIPHEX
starts at **b = 1450**. The 5×5 game tree is ~10⁶¹, and even at the unattainable
`b^{d/2}` limit the forward proof is ~10³⁰·⁵
([R&N note](notes/russell-norvig-aima-ch6-adversarial-search.md) §6.3.1).

So: checkers has ~1000× more *states* than FLIPHEX 5×5 but roughly 10³⁰× fewer
*tree nodes to prove*. State-space complexity and game-tree complexity are
independent axes, and checkers is easy on the one that matters for a forward
proof while FLIPHEX is catastrophic on it. That is the reason adr-004's "the full
5×5 game will almost certainly not be solved" survives this paper — but note that
the ADR currently justifies it by state count, which this reading shows is the
*wrong justification for the right conclusion*. Worth amending.

---

## §2 — Backward search: the endgame databases

### 2.1 — Retrograde analysis, mechanically
**Prompt.** Write the algorithm as the paper describes it: start from 1-piece
positions, enumerate and resolve 2-piece, then 3-piece, and so on to ≤10 pieces.
Two things to extract precisely: (a) how a position's value is *derived* from
already-resolved positions (what is the backward analogue of the minimax
max/min step?); (b) how **draws by repetition** are detected, since a
repeated position has no resolved successor — this is the part that makes
retrograde analysis harder than it first looks. Then: FLIPHEX has **no draws and
no repetition** (25 cells, one filled per ply, odd). Which of these complications
simply vanishes for FLIPHEX, and does that make the FLIPHEX retrograde pass
*simpler* than checkers' or merely different?

**My take.**

Retrograde analysis proceeds by solving positions in reverse order of game progression. The computation begins with terminal positions, where the game-theoretic value is known by definition, and then propagates these values backward through the game graph.

The paper describes constructing endgame databases incrementally. First, all one-piece positions are enumerated and solved. Their resolved values are then used to determine the values of two-piece positions. This process continues successively through three-piece positions and larger material configurations until all positions containing ten or fewer pieces have been solved.

The backward propagation follows a rule that is the reverse of forward minimax evaluation. For each unresolved position, the values of all legally reachable successor positions are examined. A position is classified as a **win** if there exists at least one legal move leading to a position already known to be a loss for the opponent. Conversely, a position becomes a **loss** only after every legal successor has been established as a win for the opponent. This asymmetry is identical to the logical structure of minimax but applied in reverse: wins are discovered by the existence of a losing successor, whereas losses require exhaustion of all alternatives.

Draws are more subtle. Unlike wins and losses, they cannot generally be inferred immediately because repeated positions may form cycles in the game graph without reaching a terminal state. Consequently, a position whose successors remain unresolved cannot automatically be classified as a draw. The paper therefore treats repetition explicitly during database construction, ensuring that cyclic play is correctly identified rather than being mistaken for an unresolved computation.

For FLIPHEX, one major complication disappears. The game has neither repetition nor drawn outcomes: each move permanently occupies one previously empty cell, producing an acyclic game graph with a fixed maximum depth. As a result, every legal sequence eventually reaches a terminal position without revisiting an earlier state. The retrograde propagation therefore requires only the recursive determination of wins and losses, eliminating the need for special mechanisms to detect repetition-induced draws.

This does not necessarily make retrograde analysis fundamentally different, since the underlying dynamic programming principle remains the same. However, it substantially simplifies the implementation. The absence of cycles means that every unresolved position must eventually be classified as either a win or a loss once all successors have been processed, avoiding one of the principal algorithmic complications addressed in the checkers databases.

**Refined write-up.**

The win/loss asymmetry is stated exactly right — *win* is existential (one losing
successor suffices), *loss* is universal (all successors must be wins) — and that
asymmetry is the engine of the whole backward pass. The FLIPHEX conclusion is
right too, but you undersell it: this is not merely "substantially simpler
implementation", it is a **change of algorithm class**.

**Checkers needs a fixpoint iteration; FLIPHEX needs a single sweep.** Because
checkers' game graph has cycles (non-capture king moves return to earlier
positions), values cannot be assigned in one pass — the computation must iterate
until nothing changes, and positions that never resolve are draws by repetition.
FLIPHEX's graph is a **DAG stratified by ply**: every move fills exactly one cell,
so `t` strictly increases and layer `t` depends only on layer `t+1`. You process
`t = 25, 24, 23, …` once each, in order, and you are done. No iteration, no
convergence test, no draw category. That also means the pass is trivially
streamable — one layer in memory at a time — which is exactly what makes the
storage argument in §2.3 tractable.

**And you get a bigger free win than you credited: the GHI problem disappears.**
§4 of the paper describes *graph-history interaction* — the same position reached
by two move sequences can have different values because draw-by-repetition depends
on the path — and notes that *"part of this research project was to develop an
improved algorithm for addressing the GHI problem."* GHI is a research
contribution in its own right, and it exists only because of repetition draws.
FLIPHEX has neither, so the position is genuinely path-independent, which is the
same Markov property that licenses the transposition table
([R&N note](notes/russell-norvig-aima-ch6-adversarial-search.md) §6.3.2). One
assumption, three consequences.

A caution worth carrying forward, though: no-draw is not a pure gift. It
simplifies the *backward* pass, and it makes the *forward* proof harder — see the
refinement to §6.1, where the absence of an intermediate value removes the
partial-proof shortcut Schaeffer leans on.

### 2.2 — Convergence: why this worked for checkers and may not for FLIPHEX
**Prompt.** *This is the load-bearing prompt of the whole note.* The paper notes
that "the checkers forced-capture rule quickly results in many pieces being
removed from the board, giving rise to a position with ≤10 pieces – and a known
value." Checkers is a **converging** game: material only decreases, so the
≤10-piece region is a funnel every long game is forced into.

FLIPHEX is **diverging** by Allis's formal criterion (Def. 6.1 — for the
majority of edges in the piece-count class graph the successor class is larger:
15 growing layers versus 10 shrinking ones). But be careful with what that label
does and does not imply — Allis's own example is Othello, and he qualifies it:
*"Except for the endgame, the number of legal positions increases."* FLIPHEX's
layer profile is a **hump**, peaking at ply 15 (1.1 × 10¹⁷) and collapsing to
3.4 × 10⁷ at ply 25. The endgame is the *narrowest* part, not the widest.

So the interesting question is not "is the FLIPHEX endgame too big to enumerate"
(it is not), but **what a database of the last `k` plies actually buys**. Answer
four things. (a) Why does convergence make a 10-piece database *cover* the game
rather than decorate it — and note the key structural fact: in checkers "≤10
pieces" is decoupled from move number, so it can be entered early and cover a
long tail of play. In FLIPHEX, `k` empty cells **is** ply 25−k, rigidly. (b) Get
the checkers 10-piece database size from the paper and compare honestly against
FLIPHEX's k≤3 ≈ 9 × 10¹², k≤4 ≈ 1.5 × 10¹⁴, k≤5 ≈ 1.2 × 10¹⁵ (upper bounds) —
check the exponents carefully, the answer is not the one the shape of the
question suggests. (c) Each ply further back costs roughly 5–10× more positions;
what does that imply for how deep a FLIPHEX endgame database can usefully reach?
(d) Given all of the above, is the answer to prompt 1.2 that FLIPHEX 5×5 *is*
within reach, or that state count was never the binding constraint? Say which,
and name the quantity that actually binds.

**My take.**

The effectiveness of the checkers solution depends fundamentally on the game's **converging** state-space structure rather than on its absolute size. As pieces are captured during play, the number of legal positions decreases dramatically, so every sufficiently long game is forced into a comparatively small family of endgame positions. Consequently, solving all positions with ten or fewer pieces is not merely an optimization: it creates a common destination through which essentially every line of play must eventually pass. Once play reaches this region, exact game-theoretic values become available, allowing the forward proof to terminate by connecting to the solved database.

FLIPHEX has the opposite structural property. Every move permanently adds one occupied cell, causing the state space to expand as the game progresses. Instead of converging toward a narrow endgame, legal play moves toward the largest layers of the game graph. Therefore, a retrograde database covering only the final few plies does not naturally intercept most games in the same way that a ten-piece database does in checkers. The database remains correct, but its strategic leverage is substantially reduced because there is no narrow funnel through which every game must pass.

The numerical comparison reinforces this structural distinction. The estimated upper bounds for FLIPHEX are approximately \(9 \times 10^{12}\) positions for \(k \leq 3\) empty cells, \(1.5 \times 10^{14}\) for \(k \leq 4\), and \(1.2 \times 10^{15}\) for \(k \leq 5\). These values remain below the size of the ten-piece endgame databases reported for checkers. Purely in terms of database size, a FLIPHEX \(k \leq 5\) retrograde computation therefore appears to be within a range that is not unprecedented.

However, this observation does not overturn the conclusion reached in Prompt 1.2. The limiting factor is not the raw number of stored states but the structural role played by those states within the game graph. In checkers, the solved endgame region covers the game because nearly every line is forced into it by progressive material reduction. In FLIPHEX, the corresponding endgame region occupies one of the widest parts of the state space, so solving it does not provide the same coverage of earlier play.

Thus, the principal lesson is that state-space size alone is an insufficient predictor of solvability. The decisive property is whether backward-computed knowledge naturally propagates through the game graph to the initial position. Checkers possesses this converging structure; FLIPHEX does not. Consequently, the apparent similarity in database size should not be interpreted as evidence that the full 5×5 game is comparably easy to solve.

**Refined write-up.**

**You were right to push back on the prompt, and the prompt was wrong.** The
original wording claimed the FLIPHEX endgame is "the *widest* part of the state
space". It is not — it is the narrowest. Your reasoning in chat (fewer tiles left,
fewer empty cells, many paths funnelling into few terminal configurations) is
correct, and the arithmetic confirms it:

| ply `t` filled | `k` empty | positions | share |
|--:|--:|--:|--:|
| 8 | 17 | 9.8 × 10¹³ | 0.0% |
| **15** | **10** | **1.09 × 10¹⁷** | **22.3%** ← peak |
| 20 | 5 | 1.05 × 10¹⁵ | 0.2% |
| 22 | 3 | 9.0 × 10¹² | 0.0% |
| 25 | 0 | **3.4 × 10⁷** | 0.0% |

The profile is a **hump**: it climbs for 15 plies and collapses for 10. There are
only 33.6 million terminal positions in the whole game. The prompt conflated the
*label* "diverging" with a claim about the endgame, and that inference does not
follow. Allis himself flags it — his diverging example is Othello, and he writes
*"**Except for the endgame**, the number of legal positions increases as the
number of stones on the board increases."* The label is assigned by his Def. 6.1
(majority of class-graph edges lead to a larger class: 15 growing versus 10
shrinking), so FLIPHEX *is* formally diverging — but the label says nothing about
the shape of the last few plies. Both halves of your take that repeat the prompt's
premise ("legal play moves toward the largest layers of the game graph"; "the
corresponding endgame region occupies one of the widest parts") should come out.

**Now the factual error, which runs the other way.** You wrote that the FLIPHEX
figures "remain below the size of the ten-piece endgame databases reported for
checkers." Check the exponents. The paper: *"a database of 3.9 × 10¹³ positions"*
— so k≤3 (9.0 × 10¹²) is about **a quarter** of checkers', k≤4 (1.5 × 10¹⁴) is
**~4× larger**, and k≤5 (1.2 × 10¹⁵) is **~30× larger**. Only k≤3 is comfortably
below. That inverts your "not unprecedented" conclusion for the `k ≤ 5` target
that adr-004 currently commits to.

**So what is the real structural difference?** Not width — *reach in game-time*.
In checkers, "≤10 pieces" is a **material** condition, decoupled from move number:
a game can enter that region at ply 20 and stay in it for another forty, so the
database covers a long tail of actual play. In FLIPHEX, `k` empty cells **is** ply
25−k, rigidly — one cell fills per ply, no exceptions. A `k ≤ 3` database covers
exactly the last 3 plies of a 25-ply game, or 12%, and nothing you do changes
that. Buying more reach costs ~5–10× positions per additional ply (k=3→4 is 15×,
4→5 is 7.7×), so covering even half the game means enumerating essentially the
whole state space. *That* is what Allis's "endgame databases are generally
unfeasible for diverging games" actually means operationally, and it is a claim
about coverage, not about layer size.

Your conclusion therefore survives — state count was never the binding constraint
— but the supporting argument needs replacing wholesale. And note what this does
*not* say: the FLIPHEX endgame database is perfectly feasible and every game is
guaranteed to pass through it. It just cannot be made deep enough to meet a
forward proof coming down from a root with b = 1450. The two ends do not reach
each other; that is the 5×5 obstacle, stated precisely.

### 2.3 — Storage, indexing and compression
**Prompt.** Retrograde analysis is an I/O problem before it is a search problem.
Find what the paper (and the supporting online material) says about how the
databases are **stored, indexed, and compressed**, and about the distinction
between what is kept on disk and what is recomputed. FLIPHEX's 4×4 solve is
~9.3 × 10¹⁰ states ≈ 23 GB at 2 bits each — squarely in the regime where these
choices decide feasibility. Which specific techniques would transfer, and which
depend on checkers-specific structure (piece counts, symmetry) FLIPHEX lacks?

**My take.**

The paper makes it clear that large-scale retrograde analysis is primarily a data-management problem rather than a search problem. Once the recursive propagation rules are established, the dominant engineering challenges become storing, indexing, and efficiently accessing enormous collections of solved positions.

The endgame databases are organized by material configuration, with separate databases constructed incrementally for positions containing increasing numbers of pieces. This partitioning allows each database to be generated using already-solved smaller databases while limiting the amount of information that must be accessed simultaneously.

The Supporting Online Material explains that compact encodings and carefully designed indexing functions are essential. Rather than storing complete board descriptions, positions are mapped to compact indices so that each legal position corresponds to a unique database entry. Since each position ultimately requires only a small game-theoretic value (win, loss, or draw), aggressive bit packing substantially reduces storage requirements.

The implementation also distinguishes between persistent data and transient computation. Solved position values are retained because they will be referenced repeatedly during later construction stages, whereas intermediate working structures used during database generation need not be preserved once a stage has completed. This tradeoff reduces permanent storage at the cost of recomputation where appropriate.

Several of these engineering principles transfer directly to FLIPHEX. Compact value encoding (e.g., two bits per position), deterministic indexing from game states to array locations, sequential processing of database layers, and minimizing random I/O are independent of the game itself. These techniques remain applicable whenever the complete state space is explicitly enumerated.

Other optimizations depend on structural properties specific to checkers. Database partitioning by remaining piece count follows naturally from material reduction during play. Efficient indexing exploits the representation of distinguishable piece types and legal material configurations. Symmetry reductions also benefit from the geometric and piece-specific properties of the game. FLIPHEX lacks this material-count hierarchy, since the number of occupied cells only increases, and its indexing scheme would instead be organized by the number of empty cells or move depth. Likewise, any symmetry reduction must be derived from the board geometry alone rather than from interchangeable piece configurations.

For a complete 4×4 FLIPHEX solver, where approximately \(9.3 \times 10^{10}\) states require only about 23 GB at two bits per state, these implementation choices become first-order design decisions. The feasibility of the solver depends not only on the storage capacity but also on constructing an indexing scheme and access pattern that permit efficient retrograde propagation over tens of billions of positions.

**Refined write-up.**

The transfers-versus-doesn't-transfer split is well drawn, and spotting that
FLIPHEX's natural partition is *empty-cell count* rather than material is exactly
right — that is the layer index the §2.1 single-sweep algorithm runs on. But you
missed the paper's most consequential number, and it changes the project's
arithmetic by two orders of magnitude.

**39 trillion positions compressed into 237 gigabytes — "an average of 154
positions per byte!"** That is ~**0.05 bits per position**, not the 2 bits you
assumed. The paper is explicit about why it is achievable and what constraint it
must respect: *"A custom compression algorithm was used which allows for rapid
localized real-time decompression … the backward and forward search programs can
quickly extract information from the databases with a relatively small
overhead."* The hard requirement is **random access into compressed data**, not
compression ratio in the abstract — a whole-file gzip would hit a similar ratio
and be useless.

Re-run the FLIPHEX numbers at that ratio, alongside the 2-bit figure you used:

| target | positions | @ 2 bits | @ 154 pos/byte |
|---|--:|--:|--:|
| 4×4 full solve | 9.3 × 10¹⁰ | 23 GB | **0.6 GB** |
| 5×5 endgame k≤3 | 9.0 × 10¹² | 2.3 TB | **61 GB** |
| 5×5 endgame k≤4 | 1.5 × 10¹⁴ | 37 TB | **~1 TB** |
| 5×5 endgame k≤5 | 1.2 × 10¹⁵ | 300 TB | **~7.8 TB** |

This matters directly: I earlier advised (from raw counts) that `k ≤ 3` should be
the commitment and `k ≤ 4` the stretch. At Schaeffer-class compression, k≤4 is a
1 TB external drive and k≤5 is a NAS purchase rather than an impossibility. The
storage argument was too pessimistic by ~40×. **Caveat, and it is a real one:**
154 positions/byte reflects checkers endgame structure — long runs of identical
win/loss/draw values under a material-based index. FLIPHEX's compressibility under
an empty-cell index is *unmeasured*, and the honest move is to measure it on 3×3
and 4×4 (where the whole space is enumerable) before committing a `k` in the ADR.
That is a concrete, cheap Phase-3 experiment worth pre-registering.

One correction to the transfer list: you write that checkers' "symmetry
reductions also benefit from … piece-specific properties" and imply FLIPHEX must
derive symmetry from geometry alone. True, but the useful consequence is more
specific — per [adr-008](docs/adr/adr-008-board-mirror-symmetry.md) the Z/2 mirror
becomes a *full* symmetry precisely once both chiral `P3-y` tiles are placed,
which is a condition on the *endgame*. So mirror-canonicalising the index is
available exactly where the databases live, for a clean ~2× on top of compression.
Worth building into the indexing function from the start rather than retrofitting.

---

## §3 — The architecture: backward and forward meeting in the middle

### 3.1 — The three components, and the shape of the proof
**Prompt.** The paper lists the proof procedure's three algorithm/data components.
Name them and draw the picture: the endgame databases growing *up* from the end,
the proof tree growing *down* from the opening, and what happens where they meet.
Why is this a **proof** rather than merely very strong play — what exactly is the
logical claim at the junction? Then map it onto adr-004, which already has the
same two halves (retrograde DBs + alpha-beta) but currently describes them as
*independent* deliverables rather than as two ends of one proof. Should adr-004
be rewritten around the meet-in-the-middle framing? Argue both sides.

**My take.**

The proof procedure consists of three interacting components. First, retrograde analysis constructs exact endgame databases by propagating game-theoretic values backward from terminal positions. Second, a forward search starting from the initial position builds a proof tree using game-tree search. Third, an interface connects these two computations by terminating the forward search whenever a position already exists in the solved endgame databases.

Conceptually, the computation proceeds from both directions simultaneously. The endgame databases grow upward from terminal positions toward increasingly complex game states, while the forward proof tree grows downward from the initial position. The proof is completed when every leaf of the forward search enters a region of the state space whose game-theoretic values have already been established by retrograde analysis.

The logical claim at this junction is stronger than "the program plays well." Each leaf of the forward proof tree is not evaluated heuristically but replaced by an exact theorem supplied by the endgame database. Since the forward search is itself an exact minimax computation, every propagated value remains mathematically sound. The resulting argument forms a complete proof that the game-theoretic value assigned to the initial position is correct.

This architecture differs fundamentally from a conventional game-playing engine. A strong playing program estimates values heuristically beyond its search horizon. Here, no heuristic evaluation is required once the search reaches the solved database. The horizon is replaced by exact knowledge, eliminating approximation from the proof.

The architecture described in ADR-004 already contains the same two principal components: retrograde databases and alpha-beta search. However, they are currently presented as largely independent deliverables. The meet-in-the-middle interpretation offers a stronger conceptual organization by emphasizing that these components jointly establish a single proof rather than solving separate engineering problems.

There are, however, reasonable arguments for retaining the current ADR structure. From a project-management perspective, separating the retrograde database from the forward solver produces clearer implementation milestones and independently testable artifacts. Conversely, if the ADR aims to justify the solver architecture rather than the development schedule, reorganizing it around the meet-in-the-middle proof would better reflect the paper's central contribution. The decision therefore depends on whether the ADR is intended primarily as an implementation roadmap or as an architectural rationale.

**Refined write-up.**

The meet-in-the-middle picture is right, the "exact theorem replaces the horizon"
formulation is the best sentence in the note, and framing the ADR question as
*roadmap versus rationale* is a genuinely good way to hold both sides. Two fixes.

**The third component is not an interface.** The paper's list is: *1. Endgame
databases (backward search)*, *2. Proof-tree manager (forward search)*, *3. Proof
solver (forward search)* — and of the solver it says *"this component uses two
programs to determine the value of the position. These programs approach the task
in different ways, thus increasing the chances of obtaining a useful result."*
The junction between forward and backward is not a component; it is just a
database lookup at the solver's leaves. Getting this right matters because
component 3 is where the paper's redundancy lives — two independent programs
attacking the same position — which is a design decision, not an implementation
detail, and it feeds §5.1.

**Your ADR argument is missing the fact that decides it.** You framed it as a
presentational choice. It is not: adr-004's two halves currently target
*different boards* — retrograde on the full 5×5 endgame, alpha-beta as a
depth-limited 5×5 agent, and reduced-variant solves as a third, separate thing.
They are not two ends of one proof; they never meet. Schaeffer's architecture is
a single proof of a single position. So the honest reading is that adr-004 is
**not** a meet-in-the-middle design today, and the question is whether it should
become one. My reading of the numbers (§2.2, §1.2) is that on 5×5 it *cannot* —
the endgame database cannot be pushed deep enough to meet a forward proof from
b = 1450 — and on 4×4 it is *unnecessary*, because a full enumeration solves the
whole board without needing a forward proof at all. Meet-in-the-middle is the
right architecture for a game whose two ends can actually be joined; FLIPHEX 5×5
is precisely the case where they cannot.

That is worth writing into adr-004 explicitly, because "we considered the
architecture that solved checkers and it does not apply here, for this reason" is
a much stronger ADR than silence. Keep the current three-deliverable structure;
add the rejected alternative.

---

## §4 — Forward search: the proof tree

### 4.1 — Proof-tree manager and solvers, and "least work"
**Prompt.** Describe the split between the proof-tree manager (which decides
*what* to prove) and the solvers (which prove individual positions). The key idea
is that a proof tree is **much smaller than a full search tree** — you need only
one refutation per opponent move, but all moves for your own. Connect this to the
`b^{d/2}` result in the [R&N note](notes/russell-norvig-aima-ch6-adversarial-search.md)
§6.3.1: is the proof tree the *same* object as the Knuth–Moore minimal tree, or
something different? Then: adr-004 parked proof-number search as "a good
extension if the paper track activates" — does this paper reopen that decision?

**My take.**

_(você escreve, em primeira pessoa)_

**Refined write-up.**

_(preencho depois que você compartilhar seu take)_

### 4.2 — Where the effort actually went
**Prompt.** The paper describes the manager choosing which positions to expand
and notes it "may spend unnecessary effort looking for an" (see the paper — the
extraction garbles this passage). Get the real sentence and capture the failure
mode being described. What does this say about the *scheduling* problem in a long
exact computation, and does FLIPHEX's 4×4 solve have an analogous choice, or is
it a single undifferentiated enumeration pass?

**My take.**

The forward-search component is divided into two distinct responsibilities. The proof-tree manager determines which positions require proof and allocates computational effort across the evolving proof tree. Individual solvers are then responsible for proving the game-theoretic value of specific positions assigned by the manager. This separation allows global proof construction to remain independent of the algorithms used to solve individual subproblems.

The paper emphasizes that the proof tree is substantially smaller than the complete search tree because not every branch must be explored to the same extent. At positions where the side to move seeks to establish a win, every opponent response must be addressed to ensure that no refutation exists. Conversely, for each opponent move, it is sufficient to identify a single continuation that preserves the desired game-theoretic value. Consequently, the proof records only the evidence required to establish the theorem rather than every possible continuation of play.

This resembles the minimal-tree analysis of Knuth and Moore discussed by Russell and Norvig, but the two concepts are not identical. The minimal tree is a theoretical lower bound on the amount of search required by alpha-beta under perfect move ordering. It characterizes search complexity independently of any particular proof representation. The proof tree, by contrast, is the explicit mathematical object certifying the result. Although both exploit the asymmetry between existential ("there exists a winning move") and universal ("every opponent move must be answered") reasoning, the proof tree serves as a correctness certificate rather than merely a complexity bound.

The architecture also relates naturally to Proof-Number Search (PNS). Like PNS, the proof-tree manager attempts to direct computational effort toward unresolved parts of the proof rather than expanding the game tree uniformly. However, the paper does not describe the manager as implementing PNS, nor does it rely on proof and disproof numbers as its central mechanism.

For ADR-004, this paper provides additional motivation to reconsider the earlier decision to postpone proof-oriented search methods. The central role of explicit proof construction suggests that proof-directed search deserves architectural consideration. Nevertheless, the paper alone does not justify replacing alpha-beta with PNS. Instead, it supports viewing proof-oriented search as a potentially valuable extension whose benefits should be evaluated separately from the core meet-in-the-middle architecture.

**Refined write-up.**

*(Note: this answers prompt **4.1**, not 4.2 — 4.1's slot above is still empty and
4.2's actual question, about the manager's failure mode, is unanswered. Worth
moving this text up; the missing 4.2 answer is sketched at the end here.)*

The manager/solver split and the existential-vs-universal asymmetry are correct,
and the Knuth–Moore distinction is the sharpest thing in the note: the minimal
tree is a *complexity bound*, the proof tree is a *certificate*. Keep that
wording. But the claim that decides the ADR question is wrong.

**Proof-number search is not absent from this paper — it is the manager's core
algorithm.** The text: *"The manager maintains the master copy of the proof, and
identifies a prioritized list of positions that need to be examined **using the
Proof Number search algorithm** (6)."* Reference (6) is Allis. The paper also
names the **Df-pn** variant — *"builds the search tree in a depth-first manner,
requiring less computer storage"*. So the largest game-solving result ever
published uses PN-search as the scheduler that decides *what to prove next*, with
alpha-beta (Chinook, 17–23 ply) as the solver underneath.

This forces a correction to something **I** wrote, not just to your take. The
adr-004 Phase 2 amendment argued that pn-search "loses its structural edge" on
FLIPHEX because pn-search shines on *sudden-death* goal-proving and FLIPHEX is
fixed-termination. Checkers is **also fixed-termination** (Allis classifies it
so), and pn-search is central to its proof anyway. That argument was wrong as
stated.

What survives, and is the right distinction: adr-004 rejected pn-search *as a
replacement search paradigm* — a second full engine to build, debug and explain.
That rejection still stands. What adr-004 never considered is pn-search in
Schaeffer's actual role: a **work scheduler over a proof tree**, sitting above
ordinary alpha-beta solvers. Those are different decisions and the ADR conflates
them. The amendment should be corrected to say so, and the honest verdict is your
last sentence — reopened as a scoped extension, not adopted.

Two more things the paper gives that belong in the ADR's thinking. First, the
manager iterates not on depth but **on the error threshold of the heuristic
score** (`t`, raised by ∆ until it reaches a win): sketch the proof outline
cheaply, then fill in detail. Second — and this is the missing **4.2** answer —
the manager is bootstrapped by a human-supplied line: *"From the human
literature, a single 'best' line of play was identified and used to guide the
initial foray of the manager… Without it, the manager may spend unnecessary
effort looking for an important line to explore. The line leads from the start of
the game into the endgame databases."* **FLIPHEX has no human literature.** There
are no book openings, no expert lines, nothing to seed the manager with — the
same "no domain knowledge" hole that R&N §6.3.2 identified for the evaluation
function, reappearing in the scheduler. The obvious substitute is a policy from
Axis 2: the learned network supplies the seed line that human masters supplied
for checkers. That is a genuine, non-obvious cross-axis use of the learner — the
solver consuming the learner's output rather than merely being checked against it
— and it belongs in synthesis **S4**.

---

## §5 — Correctness: how you defend an 18-year computation

### 5.1 — The verification discipline (the section nobody expects to need)
**Prompt.** The authors ask "Are the results correct?" and list the defences:
sources of error they anticipated (algorithm bugs, data transmission errors),
verification of computation results, consistency checks, and independent
re-verification. Catalogue them precisely.

Then the FLIPHEX question, which currently has **no ADR and no answer**: the 4×4
solve will be a ~10¹¹-state enumeration whose output is a single verdict for H1.
Nobody can eyeball it, and a silent bug produces a *plausible* wrong answer, not
a crash. What would the FLIPHEX analogue of each defence be? Consider at least:
solving 3×3 by two independent methods and requiring agreement; invariants that
must hold across the whole database (e.g. no draws — 25 cells is odd, so *any*
draw value anywhere is a proof of a bug); re-deriving a random sample of entries
by direct search; and checksumming. This prompt is expected to produce a new ADR
— draft its Decision section here in one paragraph.

**My take.**

The paper treats correctness as a first-class engineering problem rather than a post hoc validation step. Because the computation spans many years and processes an enormous state space, the principal risk is not an obvious program failure but a subtle error that propagates unnoticed into the final proof. The authors therefore defend the result through multiple, complementary verification mechanisms rather than relying on confidence in a single implementation.

The paper identifies several categories of potential failure, including algorithmic defects, hardware faults such as data transmission or storage errors, and implementation mistakes capable of silently corrupting intermediate or final results. To mitigate these risks, the project employed multiple layers of verification: extensive consistency checks during computation, independent re-verification of computed databases and proof components, and validation procedures designed to detect corruption even when the computation itself completed successfully. The underlying philosophy is that no single computation, regardless of scale, should be trusted without independent evidence supporting its correctness.

For FLIPHEX, the same verification philosophy applies despite the much smaller state space. A complete 4×4 solution would enumerate approximately \(10^{11}\) states, making manual inspection impossible while allowing subtle implementation errors to produce entirely plausible—but incorrect—results. Consequently, correctness should be established through mutually reinforcing verification mechanisms rather than a single successful execution.

Natural analogues include: (1) independently solving the complete 3×3 game using two fundamentally different methods (for example, exhaustive forward search and retrograde analysis) and requiring identical game-theoretic values; (2) enforcing global invariants over the database, such as the absence of draw values if the game rules mathematically preclude draws; (3) randomly selecting solved positions and independently re-deriving their values through direct search without consulting the database; (4) validating database integrity using cryptographic checksums or equivalent mechanisms to detect accidental corruption during storage or transmission; and (5) continuously checking structural consistency properties throughout database construction rather than only after completion.

**Draft ADR Decision.** The FLIPHEX solver shall treat correctness as an explicit architectural concern rather than an implementation detail. No computed database or game-theoretic result shall be accepted solely on the basis of successful execution. Instead, correctness shall be established through independent verification, global invariant checking, integrity verification of stored data, and cross-validation against independently implemented reference solvers on tractable subproblems. The final solution shall be considered valid only if all verification mechanisms agree.

**Refined write-up.**

The strongest section of the note, and the draft Decision is close to shippable —
"no computed database or result shall be accepted solely on the basis of
successful execution" is the right load-bearing sentence. Three additions, one of
which is a verification FLIPHEX gets that checkers could not have.

**Be careful attributing detail the paper does not give.** Your second paragraph
reads as a catalogue drawn from the paper, but §5 is only four sentences long:
sources of error (*"algorithm bugs and data transmission errors"*), *"verifying
all computation results and doing consistency checks"*, and *"some of the
computations have been independently verified"*. "Cryptographic checksums",
"validation procedures designed to detect corruption" and "continuous structural
consistency checking" are sensible engineering, but they are yours, not
Schaeffer's — mark them as such or the note becomes a miscitation. The paper's
*actual* redundancy mechanism is architectural and you can cite it: component 3
uses **two different programs** on the same position, *"thus increasing the
chances of obtaining a useful result"*.

**FLIPHEX has a closed-form ground truth for a whole layer.** The terminal layer
is only **3.4 × 10⁷ positions** (2²⁵ colourings, hands forced), and each one's
value is decided by simply counting cells — no search, no recursion. So the entire
base case of the retrograde pass can be verified exhaustively, in seconds, against
a definition rather than against another implementation. Checkers had nothing
comparable; its terminal set is not enumerable in closed form. That should be
verification #0 in the ADR, because a bug in the base case silently poisons every
layer above it.

**Add layer-count verification — it catches the most likely bug class.** The
number of positions in layer `t` is known in closed form
(`C(25,t)·2^t·C(13,⌈t/2⌉)·C(12,⌊t/2⌋)`, modulo reachability). Counting what the
enumerator actually produces per layer and comparing against the formula is the
FLIPHEX analogue of chess's `perft`, and it detects the failure mode your list
does not cover: not *wrong values*, but **missing or duplicated states**. A
retrograde pass over an incomplete enumeration produces perfectly
self-consistent, perfectly wrong answers, and would pass every check in your
current draft. Note the subtlety that makes this doubly useful: the formula is an
*upper* bound (the `2^t` factor assumes every colouring is reachable), so the gap
between formula and actual count is itself the reachability measurement that
§2.3 wants for calibrating `k`. One instrument, two jobs.

Your no-draw invariant is the right instinct and worth stating in its strongest
form: 25 is odd, so *every* terminal position has a strict winner, and a draw
value appearing anywhere in the database is a proof of a bug — not evidence of
one. That is a genuine theorem-backed assertion, cheap to check on every write.

Add these three to the Decision paragraph and it is ready to become an ADR.

### 5.2 — What the authors do *not* claim
**Prompt.** Read the correctness discussion adversarially. Is the claim "this is
proved correct" or "we have taken great care and found no errors"? Note the exact
hedging. How should that calibrate the wording of FLIPHEX's own H1 verdict —
specifically, what is the strongest sentence you are entitled to write about a
4×4 result produced by one implementation, run once, by one person?

**My take.**

The correctness discussion is deliberately cautious. The authors do not claim that the computation is infallible or that correctness has been established beyond all conceivable doubt. Instead, they argue that numerous independent verification procedures were designed to detect the classes of errors considered most plausible, and that these procedures consistently found no evidence of incorrectness.

The distinction is important. The mathematical argument underlying the solver is exact, but the implementation executing that argument is a large software and hardware system that cannot itself be proven correct merely by producing an output. Consequently, the paper's confidence derives not from a single computation but from the convergence of multiple, largely independent sources of evidence supporting the same conclusion.

This calibration has direct implications for FLIPHEX. A 4×4 result produced by a single implementation, executed once by a single researcher, should not be described as definitively proving the game-theoretic value of the initial position. Even if the algorithm is mathematically sound, the empirical evidence supporting the implementation remains limited.

The strongest defensible claim under those conditions would be that the implementation computed a specific game-theoretic value and that no inconsistencies were detected by the verification procedures that were applied. Stronger language—such as claiming that the result has been conclusively proven—would require substantially broader evidence, including independent implementations, reproducibility across executions and platforms, comprehensive invariant checking, and systematic verification of the generated databases.

Accordingly, the wording of H1 should remain proportional to the available evidence. Scientific claims should reflect not only the theoretical correctness of the algorithm but also the strength of the verification process supporting the computation.

**Refined write-up.**

Nothing to correct — this is the most disciplined take in the note, and the
distinction you draw (the *argument* is exact; the *system executing it* is not,
and cannot be validated by producing output) is precisely the right one. Two
things to bank.

**The paper's own hedging is even more explicit than you found, and it is worth
quoting in the writeup.** §7 concedes: *"Despite the convincing result, some
mathematicians were skeptical, distrusting proofs that had not been verified using
human-derived theorems"* and *"Although important components of the checkers proof
have been independently verified, there may be skeptics."* Note what that second
sentence admits — only *components*, not the whole, were independently verified,
and the authors decline to claim the objection is answered. If a Science paper
backed by 18 years and 50 machines writes that, the calibration for a solo project
is set.

**The sentence you are entitled to write, concretely.** Your final paragraph
argues for proportionality but stops short of drafting it. Something like: *"An
exhaustive retrograde enumeration of the 4×4 variant (deck per adr-009) assigns
the initial position the value W. The computation passed all verification
procedures in adr-0NN — closed-form terminal-layer check, per-layer state counts
against the combinatorial formula, no-draw invariant, and agreement with an
independent forward solver on the full 3×3 game and on a random sample of 4×4
positions. It has not been independently reimplemented."* That last clause is what
makes the rest credible, and it costs nothing.

This also settles the wording question for **H1**: the verdict column should carry
the *evidence class*, not just the verdict. "Supported (exact, single
implementation, verified by N independent checks)" is honest and still strong.
Worth building into `research.md`'s verdict table before the hypotheses lock.

---

## §6 — Results and cost

### 6.1 — The 19 openings, and solving by doing the least work
**Prompt.** The stated approach is "to determine the game-theoretic result by
doing the least amount of work." Unpack the concrete instance: ~300 three-move
openings, over 100 duplicates by transposition, the rest "proven to be irrelevant
by an Alpha-Beta search", leaving **19** to be solved outright. Explain what
"irrelevant" means here — it is a precise claim, not hand-waving.

Now FLIPHEX: ply 1 has **1450** legal moves. What are the available reductions?
Consider (a) transpositions, (b) the Z/2 board mirror — but note
[adr-008](docs/adr/adr-008-board-mirror-symmetry.md) says it is only a *partial*
symmetry while a chiral `P3-y` is in hand, so be careful about when it applies at
the root, and (c) the alpha-beta "irrelevance" argument above, which needs only a
*bound*, not a value. Is there a FLIPHEX analogue of "19 openings", and does the
answer differ between 4×4 and 5×5?

**My take.**

The paper's guiding principle is to determine the game-theoretic value of the initial position while performing only the computation that is logically necessary for the proof. This philosophy is reflected in the treatment of opening positions.

Approximately 300 distinct three-move openings were initially considered. More than one hundred of these were eliminated because they were equivalent through transpositions, reducing the number of genuinely distinct opening positions. The remaining openings were then analyzed by alpha-beta search. For many of them, the search established that their exact game-theoretic values could not influence the proof of the initial position. These openings were therefore classified as irrelevant, leaving only nineteen openings whose values had to be determined explicitly.

The term "irrelevant" has a precise logical meaning. It does not imply that the positions are uninteresting or unsolved. Rather, it means that the proof of the initial position can already be completed without computing their exact values. Alpha-beta establishes bounds sufficient to show that these branches cannot alter the minimax value propagated to the root. Once this has been proven, further computation on those branches cannot change the final theorem and is therefore unnecessary.

The same principle is applicable to FLIPHEX, although the available reductions differ. Transpositions remain a natural source of reduction whenever different move orders produce identical game states. Geometric symmetries can also reduce the root branching factor, but only when the game rules preserve those symmetries. According to ADR-008, the board mirror symmetry is only partially valid because of the known chiral pattern P3-y. Consequently, symmetry reduction cannot be applied indiscriminately at the root and must be restricted to positions for which equivalence has been formally established.

The alpha-beta notion of irrelevance is the most generally transferable idea. To prove the value of the initial position, it is unnecessary to compute the exact value of every branch. It is sufficient to establish bounds showing that certain branches cannot affect the root minimax value. This reduction depends on logical implication rather than on game-specific structure.

Whether FLIPHEX admits an analogue of the nineteen critical openings remains an open empirical question. A substantial reduction appears plausible for the 4×4 game, where exhaustive analysis is comparatively tractable. For the full 5×5 game, however, the much larger branching factor and the absence of the converging structure exploited in checkers make it difficult to predict comparable reductions without experimental evidence. The paper therefore motivates searching for such a critical subset but does not justify assuming that one necessarily exists.

**Refined write-up.**

The definition of "irrelevant" is exactly right — bounds, not values; logical
implication, not disinterest — and refusing to assume a FLIPHEX analogue exists is
the correct scientific posture. But there is a structural reason it *cannot* exist
in the form Schaeffer used, and it comes from the one FLIPHEX property you have
been treating as an unmixed blessing.

**No draws means no partial proofs.** Look at what the solver is allowed to
return: *"proven (win, loss, draw), **partially proven (at least a draw, at most a
draw)**, or heuristic."* That middle category is the engine of the whole "least
work" argument. Checkers' root value is a *draw*, so to discharge an opening you
need only bound it — show it is "at least a draw" for one side, "at most a draw"
for the other — and you never compute its exact value. Partial proofs are cheap;
full proofs are not.

FLIPHEX has no draw. The value set is `{win, loss}`, and on a two-element totally
ordered set **a bound is the value**: "at least a win" *is* a win; "at most a
loss" *is* a loss. There is no intermediate rung to bound against, so the
partially-proven category is empty by construction and every opening you touch
must be resolved outright. The alpha-beta cutoff still works within a search — α
and β still prune — but the *cross-opening* economy that reduced ~300 checkers
openings to 19 has no FLIPHEX counterpart.

So the honest catalogue of reductions available at a FLIPHEX root is shorter than
your take implies: transpositions (real, and large — the tree/state-space gap is
~10⁴³ on 5×5), and the Z/2 mirror (real but *unavailable at the root*, since
adr-008 makes it conditional on both chiral `P3-y` tiles being placed — which by
definition has not happened at ply 1). The third mechanism, bounding against an
intermediate value, is simply not there. 1450 openings on 5×5, roughly 725 after a
mirror fold that you cannot legally apply yet.

This is the second time in this note that "draws are impossible" cuts both ways —
it collapses the backward pass to a single sweep (§2.1) and it removes the
forward proof's main economy here. Both belong in the ADR, because the project has
so far treated no-draws purely as a simplification. It is not; it is a trade.

On 4×4 the point is moot: a full enumeration needs no opening reduction at all.
The asymmetry only bites on 5×5, which is exactly where §3.1 concluded the
meet-in-the-middle architecture already fails.

### 6.2 — The resource budget, honestly compared
**Prompt.** Collect the cost figures the paper gives: years elapsed, number of
machines/processors, the database sizes, when each phase ran. Then do the honest
comparison: FLIPHEX is a solo laptop project. Which parts of this pipeline are
*inherently* parallel-cluster-scale and which are only so because checkers is
1000× larger than FLIPHEX 5×5? Produce a one-line feasibility verdict for each of:
FLIPHEX 3×3, 4×4 (reduced deck), 5×5 endgame `k ≤ 3`, 5×5 full solve.

**My take.**

The paper presents the checkers solution as the culmination of approximately eighteen years of research. The computation relied on substantial computational infrastructure, including multiple generations of hardware, parallel processors, and large endgame databases whose construction and verification required significant storage and processing resources. Different components of the pipeline were developed and executed over different periods, with the endgame databases preceding the final proof construction by several years.

The scale of these resources should not be interpreted as an intrinsic requirement of the underlying algorithms. Retrograde analysis, alpha-beta search, database construction, and proof verification are fundamentally sequential algorithms with natural opportunities for parallel decomposition rather than inherently distributed algorithms. The use of multiple processors primarily reflects the size of the checkers state space and the practical desire to reduce computation time.

For FLIPHEX, the engineering picture differs substantially. Database indexing, retrograde propagation, proof-tree construction, and correctness verification all transfer directly as algorithmic ideas. Their implementation on a single workstation is primarily limited by memory capacity, storage bandwidth, and execution time rather than by any fundamental requirement for distributed computation.

A realistic feasibility assessment is therefore:

- **FLIPHEX 3×3:** Clearly feasible on a single laptop. Independent verification by multiple algorithms is also practical.
- **FLIPHEX 4×4 (reduced deck):** Feasible on a modern workstation or laptop, provided that storage layout, indexing, and I/O are carefully engineered. The principal challenge is implementation quality rather than computational scale.
- **FLIPHEX 5×5 endgame (k ≤ 3):** Plausibly feasible on a single machine, although execution time and storage management become significant engineering concerns. Experimental validation is required.
- **FLIPHEX 5×5 full solve:** The current evidence does not justify claiming feasibility. Although the estimated state-space size is substantially smaller than that of checkers, the diverging structure of the game implies that state-space size is not the limiting factor. Based on the arguments developed throughout the paper, the principal uncertainty lies in structural coverage rather than computational capacity.

**Refined write-up.**

The verdicts are sound and the key judgement — that cluster scale reflects
checkers' *size*, not an intrinsic property of the algorithms — is right and
important. Put the paper's actual figures behind it, because vague scale is what
makes people over- or under-estimate this kind of project:

| | figure |
|---|---|
| Project span | 1989–2007 (18 years) |
| 8-piece databases | 7 years (1989–1996); **the same computation took one month in 2001** |
| 10-piece databases | finished 2005; 3.9 × 10¹³ positions, 237 GB compressed |
| Processors | 200+ simultaneously in 1992; *"over the past year, we averaged using 50 computers continuously"* |
| Stored proof tree | 10⁷ positions |
| Forward search effort | ~10¹⁴ nodes |

The one-month-versus-seven-years line is the most useful number in the paper for
this project: the *same* computation, 84× faster, from hardware and algorithmic
improvement over five years. Nineteen more years have passed. A large part of what
looks like cluster-scale in 2007 is a laptop in 2026, and that supports your
feasibility verdicts more concretely than the general argument does.

Two corrections. **The 5×5 full-solve verdict cites the wrong reason.** You
attribute it to "the diverging structure" and "structural coverage" — but per the
corrected §2.2, the endgame layer is *narrow* and the database is feasible; what
fails is that its reach is rigidly capped at `k` plies while the forward proof
must descend from b = 1450. Name game-tree complexity (~10⁶¹, ~10³⁰·⁵ even at the
`b^{d/2}` limit) as the binding quantity. **And the `k ≤ 3` verdict is now too
conservative**: at Schaeffer's compression ratio that slice is ~61 GB, not a
storage problem at all. The open question there is compressibility, not capacity —
which is the experiment flagged in §2.3.

Revised one-liners:

- **3×3** — trivially feasible; use it as the two-method cross-validation fixture (§5.1).
- **4×4 (reduced deck)** — feasible on a laptop. ~9.3 × 10¹⁰ states; 23 GB at 2 bits, plausibly under 1 GB compressed. Engineering quality, not scale, is the risk.
- **5×5 endgame k ≤ 3** — comfortably feasible (~9 × 10¹² positions, ~61 GB compressed). `k ≤ 4` becomes a ~1 TB question and is worth attempting; `k ≤ 5` needs measured compression before it is promised.
- **5×5 full solve** — out of reach, and the reason is the forward proof, not storage. Worth stating in adr-004 with the number, since "we checked and here is the quantity that stops us" is a stronger claim than "almost certainly not".

---

## §7 — Conclusion and limits

### 7.1 — What the authors say the result means 🔄
**Prompt.** The Conclusion reflects on the scientific significance — note the
framing (AI + parallel computing, the bioinformatics transfer, the DEEP BLUE
comparison). What do the authors claim solving a game *buys*, beyond the game?
This is synthesis **S1** — put the cross-source argument there (Allis's "which
games will survive", R&N §6.7's four limitations, and this) and here only record
the one-line answer for FLIPHEX: what does an exact 4×4 verdict buy the project
that a strong learned agent does not?

**My take.**

The paper argues that solving checkers has significance beyond the game itself. The result demonstrates that long-term advances in artificial intelligence, large-scale search, database construction, and parallel computing can be integrated into a computation that produces a mathematically justified result. The authors also emphasize that techniques developed for this project have applications outside game playing, including problems in bioinformatics and other domains requiring large-scale combinatorial search.

The comparison with Deep Blue further clarifies the contribution. Whereas Deep Blue demonstrated that a machine could defeat the strongest human players, the checkers project establishes the game-theoretic value of the game itself. The scientific contribution is therefore not superior playing strength but a provably correct characterization of the game under perfect play.

For FLIPHEX, an exact 4×4 solution provides something that a learned agent cannot: a mathematically justified oracle for the game-theoretic value of every solved position within its scope, enabling exact validation of algorithms, hypotheses, and future approximations.

**Refined write-up.**

_(preencho depois que você compartilhar seu take)_

### 7.2 — The limitation this paper does not dwell on 🔄
**Prompt.** Checkers was solved and is now, in a real sense, a finished object.
The paper is upbeat about that. Read against it: what does the *design-study*
thesis of this project ([research.md](docs/research.md)) want from a solve —
strategy knowledge, balance verdicts, design feedback — and does a
win/loss/draw value at the root actually deliver any of it? A solved game tells
you the value; it does not tell you *why*. Where does that leave H5 (deck
balance) and H6 (counterfactual robustness), neither of which a root value can
answer? Feed the tension into **S4**.

**My take.**

The paper treats the game-theoretic value of checkers as the primary scientific objective. Once the initial position has been proven to be a draw under perfect play, the central research question has been answered. The solve transforms the game into a mathematically characterized object.

For the FLIPHEX project, however, the exact value of the initial position is not the final objective but an enabling result. A root win/loss/draw verdict establishes the game-theoretic outcome, but it does not explain why that outcome occurs, which strategic features determine it, or how alternative game designs would affect it.

Consequently, an exact solution directly supports H1 by establishing the game-theoretic value of the initial position and provides an oracle for subsequent experiments. However, it does not by itself answer questions about deck balance (H5) or counterfactual robustness (H6). Those hypotheses require comparative analyses across multiple game variants, structural examination of proof trees or solved databases, and counterfactual experimentation beyond the original solved game.

Thus, for FLIPHEX, the solve should be viewed as foundational infrastructure rather than the endpoint of the research program.

**Refined write-up.**

_(preencho depois que você compartilhar seu take)_

---

## Lessons Learned

his reading fundamentally changed my understanding of exact game solving. I initially viewed retrograde analysis as the primary algorithm and alpha-beta search as a separate optimization. Schaeffer instead presents them as two complementary halves of a single proof: backward analysis establishes exact game-theoretic values over a solved region of the state space, while forward search constructs the proof that the initial position reaches that region without ever relying on heuristic evaluation.

Another important shift was recognizing that the feasibility of an exact solve depends less on raw state-space size than on the structure of the game graph. The checkers result is enabled by convergence: progressive piece reduction forces play into a relatively small family of solved endgames. This provides a much stronger explanation than simply comparing state counts, and reframes how I should evaluate the prospects of solving FLIPHEX.

The paper also expanded my view of what constitutes a computational proof. Correctness is not guaranteed merely because the underlying algorithm is mathematically sound. Verification, independent rechecking, consistency testing, and data integrity become architectural concerns rather than implementation details. A solver is not only an algorithm but an evidence-producing system.

Finally, I came to see an exact solve as research infrastructure rather than the endpoint of a project. A solved game provides an oracle for validation, experimentation, and future analysis, but the game-theoretic value of the initial position alone does not explain strategy, balance, or design decisions.

## Failed Attempts

I initially assumed that the published result would be a strong solution because of the extensive retrograde databases. The paper explicitly claims a weak solution, reminding me to distinguish the capabilities of individual components from the formal claim made by the authors.

I also tended to compare games primarily through state-space size. The reading showed that this is an incomplete metric: structural properties such as convergence, decomposition, and proof coverage are often more important than the total number of reachable positions.

Another early assumption was that retrograde databases alone constituted the solution. The paper demonstrates that they are only one half of the proof; the forward proof tree is equally essential because it connects the initial position to the solved region.

Finally, I occasionally conflated a proof tree with the Knuth–Moore minimal search tree and treated proof-oriented search as synonymous with Proof-Number Search. The paper supports neither equivalence. These concepts are closely related but address different questions: complexity bounds, proof representation, and search strategy.
