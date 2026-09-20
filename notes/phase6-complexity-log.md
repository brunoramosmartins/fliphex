# Phase 6 — Axis 3: Complexity Analysis and Cross-Game Comparison (experiment log)

**Objective.** Quantify FLIPHEX's structural complexity on both axes that the
literature separates — state space and game tree — and place the game in the
Allis/Schaeffer landscape. Then decide the three hypotheses that remain: H4
(where FLIPHEX lands), H5's surviving half (win contribution per archetype) and
H6 (robustness of the design to bounded perturbation).

**Dates.** None. The roadmap is sequenced by dependency, not by calendar, and
this phase carries no external deadline.

**What the phase must end with.** The last three rows of the verdict table in
`docs/research.md`, each with the interval or exact computation that justifies
it. After this phase the table has no empty rows, and Phase 7 writes up a
closed set rather than an open one.

**What it inherits, and it is more than the previous phases carried.** Three
Phase 5 deliverables were never started — `figures/`, TIL #4 and `ex05` — and
two Phase 3 experiments have stood at "registered; 3×3 pilot run" since August:
EXP-005 and EXP-007. Their registered rule runs on the 5×3 and has not. That is
not a loose end here; EXP-007's exact reachable closure is the input to the
tightened state-space bound this phase must produce.

**The gates are in force**, all nine —
[`docs/measurement-gates.md`](../docs/measurement-gates.md). Gate 9 was written
at the close of Phase 5, after the first eight let the same defect through three
times, and this phase is the first to have it available from the start. It is
the relevant gate here more than anywhere: a complexity bound is a quantity that
the rules constrain by construction, and H5's frequency half was withdrawn for
exactly that reason.

---

## `complexity/state_space.py` — the upper bound, and the reachable one

Three numbers, in decreasing order of size and increasing order of honesty.

| | 3×3 | 5×3 | 5×5 (shipped) |
|---|---:|---:|---:|
| orientation-inflated | 7.175 × 10¹² | 8.231 × 10²¹ | **1.389 × 10³⁷** |
| configuration space | 711,963 | 17,506,580,337 | **488,676,694,181,949,003** |
| one-step orphans | 23,371 (3.2826%) | 60,009,757 (0.3428%) | 38,814,863,794,591 (**0.0079%**) |
| reachable bound | 688,592 | 17,446,570,580 | **488,637,879,318,154,412** |
| peak layer | `t = 5` | `t = 9` | `t = 15` |

The inflated row is kept in the module, under `orientation_inflated()`, because
"the bound was corrected" is a claim that should come with the discarded figure
attached. It is the roadmap's original expression, multiplying by `6^25` for
tile orientations. adr-006 makes placed tiles inert, so nothing downstream can
read a placed tile's rotation and the rotation is not part of the state. The
correction is a factor of 2.8 × 10¹⁹.

**The reachable bound needs no run.** A configuration has no predecessor exactly
when every occupied cell carries the colour of the player who did *not* just
move — the last cell placed always shows its placer's colour, because a tile's
own arrows never point at the cell it occupies. That is one colouring in `2^t`,
so the `2^t` cancels and the orphan count is a closed form. This is the identity
EXP-005's amendment proved on 2026-08-07, and it is why EXP-007's hundred-hour
5×3 closure was stopped: the correction it would refine is already in the fourth
decimal place on the shipped board.

**The correction shrinks by roughly an order of magnitude per board step** —
3.28% → 0.343% → 0.0079% — because the mass of the space sits at high `t`, where
`2^t` is enormous. A test asserts the ordering, so the claim is checked rather
than observed once.

**The profile is a hump, not a funnel**, on all three boards: the peak layer is
interior and the sizes rise then fall exactly once. That is the shape that says
the game does not converge, and it is the opposite of checkers.

### On the duplication with `scripts/layer_profile.py`

Both compute the same sum, and that is deliberate. `layer_profile` imports
nothing from `fliphex` on purpose — adr-010 V1 compares it against the solver's
own enumerator, and a comparison is only evidence if the two sides are computed
by different means. Collapsing them into one implementation would delete the
check. `test_agrees_with_the_independent_layer_profile` asserts they agree, per
layer, on all three boards, which is Phase 5's lesson 9 applied rather than
restated.

### The off-by-one, and why it has its own test

The identity calls layer 0 an orphan, because the opening position genuinely has
no predecessor. It is reachable: it is where the game starts. Without the guard
the 3×3 reports 23,372 against EXP-005's measured 23,371 — a difference that
vanishes in a percentage (3.2828% against 3.2826%) and survives in a count. I
wrote it wrong first, in the EXP-007 amendment, on all three boards, and it was
the 3×3's recorded count that caught it. `test_the_unguarded_sum_is_exactly_one_too_many`
pins the size of the mistake so a regression is recognisable rather than merely
detectable.

### Probes

Both load-bearing tests were checked by breaking the code they guard. Removing
the `t == 0` guard turns six tests red; swapping the two hand-parity factors in
`configurations()` turns eight red, including the independence check against
`layer_profile` and the `2^n` terminal-layer identity.

## `complexity/game_tree.py` — Monte Carlo estimation via random rollouts

**The Monte Carlo estimate is not needed. The count is exact and closed form.**

A move is (empty cell, tile in hand, distinct rotation), and *every* such triple
is legal — no capture condition, no passing, no position that forbids a move. So
a complete game is three independent choices made once each: a bijection from
plies to cells, a bijection from each player's plies to that player's tiles, and
a rotation per tile from its orbit. Hence

```
games = n! × d1! × ∏ orbits(hand 1) × d2! × ∏ orbits(hand 2)
```

| | 3×3 | 5×3 | 5×5 (shipped) |
|---|---:|---:|---:|
| opening moves | 180 | 525 | **1,450** |
| games (exact) | 4.876 × 10¹³ | 1.446 × 10²⁹ | **4.229 × 10⁵⁸** |
| log₁₀ | 13.69 | 29.16 | **58.63** |
| effective `b` | 33.2 | 87.9 | 221.3 |
| Knuth–Moore minimal | 10^7.62 | 10^15.56 | **10^30.49** |

Truncate the sum at `k` plies and the same argument counts the distinct `k`-ply
prefixes, with the products replaced by **elementary symmetric polynomials** over
the orbit sizes: choosing `j` tiles in order from a hand contributes
`j! · e_j(orbits)`. A naive `sum(orbits)^j / j!` would count selections with
repetition, and a tile cannot be played twice.

