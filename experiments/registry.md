# Experiment Registry

Every experiment is registered **before it runs**. Results are appended after.
An experiment that is not in this table did not happen.

Freely editable (append-only in practice).

## Format

- **ID** — `EXP-NNN`, allocated in order, never reused.
- **Hypothesis** — H1–H6, or `—` for exploratory runs.
- **Status** — `registered` → `running` → `complete` / `abandoned`.
- **Seed** — the RNG seed. Required. `—` only for deterministic exhaustive solves.
- **Result** — one line, with a CI or an exact value. Links to the notebook or figure.

## Registry

| ID | Date | Hypothesis | Axis | Description | Config / commit | Seed | Status | Result |
|---|---|---|---|---|---|---|---|---|
| EXP-001 | 2026-08-05 | H1, H2 | 1 | Exhaustive solve of the 3×3, both H2 arms; adr-010 V3 double-solve | 9 cells (3×3), hands 5 + 4, commit `4a081d8`+ | — | **complete** | **P1 wins in both arms.** 711,963 configurations enumerated, matching the closed form **exactly at every layer** (V1). V0 512 ✓, V2 asserted on every terminal ✓, V5 checksummed ✓. V3: both methods agree on every position compared (24,460 h1 / 15,376 h2) — **but that is 2–3% of the space, not "every position"; see the V3 caveat below.** [`data/subgame-solutions/3x3-h1.json`](../data/subgame-solutions/3x3-h1.json), [`3x3-h2.json`](../data/subgame-solutions/3x3-h2.json) |
| EXP-002 | 2026-08-05 | H1, H2 | 1 | Exhaustive solve of the 5×3, both H2 arms | 15 cells (5 cols × 3), hands 8 + 7, commit `17aac45` | — | running (h1 launched 2026-08-07) | |
| EXP-003 | 2026-08-05 | — | 1 | Endgame subtree cost at `k = 3…8` on the 5×5: does searching beat storing? | 25 cells, hands 13 + 12; 200 sampled positions per `k`, with and without TT; commit `4a081d8` | 1 | **complete** | **`k* > 8`.** Median nodes to prove one position: k=5 **480**, k=8 **806,474** — against a `k ≤ 5` database of ~1.2 × 10¹⁵ positions (~150 TB). Rule fires "build no database" at every registered `k`. Prediction `k* ≥ 6` **held**. → adr-012 **Option B**. [`results/exp003.json`](../results/exp003.json), [`results/exp003-tail.json`](../results/exp003-tail.json), analysis `scripts/exp003_analysis.py` |
| EXP-004 | 2026-08-05 | — | 1 | Real compressibility of a solved layer: raw / block-RLE / block-Zstd / logic-minimized | 3×3 and 5×3 layers from EXP-001/EXP-002 | — | blocked on EXP-001 | |
| EXP-005 | 2026-08-05 | — | 1 | Don't-care yield and adr-010 V1 reachability gap, per layer | 5×3, 15 cells, hands 8 + 7 | — | registered | |
| EXP-006 | 2026-08-05 | H3 | 1 + 2 | Exact ground truth on the **shipped 5×5**: 500 endgame positions at `k ≤ 8`, solved on demand, as H3's third comparison-set member | 25 cells, hands 13 + 12; `k ∈ {6, 7, 8}`, 500 positions | 2 | registered (blocked on Axis 2) | |

**Registration basis.** EXP-001 through EXP-005 are registered against the H1/H2
text at tag `v0.3-hypotheses`. Any post-lock amendment to that text is recorded
in `docs/research.md` with its reason before it can affect a verdict here.

### EXP-001 — 3×3 exhaustive solve, both arms

- **Objective.** The exact game value of the 3×3 variant and one optimal
  principal variation, **and** the adr-010 V3 artefact: the same variant solved
  twice, by forward alpha-beta and by retrograde sweep, with values agreeing on
  every position. This is the solver's **correctness fixture**, not a strategy
  result — 9 cells is too cramped for the tactics the 5×5 design is about.
