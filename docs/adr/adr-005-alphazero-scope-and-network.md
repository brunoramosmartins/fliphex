# ADR-005 — Small residual policy/value net over a factored action space

**Status:** Accepted (Phase 0)
**Date:** 2026-07-23
**Deciders:** Bruno Ramos Martins

## Context

Axis 2 implements AlphaZero on the full 5×5 game, trained on a single laptop
GPU (Dell G7). Two design pressures dominate, and they pull against each other:

**The action space is large for the size of the game.** A move is
(cell, tile, rotation) = 25 × 13 × 6 = **1950** slots, of which at most 1450 are
ever legal and typically far fewer. A flat policy head over 1950 logits on a
game with only 25 plies is a poor ratio of parameters to signal.

**The game is short and small.** 25 plies, no draws, ~4.9 × 10¹⁷ states
([adr-003](adr-003-piece-representation.md)). This is much closer to Connect
Four than to Go, and the published AlphaZero architecture (20–40 residual
blocks, 256 filters) is wildly oversized.

## Decision

**Input encoding.** The board is a `5 × 5` offset grid of planes (hex adjacency
is handled by the network learning it, not by the geometry of the tensor):

| Plane(s) | Content |
|---|---|
| 1 | own colour, per cell |
| 2 | opponent colour, per cell |
| 3 | empty, per cell |
| 4 | side to move (constant plane) |
| 5–17 | own hand: one constant plane per remaining tile (13, joker included) |
| 18–29 | opponent hand: one constant plane per remaining tile (12) |

29 planes of 5×5. Deliberately **no orientation planes** — placed tiles are
inert, so orientation is not part of the state (adr-003).

**Architecture.** A small residual tower: `3×3` conv stem to 64 filters, then
**4 residual blocks** of 64 filters, then the two heads. Target **~0.5–1.5 M
parameters**. Start at the small end; grow only if training plateaus below the
heuristic baseline.

~~**Factored policy head.** Rather than 1950 logits, the head emits three
factors — 25 cell logits, 13 tile logits, 6 rotation logits — combined as
`log p(cell) + log p(tile) + log p(rotation)`, then masked to legal moves and
renormalised. 44 logits instead of 1950.~~
**Superseded** — the head is now conditioned: rotation is read at the move's cell
from a **1×1 convolution** over `policy_conv`'s spatial map, 198 parameters. See
the two Phase 4 amendments below; the first adopted conditioning, the second
replaced its parameterisation.

**Value head.** Single `tanh` output in `[-1, 1]`. Since draws are impossible,
the training target `z` is always exactly `±1`.

**MCTS.** Plain PUCT over the real state — no determinization, no information
sets ([adr-001](adr-001-perfect-information-scope.md)). Dirichlet noise at the
root, temperature 1 for the opening plies then greedy.

~~**No symmetry augmentation.** The board's symmetry group is trivial (adr-002),
so unlike Go's 8× or Connect Four's 2×, there is none to exploit.~~
**Decision unchanged, justification superseded** — see the Phase 2 amendment
below and [adr-008](adr-008-board-mirror-symmetry.md). The board *does* have a
Z/2 mirror; augmentation is still rejected, on measured grounds.

## Consequences

**Positive**

- The factored head cuts policy parameters by ~40× and shares statistics across
  moves: learning that a cell is good transfers across all tiles played there.
  On a game with 25 plies per self-play game, sample efficiency is the binding
  constraint, and this directly attacks it.
- Dropping orientation planes shrinks the input and removes a large block of
  input the network would have had to learn to ignore.
- `z = ±1` always means the value head faces a clean binary target with no
  draw-mass to smear the output toward zero. Value learning should be fast.
- A ~1 M-parameter model trains comfortably on a G7, so the "two independent
  seeds" exit criterion for Phase 4 is realistic rather than aspirational.

**Negative / accepted costs**

