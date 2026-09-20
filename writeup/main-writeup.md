# FLIPHEX — the long-form writeup

> **Skeleton only.** The prompts below are questions to write *from*, not an
> outline to fill in. The content is first-person and is deliberately not
> drafted here — same rule as the TILs and the exercise sets. Delete each
> prompt as you replace it.
>
> **Every number in this file is pinned and checked**, so you never have to stop
> writing to go look one up. If a figure here disagrees with
> [`docs/research.md`](../docs/research.md), the research file wins and this one
> is stale.
>
> **Target: 6,000–8,000 words.** The suggested allocation is on each heading.
> Sections 4, 5 and 7 are half the piece between them; sections 1 and 8 are the
> only ones nobody else could write, so do not let them get squeezed.
>
> **One rule for the whole piece.** This project's result is *shaped* like a
> list of things that did not work: two hypotheses rejected, one true by
> construction, a locked figure wrong by 236×, a 135-hour training run that came
> 14 points short, and a database that was never built because searching was
> cheaper. Write that as the finding, not as an apology. The pre-registration is
> what makes it worth reading; a portfolio full of successes is a portfolio
> nobody can check.

---

## Opening — the hook

*~250 words.*

<!--
Candidates. Pick one, and do not use two.

- "I own the game." Most game-AI portfolio work analyses someone else's rules.
  This one analyses a game I helped design in 2017, in a course called
  Matemática, Arquitetura e Design, and that changes what the project can ask —
  I can put questions to the designer, and the designer is me, which turned out
  to cut both ways more than once.

- The deck-is-a-theorem opening (see §2). It lands in three sentences and it
  tells the reader immediately what kind of piece this is.

- The honest-failure opening: six hypotheses locked in August, verdicts written
  in September, two rejected. State the shape up front so the reader knows the
  piece is not a demo.

Whichever you choose, the second paragraph should say what the reader gets: a
game solved exactly on two boards, bounded exactly on the third, a learner that
was measured and came up short, and every claim carrying the date it was locked.
-->

---

## 1. The game, and where it came from

*~600 words. Nobody else can write this section.*

<!--
The facts, so you do not have to hunt for them:

- FLIPHEX, 2017, students of IME-USP and FAU-USP, course **MAP 2001 —
  Matemática, Arquitetura e Design**. Laser-cut wooden board, 25 hexagonal
  sockets, 25 two-sided tiles: purple on one face, green on the other.
- Each player holds 12 tiles carrying 1 to 6 outward arrows; P1 also holds the
  arrowless **joker**, so 12 + 12 + 1 = 25 and both hands exhaust exactly.
- Place one tile on any empty cell at any rotation; every arrow pointing at an
  occupied neighbour flips that neighbour to your colour. **Flips do not chain.**
  25 cells, odd, so there are **no draws**.

What this section is actually for — three things, in this order:

1. The object. It is wood. Write one honest paragraph about the physical thing,
   because the whole visual identity of the interfaces came from it (warm
   off-white, warm neutral, no grey window chrome) and because it is the reason
   §2 exists at all.
2. The course. Mathematics, architecture and design in one room. Say what the
   game was *for* in 2017, and be specific — this is the detail a reader
   remembers.
3. The turn. Eight years later the designer came back with a solver. Say what
   you actually wanted to know. The good version of this is not "I wanted to
   apply AlphaZero"; it is a question about the game you could not answer by
   playing it.

Two things to avoid: nostalgia, and any claim that the game is deep. §6 decides
how deep it is, with numbers, and it partially disagrees with the flattering
answer.
-->

---

## 2. Formalising a game that was never written down

*~900 words. This is the section with the best single story in the project.*

<!--
### The precedence order

The 2017 poster carries photographs *and* a prose rulebook, and the author — me
— flagged the prose as out of date. So `rules-canonical.md` fixes an explicit
precedence: **photographs > author's decisions > poster prose**, with every
divergence tabulated in §9 rather than silently resolved.

