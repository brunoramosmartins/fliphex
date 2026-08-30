# Phase 3 — Axis 1: Exact Solver (implementation notes)

**Objective.** Produce *ground truth*: the exact game value of reduced FLIPHEX
variants, and exact values for the last `k` plies of the shipped 5×5 game. This
is the axis that can be wrong without crashing, so correctness apparatus is a
first-class deliverable, not an afterthought.

**Dates.** None — sequenced by dependency. Opened 2026-08-05.

**Governing decisions.** Read before writing code:

- [adr-004](../docs/adr/adr-004-solver-approach.md) — alpha-beta + TT + retrograde
  endgames, and its **Phase 3 amendment**: the 5×3 is the primary exact-solve target,
  the problem is storage-bound rather than search-bound, Zobrist needs **76**
  words, and rules **R1/R2/R3** govern what an Axis-1 run may be seeded by.
- [adr-010](../docs/adr/adr-010-solver-correctness.md) — the six verification
  mechanisms **V0–V6**. No Axis-1 number reaches `docs/research.md` before its
  V-checks pass.
- [adr-009](../docs/adr/adr-009-reduced-deck-policy.md) — reduced decks keep `P6`
  and `P3-y`, then fill by ascending arrow count, as amended by adr-011. Reduced
  boards are a computational device, not a physical variant.
- [adr-003](../docs/adr/adr-003-piece-representation.md) — the search state is
  colours + hand bitmasks + side to move. Never a tile identity or rotation.
- [adr-008](../docs/adr/adr-008-board-mirror-symmetry.md) — the Z/2 mirror is a
  *partial* game symmetry, valid only once both `P3-y` are placed. Folding it is
  legitimate inside the endgame databases and nowhere else.
- [adr-011](../docs/adr/adr-011-reduced-variant-parity.md) — reduced
  boards must have an **odd** cell count, P1's extra tile is the **joker**, and
  the **5×3 replaces the withdrawn 4×4** as the primary exact-solve target.
- [adr-012](../docs/adr/adr-012-endgame-database-storage.md) — no
  endgame database is materialised until the crossover is measured; if one is
  built the sweep is **pull, not push**, and the mirror is a check rather than an
  index transform.

**The shape of the problem, from Phase 2.** Depth is a constant (exactly `N`
plies on an `N`-cell board) and the layer profile is a **hump**, not a funnel —
the widest layer is the middle, so there is no convergence to exploit and
meeting in the middle is the worst available meeting point. Reference figures
from `scripts/layer_profile.py`, on the adr-011 hand rule (`a + 1` and `a`,
exactly exhausting):

| Board | cells | hands | bound | terminal layer |
|---|--:|---|--:|--:|
| 3×3 | 9 | 5 + 4 | 7.12 × 10⁵ | 512 |
| 5×3 | 15 | 8 + 7 | 1.75 × 10¹⁰ | 32,768 |
| 5×5 | 25 | 13 + 12 | 4.89 × 10¹⁷ | 33,554,432 |

The 3×3 at the *full* deck is 2.29 × 10⁹ with a terminal layer of **326,177,280**
— not 512. The two differ because the full-deck hands are never exhausted, so
the terminal layer keeps its hand dimension. That distinction is exactly what
adr-010 V0 is checking, and a solver that dropped the hand dimension at the
terminal layer would pass V0 against the wrong number.

Implementation order follows the dependency chain:
`reduced boards → transposition → minimax → ordering → 3×3 → 5×3 → endgame`.

## Reduced-variant framework

Parameterise the board by `(n_cols, cells_per_col)` and the deck by an
adr-009 composition, so that a "variant" is data rather than a code path. Every
solver artefact must carry its board size *and* its deck composition explicitly
— a bare "5×3 result" is ambiguous and adr-009 exists because of that.

## `solver/transposition.py` — Zobrist hashing

Direct-indexed: `self._slots[state.zobrist & self._mask]`, one entry per slot,
capacity a power of two. `verify=True` stores the full key alongside the value so
a collision is *detected* rather than silently believed — worth the memory on any
run that will be cited, given that the 64-bit birthday bound (~4.3 × 10⁹) sits
below the 5×3's own configuration count (1.75 × 10¹⁰).

`truncated` latches on any non-exhaustive store, which is what an artefact reads
instead of trusting a prose claim (adr-004 R1/R3).

**One property is load-bearing and was not obvious.** `store` keeps the deeper of
two entries on a slot conflict and drops the shallower **silently** — the refusal
increments no counter. So `replacements` is a *lower* bound on how many positions
the table failed to retain, not a measure of it. That matters wherever the table
is read as a record of what the search did rather than as a cache, which is
exactly what adr-010 V3 does. On the 3×3 at 2²⁴ slots, 3,300 replacements
accounted for only 3,300 of 4,390 lost positions; the other ~1,090 were refused
stores, and a decomposition that assumed otherwise came up exactly that short.

## `solver/minimax.py` — alpha-beta with TT

Alpha-beta returns **bounds**, not values, outside the initial window. TT
entries therefore need a flag (`exact` / `lower` / `upper`); storing a bound as
if it were exact is the defect that produces a plausible wrong answer rather
than a crash.

