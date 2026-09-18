# Phase 4 — Axis 2: AlphaZero-Style Self-Play (network design log)

**Objective.** Build an AlphaZero-style pipeline on the **full 5×5** game —
small policy/value network, PUCT MCTS over real states, self-play generation, a
training loop — and produce a learned agent whose behaviour can be compared
against Axis 1's exact ground truth wherever that ground truth reaches.

**Dates.** None — sequenced by dependency. Opened 2026-08-30.

**Governing decisions.** Read before writing code:

- [adr-005](../docs/adr/adr-005-alphazero-scope-and-network.md) — the network,
  the factored head, the input encoding, and **both amendments**. The Phase 2
  amendment adds the evaluator gate (400 games at 55%), the plain-UCT floor, and
  the rule that checkpoint selection may not read Axis 1. The Phase 3 amendment
  makes **transposition-aware child expansion mandatory** and corrects the
  opening figure from 1450 actions to **325 distinct positions**.
- [adr-001](../docs/adr/adr-001-perfect-information-scope.md) — perfect
  information. No determinization, no information sets.
- [adr-003](../docs/adr/adr-003-piece-representation.md) — placed tiles are
  inert, so there are **no orientation planes** in the input.
- [adr-006](../docs/adr/adr-006-no-chain-reaction.md) — flips never chain. With
  adr-003 this is *why* the action space aliases.
- [adr-008](../docs/adr/adr-008-board-mirror-symmetry.md) — the Z/2 mirror is
  partial and does **not** fund data augmentation (≈1.31× available, rejected).
- [adr-004](../docs/adr/adr-004-solver-approach.md) R1 — the mirror-image rule:
  neither axis may select or terminate the other along the dimension on which
  they are later compared.

**What Phase 4 inherits as measurement, not assumption.**

| Quantity | Value | Source |
|---|--:|---|
| Distinct opening positions | 325 | `scripts/measure_move_collapse.py` |
| Root action aliasing | 4.46× | same |
| Whole-game aliasing | 2.28× | same |
| Exact value, 5×3 both arms | P1 wins | EXP-002 |
| Exact agent vs heuristic, 5×5 | 61.0% [56.7, 65.2] | EXP-008 |
| Heuristic vs heuristic, first seat | 40.0% | EXP-008 control |

The last two are the bar the learned agent has to clear and the baseline it has
to clear it *against*, and neither may be quoted without the caveat recorded in
the registry.

**Open risk carried in.** [R13](../docs/risk-register.md) at score 9 — the
highest in the register — is a Phase 4 risk in its entirety. **Dropped to 6 on
2026-08-31** when EXP-010 measured the mitigation; what remains is that it has
never been seen in a real 5×5 self-play loop.

## Environment and hardware

**Measured 2026-08-30, on the machine the phase opened on.**

| | |
|---|---|
| Host GPU | NVIDIA GeForce GTX 1050 Ti, 4 GB (+ Intel UHD 630) |
| Windows driver | 27.21.14.6231 (≈ 462.31, 2021) |
| CUDA in WSL2 | **unavailable** — no `nvidia-smi`, no `libcuda` under `/usr/lib/wsl/lib` |
| CPU / RAM / disk | 12 logical cores, 15 GB, 907 GB free |
| Interpreter | CPython 3.12.3, torch 2.13.0+**cpu**, 6 threads |

CUDA passthrough needs a Windows driver of at least the 470 series; 462 predates
WSL2 GPU support, which is why only the D3D12 shims are present. The GPU is
physically there and unreachable.

**The tower, measured before it is written.** A throwaway 29-plane / 64-filter /
4-block probe with the factored head:

| Batch | ms / forward | positions / s |
|--:|--:|--:|
| 1 | 0.90 | 1,112 |
| 8 | 2.45 | 3,267 |
| 64 | 7.92 | 8,081 |
| 256 | 33.91 | 7,549 |

One training step at batch 256: **77.6 ms**.

**The engine, on the same interpreter:**

| | |
|---|---|
| `legal_moves` at the root | **1.188 ms** (1,450 moves) |
| One random playout | 10.0 ms (25 plies) |
| Throughput | **2,499 plies/s** |

**The reading.** Generating a leaf's move list costs *more* than a forward pass
through the network at batch 1 — 1.188 ms against 0.90 ms — and with any
batching at all the network is roughly three times cheaper per simulation than
the engine that feeds it. Axis 2's bottleneck is `fliphex.moves` in CPython, not
tensor arithmetic.

Two consequences follow, and the second is the uncomfortable one.

The missing CUDA driver costs far less than it appears to. A 0.33 M-parameter
network over 5×5 inputs cannot saturate a 1050 Ti; the batches are small, the
transfers dominate, and the plausible gain is a small multiple on the *cheaper*
of the two costs. Updating the Windows driver is worth doing and is not on the
critical path.

The critical path is the engine. Phase 3 solved the same problem by moving to
PyPy, which is not available here: PyPy does not run torch. So the options are a
faster engine in CPython (bitboards, vectorised move generation), a two-process
split with self-play in PyPy and inference served from CPython, or parallelising
across cores — self-play is embarrassingly parallel.

**That last option was first written here as "roughly an order of magnitude for
free", which was wrong and is corrected below.** The phrase read a structural
property — games are independent — as a statement about scale, and took the
scale from 12 *logical* cores. The machine has **6 physical** cores; hyper-
threading returns very little on this workload. Measured speedup is **4.31×**,
not 10×.

## What one self-play game costs

**Measured 2026-08-31, 5×5, `ExpansionMode.POSITION`, 400 simulations per move,
three full games.** The leaf evaluator is a constant, so this isolates the cost
of the *tree* from the cost of whatever evaluates it.

| | |
|---|--:|
| Tree cost per simulation | **1.280 ms** |
| Tree cost per game (25 plies) | **12.8 s** |
| Plus the network at batch 1 (0.90 ms/sim) | **22 s** |

The cost falls **150×** from the opening to the endgame, tracking the branching
factor:

| ply | branching | ms / simulation |
|--:|--:|--:|
| 0 | 1,450 | 3.207 |
| 8 | 578 | 1.701 |
| 16 | 189 | 0.434 |
| 24 | 2 | 0.021 |

This is why the root may not be used to estimate a game. Costing 25 plies at the
root rate overstates a game by about 2.5×, and the earlier figures in this file
were all root figures.

**Parallel scaling, 12 workers over 6 physical cores** (engine only, four games
per worker so that pool startup is amortised rather than charged to the parallel
arms):

| workers | games / s | speedup |
|--:|--:|--:|
| 1 | 0.331 | 1.00× |
| 2 | 0.614 | 1.86× |
| 4 | 0.941 | 2.85× |
| 6 | 1.078 | 3.26× |
| 8 | 1.291 | 3.90× |
| 12 | 1.424 | **4.31×** |