- **The factored policy cannot represent arbitrary joint distributions.** It
  assumes cell, tile, and rotation choices are conditionally independent given
  the state, which is false — the best rotation depends heavily on the cell.
  This is the main risk in Axis 2. Mitigations, in order: (a) rely on MCTS to
  correct the prior, which is exactly what MCTS is for; (b) if the policy loss
  plateaus, condition rotation logits on the chosen cell; (c) fall back to a
  flat 1950-logit head, which is the safe design.
  **This must be checked explicitly in Phase 4 and logged**, not assumed away.
  **Checked and logged (2026-09-03, revised 2026-09-04).** (a) was measured and
  did not rescue the factored head (EXP-011); (b) was measured and is **adopted**
  (EXP-012), in its *efficient* parameterisation from 2026-09-04 (EXP-013); (c)
  is not run. The ladder is spent — see the two Phase 4 amendments below. Note
  that the clause *"the best rotation depends heavily on the cell"* is the part
  that remains **unverified**: the remedy is adopted, its stated reason is not,
  and EXP-013's prediction about *where* the efficient form would win also
  failed. Two adoptions rest on effects neither experiment could explain.
- No data augmentation means more self-play games for the same signal.
- Constant planes for hand contents are a wasteful encoding (13 planes of 25
  identical values each). Accepted for v1 because it keeps the tower
  convolutional and uniform; a concatenated vector at the head is the
  optimisation if memory bites.

**Neutral**

- Laying hex cells on a square 5×5 grid means the conv kernel's neighbourhood
  does not match hex adjacency. With a 4-block tower the receptive field covers
  the whole board anyway, so the network can learn the true adjacency. Worth a
  sentence in the writeup; not worth a hex-conv implementation in v1.

## Alternatives considered

**Flat 1950-logit policy head.** The literal AlphaZero design. Rejected as the
default on parameter-efficiency grounds, but explicitly retained as the
fallback if the independence assumption proves too costly. The comparison
between the two is a legitimate experiment for Phase 4.
**Run (EXP-011, EXP-012, EXP-013).** The flat head is the strongest arm every
time, and it is still not adopted. The conditioned head came within **3.3**
points of it, inside the tolerance this ADR's structure was worth; the
convolutional parameterisation adopted on 2026-09-04 narrows that to **2.37**
points at **347,887** parameters on the 5×5 against the flat head's 1,879,201 —
under a fifth. Retained as a fallback; no longer expected to be taken.

Recorded so it is not read as more than it is: the 2.37 figure is **descriptive**.
EXP-012's adoption rule permitted one extension and it is spent, so reopening the
comparison against the flat head requires a newly registered entry.

**Reuse `pgx` or `open_spiel`.** Would supply tested self-play plumbing. Rejected
for v1: the roadmap's stated skill goal is "implemented from first principles",
and FLIPHEX's action space would need a custom registration in either framework
anyway. Revisit if the training loop becomes the bottleneck.

**Larger network (10+ blocks, 128+ filters).** Rejected until the small one
demonstrably plateaus. Starting small makes the training curve legible and the
"grew the network because X" decision documentable — which is itself portfolio
material.

**AlphaZero-style with a learned model (MuZero).** Out of scope. The rules are
known and cheap to simulate; there is nothing to gain.

## Amendment — Phase 2 (2026-08-05): symmetry justification, the evaluator gate, and two guard rails

Reading R&N Ch.6, Silver 2017/2018 and Schaeffer 2007 produced four refinements.
None changes the network; one corrects a false premise, two add decisions the
original ADR left implicit, and one closes a methodological trap.

**1. The "no augmentation" justification was wrong; the decision survives.** The
board's symmetry group is **not** trivial — it is Z/2, a left-right mirror across
column C ([adr-008](adr-008-board-mirror-symmetry.md)). The struck bullet above
is replaced by:

> **No symmetry augmentation.** The board has a Z/2 mirror, but the chiral
> `P3-y` tile makes it a *partial* game symmetry: the mirror of a legal move need
> not be legal, so `M(s)` may not be augmented while either copy of `P3-y` is in
> a hand. Every tile is played (rules-canonical §2, I3/I5), so the condition is
> always reached — but late: under a uniform-random play order the second `P3-y`
> lands on ply 17.2 on average, leaving ≈**31 %** of plies augmentable. The
> available gain is therefore ≈**1.31×** in data, against a per-sample validity
> check and the risk that a wrong check silently trains the policy toward a move
> that does not exist. Not worth it.

Verified by `scripts/check_mirror_game_symmetry.py`: 150 of the 1450 opening
moves have no legal mirror image, all of them `P3-y`; the mirror becomes a full
game symmetry exactly once both copies are placed and inert.