The solver **proves or raises**: no evaluation function, no depth limit, and a
`BudgetExceededError` that returns nothing partial. Depth is a constant on a
FLIPHEX board, so "search to the end" is the only mode there is.

On a two-valued objective every score sits on a window endpoint, so nothing is
ever flagged `EXACT`: a value is stored as `UPPER` of `LOSS` or `LOWER` of `WIN`,
and an extremal bound *is* the value. V3 reads the table on exactly that
invariant.

**`prune=False` therefore has to stop narrowing the window as well**, and
originally did not. Disabling only the cutoff let alpha reach `WIN` and the
remaining children be searched at `alpha == beta`; two plies down a node entered
with `alpha = WIN` and value `WIN` was flagged `UPPER` — an upper bound on the
maximum, which constrains nothing. V3 correctly refused to compare those and
reported `DISAGREE` with no actual value mismatch. Unpruned mode now searches
every node at `(LOSS, WIN)`; `prune=True` is untouched.

## `solver/packed_sweep.py` — the same sweep, 580× faster

`solver/retrograde.py` is the **reference**: written for legibility, it goes
through `GameState`/`legal_moves`/`apply_move`, and it is what EXP-001
cross-checks the forward searcher against. Measured on the 3×3 it runs at ~1,900
configurations/second, which puts the 5×3 at **108 days** and 10 GB. That is not
a target; the packed sweep is why.

Four moves, none of which changed the algorithm — output verified byte-identical
by checksum across two implementations and two interpreters:

1. **Stop building objects nobody reads.** In a sweep the index *is* the key, so
   the Zobrist hash the reference computes per configuration is pure overhead:
   nothing is ever looked up by hash. Four integers instead of a `GameState` —
   **21×**.
2. **Hoist to the coarsest loop the work is constant over.** The cell rank is
   computed once per cell-subset and reused across every colouring beneath it:
   `C(n, t)` times instead of `layer_size` times.
3. **Tabulate small-domain pure functions.** Binomials, the flip rule, and all
   8,192 spent-set ranks.
4. **Only then change the runtime.** With the hot loop allocation-free, PyPy gave
   another **8×** for nothing. The ordering is the least obvious lesson: reaching
   for PyPy first would have helped far less.

**The flip rule is not restated here** — `_flip_table` asks `Board.neighbour`
once, at construction. Hand-copying it would have destroyed the thing the
reference exists for: adr-010 V3 is only evidence while two implementations
*can* disagree. A test walks every (cell, tile, rotation) of a real board
asserting the table predicts exactly what `apply_move` does.

2-bit storage quarters memory (two resident 5×3 layers: 10.05 GB → 2.51 GB).
A micro-benchmark said the packed read costs 3.18× on CPython and 0.97× on PyPy;
end to end it cost **2%**, so the micro-benchmark overstated the real cost by
>150×. Written up in
[`tils/til-06-the-index-is-the-key.md`](../tils/til-06-the-index-is-the-key.md).

## Iterative deepening and move ordering

Ordering is an *agent* concern and a *proof* concern, and adr-004 splits them:
ordering that makes the agent strong is free to use anything; ordering inside a
run that will be cited as a proof is constrained by R1–R3.

## Rotations collapse dynamically, and nothing exploits it (2026-08-28)

`legal_moves` deduplicates rotations **statically** — once per tile, from its
rotation orbit (`P6` has 1, `P3-tri` 2, the opposite-pair tiles 3), giving 58
distinct `(tile, rotation)` pairs and 1,450 moves on ply 1. It never
deduplicates *per position*, and per position there is much more to collapse.

A tile's arrows only ever flip **occupied** neighbours — `apply_move` skips
`OFF_BOARD` and `EMPTY` targets. So two rotations of the same tile on the same
cell produce the same child whenever their arrow sets meet the occupied
neighbours identically, and on an empty neighbourhood *every* rotation does:
the tile lands inert, indistinguishable from the joker.

This does **not** extend across tiles. Spending a different tile leaves a
different hand, so the children differ however alike the board looks. Only
rotations collapse.

**Measured** by `scripts/measure_move_collapse.py` — random playouts, seed 11,
12 games on the 5×5 and 40 on the 5×3; children keyed by colours + hands + mover,
with `history` excluded because it is part of `GameState.__eq__` but not of the
position, and keying on it would report no collapse at all:

| ply | 5×5 generated | distinct | collapse |
|---|---|---|---|
| 0 | 1,450 | 325 | **4.46×** |
| 4 | 992 | 375 | 2.65× |
| 8 | 633 | 347 | 1.83× |
| 12 | 356 | 248 | 1.44× |
| 20 | 47 | 41 | 1.16× |
| whole game | 148,740 | 65,126 | **2.28×** |

325 is exactly 25 cells × 13 tiles: on an empty board the rotation is pure
redundancy. The collapse decays monotonically as the board fills, which is the
mechanism stated backwards — a fuller board gives the arrows more to bite on.

**Where this would pay, and where it would not.**