Six workers on six physical cores return 3.26×, so the shortfall is not only
hyperthreading — memory bandwidth and laptop thermal limits are in it too. An
earlier one-game-per-worker run gave 4.04×; the two agree, so the ceiling is
real and not a startup artefact.

**The composed figure: ~5.1 s per game, ~705 games per hour**, at 400
simulations per move with the network at batch 1.

One caveat, and it is not small: the scaling above is **engine-only**. Once torch
is in each worker, the network's 41% of a simulation competes for the same cores,
and each worker will need its threads pinned to 1. Whether the composed rate
holds cannot be measured until `az/network.py` exists.

**Sizing note against adr-005.** The probe comes to **328,921 parameters**,
below the ADR's stated 0.5–1.5 M target band. The factored head is the reason:
44 output logits instead of 1,950 removes the projection that would have carried
most of the difference. The ADR's instruction — *start at the small end; grow
only if training plateaus below the heuristic baseline* — is unchanged and now
has more headroom than it was written to expect. Reaching 1 M would take
128 filters or 8 blocks. No amendment needed; the band was an estimate and this
is the measurement.

## The input encoding — and the plane that was missing

`az/encoding.py`. Thirty binary planes over the board grid, written from the
**mover's** point of view so that the value head's `+1` always means "good for
the player being chosen for".

| plane | content |
|---|---|
| 0–2 | own colour / opponent colour / empty |
| 3 | side to move (constant) |
| 4–16 | own hand, one constant plane per tile still held (13) |
| 17–29 | opponent hand, same (13) |

No orientation planes: placed tiles are inert, so rotation is not part of the
state at all. Pinned by `test_there_are_no_orientation_planes`, which plays every
rotation of one tile onto one cell of an empty board and asserts all of them
encode identically — the same aliasing EXP-010 measured, seen from the input
side.

**adr-005 specified 29 planes and the table could not be implemented as
written.** It splits the hands 13 own / 12 opponent, which sums to 29 with the
four board planes. But "own" and "opponent" are relative to the side to move, and
on the 5×5 the *first* player is the one holding thirteen tiles:

```
5x5-h1   purple bits=13 joker=True    green bits=12 joker=False
```

So whenever the second player moves, the opponent is the thirteen-tile player and
the 12-plane block has nowhere to put the joker. **On half of all plies the
specified encoding hides the tile that decides who moves last.** Corrected to 13
and 13 in the Phase 4 amendment; `test_the_opponents_joker_is_visible_when_the_second_player_moves`
fails if anyone narrows it back.

Worth being precise about the severity, because it is easy to overstate. The bit
is *recoverable*: occupied cells give the ply count, which gives how many tiles
each side has played, and subtracting the visible archetype planes leaves the
joker. It is a global count across the board — the operation a small conv tower
is worst at. One input plane is cheaper than teaching the network arithmetic.

The repair also makes the layout **variant-independent**. Plane *k* means the
same thing on the 3×3, the 5×3 and the 5×5; only the spatial size changes. H3
reads across all three.

**Size on the wire.** One position is `30 × n_cells` bytes: **750 B** on the 5×5,
450 B on the 5×3, 270 B on the 3×3. The encoder needs neither torch nor numpy,
which keeps two doors open — self-play in a faster interpreter, and a replay
buffer that does not drag a tensor library into its storage format.

## az/network.py — the residual tower and the two heads

3×3 convolutional stem into 64 filters, four residual blocks, then the two heads,
exactly as adr-005 specifies.

| variant | parameters |
|---|--:|
| 5×5 | **352,495** |
| 5×3 | 332,965 |
| 3×3 | 324,319 |

Below the ADR's 0.5–1.5 M band, for the reason already recorded above: 44 output
logits instead of 1,950 removes the projection that band was estimated with.

**The factored head, and why summing raw logits is not a shortcut.** adr-005
specifies `log p(cell) + log p(tile) + log p(rotation)`, masked to legal moves
and renormalised. `masked_log_policy` sums the **raw** logits instead. That is
the identical distribution, not an approximation: each `log_softmax` differs from
its logits by a term constant across moves, and three constants added to every
legal move's score cancel in the renormalisation. It saves three softmaxes and is
better conditioned. The claim is checked against the literal formulation in
`test_summing_raw_logits_equals_the_specified_log_softmax_rule` — so if a factor
ever gains a per-move term, the shortcut stops being valid and a test says so
rather than the loss curve.

**Masking is load-bearing.** The head scores every `(cell, tile, rotation)`
triple, including triples that are not moves — a tile no longer in hand, an
occupied cell, a rotation the tile's symmetry orbit collapses. Restricting the
renormalisation to the legal list is what removes them.

**One footgun, handled.** `policy_and_value` saves and restores the module's
training flag. It is called from inside the training loop, and a helper that
quietly left `eval` set would freeze every batch-norm layer for the rest of a
60-hour run without raising anything.

## az/mcts.py — PUCT, and deduplicated expansion

PUCT over the real state, no determinization (adr-001), Dirichlet noise at the
root, temperature 1 then greedy. Three expansion modes, because EXP-010 needs a
baseline and a control alongside the design adr-005 mandates:

| mode | children indexed by | isolates |
|---|---|---|
| `ACTION` | action | the deployed-naive baseline |
| `POSITION` | resulting position | the ADR's design |
| `MULTIPLICITY` | action, priors ÷ multiplicity | prior mass alone |

The third exists because without it a win for `POSITION` at a small budget is
fully explained by *"it has ~4× fewer children and can finish one pass over
them"* — an effect you would also get by deleting three quarters of the naive
arm's children at random, which is not the mechanism the ADR describes.

### Aliasing is decided without applying the move

The natural definition of "these two actions are the same move" is *they reach
the same `GameState.key()`*, and that costs an `apply_move` per move — 1,450 of
them per expansion at the 5×5 root, more than the search itself.

Since placed tiles are inert (adr-003) and flips never chain (adr-006), the
resulting position depends only on `(cell, tile, arrows ∩ occupied neighbours)`.
An integer AND replaces the whole simulation. That is an *argument*, and
arguments can be wrong or can stop being true, so
`tests/test_az_mcts.py` checks the cheap partition against the expensive one in
both directions across three variants and three depths. It reproduces
**1,450 → 325 (4.46×)** at the 5×5 root, agreeing with
`scripts/measure_move_collapse.py`, which decides by the expensive path.

### There is no DAG

**adr-005's Phase 3 amendment predicted that deduplication "turns the tree into
a DAG" and called the backup rule an unresolved subtlety it would not
pre-decide. It does not.**

Sibling-alias merging gives a child several *action labels* and still exactly
one parent. The structure stays a tree, and there is no backup rule to choose.
The DAG appears only under *cross-parent* transposition — two different parents
reaching one position — which is a separate and larger search improvement that
has nothing to do with R13, and which `az/mcts.py` deliberately does not
implement.