The tree is genuinely **unbalanced** — branching depends on which tiles the mover
has left, and the orbits run from 1 (`P6`, `JOKER`) to 6 — so no single `b^d` is
exact. The leaf count is exact anyway, because summing over orderings restores
the symmetry individual nodes break.

### H4's cited figure is wrong, and its own second figure proves it

The locked H4 statement cites **~10⁶¹** for game-tree complexity and **~10³⁰·⁵**
for the Knuth–Moore minimal tree. The exact count is **10^58.63**, about 236×
smaller.

The two locked figures are internally inconsistent, and the minimal-tree one is
the survivor. Recover `b` from 10^30.5 = `b^13` and you get `b = 222`; then
`b^25 = 10^58.65`, which is the exact answer to two decimals. Whoever derived
the minimal tree did it correctly from a branching factor and a depth, and the
full-tree figure does not follow from the same pair.

This is the second wrong number in H4's statement, after the `6^25` orientation
factor in the state-space expression. The hypothesis is **locked** and is not
edited: both belong in the verdict row, as deviations recorded against the
pre-registered text — the same treatment H1's unperformed 20-seed tournament
received. And the *claim* survives both, at least as literally worded: FLIPHEX
at 10^58.6 is far beyond the **~10⁴⁰** commonly attributed to checkers' game
tree — a figure `comparison.py` **declines to print**, because the reproductions
of van den Herik Table 1 disagree by one to two in the exponent. An earlier draft
of this paragraph cited "~10^31" for checkers. That number appears in no source
and in no artefact here; it was invented while writing. Corrected 2026-09-20.

### The estimator is kept, and it argues against itself

`rollout_estimate()` implements Knuth's 1975 random-path estimator against the
real engine — walk uniformly from the opening to a full board, multiply the
legal-move count at every node. It is unbiased: a leaf at depth `d` is reached
with probability `1 / ∏ b_i` along its own path, so each leaf contributes exactly
1 in expectation.

It is also nearly useless here, and the numbers say so:

| samples | ratio to exact | relative sd |
|---:|---:|---:|
| 100 | 0.67 | 1.86 |
| 1,000 | 1.14 | 4.82 |
| 10,000 | 1.05 | 4.04 |
| 60,000 | **1.02** | 4.00 |

A single rollout's spread is **four times** the quantity it estimates on the 3×3
and **five times** on the shipped board, because the branching is
multiplicatively skewed — a mover holding `P6` and the joker has two rotations
where a mover holding six ordinary tiles has thirty-six, compounded over 25
plies. The standard error falls as `sd / √n`, so 1% takes on the order of 10⁵
rollouts. `games()` returns the answer exactly, in microseconds.

I wrote the opposite in the docstring first — that FLIPHEX was "close to
balanced, so the spread here is small" — and the first run contradicted it. The
prose was wrong, not the measurement.

So the estimator's status is **verification of the formula, not the
measurement**: the status EXP-005's hours-long run took when its quantity turned
out to be a counting identity. This is the second time in one phase that the
roadmap asked for an expensive estimate of something a closed form already gives
exactly.

### Verified against the rules, not against itself

Gate 7. The strongest check walks the **5×1** — the smallest board adr-011
admits, five cells and hands 3 + 2 — to the **last ply**, and compares the leaf
count against `games()`. Both arms: 51,840 and 311,040, exact. Every other test
compares the closed form against a prefix or against another closed form; this
one compares it against `legal_moves` and `apply_move`.

Depth 3 on the 3×3 and 5×3, both arms, was walked once offline — sixteen cases,
sixteen exact matches — and the values are pinned in `KNOWN`. The suite re-walks
only to depth 2, because the 5×3's third ply has 95,975,880 leaves.

### Probes

Forcing every rotation orbit to 6 turns 13 tests red, including the 1,450-move
opening and the shipped tree's magnitude. Replacing `e_j` with the naive
`sum^j / j!` turns 12 red, including the full-depth 5×1 identity.

## `complexity/branching.py` — legal-move count by turn number

The width of a node is

```
(cells still empty) × (sum of rotation orbits over the mover's remaining tiles)
```

The first factor is fixed by the ply: `n − t`, always. The second is not — it
depends on *which* tiles the mover has spent, and the orbits run from 1 (`P6`,
`JOKER`) to 6. So there is no single branching factor at ply `t`; there is a
distribution, and it is closed form like everything else in this phase.

### The weighting is the part that is easy to get wrong

Nodes at ply `t` are not spread evenly over the mover's possible spent sets. A
prefix that spends a 6-orbit tile was reached by six times as many routes as one
that spends `P6`, so a spent set `S` carries weight proportional to
`∏ orbits(S)`. Averaging over spent sets uniformly answers a question about
*hands*, not about the *tree*.

The gap runs one way at every ply and it widens:

| ply | node-weighted | per spent set | gap |
|---:|---:|---:|---:|
| 8 | 628.7 | 682.6 | 8% |
| 16 | 161.8 | 200.8 | 19% |
| 24 | 2.9 | 4.5 | 36% |

**The tree's typical node is narrower than the hands alone suggest**, and
increasingly so as the game goes on, because the weighting favours having spent
the wide tiles and being left with the narrow ones.

### The identity that makes it checkable

Every node at ply `t` has one child per legal move, so

```
node-weighted mean branching at t  ==  prefixes(t + 1) / prefixes(t)
```

exactly, as a ratio of integers. `cross_check()` asserts it on every ply against
`game_tree.prefixes`, which reaches the same tree by elementary symmetric
polynomials over the whole hand with no subset enumeration anywhere. And because
these are ratios rather than averages of products, they **telescope**: the
product over all plies is the exact game-tree complexity, `4.229 × 10⁵⁸`, with no
Jensen gap to apologise for.

That identity earned its keep immediately. My first implementation weighted only
the mover's own spent sets and left out the cell arrangement, the play orders and
the other player's hand. The **mean was unaffected** — those factors are constant
across the loop — so every distributional claim still looked right. The node
count was out by twenty orders of magnitude, and the identity was the only thing
that said so.

### The shipped board, in full

| ply | mover | min | max | mean | per set | spread |
|---:|---|---:|---:|---:|---:|---:|
| 0 | P1 | 1,450 | 1,450 | 1450.0 | 1450.0 | 1.00 |
| 1 | P2 | 1,368 | 1,368 | 1368.0 | 1368.0 | 1.00 |
| 8 | P1 | 578 | 867 | 628.7 | 682.6 | 1.50 |
| 16 | P1 | 90 | 270 | 161.8 | 200.8 | 3.00 |
| 24 | P1 | 1 | 6 | 2.9 | 4.5 | 6.00 |