**2. The evaluator gate is RETAINED, with an explicit game budget.** AlphaGo Zero
promotes a challenger only at ≥55 % over 400 games; AlphaZero drops the gate.
That removal is **bundled** with several other changes (single continuously
updated network, self-play from the current rather than the best network, reused
hyper-parameters) and no experiment in either paper isolates it — so the
published evidence is "a system without the gate works", not "the gate is
unnecessary". AlphaZero's replacement is a large replay buffer plus small
continuous updates, which damps regressions by construction but was never
measured. On a single laptop, where a collapsed run costs days and there is no
external benchmark for an original game, the discrete measured guard is worth its
compute.

The budget is not optional. At n = 400 evaluation games, two equal networks clear
55 % about 2 % of the time; at n = 100 they clear it **16 %** — a gate promoting
noise one time in six is worse than no gate, because it also manufactures
confidence. Adopt **400 games at 55 %**, or an explicit relaxation (gate every
`k` generations, or a lower threshold with its false-promotion rate stated).
Removing the gate is a Phase 4 optimisation to be justified by measurement, never
inherited from AlphaZero by default.

**3. Plain UCT with random playouts is the Axis-2 baseline.** AlphaZero makes two
substitutions and they have different standing for FLIPHEX. Replacing UCB1 with
PUCT is **required**: `√(ln N / n(a))` is infinite at `n(a) = 0`, so prior-free
selection must visit all 1450 opening children before it distinguishes any of
them, and UCB1's distribution-free regret guarantee needs far more simulations
than a laptop will run. Dropping rollouts is **inherited, not forced**: FLIPHEX
playouts are ≤25 plies, always terminate and always yield a decided winner, so
R&N §6.4's early-playout-termination machinery is void. Plain UCT is therefore
cheap to build and gives an absolute floor that depends on no trained network.
The learned agent must beat it before any result is reported.

**4. Checkpoint selection may not read Axis 1.** Scoring candidate networks
against the exact 4×4 database is tempting — near-zero compute, an objective
yardstick where none otherwise exists — and it is **circular**: selecting
networks by agreement with the solver and then reporting agreement with the
solver as H3's evidence optimises the metric directly. Solver positions may be
logged, plotted and watched as a *reported diagnostic*; no promotion,
early-stopping or checkpoint-selection decision may read them. This is the mirror
image of the rule [adr-004](adr-004-solver-approach.md) adopts for the other
direction, and the general form is stated there: *neither axis may be used to
select or terminate the other along the dimension on which they are later
compared.*

## Amendment — Phase 3 (2026-08-28): the action space is 4.46× redundant at the root

**The network does not change. Two Phase 4 checks become mandatory, and one
number used above is wrong.**

Placed tiles are inert and arrows fire only at *occupied* neighbours
([adr-003](adr-003-piece-representation.md),
[adr-006](adr-006-no-chain-reaction.md)). So two rotations of the same tile on
the same cell reach the **same position** whenever their arrow sets meet the
occupied neighbours identically — and on an empty neighbourhood every rotation
does, the tile landing inert and indistinguishable from the joker. The collapse
does not cross tiles: a different tile leaves a different hand.

`fliphex.moves.legal_moves` deduplicates rotations only *statically*, from each
tile's rotation orbit. Measured per position by
`scripts/measure_move_collapse.py` (seed 11, 12 random games on the 5×5):

| ply | actions | distinct positions | collapse |
|---|---|---|---|
| 0 | 1,450 | **325** | 4.46× |
| 4 | 992 | 375 | 2.65× |
| 8 | 633 | 347 | 1.83× |
| 20 | 47 | 41 | 1.16× |
| whole game | 148,740 | 65,126 | **2.28×** |

325 is exactly 25 cells × 13 tiles. The redundancy is worst at the root and
decays monotonically as the board fills.

**1. The Phase 2 amendment's point 3 overstates prior-free UCT's cost.** It says
UCB1 "must visit all 1450 opening children before it distinguishes any of them".
There are only **325 distinct opening positions**; 1,450 is the action count. The
argument for PUCT survives unharmed — 325 prior-free visits before any
discrimination is still far past a laptop's budget — but the figure should be
quoted as 325 wherever the *positions* are meant.