Found while writing the code, after the EXP-010 registration had already fixed a
backup rule that turned out to have nothing to govern. The correction **removes**
a confounder: the falsifier no longer has to read *"the mechanism is wrong or the
backup rule is bad"*. Pinned by
`test_sibling_merging_does_not_create_a_dag`, which walks the tree and asserts
no node is reached twice.

One consequence to keep straight when quoting the result: *"deduplication helps
by X"* must never become *"transposition-aware MCTS helps by X"*. The second is
the larger, untested claim.

## az/selfplay.py — game generation

**Positions per game is exactly 25, not "at most".** The board fills every time —
25 cells, no passes, no early termination, and draws are impossible on an odd
count. So a generation of 200 games is **exactly 5,000 samples**, every time, and
the replay-buffer arithmetic has no slack in it at all: a 20,000 buffer is four
generations deep, `refresh_fraction` is a flat 0.25, and the expected age of a
training sample is four generations. Those are closed forms, not averages.

Worth stating because it is the rare place where this game is *easier* to reason
about than Go or chess, and because the ground-truth generator's own guard checks
it — a generation that does not produce 5,000 samples is a defect, and the
instrument raises rather than averaging over it.

**Parallelism is `spawn`, not `fork`**, because torch and `fork` do not coexist
safely. That has a consequence which cost two debugging sessions: **`spawn`
re-imports `__main__`**. A harness whose scale lives in module constants gets
those constants re-executed in a fresh interpreter, so a smaller debugging run is
silently the full one; and any test of the spawned path has to be a real file
with an `if __name__ == "__main__":` guard, or the workers re-execute the test.
A heredoc has no file at all and dies with `FileNotFoundError: '<stdin>'`, once
per worker, in 21 MB of tracebacks.

**Workers get a network *spec*, not a network.** The first version rebuilt every
worker's net as `FlipHexNet`, which meant parallel self-play could not drive the
adopted conditioned head — and the bug was unreachable at `workers = 1`, so no
test caught it. `net_spec()` serialises the architecture (class, board shape,
filter count, block count) and `build_net()` reconstructs it; weights travel
separately. The spec deliberately excludes `rotation_scale`, which is a
persistent buffer and therefore travels with the weights.

**Temperature.** Self-play samples from the visit counts for the opening plies
and plays greedily afterwards; evaluation uses `EVALUATION_TEMPERATURE_PLIES = 4`
for a different reason entirely — not exploration, but to stop two deterministic
searchers replaying one game 400 times. That trap is its own section below.

**Six workers, measured.** EXP-014 put self-play's optimum at six with eight
within 1%, on six physical cores. The gate's optimum is four and differs because
a gate worker holds two networks against self-play's one — the kind of thing that
is obvious once measured and was assumed identical before.

## az/replay_buffer.py

A fixed-capacity FIFO of `(planes, π, z)`. Two decisions in it are worth keeping.

**A ring buffer, not a `deque`.** The deque is the obvious FIFO and it was the
first thing written here. But sampling indexes the buffer at *random* positions,
and deque indexing is O(n) in the middle — on 100,000 samples that turns every
batch into a scan. A list with a write cursor makes eviction and random access
both O(1), which is the pair of operations this structure actually performs.

**`π` stores its own moves.** The dense alternative — a vector aligned to
`legal_moves` order — is smaller, and requires that order never to change. It is
deterministic today and nothing enforces it. A reordering would silently
misalign every stored target, and that surfaces as a training curve that never
quite converges rather than as an error.

**The refresh fraction.** `min(1, incoming / capacity)`: a generation of `g`
samples into a buffer of `c` refreshes `g / c` of it and saturates once one
generation can fill it. The expected age of a sample is `c / g` generations,
which is the quantity the capacity should be chosen against — a buffer much
larger than the run keeps training on positions from a network that no longer
exists.

`z` is exactly ±1, always, because draws are impossible. The sign convention is
the error waiting to happen: it is read **from the mover at that position**, to
match the encoding's own/opponent planes and the value head. `samples_from_game`
is the only place the alternation is written, so it is the only place it can be
written wrongly.

## az/train.py — the loss, and a normaliser that needs no move generation

Cross-entropy on the search policy plus MSE on the outcome. `z` is exactly ±1
always, so the value head's worst case is bounded at 4.0 and there is no draw
mass pulling the output toward zero.

**The problem the loss ran into.** The network's policy is the factored score
*renormalised over the legal moves*:

```
log p(m) = score(m) − log Σ_{m′ legal} exp score(m′)
```

That sum runs over **every** legal move. A replay sample stores only the visited
support — the moves the search actually reached — so the two obvious repairs are
to store the whole legal move list beside each sample, several kilobytes and more
than a doubling of the buffer, or to call `legal_moves` on every sample of every
batch.

**Neither is needed, because legality factorises exactly.** A move is legal iff
the cell is empty, the tile is in hand, and the rotation lies in that tile's
orbit — and the orbit is a property of the tile alone, never of the cell.
Measured against move generation:

| variant | ply | moves | empty | × pairs |
|---|--:|--:|--:|--:|
| 5×5-h1 | 0 | 1,450 | 25 | 58 |
| 5×5-h1 | 7 | 702 | 18 | 39 |
| 5×3-h2 | 11 | 28 | 4 | 7 |

Every row is an exact product, and the `(tile, rotation)` set is identical for
every empty cell. So the normaliser splits into two independent log-sum-exps:

```
Z = LSE over empty cells of cell
  + LSE over available (t, r) of  tile[t] + rotation[r]
```

Both masks read straight off the input planes — plane 2 gives the empty cells,
planes 4–16 give the mover's hand — and the orbit table is static. **The training
loop never calls `legal_moves`.**

With `Σ π(m) = 1` the cross-entropy then collapses to `Z − Σ π(m)·score(m)`,
which is one gather and one scatter-add over the batch.

This is checked, not argued: `test_the_closed_form_normaliser_equals_the_brute_force_one`
compares against `logsumexp` over actual generated moves across three variants
and three depths, and `test_the_loss_equals_the_naive_masked_cross_entropy`
compares the collapsed form against the literal one. If a rule change ever
introduces a cell-dependent restriction, the factorisation breaks and the loss
would silently optimise the wrong distribution — those two tests are the only
thing that would notice.

**Ragged batching.** Each position visited a different number of moves, so
policies are concatenated with a row index rather than padded. Padding to the
widest policy in a batch would allocate the worst case on every row, and the
worst case is 1,450.

## az/checkpoint.py — surviving a 60-hour run

**Decided 2026-08-31, before `az/train.py` is written.** Five seeds cost 59.6 h
on a laptop that sleeps, throttles and reboots. Axis 1 already lost two runs to
exactly that, one of them 20.8 hours in, which is why `solver/checkpoint.py`
exists. Axis 2 gets the same guarantee, and the module is separate because `az/`
may not import `solver/`.