- **Hypothesis.** H1, H2.
- **Configuration.** 9 cells, odd. Per
  [adr-011](../docs/adr/adr-011-reduced-variant-parity.md), `a = 4`:
  - **H1 arm** — P1: `{P6, P3-y, P1, P2-adj}` + joker (5 tiles). P2: the same
    four archetypes (4 tiles).
  - **H2 arm** — P1: `{P6, P3-y, P1, P2-adj, P2-skip}` (5 archetypes, no joker).
    P2: `{P6, P3-y, P1, P2-adj}`.

  Both arms: hands exactly exhausted at ply 9, P1 moves last, bound
  **7.12 × 10⁵**, terminal layer **512** (`--cells 9 --hands 5 4`). Identical
  state-space size, so the arms are matched. Deterministic and exhaustive: no
  seed.
- **Decision rule.** 9 is odd, so draws are impossible and the value is exactly
  one of `P1 wins` / `P2 wins`. The run counts as evidence only if it terminates
  by exhaustion (adr-004 R1, `termination: exhausted`); a depth- or time-capped
  run produces no verdict. Gates: adr-010 **V0, V1, V2, V3, V5**. V3 is
  mandatory here — it is why this experiment exists.
- **Expected result.** Pre-registered: **P1 wins in both arms**, i.e. H1
  supported and H2's null (the joker does not change the sign) supported. A P2
  win is the informative outcome and is reported as such, **not re-run**. No
  alternative deck, fill rule, or board size is run for H1/H2 unless registered
  in advance under H6 with its own ID.