**2. MCTS must deduplicate children, and this is a search-quality decision, not
an optimisation.** Expanding aliased actions as separate nodes splits the visit
counts of one position across up to six labels. Two effects compound and point
the same way: the factored head assigns each alias its own prior, so a position
reachable by six rotations collects roughly six times the prior mass of one
reachable by a single rotation — a bias with no basis in the position's merit;
and split visit counts make each alias look under-explored, which PUCT answers by
exploring it further. The training target `π` is then read off those split
counts, teaching the network to spread mass across rotations and closing the
loop. The distortion is largest near the root, which is where search quality
matters most.

The fix is transposition-aware child expansion — index children by position, not
by action — and it is not free: it turns the tree into a DAG, and backup over a
DAG has known subtleties this ADR does not pre-decide. **Phase 4 must implement
deduplicated expansion and report the measured effect against the naive tree**,
on the same footing as the R5 check below.

**3. R5 gains a concrete failure mode.** The recorded risk is that cell, tile and
rotation are not conditionally independent. This adds a second, sharper one: a
sizeable share of the rotation factor's output is not modelling a choice at all,
because the rotation frequently does not change the resulting position. The
fallbacks in the Consequences section are unchanged and both still apply —
conditioning rotation on cell, then the flat 1950-logit head — but note the flat
head does **not** fix this: 1,950 logits over 1,450 actions is the same aliasing
with more parameters. Only deduplication addresses it.

**Update (2026-09-03).** The first of those fallbacks is now adopted and the
second is not run; see the Phase 4 mitigation-(b) amendment. The sentence above
about "a sizeable share of the rotation factor" was also measured, and it did not
hold: EXP-011 found rotation inert on **11.4%** of multi-orbit (tile, rotation)
pairs, not a sizeable share.

**Not evidence about the game.** The collapse was measured on reachable positions
by random playout. It says nothing about H1, H2 or H3.

## Amendment — Phase 4 (2026-08-31): the input is 30 planes, not 29

**The tower, the heads and the training scheme are unchanged. The input plane
table above is wrong by one plane, and the error is not cosmetic.**

The Decision section specifies the hands as **13 own** and **12 opponent**, which
sums with the four board and side-to-move planes to 29. That table cannot be
implemented as written alongside the encoding it sits in, because "own" and
"opponent" are relative to the side to move.

On the shipped 5×5 the first player's hand is the twelve archetypes **plus the
joker** — thirteen tiles — and the second player's is the twelve archetypes:

```
5x5-h1   purple bits=13 joker=True    green bits=12 joker=False
```

So on every ply where the second player moves, the *opponent* is the player
holding the joker, and a 12-plane opponent block has nowhere to put it. The
specified encoding hides the joker on half of all plies. The joker is the tile
that gives the first player the extra ply and therefore the last move of the
game; whether it has been spent is not a detail of the position.

**Corrected table.** Both hand blocks are 13 wide:

| Plane(s) | Content |
|---|---|
| 0 | own colour, per cell |
| 1 | opponent colour, per cell |
| 2 | empty, per cell |
| 3 | side to move (constant plane) |
| 4–16 | own hand: one constant plane per tile still held (13) |
| 17–29 | opponent hand: one constant plane per tile still held (13) |

The second player's joker plane is simply always zero, which costs one plane of
25 bytes and buys a layout that means the same thing on both sides.

**The bit is recoverable in principle, which is why this is worth stating.**
Occupied cells give the ply count, the ply count gives how many tiles each side
has played, and subtracting the visible archetype planes leaves the joker. But
that is a global count across the board — the operation a small convolutional
tower is worst at. Spending one input plane is cheaper than making the network
learn arithmetic to recover it.

**A second reason, in H3's favour.** Making both blocks 13 makes the layout
independent of the variant: the 3×3, the 5×3 and the 5×5 differ only in spatial
size, and plane *k* means the same thing on all three. H3's comparison set reads
across all three, so one layout for all three is worth having.

**The alternative reading, rejected.** Keeping 29 is possible if "own" always
means the first player rather than the mover. That costs the canonical
orientation: the value head's `+1` would no longer mean "good for the side to
move", and the network would have to learn each position twice. The perspectival
encoding is the more valuable of the two properties.