**What Axis 2 does not inherit is the cheap part.** The retrograde sweep resumes
from one array because layer `t` depends on layer `t + 1` and nothing else. A
training loop has no such single-object state, and the tempting analogue — save
the weights — is *not* a resume point. A complete one is:

| | why it cannot be dropped |
|---|---|
| Challenger weights | the obvious half |
| Optimiser state (Adam moments) | dropping them restarts the moment estimates and puts a visible transient in the loss curve at every resume |
| Champion weights | it generates the self-play data and is the gate's opponent |
| Replay buffer | positions from earlier generations that have not aged out yet; regenerating them costs the generations that made them |
| Generation counter, and which generation last gated | |
| **RNG state** | see below — this is the one that matters most here |

**The RNG state is load-bearing because H3 is a seed hypothesis.** H3 reports a
per-seed win rate across ≥5 independent seeds and the variance between them. A
resume that re-seeds produces a run that is still *valid* but no longer
*reproducible from the seed it claims* — and reproducibility across seeds is the
quantity H3 is built on. This is the same failure `solver/checkpoint.py` guards
against with its `replay`: there, resume must reproduce the V5 checksum
byte-identically rather than merely restart the arithmetic. The rule generalises:
**a resume must be indistinguishable from an uninterrupted run, not merely a
correct continuation of one.**

**Cost — the estimate first written here was wrong by an order of magnitude, in
the direction that mattered.** It read: *"a position stored as its compact state
plus a 44-float factored policy target plus `z` is on the order of 200 bytes… a
buffer holding twenty generations is roughly 20 MB."* Both halves were wrong. The
factored head has 44 *logits*, but `π` is a distribution over **legal moves**, of
which there are up to 1,450 — and a sample stores its encoded planes, 750 bytes,
not a compact state.

Measured on the 5×5 at 400 simulations:

| ply | children | visited | as objects | packed | ratio |
|--:|--:|--:|--:|--:|--:|
| 0 | 325 | 16 | 3,643 B | 1,049 B | 3.5× |
| 6 | 280 | 3 | 1,415 B | 958 B | 1.5× |
| 12 | 149 | 149 | **24,139 B** | **1,980 B** | **12.2×** |

The support of `π` *widens* as the game shortens: by ply 12 the 400 simulations
reach all 149 children, and 149 `Move` objects with their floats cost 24 KB. At
that rate a 100,000-sample buffer is **2.4 GB** on a 15 GB machine — and a
checkpoint written once per generation for sixty hours carries the same weight
every time.

Packing `π` as three bytes per move plus one float32 brings the worst case to
**198 MB**; `Sample.policy` unpacks on demand, so callers still see
`(Move, float)` pairs. Weights are 0.33 M parameters and negligible beside it.
Checkpointing every generation is cheap again — but it was not cheap by default,
and the estimate here said it was.

**Granularity.** The longest uninterruptible unit is not a generation (≈24 min)
but the **evaluator gate at ≈34 min** — 400 games at 5.1 s. Self-play within a
generation is ≈17 min. Checkpointing per generation caps the worst-case loss at
the gate's 34 minutes; the gate additionally records its running win count, since
that is one integer and turns a 34-minute loss into a 5-second one.

Every write goes to a temporary file in the same directory followed by
`os.replace`, and the manifest is written *after* what it names — the same
discipline as Axis 1, for the same reason: a run killed mid-write must leave
either the old complete state or the new one, never a half-written buffer that
resumes into silent corruption.

## The evaluator gate

**Chosen 2026-08-31: the adr-005 threshold unchanged — 400 games at 55% — run
every 5 generations rather than every generation.**

The schedule it sits in is **30 generations × 200 self-play games**, which comes
to 6,000 self-play games and 2,400 evaluation games per seed: **11.9 h per seed,
59.6 h for H3's five seeds** at the 705 games/hour measured above.

The cadence is the compute decision. Gating every generation would cost 12,000
evaluation games against 6,000 self-play games — **two thirds of the phase's
compute spent judging rather than learning**, and 127.6 h for five seeds.

**H3's five seeds are affordable, so no deviation is registered.** adr-005 sized
the phase around *"two independent seeds"* and called that "realistic rather than
aspirational"; `docs/research.md` locked H3 at **≥5** at `v0.3-hypotheses`. The
ADR's estimate was written before any of this was measured and is superseded by
measurement, not amended — it was an estimate about compute, not a decision about
the hypothesis.

### The relaxation's false-promotion rate, which adr-005 requires stated

At 400 games and a 55% threshold, against a champion of genuinely equal strength:

| | |
|---|--:|
| Per-gate false promotion (true p = 0.50) | **2.55%** |
| Power at true p = 0.52 | 12.5% |
| Power at true p = 0.55 | 52.1% |
| Power at true p = 0.60 | **98.1%** |
| Power at true p = 0.65 | 100.0% |

**The relaxation makes the gate safer, not weaker, and the reason is worth
keeping.** adr-005 asks for the false-promotion rate because it was written with
a *lower threshold* in mind, where relaxing plainly costs error control. Cadence
relaxation is a different object: it does not touch the per-gate rate at all, it
reduces the number of gate events.

| cadence | gate events | P(at least one false promotion) |
|---|--:|--:|
| every generation | 30 | **53.9%** |
| every 5 generations | 6 | **14.4%** |

Gating every generation over 30 generations is more likely than not to promote a
challenger that is no better than the champion. The cheaper schedule is also the
one that controls the family-wise error.

The second effect points the same way. A challenger gated every 5 generations
has accumulated five generations of improvement before it is judged, which puts
it in the p ≥ 0.60 regime where power is 98% — rather than the p ≈ 0.52 regime,
where a single-generation challenger would be caught 12.5% of the time. Coarser
cadence buys power as well as error control.

**What it costs, stated plainly.** The champion generating self-play data can be
up to five generations stale, so some fraction of the training data comes from a
weaker generator than necessary. And promotion granularity is coarse: if the run
peaks at generation 13, the gate will not see it — only generations 5, 10, 15,
20, 25 and 30 are inspected. Neither is measured here; both are the accepted
price.

### Implementation, and two things the gate had to be protected from

`az/gate.py`. The arithmetic above lives in code — `false_promotion_rate`,
`power`, `family_wise_false_promotion` — rather than only in this note, so the
numbers a run reports are computed rather than quoted.

**Seats alternate, and an odd game count is refused.** Whether the first seat is
worth anything is an open question on this game, so a match run entirely from one
seat would confound *stronger network* with *better seat*. The result carries the
per-seat split rather than only the total.

**Two deterministic searchers replay one game.** At temperature zero a player is
a pure function of the position, so a 400-game gate between two of them reports
`n = 400` on an effective sample of **one** — and the win rate comes out 0% or
100%, which reads as a decisive result rather than a broken measurement. Nothing
errors. `run_gate` warns rather than forbids, since single-position use is
legitimate, and defaults to sampling four opening plies.

