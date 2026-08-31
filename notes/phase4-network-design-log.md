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

<!--
Parallelism model, temperature schedule, and how many games per generation.
Positions per game is <= 25, which makes the arithmetic for the replay buffer
unusually clean.
-->

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

## az/train.py — the loss and the loop

<!--
Cross-entropy on the MCTS policy plus MSE on the outcome, with weight decay.
z is always exactly +/-1 because draws are impossible.
-->

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

## The plain-UCT floor

<!--
Prior-free UCT with random playouts, as the absolute baseline that depends on no
trained network. adr-005: the learned agent must beat it before any result is
reported.
-->

## The factored-head independence check

<!--
adr-005 records the conditional-independence assumption as the main Axis-2 risk
and requires it to be checked explicitly and logged, not assumed away. The
fallbacks, in order: condition rotation logits on the chosen cell; then the flat
1950-logit head. Note the flat head does NOT fix aliasing.
-->

## agents/az_agent.py

<!--
Network + MCTS behind the same Agent interface as random, heuristic and solver,
so benchmark-protocol.md applies unchanged.
-->

## Training runs and the submission log

<!--
Every version considered done enough to evaluate gets a row in
docs/submission-log.md, reproducible from the commit and config named in it.
H3 needs >= 5 seeds.
-->

## EXP-006 — the third member of H3's comparison set

<!--
500 shipped-5x5 endgame positions at k <= 8, solved exactly on demand. Registered
2026-08-05, blocked on Axis 2 until now. It is the member that keeps H3 from
resting entirely on reduced boards.
-->

## Lessons Learned

## Failed Attempts
