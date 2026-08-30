# Takizawa (2023) — *Othello is Solved*

**Citation.** Hiroki Takizawa, "Othello is Solved", arXiv:2310.19387 (2023).
<https://arxiv.org/abs/2310.19387> · full text: <https://ar5iv.labs.arxiv.org/html/2310.19387>

**Which decision does this source inform?**
[adr-012](../docs/adr/adr-012-endgame-database-storage.md) — whether FLIPHEX
should materialise a retrograde endgame database at all, and if so from which
`k`. adr-012 is **Accepted** and defers the build decision to `EXP-003`; this
reading is what the pre-registered prediction (`k* >= 6`) should be checked
against **before** that experiment runs, not after.

**Why this source, and where it sits in the reading order.** Read **after**
Allis 1994 (the diverging/converging taxonomy) and **after** Schaeffer 2007 (the
retrograde route). Those two set up the expectation that a solve of this kind
means "build endgame databases". This paper is the counterexample, and it is the
counterexample from the game that is structurally closest to FLIPHEX.

Othello 8×8 shares every property that made the Phase 2 synthesis conclude
FLIPHEX is unlike checkers: it **diverges** (discs are placed, never removed),
its termination is at a **fixed** depth, its layer profile is a **hump** rather
than a funnel, and the number of empty squares is rigidly `N − ply`. It is the
only game with that profile that has been solved — and it was solved by forward
alpha-beta with transposition tables, with no endgame database materialised.
That makes it the single most relevant precedent in the project's reading list,
and it was not on the Phase 2 list.

Note the two places it is *not* analogous, and keep them in view while reading:
Othello's state space (~10²⁸) is eleven orders of magnitude larger than FLIPHEX
5×5's 4.9 × 10¹⁷, and its branching factor (~10) is two orders *smaller* than
FLIPHEX's opening 1450. Those cut in opposite directions.

**Cross-refs used throughout:**

- [adr-012](../docs/adr/adr-012-endgame-database-storage.md) — the consuming decision
- [adr-004](../docs/adr/adr-004-solver-approach.md) — alpha-beta + TT + retrograde, and its Phase 2 amendment
- [adr-010](../docs/adr/adr-010-solver-correctness.md) — V0–V6, and what "solved" obliges you to verify
- [notes/allis-1994-searching-for-solutions.md](allis-1994-searching-for-solutions.md) — the weak/strong/ultra-weak vocabulary and the diverging/converging split
- [notes/schaeffer-2007-checkers-is-solved.md](schaeffer-2007-checkers-is-solved.md) — the contrasting route
- [notes/phase2-synthesis.md](phase2-synthesis.md) S3, S4 — the hump argument and "4×4 is an enumeration problem"
- [docs/research.md](../docs/research.md) — H3's comparison set, H4's two complexity axes
- `experiments/registry.md` — EXP-003

**Legend.** 🔄 marks prompts that require synthesis with another source already
in `notes/`.

**Reading material.** Ingested 2026-08-05 —
[`notes/sources/takizawa-2023-othello-is-solved/`](sources/takizawa-2023-othello-is-solved/manifest.json)
(local only; `notes/sources/` is gitignored). 18 sections, ~5,500 words: this is
a short paper, and the whole method fits in §§8–12.

The prompts below are grouped by *question*, not by the paper's own numbering,
because the paper splits its method across seven small sections. Each group
names the section files it draws on.

**The manifest already corrects the scout's summary on one point: there are two
thresholds, not one** — `§09` obtains target positions at **50** empty squares
and `§10` at **36**. Read them as a pair; the two-stage structure is itself the
finding, and it is the part that maps onto `EXP-003`'s search for a crossover
`k*` rather than a single depth.

---

## A — What was claimed, and how strong is it

*Sections `01-abstract.md`, `02-1-introduction.md`, `03-2-1-solved-games.md`.*

### A1 — Which solution strength?

**Prompt.** Allis distinguishes ultra-weak, weak and strong solutions. Which one
does this paper claim, in its own words? Predict before checking: given the title
"Othello is Solved", which would a casual reader assume, and does the paper's
abstract invite that reading or guard against it? Write down what the claim does
**not** cover.

**My take.**

I started this paper already expecting a **weak solution** under Allis' terminology, so the title itself did not change my expectations. For a reader unfamiliar with the game-solving literature, however, *Othello is Solved* could easily be interpreted as a strong solution, making the distinction worth stating explicitly.

The main insight for me was not *what* was solved, but *how*. Before reading this paper, I still associated large solved games with the checkers route: constructing extensive retrograde endgame databases. Takizawa provides the strongest counterexample I have encountered so far. Othello shares several structural properties with FLIPHEX—irreversible piece placement, fixed game length and a hump-shaped state-space profile—yet its weak solution was obtained through a highly optimized forward alpha-beta search with transposition tables rather than by materialising a complete endgame database.

This does **not** imply that FLIPHEX should avoid endgame databases. Instead, it changes the default assumption. Building one is no longer the obvious architectural choice simply because the objective is to solve the game. The precedent established here supports ADR-012's decision to postpone that choice until EXP-003 can determine whether a crossover point (`k*`) exists where retrograde storage becomes worthwhile.

Finally, I found the presentation itself surprisingly instructive. The opening visualisation of the optimal line turns the weak solution into something concrete and inspectable instead of leaving it as an abstract claim. If FLIPHEX eventually reaches a comparable result, I would like its proof to include an equally clear visual certificate—whether as a principal variation, a reduced proof tree, or another reproducible witness—so that the solution is not only correct, but also understandable.

**Refined write-up.**

The reading is right and the paper is explicit, in Allis' vocabulary, twice.
§2.2: *"we utilized alpha-beta search because our goal was to obtain a weak
solution."* §5: *"We considered strongly solving Othello is intractable and
aimed for a weak solution."*

The abstract does **guard** against the casual reading, in its first paragraph
and easy to miss: *"The challenge of solving Othello, determining the outcome of
a game with no mistake made by either player."* The clause "with no mistake made
by either player" is the weak-solution qualifier, doing quiet work under a bold
title.

What the claim does not cover, in the authors' own words (§5):

> "We have created software that will always achieve a draw or win to achieve the
> criteria for weakly solving. **If the opponent makes a blunder, however, we do
> not guarantee that the software capitalizes on it.**"

> "we recognize that our achievement is **just above the criteria for weakly
> solving**."

That second sentence is unusually candid and is the honest summary of the whole
paper: the result clears the bar and does not clear it by much.

The instinct about the visual certificate is right, and it has a concrete form
worth naming, because FLIPHEX will need the same object. The paper publishes
**two** artefacts beyond the value: Figure 1 gives the full 60-move optimal
record as a move string (`F5D6C3D3 C4F4F6F3 …`), and Figure 4 gives the opening
as a tree where bold black is the optimal line and bold gray is every proved
response to a deviation. That is the *proof object*, not an illustration —
someone can re-verify any branch of it independently.

For this project the gap is real: [adr-010](../docs/adr/adr-010-solver-correctness.md)'s
V0–V6 ladder establishes that the computed value is trustworthy, but nothing in
it currently emits a publishable proof object. The 5×3 sweep will produce a
value and a checksum, not a certificate a reader can walk. Worth an open-ideas
entry before Phase 5.