It paid off immediately: the roadmap described a "5-row zigzag"; the photographs
show flat-top hexagons in five **columns**. Same 25 cells, transposed, different
direction indexing. Reading the prose alone would have produced a subtly wrong
engine — the kind that passes every test you think to write.

Worth one sentence on the uncomfortable part: I was a source *and* the person
ranking the sources, and I ranked myself second.

### The deck turned out to be a theorem

The plan was to pick the 2-, 3- and 4-arrow archetypes by inspecting the tiles.
Counting first was better. Arrow patterns on a **two-sided** hexagonal tile are
equivalence classes under rotation **and reflection** — binary bracelets of
length 6 — and there are exactly **1, 3, 3, 3, 1, 1** of them with 1 to 6
arrows. That is the poster's deck composition, term for term.

**The deck is not a selection; it is the complete enumeration.** Nothing was
left to choose, and the 2017 designers evidently found the same twelve by hand.

The reflection step is what makes it work and it is physically motivated: a tile
is purple on one face and green on the other, so turning it over both changes
its colour and mirrors its arrows. Under rotation alone there would be **13**
classes and the design would need an arbitrary omission.

This is the best three-minute story in the project. Give it room.

### Placed tiles are inert, and what that saved

From the poster's *CUIDADOS!* section: flips do not chain. Therefore a placed
tile's arrows fire once and never again, so from the next ply it is just a
coloured token — its pattern and rotation cannot affect anything downstream.

So the state does not store orientation, and the bound drops from
**1.389 × 10³⁷ to 4.887 × 10¹⁷** — about **19.5 orders of magnitude**, a factor
of 2.8 × 10¹⁹. Transposition tables go from decorative to essential: with
rotation in the state, almost nothing would ever transpose.

Two honest riders. The roadmap's own exercise carried the `6^25` factor, and so
did the **locked** text of H4, where it could not be corrected and had to be
answered in the verdict instead. And the roadmap said "8 archetypes" while
enumerating twelve in the same sentence.

### The one I got wrong

Phase 0 recorded "the board has no symmetry at all" and accepted two
consequences: no free data augmentation for Axis 2, and no strategy-stealing
argument for H1. Six days later that was corrected — the board *does* have a
**Z/2 mirror** across column C (A↔E, B↔D, NE↔NW, SE↔SW); 180° is not a symmetry.
And it buys nothing anyway, for a reason worth stating: the chiral `P3-y` tile
breaks it at the game level while it is still in hand, so the mirror is only a
*partial*, endgame-restricted symmetry. It also preserves the mover, so it gives
no strategy-stealing argument either way. adr-008 and the journal entry of
2026-07-29.

Put this here rather than in §8. A formalisation section that admits one wrong
structural claim is more credible than one that does not.
-->

---

## 3. The research question, and why it has three axes

*~500 words. The shortest section. Do not let it grow.*

<!--
The question, verbatim from the README:

> Does the first player have a provable advantage, does the joker break game
> balance, and does the game admit an efficient learned policy that approaches
> optimal play?

The three axes, and what each one can and cannot answer:

  Axis 1 — exact solver: the truth, on boards small enough to exhaust.
  Axis 2 — AlphaZero-style learner: an approximation, on the board that matters.
  Axis 3 — complexity analysis: where the boundary between those two sits.

Then the part that carries the section: **six hypotheses were pre-registered and
locked** at tag `v0.3-hypotheses` on **2026-08-05**, before any experiment ran.
After the lock `docs/research.md` could only *gain verdicts* — no statement was
edited to fit a result.

Say plainly what that cost and what it bought. It cost: a wrong `6^25` factor
and a wrong 10⁶¹ that had to be carried in the text and corrected in the
verdicts; a 20-seed tournament that was registered and withdrawn unrun; an
"optional/stretch" hypothesis (H6) with no owning phase. It bought: every
threshold in this piece has a date earlier than the result it judges.

One line on perfect information, since it is why the project is possible at all
— this is the same author's PTCG work made tractable. See
`tils/til-01-perfect-vs-imperfect-information.md`, and keep it to a line.
-->