**The resume interface was wrong on the first pass.** `on_progress` reported
`(games_done, wins)`, which is enough to restore the total and *not* enough to
restore the per-seat split — a resumed gate would have reported the right win
rate with a fabricated seat breakdown. Writing the resume test is what exposed
it; the callback now carries `first_seat_wins` too.

### A layering error caught while wiring it

The gate plays matches, so it needs move selection, and the first version took it
from `agents.az_agent`. That made `az` import `agents` while `agents` imports
`az` — a cycle Python tolerates only for as long as the import order happens to
work out.

Move selection is **search policy**, not agent plumbing, so it belongs on the
`az` side of the line. It now lives in `az/player.py` as `SearchPlayer`, and the
two agent classes are thin adapters onto it. Pinned by a test that imports
`az.gate` in a subprocess and asserts `agents` never enters `sys.modules`.

## The plain-UCT floor

Prior-free UCT with random playouts: uniform priors, no network, rollouts to the
end of the game. adr-005 says the learned agent must beat it before any result
about that agent is reported, and `UCTAgent`'s docstring says the same thing.

**Why this and not "better than the previous generation".** Generation-over-
generation improvement is a derivative, not a floor — a run going from terrible
to slightly less terrible passes it — and it is what the evaluator gate already
measures internally, so it is the training signal read back rather than
independent evidence. Prior-free UCT depends on no training at all, so a bad run
cannot flatter it, and its rollouts always terminate with a decided winner
because draws are impossible on 25 cells.

**It is also the criterion that keeps Axis 2 from being selected by Axis 1.**
Three architecture decisions had already been taken against 5×3 solver ground
truth. Under adr-004 R1, neither axis may terminate the other along the dimension
on which they are later compared — and H3 *is* the solver-versus-learner
comparison. A floor containing no solver information is what lets the training
run end without adding to that count.

### "Entirely above 50%" is a 57% bar

The criterion is that the whole Wilson interval sits above 50%, which sounds like
a coin-flip bar and is not. At 200 games the smallest clearing count is **114 =
57.0%**; 113 gives [49.6%, 63.2%] and fails. A true 55% agent fails most of the
time.

Worth stating because the wording invites the opposite reading, and because
EXP-015's registration guessed "around 58%" rather than computing it. The
analysis script now computes it and a test pins the count.

### The reference that made the floor credible

The generation-0 champion — the randomly initialised network, before any
training — plays the same match. Across five seeds it scored **3.0% to 13.5%**.

**An untrained prior is not merely useless, it is far worse than no prior.** It
lands 36.5 to 47 points below the 50% an even match would give, against an
opponent identical except for having no network at all. The obvious reading is
that an unformed prior steers PUCT away from what plain UCT would have explored;
that is an inference from one number and was not measured.

Two things this buys. It shows the floor is not trivially passable — something
can score 3% on it. And it bounds what training moved: **45 to 62.5 points** per
seed, from the generation-0 rate to the trained one.

### The equal-time arm, and a forecast that was wrong by a factor of three

The floor was registered with a secondary arm: the same match with UCT given the
simulations it can complete in the network agent's measured per-move wall clock.
The reasoning was that the network costs ~10.9 s/game while prior-free UCT "does
no forward passes at all", so UCT would get *several times* the simulations and
equal-time would be the harder bar.

**Measured across five seeds, UCT got 0.98× to 1.17×.**

The error is in comparing the network's cost against zero rather than against
what UCT actually does. A random playout runs to the end of the game — up to 25
plies of move generation and application — where a network evaluation is one
forward pass on a static position. The two per-move costs land within 15% of each
other, so equal-time and equal-simulations are nearly the same experiment at this
budget on this board.

Two consequences, both recorded as corrections rather than results. The secondary
charges the network far less for its compute than intended, so clearing it
establishes correspondingly less. And on seed 5 the measured ratio fell *below*
one — the network was the cheaper agent — where `max(SIMULATIONS, ...)` clamped
UCT to 400 and the match replayed **identically** to the primary, field for
field. That arm is a duplicate, not a measurement, so the secondary's tally is
**2 of 4**, not 3 of 5. The instrument should have detected `ratio <= 1` and
recorded the arm as inapplicable — which is itself the finding.

## The factored-head independence check — the risk materialised

**EXP-011, run 2026-09-01, 2h16. The registered rule fires.** On the 5×3 the flat
head beats the factored one and the arms do not overlap:

| | factored | flat | gap |
|---|--:|--:|--:|
| top-1 optimality after 400 PUCT sims | **66.8%** | **73.7%** | **+7.0** |
| supervised top-1 agreement | 58.6–60.8% | 65.6–68.6% | **+8.0** |
| random-legal-move floor | | 39.6% | |

Per seed: factored `67.2, 66.6, 66.2, 65.8, 68.0`, flat `74.2, 74.2, 75.6, 71.8,
72.8`. Every factored seed sits below every flat seed. Paired *t* **+6.96**
[+4.81, +9.11]; between-seed spread 1.5% against a 7.0-point gap.

### The finding is about mitigation (a), not about which head is bigger

adr-005 lists three mitigations *in order* and the first is "rely on MCTS to
correct the prior, which is exactly what MCTS is for". The entry was rewritten
after red-team specifically so the primary metric could test it. It did:

- supervised gap **+8.0** points
- gap after 400 PUCT simulations **+7.0** points

**Search closed about an eighth of the deficit.** Mitigation (a) is not merely
insufficient here — at this budget on this board it is close to inert. That is a
sharper statement than "the flat head wins", and it is the one the write-up
should carry.

### Not an artefact of the schedule

Final *training* policy loss: factored **2.616**, flat **2.375**. The factored arm
is worse on the data it was fitted to, not only on held-out data, so this is an
expressiveness ceiling rather than a generalisation gap or an early-stopping
accident. More epochs do not close it.

### What it does not establish, and this matters

The flat arm has **879,381** parameters against **332,965**; 1,170 logits against
34. **The experiment cannot separate "cell, tile and rotation are not
conditionally independent" from "34 logits is not enough capacity."** adr-005's
question — is the factored head *too costly* — is answered either way, which is
why the design was pitched at the pipeline level. But the *mechanism* is open,
and nothing written later may claim otherwise.

Fallback (b), rotation logits conditioned on the chosen cell, is registered as
EXP-012.

**Correction (2026-09-01).** This paragraph originally said (b) *"is the probe
that would settle it — if (b) recovers most of the gap the mechanism was
independence; if it does not, it was capacity"*. That is **withdrawn as
impossible rather than unproven**. In this parameterisation any relaxation of the
factorisation adds output dimensions, because relaxing it is what adding them
means: independence and output-width capacity are the same axis, and no
experiment varying the head's factorisation separates them. EXP-012 replaces the
question with one that is answerable — whether the **cell** is what rotation
depends on, which is adr-005's actual assertion.