*Not the sweep, not now.* The retrograde inner loop is the ideal place —
`_layer_configurations` holds `occupied` fixed across the whole inner nest
(≈1.0 M configurations per `filled` subset at `t = 9`), so the distinct effective
masks per (cell, tile) could be precomputed once per subset and amortised to
nothing. Layers 7 and 9 are 83% of h2's sweep and collapse 1.58× and 1.32×,
projecting to **~8 h off 34 h, near 25%**. Two caveats: the collapse is measured
on *reachable* positions and the sweep enumerates the configuration space, most
of which is unreachable; and the saving only lands on positions the sweep must
enumerate exhaustively, which is the LOSS ones — the same set the parity finding
identifies as the expensive half, so the direction is right and the magnitude is
an estimate.

None of it has a consumer. The 5×3 is solved twice over, the h1 re-run exists
specifically to reproduce `ab2620e1707f983f…` and be comparable to h2 — changing
the sweep would forfeit exactly that — and adr-012 already ruled out a 5×5
database, where 4.887 × 10¹⁷ states make a 1.3× irrelevant.

*Not the forward searcher, much.* The transposition table already absorbs the
duplicates: a repeated child hits the table and returns. What is wasted is
`apply_move` plus a probe, not a subtree — a constant factor, and concentrated
in sparse positions, which are the rare ones. Possibly a real secondary effect
on move ordering (a node can try four copies of the same losing child before
reaching a winning one), unmeasured.

***Axis 2, where it is not a constant factor at all.*** adr-005 gives the policy
head 1,950 factored logits over cell × tile × rotation, and the decision journal
already flags it as Phase 0's least-evidenced decision. At the root, 4.46 of
every 5 of those actions are aliases: the network is asked to spread probability
across 1,450 actions leading to 325 positions, and MCTS — unless it deduplicates
children — expands them as separate nodes and **splits the visit counts of
identical positions**. That degrades the search itself, not just its speed, and
it is worst exactly where quality matters most, near the root. Carry into
Phase 4 as a design input, not an optimisation.

## 3×3 — exhaustive solve (EXP-001)

Correctness fixture, not a strategy microcosm — and the adr-010 V3 artefact: the
same variant solved twice, forward and retrograde, agreeing on every position.

**P1 wins with perfect play in both arms.** 711,963 configurations enumerated,
matching `scripts/layer_profile.py` layer by layer with no tolerance.

| | h1 | h2 |
|---|---|---|
| V0 terminal layer | 512 ✓ | 512 ✓ |
| V1 per-layer counts | exact ✓ | exact ✓ |
| V3 compared, unpruned, 2²⁴ slots | 679,202 (95.4%) | 680,709 (95.6%) |
| V5 checksum | `9a16d65a…` | `307e99b8…` |

**This is not an H1 or H2 verdict**, and the pre-registered power caveat is the
reason: agreement between two binary root values is at most 1 bit against a 50%
prior, and 8 of 9 cells here are boundary cells, so many ordinary placements flip
nothing and act as joker substitutes.

The V3 coverage figure took three runs and two instrument fixes to become
meaningful — 3.4% → 46.2% → 84.9% → 95.4% — and every intermediate number was
misread as a fact about the game before it was understood as a fact about the
instrument. That story is the substance of this phase's Failed Attempts.

## 5×3 — the strategically meaningful solve (EXP-002)

Launched 2026-08-07, h1 arm, PyPy, 2 bits/entry, projected 13 h at 2.51 GB peak.
**Finished 2026-08-09: `P1` wins, all six gates pass, sweep 32.38 h at 150,192
cfg/s, ~52 h wall-clock, 7.5 GB high-water.** The projection was wrong by 4× and
the peak by 3×.

Verification rides in an **observer** called as each layer completes, while that
layer is still resident: the widened tables would be 17.5 GB, so V4 and V6 are
only affordable if they read what they need and let the layer go. The database
never exists all at once.

This is the first board where **V6 applies at all.** The withdrawn 4×4's
automorphism was a 180° rotation, and a rotation maps a tile's pattern into its
own orbit, so no tile can break it. The 5×3 has the shipped 5×5's own Z/2 mirror,
which the chiral `P3-y` *does* break while either copy is still in hand — so V6
samples only configurations where both are spent, and reports how many it
rejected.

The h1 arm ran with no per-layer output at all, which on a job measured in hours
makes a slow sweep indistinguishable from a hung one. Fixed for h2; the change is
output-only, so the arms stay comparable, and it is recorded in the registry
because the two arms now run on different commits.

### `solver/checkpoint.py` — resume, after losing 20.8 h twice over

The h2 arm died inside `t = 7` when the machine powered off, with layers 15
through 8 computed and nowhere to put them. A retrograde sweep resolves high `t`
first, so a stall leaves the root untouched — the registry's own rule is that
such a run carries *zero* information about the value, which makes the loss
total rather than partial.

What makes resume cheap is the shape of the sweep: layer `t` depends on layer
`t + 1` and nothing else, so **one array on disk is a complete resume point**.
The 5×3 ladder is 4.4 GB against 915 GB free.

The design question worth recording is the digest. adr-010 V5 is a single running
SHA-256 fed one layer at a time, and `hashlib` objects cannot be serialised. The
cheap fix — a digest per layer, combined at the end — would have worked and would
have quietly redefined what V5 measures between the h1 and h2 arms. Instead every
layer is kept and a resumed run re-feeds them in the original order, so the
checksum is byte-identical to the uninterrupted one. `tests/test_checkpoint.py`
pins that, and pins that the RNG state travels so the V4/V6 samples stay the ones
the seed selects.