The first two plies are **uniform** — neither mover has spent a tile, so there is
nothing to vary. From then on the spread grows monotonically within each
player's own plies, reaching 6× at the last ply, where the width is just the
final tile's orbit.

### Two things the profile settles

**The hump is not a branching effect.** Mean width falls *strictly* at every
single ply, on both factors at once. So the hump in `state_space.py`'s layer
profile comes entirely from the `C(n, t)` cell factor, which peaks in the middle
while the width only shrinks. Worth stating because "the game gets more complex
in the middlegame" is the natural reading of the state-space chart and it is
wrong about the branching.

**The spread explains the rollout variance.** The multiplicative skew measured
in `game_tree.rollout_estimate` — a relative standard deviation of about five —
is this table compounded over 25 plies. A rollout that keeps drawing 6-orbit
tiles rides the `max` column; one that spends them early rides the `min`. That
is why an unbiased estimator still needs ~10⁵ samples for 1%.

### Probes

Dropping the orbit weighting (uniform over spent sets) turns 8 tests red,
including the direction claim on every board. Dropping the constant scale factor
— the bug I actually wrote — turns 8 red, all of them `cross_check`, which is
exactly the test that caught it the first time.

## `complexity/comparison.py` — the cross-game table

Scouted before writing, which was the right order: the literature search changed
the module's design rather than filling a form it had already decided.

### The definitions are Allis's, not van den Herik's

The terms originate in the 1994 thesis, §1.5 and §6.2, and the ingested copy has
them. Both are quoted verbatim in the module and `self_check()` confirms the
quotes against the file.

**State-space complexity** is "the number of legal game positions reachable from
the initial position of the game", and Allis adds, of symmetry, "We refrain from
such a refinement." So the headline figure is the **reachability-corrected
4.886 × 10¹⁷**, and adr-008's Z/2 mirror is *not* quotiented out. There is a
tension worth recording: Allis's *definition* is the reachable set, but his
*computed numbers* are invariant-consistent supersets refined by Monte Carlo
legality sampling — the uncorrected quantity. At 0.0079% apart it changes
nothing here. On another game it would.

**Game-tree complexity** is Definition 6.4: the solution search tree of the
initial position, at the minimal full-width depth that determines the value. He
writes "number of nodes" and then counts *leaves* in both worked examples — 600
grandchildren for the chess sketch, "9! = 362880 terminal nodes" for tic-tac-toe.
We report leaves, and carry the node total beside it; they differ by 1.399× on
the shipped board.

### Why our exact count belongs in the same column

**FLIPHEX's solution depth is exactly 25**, and the argument is written into the
module because everything rests on it. At most 25, because the board is then
full. Not less: at ply 24 one cell is empty and the mover holds one tile, and
that tile's rotation decides which neighbours flip and therefore the final colour
count, which *is* the outcome. A depth-24 full-width search leaves it
undetermined.

So the exact figure is not a different quantity from the literature's — it is the
same quantity, computed instead of sampled. The asymmetry runs one way, and
**Connect Four is the proof**: Allis and Schaeffer both cite 10¹⁴ where the exact
enumeration is 4.53 × 10¹², a factor of 22.

### The table

| game | state space | game tree | grade | solved |
|---|---:|---:|---|---|
| FLIPHEX 3×3 | 10^5.84 | 10^13.69 | exact | unsolved (solved here) |
| FLIPHEX 5×3 | 10^10.24 | 10^29.16 | exact | unsolved (solved here) |
| Nine Men's Morris | 10^11.00 | — | verified | strongly solved |
| Awari | 10^12.00 | — | verified | strongly solved |
| Connect Four | 10^12.66 | — | reported | weakly solved |
| **FLIPHEX 5×5** | **10^17.69** | **10^58.63** | **exact** | **unsolved** |
| Checkers 8×8 | 10^20.70 | — | verified | weakly solved |
| Othello 8×8 | 10^28.00 | 10^58.00 | verified | weakly solved |
| Chess | 10^45.00 | — | verified | unsolved |
| Reversi 6×6 | — | — | **refuted** | strongly solved |
| Hex 11×11 | — | — | absent | ultra-weakly solved |

### Two findings against the literature

**The 6×6 Reversi state space of ~10²⁰ is impossible.** `3^36 = 1.501 × 10¹⁷`
bounds it before any legality constraint is applied, so the repeated claim
overshoots by **666×**, and no primary source for it was found. `comparison.py`
computes the ceiling rather than asserting it. This matters directly: H4's
original Phase 0 wording was "complexity comparable to small Reversi", and the
figure that phrase was presumably anchored to does not exist. What *is* real
about 6×6 Reversi is the effort — Feinstein weakly solved it in 1993, second
player 20–16, in about a week and a half on a workstation of that era. That is a
far better comparison for our 5×3 than any 10^x.

**Connect Four's 10¹⁴ is 22× the exact count.** Tromp's enumeration gives
4,531,985,219,092, independently confirmed. The estimate is cited by both Allis
and Schaeffer. It is the cleanest available demonstration that these table cells
are estimates, which is why the module grades every cell instead of just filling
it.

### What the table refuses to say

**van den Herik et al. (2002) Table 1 is not reproduced.** It is the canonical
cross-game table and the right thing to cite — but two secondary reproductions of
it disagree by one to two in the exponent on four separate rows (Connect Four,
checkers, chess, Go), and that is not rounding. Those cells are graded `absent`
with the disagreement recorded. Closing them means opening the PDF. Until then
the table is short and true rather than long and borrowed.

Nine cells are empty, each with a reason, printable with `--gaps`.

### Provenance is executable

Every `verified` figure carries a quote, and `self_check()` **opens the cited
file and looks for it**. A citation that stops resolving fails a check instead of
sitting in a docstring being decoration. Breaking one quote string turns two
tests red.

**But `notes/sources/` is gitignored**, and I had the check depending on it —
which would have failed on a fresh clone and in CI, and is the self-containment
rule this project already has. Fixed: the **bibliography** is what is cited and
it is tracked and complete on its own; the local text is an *extra*. Where it is
present the quote is opened, where it is absent the check reports itself as
unperformed rather than passing silently. Simulated by parking the directory: 27
pass, 1 skips with the reason, and the CLI prints "6 quotes were NOT opened".

### The Allis OCR is unusable for numbers

