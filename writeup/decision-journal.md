# Decision Journal

Chronological record of decisions that were not obvious, and what they cost.
Distinct from the ADRs: ADRs record *what* was decided and are stable; this
journal records *why it was live at the time*, including things that turned out
to be wrong. Freely editable, append-only.

Raw material for `writeup/main-writeup.md`.

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