### The margin, recorded rather than repaired

The registered rule reads on the point estimate and the seed spread: 7.0 > 5 and
7.0 > 1.5, so it fires as written. **But the paired-*t* interval reaches +4.81,
just under the 5-point margin.** Under the stricter criterion EXP-010's red-team
imposed on *its* falsifier — the interval must exclude the margin — this would be
marginal rather than decisive.

That stricter form was never written into EXP-011's rule, and it is not being
retrofitted now. Rewriting a decision rule after seeing the numbers is what
pre-registration exists to prevent, and it is no more legitimate for pointing at
the weaker conclusion. Both numbers are in the artefact.

### The claim that did not survive

adr-005's Phase 3 amendment asserts that "a sizeable share of the rotation
factor's output is not modelling a choice at all". Measured over 2,500 positions
and 51,250 `(cell, tile)` pairs: **21.6%** across all tiles, **11.4%** over
multi-orbit tiles only. The larger figure counts `P6`, whose orbit is 1 and for
which the property is vacuous — the definitional artefact the registration
required both figures in order to expose.

**11.4% is not a sizeable share.** The rotation factor has more to model than the
amendment supposed, so this is *not* why the factored head lost.

### Consequences carried forward

- **Fallback (b) must be registered and run** — the rule says so, and the ADR
  pre-specified the order.
- **R5 rises from 4 to 6** in the risk register: this is no longer a risk that
  might bite.
- **H3's 5×3 member now carries an architecture-selection caveat**, the repair
  the registration pre-committed to for exactly this branch: the architecture was
  chosen by fitting Axis 1 ground truth on 5×3 positions, and H3 later reports
  agreement against Axis 1 on a set including the 5×3.
- **Nothing here is evidence about the 5×5.** The measurement is on a 15-cell
  board with 8-tile hands.

## The head ladder, resolved — EXP-012 and EXP-013

adr-005 pre-specified three mitigations in order: (a) rely on MCTS to correct the
prior, (b) condition rotation on the chosen cell, (c) a flat 1950-logit head.
EXP-011 killed (a). These two settled the rest.

### EXP-012 — fallback (b) is adopted, by a quarter of a point

8h50 on the 5×3. The registered comparison came back **`D − B = +3.76`
[+1.78, +5.74]** — an interval straddling the 5-point tolerance, which is not a
result. A bounded extension to twelve seeds gave **+3.32 [+1.88, +4.75]**, inside
the tolerance, and (b) was adopted.

**It cleared by 0.25 points**, against a 5-point constant that had changed role —
from EXP-011's *detection threshold* to an adoption *tolerance* — without being
rejustified. A margin of 4.7 would have reversed the decision. That is in the ADR
amendment and in R5, because a decision that close should not be quoted as if it
were comfortable.

**And the entry's own validity precondition failed, unpassably.** The equivalence
gate's half-width was **2.43** against a δ of **2.00**: no point estimate,
however favourable, could have cleared it. The gate could be neither passed nor
failed on evidence, so every mechanism contrast in that experiment is unresolved.

That produced the rule the project has used since: **δ must exceed the forecast
half-width, and the room between them is tabulated before the run.** EXP-013's
forecast then landed to the second decimal — predicted `sd` 1.95, observed 1.94 —
which is the only reason the same trap did not repeat.

**What (b) does not settle.** The frozen-tower condition put all three candidate
heads on one shared tower, where they landed at 67.6–68.8% against the factored
head's own 68.0%: **no head architecture mattered at all** under that condition.
So what was fixed is the operational risk — the head plays too weakly — and not
the stated mechanism, which is still unverified. R5's likelihood came down to 2
rather than 1 for exactly that reason: a remedy that works without an understood
mechanism gives no model of when it would bite again.

### EXP-013 — the same head, 218× fewer parameters

The adopted parameterisation was the inefficient one: twenty-five unshared
per-cell rotation maps, **43,290** parameters, where a 1×1 convolution expresses
the same conditioning in **198**. The convolution shares weights across cells, so
it sees every cell on every position instead of the 36.7% an unshared map sees.

4h20, twelve seeds, one-sided non-inferiority at δ = 1.7 points:
**`V_conv − L_linear = +0.95`**, lower limit **−0.06%** against a margin of
−1.70%. Adopted. On the shipped 5×5 the conditioned head drops from 467,839
parameters to **347,887** — below the factored head's own 352,495, which is the
part worth noticing: the *more* expressive head is the smaller one.

**The registered secondary was broken twice over, and was fixed before the run.**
It read the training loss against *solver* labels rather than non-solver ones,
and its direction rule contradicted the entry's own prediction 4. Replaced with
head-to-head play by a dated amendment **before** anything ran. Catching it after
would have meant either quoting a broken secondary or retrofitting a rule.

### What the ladder cost, and what it bought

Three architecture decisions taken against 5×3 solver ground truth, out of an
adoptable choice set of four. That count is the measure of how much of Axis 2's
*design* is a function of Axis 1's answers, and it is why the training run's
success criterion had to contain no solver information at all.

**None of it was measured on the 5×5 until the run itself**, and no alternative
head has *ever* been trained on the shipped board. The 3.3-point deficit against
the flat head is a 5×3 number quoted over a 5×5 design, and it stays that way.

## The pipeline shakedown — EXP-014

Before committing ~146 hours, four checks at toy scale: the loop closes, parallel
workers drive the adopted head, the gate decides, and a `SIGKILL` mid-gate
resumes **byte-equal**. 48 minutes. All four pass — on the second attempt.

### C4 failed first, and the defect was real

First run: `1331009c1664` against `325477f94bde`. A checkpoint written *inside* a
gate carries a generation whose self-play and training have already happened —
they are baked into the buffer and the challenger it stores. The loop re-entered
the generation body on resume and replayed both, extending the buffer with the
same games twice and taking another 400 gradient steps.

**Nothing raises.** The weights simply diverge, invisibly, unless something
compares them byte for byte against an uninterrupted run.

`tests/test_az_loop.py` could not have caught it: it simulates interruption by
calling `run` twice, and two probes had already shown that comparison passes on
broken code. The defect needed a real kill at a real checkpoint boundary — which
is the argument for the shakedown existing at all.

Two smaller ones surfaced the same way. The mid-gate checkpoint cadence was a
module constant of 25 against a 20-game gate, so no mid-gate checkpoint would
ever have been written and the kill would have landed where the path had never
run — C4 would have tested nothing. And the harness's scale lived in module
constants while its child is a fresh interpreter under `spawn`, so a smaller
debugging run would silently have been the full one.

### The cost discovery, which is the actual finding