---

## 4. Axis 1 — how much of FLIPHEX can be solved exactly

*~1,400 words. With §5 and §7, half the piece.*

<!--
### What "solved" means, before any numbers

Allis's three grades, quoted verbatim in `complexity/comparison.py`:
ultra-weakly, weakly, strongly solved. Define them in three lines and then make
the distinction that the rest of the section runs on: **forward alpha-beta from
the opening, exhausted and proved, gives a *weak* solution; the same game swept
backwards gives a *strong* one.** Both terminate, both agree on who wins, and
only one can answer a question about a position handed to it.

### The two boards that fell

  | board | cells | configurations | result |
  |-------|------:|---------------:|--------|
  | 3×3   | 9     | 711,963        | **P1 wins**, both arms |
  | 5×3   | 15    | 17,506,580,337 | **P1 wins**, both arms |

All four solves: `termination: exhausted`. EXP-001 and EXP-002.

The 3×3 was done **twice, by independent methods** — forward alpha-beta and
retrograde sweep — agreeing on **604,347 of 711,963 positions (84.9%)**, with
adr-010's V1 exact at every layer. Say why the number is 84.9 and not 100: a
forward search does not visit what it prunes, which is the whole point of it.

### The reduced boards are not toys, and adr-011 is why

Every reduced board must have an **odd** cell count, and P1 draws one more tile
than P2 — so both hands exhaust exactly and **P1 moves last on every legal
board, the shipped one included**. The 4×4 is *withdrawn*: 16 is even, draws are
possible, and the canonical rules define no tie-break.

This is the design decision that makes the whole axis mean something: the
reduced boards reproduce the 5×5's own structure rather than merely being
smaller. Note the cost honestly — the feature that most plausibly *causes* the
first-player advantage is held constant by construction, so no board in the
family can vary it. That comes back in H6.

### The database that was not built

The roadmap scheduled a 5×5 endgame database. adr-012 asked the prior question:
does storing beat searching at all?

  Median nodes to prove one 5×5 position:  k=5 → **480**.  k=8 → **806,474**.

Under a second, either way, against a database of ~1.2 × 10¹⁵ positions and
~150 TB at one bit per position. Then the sharper version, which came from
reading Takizawa: the question has **two cuts**, not one — *enumerable above*
(storage) and *solvable below* (search) — and retrograde wins strictly between
them. On the 5×5 the cuts do not meet. Across k = 3…8 nothing is enumerable and
everything is provable in under a second. **The interval is empty.**

Two or three sentences, no more; the full version is TIL #4.

### The 580×, in one paragraph and a link

The 5×3 sweep went from a projected **108 days** to a projected **13 hours**
without changing the algorithm — same layer order, byte-identical output,
verified by checksum across two implementations and two interpreters. Every bit
of it came from not doing work that was never needed, starting with a Zobrist
hash computed 17 times per configuration in a sweep where **the index is the
key** and nothing is ever looked up by hash.

One paragraph and a link to `tils/til-06-the-index-is-the-key.md`. Resist.

### Verification, which is the part that makes the rest quotable

adr-010 defines **V0–V6** and grades every claim by which levels it carries. Say
what V1 is — an exact per-layer count against an independent enumerator, a
genuine `perft`, no tolerance — and say where coverage is *partial*: on the 5×3,
V4 has **no search evidence at t = 0..5**, and V6 covers **t ≥ 2 only**. Those
gaps are printed in the verdict rather than rounded away.

The generalisable point, and probably the section's closing line: a solver is
the one program that cannot be tested by comparing it against itself, because
there is nothing else that knows the answer.

### If you want one more paragraph

The 17.07% extra-tile criticality (1,237,229,498 of 7,248,350,863 positions),
and the 10,258,229,474 cross-arm positions compared with **zero mismatches**
where the tile is already spent — which proves the two arms are *distinct
instruments* rather than assuming it. But note that the 17.07% is **a magnitude,
not a verdict**: no threshold for it was ever registered. Reading it as one is
in Failed Attempts.
-->