- **Power caveat, recorded before the run.** Root-value agreement between the two
  arms is at most 1 bit of evidence against a 50% prior, and 8 of 9 cells on this
  board are boundary cells, so many ordinary placements flip nothing and act as
  joker substitutes. **H2 is not reported from root-value agreement alone**; it
  is reported from the criticality measure (fraction of solved positions whose
  value changes when P1's extra tile is swapped), which requires the database to
  be indexed by hand — a constraint on the solver, not an afterthought.
- **Artefacts.** `data/subgame-solutions/3x3-h1.json`,
  `data/subgame-solutions/3x3-h2.json`. Each header carries board size, the
  literal tile list of both hands, `ordering: internal | az-seeded` and
  `termination: exhausted | budget` (adr-004 R3), and the degree histogram of the
  board.

#### Result (2026-08-05)

**P1 wins with perfect play in both arms.** Sweep 379 s (h1) / 467 s (h2);
forward search 2.4 s / 1.7 s over 115,615 / 78,947 nodes. The asymmetry is
expected — enumerating 711,963 configurations is not the same shape of work as
pruning a tree.

| check | h1 | h2 |
|---|---|---|
| **V0** terminal layer = 2⁹ | 512 ✓ | 512 ✓ |
| **V1** per-layer counts vs closed form | exact at every layer ✓ | exact ✓ |
| **V2** no-draw, asserted on every terminal | ✓ | ✓ |
| **V3** forward vs retrograde | agree on 24,460 | agree on 15,376 |
| **V5** SHA-256 of the value tables | `9a16d65a…` | `307e99b8…` |

The enumeration independently reproduced **711,963** configurations, matching
the 7.12 × 10⁵ that adr-004 and adr-010 have carried since Phase 2 — and
matching `scripts/layer_profile.py` layer by layer with no tolerance, which is
what the adr-010 Phase 3 amendment turned V1 into.

**This is a fixture result and is not an H1 or H2 verdict.** 9 cells is too
cramped to carry a strategy claim (adr-004), and the pre-registered power caveat
stands: agreement between two binary root values is at most 1 bit against a 50%
prior, and on this board 8 of 9 cells are boundary cells, so many ordinary
placements flip nothing and act as joker substitutes. H2 is reported from the
criticality measure, not from the two arms agreeing. The Verdicts table in
`docs/research.md` stays empty until Phase 5.

#### ⚠ Open — V3's coverage falls short of what adr-010 asks

adr-010 V3 requires the two methods to agree on the **game-theoretic value of
every position**. This run compared **24,460 of 711,963** (3.4%) and 15,376
(2.2%). The shortfall is not a defect in the script: alpha-beta only *visits*
what it does not prune, so positions it never reached have no forward value to
compare against. No amount of engineering closes that while the search prunes.

Three ways out, undecided as of 2026-08-05:

1. **Amend adr-010** so V3 reads "every position the forward search visits".
   Free, honest, and weaker than the ADR promised.
2. **Disable pruning for the V3 run.** The forward search becomes plain minimax
   and visits far more; costs time, changes no ADR text.
3. **Sample reachable configurations** and forward-solve each independently.
   Covers the space uniformly rather than following what pruning left — but that
   is sampling, which makes it V4 in substance, not V3.

Recommended: measure (2) first, and amend under (1) only if the coverage is
still far from "every position". An amendment informed by a number beats one
made for convenience.

#### Amendment (2026-08-07) — option (2) measured, and it exposed an instrument defect

Option (2) was run: `pypy scripts/exp001_solve_3x3.py --arm h1 --no-prune
--no-write`, unpruned forward pass, on commit `17aac45`.

**Coverage rose from 3.4% to 46.2%** — 328,884 of 711,963 configurations —
at 314,387,787 nodes and 1,286 s forward (sweep 94.7 s under PyPy, against
379 s under CPython). The value was again **P1 wins** and the sweep's checksum
was again `9a16d65a…`, byte-identical to the pruned run: **no table, no value,
and no earlier result is affected by anything below.**

**What broke.** The run printed `DISAGREE`. Every reported problem read
`an UPPER bound of 1 is not extremal`, and **not one was a value mismatch**.
That is `check_v3`'s own precondition guard firing, not the two solvers
disagreeing.

**Mechanism, read from the source rather than inferred from the symptom.**
`Solver.prune=False` disabled the beta cutoff but left the window narrowing in
place: children were still searched at `(-beta, -alpha)` (`solver/minimax.py`,
the `_negamax` child call). Without a cutoff, `alpha` reaches `WIN` and the
remaining children are searched at `alpha == beta`; two plies down a node is
entered with `alpha = WIN`, and if its value is `WIN` then `value <= alpha`
flags it **UPPER of WIN** — an upper bound on the maximum, which constrains
nothing. V3 correctly refuses to compare a vacuous bound, so those entries were
counted as problems and skipped. The guard did exactly what its docstring said
it was for.

**Fix.** `prune=False` now also stops the narrowing: every node is searched at
`(LOSS, WIN)`. `prune=True` is untouched and byte-identical, so EXP-002 (whose
V4 uses the pruned solver) is unaffected. Every stored bound is then extremal
again — UPPER of `LOSS` or LOWER of `WIN` — which is the invariant V3 reads the
table on.

**Probe.** `tests/test_minimax.py::test_unpruned_stores_only_extremal_bounds`
asserts the invariant directly on an unpruned solve, and
`test_unpruned_reaches_more_positions_than_pruned` pins the reason the mode
exists. The first fails on the pre-fix code, which is the point — a probe that
passes either way would have proved nothing.

**Recovery.** Nothing to heal: the sweep side never ran through the defect and
the checksums match, so the only affected unit is the unpruned forward pass
itself, which is deterministic and simply re-runs. The measured 46.2% is a
**lower bound** on what the fixed run will compare, since the discarded entries
become comparable.

**The adr-010 V3 decision stays open** pending the re-run. 46.2% is already an
order of magnitude better than 3.4% and still not "every position", so option
(1) — amending V3 to read "every position the forward search visits" — remains
the likely landing place. It should be decided on the fixed number, not this
one.

### EXP-002 — 5×3 exhaustive solve, both arms

- **Objective.** The exact game value of the 5×3 variant. This is the
  **strategically meaningful** exact solve and it carries the H1/H2 partial
  verdicts.
- **Supersedes the 4×4.** Per [adr-011](../docs/adr/adr-011-reduced-variant-parity.md)
  (Accepted 2026-08-05) the previously registered 4×4 target is withdrawn:
  16 cells is even, so draws are possible and no tie-break rule exists.
- **Hypothesis.** H1, H2.
- **Configuration.** 15 cells (5 columns × 3), odd. `a = 7`:
  - **H1 arm** — P1: `{P6, P3-y, P1, P2-adj, P2-skip, P2-opp, P3-fan}` + joker
    (8 tiles). P2: the same seven archetypes.
  - **H2 arm** — P1: those seven plus `P3-tri` (8 archetypes, no joker). P2: the
    same seven.

  Both arms: hands exactly exhausted at ply 15, P1 moves last, bound
  **1.751 × 10¹⁰**, terminal layer **32,768** (`--cells 15 --hands 8 7`).
  Identical state-space size. Automorphism group measured before the run with
  `scripts/check_symmetry.py 5 3` and recorded in the artefact — expected to be
  the same Z/2 mirror as the 5×5 (A↔E, B↔D, C fixed).
  Deterministic and exhaustive: no seed.
- **Decision rule.** As EXP-001, gates adr-010 **V0, V1, V2, V4, V5, V6**. V4's
  sample size and seed are recorded here before the run. Additionally a
  **principal-variation audit**: the value of every position on the optimal PV
  from the root, plus the root value under each distinct first move, is
  independently re-derived by direct forward search. V4 bounds the *rate* of
  errors in the database; only the PV audit targets the number actually
  reported.
- **If the run does not complete**, the honest report is the deepest layer fully
  resolved and the storage footprint reached — **not** a partial value. Note that
  a retrograde sweep resolves high `t` first, so a stall leaves the root
  untouched and the artefact carries *zero* information about H1/H2. A stalled
  run may not be presented as a trend.
- **Resource budget.** Peak co-resident working set is layers `t = 8` and `t = 9`
  of the profile; recorded with a disk figure and a fallback before the run
  starts.
- **Expected result.** Pre-registered: **P1 wins in both arms**. Recorded before
  the run so that a P2 win cannot be retrofitted into "as expected", and **not
  re-run** under a different configuration if it comes out the other way.
- **Artefacts.** `data/subgame-solutions/5x3-h1.json`,
  `data/subgame-solutions/5x3-h2.json`, headers as EXP-001.

### EXP-003 — endgame subtree cost: does searching beat storing?

- **Objective.** Find the crossover `k*` at which materialising an endgame
  database beats exact forward search, on the shipped 5×5. This decides
  [adr-012](../docs/adr/adr-012-endgame-database-storage.md) between Options A
  and B.
- **Hypothesis.** — (exploratory; it constrains H3's comparison set).
- **Configuration.** 25 cells, hands 13 + 12. For each `k = 3…8`: 200 positions
  sampled uniformly from legal play at ply `25 − k` (reached by random playout),
  solved exactly by alpha-beta, **with** and **without** a transposition table.
  Report node counts and wall time as distributions, not means. **Seed: 1.**
- **Decision rule, pre-declared.** If the **median** exact search at a given `k`
  costs under **10⁶ nodes**, no database is built for that `k`. `k*` is the
  smallest `k` whose median exceeds that. If `k* > 5`, adr-012 Option B is
  adopted and Phase 3 ships no endgame database — with the consequence, recorded
  in adr-012, that H3 loses its 5×5 endgame-layer comparison member.
- **Expected result.** Pre-registered: `k* ≥ 6`, i.e. the roadmap's `k ≤ 5` target
  is not worth materialising. Precedent: Othello was weakly solved at 36 empty
  squares with no endgame database at all (Takizawa 2023).
- **Known sampling bias, recorded rather than fixed (2026-08-05).** Random
  playout does **not** sample uniformly from reachable positions — it samples
  uniformly from random-play *trajectories*, which is a different distribution.
  More specifically, positions arising from random play may be systematically
  easier or harder to solve than those a real search meets, which arise from
  *good* play. The method stays as registered because this experiment measures
  **cost**, not value, and changing the sampler after registration is the thing
  pre-registration exists to prevent. The limitation is carried with the result;
  it is not corrected in analysis.
- **Each sampled position gets a fresh transposition table.** Sharing one across
  samples would amortise work between them — which is precisely what a *database*
  does — and would bias the comparison toward "searching is cheap". A fresh table
  gives search its worst case, so a result favouring search is conservative.
- **Censoring.** A sample that exceeds `--max-nodes` is recorded at the budget
  and counted separately. A median computed over censored samples is a **lower
  bound**, which is sufficient for the decision rule (the rule only asks whether
  the median exceeds 10⁶) but must be reported as such.

#### Result (2026-08-05, commit `4a081d8`)

Complete registered sweep, `k = 3…8`, 200 positions per `k` per arm, seed 1.
Median nodes to prove one position exactly:

| `k` | ply | median (TT) | p90 (TT) | median (no TT) | TT gain |
|--:|--:|--:|--:|--:|--:|
| 3 | 22 | 18 | 60 | 18 | 1.03× |
| 4 | 21 | 126 | 373 | 134 | 1.07× |
| 5 | 20 | **480** | 1,735 | 560 | 1.17× |
| 6 | 19 | 6,660 | 24,476 | 9,742 | 1.46× |
| 7 | 18 | 20,024 | 105,897 | 32,523 | 1.62× |
| 8 | 17 | **806,474** | 2,683,470 | 1,736,922 | 2.15× |

**Verdict: `k* > 8`.** The rule fires "build no database" at every registered
`k`. The pre-registered prediction `k* ≥ 6` **held**. adr-012 **Option B** is
taken: no endgame database is materialised.

The headline comparison is not close. The roadmap's `k ≤ 5` target is
~1.2 × 10¹⁵ positions, ~150 TB at one bit — and an exact search there costs
**480 nodes**. Twelve orders of magnitude, not a constant factor.

**Secondary finding, not registered in advance and reported as exploratory.**
The transposition table's value *grows* with `k`: 1.03× at `k = 3` rising to
2.15× at `k = 8`. Within a single deep-endgame search there is almost no path
re-convergence — the subgame graph is nearly a tree — and re-convergence only
appears as empty cells accumulate. Note this does **not** settle the database
case by itself: a database sells reuse across *different* roots, which is a
different quantity from re-convergence within one search.

Median growth per layer: 7.0× · 3.8× · 13.9× · 3.0× · 40.3×, geometric mean
**8.5×**. Extrapolating one layer puts `k = 9` near 6.9 × 10⁶ — but that is an
extrapolation, not a measurement, and `k*` is reported as `> 8`.

**Qualification carried with the verdict.** `k = 8`'s median (806,474) sits
within 1.25× of the threshold, and the artefacts persist only aggregates, so
there is **no interval on any median**. The branch taken at `k = 8` and the exact
location of `k*` are therefore provisional. The decision that actually matters —
"do not build for `k ≤ 5`" — is unaffected: it clears the threshold by three
orders of magnitude and no plausible sampling error touches it.

#### Amendment (2026-08-05) — an instrument defect found by the analysis, not by the run

The run's own console output printed `cens 0` for every `k`, because
`scripts/exp003_endgame_cost.py`'s censored column showed **only the with-TT
arm**. The `k = 8` no-TT arm in fact had **1 of 200** samples pinned at the
20,000,000-node budget. The JSON recorded it correctly per arm, which is the
only reason it was recoverable, and `scripts/exp003_analysis.py`'s validity
guard caught it on first execution.

- **Units affected:** one sample, `k = 8`, `without_tt` arm.
- **Impact:** none on the verdict. The rule reads the **with-TT median**, and
  that arm is uncensored at every `k`. In the affected arm, one censored sample
  out of 200 cannot reach the median (the 100th sorted value) or the p90 (the
  180th); it pins only `max`, which is therefore a lower bound (≥ 2 × 10⁷).
- **No re-run.** The data on disk is correct; only the console display was
  wrong. Equivalence argument: the JSON is written from the same `Sample`
  objects the display reads, `censored` was recorded per arm correctly, and no
  statistic the rule consumes was censored.
- **Fix:** the column now prints `with/without` for both arms. Censoring that a
  run can hide is worse than censoring it reports.
- **Second fix, in the other direction:** the first analysis guard hard-failed on
  *any* censoring, which would have discarded a usable result. The criterion is
  now the producer's own `median_is_lower_bound` (censoring past half the
  samples), with the individually affected statistics named.
- **Regression test:** `tests/test_exp003_reporting.py` pins both — that the
  column reports both arms, and that sub-median censoring warns while
  past-median censoring refuses.
- The display fix landed **after** commit `4a081d8`, which is the instrument as
  it ran. The `Config / commit` field points at `4a081d8` deliberately.

### EXP-004 — real compressibility of a solved layer

- **Objective.** Measure bits/position achievable on an actual FLIPHEX layer,
  rather than importing a ratio from checkers or Syzygy where the index is
  material-based and the don't-care set is locally decidable.
- **Hypothesis.** —
- **Status: blocked** on EXP-001 (needs a solved layer to compress).
- **Configuration.** Every layer of the solved 3×3, then of the 5×3. Four
  encodings: raw bit array, block-RLE, block-Zstd, logic-minimized. Each measured
  at a stated block size and reported with **probe latency**, not compression
  ratio alone — the objective is bytes-touched-per-probe, not ratio.
  Deterministic: no seed.
- **Decision rule.** Chooses between adr-012 Options A and C, and calibrates the
  largest `k` that fits available disk. No pre-declared threshold: this is a
  measurement, not a test.

### EXP-005 — don't-care yield and the V1 reachability gap

- **Objective.** Two things at once: the fraction of the closed-form bound that
  has **no legal predecessor** (the only don't-care source available, per
  adr-012 decision 7), and adr-010 **V1's** measurement of the gap between the
  bound and true reachability.
- **Hypothesis.** —
- **Enabled by** [adr-011](../docs/adr/adr-011-reduced-variant-parity.md) and
  [adr-012](../docs/adr/adr-012-endgame-database-storage.md) decision 7.
- **Configuration.** 5×3, 15 cells, hands 8 + 7. For each layer `t`, count
  configurations with no legal predecessor, one step back. Deterministic and
  exhaustive: no seed.
- **Decision rule.** If the yield is under **20%**, don't-cares are dropped from
  the adr-012 design entirely. **The reachability count is recorded before any
  don't-care filling** — filling destroys the distinction between "unreachable"
  and "computed", and it cannot be recovered afterwards.
- **Calibration note, pre-registered.** V1 is **not** a pass/fail gate as adr-010
  currently words it. The closed-form bound counts configurations consistent with
  the invariants, and a correct reachable-closure enumerator disagrees with it by
  a factor of **exactly 2 at layer `t = 1`** — the formula's `2^t` counts
  colourings the mover's colour forbids (at `t = 1` on the 3×3: formula
  `9 × 2 × 13 = 234`, reachable `9 × 13 = 117`). Before either solve is cited,
  adr-010 V1 must be restated as either (a) **exact per-layer equality** against
  the configuration space, in which case it is a genuine `perft` and any
  inequality voids the run, or (b) a **one-sided measurement**
  `count_enum ≤ count_formula`, in which case it is not a gate. This experiment
  supplies the calibration for (b).