Two smaller decisions, both defensive: the layer file is written before the
manifest that names it, so a crash between them loses the layer rather than
resuming from a torn one; and a resumed run refuses to print `cfg/s` at all,
because the earlier session's time died with its process and the two pieces are
not addable.

### Why the 13 h projection missed by 4×

Worth writing down, because every one of the three errors was a modelling
mistake, not a surprise from the machine.

**The estimate was made in configurations.** Cost per configuration is not
constant. The inner loop exits as soon as it finds a losing child, so a *win*
node stops after a couple of probes while a *loss* node examines all `b(t)` of
them — and `b(t)` runs from 26 at `t = 12` to 155 at `t = 7`. The loss nodes set
the price and the price rises as the sweep descends.

**A mid-run calibration then pointed the other way, and it was sampled from two
layers that happen to disagree about the thing being measured.** Timing the top
layers gave 1.678 µs/cfg at `t = 13` and 1.619 at `t = 12` — flat despite `b(t)`
nearly tripling, which looks like proof that cost does not track branching. The
sweep's true average was **6.66 µs/cfg, 4.1× the calibrated figure.**

At the time I explained the flatness by cache: both points probe a layer that
fits in this machine's 9 MiB L3 (0.5 MB and 12 MB), so enumeration overhead
swamps the branch term. That was wrong, or at least unsupported — see below. The
real reason those two points look flat is that `t = 13` and `t = 12` have
**opposite parity**, and parity is what governs the cost.

**The term I was missing entirely.** Cost is not `A + C·b(t)`. It is

    cost(t) ≈ 0.2 + 0.27 · b(t) · P(loss | t)   µs per configuration

Because the inner loop exits at the first losing child, a *loss* node pays the
full `b(t)` and a *win* node pays almost nothing. On a board P1 wins, `P(loss)`
is near zero when P1 is to move and near one when P2 is — so the cost alternates
with the parity of `t`, by **two orders of magnitude between adjacent layers**:
0.241 µs at `t = 4` against 39.9 µs at `t = 3`. Sampling any two adjacent layers,
as the calibration did, samples one of each and averages away the only variable
that matters. Measured in `experiments/registry.md`, EXP-002, finding of
2026-08-13.

**And the cache explanation is withdrawn as unproven.** The `t = 12` → `t = 11`
jump is simultaneously a cache boundary, a parity flip, and a `b(t)` rise from 27
to 39. `b·P(loss)` goes 2.42 → 18.08 there — a 7.5× rise against a 4.2× rise in
cost, so parity over-explains the jump on its own and leaves nothing for cache to
account for. Not disproved; unsupported. Separating them needs same-parity
comparisons at controlled `b(t)`, which no measurement here provides.

**V4 was never in the model at all,** and it cost ~20 h, more than the entire
original projection. It re-derives sampled positions by forward search, and
positions sampled from low layers have enormous subtrees; 217 of 561 samples hit
the 2,000,000-node budget.

The calibration also had a cost I did not anticipate before starting it: it
competes with the sweep for the same machine, so measuring the run slowed the
run. It was killed for that reason.

**The lid closures turned out not to matter, and I over-corrected for them.**
When the h1 log showed layers that looked impossible — `t = 8` faster than a
small cache-resident layer — I attributed it to `CLOCK_MONOTONIC` being re-based
across WSL2 suspend, and recorded in the registry that those timings were corrupt
and only the layer *order* was evidence. The restarted h2 arm, on a machine that
never suspended, reproduced the same shape and agreed with h1 layer for layer:
`t = 9` within **0.6%**, `t = 8` within 1.6%. The pattern was the parity effect
all along. A re-based clock does not reproduce to 0.6% across two runs with
different decks.

The lesson is narrower than "don't trust the clock": I had a real anomaly, a real
recent event to blame it on, and I stopped there instead of asking what would
reproduce and what would not. **The h1 timings are usable, and the retraction is
recorded next to the original claim in the registry rather than replacing it.**

Two smaller caveats that do stand: the wall-clock figures are inflated by
low-power throttling (`perf_counter` does not advance across a true suspend but
does advance while the CPU is down-clocked), and h1's V4 phase is not in any of
the per-layer numbers.

The transferable rule: **do not report a point estimate from a model validated
only outside the regime that dominates the cost.** One data point in the cheap
regime admitted totals from 7.9 h to 21.8 h, and the answer was 32.4 h. A range,
or a refusal, was the honest output.

### The PV audit's four lost runs — a table that never could have fit

Between 2026-08-17 and 2026-08-23 the 5×3 PV audit was launched four times and
killed four times. It is worth recording in full because none of the four was a
bug in the solver, all four were losses in the *instrument*, and the root cause
was a number nobody had measured.

**What was actually wrong.** The transposition table stored a
`list[Entry | None]` of namedtuples, each holding a `StateKey` holding a colours
tuple. That is **331 bytes per filled entry**, measured afterwards. So the
`--tt-bits 26` everyone had been using needs **21.2 GiB when full**, on a VM with
15.5 GiB. The table was never *capable* of filling. That was not bad luck; it was
arithmetic, and the arithmetic had never been done.

