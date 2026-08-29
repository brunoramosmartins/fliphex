# Decision Journal

Chronological record of decisions that were not obvious, and what they cost.
Distinct from the ADRs: ADRs record *what* was decided and are stable; this
journal records *why it was live at the time*, including things that turned out
to be wrong. Freely editable, append-only.

Raw material for `writeup/main-writeup.md`.

---

## 2026-08-28 — Interim peek at the h1 re-run, and what the clock is made of

**No decision is taken here.** The h1 sweep is 13.7 h in and unfinished; this
records what was looked at so a later reader can see the peek happened and that
nothing was conditioned on it. EXP-002's registered measures — the digest replay
and the H2 criticality — need the complete sweep and are untouched.

**What was read: wall-clock only.** Six layers done (15 down to 10) in 12,906 s,
against h2's 13,245 s at the same point — h1 running 2.6% ahead. Layer 9, the
largest at 5.02 × 10⁹ configurations, has been running 10.1 h; h2 spent 16.4 h
there. Process CPU time equals elapsed time to the second, so nothing has been
suspended. No outcome data was read: both arms' root values were published on
2026-08-09 and 2026-08-13, and criticality is not visible until the sweep ends.

**The timing profile is a parity signature, not noise.** h2's per-layer
throughput alternates violently — 785k cfg/s at `t = 10` against 84.9k at
`t = 9`, 1,055k at `t = 8` against 46.8k at `t = 7`, and the gap widens going up:
9.2×, 22.5×, 66.8×, then 166× between `t = 4` and `t = 3`. Every slow layer is
odd, every fast one even.

The mechanism is in `solver/packed_sweep.py:385` — the child scan is
`while remaining and slot == SLOT_LOSS`, breaking out of all three nested loops
the moment a losing child appears. A position that is a **win** stops at its
first winning move; a position that is a **loss** must enumerate every
(cell × tile × rotation) before it can say so. Cost per configuration is
therefore a direct read-out of the win/loss mix, and odd `t` is P2 to move. The
sweep is slow exactly where the mover is mostly lost.

Two things this is **not**. It is not evidence for H1: it describes the
enumerated configuration space, most of which is unreachable, not the game. And
it is not evidence for H2 — criticality is a position-by-position comparison
between the arms and the clock says nothing about it. The residual 18% gap
between the arms at `t = 11`, where both hands are identical, is the deck showing
through the *values* rather than through the branching, which is the same
mechanism seen from the other side.

Worth keeping because it makes the runtime predictable for the first time: the
5×3's cost is not "17.5 × 10⁹ configurations" but "however many of them are
losses", and that is a property of the game, not of the machine.

---

## 2026-08-05 — The endgame database is cancelled, and H3 comes out better

`EXP-003` ran the full registered sweep and the answer is not close. Median nodes
to prove one 5×5 endgame position exactly: **480** at `k = 5` — the layer whose
database would be ~1.2 × 10¹⁵ positions and ~150 TB — and 806,474 at `k = 8`.
`k* > 8`, the pre-registered prediction (`k* ≥ 6`) held, and adr-012 takes
**Option B**: no endgame database is built. Twelve orders of magnitude is not a
constant factor to engineer away.

**The consequence I had pre-recorded fired, and forced a better design.** adr-012
said in advance that if the crossover was out of reach, H3 would lose the "5×5
retrograde endgame layers" member of its comparison set — the member the Phase 2
amendment added specifically so H3 would not rest on toy boards. Writing the
re-scope, I noticed the member H3 loses and the member H3 *needs* are not the
same thing. What it needed was **exact ground truth on the shipped game**; the
database was only the assumed way to get it. EXP-003 supplies a cheaper way:
solve sampled endgame positions on demand.

So H3's set becomes 3×3, 5×3, and 500 shipped-5×5 positions at `k ≤ 8` solved at
query time (`EXP-006`). That is stronger than what it replaces. The retrograde
route would have delivered whatever `k` the disk allowed, discovered afterwards;
the sample is fixed in advance at a `k` already measured to be affordable. And
because `solver/minimax.py` proves or raises rather than approximating, every
value in the set satisfies adr-004 R1 by construction instead of by audit.