### A2 — What is the game value, and from which position?

**Prompt.** What value does the paper report for Othello 8×8, and is it the value
from the initial position or from some set of positions? Compare with FLIPHEX,
where draws are impossible by parity: what does Othello's answer being what it is
tell you about how informative "who wins" is as a headline?

**My take.**

The reported game-theoretic value is a **draw**, and importantly it is the value of the **initial position**, not of every reachable position. That distinction reinforces Allis' definition of a weak solution: the result characterises optimal play from the standard starting board rather than solving the entire state space.

I found it interesting that the headline result itself is almost the least informative part of the paper. "Othello is a draw" tells us very little about the scientific contribution. The real contribution lies in demonstrating that this value can be established for such a large game through a feasible computational strategy.

Comparing this with FLIPHEX also changes the perspective. Since draws are impossible by parity, the final headline will necessarily be "first player wins" or "second player wins". That outcome alone will not be particularly informative. Just as in Othello, the interesting question is not the game-theoretic value itself, but the computational argument required to establish it. The methodology is likely to outlive the specific result.

**Refined write-up.**

Correct on both counts — draw, and from the initial position. One sharpening:
the claim is **asymmetric**, and the asymmetry is what makes it a weak *solution*
rather than merely a known value. Figure 1's caption:

> "Our study confirms that if a deviation from this record occurs at any point,
> our software, playing as the opponent, is guaranteed a draw or win."

So the proved statement is two-part: the value is exactly 0 under mutual optimal
play, **and** the published strategy achieves ≥ 0 against every deviation. §3.6
is the constructive half — a Python script that reads a result table while more
than 36 squares are empty and delegates to Edax below that. The strategy is a
deliverable, not a corollary.

On "who wins" being the least informative part: the paper agrees by its own
allocation of space — §5 spends its length on method, on the ECC/skepticism
question, and on proposing a new taxonomy category, and almost none on the draw
itself.

Worth adding a quantitative version of the point, because it cuts *harder* for
FLIPHEX than the note claims. Othello's value could have been any integer in
[−64, +64]; it landed exactly on 0, which is a genuinely surprising outcome
carrying real information about the game's balance. FLIPHEX 5×5 has **two**
possible values, so H1's headline carries at most one bit against a prior of
1/2. There is no FLIPHEX analogue of "and it came out exactly balanced" — parity
forbids it ([adr-011](../docs/adr/adr-011-reduced-variant-parity.md)). Under the
game-design thesis, the interesting balance evidence has to come from H5 and the
margin structure, not from H1's sign.

### A3 — 🔄 Place Othello in the Allis two-axis table

**Prompt.** Using [notes/allis-1994-searching-for-solutions.md](allis-1994-searching-for-solutions.md),
write down Othello's state-space and game-tree complexity and put them beside
checkers and FLIPHEX 5×5. Which of the two axes does this solve consume, and does
it support or complicate H4's claim that FLIPHEX 5×5 is out of reach on **both**?
Be specific: H4 rests on checkers being solvable at 5 × 10²⁰ states because it is
easy on the *tree* axis. Does Othello fit that story or is it a third pattern?

**My take.**

This comparison made H4 much more concrete. Before reading Takizawa, I mostly thought of solved games through the checkers example: an enormous state space made tractable because the game-tree complexity is relatively benign. Othello does not fit that pattern cleanly.

Othello has an even larger state space than checkers in practical terms, yet its game-tree complexity remains sufficiently manageable that an optimized forward search can still reach the initial position without relying on a complete retrograde database. It therefore occupies an intermediate point in Allis' two-axis view rather than simply reinforcing the checkers story.

This strengthens H4 rather than weakening it. FLIPHEX 5×5 is not merely "smaller than Othello", because the state-space axis is only one dimension of the problem. Its extraordinarily large branching factor pushes it much further along the game-tree axis, making direct comparisons based on state-space size alone misleading. The Othello result therefore reinforces the importance of analysing both axes independently before drawing conclusions about solvability.

At this stage of the paper, Othello appears to represent a third point in Allis' design space rather than a simple extension of the checkers case. Whether that interpretation holds depends on understanding why Takizawa's search remained feasible without a complete retrograde database, which is addressed in the methodological sections.

**Refined write-up.**

The conclusion — Othello is a third pattern — is right. The reason given for it
is not, and the correct reason is more useful to this project.

The numbers, from `notes/allis-1994-searching-for-solutions.md` §3.2 and
[research.md](../docs/research.md) H4 (Allis' figures are reference points, not
ours):

| Game | State-space | Game-tree |
|---|---:|---:|
| Connect-Four | 4.5 × 10¹² | 10²¹ |
| Checkers | 5 × 10²⁰ | 10³¹ |
| **Othello 8×8** | **10²⁸** | **10⁵⁸** |
| FLIPHEX 5×5 | 4.9 × 10¹⁷ | ~10⁶¹ (~10³⁰·⁵ Knuth–Moore) |

The paper's own abstract confirms the Othello row: *"roughly ten octodecillion
(10 to the 58th power) possible game records and ten octillion (10 to the 28th
power) possible game positions."*

So the claim that Othello's *"game-tree complexity remains sufficiently
manageable"* is **wrong**. Othello is worse than checkers on **both** axes — 8
orders on state space and **27 orders** on the tree. Nothing about Othello is
manageable by the Allis measures; it is the hardest game in the table on both.

Why it was solved anyway: **game-tree complexity is a ceiling, not a cost.** The
gap between 10⁵⁸ and the 1.5 × 10¹⁸ positions the proof actually searched is a
factor of 10⁴⁰, closed by three independent mechanisms:

1. **Knuth–Moore.** Perfect ordering takes `b^d` to roughly `b^(d/2)`: 10⁵⁸ →
   ~10²⁹. This alone is 29 orders.
2. **Transposition and symmetry.** With memoization the tree collapses onto the
   state space, so distinct nodes are bounded by 10²⁸, and Othello's 8-fold
   board symmetry cuts that again — §4 says symmetric positions were treated as
   identical.
3. **The decomposition.** A weak solution proves only *one* move at each of the
   prover's own nodes. Algorithm 1 turned the 2,958,551 enumerated 50-empty
   positions into an obligation set of **2,587** — a 1,143× reduction at that
   single layer (see B2).

And here is the sentence this reading exists to produce, which changes how H4
has to be argued:

> **Takizawa's proof searched 1.5 × 10¹⁸ positions. FLIPHEX 5×5's entire state
> space is 4.9 × 10¹⁷.** The Othello solve visited about three times more nodes
> than FLIPHEX 5×5 has positions.

This does **not** make FLIPHEX solvable, and it does not falsify H4's
conclusion. What it refutes is H4's *form*. H4 currently argues that 5×5 is out
of reach because it is large on both axes, resting on checkers being solvable
only because checkers is easy on the tree. Othello is harder than checkers on
both axes and was solved regardless — so "large on both axes" is not by itself
a reason. The defensible version of H4 has to name what FLIPHEX **lacks**
rather than what it has: no strong evaluation function (so no hypothesis set and
no Algorithm 1), only a partial Z/2 symmetry broken by the chiral `P3-y`
([adr-008](../docs/adr/adr-008-board-mirror-symmetry.md)) against Othello's 8-fold, 1450-wide
branching at the root, and a laptop instead of 1,600 core-years (C3).