**Why it took four runs to see it.** The failure mode is close to the worst
available:

- The slot list allocates as pointers and materialises only as entries are
  written, so an impossible table starts fine and stays fine for hours.
- It then dies to the kernel's OOM killer, which writes no checkpoint and leaves
  no traceback — from the log the run simply stops mid-sentence.
- The first proof, ply 0, *succeeded* at 2²⁶ — because in 21 hours it never
  filled the table, topping out near 12.9 GiB. Success at the size that cannot
  work is what made the size look validated.

**The four runs, and what each one actually cost.**

| when | what happened | cost |
|---|---|---|
| 08-17 | ran 68.8 h and printed nothing; no way to tell progress from death | 68.8 h, no output |
| 08-21 | proved ply 0, then ply 2's table was allocated on top of ply 1's | 21 h kept, run lost |
| 08-23 | `--tt-bits 27` (42.4 GiB when full) OOM-killed at 504M nodes | 4.8 h CPU |
| 08-23 | `--tt-bits 26`, guard fired but could not free memory, cascaded | 374M nodes |

**Three compounding defects, all in the harness.**

1. *Silence.* A search that prints nothing cannot be distinguished from a dead
   one. Fixed by a `Heartbeat` thread reporting nodes, rate, resident size and
   suspended time — and it must read the counter *through* the solver, because
   `solve()` rebinds `solver.stats`.
2. *Double allocation.* `fresh = TranspositionTable(...)` evaluates the
   right-hand side while `fresh` still names the previous position's table, so
   part 1 held two at once and doubled the peak. The old table is now released
   and collected first.
3. *A guard that could not act.* An RSS ceiling that aborts the *position* does
   not give the memory back, so every later position began already over the
   line and died in seconds — plies 2 through 7 were marked `unproven` in
   moments and the process was OOM-killed regardless. Past the ceiling the only
   useful action is to end the run.

**The fix that removes the class, not the instance.** `Entry` objects are gone;
slots are five parallel `array` buffers of fixed-width integers — **28 bytes**
verified, 12 unverified, an 11.8× reduction. The same 2²⁶ table is now 1.75 GiB
and 2²⁸ fits in 7.0 GiB, four times the entries that proved ply 0.

Verification is **not** weakened to buy this, which mattered: with 1.75 × 10¹⁰
states against a 2³² birthday bound, Zobrist collisions on this board are
expected rather than hypothetical. The whole `StateKey` is a bounded bit-field —
`n_cells × 2` bits of colour, two 13-bit hands, one bit of side to move, 55 bits
on the 5×3 and 77 on the 5×5 — so it packs losslessly into two 63-bit words and
compares exactly. A test pins the *iff*: two states pack alike if and only if
their keys are equal.

Because the buffers are now allocated up front, resident size reaches its
ceiling in **minutes rather than hours**. An oversized table reveals itself
immediately instead of at hour four. And `--tt-bits` is checked against
`max_capacity_for()` before any search starts, so an impossible configuration is
refused in the first second, naming the size that would fit.

**The transferable rule.** *A resource ceiling that has never been measured is
not a configuration choice, it is an assumption.* Four runs died to a per-entry
cost that took two minutes to measure and that nobody had measured, while
attention went to node budgets and table sizes — the dials in front of us. The
second rule is narrower and cost the fourth run on its own: **a guard must be
able to act on what it detects.** Detecting an over-ceiling condition it cannot
remedy converted a slow failure into a fast cascade, which is strictly worse
than no guard at all, because it also destroyed the run's remaining work.

A related near-miss, worth recording because it is the same shape: the run's
suspended-time counter is *cumulative*, and reading one sample of it as a
per-interval figure produced a confident claim that the VM was suspended 72% of
the time and that a 4 h job would take 34 h. Five more samples showed the number
had never grown past its first step. **One sample of a cumulative counter is not
a rate.**

## `solver/retrograde.py` — endgame on 5×5 (EXP-003)

The roadmap's `k ≤ 5` target is ~1.2 × 10¹⁵ positions, ~150 TB at one bit. Per
adr-012 the first question is not the format but whether storing beats searching
at all: the subtree below a `k = 5` node is order 10⁵–10⁷ nodes. The terminal
layer (4 MB) is built regardless — it is adr-010 V0's base case.

**Measured: `k* > 8`, so no database is built.** Median nodes to prove one
position: `k = 5` → **480**, `k = 8` → **806,474**. Searching wins at every
registered `k`, by margins that make the storage question moot. The
pre-registered prediction `k* ≥ 6` held. → adr-012 **Option B**.

That result also killed H3's endgame-database member and forced a re-scope: the
member H3 loses and the member it needs — exact ground truth on the *shipped*
game — are not the same thing, so EXP-006 replaces it with 500 5×5 positions at
`k ≤ 8` solved on demand, seeded differently from EXP-003 to avoid circularity.