I registered EXP-006 **before Axis 2 exists**. A comparison set fixed after
seeing the learner is not a comparison set. Two choices inside it that could
easily have gone unexamined: it uses **seed 2**, not EXP-003's seed 1, because
evaluating the learner on the very positions whose cost justified the design
would be circular; and positions come from **random play, not the learner's own
play**, because sampling from self-play lets Axis 2 choose its own exam. The
learner-distribution version is a more interesting question and is a *different*
experiment — it needs its own ID and may not be substituted for this one.

**An instrument defect, found by the analysis rather than by the run.** The
experiment printed `cens 0` for every `k` while `k = 8`'s no-TT arm had one
sample pinned at the 20M budget: the column showed only the with-TT count. The
JSON recorded it correctly per arm, which is the only reason it was recoverable,
and the analysis script's validity guard caught it on first execution. No re-run
— the rule reads the with-TT median, that arm is uncensored everywhere, and one
censored sample in 200 cannot reach a median anyway.

I got it wrong in both directions on the way through. The display hid censoring;
then my first guard hard-failed on *any* censoring, which would have thrown away
a perfectly usable result. The right criterion is the producer's own
`median_is_lower_bound`, with the individually affected statistics named — `max`
here, not the median. Both are now pinned by regression tests.

**Secondary finding, exploratory and labelled as such.** The transposition
table's value grows with `k`: 1.03× at `k = 3` to 2.15× at `k = 8`. Inside a
single deep-endgame search there is almost no path re-convergence — the subgame
graph is nearly a tree — and it only appears as empty cells accumulate. This does
*not* settle the database case by itself: a database sells reuse across different
roots, which is a different quantity from re-convergence within one search. Worth
keeping the two apart.

---

## 2026-08-05 — The 4×4 was never a FLIPHEX board

A pre-run red-team of `EXP-001`/`EXP-002` — deliberately before either ran —
found that the exact-solve target Phase 2 had just promoted is not a variant of
this game.

**16 is even, so draws are possible, and there is no tie-break.** `rules-canonical.md`
derives the impossibility of draws entirely from 25 being odd; `adr-010` V2
asserts the invariant totally and even says any `N` used must be odd;
`fliphex/rules.py` raises on a tied terminal. And `C(16,8) = 12,870` of the
4×4's 65,536 terminal configurations are 8–8 ties, about 20%. Phase 2 shipped
that contradiction inside itself: `adr-009` set `a = 8` on a 16-cell board while
`adr-010` was being written two documents away requiring odd `N`. Nobody
introduced the bug; it existed in the gap between two ADRs written the same week.

**Worse, the 4×4 deletes the mechanism H1 names.** The rules say the joker is the
25th tile and 25 is odd, so *the joker is what gives P1 the extra ply*. With
8 + 8 and no joker, P1 has no extra ply and **P2 places the last tile** — on the
fullest board, where flip power is maximal. So H1 could not lose there: "P1 wins"
reads as support, "P2 wins" gets dismissed as a parity artefact. An experiment
that cannot fail is not an experiment.

**A correction to the red-team, which was worth making.** It predicted the
4-column board had no symmetry at all. `scripts/check_symmetry.py 4 4` says
`|Aut| = 2` — but the automorphism is a **180° rotation**, not a reflection, the
exact opposite of the 5×5. Rotations map a tile's arrow pattern to another
rotation of the same tile, so the chiral `P3-y` cannot break one. `adr-009` keeps
`P3-y` in every reduced deck to "keep the mirror question alive"; on the 4×4 that
reason is void, for a different reason than the one proposed.

