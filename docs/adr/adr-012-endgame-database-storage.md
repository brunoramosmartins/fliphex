# ADR-012 — Endgame databases: measure the crossover before building one

**Status:** Accepted
**Date:** 2026-08-05 (ratified 2026-08-05)
**Deciders:** Bruno Ramos Martins

## Context

[adr-004](adr-004-solver-approach.md) commits to retrograde endgame analysis on
the 5×5 and says nothing about how the resulting databases are indexed, stored,
or compressed. The roadmap's Phase 3 exit criterion asks for coverage to `k ≤ 5`
empty cells. Nothing in the repo justifies either the format or the target `k`.

The sizes, from `scripts/layer_profile.py` (upper bounds — the formula assumes
every 2-colouring of the filled cells is reachable):

| `k` empty | cumulative bound | at 1 bit/position |
|--:|--:|--:|
| 0 (terminal) | 3.36 × 10⁷ | 4 MB |
| ≤ 3 | 9.4 × 10¹² | ~1.2 TB |
| ≤ 4 | 1.5 × 10¹⁴ | ~19 TB |
| ≤ 5 | 1.2 × 10¹⁵ | ~150 TB |

Each additional `k` costs 8–15×. The roadmap's `k ≤ 5` is not reachable on a
personal machine at any compression ratio the literature reports.

### Three things about FLIPHEX that the tablebase literature does not cover

**1. FLIPHEX layers form a DAG, so the standard algorithm is the wrong one.**
Chess and checkers material slices are closed under *successors* and contain
**cycles** — non-capture moves stay inside a slice. Cycles are the entire reason
that literature uses predecessor-driven propagation with successor counters and
fixpoint iteration: a position cannot be evaluated until its successors settle,
and they may never settle. FLIPHEX layer `t` depends **only** on layer `t + 1`;
one sweep suffices. `notes/schaeffer-2007-checkers-is-solved.md` §2.1 already
calls this "a change of algorithm class"; the storage consequence was never
drawn out.

There is a second, sharper reason. [adr-003](adr-003-piece-representation.md)
discards tile identity and rotation from the state, so **a move is not locally
invertible**: un-placing requires guessing which arrow pattern caused which
flips and enumerating candidate un-flips. Forward move generation already exists
in `fliphex/`.

**2. The "don't care" trick does not transfer.** Syzygy and the checkers
databases gain heavily by marking illegal positions as don't-care and letting the
compressor choose whatever value compresses best. That works because in chess
*broken* is a **local, O(1) predicate** (kings adjacent, pawn on rank 1). In
FLIPHEX, the gap between the closed-form bound and true reachability is
**global**: deciding whether a layer-20 configuration is reachable needs a path
from ply 0 — the whole hump. The don't-cares cannot be cheaply labelled, so they
cannot be cheaply handed to a compressor.

Note that reachability is not needed for *correctness*. Backward induction over
all configurations gives correct values on the reachable subset regardless.
Reachability buys space only.

**3. Folding a Z/2 mirror into the index is not worth it.** Chess folds a group
of order 8, which is why canonicalisation pays there. The mirror saves 50% —
**less than half a ply of depth**, against 8–15× per additional `k`. It costs on
every write and every probe, breaks the locality that block compressors exploit,
and [adr-010](adr-010-solver-correctness.md) V6 requires keeping an unfolded
sample anyway.

### The precedent that reframes the whole decision