Per the working agreement, H4 is a Phase 5 verdict and `research.md` is not
edited here. This paragraph is the material that verdict will have to confront.

---

## B — The method

*Sections `04-2-2-solving-technique.md`, `08-3-3-modification-to-edax.md`,
`09-3-4-obtaining-a-set-of-target-positions-with-50-.md`,
`10-3-5-obtaining-a-set-of-target-positions-with-36-.md`,
`11-3-6-constructing-a-program-that-never-loses.md`.*

### B1 — The core algorithm, stated precisely

**Prompt.** What is the search algorithm, in one sentence? Identify: the search
framework, the pruning, the role of the transposition table, and whether any
learned or heuristic component enters the *proof* (as opposed to the move
ordering). Then answer the question that matters for adr-004: **is anything in
the proof path allowed to be approximate?**

**My take.**

The most important distinction in this section is between *guiding the search* and *establishing the proof*. Takizawa's solver combines alpha-beta search, pruning and transposition tables with several practical optimizations, but none of these change the game-theoretic result. Their role is purely computational: reducing the amount of work required to reach the exact minimax value.

This clarified an architectural principle that is directly relevant to ADR-004. Every heuristic component belongs outside the proof path. Move ordering, search scheduling and other engineering techniques may dramatically improve performance, but they must never influence the computed value itself. If removed entirely, the solver should remain correct—only slower.

That observation also sharpened my understanding of what "exact" means in a game-solving context. Approximation is acceptable only when it affects efficiency, never correctness. The proof path itself admits no approximation: every propagated value must remain mathematically exact. This separation between optimisation and proof is, in my view, one of the paper's strongest design lessons.

**Refined write-up.**

In one sentence: **alpha-beta / NegaScout over Edax, with the endgame reached
through a two-stage decomposition whose intermediate results are memoized in
dictionaries, and whose proof obligations are proposed heuristically and
discharged exactly.**

§2.2 states the framework choice and its reason explicitly, and the sentence is
worth keeping because it is the cleanest statement of the adr-004 fork this
project already took:

> "For weak solutions, alpha-beta search is often used, while **retrograde
> analysis is frequently used for strong solutions**. […] In our study, we
> utilized alpha-beta search because our goal was to obtain a weak solution."

Note it also names a third option this project has not considered: **df-pn**
(depth-first proof-number search), which §2.2 credits for "puzzles with very long
solution sequences". FLIPHEX has a *fixed* solution length of 25, so df-pn's
advantage does not apply — but that is an argument adr-004 does not currently
make, and it is worth one line there.

The answer to the question that matters — **is anything in the proof path
allowed to be approximate?** — is *no*, and the paper enforces it with a
mechanism sharper than "heuristics only order moves". The architecture carries
**two dictionaries with different types**:

| | contents | read by | role |
|---|---|---|---|
| `D` | exact **upper and lower bounds** per position | Algorithm 3 (`G³⁶_third`) | proof |
| `D′` | an **estimate** of the game-theoretic value | Algorithms 2, 4 | conjecture |

Algorithm 3, the routine that returns a genuine bound, reads **only** `D`.
Algorithm 4, which returns an estimate, may read both. Exactness is therefore not
a convention about what the evaluation function is "used for" — it is a property
of *which dictionary a routine is permitted to open*, and it is visible in the
pseudocode's type signature.

That is the portable lesson for [adr-010](../docs/adr/adr-010-solver-correctness.md),
and it is stronger than what the ladder currently states. V0–V6 verify the
*output*; Takizawa's discipline constrains the *inputs a proof routine may
touch*. FLIPHEX's `solver/` has no equivalent separation today: the
transposition table stores `Flag.UPPER` / `Flag.LOWER` bounds and there is no
second store, because nothing in Axis 1 is allowed to estimate. That is fine
while adr-004 R1 holds — but the moment EXP-006 lets an Axis-2 policy propose
endgame positions to solve, this two-dictionary shape is the design to copy.

### B2 — The endgame threshold — the central question for adr-012

**Prompt.** There are **two** thresholds, in `§09` (50 empty squares) and
`§10` (36 empty squares). For each, find: (a) how the target set was obtained,
(b) how many positions it contains, (c) whether the results were **stored** and
reused across queries or recomputed per query, and (d) the storage footprint, if
any. Then answer the question the two-stage structure raises: **why two, and what
decided where each cut fell?** That is the shape `EXP-003` is looking for — a
crossover, not a single magic depth. This is the most important passage in the
paper for this project, since adr-012 Option B rests on it. Quote it exactly.

**My take.**

This section changed my understanding of what "avoiding an endgame database" actually means. I initially interpreted Takizawa's approach as performing the entire proof through forward search alone. After reading the methodology more carefully, that interpretation proved too simplistic.

The solver does materialise intermediate target layers and reuses them throughout the proof. What it avoids is not storage itself, but the construction of a complete retrograde endgame database covering every late-game position. The distinction is subtle but important: storage is used selectively as an engineering device rather than as the primary solving paradigm.

This substantially refines my interpretation of ADR-012. The architectural question is therefore not "database or no database", but rather "what information is worth materialising, and at which point does materialisation become more efficient than continued forward search?" Takizawa provides evidence that intermediate layers can occupy this crossover region, suggesting that EXP-003 should search for an empirical transition between pure search and progressively materialised subproblems rather than treating the choice as binary.

**Refined write-up.**

The revised reading is right, and the numbers make it concrete. The four
extractions the prompt asked for:

**§3.4 — the 50-empty cut.**

- **(a) How obtained.** Algorithm 1, `G₅₀(p, D₅₀)`, recursing from the initial
  position. It requires `D₅₀`, *"a dictionary where the keys are all positions
  with 50 empty squares, and the values are their respective **predictive
  scores**"*, and its contract is the quotable passage of the paper:

  > "**Ensure:** set of positions such that if all positions in it are solved and
  > all solutions match the predictions, the initial position is consequently
  > solved."

  The paper adds that it is *"similar to the alpha-beta search with (α, β) =
  (−1, 1) fixed"* and that it runs an **inner** alpha-beta first to find the best
  move, precisely to keep the returned set small.
- **(b) How many.** **2,958,551** positions with 50 empty squares were
  enumerated — only those with at least one legal move, with symmetric positions
  treated as identical. All were evaluated by Edax for 10 s on one core, with
  longer evaluations for near-draw cases. From those, **2,587** were selected as
  the hypothesis set, ties broken by frequency in the WTHOR database (61,549
  games, 2001–2020). §4: *"it was proven that all these 2,587 hypotheses were
  correct."*
- **(c) Stored, and reused.** `D₅₀` is a dictionary over the whole layer, and
  §3.6 confirms the store survives into the shipped artefact: the never-loses
  script *"refers to the result table while there are more than 36 empty squares,
  and after that, it delegates to Edax."*