**Consequence for the sizing target.** The tower is now measured at **352,495**
parameters on the 5×5 (332,965 on the 5×3, 324,319 on the 3×3), still below the
0.5–1.5 M band this ADR targets. (Those are the factored head's counts. The
conditioned head adopted on 2026-09-03 brought the 5×5 to 467,839; the
convolutional form adopted on 2026-09-04 brings it to **347,887**, *below* the
factored figure and well inside the band.) That band was an estimate made before the
factored head existed; 44 output logits instead of 1,950 removes the projection
that carried most of the difference. The instruction — start at the small end,
grow only if training plateaus below the heuristic baseline — is unchanged.

Pinned by `tests/test_az_encoding.py`, whose
`test_the_opponents_joker_is_visible_when_the_second_player_moves` fails loudly
if the opponent block is ever narrowed back to 12.

## Amendment — Phase 4 (2026-09-03): mitigation (b) is adopted; the policy head is conditioned

**The input, the tower, the value head and the MCTS are unchanged. The policy
head changes, and the reason this ADR gave for needing it is *not* established.**

### What the Decision section now says

The Decision's **Factored policy head** paragraph is superseded:

> ~~Rather than 1950 logits, the head emits three factors — 25 cell logits, 13
> tile logits, 6 rotation logits — combined as
> `log p(cell) + log p(tile) + log p(rotation)`, then masked to legal moves and
> renormalised. 44 logits instead of 1950.~~

**Conditioned policy head.** The head emits 25 cell logits, 13 tile logits, and a
`25 × 6` **rotation tensor** read at the row of the move's cell. A move scores
`cell[c] + tile[t] + rotation[c, r]`, masked to legal moves and renormalised.
Cell and tile remain factored; **rotation is conditioned on the cell** and is no
longer independent of it.

The normaliser is no longer separable and must not be computed as if it were.
The correct closed form is nested:

```
Z = LSE over empty c of ( cell[c] + LSE over available (t, r) of ( tile[t] + rotation[c, r] ) )
```

A separable normaliser here does not raise. It optimises the wrong distribution
and reads as a slightly worse head, in the direction that would have refuted this
very amendment.

### Why: the ladder in Consequences is now spent to (b)

The Negative consequences list three mitigations in order. Both of the first two
have now been measured, and the entry for each is in `experiments/registry.md`.

**(a) rely on MCTS to correct the prior — did not rescue the factored head.**
EXP-011 measured the flat head at 73.7% against the factored head's 66.8% on
top-1 optimality after 400 PUCT simulations, a gap of **+7.0 points**
[+4.81, +9.11] over five seeds. The supervised gap before any search was +8.0.
Search closed one point of eight. That is the direct test of (a), and it failed.

**(b) condition rotation logits on the chosen cell — adopted.** EXP-012 trained
the conditioned head against the flat head at twelve seeds:

| head | top-1 after 400 sims (5×3) | seeds |
|---|--:|--:|
| factored (incumbent) | 68.0% | 5 |
| **conditioned (adopted)** | **73.2%** | 12 |
| flat | 76.5% | 12 |
| random legal move | 39.4% | — |

Only the two arms the adoption is read on were extended to twelve seeds; the
incumbent's figure is its five-seed mean, and it is shown for scale rather than
as a term in the contrast.

`flat − conditioned = +3.32 points [+1.88, +4.75]`, entirely below the 5-point
margin the experiment registered as the price worth paying for a factored
structure. **The rule fires and (b) is adopted.**

**(c) fall back to a flat 1950-logit head — not run, and now unlikely to be.**
Two reasons, both recorded before the result. It does not fix action aliasing:
1,170 logits over 540 legal moves on the 5×3 is the same redundancy with more
parameters. And on the 5×5 it costs **1,879,201** parameters against the
conditioned head's **467,839** — above the 0.5–1.5 M band this ADR targets, where
(b) sits comfortably inside it.

| board | factored | conditioned | flat |
|---|--:|--:|--:|
| 5×5 (shipped) | 352,495 | **467,839** (+32.7%) | 1,879,201 |
| 5×3 | 332,965 | 373,369 (+12.1%) | 879,381 |
| 3×3 | 324,319 | 345,127 (+6.4%) | 519,105 |