**`k*` was the wrong shape, and the Takizawa reading is what exposed it.**
EXP-003 looked for
one crossover. The Othello solve has *two* cuts with different justifications —
enumerability above, solvability below — and EXP-003 measured only the second.
The first needs no experiment; it is `scripts/layer_profile.py`. On the 5×5, by
empty cells:

| `k` | layer | at 2 bits |
|---:|---:|---:|
| 1 | 5,452,595,200 | **1.4 GB** |
| 2 | 392,586,854,400 | 98 GB |
| 3 | 9,029,497,651,200 | 2.3 TB |
| 8 | 50,173,893,918,720,000 | **12.5 PB** |

Enumerable at `k ≤ 1` in memory; solvable on demand at `k > 8`. The two cuts do
not meet, so there is **no crossover region at all** — across `k = 3…8` nothing
is enumerable and everything is solvable in under a second. adr-012 Option B is
closed by arithmetic, not just by EXP-003's sampled medians.

The sharper consequence is what the hump implies for a 5×5 attempt.
Layers are small at *both* ends — the opening is enumerable to `t ≤ 5` (8.0 GB),
the endgame to `k ≤ 2` — and what neither end reaches is `t = 6…16`, eleven
layers between 19 and 9 empty cells, peaking at 1.09 × 10¹⁷ configurations at
`t = 15`. That interval is exactly where Takizawa's Algorithm 1 does its work,
and it is the part FLIPHEX has no instrument for: bridging it needs an evaluator
whose predictions are almost always right. Recorded as a note under EXP-003 in
the registry, not as an amendment — the experiment is complete and its quantity
is not being redefined.

## Reachability — EXP-005 and EXP-007

adr-012 decision 7 allows one source of don't-cares: a configuration with no
legal predecessor. `solver/reachable.py` counts them **forward** — walk layer
`t-1`, generate every legal move, mark the successor's bit — rather than by
inverting the flip rule, which would have been a second hand-written statement of
it. One bit per configuration, one layer resident.

**EXP-005's quantity turned out to be a counting identity.** Both 3×3 arms
returned identical orphan counts at every layer despite different decks, which is
not a coincidence:

> `orphans(t) = layer_size(t) / 2^t`, exactly.

A configuration has no legal predecessor precisely when *every* occupied cell
carries the colour of the player who did **not** just move — the last-placed cell
always shows its placer's colour, since a tile's own arrows never point at the
cell it occupies. That is one colouring out of `2^t`. It does not depend on the
arrow patterns, which is why the decks make no difference, and it generalises
adr-010 V1's `t = 1` calibration note to every layer. The 5×3 answer follows
without a run: **0.3428%**.

So the registered measurement is an artefact of the index, not a fact about
FLIPHEX, and 0.34% of don't-cares informs no design. The quantity adr-012
actually needs is the **transitive closure** — configurations no *game* reaches,
which is strictly smaller than the one-step-reachable set. Registered as
**EXP-007**, a new ID rather than an amendment, because the two yields can fall
on opposite sides of the same 20% threshold and redefining a live experiment's
measured quantity is the anti-pattern adr-010 was already amended once to avoid.

The closure does depend on the deck, and the arms disagree: **3.9131%** (h1)
against **3.8866%** (h2) on the 3×3. That disagreement is the signature that
distinguishes the two instruments.

## Verification — adr-010 V0–V6

V0 terminal layer in closed form · V1 **exact** per-layer equality against
`scripts/layer_profile.py` — a genuine `perft`, no tolerance · V2 the no-draw
invariant asserted totally · V3 3×3 solved twice by different methods · V4
random-sample re-derivation on 5×3 · V5 checksums · V6 mirror consistency,
against an **unfolded** sample.

V1 is **not** the reachability measurement. The adr-010 Phase 3 amendment split
them: the closed-form formula counts configurations, so a correct
reachable-closure enumerator disagrees with it by exactly 2× at layer 1. The gap
is measured by `EXP-005`, before any don't-care filling.

**Two of the six were not runnable as written, and both needed amendments.**

*V1* was specified as both a gate that can fail *and* a measurement of an
unknown. Those are incompatible: under the original wording a correct run was
indistinguishable from a failed one, and the only resolution would have been to
inspect the gap and decide — the precise anti-pattern pre-registration exists to
prevent. Restated as exact per-layer equality, a genuine `perft`.

*V3* required agreement on "every position", which no forward search can meet: a
configuration with no legal predecessor is never a node in any game tree, so
there is no forward value in existence to compare. Restated 2026-08-07 as **every
position the search reaches**, unpruned, with the table sized so retention is not
the binding constraint — and reported as **three numbers** (compared, unreachable
floor, table occupancy) so a shortfall is *attributable* rather than merely
disclosed.

That is not the weakening that was on the table. The option recorded on
2026-08-05 was to accept whatever pruning left, which was 3.4%. The amendment
mandates the unpruned search, mandates a table that is not the constraint, and
requires the unreachable floor to come from a separate experiment that can
falsify it. Final figure: **679,202 of 684,103 reachable = 99.28%**, with the
residue accounting for itself exactly — 511 terminal configurations the search
never stores, plus 4,390 positions that lost a slot conflict.

### The threat none of the six covers

