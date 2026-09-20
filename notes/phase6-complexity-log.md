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
for the Knuth–Moore minimal tree. The exact count is **10^58.63**, about 240×
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
received. And the *claim* survives both: FLIPHEX at 10^58.6 is still far beyond
the weak-solution route that carried checkers at ~10^31.

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

## H4 — where FLIPHEX lands on both axes

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

## `figures/` — the canonical figure per hypothesis, carried from Phase 5

## TIL #4 — retrograde analysis, when backwards beats forwards

## `exercises/ex05_complexity_analysis.md`

## Lessons Learned

## Failed Attempts