#### Amendment (2026-08-07) — the calibration clause's premise is now closed

The adr-010 **Phase 3 amendment took option (a)**: V1 is exact per-layer
equality against the configuration space, a genuine `perft`, and EXP-001 passed
it exactly on both arms. So the clause above no longer describes an open choice.
What survives of it is the *measurement*, which is this experiment's own
objective and is unchanged: the closed form and the reachable set are different
quantities, V1 gates the first, and EXP-005 measures the second. The 2× figure
at `t = 1` stays as the calibration anchor — it is now pinned as a test rather
than a note (`tests/test_reachable.py::test_layer_one_is_exactly_half`).

**Instrument** (written 2026-08-07, before the run, on commit `17aac45` plus
`solver/reachable.py`): predecessors are counted **forward**, not by inverting
the flip rule. The pass walks every configuration of layer `t-1`, generates
every legal move with the machinery `solver/packed_sweep.py` already uses, and
marks the successor's bit; what stays unmarked has no predecessor by
construction. Inverting the rule would have been a second hand-written statement
of it, which is exactly what adr-010 V3 exists to prevent. One bit per
configuration, one layer resident: the 5×3's largest layer is 5.02 × 10⁹
configurations, so **628 MB** peak.

Unlike the sweep, this must not stop at the first successor — a short-circuit
would undercount predecessors and inflate the orphan count — so the loop is
written out rather than shared, and
`tests/test_reachable.py::test_marking_matches_the_reference_move_generation`
checks the marked set against `legal_moves`/`apply_move`/`LayerIndex` on every
layer of both 5×1 arms.