**Zero** `<sup>` tags in that ingest, against 33 in Takizawa and 20 in Schaeffer.
The exponents were dropped: `3^ = 19,683`, `approximately 10"`, and line 1706 is
an entire table row reading `10*|10*|10»|10*|10*|10«|10'|10»|10"`. The prose and
all the definitions are intact, which is what we use it for. Every Allis-derived
*figure* in the table is taken from Takizawa or Schaeffer quoting him. Recorded
in a caveat file beside the source.

### One finding the H4 verdict will have to answer

**Othello 8×8's game tree is 10^58.00 and it was weakly solved in 2023.**
FLIPHEX's is 10^58.63 — a factor of four, not an order of magnitude.

H4 says the shipped board "is out of reach on both complexity axes", with the
game-tree clause reading "beyond the weak-solution route that carried checkers".
Read against checkers alone, the clause holds. Read against what has actually
been weakly solved, FLIPHEX sits just past a frontier that was crossed three
years before the hypothesis was written — and Takizawa, who crossed it, is in
this repo and was read in Phase 2.

The state-space clause is in better shape: 10^17.69 does exceed every
**strongly** solved game in the table (10^11, 10^12, 10^12.66), which is what
that clause actually claims. A test asserts it.

This is not resolved here. It belongs in the verdict, with both numbers.

## EXP-005 and EXP-007 on the 5×3 — the closure the bound depends on

**Both resolved without the run. Neither needed compute; both needed reading.**

The phase opened treating these as its heaviest inherited debt — two experiments
stuck at "registered; 3×3 pilot run" since 2026-08-05, whose exact reachable
closure the tightened state-space bound supposedly required. They dissolved on
inspection.

### The registered rules were already moot

Both entries decide the same thing: whether don't-cares stay in the adr-012
design. **adr-012 chose Option B — no materialised database.** With no database
there is no don't-care set to drop or keep, so neither branch of either rule
names a live choice. This is the status EXP-004 has carried since August,
recorded there as *"rule moot"* rather than repointed at some other decision, and
both entries now carry it the same way.

**EXP-005 needed no run at all**, and its own amendment of 2026-08-07 said so:
the quantity is a counting identity, `orphans(t) = layer(t) / 2^t`, so the
registered 5×3 figure is **0.3428%** exactly. That amendment even wrote *"the
hours-long run becomes a verification of the formula… not worth a day of compute
on the 5×3."* It was sitting in the registry the whole time.

### EXP-007 ran for 429.8 seconds and was stopped

| layer | total | reachable | unreachable | frac | time |
|---:|---:|---:|---:|---:|---:|
| 0–2 | 23,761 | 13,081 | 10,680 | — | 0.0 s |
| 3 | 713,440 | 501,876 | 211,564 | 29.7% | 0.6 s |
| 4 | 12,841,920 | 11,069,389 | 1,772,531 | 13.8% | 18.0 s |
| 5 | 113,008,896 | 105,552,006 | 7,456,890 | 6.6% | 411.3 s |

Six layers, 0.72% of the configuration space, matching the 3×3's shape and
extrapolating to **~0.7%** complete. The artefact records `complete: false` and
the instrument **refused to apply the registered rule to a partial run** — the
pre-registration working exactly as designed, with no intervention.

The surviving reason to finish was H4's bound, and the closed form settles that
too: one-step orphans are **3.2826%** on the 3×3, **0.3428%** on the 5×3 and
**0.0079%** on the shipped board. A fourth-decimal correction cannot move FLIPHEX
in a table spanning 10¹¹ to 5 × 10²⁰.

### My cost estimate was wrong twice, in the project's signature way

I told the author ~23 h per arm. That extrapolated the 3×3's runtime linearly
over **number of configurations**, and the closure's work is not per
configuration — it is `reachable(t−1) × empty cells`, because every marked
configuration is expanded over every legal move. The 5×3 has more empty cells and
larger hands, so branching enters as a multiplier a count-based extrapolation
cannot see.

Recalibrated on layer 4: **~89 h**. Recalibrated again on layer 5, whose forecast
came in 3% high at 411.3 s against 422 s predicted: **~100 h per arm**, with
throughput already degrading from 335k to 296k expansions/s as the bitsets grew.
Two arms exceed eight days.

This is Phase 4's first lesson — *measure the composed system, not its
components* — recurring on a Phase 6 instrument, **with the lesson already
written down**. Being able to quote a lesson is not the same as applying it.

### The gate was answered for the measure and not for the decision

EXP-007 answered gate 9 correctly for its own quantity. Its entry has carried a
falsifier since 2026-08-07 saying the closure must not collapse onto the one-step
identity — which is gate 9's question asked **six weeks before the gate existed**.

And the run was started anyway. Nobody asked the same question about the
*decision the number would inform*: the bound is 4.887 × 10¹⁷ with the correction
and without it, at the precision H4 reports. The quantity was free to vary; the
conclusion was not. `docs/measurement-gates.md` now asks both, and the second
question is cheap — compute the conclusion at the measure's floor and at its
ceiling and check they differ.

### The debt no phase close was responsible for noticing

These two sat in a non-terminal state through **three** phase closes. The
close-mode audit walks the *closing phase's* checklist, and these belong to Phase
3. They surfaced here only because a later phase happened to depend on them —
which is to say, by luck. A registry entry that is neither complete nor withdrawn
is currently nobody's job to find.

## H4 — where FLIPHEX lands on both axes

**Clause 1 supported; clause 2 survives only as literally worded, and the "out of
reach" reading it serves does not.** The two module sections above carry the
derivations; this one carries the verdict's shape.

### Clause 1 — supported, with its universal form flagged

10^17.69 exceeds every strongly solved game this project could source: Nine Men's
Morris 10¹¹ and Awari 10¹² (both quoted from Schaeffer, quotes resolved against
the text), Connect Four (10¹⁴ cited, 4.53 × 10¹² exact — FLIPHEX exceeds either),
and **Reversi 6×6**, which the hypothesis does not name: strongly solved, and
bounded above by `3^36 = 1.501 × 10¹⁷` before any legality constraint, so the
comparison uses that ceiling rather than a figure.

The clause says *"every game solved by full enumeration"*. That universal form is
**not decidable from a table of nine rows**, and the verdict says so. What is
established is that it holds against every such game with a sourced figure.

One classification caveat recorded rather than smoothed: the hypothesis lists
Connect Four among the full-enumeration games, but Allis solved it *weakly* in
1988, which is how this project grades it. It appears to have been strongly
solved later by symbolic classification, not verified here. The comparison runs
the same direction either way.