### What this amendment does **not** establish

This matters more than the adoption, because the sentence being amended is one of
this ADR's own claims.

**The stated mechanism is unverified.** The Consequences section asserts that
*"the best rotation depends heavily on the cell"*, and that assertion is
**exactly what EXP-012 could not read**. The experiment carried a validity
precondition — a pooled control with the conditioned head's parameter count and
shape but the factored head's function class — and that precondition **failed its
equivalence test unpassably**: the interval's half-width alone exceeded the
tolerance, so no result whatsoever could have cleared it. Every mechanism
contrast is therefore recorded as unresolved.

**The remedy is adopted; the reason this ADR gives for it is not confirmed.** Two
independent findings sit against the stated reason and neither is decisive:

- EXP-011 measured rotation to be **inert on only 11.4%** of multi-orbit
  (tile, rotation) pairs, against this ADR's implicit claim that much of the
  rotation factor models no real choice.
- EXP-012's frozen-tower condition put the conditioned, pooled and tile-indexed
  heads on one shared tower trained for the factored head. All three landed at
  **67.6–68.8%**, on top of the factored head's own 68.0%. On a tower trained for
  the factored head, **no head architecture makes any difference**. Whether that
  means conditioning is a property of the co-adapted network rather than of the
  head, or that an incumbent-optimal tower simply supplies no features a
  conditioned head could use, is not decided.

So: the head is conditioned because conditioning **works**, measured end to end
in the deployment configuration. It is not conditioned because the
cell–rotation dependence was demonstrated. A future entry that wants the
mechanism needs an equivalence gate whose tolerance is not equal to its own
forecast half-width, and a head-level condition that does not freeze the tower
into one arm's optimum.

### The adopted head is not the efficient implementation of (b)

`Linear(policy_features, 25 × 6)` is twenty-five independent maps with **no
weight sharing across cells** — it learns "which rotation, given which cell"
twenty-five separate times.

The tower is convolutional and `policy_conv` already produces a spatial map
before its flatten. A **1×1 convolution from 32 to 6 channels** on that map gives
per-cell rotation logits from shared weights over each cell's own features:
**198 parameters**, fully cell-conditioned, and statistically efficient in
precisely the way the adopted form is not. It also would not carry the adopted
form's data-efficiency handicap — a rotation row for cell `c` receives gradient
only on plies where `c` is empty.

It was named in EXP-012's registration as the obvious follow-up and deliberately
not run, so **this amendment adopts the inefficient implementation knowingly**.
The follow-up is registered. If it measures at least as well, this ADR should be
amended again to the convolutional form; the decision here is "conditioned, not
factored", and the parameterisation is the part still open.

**Closed (2026-09-04).** It measured at least as well. The convolutional form is
adopted by the next amendment, one day after this one; the sentence above is the
condition that was met, not a reversal.

### Two caveats on the evidence, stated at full strength

**The verdict cleared by a quarter of a point.** The interval's upper limit is
+4.75 against a 5-point margin. That margin was EXP-011's *detection threshold*
and became EXP-012's *adoption tolerance* without being rejustified for the new
role. A margin of 4.7 reverses the decision. This is recorded as the principal
threat in the registry entry and it is repeated here because it qualifies the
amendment, not just the experiment.

**All of it is 5×3 evidence, and this ADR governs the 5×5.** The direction is
favourable and that is why the amendment is taken: the conditioned head's tensor
is `15 × 6` on the 5×3 and `25 × 6` on the 5×5, and cell–rotation interaction
grows with the board, so the 5×3 **understates** (b) specifically. But
"understates in the expected direction" is an argument, not a measurement, and
nothing here is evidence about the shipped board.

### Anti-circularity

Under [adr-004](adr-004-solver-approach.md) R1, this is the **second** Axis 2
architecture decision taken against Axis 1's exact ground truth on the 5×3, over
an adoptable choice set of three (factored stands, conditioned, flat). H3's 5×3
evidence class records the count, and the count is the thing that measures the
leak — drawing a disjoint sample prevents statistical overlap but does not touch
the mechanism, since the architecture is a function of solver labels on a variant
inside H3's own comparison set.