### EXP-006 — exact ground truth on the shipped 5×5, for H3

- **Objective.** Give H3 a comparison-set member on the **shipped game** rather
  than on reduced boards only. Replaces the retrograde endgame layers the Phase 2
  amendment assumed, which `EXP-003` showed are not worth materialising.
- **Hypothesis.** H3.
- **Status.** Registered 2026-08-05, **before Axis 2 exists**. That ordering is
  the whole point — a comparison set fixed after seeing the learner is not a
  comparison set. It runs in Phase 5.
- **Why this is affordable, measured rather than assumed.** `EXP-003` puts the
  median exact search at 6,660 nodes (`k = 6`), 20,024 (`k = 7`) and 806,474
  (`k = 8`). 500 positions at `k ≤ 8` is therefore hours, not a database.
- **Configuration.** 25 cells, hands 13 + 12 (the shipped game, no reduced deck).
  **Seed 2**, deliberately not `EXP-003`'s seed 1: reusing seed 1 would evaluate
  the learner on the exact positions whose cost was used to justify this design.
  Positions are drawn by **random playout** to ply `25 − k`, matching EXP-003's
  sampler and carrying the same registered bias. Stratified: 500 positions split
  evenly across `k ∈ {6, 7, 8}` (166/167/167). `k ≤ 5` is excluded as too shallow
  to discriminate — at 480 nodes the subgame is nearly forced.