### Clause 2 — the claim outgrew its test

The magnitude is wrong by **236×**, and the locked statement's own second figure
proves it without any new measurement. Against checkers specifically the clause
holds. Against what has actually been weakly solved it does not: **Othello 8×8 at
10^58.00, solved in 2023**, three years before the hypothesis was written and by
a paper held in this repository and read in Phase 2. FLIPHEX is 4.2× larger — a
factor, not an order.

### The Phase 0 worry closed in H4's favour

The Phase 0 amendment recorded a fear that H4 *"may already be false"* because
4.9 × 10¹⁷ sits **below** Reversi 6×6's commonly cited ~10²⁰. That figure cannot
exist. FLIPHEX is in fact the larger of the two, by at least **3.26×**. The worry
was reasoning from a phantom — and the rewording it prompted was still the right
move, for the separate reason the Phase 2 amendment gives: proximity to one game
was the wrong *shape* of claim.

### What is not established

That FLIPHEX is solvable — nobody has attempted it, and clause 1 stands. Nor that
the Othello comparison is tight: Othello's 10⁵⁸ is a `b^d` estimate over 58 ply
while ours is an exact count, so they are the same order *as the literature
reports them*, and the comparison inherits the estimate's uncertainty.

### No experiment ID was allocated, and that is written down

