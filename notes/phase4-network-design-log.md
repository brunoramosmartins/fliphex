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
highest in the register — is a Phase 4 risk in its entirety.

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
split with self-play in PyPy and inference served from CPython, or accepting
2,499 plies/s and parallelising across the 12 cores — self-play is
embarrassingly parallel, which recovers roughly an order of magnitude for free.

**Sizing note against adr-005.** The probe comes to **328,921 parameters**,
below the ADR's stated 0.5–1.5 M target band. The factored head is the reason:
44 output logits instead of 1,950 removes the projection that would have carried
most of the difference. The ADR's instruction — *start at the small end; grow
only if training plateaus below the heuristic baseline* — is unchanged and now
has more headroom than it was written to expect. Reaching 1 M would take
128 filters or 8 blocks. No amendment needed; the band was an estimate and this
is the measurement.

## az/network.py — the residual tower and the two heads

<!--
adr-005: 3x3 conv stem to 64 filters, 4 residual blocks, ~0.5-1.5 M parameters,
factored policy head (25 + 13 + 6 = 44 logits), tanh value head. Record actual
parameter count, and the masking-and-renormalisation path for illegal moves.
-->

## The input encoding

<!--
29 planes of 5x5, per the adr-005 table. Record the tensor size in bytes, the
plane ordering as implemented, and any deviation from the ADR with its reason.
Ex04 question 4 asks for exactly this justification.
-->

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

<!--
FIFO of (position, pi, z) triples. Capacity, and the refresh fraction per epoch
— ex04 question 3 asks for the closed form.
-->

## az/train.py — the loss and the loop

<!--
Cross-entropy on the MCTS policy plus MSE on the outcome, with weight decay.
z is always exactly +/-1 because draws are impossible.
-->

## The evaluator gate

<!--
400 games at 55%, per the adr-005 Phase 2 amendment. If it is relaxed, the
relaxation must state its own false-promotion rate. Record which was chosen and
what it cost in compute.
-->

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