Pinned by `tests/test_az_train.py`:
`test_each_conditioned_normaliser_equals_brute_force` checks the nested
normaliser against `logsumexp` over generated moves across three readouts, three
variants and three depths, and
`test_the_three_arms_have_identical_parameter_counts` pins the matching that made
the comparison legitimate.

## Amendment — Phase 4 (2026-09-04): the rotation head is a 1×1 convolution

**This supersedes yesterday's amendment after one day.** That is the condition
the previous amendment set for itself, not a reversal: it adopted the
unshared parameterisation *knowingly*, named the convolutional form as the
obvious follow-up, and wrote that "if it measures at least as well, this ADR
should be amended again". EXP-013 measured it. It does.

### What the Decision section now says

The rotation term is produced by a **1×1 convolution from 32 to 6 channels** over
the `(32, n_cols, n_rows)` map `policy_conv` already computes before its flatten,
read at the move's cell. Cell and tile logits are unchanged, the score is
unchanged — `cell[c] + tile[t] + rotation[c, r]` — and the nested normaliser is
unchanged. **Only the parameterisation of `rotation[c, r]` changes**, from
`n_cells` unshared maps to one shared map applied per cell.

| head | rotation params | 5×5 network total |
|---|--:|--:|
| factored (superseded 2026-09-03) | 4,806 | 352,495 |
| linear-conditioned (superseded here) | 120,150 | 467,839 |
| **1×1 convolution (adopted)** | **198** | **347,887** |
| flat (never adopted) | — | 1,879,201 |

**Full cell conditioning now costs less than not conditioning.** The adopted
network is 4,608 parameters *below* the factored head this ADR shipped with, and
119,952 below the head it carried yesterday. For an ADR whose stated thesis is
parameter efficiency on a 25-ply game, that is the outcome the Context section
was arguing for.

### The evidence

EXP-013, twelve seeds, 5×3-h2, 500 held-out positions, top-1 optimality after 400
PUCT simulations. The incumbent's twelve rows were **reused** from EXP-012 under
a reproduction guard that retrained its seed 0 after this change to
`az/network.py` and compared hit vectors element-wise: 500/500 identical,
training loss matching to 1e-9.

| arm | top-1 | final train loss |
|---|--:|--:|
| linear-conditioned | 73.2% | 2.4967 |
| **1×1 convolution** | **74.2%** | 2.5068 |

`V − L = +0.95 pts`, lower limit **−0.06%** against a **non-inferiority** margin
of **−1.70%**, one-sided at `t(11) = 1.796`.

**The margin was derived, not reused.** This ADR adopted a head conceding 3.3
points to the flat head under a 5.0-point tolerance, so 1.7 is what a
parameterisation may give back before the architecture leaves the tolerance the
adoption was taken under. The 3.3 carries [1.88, 4.75], so a conservative reader
derives 0.25 instead — and **the observed lower limit of −0.06% clears even
that**. This is the one decision in the EXP-011/012/013 sequence where the
conservative reading does not change the verdict.

### What this amendment does **not** establish

**The convolution is not better. It is not worse.** The test was one-sided by
design and it passed; the two-sided read is `+0.95 [−0.29, +2.19]` and contains
zero, with seven of twelve seeds favouring the convolution. Parsimony breaks the
tie, in a decision whose stated purpose is parameter efficiency. Nothing here
licenses "the convolution wins".

**Why it wins the tie is unknown, and the entry predicted the wrong place.** The
argument for the shared form was data efficiency: a rotation row for cell `c` in
the unshared head receives gradient only on plies where `c` is empty — about
**36.7%** of positions — while shared weights see every cell on every position.
That predicted the advantage would concentrate on the **odd** layers, where
EXP-012 measured the head effect at +8.1 against +2.8. It came out **flat across
parity**: +0.8 odd, +1.1 even. The prediction failed in the place it should have
been most visible, and nothing replaces it.

**So the mechanism is now doubly unexplained.** EXP-012 adopted conditioning
without establishing *why* conditioning helps — its validity precondition failed
unpassably. EXP-013 adopts the efficient form without establishing why the
efficient form suffices. **Two consecutive architecture decisions on this ADR
work for reasons neither experiment could show.** That is recorded here rather
than in a threats section because it qualifies the architecture, not one
measurement.