**The fix is better than the thing it replaces.** `adr-011` (Accepted the same day): reduced
boards must be odd, and the hands mirror the shipped game — P2 draws `a`
archetypes, P1 draws the same `a` **plus the joker**. Then `(a+1) + a = N`, both
hands exhaust exactly, P1 moves last, and P1's extra tile *is* the joker. That is
the 5×5's own structure at smaller scale. The 5×3 (15 cells) becomes the primary
target: same Z/2 mirror as the 5×5 (A↔E, B↔D, C fixed), `P3-y` breaks it again,
and 1.75 × 10¹⁰ against the 4×4's 9.3 × 10¹⁰ — cheaper *and* faithful.

It also fixes H2, which I had registered without a second arm. The contrast is no
longer "joker present/absent" — on an odd board you cannot remove the joker
without leaving the board unfillable. It is **what P1's extra tile is**: the
zero-arrow joker, or the next archetype. Both arms have `a+1` and `a` tiles, so
the two state spaces are *exactly the same size*. That isolates the joker's
strategic content from the structural extra ply, which is the distinction the
rules draw and which the old design confounded.

**And a number that was right all along.** `adr-004` and `adr-010` both quote
7.1 × 10⁵ for the reduced 3×3 — reproducible only with hands 5 + 4, which
`adr-009`'s "identical decks, `a = ⌈N/2⌉`" rule does not produce (it gives 5 + 5
and 1.47 × 10⁶). The documented figures had always assumed the rule adr-011 now
writes down. The rule was wrong, not the numbers.

**Two errors of mine in the registered entries**, both caught before running:
EXP-001's terminal layer read 512, which is `2⁹` and only correct if the hands
are exhausted — the full-deck 3×3 terminal is **326,177,280**, and a solver that
dropped the hand dimension there would pass V0 against my wrong number. And I
gated both entries on adr-010 V1 without noticing V1 is not decidable as written:
the closed-form bound counts configurations, so a *correct* reachable-closure
enumerator disagrees with it by exactly 2× at layer 1. "V1 must pass" had no
truth value.

---

## 2026-08-05 — Maybe there should be no endgame database

A literature scout on the endgame storage format came back arguing the format is
the wrong question.

**Othello.** Takizawa (2023) weakly solved Othello 8×8 with forward alpha-beta
and transposition tables, resolving positions at 36 empty squares and referencing
them from shallower search — and **materialised no endgame database**, having
judged a strong solution intractable. Othello is FLIPHEX's structural twin:
diverging, fixed termination, cells only fill, `k` empty ≡ ply `N − k`, hump
profile. It is the only game with that shape that has been solved, and it did not
use the artefact I was about to spend Phase 3 designing. It was not on the Phase 2
reading list; it should have been.

The arithmetic agrees. `k ≤ 5` is ~1.2 × 10¹⁵ positions, ~150 TB at one bit, and
each extra `k` costs 8–15×. Meanwhile the subtree below a `k = 5` node is order
10⁵–10⁷ nodes. A tablebase pays by amortising probes; here the search that would
probe it may be cheaper than decompressing a block.

**Three techniques that do not transfer, and I would have imported all three.**
(1) Predecessor-driven propagation with successor counters exists because chess
and checkers slices contain *cycles*; FLIPHEX layers form a DAG, one sweep
suffices — and `adr-003` discards tile identity, so un-placing is not even
locally invertible. Pull, not push. (2) The don't-care trick works because
"broken" is an O(1) *local* predicate in chess; FLIPHEX unreachability is
**global**, needing a path from ply 0. (3) Folding the mirror saves 50% against
8–15× per `k` — less than half a ply of depth, at a cost on every probe.