- **(d) Footprint.** Not reported. Order of magnitude, reconstructed: 2.96 M
  positions × (a 16-byte board + a score) is tens of megabytes. Trivial.

**§3.5 — the 36-empty cut.**

- **(a)** Algorithm 5 takes a 50-empty position plus known data about 36-empty
  positions and emits 36-empty positions each with a **result hypothesis**.
  Crucially — and this is the sentence that makes the whole scheme sound — *"it
  can differentiate between positions that we have obtained game-theoretic value
  for and those that we have only estimated the value of."*
- **(b)** **1,505,367,525** positions with 36 empty squares were solved. Total
  positions searched, as reported by Edax:
  **1,526,001,455,595,489,506** ≈ 1.5 × 10¹⁸.
- **(c)** Stored and grown. `D` maps position → exact upper and lower bounds and
  persists across queries. Algorithm 6 is the fixed point: *"by adding the
  results to D and rerunning the Algorithm 5, more positions to be solved can be
  identified. Once Algorithm 5 no longer outputs any position, it can be said
  that the proof of the input position with 50 empty squares has been
  established."*
- **(d)** Not reported, and the layer was **never enumerated** — 1.5 × 10⁹
  positions were reached on demand, out of a 36-empty layer vastly larger.

**Why two, and what decided each cut.** The paper never says, which is itself the
finding. The inference that fits the data: the **upper** cut is set by
*enumerability* — 50 empties is the last layer you can still write down whole
(2.96 M after symmetry) — and the **lower** cut by *solvability*, the depth at
which Edax settles a position outright under a narrow window. Between them
nothing is enumerated; the gap is bridged by conjecture-and-verify.

**This is an amendment-worthy observation for EXP-003.** The prompt calls the
target "a crossover, not a single magic depth", and the paper shows it is not
even a single crossover: it is a **pair of cuts with different justifications**,
one bounded by memory and one bounded by search time. EXP-003 was designed to
locate one `k*`. The honest reporting shape is two numbers — the largest `k`
whose layer is enumerable, and the largest `k` solvable on demand — with the
strategy living in between. Worth a dated amendment in `experiments/registry.md`
before the 5×5 work starts.

One correction of vocabulary that propagates to adr-012: Takizawa **did**
materialise storage — a fully enumerated and evaluated 50-empty layer, plus a
growing exact-bounds dictionary at 36, plus a result table shipped with the
player. Option B should therefore be read as *"no complete retrograde layer of
exact values"*, never as *"no stored positions"*. Under that reading, FLIPHEX's
`EXP-006` (5×5 endgame positions at `k ≤ 8`, solved exactly on demand) is not an
alternative to Takizawa's architecture — it **is** Takizawa's architecture,
minus the evaluator that would let us choose the positions well.

### B3 — Why no retrograde database?

**Prompt.** The paper says the authors considered a *strong* solution intractable
and did not attempt one. Reconstruct the reasoning: what specifically makes a
strong solution of Othello harder than the weak solution they achieved, given
that both range over the same game? Then apply the same reasoning to FLIPHEX
5×5 and write down whether it lands the same way. 🔄 Contrast with
[schaeffer-2007](schaeffer-2007-checkers-is-solved.md) §2.1, where the endgame
databases were the *enabling* device rather than an omitted luxury — what is
different about checkers that makes them pay there?

**My take.**

This section clarified that the difference between a weak and a strong solution is not merely one of computational scale, but of objective. A weak solution only needs to establish the game-theoretic value of the initial position and provide a strategy that guarantees that value from the start of the game. A strong solution, by contrast, requires assigning an exact value to every legal position, including positions that arise only after suboptimal play. The latter therefore demands certification of the entire reachable state space rather than a single proof rooted at the initial board.

This distinction also explains why Takizawa could avoid constructing a complete endgame database. Since the goal was only to solve the initial position, a forward proof was sufficient. In contrast, Schaeffer's checkers project relied on endgame databases because they formed part of the mechanism required to value arbitrary late-game positions, making them an enabling component of the strong solution rather than a mere optimisation.

The same reasoning appears to apply to FLIPHEX 5×5. If the objective is a weak solution, there is no a priori reason to assume that a complete retrograde database is necessary. If, however, the objective shifts towards a strong solution or solving arbitrary positions, the balance changes substantially, and retrograde storage becomes much more compelling. This reinforces ADR-012's decision to treat endgame databases as a design trade-off driven by the target solution class rather than as a mandatory component of every solver.

**Refined write-up.**

Correct throughout. Three things to add, one of which is a mechanism the answer
gestures at without naming.

**The paper does not argue intractability — it asserts it.** §5, in full: *"To
the best of our knowledge, no category in between weakly and strongly solving has
been proposed. We considered strongly solving Othello is intractable and aimed
for a weak solution."* No estimate is given. The mechanical reason is visible in
B2's numbers: the weak solution's obligation set was 2,587 positions out of
2,958,551 enumerated at one layer. A strong solution has **no such filter** —
every one of the 2.96 M needs a value, and so does every other layer. The
2,587/2,958,551 ratio *is* the distance between weak and strong, measured at the
only layer where both quantities are known.

**The diverging/converging split is the real answer to the checkers contrast,**
and it is already in `notes/phase2-synthesis.md` S3. Checkers **converges**:
pieces are removed, so the endgame space *shrinks* to 3.9 × 10¹³ positions at
≤ 10 pieces, and that one table is consulted by an enormous number of distinct
middlegame lines. The database pays because it is small *and* densely reused.
Othello and FLIPHEX **diverge**: the layer at `k` empty cells is the largest
object you will ever store, and it serves only positions at exactly that depth.
A diverging game gets no compounding return on a materialised layer — which is
why the same technique that carried checkers is an omitted luxury here.

**Where FLIPHEX lands.** The same way, and EXP-003 already measured it: the
median subtree below a 5×5 position with `k = 8` empty cells is **806,474**
nodes, and **480** at `k = 5`. Solving on demand at `k ≤ 8` costs under a second;
materialising the `k = 8` layer costs the whole layer. That is the arithmetic
behind adr-012 Option B, and it is the same shape as Takizawa's 36-empty cut.

The conditional in the last paragraph is the right one to have flagged, and the
paper gives it a name that the note should adopt — see D1 on **semi-strong
solving**. FLIPHEX's H3 needs the solver to value *arbitrary* 5×5 endgame
positions, not just the opening. That obligation is strictly stronger than weak
solving, and it is exactly the category Takizawa proposes and does not achieve.

### B4 — Move ordering and where the engineering actually went

**Prompt.** How much of the feasibility comes from the algorithm and how much
from move ordering, the evaluation function used for ordering, and engineering?
Identify the single largest contributor the paper credits. Then answer for
FLIPHEX: adr-004's Phase 2 amendment split move ordering into an *agent* concern
and a *proof* concern (rules R1–R3). Does this paper respect that separation, and
if it does not, does its proof survive the objection?

**My take.**