---

## 5. Axis 2 — learning it from scratch

*~1,400 words.*

<!--
### The architecture decision with the least evidence behind it

adr-005 chose a **factored** (cell × tile × rotation) policy head over a flat
1,950-logit one, on parameter-efficiency grounds. The factorisation assumes
conditional independence, which is **obviously false** — the best rotation
depends on the cell. It was taken anyway, on the grounds that MCTS exists to
correct a bad prior, and logged as **R5** in the risk register with both
fallbacks written into the ADR and a requirement to test it in Phase 4.

Write this as the setup, because the risk materialised and the interesting part
is not *that* it did.

### EXP-011 — the risk fires, and the finding is about the mitigation

On the 5×3, flat beats factored and the arms do not overlap:

  | | factored | flat | gap |
  |---|--:|--:|--:|
  | top-1 optimality after 400 PUCT sims | 66.8% | 73.7% | **+7.0** |
  | supervised top-1 agreement | 58.6–60.8% | 65.6–68.6% | **+8.0** |
  | random-legal floor | | 39.6% | |

Per seed, factored `67.2, 66.6, 66.2, 65.8, 68.0` against flat
`74.2, 74.2, 75.6, 71.8, 72.8` — every factored seed below every flat seed.
Paired *t* = **+6.96** [+4.81, +9.11].

**The finding is that search closed about an eighth of the deficit.** adr-005's
first mitigation was "rely on MCTS to correct the prior, which is exactly what
MCTS is for", and at this budget on this board it is close to **inert**. That is
the sentence to carry, not "the flat head wins".

And it is an expressiveness ceiling, not an early-stopping accident: final
*training* policy loss **2.616** factored against **2.375** flat. The factored
arm is worse on the data it was fitted to. More epochs do not close it.

### The ladder, and the head that is smaller *and* better

EXP-012 adopted fallback (b) — and **cleared by 0.25 points**: `+3.32`
[+1.88, +4.75] against a 5-point tolerance, on a constant that had silently
changed role from EXP-011's *detection threshold* to an adoption *tolerance*
without being rejustified. A margin of 4.7 would have reversed it. Say so; a
decision that close should never be quoted as if it were comfortable. The
entry's own equivalence precondition also failed *unpassably* — half-width
**2.43** against δ = **2.00** — so no point estimate could have cleared it.

EXP-013 then replaced twenty-five unshared per-cell rotation maps (**43,290**
parameters) with a 1×1 convolution expressing the same conditioning in **198**,
a 218× reduction; on the shipped board the conditioned head drops from 467,839
to **347,887** parameters, which is *below* the factored head's own 352,495.
**The more expressive head is the smaller one**, and the reason is that a shared
convolution sees every cell on every position instead of the 36.7% an unshared
map sees.

Then the rider that matters: three architecture decisions taken against **5×3
solver ground truth**, and *none of them measured on the 5×5 until the run
itself*. The 3.3-point deficit is a 5×3 number quoted over a 5×5 design.

### EXP-015 — the run, and the seed that did not clear

5 seeds × 30 generations, **135.0 hours**. Four seeds clear the prior-free UCT
floor and one does not: seed 4 at **56.0%** [49.1%, 62.7%], **two games short**
of the bar. Per the pre-registered falsifiability clause a failing seed is
recorded, never averaged away.

And it is not one unlucky draw: between-seed `sd` **7.3%** against the **3.4%**
that sampling alone predicts, and homogeneity **χ² = 18.52 on 4 df rejects a
single underlying rate**.

### EXP-006 — fourteen points short, and a measure that was vacuous for six weeks

352 exactly solved won 5×5 endgame positions at k ≤ 8. All five champions score
**74.4% to 77.0%** against a threshold of **0.90** pre-declared on 2026-08-05 —
the best seed's *upper* limit is 81.1%. Context the rate may not be quoted
without: a random mover scores **21.9%**, the raw policy head **53.5%**.