**The win is confounded with regularisation.** The two arms were deliberately not
parameter-matched — the 218× difference *is* the treatment — so "sharing is the
right inductive bias" and "43,290 parameters was too many" cannot be told apart.
The registration says so and this amendment inherits it.

**All of it is 5×3.** Weight sharing gets *more* attractive as cells multiply —
25 unshared maps against one shared one — so a convolutional win on 15 cells
understates the 25-cell case. That is the favourable direction, and it is an
argument, not a measurement.

### One diagnostic the entry did produce

The only non-solver evidence: the two heads played **200 games** head-to-head at
seed 0, seats alternating. The convolution took **106 (53.0%, [46.1%, 59.8%])**.
The interval crosses 50%, so it neither confirms nor contradicts — it is one seed
pair, and it is recorded at that weight.

### The initialisation had to be measured

The two heads' rotation logits are dot products over **480** features and **32**
respectively, and default initialisation bounds go as `1/sqrt(fan_in)`. Measured
over 500 positions and three seeds before training:

```
incumbent rotation-logit sd 0.04354, convolution 0.09021 -> scale 0.4826
```

**The convolution starts at 2.07× the incumbent's scale.** Left alone, the
comparison would have measured an initialisation difference and attributed it to
weight sharing. The output is scaled by a fixed measured constant, which leaves
the function class untouched. This is the same trap the pooled control hit with
its `sqrt(n_cells)` in EXP-012, and larger — the general lesson stands: **equal
parameter counts, equal shapes and equal function classes do not imply equal
initial functions.**

### A repair the adoption of (b) had left undone

Found while building EXP-013 and recorded here because it concerns whether the
architecture this ADR specifies can actually be *played*.

`NetworkEvaluator` computed priors through the factored `masked_log_policy`,
which expects a 6-wide rotation vector, and `az/player.py` and `az/selfplay.py`
both constructed it by name. **Self-play, the evaluator gate and the agents were
therefore still factored-only after the 2026-09-03 amendment moved the
architecture record.** The adoption changed the ADR and the training path and
left the play path behind; it raised rather than misbehaving quietly.

Repaired with a `ConditionedNetworkEvaluator` and an `evaluator_for(net, board)`
factory that both call sites use. Pinned by two tests: that every head type
receives a normalised prior over legal moves from one forward pass, and that the
evaluator's distribution is the one `conditioned_policy_loss` optimises — without
which a network could be trained on one distribution and played on another with
nothing raising.

**The architecture has still never run a self-play loop.** Everything measured in
EXP-011, EXP-012 and EXP-013 trains on exact solver labels. The pipeline this
head was chosen for has not yet trained on its own visit counts.

### Anti-circularity

Under [adr-004](adr-004-solver-approach.md) R1, this is the **third** Axis 2
architecture decision taken against Axis 1's exact ground truth on the 5×3, over
an adoptable choice set of **four** (factored, linear-conditioned,
convolutional-conditioned, flat). The refinement argument — that this only picks
between two implementations of a decision already taken — does not exempt it: R1
counts decisions, not families. H3's 5×3 evidence class carries the count.

The head-to-head match above is the only selection evidence in the sequence that
does not come from solver agreement, and it was weak enough to be a veto and
nothing more.

Pinned by `tests/test_az_train.py`:
`test_the_conv_rotation_normaliser_equals_brute_force`,
`test_the_conv_rows_are_the_convolution_at_that_cells_position` (the cell
ordering — a mismatch would raise nowhere and simply read rotation logits from
the wrong cell),
`test_the_conv_arm_shares_every_non_rotation_parameter_with_the_adopted_head`,
and `test_the_conv_rotation_head_is_198_parameters_on_every_board`.

## Related

- [adr-003](adr-003-piece-representation.md) — why no orientation planes
- [adr-004](adr-004-solver-approach.md) — the ground truth this is compared against
- [adr-008](adr-008-board-mirror-symmetry.md) — the mirror that does *not* fund augmentation
- [adr-010](adr-010-solver-correctness.md) — the verification the diagnostic in (4) reads from
- `docs/research.md` — H3, H5
- `notes/phase2-synthesis.md` — S1, S2, S3 (the readings behind the amendment)
