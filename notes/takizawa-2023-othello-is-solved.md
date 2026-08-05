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

**Refined write-up.**

### A2 — What is the game value, and from which position?

**Prompt.** What value does the paper report for Othello 8×8, and is it the value
from the initial position or from some set of positions? Compare with FLIPHEX,
where draws are impossible by parity: what does Othello's answer being what it is
tell you about how informative "who wins" is as a headline?

**My take.**

**Refined write-up.**

### A3 — 🔄 Place Othello in the Allis two-axis table

**Prompt.** Using [notes/allis-1994-searching-for-solutions.md](allis-1994-searching-for-solutions.md),
write down Othello's state-space and game-tree complexity and put them beside
checkers and FLIPHEX 5×5. Which of the two axes does this solve consume, and does
it support or complicate H4's claim that FLIPHEX 5×5 is out of reach on **both**?
Be specific: H4 rests on checkers being solvable at 5 × 10²⁰ states because it is
easy on the *tree* axis. Does Othello fit that story or is it a third pattern?

**My take.**

**Refined write-up.**

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

**Refined write-up.**

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

**Refined write-up.**

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

**Refined write-up.**

### B4 — Move ordering and where the engineering actually went

**Prompt.** How much of the feasibility comes from the algorithm and how much
from move ordering, the evaluation function used for ordering, and engineering?
Identify the single largest contributor the paper credits. Then answer for
FLIPHEX: adr-004's Phase 2 amendment split move ordering into an *agent* concern
and a *proof* concern (rules R1–R3). Does this paper respect that separation, and
if it does not, does its proof survive the objection?

**My take.**

**Refined write-up.**

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

**Refined write-up.**

### C2 — Is anything here statistical?

**Prompt.** Identify every number in the paper that is an estimate rather than an
exact count, and how its uncertainty is reported. Predict first: in a paper about
an *exact* result, where would statistics have to creep in? Then check whether
your prediction was right.

**My take.**

**Refined write-up.**

### C3 — Compute budget

**Prompt.** How much compute did the solve take, and on what hardware? Divide by
the state-space ratio to FLIPHEX 5×5 (~10²⁸ vs 4.9 × 10¹⁷) and by the branching
ratio (~10 vs 1450), and write down what those two adjustments do in *opposite*
directions. This is the honest version of "could I do this on a laptop?".

**My take.**

**Refined write-up.**

---

## D — Limitations, in the authors' own words

*Section `14-5-discussion-and-conclusions.md`.*

### D1 — What do they say they did not do?

**Prompt.** List the acknowledged limitations verbatim. Which of them would a
critical reader add that the authors do not? Pay attention to whether "solved"
in the title is defended or simply asserted.

**My take.**

**Refined write-up.**

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

**Refined write-up.**

---

## Lessons Learned

## Failed Attempts