`adr-012` (Accepted the same day) therefore decides *not to decide*: three cheap measurements
(EXP-003 subtree cost, EXP-004 real compressibility, EXP-005 don't-care yield)
choose between building, not building, and a symbolic representation. One thing
it does fix now because it cannot be retrofitted: **V1's reachability count is
taken before any don't-care filling**, or the distinction between "unreachable"
and "computed" is destroyed.

The risk I am accepting, recorded so it is not discovered later: if the crossover
turns out to be beyond any reachable `k`, Axis 1 ships no endgame database, and
H3 loses the "5×5 endgame layers" member of its comparison set — the member the
Phase 2 amendment added specifically to stop H3 resting on toy boards.

---

## 2026-08-05 — Phase 3 opened

**Gate.** Phase 2's deliverables are all present: the four lit-notes and the
synthesis, `research.md` with H1–H6 locked under the `v0.3-hypotheses` tag, and
the TIL #1 draft. One item is short of the roadmap's wording.

**Carry-over: the exercise answers stay open, with no phase owner.** `ex01` and
`ex02` exist as problem sets; the answers are empty. The roadmap's task says
"complete `ex02`". Deliberately *not* carried into Phase 3 as a task and
deliberately not dropped either — Phase 3 will produce `ex03`, and making three
open sets compete for the same hours is how all three stay open. What the lock
actually needed from `ex02` was the corrected state-space bound, and
`scripts/layer_profile.py` supplies that independently, so nothing downstream is
waiting on them.

**Divergence from the roadmap.** Phase 2 ran on `phase-2/solver-reframe`, not the
planned `phase-2/study-and-hypotheses`, and the PR title followed the branch. The
phase turned into a solver-scoping phase somewhere around the Allis note. Not
patched in place — it is a `/project-roadmap revise` item.

**Scope call: verification is a first-class deliverable, not a test file.**
adr-010's V0–V6 got its own issue rather than riding along inside the solve
issues. The reason is the failure mode: a 4×4 solve emits one verdict out of
~10¹¹ states, and a wrong one looks exactly like a right one. If verification is
a subtask of "solve the 4×4", it gets done by whoever is trying to finish the
4×4, which is the wrong incentive.

**Open decision, ADR-shaped.** The endgame database storage format. adr-004
commits to retrograde analysis but says nothing about indexing, compression, or
how mirror folding interacts with the two. `k ≤ 5` on the 5×5 is 1.2 × 10¹⁵
positions in the bound; the gap between that and reachability (adr-010 V1) is
what decides whether this is feasible at all. Flagged now so it is decided before
code, not around it.

---

## 2026-08-05 — Phase 2 closing: four corrections and a numeric erratum

*Written the same day as the merge, after the fact.* Writing the refined
write-ups for `notes/phase2-synthesis.md` turned into an audit, and four things
that were already in the repo turned out to be wrong.

**The state counts were computed with both hands at 13.** Player 1 holds 13
tiles (12-tile deck + joker); Player 2 holds **12**. Three documents had used
13/13. Corrected: 3×3 full deck 3.1 × 10⁹ → **2.3 × 10⁹**; 4×4 full deck
8.3 × 10¹³ → **4.8 × 10¹³**. The reduced-deck 9.3 × 10¹⁰ and the headline
5×5 4.9 × 10¹⁷ were right. Found by writing `scripts/layer_profile.py` and
running it — not by re-reading. The 2026-07-31 entry above still carries the old
figures; it is left as written, because this journal records what was live at the
time.

**The same error had inflated the mirror argument.** I had reasoned that one
player could finish holding an unplayed `P3-y`, giving P(the mirror is never a
valid game symmetry) = 1/13 ≈ 7.7%. Every tile reaches the board, so that case
does not exist. E[fraction of plies where the mirror is valid] 0.29 → **0.31**,
effective augmentation 1.29× → **1.31×**, P(never valid) = **0**. The conclusion
— no clean 2× augmentation for Axis 2 — did not move, but it was resting partly
on a case that cannot occur.

**`k ≤ 3` was mislabelled.** 9.0 × 10¹² is the *exactly*-k=3 layer; the
cumulative slice is 9.4 × 10¹². The R&N note had it right and the Schaeffer note
and S3 conflated them.

**I had the proof-number-search argument backwards.** adr-004 said FLIPHEX has no
sudden-death goal, therefore PN-search offers no edge. That inference is wrong:
PN-search exploits tree *shape*, and Schaeffer used Df-pn on checkers, which has
no sudden-death goal either. What actually parks PN-search here is that FLIPHEX
enumeration has no scheduling problem to solve. Corrected in the amendment rather
than quietly rewritten.

**Two circularity traps, closed with one rule.** Axis 2 must not gate checkpoint
selection on Axis 1's solved values, and Axis 1's proof-producing runs must not
be seeded by Axis 2. Both are instances of: *neither axis may be used to select
or terminate the other along the dimension on which they are later compared*
(adr-004 R1/R2/R3, adr-005 amendment). H3 is the hypothesis that would have been
silently destroyed.

**adr-010 exists because a wrong answer will not crash.** Six mechanisms, V0–V6,
and — drafted before any result exists — the strongest sentence a single
implementation run once is entitled to write. It ends: "It has not been
independently reimplemented."

**What the phase actually was.** Planned as a study week. It became a scoping
phase: 4×4 promoted over 3×3, the problem reclassified as storage-bound rather
than search-bound, and the verification apparatus specified before the thing it
verifies.

---

## 2026-07-31 — Allis reframes the solver: 4×4 is the real target, not 3×3

Filling in the Allis lit-note surfaced four questions from the co-designer, and
two of them moved ADRs.

**The state-space bound, verified on paper.** Reconstructed the ~4.9 × 10¹⁷
figure from scratch to answer "why isn't it just 3²⁵?". The answer: a FLIPHEX
state is *not* colour-per-cell — because flips detach a cell's colour from who
placed it, the hands (which tiles each player has spent) are independent state.
`3²⁵ ≈ 8.5 × 10¹¹` is only the board; the hand factor (~5.8 × 10⁵) lifts it to
`Σ_t C(25,t)·2^t·C(13,⌈t/2⌉)·C(12,⌊t/2⌋) = 4.89 × 10¹⁷`. The `2^t` is the
upper-bound step — it treats every 2-colouring as reachable, which flip dynamics
do not guarantee. So the number is an honest *upper bound*, not Allis's exact
state-space complexity; the true value would need his Monte-Carlo method.

**4×4 is the strategically meaningful exact solve.** Swept the bound across board
sizes and found the full-enumeration frontier at N ≈ 13–15. 3×3 (9 cells,
3.1 × 10⁹) is trivially solvable but too cramped for real tactics — it is a
correctness fixture, not a strategy microcosm, and I was previously letting it
carry more weight than it can bear. 4×4 (16 cells, 8.3 × 10¹³ full deck /
9.3 × 10¹⁰ reduced) is both enumerable and rich enough for spatial/tempo play.
Promoted 4×4 from "attempt" to the primary exact-solve target for H1/H2
(adr-004 Phase 2 amendment; research.md Phase 2 amendment).

**Allis confirms alpha-beta over pn-search.** FLIPHEX is diverging +
fixed-termination (the Othello profile). Proof-number search earns its keep on
sudden-death goal-proving (qubic, go-moku); FLIPHEX has no such goal, so the
reading *strengthens* adr-004 rather than reopening it. Also corrected adr-004's
stale "trivial symmetry group" line: the Z/2 mirror (adr-008) is usable for TT
folding precisely in the endgame DBs, where both P3-y are placed.

**The reduced-deck gap is now explicit (adr-009, Proposed).** "Proportionally
smaller decks" was hand-waved in adr-004. It swings the 4×4 bound by ~3 orders of
magnitude and decides whether a reduced solve is a faithful shrink — so it needed
an ADR, not a default buried in code. Proposed policy: always keep P6 (max flip)
and P3-y (the chiral symmetry-breaker), fill by ascending arrow count. Flagged
OPEN-3: is a reduced board a physical variant or a purely computational device?

**Variants promoted to an optional hypothesis (H6).** The co-designer's "what if
we change the pieces or grow the board?" is the design-space question that lifts
this above "an agent for my game". Turned it into H6 — a *robustness* claim
(does the balance keep its sign under bounded perturbation?), guard-railed:
tested only after H1–H5 settle on the shipped 5×5, shipped game as fixed
baseline, analyse-don't-redesign. Droppable at lock without touching the spine.

---

## 2026-07-29 — OPEN-2 resolved, and a correction to adr-008

Two things, same day, tightly linked.

**OPEN-2 is resolved.** The two decks were cut from the same mould, so their
chiral `P3-y` tiles are *identical* (same chirality), not mirror images — both
players hold `(0,1,3)` on their own face. Consequence: **no deck confound for
H1**; it is a clean first-move (plus joker) question and does not split into
H1a/H1b. This clears the last blocker to locking the Phase 2 hypotheses.

**Correction to adr-008.** Working out the OPEN-2 consequence exposed an error I
had made: I claimed the board's Z/2 mirror gives the *game* a 2× augmentation
"conditional on OPEN-2." Redoing the arrow algebra, the chiral `P3-y` breaks the
mirror at the dynamics level **whenever it is still in a hand**, independent of
OPEN-2 (its reflection {0,3,5} is not a rotation of {0,1,3}, and no player holds
the reflected tile). The mirror is only a *partial* symmetry — valid on the
sub-game after both `P3-y` are placed and inert. OPEN-2 governs *seat
equivalence* (H1), not the augmentation. adr-008, `research.md` (dropped the
symmetry hypothesis), and the geometry prose were corrected.

Caught it before the lock, which is the point of the discipline — but noting it
as a genuine over-claim I made and then had to walk back.

---

## 2026-07-29 — The board is not asymmetric: it has a mirror (Z/2)

Studying AlphaZero — which *drops* symmetry augmentation because chess and shogi
are asymmetric — I stopped trusting the Phase 0 prose and actually computed the
board's automorphism group (`scripts/check_symmetry.py`). Phase 0 said the
symmetry group was **trivial**; it is **Z/2**. There is a left-right mirror
across column C (A↔E, B↔D, C fixed; NE↔NW, SE↔SW). 180° is genuinely not a
symmetry (columns B/D are staggered half a cell; and 25 is odd, so an involution
must fix a cell — the mirror fixes column C).

The Phase 0 argument ("A/C/E and B/D have different vertical centres") only ruled
out symmetries that *mix* the two column groups. The mirror stays within each
group, so the argument never applied to it. The doc even lists the counterexample
unknowingly: A1 and E1 are the two degree-2 cells and are each other's mirror
image.

Recorded as **adr-008 (Proposed)**. The subtle, project-elevating part: the
board-level mirror is unconditional, but the **game-level** symmetry is
conditional on **OPEN-2** — the chiral P3-y tile is the one piece whose mirror
leaves the deck. So OPEN-2 now gates two things: the H1 seat-asymmetry confound
*and* whether we get the 2× self-play augmentation / mirror-canonical
transposition. If it holds, FLIPHEX sits between chess (1×) and Go (8×). H1 is
unaffected either way — the mirror preserves the player to move, so it gives no
strategy-stealing argument.

This is also the second time a Phase 0 "fact" fell to a concrete check (after the
flip-rule toggle, adr-007). Pattern noted: validate load-bearing claims by
computation, not prose.

---

## 2026-07-29 — Thesis reframe: self-play as a game-design instrument

Reading AlphaZero shifted the project's centre of gravity. The compelling story is
not "apply AlphaZero to my game" (a common exercise) but "use self-play and exact
search as instruments to *understand and validate the design* of an original,
un-analysed game" — its first-player balance, joker effect, board geometry, and
tile distribution. Strong play becomes the means; understanding the design is the
end. H1/H2/H5 (already design-balance questions) become the spine; H3 is the
cross-axis honesty check; H4 situates the game; a new optional H6 turns the
adr-008 mirror into a testable sample-efficiency claim.

Applied to `docs/research.md` as the pre-lock working version (added a Thesis
section, promoted H1/H2/H5, made H3's multi-seed/Wilson-CI rigour explicit, added
H6, and corrected the symmetry amendment for adr-008). Guardrails held: analyse,
do not redesign; the shipped 5×5 first, variants as a stretch; keep a fixed
benchmark. Not yet locked — the lock waits on `OPEN-2` and lands at
`v0.3-hypotheses`.

---

## 2026-07-25 — Phase 2 opened

Study phase. Gate check on Phase 1 passed: engine, both agents, and 71 tests
present; `smoke_selfplay.py` covers the 1000-games criterion. Two carry-overs,
neither blocking:

- The `01_rules_and_geometry` notebook stays deferred to Phase 7 (decided at
  Phase 1 close, above).
- The "heuristic beats random ≥60%" exit criterion was never measured — only
  random-vs-random invariants were checked. Added as a Phase 1 close item (a
  short win-rate check) rather than assumed.

No new technique decision enters Phase 2 that needs a `literature-scout`
dispatch up front — the ADRs already fix the design. Instead the phase's job is
the *reverse*: read the founding literature (R&N Ch.5, Silver 2017/2018, Allis
1994, Schaeffer 2007) with one `lit-note` per source, and let any source that
contradicts adr-004 or adr-005 trigger an ADR amendment. `literature-scout`
stays available for any ADR the author decides to actively re-litigate.

No experiment runs this phase, so nothing is registered in
`experiments/registry.md` — the first entries arrive with the Phase 3 solver.

**Blocking exit condition:** OPEN-2 (are the two decks' chiral `P3-y` tiles
mirror images?) must be resolved on the physical board before H1–H5 lock at
`v0.3-hypotheses`. It is a live confound for H1 and cannot be deferred past the
lock.

---

## 2026-07-25 — Phase 1 closing: scope calls

Engine, both baseline agents, and the full test suite are done, and the flip
rule was validated by hand-play (see the toggle entry below). Two closing
decisions:

- **CI landed now** (`.github/workflows/ci.yml`): ruff, pytest, and a
  generated-docs-clean check. Worth having before the Phase 2 study work so the
  branch stays honest.
- **The `01_rules_and_geometry` notebook (#12) is deferred to Phase 7.** The
  hotseat CLI already gives interactive visual inspection of geometry and the
  flip rule, so the notebook's value now is presentational, not correctness. It
  travels with the UI/portfolio work.
- The "1000 random games" exit criterion is covered by
  `scripts/smoke_selfplay.py` (run once: 1000 games, all invariants held, ~11s)
  rather than a slow pytest case, keeping the suite fast.

---

## 2026-07-25 — Play-testing caught a wrong core rule: flip is a toggle

Building the hotseat CLI before training any agent paid off on day one. Playing
a two-human game, the co-designer noticed the 6-arrow tile placed among his own
pieces changed nothing, and questioned whether an arrow should flip a same-colour
tile.

Investigation confirmed the engine did exactly what Phase 0's `rules-canonical.md`
§4 told it to: a flip was an **assignment** to the placing player's colour, so
aiming at your own tile was a no-op. That was my error. The tiles are two-sided;
the poster says the pointed tile is *"virada (flipada)"* — **turned over** —
which inverts its colour unconditionally. An arrow at your own tile therefore
hands it to the opponent.

Fixed as a **toggle** (adr-007): one line in `apply_move`, plus the rulebook,
`engineering.md`, the greedy heuristic (now maximises net swing = opponent flips
minus self-flips, or it would damage itself), and the flip tests. Nothing
structural moved — toggle only changes colours, so adr-003's representation and
the state-space bound are untouched.

The lesson is the whole reason the CLI came before the solver and the network: a
subtly wrong core rule would have been learned faithfully by every agent and
silently poisoned every hypothesis verdict. "Play the game by hand first" earned
its place in the plan.

---

## 2026-07-25 — Phase 1 opened

Phase 0 shipped (tag `v0.1-foundation`, clean linear history). Gate check for
Phase 1 passed with no carry-overs — all 16 Phase 0 deliverables present.

Scope decision: keep the roadmap, the local tooling config, and `FLIPHEX.pdf`
local only (gitignored, purged from remote history via force-push). The remote is
the public artifact; the project direction and tooling are not part of it.

No open technique decision enters Phase 1 — the six ADRs already fix the engine
design — so no `literature-scout` dispatch here. Literature grounding (and any
ADR rebuttal) is deferred to Phase 2, as recorded in the roadmap's Phase 1
`lit-note` note.

---

## 2026-07-23 — Phase 0

### The physical artifact outranks the written rules

The 2017 poster carries both photographs and a prose rulebook, and the author
flagged the prose as out of date. Set an explicit precedence order in
`rules-canonical.md`: photographs > author's decisions > poster prose. Every
divergence is tabulated in §9 of the rulebook rather than silently resolved.

This mattered immediately — the roadmap described a "5-row zigzag", but the
photographs show flat-top hexagons in five *columns*. Same 25 cells, transposed,
different direction indexing. Reading the rules text alone would have produced
a subtly wrong engine.

### The deck turned out to be a theorem

The roadmap deferred "3 distinct archetypes — TBD" for the 2-, 3-, and 4-arrow
pieces, and the plan was to pick them by inspecting the physical tiles.

Counting first was better. Arrow patterns on a *two-sided* hexagonal tile are
equivalence classes under rotation **and** reflection — binary bracelets of
length 6 — and there are exactly 1, 3, 3, 3, 1, 1 of them with 1 to 6 arrows.
That is the poster's deck composition, term for term. The deck is not a
selection; it is the complete enumeration. Nothing was left to choose.

The reflection step is what makes it work, and it is physically motivated: the
tiles are purple on one face and green on the other, so turning one over both
changes its colour and mirrors its arrows. Under rotation alone there would be
13 classes and the design would need an arbitrary omission.

Left one thing open (`OPEN-2`): if both decks are the *same* physical object,
the two players hold mirror-image versions of the single chiral tile, and the
seats are not equivalent. That is a confound for H1 and has to be settled with
a photograph before hypotheses lock.

### Noticing that placed tiles are inert

The largest decision of the phase, and it came from reading the poster's
*CUIDADOS!* section: flips do not chain. Therefore a placed tile's arrows fire
once and never again, so from the next ply onward it is just a coloured token —
its pattern and rotation cannot affect anything.

So the state does not need to store orientation. The reachable state-space bound
drops from ~1.4 × 10³⁷ to ~4.9 × 10¹⁷, about 19.5 orders of magnitude, and
transposition tables go from decorative to essential (with rotation stored,
almost nothing would ever transpose).

This contradicts the roadmap's own Phase 2 exercise, which puts a `6^25` factor
in the state-space bound. Left the exercise in place but reframed: derive the
naive bound, find the inertness argument, derive the corrected one. Better
exercise than the original.

### The roadmap says 8 archetypes; there are 12

The roadmap says "the 8 arrow archetypes" and then enumerates 1+3+3+3+1+1 = 12
in the same sentence. 12 is right — one per piece per player. Corrected in
`piece-archetypes.md` rather than silently.

### The board has no symmetry at all

Expected some symmetry to exploit for transposition-table canonicalisation and
for network data augmentation. There is none: columns A/C/E and B/D sit at
different vertical centres, so the symmetry group is trivial.

Two consequences, both accepted: no free 2–8× augmentation in Axis 2 (unlike Go
or Connect Four), and no strategy-stealing argument available for H1, which now
*must* be settled computationally. The second is arguably good news — it makes
H1 a real question rather than a formality.

### Deferred: chose a factored policy head without evidence

`adr-005` picks a factored (cell × tile × rotation) policy head over a flat
1950-logit one, on parameter-efficiency grounds. The factorisation assumes
conditional independence, which is *false* — the best rotation obviously depends
on the cell. Went with it anyway because MCTS exists to correct a bad prior, and
wrote both fallbacks into the ADR.

Flagging it here because it is the decision in Phase 0 with the least evidence
behind it. It is R5 in the risk register and must be tested in Phase 4, not
assumed.