This section made me distinguish two different notions of correctness: **mathematical correctness** and **computational reproducibility**. Takizawa's solver relies heavily on engineering—particularly high-quality move ordering driven by Edax's evaluation function—to make the search computationally feasible. However, these components influence only *which branches are explored first*, never the minimax value ultimately propagated by the proof. In that sense, the exact result remains independent of the heuristic.

At first sight, this appears to match the separation adopted by ADR-004, where heuristics accelerate the search without becoming part of the proof. On closer inspection, however, the correspondence is not perfect. Edax's move ordering depends on a learned evaluation function. While this does not affect the correctness of the computed game-theoretic value, it does affect the auditability and reproducibility of the computation. Reproducing the same proof efficiently requires access to the learned evaluator—or an alternative ordering strategy with comparable effectiveness.

This distinction refined my interpretation of ADR-004. The important architectural boundary is not simply "heuristics versus proof", but "heuristics that influence performance versus mechanisms that determine correctness". Learned move ordering belongs to the former category: it preserves the mathematical validity of the proof while raising the practical cost of independently reproducing it. For FLIPHEX, separating the proof engine from the ordering policy therefore remains desirable, not only for correctness but also for long-term verifiability.

**Refined write-up.**

The auditability-versus-correctness distinction is the right one and it is the
most valuable thing in this note — it is a sharper reading of adr-004 R1–R3 than
the ADR itself currently has. But it rests on a factual premise that this paper
does not satisfy, and the corrected version is a stronger argument for the same
conclusion.

**The claim to revise:** *"these components influence only which branches are
explored first, never the minimax value ultimately propagated by the proof."*
For move ordering proper, true. For Edax's evaluation function in this
architecture, **not** what happens. Algorithm 2, `E(p, D′)`, calls *"Edax's
static evaluation function"* and returns *"an integer that is an estimation of
game-theoretic value of p"*. Those estimates populate `D′`; `D′` is what
Algorithm 4 consults to attach a **result hypothesis** to each 36-empty
position; and Algorithm 1's entire contract is conditional on those predictions
— *"if all positions in it are solved and **all solutions match the
predictions**"*. The evaluation function therefore selects **which theorem gets
proved**, not merely the order in which nodes are visited. It sits upstream of
the proof obligation, which is a more intimate position than move ordering, not
a less intimate one.

**Why the conclusion survives anyway,** and this is the mechanism worth naming:
a wrong estimate cannot produce a wrong value, because it is never *believed* —
it is *checked*. §3.5: *"The game-theoretic values of the output positions can
sometimes deviate from the estimations… In such cases, by adding the results to
D and rerunning the Algorithm 5, more positions to be solved can be identified.
Once Algorithm 5 no longer outputs any position, it can be said that the proof
… has been established."* That is Algorithm 6, a **fixed-point loop**. A bad
evaluator costs *iterations*; it cannot cost *soundness*. The pattern is
**conjecture-and-verify**: a heuristic proposes the decomposition, exact search
discharges it, and termination is defined as "nothing left unproven".

This is a genuinely different licence from the one adr-004 grants. R1–R3 permit
heuristics in *ordering*. Takizawa permits them in *problem selection*, and buys
back the guarantee with a termination condition rather than with a restriction.
The rule that covers both, and which I would propose as an adr-004 amendment:

> A learned or heuristic component may enter an Axis-1 proof at any point
> **provided the resulting proof object is independently checkable without it.**

Takizawa satisfies this: any of the 2,587 hypotheses can be re-verified by an
exact search that never opens Edax's evaluation function. Ordering is the
special case where the artefact is checkable because the value does not depend
on it at all. This is also the resolution of `exercises/ex03_alpha_beta.md`
Q3(c), which currently asks the question as if the answer were "learner-seeded
ordering is inadmissible" — it is admissible, under that proviso.

**On the "single largest contributor" the prompt asked for:** the paper never
credits one, and the reason is §5's most counter-intuitive finding, which
belongs in C1 as well —

> "As Figure 3 indicates, many of our calculations to weakly solve Othello were
> devoted to positions where, according to the estimation, there is a clear
> advantage in terms of winning or losing. This indicates that **one cannot claim
> a pseudo-solution by not proving positions whose estimated game-theoretic value
> exceeds any threshold.**"

The positions that *looked* easy consumed the compute. So the honest answer to
"how much came from move ordering" is that the evaluation function's quality
determined how much work there was, and where it was *systematically wrong* —
§5 blames *"systematic and significant errors in Edax's … static evaluation
function, especially for positions unlikely to appear in actual games"* — is
exactly where the cost landed. For FLIPHEX that is a warning about EXP-006:
positions sampled from self-play are the ones a learner evaluates well, and they
are therefore *not* the expensive ones. A pre-declared sample drawn only from
plausible play would understate the cost of the thing it is meant to measure.

---

## C — Validation, and what "solved" obliged them to prove

*Sections `12-3-7-materials.md`, `13-4-results.md`.*

### C1 — How was the result verified?

**Prompt.** A solve produces one answer out of an astronomical space, and the
failure mode is a plausible wrong answer rather than a crash. What verification
did the authors perform, and how does it compare to
[adr-010](../docs/adr/adr-010-solver-correctness.md)'s V0–V6? Specifically: was
there an independent reimplementation, a second method, a sampled re-derivation,
or a checksum discipline? Was the result independently reproduced by anyone else
at the time of writing?

**My take.**

This section shifted my attention from solving the game to convincing others that the reported solution is correct. In a game-solving project, the most dangerous failure mode is not a crash but a plausible yet incorrect answer. That makes verification a first-class research problem rather than an implementation detail.

Compared with Schaeffer's checkers project, Takizawa relies primarily on the correctness of an exact deterministic search together with internal consistency checks and reproducibility of the computed solution. I did not find evidence of an independent implementation, an alternative proof method, or an external reproduction of the complete result at the time of publication. The paper therefore demonstrates that exact computation alone is not the same as independent verification.

This comparison strengthened my appreciation for ADR-010. Its validation ladder (V0–V6) goes beyond what is strictly necessary to obtain a game-theoretic value and instead focuses on building confidence that the reported value is genuinely correct. If FLIPHEX is ever claimed to be solved, I would want the validation strategy to be at least as convincing as the search algorithm itself.

**Refined write-up.**

The headline finding is correct and correctly hedged — *"I did not find evidence
of"* is the right register for a negative claim about a literature. There was no
independent reimplementation, no second proof method, and no external
reproduction at publication. That stands.

But the paper has more verification discipline than "internal consistency
checks", and enumerating it is what makes the comparison with adr-010 sharp:

1. **Determinism as a design goal.** §3.5 chose 1-core runs over 4-core ones
   partly because *"the number of search positions becomes deterministic, it
   ensures reproducibility"* — accepting slower wall-clock to make the
   computation replayable. Reproducibility bought with performance, deliberately.
2. **A fixed-point termination condition.** Algorithm 6 cannot halt while any
   hypothesis is unproven (B4). The stopping rule *is* the verification.
3. **A falsifiable obligation set.** The 2,587 hypotheses at 50 empties are
   independently checkable statements, and §4 reports all 2,587 confirmed. This
   is the closest thing in the paper to adr-010's V4.