- **Positions come from random play, not from the learner's play.** This is a
  pre-declared choice, not an oversight. Sampling from Axis 2's own self-play
  would test the learner on its own distribution — a different and arguably more
  interesting claim, but one that lets Axis 2 choose the exam. Registered here as
  the *independent* set; a learner-distribution version, if wanted, needs its own
  ID and must not be substituted for this one.
- **Measure.** For each position: the exact game value, and whether the learned
  policy's chosen move **preserves** it. Agreement rate with a Wilson 95% CI, per
  `k` and pooled.
- **Decision rule.** H3's clause on this member is satisfied only if the
  agreement rate's Wilson lower bound exceeds a pre-declared floor, fixed here as
  **0.90**. Below that, H3 is reported as failing on the shipped game regardless
  of how it does on 3×3 and 5×3 — the reduced boards cannot rescue it, since
  carrying the shipped game is the entire reason this member exists.
- **Provenance is structural, not audited.** `solver/minimax.py` proves or raises
  `BudgetExceededError`; it has no evaluation function and no depth limit, so
  every ground-truth value here satisfies adr-004 R1 `termination: exhausted` by
  construction. Any position that cannot be proved is reported as excluded, with
  its count — never silently replaced by a fresh sample.
- **Artefacts.** `data/ground-truth/5x5-endgame-seed2.json`, with the adr-004 R3
  header fields.