**Takizawa (2023), "Othello is Solved"** ([arXiv:2310.19387](https://arxiv.org/abs/2310.19387)).
Othello 8×8 was weakly solved with **forward alpha-beta and transposition
tables**, exhaustively resolving positions at 36 empty squares and referencing
those from shallower search. The authors state that they considered a *strong*
solution intractable and did not attempt one. **No endgame database was
materialised.**

Othello is FLIPHEX's structural twin: diverging, fixed termination, cells only
fill, `k` empty ≡ ply `N − k` rigidly, hump-shaped layer profile. It is the only
game with these properties that has been solved, and it was solved without the
artefact this ADR was convened to design.

The arithmetic points the same way. At `k = 5` the mover holds ~3 tiles and there
are 5 empty cells, so the subtree below such a node is of order 10⁵–10⁷ nodes —
milliseconds of exact alpha-beta, and far less with a transposition table. A
tablebase earns its keep by amortising across many probes; here the search that
would probe it may be cheaper than decompressing a block.

## Decision

**1. No endgame database is materialised in Phase 3 until the crossover is
measured.** The question the ADR answers is not "which format" but "**at which
`k`, if any, does storing beat searching**". Phase 3 registers three measurements
(below) and the format decision is made against their results, not ahead of them.

**2. The terminal layer is built regardless.** 3.36 × 10⁷ positions, 4 MB at one
bit, and it is adr-010 V0's base case. It is built and checksummed whatever else
is decided.

**3. If a database is built, the sweep is `pull`, not `push`.** Enumerate layer
`t`, generate each position's successors in layer `t + 1` via the existing
forward move generator, take max/min. No predecessor generation, no successor
counters, no fixpoint iteration. This turns the workload from random writes into
a mutable layer — the case that forces the checkers-style uncompressed working
arrays — into **random reads from an immutable, already-compressed layer**, which
is the access pattern block-compressed formats are designed for.

**4. The index is a mixed-radix rank, stated explicitly.** Position → integer as
the composition of four ranking functions matching the bound's four factors:
`C(N, t)` for which cells are filled, `2^t` for their colours, `C(d₁, ⌈t/2⌉)` and
`C(d₂, ⌊t/2⌋)` for the two hands. Side to move and both hand sizes are
*determined* by `t`, so they are not stored.

**5. No symmetry folding in the index.** The mirror stays what adr-010 V6 makes
it — a consistency *check* against an unfolded sample — not an index transform.

**6. adr-010 V1's reachability count is taken before any don't-care filling, and
recorded separately.** Filling destroys the ability to distinguish "unreachable"
from "computed". This is cheap to honour up front and impossible to retrofit.

**7. Any don't-care set comes only from the sound over-approximation "has at
least one legal predecessor", iterable `j` steps back.** `j = 1` is one
predecessor pass per layer. Its yield is unknown and is one of the three
measurements.

## The three measurements that decide it

Registered in [`experiments/registry.md`](../../experiments/registry.md) before
any run.

- **EXP-003 — endgame subtree cost.** Exhaustive search from sampled ply-`(25−k)`
  positions, `k = 3…8`, with and without a TT. **Decision rule:** if the median
  exact search at `k` costs under 10⁶ nodes, no database is built for that `k`.
  The output is the crossover `k*` where storing starts to pay.
- **EXP-004 — real compressibility.** Measured on the 3×3 and 5×3, where the
  space is fully enumerable. Bits/position under raw, block-RLE, block-Zstd and
  logic-minimized, each with a probe-latency budget. Separates options A and C
  and calibrates which `k` fits the actual disk.
- **EXP-005 — don't-care yield.** Fraction of the closed-form bound with no legal
  predecessor, per layer, on the 5×3. This is also where the **reachability gap**
  is measured — a quantity the adr-010 Phase 3 amendment removed from V1, because
  V1 is now exact per-layer equality against the configuration space and cannot
  also be a measurement of an unknown.
  **Decision rule:** if the yield is under 20%, don't-cares are dropped from the
  design entirely.

## Alternatives considered

These remain live; the measurements choose between them.

- **Option A — dense bit array, one immutable block-compressed file per layer,
  pull sweep, no folding.** The conservative option, supported by the
  checkers and Syzygy literature. Block index plus per-file checksum satisfies
  V5; unfolded storage satisfies V6 for free.
- **Option B — no materialised database; exact endgame search with a TT, seeded
  per query.** adr-004's stated purpose is that alpha-beta consult the database
  as a perfect evaluation function at depth `25 − k`; a ~10⁵–10⁷-node exact
  search may deliver exactly that at lower total cost. Precedent: Othello. Cost:
  nothing persists, so V5 has no artefact and V1's reachability measurement must
  come from elsewhere (EXP-005 supplies it).
- **Option C — symbolic representation.** Store the win-set as a minimized
  Boolean function or a ZDD/BDD over the index bits (Gomboc & Shelton 2022).
  Exploits a large *unlabelled* don't-care set without needing to label it, and
  needs no block index — you evaluate a formula rather than decompress. High
  risk: construction cost is the unknown, and it is a third representation to
  verify.

## Consequences

**Positive**

- Phase 3's exit criterion stops asserting an artefact whose feasibility was
  never checked. `k ≤ 5` at 150 TB was not going to happen.
- The pull-direction decision removes the single largest piece of machinery the
  literature would have imported, and it follows from the project's own
  established facts (DAG layers, adr-003) rather than from taste.
- Ordering V1 before don't-care filling protects a measurement that cannot be
  recovered later.

**Negative / accepted costs**

- Phase 3 now carries three measurement experiments before its main artefact.
  They are cheap, but they are sequenced ahead of the interesting work.
- If EXP-003 shows the crossover is beyond any reachable `k`, Axis 1 produces no
  endgame database at all, and **H3's comparison set loses the "5×5 endgame
  layers" member** it gained in the Phase 2 amendment to `docs/research.md`. That
  would leave H3 resting on reduced boards again, which is the problem the
  amendment was written to fix. This is the real risk of this ADR and it should
  be watched, not discovered.
- The roadmap's Phase 3 exit criterion and deliverable list need revising.

## Related

- [adr-004](adr-004-solver-approach.md) — commits to retrograde analysis; this
  ADR fills the storage gap and qualifies the commitment
- [adr-003](adr-003-piece-representation.md) — why moves are not locally
  invertible
- [adr-008](adr-008-board-mirror-symmetry.md) — the mirror, kept as a check
- [adr-010](adr-010-solver-correctness.md) — V0, V1, V5, V6 constrain the format
- [adr-011](adr-011-reduced-variant-parity.md) — the 5×3 that EXP-004 and EXP-005
  are measured on
- `notes/takizawa-2023-othello-is-solved.md` — the precedent
- `notes/schaeffer-2007-checkers-is-solved.md` §2.1, §2.3 — the algorithm-class
  change and the checkers database sizing