**145 games/hour composed, 0.21× the engine-only 705.** The budget in R8 said
59.6 h for five seeds. Reconstructing that number showed the error was compounded
twice: 42,000 games ÷ 705, where the 42,000 is the run's 30,000 self-play games
**plus the gate's 12,000**, all priced at the *parallel self-play* rate. The gate
had never been parallelised — one process, **89 games/hour**, four times the
per-game cost — and was **61% of a projected 220.9 h**.

Parallelising it brought the projection to 137.6 h. Worker optima differ by
activity and were measured rather than assumed: self-play saturates at **six**,
the gate peaks at **four** and loses 33% at eight, because a gate worker holds
two networks against self-play's one.

**The residual R8 had named was the right worry pointed at the wrong quantity.**
It said the parallel scaling had been measured engine-only. Scaling was roughly
right — 3.26× predicted, 3.76× measured. The **per-game cost** was 2.1× worse for
self-play and 2.7× for the gate. Scaling was fine; cost was not.

## agents/az_agent.py — and a determinism trap the gate walks into

`AZAgent` (network + PUCT) and `UCTAgent` (uniform prior + random rollouts, the
floor), both behind the same interface as random, heuristic and solver, so the
benchmark protocol applies unchanged.

**Deliberately not exported from `agents/__init__.py`.** Importing any submodule
of a package runs that package's `__init__` first, so listing `AZAgent` there
would make `from agents.random_agent import RandomAgent` load torch — a second or
two on every import, and an outright failure under the faster interpreter the
exact-solver runs use, which has no torch build. Pinned by a test that imports an
agent in a subprocess and asserts `torch` is absent from `sys.modules`.

**The trap, which belongs to the gate and not to the agents.** At temperature
zero with no root noise, a searcher is a *pure function of the position*. Two of
them play the same game every time. A 400-game evaluator gate between two
deterministic agents therefore measures a sample of size **one** while reporting
`n = 400`, and the binomial interval computed on it is fiction.

It is easy to walk into because nothing errors: the games run, the win rate comes
out 0% or 100%, and a 100% win rate looks like a decisive result rather than a
broken measurement.

The fix is to sample the opening from the visit counts and play greedily after —
`EVALUATION_TEMPERATURE_PLIES = 4`. It weakens both sides identically, so the
comparison stays fair, and it makes the games genuinely distinct. The default
stays 0, because the strongest configuration is the right default for anything
that is not a match; **the caller has to introduce diversity deliberately.** Both
halves are pinned by tests, one asserting the replay and one asserting the way
out.

## The training run — EXP-015

Five seeds × 30 generations × 200 games, gate every 5 generations at 400 games,
buffer of 20,000 crossing generations. **135.0 hours of machine time**, 27.0 per
seed, over eleven calendar days with the machine hibernating overnight.

**The cost estimate landed.** ≈146 h projected, 135.0 h spent — 8% high, and the
first cost estimate in this project to come in close. It landed because it was
built from EXP-014's measured decomposition rather than from a composed rate,
which is the whole lesson of R8's two compounded errors.

### Four of five seeds clear the floor

| seed | rate | Wilson 95% | verdict |
|--:|--:|:--|:--|
| 1 | 64.0% | [57.1%, 70.3%] | clears |
| 2 | 76.0% | [69.6%, 81.4%] | clears |
| 3 | 63.0% | [56.1%, 69.4%] | clears |
| **4** | **56.0%** | **[49.1%, 62.7%]** | **fails** |
| 5 | 62.0% | [55.1%, 68.4%] | clears |

Seed 4 missed by **two games** — 112 where 114 was needed. That is recorded and
it changed nothing. A pre-registered rule that bends for a two-game miss is not a
rule, and the same two games of noise would equally have carried a genuinely
unstable seed over the line.

**The mean is 64.2% and it is not the result.** It is in the artefact because the
registration promised the five rates and their spread whatever happened, and it
is the number most likely to be quoted in place of the verdict.

### The spread is a measurement, not one unlucky seed

This is the part that gives H3's stability clause more than a shrug. The clause's
measurement column said "variance reported", and reported alone cannot be wrong.

Between-seed `sd` **7.3%** against the **3.4%** the 200-game samples alone would
produce; homogeneity `χ² = 18.52` on 4 df against a 0.05 critical value of 9.488.
**A single underlying win rate is rejected.** Runs differing only in seed reach
genuinely different strengths, and 56% and 76% are both things this pipeline
produces.

The χ² gates nothing — the criterion is per-seed precisely because a homogeneity
test can pass while a seed sits below 50% — and it names no cause. Nothing
separates seed-dependent training dynamics from seed-dependent self-play data,
and five seeds could not separate them if they tried.

### What the training curves say, and what they do not

Policy loss fell 5.05–5.20 → 3.74–3.88 on every seed; value loss 0.49–0.61 →
0.42–0.44. **Every seed converged.** R6 is worded "unstable *or* non-convergent"
and only the first half bit: what varies is the level reached, not whether
training proceeds. Bundling two failure modes into one risk row cost that
distinction until the data forced it.

Gate rates decay into the threshold — the three early gates average **75.1%**,
the three late ones **56.4%**, with 6 of 15 late gates below the 55% line against
0 of 15 early. That is what a run approaching the capacity of its budget looks
like. It is also what a run whose gate has stopped discriminating looks like, and
nothing here separates them.

**A correlation reported and not explained.** Seed 4 has the fewest promotions (4
of 6) and the lowest floor rate, which is the story one wants. It does not
survive the other rows: seeds 1 and 3 also froze their champion at generation 24
and landed at 64.0% and 63.0%, while seeds 2 and 5 both carried generation-29
champions and landed 14 points apart. At five seeds with one failure, no such
relationship is identifiable.

**The gate's own discipline is a live suspect and was never tested.** Thirty
gates promoting on a 55% point estimate at 400 games carry a **54.0%** chance of
at least one false promotion across the run. A champion promoted on noise would
present exactly as a weak seed.

### The seat splits, which are not evidence for H1

Large and consistent — 75 to 97 wins as first against 34 to 55 as second. They
are **confounded**: the two seats are held by different agents, so a seat effect
cannot be told apart from the champion being stronger than UCT by a different
amount in one role than the other. H1 is measured in Phase 5 under a matched
protocol.

## Training runs and the submission log

`docs/submission-log.md` carries one row per agent version considered done enough
to evaluate. Phase 4 produces **five**: the champions of EXP-015's five seeds,
each reproducible from the commit and the registry entry named in its row.

**The log's original columns do not fit what was measured, and the row is honest
about that rather than padded.** They read *vs random / vs heuristic / vs
solver*, which is the protocol built for Axis 1's agents in EXP-008. The Axis 2
champions were never played against `RandomAgent` or `HeuristicAgent` — their
registered opponents are prior-free UCT (EXP-015) and exact ground truth
(EXP-006). Those columns stay empty rather than being filled with a different
measurement wearing their name.

## EXP-006 — the third member of H3's comparison set