All six levels assume the machine computed what the code says. Takizawa §3.7
records that every CPU in that cluster had ECC, and §5 defends the choice
explicitly against this exact objection. EXP-002 cannot make the same claim, and
until that reading nothing in this note said so.

The 5×3 sweep is a **single** PyPy process holding 4.2 GB resident (7.5 GB
high-water) for **32.4 h of sweep plus ~20 h of V4**, writing 17,506,580,337
packed 2-bit values, on consumer WSL hardware with
**no ECC**. One flipped bit is a wrong value for one configuration, propagated to
every ancestor that reads it, with no crash and no counter — a plausible answer,
which is the whole failure mode adr-010 exists for.

The ladder is blind to it. V1 counts entries, not values. V2 is total but only on
terminals. V3 is 3×3-scale. V4 and V6 do read values, at **40 sampled positions
per layer** against layers of up to 5.0 × 10⁹ — the chance of sampling a flipped
entry is nil. V0–V6 are strong against *logic* errors, which repeat and therefore
show up in samples, and have no coverage against *substrate* errors, which do
not.

The mitigation exists and is cheap to state: `PackedSweep` already keeps
`checks.digest`, and the sweep is deterministic, so **re-running an arm and
comparing digests is a real replay check**. Priced here originally at "~13 hours
per arm" — that was a projection made before any arm finished, and h1 came in at
**32.4 h of sweep, ~52 h wall-clock**. The replay is a multi-day commitment.

It is not spent on the current run. The exposure is disclosed instead, with the
trigger recorded in the adr-010 amendment of 2026-08-07: if the 5×3 value is cited
as an H1 or H2 verdict, the digest replay runs first. Deliberately **not** a new
`V7` — a mandatory level that gets skipped every time is worse than an honest
gap, because it turns a limitation into a false claim of coverage.

## H1 / H2 partial verdicts

Partial: on reduced variants only, with the evidence class stated per
`docs/research.md` (`exact`, qualified by verification status).

**Not written yet, and deliberately.** The Verdicts table in `docs/research.md`
stays empty until Phase 5 — that is a working agreement, not an oversight. Two
things must land first: EXP-002 (the 5×3 is the board that carries the claim; 9
cells cannot) and the criticality measure, since H2 is reported from the fraction
of solved positions whose value changes when P1's extra tile is swapped, **not**
from the two arms agreeing on a root value.

When the row is written it carries its evidence class qualified by adr-010
status, e.g. *"supported (exact, single implementation, V0–V6 passed, not
independently reimplemented)"*.

**What is now in hand, and what it is not.** Both 5×3 arms are solved — h1 on
2026-08-09, h2 on 2026-08-13 — and **`P1` wins both**, with V0–V6 passing and V1
exact on 17,506,580,337 configurations each. Three things still separate that
from an H1 or H2 input:

1. **The registered principal-variation audit had not run on either arm.**
   EXP-002's decision rule requires it and says why it is not redundant with V4 —
   V4 bounds the error *rate* in the database, the PV audit targets the *number
   reported*. `scripts/exp002_pv_audit.py` now exists and does two things: walks
   the PV out of the sweep's own layer files and re-derives every position on it
   by forward search, then re-derives the root under **every distinct first
   move**, so a sweep that got one opening wrong cannot hide behind the opening
   the PV happens to take.
2. **Both arms agreeing on `P1` is not H2.** H2 is reported from the criticality
   measure — the fraction of positions whose value *changes* when P1's extra tile
   is swapped — and that needs both databases side by side. Only h2's layers
   survive; h1 predates `solver/checkpoint.py`. Re-running h1 with
   `--checkpoint` is the move that unlocks it, and it simultaneously discharges
   the adr-010 digest replay and gives h1 its first clean wall-clock.
3. **adr-009 stands**: a reduced-board result transfers to the shipped 5×5 as
   evidence, never as proof. The runner prints this line itself, and it belongs
   next to the number wherever the number goes.

The audit is only possible because the layers survive the sweep. That was built
for crash resume and has now paid for itself twice — the parity finding above
came out of the same files.

## Experiment registration

Every run in this phase has an `EXP-NNN` row in
[`experiments/registry.md`](../experiments/registry.md) **before** it starts.

## TIL drafts

TIL #2 — MCTS in perfect-information games. TIL #3 — alpha-beta from first
principles. **TIL #6 — the index is the key** is drafted:
[`tils/til-06-the-index-is-the-key.md`](../tils/til-06-the-index-is-the-key.md),
on what an exhaustive simulation is really paying for, with the identification
questions and the trade-offs.

## Lessons Learned

I learned that in an exact solver, correctness is not a property of the algorithm alone. It depends on the entire experimental apparatus: state representation, instrumentation, resource accounting, independent implementations, and verification. The strongest evidence I obtained came from making it possible for two different implementations to disagree and then showing that they did not.

I learned to measure the quantity that actually drives a decision instead of inferring it from secondary effects. Runtime, compression ratio, memory usage, and criticality all led me toward explanations that turned out to be incomplete or wrong. In one case, directly counting the values took 70 seconds and resolved a question that several indirect measurements had failed to answer.