The part worth the most words: the **first** version of this measure scored a
hit for every move from a *lost* position, because from a lost position every
move preserves the outcome. It was vacuous, and nobody noticed for six weeks.
Restricting to *won* positions is what made it a measurement.

### What this axis does and does not establish

Not established: **any cause** for either failure. Nothing varies architecture,
budget or training length. And not that the learner is weak in general — it
beats prior-free UCT on four seeds of five and a random mover by 54 points.

If you want the concrete ending: it also beat me. Say so, once, without
decorating it.
-->

---

## 6. Axis 3 — where FLIPHEX sits among known games

*~900 words.*

<!--
### Both bounds are exact, not estimated

  state space   **4.886 × 10¹⁷** reachable  (= 10^17.69)
  game tree     **4.229 × 10⁵⁸**            (= 10^58.63)

The game tree is an exact count of distinct complete games, not a `b^d`
estimate. Three facts make that possible: the solution depth is **exactly 25**
(at ply 24 the last tile's rotation still decides the colour count, so a
depth-24 full-width search cannot determine the value); **every** (empty cell,
tile in hand, distinct rotation) triple is legal — no captures, no passing, no
forbidden placement; and so a complete game is three independent bijections:

  games = 25! × 13! × ∏orbits × 12! × ∏orbits

Checked against `fliphex.legal_moves` at **full depth** on the 5×1 and to three
plies on both reduced boards and both arms — sixteen cases, sixteen exact
matches.

### Two findings against the literature, and they are the section's content