## Planned

Sketched in Phase 0 so the phases have targets. IDs are allocated on
registration, not here.

| Phase | Experiment | Hypothesis |
|---|---|---|
| 3 | Exhaustive solve of the 3×3 variant; record game value and a principal variation | H1, H2 |
| 3 | Exhaustive solve of the 3×3 at the *full* deck (2.3 × 10⁹), as a stretch beyond the adr-011 reduced fixture | H1, H2 |
| 3 | Retrograde endgame database, `k ≤ 5` empty cells on 5×5 | H3 |
| 3 | Alpha-beta + endgame DB vs random and heuristic, 1000 games | — |
| 3 | **adr-010 V3** — 3×3 solved twice (forward alpha-beta vs retrograde), values must match on every position | — |
| 3 | **adr-010 V4** — random-sample re-derivation of 5×3 entries by direct search, database not consulted | — |
| 4 | AZ training run, seed 1, to 1M self-play positions | H3 |
| 4 | AZ training run, seed 2 (convergence replication) | H3 |
| 4 | Factored vs flat policy head (adr-005 risk R5) | — |
| 5 | First-player win rate, 20 seeds × 1000 games, Wilson CI | H1 |
| 5 | Joker-less variant, matched protocol | H2 |
| 5 | AZ vs solver at matched depth caps | H3 |
| 5 | Sensitivity: MCTS simulations, `c_puct`, temperature schedule | — |
| 6 | State-space and game-tree bounds; cross-game comparison table | H4 |
| 6 | Archetype placement frequency and win contribution | H5 |
| 6 | **Tile criticality** — for each archetype, the fraction of solved 5×3 positions whose value changes when that tile is removed from the hand | H5 |
| 6 | **Mirror-optimality rate** — on solved positions where the Z/2 mirror is a valid game symmetry (both `P3-y` placed), the fraction of optimal moves whose mirror image is also optimal | H5, H6 |
| 6 | **First-player advantage curve** — fraction of solved positions at each ply `t` won by the player to move, 5×3 | H1 |