I learned that performance models must be validated in the regime that dominates the computation. My initial runtime estimate for the 5×3 sweep was off by roughly 4× because I modeled cost per configuration while ignoring the strong dependence on branching and node value. The decisive variable was the probability of encountering a loss node, which caused adjacent layers to differ by orders of magnitude in cost.

I learned that a compute budget has to cover the verification, not only the computation being verified. My thirteen-hour projection for the 5×3 sweep modelled the sweep and nothing else. The V4 re-derivation was not in the model at all, and it cost roughly twenty hours on its own — more than the entire original estimate for the whole run. The sweep produces a number and the verification is what makes that number citable, so leaving it out was not an inaccuracy in the estimate but a missing term in it. I now treat "how long to compute it" and "how long to establish it is right" as two line items, because on this phase the second was the larger one.

I learned to treat resource limits as part of the algorithm rather than as deployment details. A transposition table configuration is not meaningful until its actual memory footprint has been measured. Four failed runs ultimately traced back to a per-entry cost that took minutes to measure. After replacing Python objects with fixed-width buffers, the same table became practical and oversized configurations could be rejected before the search started.

I learned that instrumentation can fail in ways that produce plausible scientific results. Several measurements in this phase initially looked like facts about FLIPHEX when they were actually facts about the instrument. A guard that cannot act on the condition it detects, a cumulative counter interpreted as a rate, or a verification metric with undefined coverage can all produce misleading conclusions without crashing.

I learned that independent verification must remain genuinely independent. Reimplementing the same rule twice would only reproduce the same mistake. The reference retrograde solver therefore remained deliberately different from the optimized packed implementation, allowing the two approaches to cross-check each other.

I also learned to distinguish optimization from useful progress. Removing object allocation, hoisting invariant work, and tabulating small pure functions produced large gains before changing the runtime. Only after the hot loop was already allocation-free did PyPy provide its additional 8× improvement. Optimizing the wrong layer of the system would have produced much less value.

Finally, I learned that knowing when not to continue is part of solving the problem. The 5×5 cannot be strongly solved with the current exhaustive approach: its state space and branching factor make the required computation and storage impractical. Rather than continuing to optimize a dead end, I now have a clear boundary for the exact-search approach and a concrete motivation for Phase 4: use a learned evaluator and move ordering to reduce the search problem itself.

## Failed Attempts

I made several incorrect assumptions during this phase, and some of them cost substantial computation.

The largest one cost nothing, and only because of when it was caught. I planned the whole phase around the 4×4 as the primary exact-solve target, and the 4×4 was never a legal FLIPHEX board: sixteen cells is an even count, so the two colours can tie, and the rules define no tie-break. By the time this surfaced the board had already shaped the roadmap, adr-004 and my own sequencing — but it surfaced while red-teaming the registry entry, before a single configuration had been enumerated. Pre-registration paid for itself here before it had produced any experimental result at all, which is not the argument I would have made for it in advance.

I repeatedly inferred causes from indirect evidence instead of measuring the underlying quantity. I initially attributed unexpected sweep timings to cache behavior and later to WSL clock behavior; both explanations were unsupported. The actual pattern was caused by the interaction between parity, branching factor, and the probability of encountering loss nodes.

I underestimated the importance of memory accounting. I recommended transposition-table sizes based on observed RSS while the table was still filling. This led to multiple OOM failures, including a configuration that required 42.4 GiB on a 15 GiB machine. The underlying per-entry cost was only measured after the failed runs.

I also designed safeguards that were unable to recover from the conditions they detected. An RSS guard could mark a position as unproven, but it could not release the memory responsible for the violation. Instead of protecting the experiment, it caused a cascade of failures. I subsequently changed the design so impossible configurations are rejected before the search begins.

Several verification measurements were initially misinterpreted. I treated part of the V3 residue as unreachable states when most of it was actually transposition-table retention. I also initially computed reachability using a one-step criterion rather than transitive closure, producing the wrong estimate. These mistakes reinforced the need to define exactly what each metric measures before interpreting it.

I introduced measurement code that was itself capable of distorting the experiment. One exploratory probe stored full GameState objects in a set, but included move history in equality, so it deduplicated paths rather than positions and consumed 12.5 GiB of memory. The measurement infrastructure had become part of the problem.

I also made a premature refactoring based on a linter recommendation. A seemingly harmless change from a lazy branch to an eager expression broke ten tests. This reinforced that even mechanical code-quality changes must be validated against behavioral semantics.

I also registered a verification I could not afford. The principal-variation audit's second part re-derives the root value under each distinct first move by direct forward search, which is a full subgame proof per opening. Thirty of the five hundred and forty openings consumed 9.7 hours of CPU, and the marginal cost was climbing steeply enough — ten openings in twenty minutes, then the next ten in 8.3 hours — that the remainder extrapolated past four hundred hours. I stopped it at opening 34 and replaced it with a layer-to-layer recurrence check that covers more positions for a small fraction of the cost. Registering a gate is not the same as establishing that the gate fits the budget, and I had never measured the difference.

Most importantly, I learned that a successful run does not necessarily validate a configuration. A table size that successfully solved the first ply had never reached its actual capacity, so its apparent success said nothing about whether the configuration could survive a full search. The experiment was only meaningful once the resource envelope itself had been measured.