Registered **2026-08-05, before Axis 2 existed**, which is the entry's whole
point: a comparison set fixed after seeing the learner is not a comparison set.
It is the member that keeps H3 from resting entirely on reduced boards.

750 positions from the shipped 5×5 at `k ∈ {6, 7, 8}`, solved exactly. 4.39 h.
**749 proved**, one excluded at the 20,000,000-node budget and recorded rather
than replaced — replacing it would select the sample on how hard it was to solve.
The registered stratum is complete: 500 of 500, zero exclusions.

### The measure was vacuous, and nobody noticed for six weeks

Draws are impossible, so every position is a WIN or a LOSS for the mover. **From
a LOSS, every legal move preserves the value** — the opponent wins whatever is
played — so the registered measure, "does the chosen move preserve the value",
scores a hit for free on every lost position.

Measured on the real sample, the lost fractions are **39.2%, 3.6% and 46.1%** at
`k = 6/7/8`. Under the original rule, **148 of the registered stratum's 500
positions** would have been automatic hits, and the 0.90 threshold would have
demanded ~85% real accuracy at one `k` and ~89% at another — one number meaning
two different things, with the pooled meaning fixed by a mix nobody had measured.

**The mix is structural, not noise.** `t = 25 − k` and the mover alternates with
`t`, so odd `k` puts the first player on move — and odd `k` is also exactly when
the mover places one more tile than the opponent before the board fills. Those
two explanations are **perfectly confounded** on this board: the first player is
on move precisely when an odd number of cells remain. The swing is not evidence
for H1, and not for a pure tempo effect either.

The fix, amended in before the run: the denominator is the positions the mover
**wins**. The threshold stayed at 0.90 and is therefore *stricter* than
registered — discovering that a measure was inflated is not a licence to re-tune
the bar to the inflation.

### Verifying the claim instead of asserting it

A 100-position calibration sweep solves every distinct child. Its pre-registered
check **holds**: on all 26 lost positions, every child is a win for the opponent.

And it caught what the probe behind the amendment had missed — **3 of the 74 won
positions have no losing move at all**, vacuous for the same reason. The probe
had found zero in 30 and the amendment said explicitly that "zero is a
measurement on one `k` at one sample size and not a proof". That sentence is the
only reason the sweep was registered.

The sweep also gives the floor the rate sits on: the median share of legal moves
that throw the win away is **78.1%**, so **a random mover agrees on 21.9%** of
won positions. No agreement rate is quoted without it.

### The result: fourteen points short, on every seed

Agreement is scored by **value preservation** — the chosen move is applied and
the child solved exactly — never by identity with the solver's move. A won
position usually has several winning moves, and scoring identity would report
correct play as an error.

| | rate |
|---|--:|
| random mover | 21.9% |
| raw prior, no search | 53.5% |
| **champion, 400 simulations** | **75.7%** |
| required | 90.0% |

All five seeds fail: 74.4% to 77.0%, and the **upper** limit of the best is
81.1%. Search is worth +22.2 points over the raw prior and the prior +31.6 over
random, so the learner is emphatically doing something. It is 14 points from the
standard.

**Why the failure is believed, given that a unanimous result is exactly the shape
an instrument defect takes.** Across all five seeds and both arms the rate is
monotone in difficulty — `k = 7` 85.7–89.4%, `k = 6` 69.3–78.2%, `k = 8`
51.1–62.2% — and a broken scorer does not produce that ordering ten times out of
ten. Ten rows re-derived from scratch with a fresh solver and a fresh
transposition table: 10/10 roots re-solve to WIN, 10/10 moves reproduce from the
recorded seed, 10/10 verdicts confirm. Zero child solves hit the budget. A second
full run produced a byte-identical artefact.

### Two readings that only exist because the design was adversarial

**The Takizawa gap is real.** The second stratum — uniform over the layer index
rather than reached by play — was added in 2026-08-07 against Takizawa 2023 §5,
which gives empirical evidence that an evaluator's systematic errors concentrate
where play does not go. Four of five seeds score worse off the play distribution.
And the raw gap **understates** it, because the off-distribution stratum is
*easier* by composition (more `k = 7`, less `k = 8`): standardising to the
registered mix moves the gap from **−4.2 to −5.9 points**. The strata are never
pooled, and seed 5 reversing the sign is reported rather than smoothed.

**The seed spread collapsed.** The same five champions:

| | mean | sd | range |
|---|--:|--:|--:|
| solver agreement | 75.7% | **0.9%** | 74.4–77.0% |
| prior-free UCT floor | 64.2% | **7.3%** | 56.0–76.0% |

Seed 4 — the one that failed the floor, the one whose `χ²` rejected a common
rate — is ordinary here, 1.2 points below the best. **This does not resolve the
instability; it says the two measures are measuring different things.** A
plausible mechanism is that the floor is a whole game where a difference
compounds over 24 plies, while this is a single decision in a deep endgame, but
that is an inference from two numbers. What is established is narrower and still
useful: endgame value agreement is far more stable across training seeds than
head-to-head strength is, so seed variance is a property of the measurement as
much as of the learner.

### The threshold, and what it cost to leave underived

**0.90 was pre-declared on 2026-08-05 and never derived.** For a negative verdict
that would normally be a serious weakness — a bar set by taste can fail a learner
a justified bar would pass. It does not matter at a 14-point gap, by arithmetic
rather than by rhetoric. It is recorded because the next entry to use this bar
may land near it, and then the missing derivation decides the outcome.

### Where this leaves H3

**Both clauses now have negative verdicts.** Clause 1 (stability across seeds) is
recorded as instability from EXP-015; clause 2 fails on the shipped-5×5 member
here. H3 is not closed — the 3×3 and 5×3 members remain unread — but no
combination of the remaining reads converts either verdict.

**What is not established.** That the architecture is wrong, the budget too
small, or more training would close 14 points: nothing here varies any of those,
and attributing the gap to one would be a story. That the learner is weak in
general — it beats prior-free UCT on four seeds of five and a random mover by 54
points here. And nothing about play away from `k ≤ 8`.

Retraining or re-tuning to move 75.7% toward 90% requires a new registered entry.
Selecting on this outcome is what the pre-registration exists to prevent.

### The risk register had no row for this

Thirteen risks, every one naming a *cause* that could make the learner weak —
head architecture, action aliasing, no augmentation, compute, training
instability — and none naming the outcome. H3's own falsification condition had
no row. The nearest, R9, is scoped to a 3×3 value disagreement at likelihood 1.
R6 does not cover it by its own text: a run whose five seeds all landed on 75.7%
with an `sd` of 0.2% would satisfy R6 completely and still fail H3.

**R14 was added after the fact and the lateness is part of the entry.** What the
missing row cost was not the result — a pre-registered bar that is missed and
reported is worth more than one that is met — but the foresight: with no
pre-declared response to falling short, five causal stories were available to
reach for afterwards.

## Lessons Learned

## Failed Attempts