Both axes turned out to be exact sums: no configuration, no seed, no sampling, no
decision rule, so the nine gates have nothing to be answered about. What replaces
them is verification against the engine's own move generator. The cross-game half
is a citation exercise, graded per cell rather than run. The registry's `##
Planned` section records this rather than leaving an absence, because *"this
planned row produced no entry"* should be a statement in the registry and not a
gap in it.

## H5 — win contribution per archetype

**Withdrawn 2026-09-20, before any entry was written. The surviving half of the
locked test is forced by the same mechanism as the half withdrawn two days
earlier.**

### The demonstration

Both hands exhaust exactly, and each player holds each of the 12 archetypes
once. So every archetype is played **once by the winner and once by the loser,
in every game**. Checked on EXP-017's 5,000 recorded games: **zero exceptions**.
"Win rate given archetype X was played by the winner" is 100% for all twelve, for
any agent and any strategy.

**The joker is worse than vacuous — it is an alias.** Only P1 holds it, so "the
joker was played by the winner" *is* "P1 won". The tally comes out at
**2,712 / 2,288**, which is exactly EXP-017's first-player split, game for game.
A joker win-contribution figure would have been the first-player advantage under
a different label, and would have been read as evidence about the deck.

That is a failure shape the first three gate-9 instances did not have. EXP-006's
denominator, EXP-016's root coverage and H5's frequency were all **constants**.
This one is free to vary — it just varies with something already measured and
reported elsewhere. A quantity can be unforced and still be worthless.

### Three unforced alternatives, and why none is registered

**Placement timing varies genuinely**: mean ply runs from **5.11** (`P5`) to
**22.80** (joker). But a uniform-random null stratifies it almost entirely by
**rotation-orbit size** — a uniform mover picks a 6-orbit tile six times as often
as a 1-orbit one:

| orbit | null mean ply | tiles |
|---:|---:|---|
| 6 | 9.58 – 9.87 | eight of them, inside a 0.3-ply band |
| 3 | 13.61, 13.81 | `P2-opp`, `P4-opp` |
| 2 | 16.07 | `P3-tri` |
| 1 | 19.02, 19.10 | `P6`, `JOKER` |

Most of the raw spread is the deck's rotation symmetry, not its design.

**Net of that null there is a large residual**, monotone in arrow count —
`r = −0.855` over 13 tiles, with `P6` at −8.56 plies, `P5` at −4.73 and `P1` at
+6.59. More arrows, played earlier than chance.

**And it is not usable.** The only ordered-game database this project holds is
EXP-017's, played by `SolverAgent`, whose pre-solver phase *is* the greedy
net-flip heuristic in `agents/heuristic_agent.py`. A flip-maximiser plays
many-arrowed tiles early and avoids them late, because late their arrows land on
its own pieces and score negative. The residual is a prediction of the agent's
objective, not a finding about the game.

**Cell choice and rotation choice** inherit the same confound and have no null
computed.

### What a registrable entry would need

An ordered-game database from an agent whose objective is not net flips, plus the
orbit null above as the comparison. The EXP-015 champions cannot supply it:
`data/az-runs/*/buffer.pkl` stores sampled positions, not ordered games. No run
is scheduled, and the gap is recorded as a statement rather than left as an
absence.

### The procedural lesson, which is the uncomfortable one

The frequency half was withdrawn on 2026-09-18 with a note saying win
contribution "survives — it is not forced". **I wrote that sentence in the same
paragraph where I applied the gate to its sibling, without applying it here.**
Answering gate 9 for one measure is not answering it for the measure you name as
the replacement. `docs/measurement-gates.md` now says so.

The H5 verdict row in `docs/research.md` carries a dated correction rather than a
silent rewrite, and H5 is now complete rather than half-open to this phase.

## H6 — robustness to bounded design perturbation

**Supported on every perturbation that exists, and the perturbation set cannot
falsify it.** Decided without a single new computation.

### The board-size family holds its own mechanism constant

Three points named: 3×3 → 5×3 → 5×5. Four exact solves, all returning **P1** at
`termination: exhausted`; the shipped board is not decidable and contributes only
EXP-017's corroborative 54.2%.

But **adr-011 requires every reduced board to have an odd cell count and gives P1
the extra tile**, so P1 moves last on every legal board including the shipped one.
The structural feature that most plausibly *causes* the advantage is held constant
by construction across the whole family.

EXP-009 makes that concrete on the 5×3-`h1`: **every one of the 12,841,920
configurations at `t = 4` is a P1 win**, and every one of the 713,440 at `t = 3` a
P2 loss. An early-game advantage that is total rather than positional is what a
structural cause looks like.

And the one board that *would* have perturbed the structure — the **4×4**, even
cells, and a 180° automorphism rather than the mirror — **is withdrawn by
adr-011**, because an even board admits draws and the rules define no tie-break.

### The named deck swap was forbidden five days before the lock

H6's example is "removing the chiral `P3-y`". `P3-y` is one of adr-009's two
**anchors**, and clause 1 reads *"Always include `P6` and `P3-y`"* — kept
precisely **because** it is the sole chiral tile.

**adr-009 was ratified 2026-07-31. The hypotheses locked 2026-08-05.**

Beyond that example there is no lever. `Variant` carries `n_cols`, `n_rows`,
`arm` and `first`; `archetypes_for` is deterministic in capacity. So the only
deck perturbation the engine admits is the `arm` swap — **which is H2**. And
`first` merely selects which colour moves first, which with identical decks
(`OPEN-2`, resolved 2026-07-29) is a relabelling.

### The joker half has no sign to preserve

H2 found the root value unchanged on both boards and both arms. The joker effect
on the game value is exactly **zero** — not positive, not negative — so "holds
its sign" is not a statement that can be true or false of it.

### What it cost, and what it rests on

Nothing, and that is the point. Every exact datapoint is one of the four solves
already read for H1 and again for H2; H6 reports them a third time. Producing an
independent one would have needed arbitrary-deck machinery the engine does not
have, an adr-009 amendment against a ratified clause, and **31–34 h** per new 5×3
arm at EXP-002's measured sweep cost.

### The shape of the finding

This is H4's clause-2 shape again, one hypothesis over: the claim survives its
test, and the test is narrower than the claim it was written to carry. A
falsifying experiment would need a board whose parity construction differs —
adr-011 forbids it — or a deck without an anchor — adr-009 forbids it. The
hypothesis asks whether the design is robust; the decision records that make the
variants legal are the same ones that keep the answer fixed.

Worth saying plainly: this is not a case of the ADRs being wrong. adr-009 and
adr-011 are both well argued and both predate the lock. It is a case of a
hypothesis written without checking what its own project already permitted.

## Tile criticality — the reference distribution H2's 17.07% is waiting for

**Unrun, and deliberately *not* withdrawn.** The distinction matters, because
this phase withdrew three other planned measures and the reasons were different
every time.

H2's registered measure came out at **17.07%** — the fraction of solved 5×3
positions whose value changes when P1's extra tile is swapped. The EXP-002
amendment of 2026-09-18 deferred its interpretation rather than reading it as a
verdict, because **no threshold for it was ever registered**. A magnitude with no
decision rule attached decides nothing, and the figure's canonical plot carries
no reference line for exactly that reason.

What would make 17.07% interpretable is the same measure computed **per
archetype**: if the joker sits inside the distribution the other twelve tiles
produce, it is an ordinary tile on this axis; if it sits outside, it is not. That
is the reference distribution, and it is this row.

### Why it was not run, and why that is not a withdrawal

It was not needed. H2's verdict rests on the four exhaustive solves, which return
P1 on both arms of both boards; H5 closed because both halves of its locked
measure are fixed by the rules; H6 closed because every perturbation it names is
either forbidden by a ratified ADR or not constructible. **No verdict waited on
this row.**

But unlike the frequency half of H5, the win-contribution half, or EXP-016's root
coverage, this measure is **not vacuous**. It is genuinely free to vary, it has
no agent confound — it reads a solved database rather than anybody's play — and
its null is not obvious in advance, which is what makes it worth measuring. The
other three were withdrawn because asking the question was a mistake. This one is
simply unasked.

### What it would cost

Almost nothing, which is the awkward part. It reads the existing 5×3 solution;
**no new sweep is required**. The reason it is unrun is not expense but that
nothing in the project currently needs the answer — and running a measurement
because it is cheap, rather than because a decision turns on it, is the habit
gate 1 exists to break.

Left in the registry as an open, affordable and unclaimed measurement rather than
deleted, so that a later phase or a reader can pick it up knowing exactly what it
would settle.

## `figures/` — the canonical figure per hypothesis, carried from Phase 5

**Seven figures, one per hypothesis with a verdict plus one support panel.** The
directory that shipped nothing in Phase 5 is now non-empty and checked.

| file | for | what it shows |
|---|---|---|
| `complexity-landscape.png` | H4 | the two-axis plane, and the state-space strip where the data actually is |
| `h1-first-player.png` | H1 | four exact solves in one panel, one sampled interval in another — deliberately different axes |
| `h2-extra-tile-criticality.png` | H2 | criticality by layer, with **no threshold line**, because none was registered |
| `h3-seeds-and-agreement.png` | H3 | both clauses failing, side by side |
| `h5-forced-measures.png` | H5 | two quantities that could not have varied, and the confounded third |
| `h6-perturbation-lattice.png` | H6 | every perturbation the ADRs permit, and the ones off the lattice |
| `state-space-and-branching.png` | support | the hump is a cell-count effect, not a width effect |

### The clause, made checkable

Phase 6 wrote the exit criterion as *"`figures/` is non-empty and every figure
regenerates from a tracked artefact"*. A clause nobody checks is how a directory
ships empty twice, so the check is code:

- **`figures/manifest.py`** declares each figure's sources by repository path and
  **imports nothing but the standard library** — matplotlib is in the `figures`
  extra, not `dev`, so CI can read the manifest without being able to plot. The
  test parses the module with `ast` rather than grepping, because its own
  docstring discusses matplotlib at length.
- **`test_every_source_is_tracked_by_git`** runs `git ls-files` on every declared
  source. This project gitignores `results/*.jsonl`, `data/` and
  `notes/sources/`, and a figure drawn from any of them would render here and
  nowhere else. That is the same self-containment trap `complexity/comparison.py`
  fell into earlier in this phase.
- **`figures/README.md` is generated** from the manifest, like
  `docs/board-geometry.md`, with a test asserting it is current.

### The outputs are not tracked, and that is the rule being followed

`figures/*.png` is gitignored, and the reason is written directly above the line:
*"track the per-item record when regenerating it needs something the repository
does not have. **Reproducibility is the test, not size.**"* A rendered figure
needs only tracked inputs and a few seconds, so it stays out. The exit criterion
is satisfied by the *sources* being tracked, not by committing binaries.

`test_the_figures_are_ignored_because_their_inputs_are_tracked` pins that as a
decision rather than a habit: if someone starts committing PNGs, or stops
ignoring them, the test says so and the rationale has to be updated with it.

**I got this wrong first, and the skips are what caught it.** My original test
asserted the rendered files were tracked and, when they were not, skipped with
the instruction *"run `git add figures/…`"* — which `git` would have refused,
because the path is ignored. Seven skips that could never be resolved.

Pulling that thread found two tests that would have **broken CI on a fresh
clone**, where no PNG exists because none can be checked out:

- `test_the_rendered_file_exists` asserted existence unconditionally. It passed
  here only because I had just built them.
- `test_the_directory_holds_no_stray_images` asserted `rendered == declared`.
  On a clone `rendered` is empty. The right relation is **subset**: an
  undeclared PNG is the defect, absence is not.

Both are the same mistake — writing a test against the machine I was sitting at
rather than against a clone — and it is the same shape as the
`notes/sources/` dependency in `complexity/comparison.py` earlier this phase.
Simulated both ways now: with the figures parked, 41 pass and 7 skip with a
*followable* instruction; with them present, 48 pass and nothing skips.

The real guard against Phase 5's empty directory is
`test_a_builder_really_produces_a_file`, which imports matplotlib or skips, runs
one builder end to end, and checks a file comes out. Everything else in the
module checks declarations; that one checks a declaration becomes a figure.

### Two conventions the figures follow

**Provenance is drawn, not annotated.** Filled markers are computed here, hollow
ones are cited, and a cell nobody could source is absent rather than
interpolated. The landscape figure's plane has four points and its strip has
nine, and the titles count them from the data so they cannot drift.

**A threshold line appears only if one was registered.** H2's figure is the
standing example: 17.07% is drawn, and no reference line is drawn beside it,
because a line on a chart reads as a threshold whether or not anyone declared
one. The chart says so in words.

### What the figures caught

Rendering forced three corrections that reading had not. The `state-space`
annotation sat on top of the bars and hid the very numbers it quoted; H5's note
rendered literal `**` because matplotlib has no markdown; and the landscape's
first title hardcoded "eight games" over a chart with nine rows. All three are
the same defect — prose written next to data rather than from it — and the fix
in each case was to derive the text from the figure's own inputs.

## TIL #4 — retrograde analysis, when backwards beats forwards

<!--
Carried from Phase 5, not started, and on the author's standing standby with
TILs #2, #3 and #5. First person, not ghost-written.

Material this phase added to what Phase 5 already listed: EXP-007's stopped
closure is a *forward* sweep that was abandoned because a closed form answered
the same question, which sharpens "when does backwards beat forwards" into "when
does either beat a derivation". And EXP-005's identity is the cleanest example in
the project of a retrograde quantity that turned out not to need the retrograde.
-->

## `exercises/ex05_complexity_analysis.md`

<!--
Carried from Phase 5, not started, same standby.

The roadmap's three questions are all now answerable from this phase's modules,
and two of them have answers that differ from what the question expects:

- Q1, derive an upper bound on the state space "accounting for 25 cells with 4
  states x 6 orientations" — the 6 orientations are **wrong**, adr-006 makes
  placed tiles inert, and the exercise should end at 4.887e17 rather than the
  1.389e37 its own wording leads to.
- Q2, tighten the bound by removing unreachable states — closed form, 0.0079% on
  the shipped board, and the exercise is a good place to derive the `2^-t`
  cancellation by hand.
- Q3, explain why MC estimation of game-tree size is unbiased and state its
  variance behaviour — `complexity/game_tree.rollout_estimate` has the measured
  numbers, and the honest answer is that it is unbiased and useless here.
-->

## Lessons Learned

1. **Complexity analysis should search for structure before relying on samples.**
   Several Phase 6 quantities that initially appeared to require enumeration had exact or closed-form solutions. The orphan count, game-tree size, and branching identities could be derived directly from the game's combinatorial structure. The general lesson is to establish what can be known analytically before allocating compute to estimate it.

2. **An unbiased estimator can still be the wrong instrument.**
   The random rollout estimator for game-tree size was unbiased, but its variance made it practically useless at the required precision. Unbiasedness establishes correctness of the estimator, not suitability for the measurement.

3. **The distribution of branching matters more than a single average branching factor.**
   FLIPHEX does not have one representative branching factor. Branching depends strongly on the spent-tile configuration and declines through the game. Node-weighted and uniformly weighted averages diverge substantially at later plies. Reporting only one average would hide the structure that determines actual search cost.

4. **Independent implementation paths are stronger than repeated checks of the same computation.**
   The layer-profile analysis was cross-checked with an independently implemented script rather than only validating the original enumerator against itself. That check has passed from the first run, which is what a standing guarantee looks like rather than a discovery. The route that actually caught something was the same principle applied to branching: the prefix-ratio identity reaches the tree by a different derivation, and it was the only thing that exposed a node count wrong by twenty orders of magnitude.

5. **A count can look correct in percentages while being wrong in absolute terms.**
   The branching analysis initially omitted constant factors from the node count. The resulting percentage-level quantities looked plausible and the mean branching factor was unaffected, while the absolute node count was wrong by roughly twenty orders of magnitude. Ratios are not sufficient evidence when the underlying count is itself a reported result.

6. **A literature table is an evidence structure, not a collection of numbers.**
   Numerical comparison required provenance, definitions, and compatibility checks before values could be used. Several published or reproduced figures could not be safely transferred into the comparison table because their definitions or sources were insufficiently reliable. The table therefore records the boundary of the evidence rather than forcing every cell to contain a number.

7. **Not every registered experiment needs to be run; some experimental debt dissolves by inspection.**
   EXP-005 did not require the planned computation because the registered quantity followed exactly from the closed-form orphan identity. Likewise, part of the inherited EXP-007 debt was rendered moot by adr-012, which had already selected Option B and therefore eliminated the need for the corresponding materialized-database path. A registered experiment should be executed when it resolves an open question, not merely because its identifier exists.

8. **A lesson is not learned until it changes the next experiment.**
   EXP-007 reproduced a Phase 4 failure despite the relevant lesson already being explicitly documented: estimating compute by extrapolating configuration counts instead of measuring the composed workload. The first estimate suggested roughly 23 hours per arm. Recalibrating on layer 4's measured time raised that to roughly 89 hours per arm, and recalibrating again on layer 5's raised it to approximately 100. Both figures are totals for the complete closure, not per-layer costs — the next layer alone was projected at about one hour. The important failure was therefore not the arithmetic itself, but the failure to apply an already-known experimental principle.

9. **A measurement gate must be answered for the decision, not only for the measurement.**
   Gate 9 was initially treated as asking whether the registered quantity could vary. That is only half of the question. The relevant question is whether plausible variation in that quantity could change the decision the experiment was intended to inform. For EXP-007, the bounds changed the measured quantity but did not change the conclusion relevant to H4. A gate that does not connect measurement uncertainty to decision sensitivity can pass while leaving the decision effectively unchanged.

10. **Experimental debt needs an explicit owner and a terminal state.**
    EXP-005 and EXP-007 remained non-terminal across three phase closes because the close-mode audit inspected the current phase's checklist, while the unresolved registry entries belonged to an earlier phase. The same ownership problem appeared in H6: an “optional” hypothesis had no phase responsible for bringing it to a terminal state. Optional work without an owner is not merely deferred work; it is unassigned experimental debt.

11. **A hypothesis can survive a test that cannot falsify the claim it was written to carry.**
    H6 survived every permitted perturbation, but the project's own ADRs restricted the design space so strongly that the test could not exercise several of the mechanisms named by the hypothesis. The result is therefore not evidence of robustness against those perturbations. More generally, a passing experiment is only informative when the experiment had a reachable path to failure.

12. **A full verdict table does not mean the hypotheses were well posed.**
    Phase 6 produced a complete verdict table, but several hypotheses exposed a different problem: the locked test was not capable of doing what the hypothesis appeared to ask. Administrative closure and epistemic closure are different things. A hypothesis can have a verdict, supporting artifacts, and passing tests while still requiring qualification because its experimental boundary was narrower than its claim.

## Failed Attempts

### EXP-007 — Full 5×3 layer expansion

The initial cost estimate extrapolated execution time from the number of configurations in each layer. The estimate was approximately 23 hours per arm, but this treated configuration count as a proxy for expansion work.

The experiment was stopped after 429.8 seconds. At that point, the observed workload showed that expansion cost was driven by reachable states multiplied by their available successors, not by the number of configurations alone. Recalibrating on layer 4's measured time produced approximately 89 hours per arm, and recalibrating again on layer 5's produced approximately 100 — both totals for the complete closure rather than per-layer costs. The original plan was therefore out by more than a factor of four.

This was a recurrence of a Phase 4 failure for which the methodological lesson was already documented. The failure was therefore not only an inaccurate estimate; it demonstrated that documenting a lesson does not guarantee that the experimental process has incorporated it.

### Gate 9 — Measurement validity without decision sensitivity

Gate 9 was applied to EXP-007 by asking whether the registered quantity could vary. That question was answered, but it was insufficient.

The corrected and uncorrected bounds both led to the same H4 decision at the relevant precision. The measurement therefore had uncertainty, but that uncertainty was not decision-informative. The gate had been answered at the level of the quantity rather than at the level of the decision the quantity was supposed to support.

The measurement-gate procedure was subsequently extended to ask both whether the measure can vary and whether plausible variation can change the associated decision.

### EXP-005 / inherited debt — Compute replaced by inspection

Two pieces of inherited experimental debt were resolved without running the originally anticipated computation.

EXP-005's registered 5×3 orphan quantity followed directly from the closed-form identity already established for the orphan count, so enumeration would not have added evidence.

A separate inherited dependency was also rendered moot by adr-012, which had already selected Option B and therefore eliminated the need for the materialized-database path. The important distinction is between an experiment that has not been run and an experiment whose unresolved question no longer exists.

### Registry debt — Non-terminal entries surviving phase closure

EXP-005 and EXP-007 remained in the registry without a terminal state through three phase closes. The close procedure checked the active phase's checklist, but the entries belonged to an earlier phase and therefore escaped the local closure audit.

The failure exposed an ownership gap: a registry entry that is neither complete nor explicitly withdrawn has no mechanism guaranteeing that a future phase will rediscover it.

The closure process was therefore changed to treat non-terminal registry state as experimental debt that must have an explicit owner, rather than as a problem belonging implicitly to whichever phase happens to encounter it later.

### H6 — Optional became unassigned

H6 remained marked as optional, but no phase was explicitly responsible for resolving it. As a result, “optional” functioned operationally as “unassigned.”

The problem was not that the hypothesis was optional. The problem was the absence of a terminal-state owner. A hypothesis can be optional and still require an explicit decision about whether it will be tested, withdrawn, or carried forward.

### H6 — The perturbation set could not falsify the hypothesis

The H6 test technically survived all permitted perturbations, but the project's ADRs constrained the legal design space so that several perturbations named by the hypothesis were unavailable.

The board-size family preserves odd parity, while the 4×4 case is excluded by adr-011. The named tile perturbation is also constrained by adr-009, and the remaining permitted deck/first-player variants either reduce to H2 or amount to relabeling. Consequently, the test could not exercise the full mechanism described by H6.

The result was therefore not evidence that the hypothesis was robust under those perturbations. It was evidence that the hypothesis had been formulated against a broader design space than the project actually permitted.

### H5 — Replacement measure remained structurally uninformative

H5 lost two measures two days apart, for two different reasons. The frequency measure was withdrawn on 2026-09-18 because the count vector is `[2]×12 + [1]` in every game: each archetype is played twice regardless of who wins. Its named replacement, win contribution, was withdrawn on 2026-09-20 because every archetype is played once by the winner and once by the loser, so the rate is 100% for all twelve.

Timing was a third quantity examined, never a registered replacement for either. It genuinely varies, but its residual association with arrow count is confounded by the behavior of the SolverAgent used to generate the games: its pre-solver is itself based on a greedy net-flip heuristic.

The observed correlation therefore cannot be interpreted as a game-intrinsic effect. A stronger experiment would require ordered games from an agent with an objective independent of net flips, together with an orbit-aware null model. Those ordered games were not retained in the existing AlphaZero buffers.

The failed attempt illustrates a broader distinction: a variable can have substantial empirical variation and still fail to provide an informative causal or mechanistic measurement.

### Random rollout tree-size estimator

The random rollout estimator was unbiased but had extremely high variance. Its relative standard deviation was approximately 4 on 3×3 and approximately 5 on the shipped board, implying on the order of 10^5 samples for 1% relative precision.

The exact game-tree formula could instead be evaluated in microseconds. The estimator was therefore abandoned as the primary instrument rather than optimized further.

### Branching-count implementation

The first branching implementation omitted constant factors associated with cell arrangements, play orders, and opponent hands. This did not affect the mean branching factor, which made the intermediate output appear plausible, but it made the absolute node count incorrect by roughly twenty orders of magnitude.

An independent derivation exposed the discrepancy. The implementation was corrected before the branching results were used.

### Literature comparison

Several external values initially appeared suitable for direct comparison but failed provenance or consistency checks. In particular, a commonly repeated 6×6 Reversi state-space figure is incompatible with the basic 3^36 upper bound, and secondary reproductions of the Allis table disagreed on multiple rows.

Rather than filling the comparison table with uncertain values, unsupported cells were left absent and the provenance requirements were made executable through `self_check()`. The failure was therefore in the attempted use of the literature as a numerical lookup table; the corrected approach treated each value as an evidence item requiring a definition and traceable source.
