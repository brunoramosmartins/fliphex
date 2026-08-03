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

_(você escreve, em primeira pessoa)_

**Refined write-up.**

_(preencho depois que você compartilhar seu take)_

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

_(você escreve, em primeira pessoa)_

**Refined write-up.**

_(preencho depois que você compartilhar seu take)_

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

_(você escreve, em primeira pessoa)_

**Refined write-up.**

_(preencho depois que você compartilhar seu take)_

### 2.2 — Convergence: why this worked for checkers and may not for FLIPHEX
**Prompt.** *This is the load-bearing prompt of the whole note.* The paper notes
that "the checkers forced-capture rule quickly results in many pieces being
removed from the board, giving rise to a position with ≤10 pieces – and a known
value." Checkers is a **converging** game: the state gets *smaller* as play
proceeds, so the endgame is a narrow funnel every line must pass through.
FLIPHEX is **diverging** — a tile is added every ply, so the endgame is the
*widest* part of the state space, not the narrowest. Allis says endgame databases
are "generally unfeasible for diverging" games.

Answer three things. (a) Restate in your own words why convergence is what makes
a 10-piece database *cover* the game rather than just decorate it. (b) For
FLIPHEX, the last-`k`-empty slice grows explosively going backwards: k≤3 ≈
9 × 10¹², k≤4 ≈ 1.5 × 10¹⁴, k≤5 ≈ 1.2 × 10¹⁵ (upper bounds). Compare with
checkers' ≤10-piece database size, which the paper gives — is FLIPHEX's `k ≤ 5`
target above or below what an 18-year multi-machine project achieved? (c) Given
(a) and (b), is the answer to prompt 1.2 that FLIPHEX 5×5 *is* within reach, or
that raw state count was never the binding constraint? State which, and why.

**My take.**

_(você escreve, em primeira pessoa)_

**Refined write-up.**

_(preencho depois que você compartilhar seu take)_

### 2.3 — Storage, indexing and compression
**Prompt.** Retrograde analysis is an I/O problem before it is a search problem.
Find what the paper (and the supporting online material) says about how the
databases are **stored, indexed, and compressed**, and about the distinction
between what is kept on disk and what is recomputed. FLIPHEX's 4×4 solve is
~9.3 × 10¹⁰ states ≈ 23 GB at 2 bits each — squarely in the regime where these
choices decide feasibility. Which specific techniques would transfer, and which
depend on checkers-specific structure (piece counts, symmetry) FLIPHEX lacks?

**My take.**

_(você escreve, em primeira pessoa)_

**Refined write-up.**

_(preencho depois que você compartilhar seu take)_

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

_(você escreve, em primeira pessoa)_

**Refined write-up.**

_(preencho depois que você compartilhar seu take)_

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

_(você escreve, em primeira pessoa)_

**Refined write-up.**

_(preencho depois que você compartilhar seu take)_

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

_(você escreve, em primeira pessoa)_

**Refined write-up.**

_(preencho depois que você compartilhar seu take)_

### 5.2 — What the authors do *not* claim
**Prompt.** Read the correctness discussion adversarially. Is the claim "this is
proved correct" or "we have taken great care and found no errors"? Note the exact
hedging. How should that calibrate the wording of FLIPHEX's own H1 verdict —
specifically, what is the strongest sentence you are entitled to write about a
4×4 result produced by one implementation, run once, by one person?

**My take.**

_(você escreve, em primeira pessoa)_

**Refined write-up.**

_(preencho depois que você compartilhar seu take)_

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

_(você escreve, em primeira pessoa)_

**Refined write-up.**

_(preencho depois que você compartilhar seu take)_

### 6.2 — The resource budget, honestly compared
**Prompt.** Collect the cost figures the paper gives: years elapsed, number of
machines/processors, the database sizes, when each phase ran. Then do the honest
comparison: FLIPHEX is a solo laptop project. Which parts of this pipeline are
*inherently* parallel-cluster-scale and which are only so because checkers is
1000× larger than FLIPHEX 5×5? Produce a one-line feasibility verdict for each of:
FLIPHEX 3×3, 4×4 (reduced deck), 5×5 endgame `k ≤ 3`, 5×5 full solve.

**My take.**

_(você escreve, em primeira pessoa)_

**Refined write-up.**

_(preencho depois que você compartilhar seu take)_

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

_(você escreve, em primeira pessoa)_

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

_(você escreve, em primeira pessoa)_

**Refined write-up.**

_(preencho depois que você compartilhar seu take)_

---

## Lessons Learned

_(filled at merge — what changed in how I think about exact solving.)_

## Failed Attempts

_(filled at merge — revised assumptions, reading dead-ends.)_