4. **Hardware integrity, claimed explicitly.** §3.7 notes all CPUs *"feature main
   memory with Error Checking and Correction (ECC)"*, and §5 defends it:

   > "we recognize that some readers may be skeptical about the validity of
   > computational proofs. Naturally, **computational errors due to CPU or memory
   > faults cannot be entirely ruled out**. However, as the vast majority of
   > calculations were executed on a computer cluster with ECC memory, we believe
   > the results to be nearly indisputable."

5. **Published source**, so any detected error *"can be easily recalculated"*.

Against adr-010's ladder: he has something like **V5** (determinism /
replayability) and a **hardware-integrity claim adr-010 does not have at all**.
He lacks **V4** as adr-010 defines it — sampled re-derivation by an *independent
method* — and lacks V6 and a second implementation. So the two disciplines are
not ranked; they are **differently shaped**. adr-010 is stricter on cross-method
agreement; Takizawa is stricter on the physical substrate.

That asymmetry is worth acting on. adr-010 has no clause about memory integrity,
and EXP-002 is a single PyPy process running 32.4 h of sweep (~52 h
wall-clock, measured after the fact — this note first said ~13 h, from a
projection) over 17.5 × 10⁹ packed
entries on consumer WSL hardware with no ECC. A single bit flip in the 2-bit
value array is a silent wrong answer of exactly the kind adr-010 exists to
prevent, and none of V0–V6 would catch it — V1 counts entries, not their values.
This is a **Threats to Validity** item for the Phase 3 note, not an ADR change.

One further finding belongs here rather than in B4, because it is about what
verification *cannot* be cheapened into (quoted in full in B4): §5 reports that
the compute went disproportionately into positions the evaluator thought were
one-sided, and concludes that *"one cannot claim a pseudo-solution by not proving
positions whose estimated game-theoretic value exceeds any threshold."* That
closes off the most tempting shortcut a FLIPHEX solve would reach for — skipping
subtrees a policy is confident about — and it is closed off empirically, not by
principle.

### C2 — Is anything here statistical?

**Prompt.** Identify every number in the paper that is an estimate rather than an
exact count, and how its uncertainty is reported. Predict first: in a paper about
an *exact* result, where would statistics have to creep in? Then check whether
your prediction was right.

**My take.**

Before reading this section, I expected that any statistical reasoning would appear only in the computational aspects of the project rather than in the proof itself. That prediction turned out to be correct.

The game-theoretic result is exact and therefore carries no uncertainty: the initial position is either a draw or it is not. Statistics only enter where exact measurement is either unnecessary or impractical, such as performance measurements, computational effort, or estimated characteristics of the search. They describe the process of obtaining the proof, never the proof itself.

This distinction reinforced another useful design principle for FLIPHEX. Approximation belongs in engineering, not in correctness. Runtime, resource usage and scalability may legitimately be reported through estimates or empirical measurements, but the computed game-theoretic value and every step of the proof path must remain exact. In that sense, the paper draws a remarkably clean boundary between empirical computer science and mathematical verification.

**Refined write-up.**

The prediction was right. Completing it with the actual list, since the prompt
asked for *every* such number:

**Exact counts** (reported to the unit, and the precision is a provenance claim
rather than a precision claim — they are what the enumerator and Edax reported):

- 2,958,551 positions with 50 empty squares enumerated
- 2,587 hypotheses selected
- 61,549 WTHOR game records, 2001–2020
- 1,505,367,525 positions with 36 empty squares solved
- 1,526,001,455,595,489,506 total positions searched — nineteen significant
  figures, and quoted in full precisely because it is a sum of Edax's own reports

**Estimates:**

- **~1.2 × 10⁷ positions/GHz/core/sec** (Table 1, "Searching capability"). This
  is the only number in the paper that is a *measurement* rather than a count,
  and it is averaged across four different microarchitectures — Xeon 6254, EPYC
  7713, Xeon 8380, Xeon 8260M. **No dispersion is reported**: no range, no
  variance, no per-CPU breakdown.
- Table 1's other two rows, ~1.5 × 10⁹ and ~1.5 × 10¹⁸, are the exact counts
  above rounded to one significant figure.
- Edax's static evaluation values (Algorithm 2) are estimates by construction,
  and the 10-second-per-position budget in §4 makes them *truncated* estimates
  — but they are never reported as results, only consumed.

**How uncertainty is reported: it is not.** Not one interval, not one variance,
anywhere in the paper.

So the clean boundary the note observes is real, with one crack worth naming.
The single averaged number, Table 1's throughput, is the one every "how much did
this cost" and "could I do this" claim depends on — including the derivation in
C3. It carries no error bar while being averaged over hardware that plausibly
varies by 2× end to end. That is not a flaw in the proof; it is a flaw in the
*only* part of the paper anyone would want to reuse quantitatively, and it means
C3's core-year figure should be read as an order of magnitude, not a
measurement.

The transferable rule for this project: **the numbers that describe a proof
deserve the statistical hygiene the proof itself does not need.** `docs/`
reports FLIPHEX's exact results without intervals, correctly — but EXP-003's
806,474-node median, EXP-002's cfg/s, and every runtime in the phase note are
measurements, and per the `exp-analysis` discipline they get intervals and
dispersion or they get labelled as single observations.

### C3 — Compute budget

**Prompt.** How much compute did the solve take, and on what hardware? Divide by
the state-space ratio to FLIPHEX 5×5 (~10²⁸ vs 4.9 × 10¹⁷) and by the branching
ratio (~10 vs 1450), and write down what those two adjustments do in *opposite*
directions. This is the honest version of "could I do this on a laptop?".

**My take.**

Before reading this paper, I tended to treat computational budget as something that scaled primarily with the size of the state space. This comparison showed why that intuition is incomplete.

Othello requires dramatically more storage in principle because its state space is roughly ten orders of magnitude larger than FLIPHEX 5×5. If state-space complexity were the dominant factor, FLIPHEX would appear vastly easier to solve. The branching factor comparison points in the opposite direction. FLIPHEX begins with roughly 1450 legal moves, compared with about 10 in Othello, suggesting that forward search may become dramatically more expensive even though the underlying state space is much smaller.

The important lesson is therefore not whether FLIPHEX can be solved on commodity hardware, but that different complexity measures predict different bottlenecks. Othello demonstrates that an enormous state space does not necessarily prevent an exact solve, while FLIPHEX reminds us that search complexity cannot be inferred from state-space size alone. Whether a laptop is sufficient ultimately depends on the structure of the proof tree rather than on either complexity measure in isolation.

**Refined write-up.**

The conclusion is right — the bottleneck is the proof tree, not either axis. Here
is the arithmetic that backs it, which is what makes this the honest version of
"could I do this on a laptop".

**Hardware** (§3.7). MN-J, a supercomputer owned by Preferred Networks Inc. —
MN-2A, MN-2B and MN-3 presented to users as one Kubernetes cluster. Intel Xeon
6254, AMD EPYC 7713, Intel Xeon 8380, Intel Xeon 8260M; all with ECC memory.
**Wall-clock duration is never reported.**

**Compute**, derived from Table 1:

- positions searched: 1.526 × 10¹⁸
- throughput: ~1.2 × 10⁷ positions/GHz/core/sec
- ⇒ 1.526 × 10¹⁸ / 1.2 × 10⁷ = **1.27 × 10¹¹ GHz·core·sec**
- at a nominal 2.5 GHz: 5.1 × 10¹⁰ core·sec = **1.4 × 10⁷ core-hours ≈ 1,600
  core-years**

On an 8-core laptop that is **~200 years**. So the answer to the prompt's
question is no, by roughly two orders of magnitude beyond a human career — and
that is before observing that the laptop lacks ECC (C1) and Edax.

**The two adjustments, and why they do not cancel.**

- **State-space ratio.** 10²⁸ / 4.9 × 10¹⁷ ≈ 2 × 10¹⁰. Dividing the budget by it
  gives 1.4 × 10⁷ / 2 × 10¹⁰ ≈ 0.0025 core-hours — about **nine seconds**. The
  absurdity is the point: forward-search cost is not proportional to state-space
  size, so this adjustment is not a cost adjustment at all. It measures a
  *ceiling*.
- **Branching ratio.** Othello `b ≈ 10` over `d ≈ 58`; FLIPHEX `b₀ = 1450` over
  `d = 25`, decaying on two factors at once. The Knuth–Moore minimal trees are
  ~10²⁹ for Othello against **~10³⁰·⁵** for FLIPHEX 5×5 (already computed in
  [research.md](../docs/research.md) H4). FLIPHEX's minimal tree is therefore
  about **32× larger** than Othello's — not smaller.

They point in opposite directions by wildly different magnitudes — 10¹⁰ one way,
10¹·⁵ the other — because only one of them is a cost. The state-space ratio says
FLIPHEX is 10 orders *cheaper to memoize*; the branching ratio says it is 1.5
orders *more expensive to search*. Both are true simultaneously, and the second
is the one that sets the bill.

**The single comparison worth remembering** (developed in A3): Takizawa searched
1.5 × 10¹⁸ positions; FLIPHEX 5×5 has 4.9 × 10¹⁷ states. **He visited three
times more nodes than FLIPHEX 5×5 has positions.** With a perfect transposition
table, no FLIPHEX forward search can ever visit more than 4.9 × 10¹⁷ distinct
nodes. Magnitude is therefore not what stands between this project and a 5×5
solve.

What does, concretely:

1. **No evaluator.** Algorithm 1 needs `D₅₀` — predictions accurate enough that
   almost all of them survive verification. FLIPHEX has nothing that plays well,
   and adr-004 R1–R3 restrict what an Axis-1 run may consume anyway (though see
   B4's proposed amendment).
2. **No symmetry to speak of.** Othello has 8-fold board symmetry and used it.
   FLIPHEX has Z/2, partial, and broken while the chiral `P3-y` is in hand
   (adr-008) — so it does not even apply at the opening, which is where the
   1450-wide branching is.
3. **Storage stays closed regardless.** 4.9 × 10¹⁷ states × 2 bits = **122 PB**.
   The memoization ceiling being 10 orders below Othello's does not make it
   reachable; it makes on-demand solving (EXP-006) the only door.
4. **1,600 core-years against one WSL laptop.** EXP-002's 5×3 sweep is 32.4 hours
   on one core. The 5×5 is not a bigger version of that run.

---

## D — Limitations, in the authors' own words

*Section `14-5-discussion-and-conclusions.md`.*

### D1 — What do they say they did not do?

**Prompt.** List the acknowledged limitations verbatim. Which of them would a
critical reader add that the authors do not? Pay attention to whether "solved"
in the title is defended or simply asserted.

**My take.**

I appreciated that the paper remains disciplined about the scope of its claims. Although the title is intentionally bold, the technical discussion consistently frames the result as a weak solution of the initial position and explicitly acknowledges that a strong solution remains out of reach. In that sense, the title is defended by a precise definition rather than by rhetorical overstatement.

The main limitation I would add concerns independent verification. The paper convincingly explains how the result was obtained, but it offers relatively little external evidence beyond the correctness of the implementation itself. Given the scale of the computation, an independently developed solver or an alternative proof route would have further strengthened confidence in the claim.

More broadly, I found it interesting that the paper focuses on demonstrating that the solve is possible rather than extracting general design principles about why this particular computational strategy succeeds. That is entirely appropriate for its objective, but it also explains why projects such as FLIPHEX still need architectural experiments like EXP-003 instead of directly inheriting the design decisions made here.

**Refined write-up.**

The judgement on the title is right: it is defended by definition, in §2.2 and
§5, not asserted. The verbatim limitations the prompt asked for, all from §5:

> "we recognize that our achievement is **just above the criteria for weakly
> solving**."

> "For certain borderline positions with 36 empty squares, Edax requires a large
> amount of computation to determine the game-theoretic value and corresponding
> move."

> "**If the opponent makes a blunder, however, we do not guarantee that the
> software capitalizes on it.**"

> "computational errors due to CPU or memory faults cannot be entirely ruled
> out."

> "To expedite our announcement, we opted against computing additional books in
> this study."

The last one is a candour worth noticing: the scope was cut for *publication
speed*, and he says so.

What a critical reader adds, beyond the independent-verification point — which
is the right one, and is C1's finding:

- **The throughput figure has no error bar** (C2), and it is the sole basis for
  any cost claim about the work.
- **"Reasonable computational resources" is doing heavy lifting.** §5 argues that
  *"given the continuing advances in personal computers, it is reasonable to
  conclude that our approach requires only reasonable computational resources."*
  The proof consumed ~1,600 core-years on a corporate supercomputer (C3). The
  claim is about *replaying* the shipped strategy, not about *producing* the
  proof, and the sentence does not distinguish them.
- **The evaluator's blind spot is acknowledged but not bounded.** §5 attributes
  the cost overruns to *"systematic and significant errors in Edax's … static
  evaluation function, especially for positions unlikely to appear in actual
  games"* — but never estimates how much work a better evaluator would have
  saved, which is precisely the number anyone reusing the method needs.

**The omission worth correcting in the note, though: the paper does extract a
general principle, and it is a new entry in Allis' taxonomy.** §5:

> "To the best of our knowledge, no category in between weakly and strongly
> solving has been proposed. […] developing software that consistently makes the
> best move represents a challenge that lies between weak and strong solving
> […] Therefore, we would propose to call this intermediate category
> **"semi-strong solving"**. This study does not achieve semi-strong solving of
> Othello; this remains as future work."

That is a contribution to vocabulary, not just to Othello, and it lands directly
on this project. FLIPHEX's H3 requires the solver to value *arbitrary* 5×5
endgame positions at `k ≤ 8` (EXP-006) — an obligation strictly stronger than
weak solving and strictly weaker than strong. **FLIPHEX's Axis-1 target is
semi-strong on the 5×5 and strong on the 5×3**, and the project has been calling
both "the exact solve". `notes/allis-1994-searching-for-solutions.md` should gain
the term, and the glossary with it.

He also names his own succession: *"we speculate that chess might be the next
weakly solved grand challenge. However, because the search space of chess is very
large, not only improvements in computational power but also **theoretical
breakthroughs** might be necessary."* Note the criterion he reaches for — not
size, but whether size alone is the obstacle. That is the same distinction A3
and C3 arrive at from the other direction.

### D2 — 🔄 What does this change in this project?

**Prompt.** Three concrete questions, each of which has a live decision behind it:

1. Does adr-012 adopt Option B (no materialised database)? What in this paper
   would have to be false for Option A to be right instead?
2. [docs/research.md](../docs/research.md)'s Phase 2 amendment gave H3 the "5×5
   retrograde endgame layers" as its comparison set member on the *shipped*
   game. If FLIPHEX follows Othello and ships no database, what replaces it —
   and is H3 still worth having?
3. EXP-003 pre-registers `k* ≥ 6` on the strength of this precedent. After
   reading, is that prediction still the one you would register? If not, amend
   it **before** the run, not after.

**My take.**

This paper did not settle ADR-012, but it substantially changed my prior. Option B (solving without a materialised endgame database) now has a compelling precedent in a game that is structurally much closer to FLIPHEX than checkers. At the same time, the paper never argues that retrograde databases are unnecessary in general. Their usefulness remains an empirical question whose answer depends on the interaction between state-space complexity, game-tree complexity and implementation cost. That is precisely why EXP-003 remains necessary.

Consequently, I would keep H3, but reinterpret its purpose. Rather than comparing specific implementation artefacts, it now compares alternative architectural strategies for obtaining an exact solution. Whether FLIPHEX ultimately ships with or without a retrograde database becomes less important than understanding *why* one strategy outperforms the other.

Finally, I would keep the pre-registered prediction that `k* ≥ 6`, although with more caution than before reading the paper. My confidence no longer comes from expecting FLIPHEX to behave exactly like Othello, but from adopting the broader hypothesis suggested by Takizawa: useful endgame thresholds appear to emerge from engineering trade-offs rather than theoretical constants. The experiment exists to locate that crossover, not to confirm a value inherited from another game.

**Refined write-up.**

Taking the three questions in order, since each has a decision behind it.

**1 — Does adr-012 adopt Option B?** Yes, and the precedent is stronger than the
note claims once B2's correction is applied: Takizawa is not an example of
*solving without storage*, he is an example of **storing selectively and never
retrogradely**. He enumerated and evaluated a full 50-empty layer (2,958,551
positions), grew an exact-bounds dictionary at 36 empties across the whole run,
and shipped a result table with the player. What he never built was a complete
retrograde layer of exact values.

What would have to be false for Option A to be right instead: the on-demand
subtrees would have to be too expensive to solve repeatedly. **EXP-003 already
falsified that** — median 806,474 nodes at `k = 8`, 480 at `k = 5`. Materialising
buys nothing when the query costs under a second and the layer costs the layer.
Option A would return only if FLIPHEX acquired an evaluator good enough to make
a *hypothesis set* worthwhile, which is a different argument from the one
adr-012 rejected.

**2 — What replaces the retrograde layers in H3's comparison set?**
Already resolved in the repo, and the note can simply record it:
[research.md](../docs/research.md) H3 now reads *"a pre-declared random sample of
shipped-5×5 endgame positions at `k ≤ 8` empty cells, solved exactly on demand
(EXP-006, registered 2026-08-05 — replaces the retrograde endgame layers, which
EXP-003 showed are not worth materialising)"*.

H3 is **more** worth having under this reading, not less, for a reason the
reinterpretation above gets close to: H3 is the only hypothesis that requires
Axis 1 to value positions it did not choose. That is the semi-strong obligation
(D1). Its scientific content is not "does the learner agree with the solver" but
"does exact agreement survive outside the distribution the learner trained on" —
and B4's finding sharpens the design: sampling `k ≤ 8` positions from self-play
would draw exactly the positions a learner evaluates well, which §5 shows are
*not* the expensive or the informative ones. **The pre-declared sample should be
drawn uniformly from the reachable `k ≤ 8` set, not from self-play games.** That
is a registry amendment worth making before EXP-006 runs.

**3 — Is `k* ≥ 6` still the prediction to register?** It stands, and it was not
falsified — EXP-003 measured `k* > 8`. But the note's own framing understates
what changed, because the *shape* of the prediction was wrong in a way the value
hides. EXP-003 looked for **one** crossover. Takizawa has **two cuts with
different justifications** (B2): an upper one bounded by *enumerability* and a
lower one bounded by *solvability*, with conjecture-and-verify spanning the gap.
A single `k*` cannot express that.

So the honest amendment is not to the predicted value but to the reported
quantity: EXP-003 should report a **pair** — the largest `k` whose layer is
enumerable within budget, and the largest `k` solvable on demand within budget —
and say what, if anything, lives between them. On the 5×5 those are plausibly far
apart, and the interval is where an architecture would go. Dated amendment in
`experiments/registry.md`, before any 5×5 work starts; the registered prediction
itself is untouched.

---

## Lessons Learned

* A weak solution and a strong solution differ in objective, not merely in computational scale.

* Solving a game does not prescribe a unique computational route.

* The paper reinforced an important architectural distinction between correctness and reproducibility. Learned evaluation functions and move ordering may dramatically reduce the amount of search required without changing the minimax value itself. They therefore belong outside the logical proof, although they directly affect how easily the computation can be independently reproduced and audited.

* The paper introduced semi-strong solving as a practically meaningful target between weak and strong solutions. Rather than assigning exact values to every legal position, it extends the guarantee beyond the initial board while avoiding the prohibitive cost of a complete strong solution.

* The choice of endgame thresholds is presented as an engineering trade-off rather than a mathematical constant.

* State-space complexity and game-tree complexity must always be analysed independently.

* I expected computational effort to correlate with positions that looked strategically difficult. The paper showed the opposite can happen: positions that appear easy may still dominate the computational cost. This makes heuristic pruning an unsafe basis for claiming even a pseudo-solution.

* Validation is a research problem in its own right.

* For FLIPHEX, the paper strengthens ADR-012 by motivating experimental evaluation of what should be materialised rather than assuming either pure forward search or a complete retrograde database.


## Failed Attempts

* I initially looked for a theoretical justification for the specific thresholds of 50 and 36 empty squares. The paper provides none. Instead, these values appear as successful engineering choices whose usefulness was validated empirically.

* I expected the main contribution to be a novel search algorithm. Instead, the breakthrough comes from combining well-established exact algorithms with decades of engineering improvements and highly effective move ordering.

* I implicitly treated the game-theoretic value ("draw") as the primary scientific result. After reading the paper, it became clear that the methodology used to establish that value is considerably more informative than the value itself.

* I initially viewed retrograde endgame databases as the natural consequence of attempting to solve a game. Othello showed that this assumption is too strong: whether a materialised database is worthwhile depends on the computational trade-off, not on the mere objective of obtaining a weak solution.

* I expected the paper to derive general principles for selecting endgame thresholds. Instead, it presents a successful design for Othello, leaving the identification of crossover points as an empirical question rather than a theoretical one.

* I expected "Othello is Solved" to be primarily a statement about the game. By the end of the paper, I found it more useful to interpret it as a statement about a proof strategy and the engineering decisions that made that proof computationally feasible.