**Reversi 6×6's widely repeated ~10²⁰ state space cannot exist.** `3^36 =
1.501 × 10¹⁷` bounds it before any legality constraint, so the claim overshoots
by **666×**, and no primary source for it was found. This matters to us
specifically: H4's original Phase 0 wording was "complexity comparable to small
Reversi", and the figure that phrase was anchored to is a phantom. FLIPHEX is in
fact the larger of the two by at least 3.26×.

**Connect Four's cited 10¹⁴ is 22× the exact count** — Tromp's enumeration gives
4,531,985,219,092, independently confirmed, and both Allis and Schaeffer cite the
estimate. It is the cleanest available demonstration that these table cells are
estimates, which is why `comparison.py` **grades** every cell (`exact`,
`verified`, `reported`, `refuted`, `absent`) instead of just filling it, and why
`self_check()` opens the cited source file and looks for each `verified` quote.
A citation that stops resolving fails a check rather than sitting in a docstring
being decoration.

Nine cells are empty, each with a reason. **van den Herik et al. (2002) Table 1
is not reproduced at all**: two secondary reproductions of the canonical
cross-game table disagree by one to two in the exponent on four separate rows,
and that is not rounding. Short and true beats long and borrowed.

### The comparison that should worry a reader, and does

**Othello 8×8's game tree is 10^58.00 and it was weakly solved in 2023.
FLIPHEX's is 10^58.63 — a factor of four, not an order of magnitude.**

H4's locked clause 2 says the shipped board is "beyond the weak-solution route
that carried checkers". Against checkers, the clause holds. Against what has
actually been weakly solved, FLIPHEX sits just past a frontier crossed three
years before the hypothesis was written — by Takizawa, who is in this repository
and was read in Phase 2. Do not resolve this in your favour. It is in the
verdict with both numbers, and it should be in the piece the same way.

### One more, if there is room

The layer profile is a **hump, not a funnel**, on all three boards — the peak is
interior (t = 5, 9 and 15) and the sizes rise then fall exactly once. That shape
says the game does not converge, and it is the opposite of checkers. The
branching, meanwhile, falls *strictly* from ply 0, so "the game gets more complex
in the middlegame" is the natural reading of one chart and false of the other.
-->

---

## 7. The six verdicts

*~1,200 words. Every row gets its caveat or the section is worthless.*

<!--
Open with the shape, not the table: **two rejected, one true by construction,
one carrying a locked figure that is 236× wrong, and one supported on a
perturbation set that cannot falsify it.** Then go row by row. Full text with
intervals and evidence classes is in `docs/research.md` — quote it, do not
paraphrase it loosely.

**H1 — the first player has an advantage.** *Supported where perfect play is
computable; **not decidable** on the shipped 5×5.* Four exhaustive solves, all
returning P1. The caveat that must appear: the locked test's "20-seed self-play
win rate" **was not performed as written**. EXP-016 registered it and withdrew
it the same day, before running — prior-free UCT at 400 simulations visits only
10–18 of 325 root children, in board-cell order. EXP-017 replaced it with a
different quantity: **54.2% [52.9%, 55.6%]** over 5,000 games, under play that is
heuristic for ~17 plies and exact for the last 8 (`proved_rate` 32.0%). That
corroborates the direction and **says nothing about perfect play**.

**H2 — removing the joker does not change who wins.** *Supported where
computable; out of reach **by construction** on the 5×5.* Both arms return P1 on
both boards. The construction point is the interesting one: at capacity 12 there
is no next archetype to promote, so the joker is the only tile that can give P1
the extra ply, and `Variant(5, 5, Arm.H2)` **raises**. The hypothesis cannot be
tested on the shipped board because the board cannot be built.

**H3 — self-play converges and agrees with the solver.** ***Rejected, on both
clauses independently.*** Clause 1 by the seed spread (χ² = 18.52); clause 2 by
74.4–77.0% against 0.90. Then the clause-2 detail that is easy to miss and is
worth a paragraph: the 3×3 and 5×3 members are **unread**, and it changes
nothing — "every member" means one failure decides it. They are also
**unreadable with the artefacts that exist**: the champions are shape-locked to
the 5×5 (the head flattens 32 × 25 into a 25-logit readout, so a 5×3 raises),
and the only reduced-board networks this project holds were trained *supervised
on solver labels*, which adr-004 R1 forbids for exactly this comparison.

**H4 — where FLIPHEX sits.** *Clause 1 supported; clause 2 survives only as
literally worded, and the "out of reach" reading it serves does not.* The locked
~10⁶¹ is **236× high**; the exact count is 10^58.63. The two locked figures were
internally inconsistent and the *minimal-tree* one is the survivor — recover b
from 10^30.5 = b^13 and you get b = 222, then b^25 = 10^58.65, the exact answer
to two decimals. Whoever derived the minimal tree did it correctly from a
branching factor and a depth; the full-tree figure does not follow from the same
pair. Second locked error in the same statement, after the `6^25`.

**H5 — no archetype dominates.** ***True by construction on the measure it
names, and therefore not evidence of anything.*** Hands exhaust exactly, so every
archetype is played every game: the per-archetype count vector is `[2]×12 + [1]`
in **every one of 500 recorded games**. The inference the hypothesis draws —
"i.e. the 12-tile deck is well balanced" — **does not follow**. And the
correction of 2026-09-20 is the part to write: the *other* half is forced too.
Each player holds each archetype once, so every archetype is played once by the
winner and once by the loser, in 5,000 games, zero exceptions. Worse, the joker
is held only by P1, so "the joker was played by the winner" is "P1 won" — and
the count is **2,712 / 2,288, exactly EXP-017's first-player split**. Measuring
the joker's win contribution measures the first-player advantage under another
name.

**H6 — robust to bounded design perturbation.** *Supported on every perturbation
that exists — **and the perturbation set cannot falsify it**.* Every reduced
board returns P1, and EXP-009 makes it vivid: **all 12,841,920 configurations at
t = 4 on the 5×3-h1 are P1 wins**, and all 713,440 at t = 3 are P2 losses. An
early advantage that is *total* rather than positional is what a structural
cause looks like. But adr-011 requires every legal board to be odd and to give
P1 the extra tile, so the structural feature is held constant rather than
varied; the named deck swap — removing the chiral `P3-y` — is **forbidden by
adr-009 clause 1, ratified 2026-07-31, five days before the lock**; and the only
deck perturbation the engine admits is the arm swap, which *is* H2. A hypothesis
that cannot be falsified by its own perturbation set is a finding about the
hypothesis.

### The paragraph that ties the section together

Pick one of these and commit:

- Four of the six verdicts turned on something other than the measurement: a
  withdrawn experiment, an unbuildable variant, a forced quantity, an empty
  perturbation set. Pre-registration did not prevent any of that — it made all
  four visible and dated.
- Or: the most useful thing here is a catalogue of ways a well-posed hypothesis
  can fail to be a question. Name them: vacuous denominators, forced quantities,
  unbuildable arms, untestable universals.
-->

---

## 8. What exists now, and what I would do differently

*~700 words. The other section nobody else can write.*

<!--
### What you can actually run

Keep this to a short paragraph, because it is a call to action rather than a
finding. Three interfaces on one engine: a CLI, a pygame window, and a browser
page running the real Python engine under Pyodide — no reimplementation of the
rules in JavaScript, which is the whole point. Six seats per colour. The window
can seat the solver on top of the completed 5×3 sweep, and then `proved_rate` is
**1.0 from the opening**; the cost of that is peak resident **3.0 GB** and a
worst move of **4.9 s**, because layer 9 alone is 1.2 GB. Perfect play turned
out to be priced in memory bandwidth.

One sentence on what a visitor cannot have: the champion and the database are
gitignored (5.7 MB and 4.1 GB), so a clone falls back to search and says so.

### What I would do differently

Draw from `writeup/decision-journal.md` and the per-phase *Lessons Learned*.
Candidates, strongest first — pick three or four and write them properly rather
than listing eight:

1. **Check that the quantity varies before registering the experiment.** H5's
   both halves, EXP-005's orphan count and EXP-006's first denominator are the
   same defect: a number the rules already fix. The cheap guard is one
   paragraph, before the run, asking what the measurement would look like under
   a *different* strategy. That paragraph would have saved hours in three
   separate phases.
2. **A comment is not a constraint.** The palette, the typography and the arrow
   grammar were each declared twice, in two interfaces, with comments asserting
   agreement and nothing checking it — and one of them had been wrong since the
   file was written (pygame ignores the alpha channel, so arrows asking for 75%
   opacity drew at 100%, while the CSS honoured it). Single-source it, generate
   the second copy, and let CI fail on a dirty tree.
3. **Writing a restriction and implementing it are different artefacts, and the
   first feels like the second.** This happened four separate times in Phase 7
   alone. Worth its own paragraph.
4. **Derive thresholds when you set them, not when you quote them.** EXP-012
   cleared by 0.25 points against a constant that had changed role without being
   rejustified, and EXP-006's 0.90 was left underived.
5. **The roadmap is a hypothesis too.** `6^25`, "8 archetypes", "5-row zigzag",
   `b_avg = 30`, ~10⁶¹, a database that should not be built, and a peak in a
   monotone curve. Every one was caught by computing rather than by reading. Say
   what you would change about how the plan was written — that is the actually
   useful version of this item.

### The closing

Do not end on redemption. The candidate ending, if you want one: the game was
designed in 2017 to be played, and the most defensible thing this project
established about it is a list of questions it turns out not to answer. The
thing that makes that publishable rather than embarrassing is a tag dated
2026-08-05.

You can do better than that sentence. But do not do *nicer* than it.
-->

---

## Sources and pointers

<!--
- docs/research.md — every verdict, in full, with intervals
- writeup/decision-journal.md — dated decisions; Phase 0 entry is §1 and §2
- writeup/outline.md — the section plan this file follows
- notes/phase1..7-*.md — the per-phase record, and every number quoted above
- docs/adr/ — thirteen decision records; 003, 005, 006, 008, 009, 010, 011, 012
- experiments/registry.md — EXP-001..019, including the withdrawn ones
- tils/ — #1 perfect information, #4 retrograde, #6 the index is the key
- exercises/ex05_complexity_analysis.md — the complexity material as problems
-->
