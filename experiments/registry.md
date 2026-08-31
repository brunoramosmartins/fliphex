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
| EXP-002 | 2026-08-05 | H1, H2 | 1 | Exhaustive solve of the 5×3, both H2 arms | 15 cells (5 cols × 3), hands 8 + 7, commit `17aac45` (h1, superseded) / h1 re-run `2432572` / crash-resume build (h2) | — | **both arms complete** | **P1 wins in both arms.** V0–V6 pass on both; V1 exact on all 16 layers. Sweeps 30.95 h (h1 re-run) / 34.25 h. **PV audit part 1: 15 of 15 agree, 0 unproven**; part 2 stopped at opening 34/540 on its measured slope and replaced by the layer-to-layer recurrence check (layers 0–3, 515,229 positions, 0 problems). V4/V6 now report coverage — V4 has **no search evidence at `t = 0..5`**; V6 covers `t ≥ 2` only. h1's re-run reproduced its V5 digest `ab2620e1707f983f…` bit-for-bit, discharging the adr-010 2026-08-07 replay. **H2's registered measure is computed: criticality 17.07%**, with 10,258,229,474 cross-arm positions compared and **0 mismatches**. [`5x3-h1.json`](../data/subgame-solutions/5x3-h1.json), [`5x3-h2.json`](../data/subgame-solutions/5x3-h2.json), [`criticality`](../results/exp002-criticality-5x3.json) |
| EXP-003 | 2026-08-05 | — | 1 | Endgame subtree cost at `k = 3…8` on the 5×5: does searching beat storing? | 25 cells, hands 13 + 12; 200 sampled positions per `k`, with and without TT; commit `4a081d8` | 1 | **complete** | **`k* > 8`.** Median nodes to prove one position: k=5 **480**, k=8 **806,474** — against a `k ≤ 5` database of ~1.2 × 10¹⁵ positions (~150 TB). Rule fires "build no database" at every registered `k`. Prediction `k* ≥ 6` **held**. → adr-012 **Option B**. [`results/exp003.json`](../results/exp003.json), [`results/exp003-tail.json`](../results/exp003-tail.json), analysis `scripts/exp003_analysis.py` |
| EXP-004 | 2026-08-05 | — | 1 | Real compressibility of a solved layer: raw / block-RLE / block-Zstd / logic-minimized | 5×3-h2, all 16 layers, 4,096-byte blocks | — | **complete (rule moot)** | **2.00 bits/position raw; block-RLE 3.04×, block coder 9.10×**, logic-minimised absent (needs EXP-007's closure). The registered rule chose between adr-012 Options A and C; adr-012 chose **B**, so it is recorded as moot rather than reinterpreted. zlib substituted for zstd (absent), flagged in the artefact. [`exp004-compressibility-5x3.json`](../results/exp004-compressibility-5x3.json) |
| EXP-005 | 2026-08-05 | — | 1 | Don't-care yield and adr-010 V1 reachability gap, per layer | 5×3, 15 cells, hands 8 + 7 | — | registered; 3×3 pilot run | **The registered rule runs on the 5×3** and has not. The 3×3 pilot returned **3.28%** orphans (23,371 of 711,963) and is superseded on its own terms by EXP-007's exact closure: [`exp005-3x3-h1.json`](../results/exp005-3x3-h1.json), [`exp005-3x3-h2.json`](../results/exp005-3x3-h2.json). |
| EXP-006 | 2026-08-05 | H3 | 1 + 2 | Exact ground truth on the **shipped 5×5**: 500 endgame positions at `k ≤ 8`, solved on demand, as H3's third comparison-set member | 25 cells, hands 13 + 12; `k ∈ {6, 7, 8}`, 500 positions | 2 | registered (blocked on Axis 2) | |
| EXP-008 | 2026-08-30 | — | 1 | Exact agent strength on the shipped 5×5 with no endgame database | 25 cells, hands 13 + 12; 2M-node budget, `search_below_k = 8`; 250 games per opponent × seat | 5 | **complete** | **Exit criterion NOT met.** vs random **98.0%** [96.4, 98.9] ✅; vs heuristic **61.0%** [56.7, 65.2] ❌. `proved_rate` **32%** — no rate may be quoted without it. Post-hoc control: between two heuristics the **first** seat wins only 40.0%, a property of the greedy agent and **not** an H1 input; it does not baseline the P2 arm (seeds unmatched by seat). [`exp008-agent-strength.json`](../results/exp008-agent-strength.json) |
| EXP-009 | 2026-08-30 | — | 1 | WIN/LOSS mix per layer: the parity split, measured instead of inferred | 5×3-h1, all 16 layers, exhaustive | — | **complete** | **Uniformity breaks at `t = 5`.** Layers 0–4 are uniform — every one of the 12,841,920 configurations at `t = 4` is a P1 win, every one of the 713,440 at `t = 3` a P2 loss — then the parities converge monotonically to 50/50. Confirms EXP-002's criticality boundary and EXP-004's compression ratios from a third direction, and retires the parity question. 70.8 s. [`exp009-parity-5x3-h1.json`](../results/exp009-parity-5x3-h1.json) |
| EXP-007 | 2026-08-07 | — | 1 | True reachable closure per layer, and what one-step-back predecessor counting misses | 5×3, 15 cells, hands 8 + 7, both arms | — | registered; 3×3 pilot run | **The registered rule runs on the complete 5×3 only** and has not. The 3×3 pilot is instrument shakedown, not the result: [`exp007-3x3-h1.json`](../results/exp007-3x3-h1.json), [`exp007-3x3-h2.json`](../results/exp007-3x3-h2.json). Row added retrospectively on 2026-08-30 — the experiment was registered in full below but never listed here. |
| EXP-010 | 2026-08-30 | — | 2 | Deduplicated (by-position) MCTS expansion against the naive by-action tree, with a multiplicity-corrected control | 5×3-**h2** (V5 `51192b4d…`), 3,000 WIN positions stratified over `t = 5..14`, uniform prior + rollout leaves, 3 arms, primary at budget 400 | 17 | **registered, revised after red-team** (blocked on `az/mcts.py`) | |
| EXP-011 | 2026-08-30 | — | 2 | Is the factored policy head too costly *in the pipeline*? (risk R5) | 5×3-**h2** (V5 `51192b4d…`), 2,500 WIN positions, 2,000 train / 500 held out, 5 seeds per arm, primary = top-1 optimality after 400 PUCT sims | 23 | **registered, revised after red-team** (blocked on `az/mcts.py` + `az/network.py`) | |

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

#### Amendment (2026-08-07) — the fixed re-run, and what the residue actually is

Re-run on commit `a1a7eb1` (the window fix), h1 arm, PyPy:
`data/subgame-solutions/3x3-h1-unpruned.json`.

| | pruned | unpruned, pre-fix | unpruned, fixed |
|---|---|---|---|
| compared | 24,460 (3.4%) | 328,884 (46.2%) | **604,347 (84.9%)** |
| outcome | agree | DISAGREE (the guard) | **agree** |
| forward nodes | 115,615 | 314,387,787 | 307,340,818 |
| sweep / forward | 379 s / 2.4 s | 94.7 s / 1,286.1 s | 116.5 s / 1,438.6 s |

Fewer nodes than the pre-fix unpruned run, which is the expected direction: with
a single window every stored bound applies at every probe, so the table cuts more
often. `V0`, `V1`, `V2`, `V5` unchanged; checksum still `9a16d65a…`; the
principal variation is the same line.

**The remaining 15.1% is not a shortfall in V3.** An unpruned search with a
transposition table visits every position **reachable from the opening**, once.
What it does not compare are configurations no game ever reaches — which is
precisely the quantity EXP-005 measures. So the three options recorded on
2026-08-05 were framed on a false premise: option (1) is not a weakening of
adr-010 but the *correct* statement of what V3 can mean, and under it 84.9%
would be 100% of what exists to compare.

**Held open pending one cheap number.** EXP-005 on the 3×3 gives the
unreachable-configuration floor for this exact board. Orphans are a lower bound
on unreachability — a configuration whose only predecessors are themselves
unreachable is also unvisitable and the one-step test misses it — so the
prediction is **≤ 15.1%**, and the closer it lands the more the amendment carries
itself. The adr-010 V3 amendment is drafted only after that number exists; an
amendment argued from a number beats one argued from a plausible story about a
number.

#### Amendment (2026-08-07, later) — the prediction failed, and the residue was the instrument

EXP-005 on the 3×3 returned **3.28%** orphans (23,371 of 711,963), not the
≈15.1% predicted above. The prediction is recorded as failed rather than
adjusted: orphans account for less than a quarter of the V3 residue, so
"the missing 15.1% are unreachable" was **wrong**.

Reading the source instead of the model: `check_v3` iterates `tt._slots`, and
`TranspositionTable` is direct-indexed — `self._slots[state.zobrist & self._mask]`,
one entry per slot, replace on collision. So "positions compared" is the count of
**surviving table entries**, capped by retention rather than by what the search
visited. At 2²¹ slots against ~7 × 10⁵ positions, collision loss is of the order
of the residue.

**Discriminating run, predicted before it was launched.** Re-run at `--tt-bits 24`.
Prediction band 94.8–97.9%, with a hard falsifier: EXP-005 puts a ceiling of
**96.72%** on any search, so a coverage *above* it would mean orphans were being
probed — impossible by definition — and would indict one of the two instruments.

**Result: 679,202 of 711,963 = 95.4%, values agreeing.** Inside the band, below
the ceiling; the falsifier did not fire, and the two instruments are mutually
consistent.

| | configurations | % of total | % of reachable |
|---|---|---|---|
| total | 711,963 | 100% | |
| orphans (never probeable) | 23,371 | 3.28% | |
| **reachable ceiling** | 688,592 | 96.72% | 100% |
| compared at 2²¹ | 604,347 | 84.9% | 87.8% |
| **compared at 2²⁴** | **679,202** | **95.4%** | **98.64%** |

**Correction, twice.** The decomposition first written here — 3.28 points
unreachable, 1.36 points collision loss — was wrong on the second term: the 2²⁴
run reported **3,300 replacements**, so collisions cannot account for 9,390
configurations. The repair written next — "≥ 6,090 never visited, so true
unreachability is ≥ 4.14%" — was also wrong, because it measured the gap against
the *one-step* ceiling. Both are superseded by EXP-007's exact closure, computed
the same evening:

| | configurations | share |
|---|---|---|
| configuration space | 711,963 | 100% |
| unreachable from the opening (exact) | 27,860 | 3.91% |
| **reachable** | 684,103 | 96.09% |
| **compared** | 679,202 | **99.28% of reachable** |
| residue | 4,901 | 0.72% of reachable |

The residue accounts for itself exactly: **511** reachable terminal
configurations, which `_negamax` returns from before reaching `store` and which
are therefore structurally absent from the table, plus **4,390** non-terminal
positions that shared a slot — 3,300 evicted (the reported `replacements`) and
~1,090 *refused entry*, because `store` keeps the deeper of two entries on a
conflict and drops the shallower without recording it. 511 + 4,390 = 4,901.

The refusals matter beyond the arithmetic: `replacements` is a **lower** bound on
coverage loss, not a measure of it, and a first pass at this decomposition
assumed otherwise and came up 1,090 short. Both effects are birthday collisions
and shrink with table size.

Both wrong numbers are kept above rather than deleted. The pattern in them is
the lesson: each was a plausible arithmetic on a ceiling that had not been
measured, and each survived until an instrument was built to measure it.

**Side effect worth recording.** Node count fell from 307,340,818 at 2²¹ to
26,287,459 at 2²⁴ — **11.7×** — for the same values and the same checksum. A
thrashing table does not merely lose entries for V3 to read; it forces the search
to re-prove subtrees it had already proved. The forward pass went from 1,438.6 s
to 121.6 s.

**Decision taken.** adr-010 V3 amended 2026-08-07 — "every position the forward
search reaches, unpruned, with the table sized so retention is not the binding
constraint", reported as three numbers. Options 2 and 3 of 2026-08-05 are closed;
option 1 is superseded, since it would have accepted the 3.4% pruned figure.

**Instrument changes.** `scripts/exp001_solve_3x3.py` gained `--tt-bits` and now
reports table occupancy and replacements beside the coverage — without them the
shortfall reads as a property of the game rather than of the table, which is
exactly the misreading that occurred. The artefact carries `tt_capacity`,
`tt_occupied` and `tt_replacements`, so a stored run identifies its own table
regardless of filename.

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

#### Amendment (2026-08-07) — the h1 arm ran without progress output

The h1 arm was launched on commit `17aac45`, whose observer printed nothing per
layer and left the header prints block-buffered. Redirected to a file that means
**an empty log for the whole run** — on a job measured in hours there is then no
way to distinguish a slow sweep from a hung one, and the peak-working-set clause
above becomes unobservable while it matters.

Fixed for the h2 arm: a flushed line per layer with its configuration count and
elapsed time. The change is **output only** — no sampling, no RNG draw, no
arithmetic is touched, so the two arms remain comparable and the h1 result stands
as produced. Recorded here rather than silently, because the arms now run on
different commits.

The h1 arm was monitored instead by resident set size, which tracks the two
co-resident layers and is therefore a real progress signal on this sweep: RSS
climbs while `t` descends from 15 to 9, peaks near 2.5 GB at `t = 9`, and falls
away after. It is a proxy and is not recorded as a measurement.

> **Retracted 2026-08-09.** The paragraph above is wrong and is kept for the
> record. RSS is **not** a progress signal on this sweep. PyPy does not return
> arena to the OS as layers shrink, so RSS froze at 4,204,888 kB for over five
> hours across four samples, and `minflt` froze with it — both while the run was
> progressing normally. RSS also rose late (to 4.5 GB) from the observer's
> `bytes(values)` copy, not from a larger layer. Nothing outside the process's
> own stdout locates the layer, which is exactly what the missing `flush` cost.

#### Amendment (2026-08-12) — the h2 arm died at 20.8 h, and the instrument gained crash resume

**What happened.** The h2 arm ran on commit `40355de`, completed layers `t = 15`
down to `t = 8`, and died inside `t = 7` when the machine powered off after
20.8 h. Nothing was recoverable: `PackedSweep` held two layers in RAM and wrote
nothing until the end, so the run's own rule applies — *"a retrograde sweep
resolves high `t` first, so a stall leaves the root untouched and the artefact
carries zero information about H1/H2."* It carried none.

~~**The per-layer times in `results/exp002-h2.log` are corrupt and must not be
used.** The log records `t = 8` at 0.96 µs/cfg, which is faster than the
cache-resident `t = 12` (1.15 µs/cfg) while probing a 1.26 GB array at random —
physically impossible. `t = 9` reads 16.3 h and `t = 10` reads faster than the
smaller `t = 11`. The cause is `CLOCK_MONOTONIC` being re-based across WSL2
suspend/resume: one layer absorbs the gap and its neighbours come out deflated.
**Only the layer *order* in that log is evidence.** The usable timings remain
`t = 13`, `t = 12` and `t = 11`, all measured before the first suspend, and they
are what established the cache cliff: 1.31 → 1.15 → **4.50 µs/cfg** as the
probed array crosses this machine's 9 MiB L3 (0.5 MB → 12 MB → 91 MB).~~

> **Retracted 2026-08-13, struck through above.** The times are **not** corrupt.
> The restarted h2 arm reproduced the same alternating pattern on a machine that
> never suspended, and the two arms agree layer for layer: `t = 11` 7,393.8 s vs
> 8,145.2 s (+10.2%), `t = 10` 4,429.5 vs 4,607.4 (+4.0%), `t = 9` 58,791.0 vs
> 59,140.8 (**+0.6%**), `t = 8` 3,885.7 vs 3,824.8 (−1.6%). A re-based clock does
> not reproduce to 0.6% across two runs with different decks. See the parity
> finding below for the mechanism. The `CLOCK_MONOTONIC` concern was a real
> possibility reasoned from a real event, and it was wrong; the h1 log's timings
> are usable after all.
>
> The **cache-cliff claim in the same paragraph is also withdrawn**, as
> unproven rather than as false — see below. It was confounded: `t = 12` → `t = 11`
> is both a cache boundary *and* a parity flip, and the parity term alone
> accounts for the jump.

**Change to the instrument.** `solver/checkpoint.py` (new) persists each
completed layer; `PackedSweep.sweep` gains a `checkpoint=` parameter and resumes
from the lowest layer on disk. `scripts/exp002_solve_5x3.py` gains `--checkpoint`
(on by default, `data/checkpoints/`) and `--no-checkpoint`. The directory is
gitignored: ~4.4 GB per arm, against 915 GB free.

**Why this does not compromise the comparison between arms.** The change is I/O
only — no sampling, no RNG draw, no arithmetic is touched — the same class as the
`flush` change disclosed above. Two properties are pinned by
`tests/test_checkpoint.py` rather than asserted:

- **V5 survives a resume byte for byte.** Every completed layer is retained, and
  a resumed run re-feeds them into a fresh SHA-256 in the original sweep order.
  The tempting cheaper design — one digest per layer, combined at the end — was
  rejected because it would silently redefine what V5 measures between h1 and h2.
- **The RNG state travels**, so a resumed run draws the same V4 and V6 samples an
  uninterrupted run would have drawn. Without that a resume re-seeds the sampling
  and the arms stop being comparable on evidence the registry pins by seed.

Layers are written before the manifest that names them, and every write is
`os.replace` over a temporary file, so a torn write is invisible to resume rather
than resumed into silently.

**Timing on a resumed run is reported as partial, never summed.** The earlier
session's elapsed time dies with its process, and layers differ in cost by an
order of magnitude, so the pieces are not addable. The runner prints "this
session only", suppresses the `cfg/s` figure entirely, and the artefact carries
`resumed_from_layer`. **A resumed h2 therefore yields no clean wall-clock
number** — h1's 32.38 h stands as the only end-to-end sweep timing, itself
degraded by the lid closures recorded below.

**h2 restarts from zero**, since the dead run left no checkpoint. Third commit
for this arm; recorded here because the arms now run on three different commits.

#### Finding (2026-08-13) — sweep cost alternates with the parity of `t`, and why

The restarted h2 arm ran to a complete sweep with per-layer output, and the
profile is not smooth. It alternates, hard, by the parity of `t`:

| `t` | to move | WIN | LOSS | µs/cfg |
|---:|---|---:|---:|---:|
| 12 | P1 | 91.02% | 8.98% | 1.168 |
| 11 | P2 | 53.46% | 46.54% | **4.955** |
| 10 | P1 | 93.79% | 6.21% | 1.274 |
| 9 | P2 | 46.96% | 53.04% | **11.775** |
| 8 | P1 | 97.07% | 2.93% | 0.948 |
| 7 | P2 | 34.38% | 65.62% | **21.351** |
| 6 | P1 | 99.71% | 0.29% | 0.483 |
| 5 | P2 | 3.88% | 96.12% | **32.302** |
| 4 | P1 | 100.00% | 0.00% | 0.241 |
| 3 | P2 | 0.00% | 100.00% | **39.947** |

**Mechanism.** `PackedSweep`'s inner loop exits at the first losing child, so a
**win** node stops after a couple of probes while a **loss** node examines all
`b(t)` of them. Cost is therefore governed by `P(loss | t)`, not by layer size.
On a board the first player wins, `P(loss)` is low when P1 is to move (even `t`)
and high when P2 is (odd `t`) — so the cost alternates with the parity. A
single-parameter model,

    cost(t) ≈ 0.2 + 0.27 · b(t) · P(loss | t)   µs per configuration

reproduces the whole 40× span from `t = 13` to `t = 3`.

This is the term missing from the model that mis-predicted the h1 runtime by 4×.
That model was `A + C·b(t)`; the correct shape carries `P(loss | t)` as a factor,
and it swings by two orders of magnitude between adjacent layers.

**Provenance.** The WIN/LOSS fractions were counted from the checkpoint layer
files written by `solver/checkpoint.py` — an unplanned benefit of adding crash
resume, and the same artefact `EXP-004` needs. **`t = 3` and `t = 4` are exact**
(the whole layer fits the sample); `t ≥ 5` is the first 8 MB of the layer file,
which is a **prefix of the mixed-radix index and not a random sample**, so those
percentages indicate direction, not layer-wide values. A proper measurement is
cheap now that the layers are on disk and has not been made.

**What this withdraws.** The 2026-08-12 amendment attributed the `t = 12` →
`t = 11` jump (1.17 → 4.96 µs/cfg) to the probed array crossing this machine's
9 MiB L3. That boundary is real, but it coincides with a parity flip, and `b(t)`
also rises 27 → 39 there. `b·P(loss)` goes 2.42 → 18.08, a 7.5× rise against a
4.2× rise in cost — the parity term alone over-explains the jump, leaving no
residual for cache to account for. The cache hypothesis is **not disproved**; it
is **unsupported by this data** and must not be cited as established. Separating
the two needs same-parity comparisons at controlled `b(t)`, which nothing here
provides.

#### Result — h1 arm (2026-08-09)

**`P1` wins the 5×3-h1 with perfect play.** The pre-registered expectation was
"P1 wins in both arms"; h1 holds. `termination: exhausted`, `ordering: internal`,
so the artefact satisfies adr-004 R1. Artefact
[`data/subgame-solutions/5x3-h1.json`](../data/subgame-solutions/5x3-h1.json),
log [`results/exp002-h1.log`](../results/exp002-h1.log).

| gate | outcome |
|---|---|
| V0 terminal layer | 32,768 — ok |
| V1 per-layer counts | **ok**, exact equality on all 16 layers, 17,506,580,337 configurations |
| V2 no-draw | asserted on every terminal |
| V4 sampled re-derivation | 344 agree, 0 disagree, **217 over budget** |
| V5 checksum | `ab2620e1707f983fb0f57b5486062601925ab7fc7d6b5e4eaae856843e4bb22d` |
| V6 mirror | 518 pairs checked, 0 differ, **4,768 sampled but ineligible** |

**Cost.** Sweep 32.38 h at 150,192 cfg/s; V4 a further ~20 h; ~52 h wall-clock
end to end. The pre-run projection was ~13 h — wrong by 4×, with V4 alone
exceeding the whole projection. Root cause in the phase note; in short, the
estimate was made in configurations, and cost per configuration is not constant.

**The timing figures are low-grade measurements and are not a benchmark.** The
run executed in an uncontrolled environment: the laptop lid was closed several
times, so the machine passed through sleep and low-power states during the run.
`time.perf_counter()` is `CLOCK_MONOTONIC` and does not advance across a genuine
suspend, but it does advance during frequency throttling, so 32.38 h includes an
unknown amount of down-clocked execution. The wall-clock figure is worse still.
**Correctness is unaffected** — suspend/resume preserves memory and the
verification gates are indifferent to how long they took — but no scaling claim,
cross-board comparison, or `cfg/s` figure may be built on these numbers without
re-measuring on a quiescent machine.

#### Amendment (2026-08-09) — a registered gate did not run, and two that did report no coverage

**The principal-variation audit was not performed.** The decision rule above
registers it explicitly, and states why it is not redundant with V4: *"V4 bounds
the rate of errors in the database; only the PV audit targets the number actually
reported."* `solver/minimax.py::principal_variation` exists and documents itself
as this audit's input; `scripts/exp001_solve_3x3.py` calls it; **`scripts/exp002_solve_5x3.py`
never does.** The 5×3 therefore passed every gate the instrument implements and
skipped the only registered gate aimed at the value being reported.

Consequence, stated plainly: `P1 wins the 5×3-h1` is **not yet fully verified to
its own registered standard**. It may be reported with that qualification
attached; it may not be cited as an H1 input until the audit runs. The audit is a
forward search, not a second sweep, so it is affordable — and per the adr-010
amendment of 2026-08-07 it takes priority over the digest replay.

**V4 and V6 pass without reporting coverage, which is the V3 lesson recurring.**

- **V4 covered 61.3%** — 217 of 561 samples exceeded the 2,000,000-node budget
  and produced no evidence in either direction. The instrument sets
  `passed: true` because `disagreed == 0`, which is defensible, but a check that
  is silent on 38.7% of its own sample should say so in its verdict.
- **V6 covered 9.8%** — 518 eligible pairs against 4,768 sampled and rejected,
  because adr-008 makes the mirror a game symmetry only once neither hand holds
  `P3-y`. V6 therefore tests the endgame and almost nothing else. This is a known
  consequence of adr-008, now quantified for the first time.

Both should report a coverage figure alongside their verdict, exactly as V3 was
amended to do on 2026-08-07. Not changed here — a gate is not redefined between
the two arms of a running experiment. Filed for the instrument's next revision,
after h2 completes.

#### Result — h2 arm (2026-08-13)

**`P1` wins the 5×3-h2 with perfect play.** The pre-registered expectation was
"P1 wins in both arms"; both arms now hold. Artefact
[`data/subgame-solutions/5x3-h2.json`](../data/subgame-solutions/5x3-h2.json),
log [`results/exp002-h2.log`](../results/exp002-h2.log). `resumed_from_layer:
null` — the arm ran uninterrupted, so its timing is clean and its
`seconds` figure is whole.

| gate | h1 | h2 |
|---|---|---|
| V0 terminal layer | 32,768 ok | 32,768 ok |
| V1 per-layer counts | ok | ok |
| V2 no-draw | asserted | asserted |
| V4 re-derivation | 344 / 0 / **217** over budget | 349 / 0 / **212** over budget |
| V5 checksum | `ab2620e1707f983f…` | `51192b4d403ac1cb…` |
| V6 mirror | 518 pairs, 4,768 ineligible | **518 pairs, 4,768 ineligible** |
| sweep | 32.38 h, 150,192 cfg/s | 34.25 h, 142,004 cfg/s |

**H2 is NOT reported from this.** Both arms agreeing on a root value is one bit.
The registered measure is the **criticality** — the fraction of solved positions
whose value changes when P1's extra tile is swapped — and that is a
position-by-position comparison, not a comparison of two roots. The decision rule
above says so explicitly and is not being reinterpreted now that a convenient
agreement exists.

**The criticality measure is one re-run away from being computable.** The two
arms index the same object: 15 cells, hands 8 + 7, 17,506,580,337 configurations,
the same mixed-radix encoding of cells, colours and spent slots. Criticality is
an XOR and a popcount between the two databases. Only h2's layers survive — h1
ran before `solver/checkpoint.py` existed and its layers were discarded as the
sweep passed them.

**Re-running h1 with `--checkpoint` therefore discharges three registered
obligations at once**, which is the best ratio available on a ~52 h job:

1. the layers the criticality measure needs, and with them H2's actual test;
2. the **digest replay** the adr-010 amendment of 2026-08-07 requires before the
   5×3 value may be cited — it is satisfied exactly when V5 comes back
   `ab2620e1707f983f…`;
3. a clean end-to-end wall-clock, which h1 has never had (lid closures).

**Two observations from the artefacts.**

*V6's two arms are not independent evidence.* Both report **exactly** 518 pairs
checked and 4,768 rejected. Not a defect: seed 3 is registered for both arms, the
hands are the same size, and eligibility turns only on whether `P3-y` has been
played — never on the arrow patterns. Same seed ⇒ same indices drawn ⇒ same
eligibility verdicts. The consequence is that V6 examined *the same positions*
in both arms and the two results do not corroborate each other. V4 does differ
(344/217 against 349/212) because forward-search cost depends on the deck.

*The deck explains the runtime gap.* h2 was 5.8% slower. P1's hand holds 36
distinct (tile, rotation) pairs in h2 against 35 in h1 — `P3-tri` has 2 rotation
orbits where `JOKER` has 1 — so h2 carries **2.9% more branching** on every
even-`t` layer. Same direction, same order of magnitude. The clock is explained
by the deck, not by the machine.

#### Amendment (2026-08-23) — the PV audit's first result, and four runs lost to an unmeasured ceiling

**Part 1 complete, h2 arm: all fifteen PV positions re-derived and agreeing.**
Every position on the sweep's own principal variation was proved by forward
search through `solver/minimax.py`, which shares no code with the packed sweep,
and **all fifteen agree — zero disagreements, zero unproven**. This is the first
evidence the registered PV audit has produced on either arm, and it targets
exactly the position the amendment of 2026-08-09 says the reported number lives
at. Artefact
[`results/exp002-pv-audit-5x3-h2.json`](../results/exp002-pv-audit-5x3-h2.json).

| ply | sweep | forward | nodes | | ply | sweep | forward | nodes |
|---|---|---|---|---|---|---|---|---|
| 0 | WIN | agree | 1,400,240,037 | | 8 | WIN | agree | 65,711 |
| 1 | LOSS | agree | 611,392,685 | | 9 | LOSS | agree | 49,895 |
| 2 | WIN | agree | 69,261,302 | | 10 | WIN | agree | 3,403 |
| 3 | LOSS | agree | 69,261,301 | | 11 | LOSS | agree | 1,315 |
| 4 | WIN | agree | 9,532,471 | | 12 | WIN | agree | 54 |
| 5 | LOSS | agree | 9,532,470 | | 13 | LOSS | agree | 24 |
| 6 | WIN | agree | 995,743 | | 14 | WIN | agree | 2 |
| 7 | LOSS | agree | 995,742 | | | | | |

**What the fifteen checks actually cover, stated precisely.** Each WIN ply costs
its LOSS child's proof **plus exactly one node** — 69,261,302 against 69,261,301,
9,532,471 against 9,532,470, and so on down the line. A winning node is proved by
trying the PV move first and cutting, so its search subsumes the next ply's. The
line therefore rests on **eight distinct proofs** (the odd plies) with seven
one-node confirmations on top. Each still ran under its own fresh table, so they
remain independent *executions* — but the cost, and the evidence, is concentrated
in the LOSS positions.

**It does not discharge the gate.** Part 2 (every distinct first move) has not
run, so the artefact records `complete: false`, `passed: false` — a partial audit
does not report as passing. `P1 wins the 5×3-h2` remains reportable with the
2026-08-09 qualification attached and **not yet citable as an H1 input**.

**Four runs were lost to a harness defect, not to the search.** The
transposition table stored one Python object per slot at **331 bytes per filled
entry**, measured only after the fourth failure. `--tt-bits 26` therefore needs
**21.2 GiB when full** on a 15.5 GiB VM: the table was never capable of filling.
The slots materialise lazily, so an impossible size runs for hours before the
OOM killer takes it — writing no checkpoint and leaving no traceback. Ply 0
*succeeded* at that size only because in 21 h it never filled the table, which
is what made the size appear validated.

| run | outcome | cost |
|---|---|---|
| 2026-08-17 | 68.8 h with no output at all; progress indistinguishable from death | 68.8 h |
| 2026-08-21 | ply 0 proved, then ply 2's table allocated on top of ply 1's | run lost, ply 0 kept |
| 2026-08-23 | `--tt-bits 27` (42.4 GiB full) OOM-killed at 504M nodes | 4.8 h CPU |
| 2026-08-23 | `--tt-bits 26`, ceiling guard fired but could not free memory | 374M nodes |

**Instrument changes, none of which touch what the audit measures.** The table
is now five parallel fixed-width `array` buffers — **28 bytes per slot**
verified, an 11.8× reduction — so 2²⁸ slots fit in 7.0 GiB. Verification is
**not** weakened: the `StateKey` is a bounded bit-field (55 bits on the 5×3, 77
on the 5×5) that packs losslessly into two 63-bit words and compares exactly,
with a test pinning that two states pack alike *iff* their keys are equal. This
matters here because with 1.75 × 10¹⁰ states against a 2³² birthday bound,
Zobrist collisions on this board are expected rather than hypothetical, and a
weakened key would have silently converted a detected collision into a wrong
value — the exact defect class adr-010 exists to catch.

The audit also gained a heartbeat, a memory ceiling that ends the run rather
than cascading through the remaining positions, per-row provenance recording
whether a row stopped on budget or on memory, and a startup check that refuses
an oversized `--tt-bits` in the first second rather than at hour four.

**The registered method is unchanged.** No decision rule, budget, seed or
comparison was altered — only the instrument's memory layout and its failure
handling. Node counts across sessions are not comparable without their table
size, so each row now records its own `budget` and `tt_bits`.

**The packed table is what made part 1 finish, and the margin is measured.**
Plies 1 through 14 took **4,807 s** at ~160,400 nodes/s. The same ply 1 under
the old table reached 504M nodes in 4.79 h at a *decaying* 29,256 nodes/s and
never finished. That is **5.5×**, well beyond the 1.3× penalty the packing
micro-benchmark predicted — the larger table stopped the thrashing, which is an
effect that only appears deep in a run and was deliberately not claimed before
it was observed.

**Open: part 2's cost is now plausible rather than hopeless, and unmeasured.**
It is 540 legal first moves over 120 distinct positions (the factor-two gap
between 240 layer-1 configurations and 120 reachable ones is the EXP-005
reachability identity at layer 1). Every one leads to a position the sweep calls
a loss for P2 — so P1 wins under *every* opening, and each is therefore a full
refutation, the expensive case, comparable to ply 1's 611M nodes.

The naive bound is 120 × 611M ≈ 7.3 × 10¹⁰ nodes, about **127 h** at the
observed rate. But part 2 shares one table across all 120, and sibling openings
transpose heavily, so the real figure is bounded above by that and unknown below
it. Yesterday's reading of "beyond any budget this project has" was made against
the old table's cost and is **withdrawn**. The honest next step is to run it with
the heartbeat reporting progress and let the first hours give the slope, rather
than to estimate it again.

#### Amendment (2026-08-26) — part 2 stopped on its measured slope, and a linear instrument registered in its place

**Part 2 ran and was stopped at opening 34 of 540.** It is registered here
before the replacement runs, as the working agreements require.

*What it produced.* **30 openings proved, 0 disagreements**, in 9.7 h of CPU.
That evidence stands and is kept in the artefact. The machine behaved perfectly
throughout — memory flat at 7.1 GiB, throughput steady at ~175,500 nodes/s with
no decay across 1.2 × 10⁹ nodes, which is the packed table doing exactly what it
was built for.

*Why it was stopped.* The marginal cost is rising by orders of magnitude, and
the progress line measures it directly:

| milestone | elapsed | marginal |
|---|---|---|
| 10 / 540 | 3,702 s | — |
| 20 / 540 | 4,917 s | 1,215 s per ten |
| 30 / 540 | 34,839 s | **29,922 s per ten** |

Opening 34 alone then ran 1.86 h to reach 23.5% of its node budget; carried to
the budget it would cost ~7.9 h and be recorded `unproven`. At the last block's
rate the remaining 510 openings are **~424 h of CPU**, and the trend is upward
because the expensive openings are not front-loaded. The elapsed figures come
from `perf_counter`, so they exclude suspend time and are not inflated by the
machine being closed overnight. **This supersedes the 127 h estimate above,
which was an upper bound whose floor turned out to be higher.**

*What is not being claimed.* Stopping is a **budget decision, not a finding**.
Part 2 produced no disagreement in the 30 openings it covered, and the remaining
510 are simply unmeasured. The artefact keeps `complete: false, passed: false`.

**The replacement, pre-registered.** `scripts/exp002_recurrence_check.py`
verifies the sweep's layers against *each other* rather than against a fresh
search: for every reachable position at layer `t`, the stored value must satisfy
`value(s) == WIN` **iff** some child of `s` is stored `LOSS`. No search is
involved, so the cost is linear in (positions × branching).

- **Scope.** Exhaustive over the **reachable** set of layers 0..`--max-layer`,
  not sampled. Layers 0-3 hold 737,204 configurations by the closed form, so the
  opening can be covered entirely. `--max-layer` is raised one step at a time
  with the measured cost read before each increase; layer sizes grow ~18× per
  level.
- **Decision rule, fixed before the run.** The check **passes** only with zero
  problems of either kind: a `recurrence` problem (a stored value that does not
  follow from the layer below) or a `roundtrip` problem
  (`decode(encode(s)) != s`). Any problem is a **finding about the sweep** and
  is reported, not re-run. Partial coverage is reported as the layer range
  actually checked and never as a pass over more.
- **Expected result.** Zero problems. A non-zero count is the informative
  outcome — it would mean the h2 database is internally inconsistent, which no
  gate so far is positioned to see.

**What it covers that part 2 did not, and what it does not.** Part 2 asks
whether the sweep is right about each opening, one full subgame proof at a time.
This asks whether the sweep is self-consistent across a layer boundary, over
every reachable opening position at once. It therefore covers **more positions
and a different bug class** — ranking, indexing, packing, checkpoint I/O,
aggregation — for a fraction of the cost.

It is **weaker in one specific way** and that is why it supplements rather than
replaces part 1: it shares `LayerIndex` with the sweep, which the PV audit's
forward searcher does not, so a ranking bug could in principle appear on both
sides. Two things bound it — the check reaches positions by walking *forward*
and encoding, where the sweep *decoded* rank indices, so the bijection is
exercised in both directions and asserted position by position; and part 1,
which shares no ranking code at all, already passes 15 of 15 on this arm.
Neither instrument is sufficient alone and neither is claimed to be.

**Not a numbered adr-010 gate.** adr-010 defines V0–V6; this is registered under
EXP-002 as a replacement for part 2's coverage role. Promoting it to a `V7`
requires an adr-010 amendment and is deliberately not done here — a gate is not
added to the standard in the middle of the run it was written for.

#### Amendment (2026-08-27) — V4 and V6 now report coverage, and V4 was dropping samples

The 2026-08-09 amendment filed this for "the instrument's next revision, after
h2 completes". h2 completed on 2026-08-13 and the PV audit's part 1 passed
15 of 15 on 2026-08-26, so the revision lands now, **before the h1 re-run**, which
is the last moment it can land without splitting the two arms across two
instruments.

**What changed.** Reporting only. `scripts/exp002_solve_5x3.py` gains a per-layer
breakdown for both gates; no sampling rule, seed, budget or pass criterion moved.

- **V4** reports `coverage`: samples drawn, how many produced evidence in either
  direction, which layers were actually searched, and
  `shallowest_layer_searched`. The aggregate percentage was never the
  interesting number — *where* the gate had purchase is.
- **V6** reports eligibility per layer, and separates **mirror-fixed pairs**: a
  configuration the reflection maps to itself encodes to its own index, so the
  comparison is a value against itself and cannot fail. On the 5×1 fixture 23 of
  160 pairs (14%) are of this kind. Not previously distinguished, in either arm.

**A gate was discarding evidence in silence.** V4 skipped terminal samples with a
bare `continue`, counting them nowhere. On h2 that was **40 of 601 draws** — which
is why that artefact's `agreed (349) + unaffordable (212) = 561` falls 40 short
of its own sample size, with nothing in the artefact saying so. They are now
re-derived instead, through `fliphex.rules.winner`. This is not circular: the
sweep decides a terminal layer by counting set bits in a packed integer and
taking the mover from layer parity, while this path decodes a `GameState` and
counts its colours. A parity or colour-orientation error in either would surface
here. The evidence is weaker than a search — it exercises no move generation —
so it is counted separately and never folded into `agreed`.

**h2's true V4 coverage was 58.1%, not the 61.3% previously recorded.** The
earlier figure used the non-terminal count as its denominator, which flattered
the gate by excluding exactly the samples it was throwing away. Against the 601
draws actually made: 349 verified, 212 over budget, 40 discarded.

**The independence defect is quantified, not fixed.** The 2026-08-09 amendment
observed that both arms draw the same indices from seed 3 and therefore do not
corroborate each other. Deriving the stream from `(seed, arm)` would fix it and
is **deliberately not done**: h1 is about to be re-run specifically to be
compared against h2, and a changed draw sequence would destroy that comparison to
buy independence on a gate that has never once disagreed. Recorded as a known
limitation of V6 on the 5×3, to be fixed on the next board rather than mid-arm.
For the same reason mirror-fixed pairs are *counted* but left inside `checked` —
excluding them would mean drawing replacements, which moves the stream.

##### Instrument — `scripts/exp002_coverage_replay.py` (registered before running)

- **Objective.** Recover the h2 arm's V4/V6 coverage breakdown without
  re-sweeping it, so both arms carry the same numbers.
- **Method.** The sampling is a pure function of the seed and the layer sizes,
  and h2's 4.1 GB of layers survive on disk. The script constructs the **real**
  `Checks` observer and calls it with the stored layers in sweep order — same
  object, same RNG, same draw sequence. It does not reimplement the sampling. An
  earlier draft did, and reproduced h2's 518 / 4,768 on the first attempt; that
  was reassuring and it was the wrong design, because two implementations of one
  rule drift and the one that drifts silently is the audit.
- **Fidelity check, fixed before the run.** The replay must reproduce the arm's
  **V5 checksum** exactly — a hash of every layer in sweep order, which fails if
  the layers are visited in the wrong order, and that order is also what the RNG
  stream depends on. For h2 that is `51192b4d403ac1cb…`. Verified end to end on a
  5×1 fixture: identical digest, identical draws, identical verdicts.
- **Scope.** Recovers what needs no search — per-layer V4 draws, the terminal
  count, the full V6 breakdown, the V5 digest. Does **not** recover which
  individual V4 samples were affordable; that is the ~20 h of forward search the
  archived artefact already reports in aggregate. `--v4-budget` runs it anyway.
- **Not a new gate.** It re-reads an existing arm and adds no criterion. Nothing
  it reports can change the h2 verdict; it can only describe how much of the
  sample that verdict rested on.

##### Result — h2 (2026-08-27)

Ran in **33.7 s** against the 4.1 GB checkpoint. Artefact
[`results/exp002-coverage-5x3-h2.json`](../results/exp002-coverage-5x3-h2.json).
The fidelity check passed: V5 came back `51192b4d403ac1cb…`, the arm's own
checksum, so the replay visited every layer in sweep order and drew the arm's own
samples. 601 V4 draws, 518 V6 pairs, 4,768 ineligible — the archived aggregates,
reproduced.

**V6's eligibility profile, measured for the first time.** Zero at `t = 0` and
`t = 1`, then 15 and 23 pairs at `t = 2` and `t = 3` — both of which **exhausted
the 800-attempt cap without finding 40**, so they are limited by the instrument,
not by the layer — then the full 40 from `t = 4` up. Eligibility rises
monotonically, 1.9% at `t = 2` to 100% at `t = 15`. The 9.8% aggregate was
concealing a clean gradient: V6 is a strong check on the endgame, a weak one at
mid-board, and no check at all on the opening.

**Mirror-fixed pairs are negligible here: 2 of 518.** Worth having measured
rather than assumed — the 5×1 fixture runs at 23 of 160 (14%), so vacuity is a
real effect on small boards and simply is not one on the 5×3. Had it gone the
other way, V6's 518 would have needed restating.

**What this does not resolve.** Which V4 samples were affordable is still only
known in aggregate for h2 (349 / 212), because that needs the searches. The h1
re-run produces it natively per layer; if the two must be compared at that
granularity, `--v4-budget 2000000` on this script recovers it for h2 at ~20 h.

#### Result — h1 re-run (2026-08-30): all three obligations discharged

**`P1` wins the 5×3-h1**, unchanged. Artefact
[`data/subgame-solutions/5x3-h1.json`](../data/subgame-solutions/5x3-h1.json),
log [`results/exp002-h1-rerun.log`](../results/exp002-h1-rerun.log).
`resumed_from_layer: null` — uninterrupted, so the timing is whole.

The amendment of 2026-08-13 said re-running h1 with `--checkpoint` would
discharge three registered obligations at once. It did, and each can be checked:

1. **The layers the criticality measure needs.** All 16 on disk, 4.1 GB, matching
   h2's 4.1 GB. H2's actual test is now computable — an XOR and a popcount
   between two databases that index the same object.
2. **The digest replay** the adr-010 amendment of 2026-08-07 requires before the
   5×3 value may be cited. V5 returned **`ab2620e1707f983f…`**, bit-identical to
   the 2026-08-09 run. 17.5 × 10⁹ values recomputed three weeks later, on a
   different memory state, after four OOM kills and a rewritten transposition
   table, agreeing on every one. That is the memory-integrity threat the
   amendment raised, answered.
3. **A clean end-to-end wall-clock**, which h1 had never had. **30.95 h at
   157,140 cfg/s** — faster than both the old h1 (32.38 h) and h2 (34.25 h).

**V4 returned `344 agree / 0 disagree / 217 over budget`, identical to
2026-08-09.** That is the design working: the coverage revision moved no draw, so
the arm reproduces its own sampling exactly. The 40 terminal draws are the
newly-visible bucket; 344 + 217 + 40 = 601 now balances against the sample size.

**V4's evidence begins at `t = 6`, and the cliff is sharp.** Newly visible:

| t | 0–5 | 6 | 7 | 8–14 | 15 |
|---|---|---|---|---|---|
| searched & agreed | **0** | 30 | 34 | 40 | — |
| over budget | all | 10 | 6 | 0 | — |
| terminal | — | — | — | — | 40 |

The gate reported `PASSED` in both arms while producing **no search evidence
whatsoever about the first six plies** — the entire opening, and the only part of
the tree the root value actually depends on. The 2026-08-09 amendment said V4
"covers the endgame and thins out going up"; the truth is harder: it covers
`t ≥ 8` completely, degrades across `t = 6..7`, and stops dead. This is not a new
defect — it is the old one, finally legible. The PV audit's part 1 remains the
only instrument that touched the opening, and it passed 15 of 15.

**Correction to this registry's own arithmetic (2026-08-27 entry).** That
amendment called 58.1% h2's "true" V4 coverage against 61.3%. Both are real and
they measure different things; neither deserved the word *true*:

| definition | h1 | h2 |
|---|---|---|
| searched ÷ non-terminal draws (the 2026-08-09 figure) | 61.3% | 62.2% |
| searched ÷ all draws | 57.2% | 58.1% |
| searched + terminal ÷ all draws (what the artefact now prints) | **63.9%** | 64.7%\* |

\* h2 discarded its 40 terminal draws rather than re-deriving them, so its third
row is what a re-run under the current instrument would report, not what it did.
The two arms are within a point of each other on every definition. The figure to
quote is the second — it has the honest denominator and makes no claim on the
weaker terminal evidence.

**V6 is identical across the arms again**: 518 pairs, 4,768 ineligible, 2
mirror-fixed, no coverage at `t = 0, 1`. Expected, and still the known
independence defect — same seed, same layer sizes, same indices drawn.

#### Instrument — `scripts/exp002_criticality.py` (registered 2026-08-30, before running)

- **Objective.** Compute H2's registered measure — the fraction of solved
  positions whose value changes when P1's extra tile is swapped (`JOKER` ↔
  `P3-tri`) — and, as a by-product, an exhaustive cross-arm verification.
- **Method.** Both arms' 4.1 GB databases index the same object. Deterministic
  and exhaustive: no seed, no sampling, no search.
- **The correspondence is a permutation, not index equality.** `LayerIndex`
  orders a hand by **tile index**, and `P3-tri = 6`, `P6 = 11`, `JOKER = 12`, so
  P1's positions are `(…, P6, JOKER)` in h1 and `(…, P3-tri, P6)` in h2. The
  extra tile sits at a different position in each arm, and `P6` — *shared* by
  both — moves with it. Comparing index against index would line "P6 spent" up
  against "P3-tri spent" and report a criticality manufactured by the encoding.
  The correspondence is the permutation carrying positions across by tile
  identity, derived from the hands at run time and asserted against decoded hands
  before use.
- **The denominator is the positions where the extra tile is still in hand.**
  Where it is already spent, both arms hold the same tiles on the same board with
  the same mover — the same game position, since placed tiles are inert
  (adr-003). Including those would dilute criticality with a subset identical by
  construction and report a number too small for a reason unrelated to the game.
- **Decision rule, fixed before the run.** Two separable outcomes:
  1. **Verification.** Zero mismatches on the already-spent subset is required.
     Any mismatch is a **finding about the solver**, not about the joker: it
     halts the criticality reading, is reported with example indices, and the
     5×3 value returns to *not citable* until explained. This is not a
     numbered adr-010 gate; promoting it to one needs an adr-010 amendment.
  2. **Criticality.** Reported as an exact fraction, overall and per layer.
     **No H2 verdict is taken in Phase 3** — `docs/research.md`'s Verdicts table
     stays empty until Phase 5, as registered. What Phase 3 delivers is the
     measure and its shape.
- **What the verification can and cannot catch.** Both arms ran the same code, so
  a shared logic error survives it. It catches the deck leaking where it must not
  — P1's hand consulted for P2's moves, a rotation-orbit count applied to the
  wrong hand — and any non-determinism or memory corruption that differs between
  two 30-hour runs. V4 sampled 601 positions and searched 344; this compares
  billions.
- **Expected result.** Pre-registered: **zero mismatches**, and criticality
  **non-trivial** — strictly greater than zero and not vanishingly small. The
  power caveat in EXP-001's registration is the reason this matters: if
  criticality came back near zero, the two arms would be nearly the same game,
  and their agreeing on the root value would carry no information about the
  joker. A near-zero result is therefore an informative *negative* about the
  instrument's power, not a confirmation of H2, and must be reported that way.
- **Artefact.** `results/exp002-criticality-5x3.json`.

##### Result (2026-08-30) — 164.5 s, and the largest verification the project has run

Artefact [`results/exp002-criticality-5x3.json`](../results/exp002-criticality-5x3.json).
The buckets partition the layer total exactly: 7,248,350,863 + 10,258,229,474 =
17,506,580,337.

**Verification: 10,258,229,474 positions compared, 0 mismatches.** Two
independently executed 30-hour sweeps, on decks that differ, agree on every
position where the swapped tile is already spent. For scale, V4 searched **344**
positions; the PV audit's part 1 re-derived **15**. This does not verify the
rules — both arms share `legal_moves` — but the deck does not leak where it must
not, across ten billion opportunities.

**Criticality: 1,237,229,498 of 7,248,350,863 = 17.07%.** Against all
17.5 × 10⁹ indices it would read 7.07%; the larger figure is the honest one,
since the diluting subset is identical by construction. The pre-registered
expectation was "non-trivial, not vanishingly small", and it holds: the arms are
genuinely different games, so their agreeing on the root value is informative
rather than vacuous. **No H2 verdict is taken here** — that is Phase 5's, as
registered.

| t | 0–4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| criticality | **0.00%** | 3.22% | 0.13% | 22.86% | 2.61% | **35.37%** | 11.00% | 28.55% | 18.75% | 23.94% | 23.15% |

**Two features of the shape, both unregistered and therefore descriptive only.**

*The swap is inert for five plies.* Criticality is **exactly zero** at
`t = 0..4` — not small, zero, across 10.2 million positions in which P1 holds a
different tile. Whether P1's eighth tile is the arrowless joker or `P3-tri` does
not change the value of a single position until the fifth ply. The root is one of
those positions, which is why both arms report `P1 wins`.

*It alternates with parity, like the runtime did.* Odd layers 5, 7, 9, 11, 13
run 3.22 / 22.86 / 35.37 / 28.55 / 23.94; even layers 6, 8, 10, 12 run
0.13 / 2.61 / 11.00 / 18.75. Odd `t` is P2 to move — the same layers the
2026-08-28 journal entry found are LOSS-dominated and therefore slow to sweep. A
mechanism is not claimed: this is the third instrument to show the parity split,
and it is worth one experiment of its own rather than a paragraph of speculation.

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

#### Note (2026-08-07) — `k*` was the wrong shape, and the missing half is arithmetic

**Not an amendment.** EXP-003 is complete, its measured quantity is unchanged,
its verdict stands, and `k* ≥ 6` held. Redefining a finished experiment's
reported quantity is the anti-pattern that produced EXP-007 rather than an
EXP-005 rewrite, and it is not repeated here. What follows is a reading note: the
number EXP-003 produced answers **half** of adr-012's question, and the other
half needs no experiment at all.

**Where the shape came from.** Takizawa 2023 has *two* thresholds, not one — §3.4
at 50 empty squares and §3.5 at 36 — and they are justified differently. The
upper cut is set by **enumerability** (the last layer you can write down whole:
2,958,551 positions after symmetry) and the lower by **solvability** (the depth
at which Edax settles a position outright). Between them nothing is enumerated;
the gap is bridged by conjecture-and-verify. EXP-003 was designed to locate a
single crossover and measured the **solvability** cut only.

**The enumerability cut is closed form.** From `scripts/layer_profile.py` on the
shipped 5×5 (25 cells, hands 13 + 12), by empty-cell count `k = 25 − t`:

| `k` | configurations in the layer | at 2 bits |
|---:|---:|---:|
| 0 | 33,554,432 | 8 MB |
| 1 | 5,452,595,200 | **1.4 GB** |
| 2 | 392,586,854,400 | 98 GB |
| 3 | 9,029,497,651,200 | 2.3 TB |
| 4 | 136,571,151,974,400 | 34 TB |
| 5 | 1,051,597,870,202,880 | 263 TB |
| 8 | 50,173,893,918,720,000 | **12.5 PB** |

So the two cuts on the 5×5 are **enumerable at `k ≤ 1`** in memory (`k ≤ 2` if
98 GB on disk is allowed) and **solvable on demand at `k > 8`**.

**There is no crossover region.** The solvability cut sits far *above* the
enumerability cut, so across the whole of `k = 3…8` nothing is enumerable and
everything is solvable in under a second. Materialising is not merely worse at
the measured points — it is **dominated over the entire interval**, by arithmetic
rather than by sampling. adr-012 Option B is closed more firmly than EXP-003
alone establishes.

**The interesting consequence is about the 5×5 attempt, not about adr-012.**
Because the layer profile is a hump, the layers are small at *both* ends: the
opening is enumerable to `t ≤ 5` (32.1 × 10⁹ configurations, 8.0 GB) and the
endgame to `k ≤ 2`. What has no coverage from either direction is
**`t = 6…16`** — between 19 and 9 empty cells, eleven layers, peaking at
1.09 × 10¹⁷ configurations at `t = 15`. That interval is precisely where
Takizawa's Algorithm 1 lives, and it is the part FLIPHEX cannot attempt: it needs
an evaluator whose predictions are almost always right, and adr-004 R1–R3 govern
what an Axis-1 run may consume from one.

**For future 5×5 work, the reportable quantity is a pair** — largest enumerable
`k`, largest on-demand-solvable `k` — with the uncovered interval named. Any
successor experiment registers its own ID; this note does not create one.

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

#### Note (2026-08-13) — unblocked as a side effect of crash resume

The blocker was never the solve; it was that a solved 5×3 layer existed only in
RAM and was discarded as the sweep moved past it. `solver/checkpoint.py`, added
for crash resume, now leaves **all 16 layers of the h2 arm on disk** —
`data/checkpoints/5x3-h2/`, 4.1 GB, exactly the input this experiment specifies.
Nothing here is re-registered and the decision rule is untouched; the status
changes from *blocked* to *runnable* once h2 finishes, since the files are the
live run's resume state until then.

The same files already paid for themselves once: the WIN/LOSS-per-layer counts
behind the parity finding in EXP-002 were read straight out of them, which is a
measurement nobody could have made while the layers were transient.

#### Result (2026-08-30) — 81.6 s over the h2 arm, and the decision rule is dead

Artefact [`results/exp004-compressibility-5x3.json`](../results/exp004-compressibility-5x3.json),
block size 4,096 bytes (16,384 positions per probe).

| encoding | size | ratio |
|---|---|---|
| raw (2 bits/position) | 4.08 GiB | 1.00× |
| block-RLE | 1.34 GiB | 3.04× |
| block general-purpose coder | 0.45 GiB | 9.10× |
| logic-minimised | **absent** | — |

**The registered decision rule no longer has anything to decide.** It was written
to choose between adr-012 Options A and C. adr-012 chose **B** — no database —
on EXP-003's measurement. The rule is recorded as moot rather than reinterpreted
into something these numbers could satisfy, and the experiment stands as a
measurement.

**Two deviations from the registered configuration, both recorded rather than
absorbed.** `zstandard` is installed in neither interpreter here, so **zlib
stands in** for block-Zstd; the artefact carries `coder_is_registered_zstd:
false`. The two answer the same question and differ by a few percent at this
block size, well below anything a decision would turn on. And **logic-minimised
is absent, not estimated**: it needs the reachable closure, which is EXP-007 and
has not run on the 5×3.

**The parity split appears for the fourth time, and corrects the journal.**
Block-RLE compresses even layers 120×, 88×, 33× at `t = 4, 6, 8` and odd layers
3.2×, 1.6×, 1.2× at `t = 7, 9, 11`. A *mostly*-LOSS layer would be as homogeneous
as a mostly-WIN one and would compress just as well — it does not. So even layers
are near-uniformly WIN and **odd layers are mixed**, which is what makes them
both slow to sweep and incompressible. The 2026-08-28 journal entry said "the
mover is mostly lost"; that overstated it and is corrected there.

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

**Instrument** (written 2026-08-07, before the run): `solver/reachable.py` with
`scripts/exp005_reachability.py` as the runner. Predecessors are counted
**forward**, not by inverting
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

The runner refuses to print a verdict on anything but the registered 5×3, and on
an incomplete run — the rule applies to the complete design only. Smoke run on
the 5×1 (1,023 configurations, not the registered board, **no verdict**): 14.76%
orphans overall, 50.0% at `t = 1` falling monotonically to 3.1% at the terminal
layer. Recorded as an expectation-setter, not as evidence: 5 cells is not 15, and
the shape of that curve is exactly what a real measurement could overturn.

#### Amendment (2026-08-07, evening) — the measurement is a counting identity

Both 3×3 arms returned **identical** orphan counts at every layer — 45, 720,
3,360, 7,560, 7,560, 3,360, 720, 45, 1 — despite differing in their fifth
archetype (`JOKER` vs `P2-skip`). That is not a coincidence, and checking it
closed the experiment analytically:

> **`orphans(t) = layer_size(t) / 2^t`, exactly**, on the 5×1 and on both 3×3
> arms, at every layer.

**Mechanism.** A configuration has no legal predecessor exactly when *every*
occupied cell carries the colour of the player who did **not** just move. The
last-placed cell always shows its placer's colour — a tile's own arrows never
point at the cell it occupies — so if no cell has the right colour, no cell can
have been the last. That is exactly 1 of the `2^t` colourings under each
(cell-set, hand-state), hence the `2^-t`. It is the adr-010 V1 calibration note's
`t = 1` observation generalised to every layer.

**Consequences, both awkward for this experiment as registered.**

1. **The 5×3 run is unnecessary for the registered number.** By the identity,
   the answer is **60,009,757 of 17,506,580,337 = 0.3428%**. The hours-long run
   becomes a *verification of the formula*, worth doing cheaply on small boards
   and not worth a day of compute on the 5×3.
2. **The quantity is an artefact of the index, not of the game.** It counts
   colourings the mover's colour forbids — it does not depend on the arrow
   patterns, which is why the two arms agree exactly. A don't-care yield of
   0.34% fires the "drop" branch by an enormous margin, but for a reason that
   says nothing about FLIPHEX.

**This does not retro-fit the rule.** EXP-005's rule and threshold stand, and the
0.3428% figure fires *drop don't-cares* once verified on the registered board.
What changed is the assessment of how much that verdict is worth, and the answer
is: very little on its own. The quantity adr-012 decision 7 needs is the
transitive closure, which is registered separately as **EXP-007** rather than
substituted in here.

**Verification, not discovery.** The identity is checked as a unit test on the
boards where it is affordable rather than by a 5×3 run.

### EXP-007 — true reachable closure, and what one-step-back misses

- **Objective.** The **transitive** reachable set from the opening position, per
  layer, on the 5×3. EXP-005 counts configurations with no legal *predecessor*;
  this counts configurations no *game* reaches. The second is the quantity
  adr-012 decision 7 actually needs, and it is strictly larger.
- **Hypothesis.** —
- **Registered.** 2026-08-07, before the instrument existed, after EXP-005 on the
  3×3 showed its own measurement to be a counting identity (see the EXP-005
  amendment of the same date). Registered as a **new ID rather than an amendment
  to EXP-005** deliberately: the two yields can fall on opposite sides of the 20%
  threshold, and redefining a live experiment's measured quantity is the
  anti-pattern adr-010 was already amended once to avoid. EXP-005 keeps its rule
  and its number; this one gets its own.
- **Configuration.** 5×3, 15 cells, hands 8 + 7, both arms. Forward closure by
  layer: layer 0 is the opening; a configuration in layer `t` is marked iff some
  legal move from a **marked** configuration in layer `t-1` produces it. One bit
  per configuration, two layers resident — peak `5.02 × 10⁹ + 3.62 × 10⁹` bits =
  **1.08 GB**. Deterministic and exhaustive: no seed.
- **Decision rule, pre-committed.** The same threshold EXP-005 carries, on the
  correct quantity: if the unreachable fraction is **under 20%**, don't-cares are
  dropped from the adr-012 design entirely; at or above 20%, adr-012 keeps the
  don't-care path and EXP-004 measures what it is worth after compression. The
  rule runs on the complete 5×3 design only — not on the 3×3, not on a partial
  run.
- **Expected result, recorded before the instrument exists.** **Below 20%**, so
  the expected branch is *drop don't-cares*. Basis: on the 3×3, one-step-back
  gives 3.28% while the true figure is **≥ 4.14%** (from EXP-001's `--tt-bits 24`
  run — at most 3,300 of the 9,390 configurations below the reachable ceiling are
  attributable to table collisions, leaving ≥ 6,090 never visited); the closure
  is therefore ≥ 1.26× the one-step figure there. The 5×3's one-step figure is
  **0.3428%** by closed form. Nothing in that chain gets near 20%. **The
  informative outcome is the opposite one** and is reported as such, not re-run.
- **Predicted, so it can fail.** The one-step yield obeys
  `orphans(t) = layer(t) / 2^t` exactly on the 5×1 and on both 3×3 arms. The
  closure has no such prediction — if it also comes out at `layer(t)/2^t`, the
  instrument is measuring one-step-back again and is wrong.
- **Artefacts.** `results/exp007-5x3-h1.json`, `results/exp007-5x3-h2.json`,
  written per layer so an interrupted run still reports what it finished.

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

#### Amendment (2026-08-07) — the sampler's bias is not neutral, and a second stratum

Amended **before the run**, which is the only time this is allowed. The
registered design above is untouched: same seed, same 500 positions, same
stratification, same decision rule. This adds a disclosed second stratum and
records why.

**What prompted it.** Takizawa 2023 §5, read for
[the lit-note](../notes/takizawa-2023-othello-is-solved.md) B4/D1. Two findings
bear directly on this design:

> "many of our calculations to weakly solve Othello were devoted to positions
> where, according to the estimation, there is a clear advantage in terms of
> winning or losing. This indicates that one cannot claim a pseudo-solution by not
> proving positions whose estimated game-theoretic value exceeds any threshold."

> "systematic and significant errors in Edax's function to estimate the
> game-theoretic value from a position […] **especially for positions unlikely to
> appear in actual games**."

**Why that lands here.** The registered sampler draws by *random playout* to ply
`25 − k`. That was chosen to keep Axis 2 from choosing its own exam, and it still
does that job. But random playout is a **play** distribution, and Takizawa gives
empirical evidence that an evaluator's systematic errors concentrate exactly
where play does not go. H3 asks whether the learned policy's move preserves the
exact value. Measuring that only on positions a playout reaches risks reporting
the agreement rate on the learner's easy half — a milder version of the failure
the "not from self-play" clause already guards against, and one the existing
disclosure ("carrying the same registered bias") names without bounding.

**Second stratum, pre-declared here.** **250 positions**, `k ∈ {6, 7, 8}` split
84/83/83, **seed 4**. Drawn **uniformly from the layer index**: pick a uniform
random integer in `[0, layer_size(25 − k))` and `LayerIndex.decode` it
(`solver/retrograde.py` already has `unrank_subset` and `decode`, so no new
instrument is needed). Reject any configuration with **no legal predecessor**,
using the closed characterisation proved for EXP-005 — a configuration is an
orphan exactly when every occupied cell carries the colour of the player who did
*not* just move — which is an `O(N)` test on a single position and needs no
enumeration.

**What this stratum is not, stated plainly.** It is uniform over the *layer*, not
over the *reachable* set. Uniform-over-reachable is **not implementable on the
5×5**: the `k = 8` layer holds 5.0 × 10¹⁶ configurations (12.5 PB at 2 bits) and
EXP-007's transitive closure is infeasible at that scale. The orphan filter
removes only the one-step-unreachable share, which the EXP-005 identity puts at
`2^-t` — about **1 in 131,072** at `k = 8`. So the filter is a *correctness
guard, not a meaningful filter*, and the residual gap between this stratum and
true reachability is disclosed rather than closed. EXP-007 measured that gap on
the 3×3 at 3.91% closure against 3.28% one-step; on the 5×5 it is unmeasured.

**Reported separately; pooling is forbidden.** The H3 decision rule (Wilson lower
bound > 0.90) runs on the **registered stratum only**. The second stratum is
reported alongside with its own Wilson CI and is **descriptive**. A gap between
the two strata is the finding — it is the FLIPHEX measurement of Takizawa's
observation — and it must not be averaged away into a single number, in either
direction.

**Cost.** EXP-003's medians are 6,660 / 20,024 / 806,474 nodes at `k = 6/7/8`, so
250 more positions is well under an hour. It is not a reason to skip it, and it
was not free to *decide*: the decision had to be made before the run, which is
why it is here and dated.

### EXP-008 — how strong is an exact agent with no endgame database?

- **Registered.** 2026-08-30, before the instrument existed, at the Phase 3
  close.
- **Objective.** Phase 3's third exit criterion reads *"on the 5×5 game,
  alpha-beta agent + endgame database beats random and heuristic agents ≥ 90%."*
  [adr-012](../docs/adr/adr-012-endgame-database-storage.md) cancelled the
  database on `EXP-003`'s measurement, so the criterion names an artefact that
  was deliberately not built. This runs the half that survives — the exact agent
  without a database — rather than dropping a strength number from the phase
  entirely.
- **Hypothesis.** — (exploratory; it supplies a Phase 4 baseline, and no H3
  comparison is made here).
- **Configuration.** Shipped 5×5, 25 cells, hands 13 + 12.
  `agents/solver_agent.py` with `max_nodes = 2,000,000` — the same budget adr-010
  V4 uses — and `search_below_k = 8`, against `RandomAgent` and `HeuristicAgent`.
  **250 games per (opponent × seat) = 500 per opponent, 1,000 total.** Both seats
  in equal number, because H1 says the seat itself carries an advantage and
  pooling unbalanced seats would measure that instead. **Seed: 5.**
- **Why `search_below_k = 8`.** A search that will exceed its budget spends the
  *whole* budget before saying so. `EXP-003` puts the median proof at `k = 8` at
  806,474 nodes and rising steeply above it, so attempting all 25 plies would
  burn ~34 M nodes per game to learn nothing. Declining the attempt above `k = 8`
  is the same threshold `EXP-003` already established, reused rather than
  reinvented.
- **Decision rule, fixed before the run.** The win rate is reported with a Wilson
  95% interval, **and never without `proved_rate` beside it.** At `k ≤ 8` on 25
  cells the agent can prove at most the last eight plies, so a strength number
  quoted alone would be largely a fact about `HeuristicAgent`, which is the
  instrument defect `agents/solver_agent.py` was written to make impossible to
  hide. The exit criterion counts as met only if the interval's **lower bound**
  clears 90% against both opponents; anything else is reported as the number it
  is, and the criterion is recorded as unmet rather than reinterpreted.
- **Expected result, recorded before the run.** ≥ 90% against `RandomAgent`.
  **Against `HeuristicAgent`, unknown and quite possibly below 90%** — the agent
  plays the heuristic's own moves for roughly the first seventeen plies and
  differs only in the endgame, so this is close to asking how much perfect
  endgame play is worth on top of the heuristic. A result under 90% there is
  informative, not a failure, and may not be re-run at a larger budget to chase
  the threshold.
- **Artefact.** `results/exp008-agent-strength.json`.

#### Result (2026-08-30) — 1,647 s, criterion not met, and a control that surprised

Artefact [`results/exp008-agent-strength.json`](../results/exp008-agent-strength.json),
log [`results/exp008.log`](../results/exp008.log).

| pairing | exact seat | wins | rate | Wilson 95% | proved |
|---|---|---|---|---|---|
| vs random | P1 | 248/250 | 99.2% | [97.1, 99.8] | 30.8% |
| vs random | P2 | 242/250 | 96.8% | [93.8, 98.4] | 32.9% |
| **vs random** | **pooled** | **490/500** | **98.0%** | **[96.4, 98.9]** | 31.8% |
| vs heuristic | P1 | 178/250 | 71.2% | [65.3, 76.5] | 30.8% |
| vs heuristic | P2 | 127/250 | 50.8% | [44.6, 56.9] | 33.3% |
| **vs heuristic** | **pooled** | **305/500** | **61.0%** | **[56.7, 65.2]** | 32.0% |

**The exit criterion is not met**, and both halves were pre-registered. Against
random the lower bound clears 90% comfortably. Against the heuristic it does not,
and the registration said to expect exactly that: the agent plays its fallback's
moves for the first seventeen plies and differs only in the endgame, so 61% is
close to asking what perfect endgame play is worth on top of the heuristic. It is
**not re-run at a larger budget to chase the threshold**, as registered.

**`proved_rate` is 32%** — eight of twenty-five plies, which is what
`search_below_k = 8` buys. No rate above may be quoted without it.

**The control, added post hoc, returned 40.0%** [34.1, 46.2] for the *first* seat
between two `HeuristicAgent`s. Between two greedy heuristics on the 5×5, moving
first is a **disadvantage** of about ten points. That is a fact about the
heuristic pair, not about FLIPHEX — a greedy agent's pieces sit on the board
longer when it moves first and are flipped more often — and it is emphatically
**not** an H1 input.

**The control does not baseline the P2 arm, and the tempting subtraction is
wrong.** Seeds are assigned by construction order, not by seat: the control runs
`seed+game` first and `seed+10000+game` second, while the treatment-as-P2 gives
`seed+10000+game` to the *first* seat. With many tied moves for a greedy
heuristic to break, those are not the same opponent. So "71.2% against a 40.0%
baseline is +31 points" is defensible for the P1 arm and "50.8% against 60.0% is
−9 points" is **not** — the second reading would have perfect endgame play making
an agent worse, which is implausible enough to point at the instrument rather
than the game. A seat-matched control is the fix and is not run here.

### EXP-009 — the WIN/LOSS mix per layer

- **Registered.** 2026-08-30, before the instrument existed, at the Phase 3
  close.
- **Objective.** Measure, rather than infer, the fraction of configurations in
  each layer that are a win for the side to move. Four Phase 3 measurements split
  on the parity of `t` — sweep runtime, criticality, block-RLE ratio, and a
  notebook cell — and each was explained by a guess at the value mix.
- **Why it is needed, stated as a contradiction.** The compressibility result
  reads odd layers as *mixed*: block-RLE gets 1.2–3.2× at `t = 7, 9, 11` against
  120× at `t = 4`. A notebook cell reads layers 1 and 3 as **100% LOSS** — every
  configuration, not most. Both cannot describe the same thing: a uniformly-LOSS
  layer is as homogeneous as a uniformly-WIN one and would compress just as well.
  Uniformity must therefore break somewhere between `t = 3` and `t = 7`, and no
  instrument so far can say where.
- **Hypothesis.** — (exploratory; it is a structural description of the solved
  object, and links to no registered hypothesis).
- **Configuration.** 5×3, both arms available; h1 by default. All 16 layers,
  exhaustive, from the checkpointed databases. Deterministic: no seed, no
  sampling.
- **Decision rule.** None — this is a measurement, not a test, and no threshold
  is pre-declared. The instrument reports `uniform: true` for any layer whose
  configurations all share a value. **It does not explain the split**; the
  mechanism is a separate question and deliberately not speculated about here,
  after three earlier attempts to explain the parity from the side rather than
  measure it.
- **Integrity check.** Every 2-bit field must be `SLOT_WIN` or `SLOT_LOSS`; a
  `SLOT_UNSET` halts the run rather than being counted as a loss.
- **Expected result, recorded before the run.** Uniformity at the shallow
  layers, breaking down somewhere in the middle game. **The layer where it breaks
  is the number this exists to produce**, and no prediction is offered for it.
- **Artefact.** `results/exp009-parity-5x3-h1.json`.

#### Result (2026-08-30) — 70.8 s, and uniformity breaks at `t = 5`

Artefact [`results/exp009-parity-5x3-h1.json`](../results/exp009-parity-5x3-h1.json).

| t | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| WIN % | 100 | 0 | 100 | 0 | 100 | 4.75 | 99.84 | 24.92 | 98.14 | 46.36 | 93.64 | 57.01 | 87.81 | 59.57 | 77.61 | 50.00 |

**Layers 0–4 are uniform**, which is what the experiment existed to locate. Every
one of the 12,841,920 configurations at `t = 4` is a win for P1; every one of the
713,440 at `t = 3` is a loss for P2. From `t = 5` the two parities converge
monotonically toward 50/50 — even layers fall 100 → 77.61, odd layers rise
0 → 59.57 — and the terminal layer sits at exactly 50%, which is forced: 2¹⁵
colourings on an odd cell count split evenly.

**This retires the parity question rather than adding to it.** Sweep runtime,
criticality and block-RLE ratios are all downstream of this one number, and each
was used to guess at it. Two of those guesses were wrong, and the direct count
took 70 seconds — the note is in the 2026-08-28 journal entry.

**Two independent confirmations fall out.** EXP-002's criticality is exactly zero
on layers 0–4 and first becomes non-zero at `t = 5`; that instrument shares no
code with this one and finds the same boundary. And EXP-004's block-RLE gets
120× at `t = 3` and `t = 4` against 11.64× at `t = 5` — compression was tracking
uniformity all along.

**Not a claim about the game.** This describes the *configuration space* the
sweep enumerates, most of which is unreachable in play. What it licenses is a
statement about the artefact's structure, not about FLIPHEX strategy, and it
links to no hypothesis.

### EXP-010 — deduplicated MCTS expansion against the naive tree

- **Registered.** 2026-08-30 at the Phase 4 opening; **revised the same day**
  after `experiment-redteam`, before any instrument existed. The first draft is
  superseded in full — it is not preserved, because nothing was run from it. The
  defects it carried are recorded in the 2026-08-30 journal entry, since three of
  them are recurrences of failures this project has already had once.
- **This is not an open decision.** The
  [adr-005](../docs/adr/adr-005-alphazero-scope-and-network.md) Phase 3
  amendment already *requires* children to be indexed by position rather than by
  action. This entry registers a measurement, not a choice.
- **Objective.** Measure what deduplicated expansion buys, and what it costs,
  against an otherwise identical naive tree, on positions whose exact value is
  known — and separate the benefit that comes from the ADR's stated mechanism
  from the benefit that comes merely from having fewer children.
- **The mechanism being measured.** 1,450 root actions reach **325** distinct
  positions on the 5×5 (4.46×; 2.28× over a whole game),
  `scripts/measure_move_collapse.py`. Expanding by action splits one position's
  visit counts across up to six labels **(i)** *and* gives each label its own
  prior **(ii)**. `π` is then read off the split counts. Risk **R13**, score 9.
- **Hypothesis.** — none. This is an instrument-quality measurement about the
  search. It is **not** evidence about H1, H2 or H3, and the anti-circularity
  clause below explains why it may read Axis 1 anyway.

#### Ground truth, pinned

`data/subgame-solutions/5x3-**h2**.json`, V5 digest
`51192b4d403ac1cb45c22d92ce58bab215843f457f245e7aca6d18744f8a3f43`. The run must
verify the digest before drawing and abort on mismatch.

**Why h2 and not h1**, recorded because the first draft chose h1 and the reason
it changed is not obvious. h2 is the arm the principal-variation audit actually
ran on — 15 of 15, `results/exp002-pv-audit-5x3-h2.json` — and the arm the
layer-to-layer recurrence check covered. h1 has neither, and its V4 produced no
search evidence at `t = 0..5`, which includes the shallowest layer sampled here.
h2 is also **less contaminated for EXP-011's purposes**: its P1 deck holds one
single-rotation-orbit tile (`P6`) against h1's two (`P6` and the joker).

#### The sample

- **3,000 positions**, drawn once, seed **17**, and used by **both** arms — the
  comparison is paired. **Independent of EXP-011's draw**: different seed,
  separate draw, so the two entries' results do not share sampling error and may
  be read jointly.
- **Stratified uniformly across layers `t = 5..14`**, 300 per layer. Uniform
  sampling over the union would concentrate the draw near `t = 8–9` where the
  layers are widest and would set the parity mix by accident.
- **`t ≥ 5` because EXP-009 measured layers 0–4 as uniform** — every
  configuration there shares one value, so every legal move is optimal and the
  comparison would discriminate nothing. `t = 15` is terminal and has no moves.
- **Restricted to positions that are a WIN for the side to move.** This is the
  repair for the defect that killed the first draft: in a position that is a
  *loss*, no optimal move exists, every arm scores zero deterministically, and
  the pooled metric becomes a parity-weighted mixture of degenerate cases. The
  restriction is a declared domain, not a filter applied after seeing results,
  and it is the only domain on which the primary metric is defined.

#### The searcher, specified

The first draft said "uniform prior, no trained network", which names the prior
and leaves the **leaf evaluator** unstated — three different experiments hide in
that gap, and under one of them the headline number is decided by child
insertion order, which differs between arms by construction.

- **Prior: uniform** over the expanded children. No trained network anywhere.
  With a network in the loop any difference is confounded with that network's
  quality, and at generation 0 the network is noise.
- **Leaf evaluator: random rollout to a terminal**, one playout per simulation,
  returning the exact ±1 outcome. FLIPHEX playouts are ≤ 15 plies here, always
  terminate and always yield a decided winner, so this is well defined and cheap.
  It makes the searcher plain UCT with a uniform prior, which is
  [adr-005](../docs/adr/adr-005-alphazero-scope-and-network.md)'s own designated
  baseline — appropriate, because the question is about the *tree*, not about a
  policy.
- **`c_puct` fixed at its default, not tuned here.** Recorded as a stated
  constant rather than a control: the same `c_puct` does **not** mean the same
  exploration behaviour across arms with different child counts, because PUCT's
  exploration term normalises the prior over the children. Arm C below exists
  because of this.
- **Deduplication is sibling-alias merging at a single parent**, not a full
  cross-parent transposition DAG. On a placement game with inert tiles the latter
  is a large separate benefit unrelated to R13, and folding the two together
  would credit deduplication with someone else's win.
- **There is no DAG, and therefore no backup rule to choose.** Corrected
  2026-08-30 while implementing `az/mcts.py`, against an earlier revision of this
  entry that fixed the rule as "the mean over parents". Sibling-alias merging
  gives a child several *action labels* and still exactly **one parent**, so the
  structure stays a tree. adr-005's Phase 3 amendment predicted that
  deduplication "turns the tree into a DAG" and called the backup rule an
  unresolved subtlety — that is true of *cross-parent* transposition, which this
  entry does not implement, and not of the merging that addresses R13. Pinned by
  `tests/test_az_mcts.py::test_sibling_merging_does_not_create_a_dag`, which walks
  the tree and asserts no node is reached twice.

  This **removes a confounder** rather than adding one: the earlier revision had
  to word its falsifier as "the mechanism is wrong *or* the backup rule is bad",
  and that disjunction is now gone. The ADR's stated cost for deduplication does
  not materialise; only its benefit is at stake.

#### Three arms

| | Children indexed by | Prior per child | Isolates |
|---|---|---|---|
| **A — naive** | action | uniform over actions | the deployed-naive baseline |
| **B — deduplicated** | position | uniform over positions | the ADR's design |
| **C — multiplicity-corrected** | action | uniform, divided by alias multiplicity | mechanism (ii) alone |

**Arm C is the control the first draft lacked.** Without it, a gain for B at a
small budget is fully explained by "B has ~4× fewer children and can complete a
pass over them" — an effect obtainable by deleting three quarters of A's children
at random, which is not the ADR's mechanism. B vs C isolates visit-splitting
**(i)**; C vs A isolates prior mass **(ii)**.

**Arm A's root readout is the argmax over action labels**, matching what the ADR
says happens in deployment — "`π` is then read off those split counts" — not the
argmax after aggregating aliased visits. Registered because the choice moves the
primary number and a competent implementation would silently do the other thing.

#### Metrics

1. **Primary — top-1 optimality at budget 400**, paired: the fraction of the
   3,000 positions where the most-visited root child is a move whose resulting
   position is exactly a loss for the opponent. Comparisons B vs A, B vs C, C vs A
   by McNemar on the discordant pairs, with 95% intervals on each difference.
2. **Reported with it, and the primary number may not be quoted without them:**
   - the **random-legal-move floor** on the same sample, measured rather than
     assumed, per layer;
   - the **exact-search ceiling** (100% by construction, stated so the scale is
     explicit);
   - the primary metric **stratified by `t`**, never only pooled.
   The floor is not a constant: it is set by the value mix of the layer *below*
   the sampled one, and EXP-009's table implies it swings from near 0% at `t = 5`
   to roughly 75% at `t = 6`. A pooled number without the floor beside it has no
   interpretable scale, which is the V3/V4 failure mode this project has now hit
   three times.
3. **Budgets 100 and 1,600** are run and reported as **secondary and
   descriptive**, carrying no decision rule. Only budget 400 is tested. This is
   the multiplicity control: three tested budgets on one sample would fire
   somewhere under the null about 14% of the time.
4. **Cost, split in two** because the two halves transfer differently:
   - **tree cost** — position hashing and DAG backup, per simulation. This
     transfers to deployment.
   - **inference cost** — *not measured here*, because there is no network. In
     deployment deduplication **reduces** the number of distinct children to
     evaluate, so its sign is plausibly negative. Recorded so that a measured
     tree overhead is never quoted as the pipeline's overhead.
5. **Diagnostic — aliased policy mass at the root**, defined without ambiguity:
   for a root position whose legal actions partition into `k` classes by
   resulting position, with class `j` holding `m_j` actions, the aliased share is
   `Σ_j (m_j − 1) / Σ_j m_j` — i.e. every action beyond the first in its class.
   Measured on the sample rather than predicted from the 5×5 root. **Under-reports
   by construction**: the mechanism compounds down the tree and this is measured
   at the root only.

#### Decision rule

The adopted design does not depend on the outcome; what the outcome governs is
whether adr-005 stands.

- **B ≥ A on the primary** → proceed as the ADR directs.
- **Falsifier, stated as a non-inferiority test**: B worse than A by more than a
  **2-point margin**, i.e. the 95% interval on `(B − A)` lies entirely below
  **−2** — not below zero, which is a different and much weaker claim. If it
  fires, an ADR amendment is written **before** any self-play run. Since there is
  no backup rule to confound it (see above), the falsifier reads cleanly: **the
  amendment's stated mechanism is wrong.**
- **If B beats A but C also beats A by a comparable margin**, the benefit is
  mostly prior mass and not visit-splitting. That does not change the design —
  the ADR mandates B — but it is reported as such rather than as a vindication of
  both mechanisms.
- **Cost is reported, not gated.** The first draft listed a "50% overhead
  ceiling" under *Decision rule* with no consequence attached, which invites it
  to be quoted as a threshold that was met. There is no cost threshold.

#### Power

McNemar, discordant proportion `π_d ≈ 0.15`, two-sided 5%, 80% power. At
**N = 3,000** the detectable difference is **~2 points**, which is what makes the
2-point falsifier resolvable — at the first draft's N = 1,000 the floor was ~3.4
points and the falsifier could not fire, while the entry nonetheless presented it
as a test. If the realised `π_d` differs materially from 0.15 the achieved
detectable difference is recomputed from it and **reported**, rather than the
threshold being quietly reinterpreted.

#### Anti-circularity

adr-005 point 4 forbids Axis 1 from driving Axis 2's selection. This experiment
reads Axis 1 and is nevertheless compliant, on a narrower and stronger argument
than the first draft's:

The first draft argued "no trained parameters, so nothing is selectable". That
reading is too narrow — a **search design** selected by agreement with the solver
on the 5×3 is still a selection along the dimension H3 later reports, since the
5×3 is a member of H3's comparison set and top-1 optimality against the solver is
metric-for-metric H3's 5×3 evidence.

What actually holds: **adr-005 already mandates arm B**, so no outcome selects
anything. The one channel that could is the falsifier, and it triggers an *ADR
amendment written by hand*, not an automatic design change. If this experiment
ever gains a trained network or the power to choose between arms, the clearance
lapses and the entry is re-registered.

#### Expected result, recorded before the run

- **B > A on the primary, by 2 to 8 points at budget 400.** Band re-derived for
  the regime actually sampled. The first draft predicted 3–15 points from the
  5×5 root's 4.46× collapse — a regime this design *excludes*, since `t ≥ 5` on
  15 cells corresponds to the 5×5 around ply 8 (~1.8×) and decays from there.
- **Aliased mass on the sample: 20 to 45%**, not the 60–80% the first draft
  imported from `1 − 1/4.46 = 77.6%` at the 5×5 root.
- **C between A and B**, nearer B — most of the effect predicted to be prior mass
  rather than visit-splitting.
- **Tree overhead under 20%.**
- The margin between B and A is predicted to shrink as the budget rises, since a
  naive tree with enough simulations eventually visits all six aliases anyway.

#### Threats to validity

- **Regime mismatch.** Measured where the aliasing is weakest, by construction.
  Generalising to the 5×5 root requires the alias structure to be comparable, and
  adr-005's own decay table says it is not. The result licenses "deduplication
  helps at ~1.8× collapse"; the 5×5 root is 4.46× and is *more* favourable, so
  the direction transfers and the magnitude does not.
- **The searcher is not the deployed searcher.** Uniform prior, rollout
  evaluation. A trained value head changes the tree's shape and could change the
  sign, though no mechanism for that is known.
- **Reachability.** The sample is drawn from the configuration space, not from
  positions a strong agent reaches. EXP-005 and EXP-007 have **not run on the
  5×3**, so the unreachable share is unknown; on the 3×3 it was 3.28%. The
  reachable share is reported as unknown rather than assumed small.
- **h2's `t = 5` layer** is the most discriminating and the least independently
  verified: V4's coverage there is thin on both arms.
- **Cross-parent transposition is deliberately absent.** Two different parents
  reaching the same position get separate nodes here. That is a real search
  improvement this entry declines to measure, so "deduplication helps by X" must
  never be read as "transposition-aware MCTS helps by X" — the second is a larger
  and untested claim.

**Artefact.** `results/exp010-mcts-dedup-5x3-h2.json`, carrying every quantity
above including the floors, the per-layer table, and the realised `π_d`.

### EXP-011 — is the factored policy head too costly in the pipeline? (risk R5)

- **Registered.** 2026-08-30 at the Phase 4 opening; **revised the same day**
  after `experiment-redteam`, before any instrument existed. The first draft is
  superseded in full and nothing was run from it.
- **Objective.** Test whether the factored policy head's conditional-independence
  assumption is *too costly*, which is the question
  [adr-005](../docs/adr/adr-005-alphazero-scope-and-network.md) actually asks and
  requires to be "checked explicitly and logged, not assumed away". Risk **R5**.
- **The assumption.** 25 cell + 13 tile + 6 rotation logits combined as
  `log p(cell) + log p(tile) + log p(rotation)` — 44 instead of 1,950. It asserts
  that cell, tile and rotation are conditionally independent given the state,
  which is false on its face.
- **Hypothesis.** — none. A negative result changes the architecture, not a claim
  about FLIPHEX.

#### What the first draft got wrong about its own question

It measured supervised approximation error against the exact optimal policy and
let that fire fallback **(b)**. But adr-005 lists the mitigations *in order*, and
**(a) is "rely on MCTS to correct the prior, which is exactly what MCTS is
for"**. A supervised test contains no MCTS, so it cannot speak to the ADR's first
and primary defence — while being empowered to trigger the second. It is entirely
possible for 400 simulations to wash out a 7-point gap in the prior, which is
precisely what (a) claims.

The repair is to make the **MCTS-corrected readout primary** and the supervised
error secondary. This costs little: the searcher already exists as EXP-010's
instrument.

#### Ground truth and sample

`data/subgame-solutions/5x3-h2.json`, V5 digest
`51192b4d403ac1cb45c22d92ce58bab215843f457f245e7aca6d18744f8a3f43`, verified
before drawing. Same arm as EXP-010, for the reasons recorded there.

- **2,500 positions**, seed **23** — **a separate draw from EXP-010's**, so the
  two entries are not nested and their results may be read together.
- Stratified uniformly across `t = 5..14`; **restricted to positions that are a
  WIN for the side to move**, for the reason given in EXP-010.
- **Split 2,000 train / 500 held-out, declared here.** The first draft had no
  split at all, which made it a memorisation contest between a 720-logit output
  layer and a 29-logit one over 2,000 examples on a 0.33 M-parameter tower — a
  contest whose result would have been an artefact either way. **Every reported
  number is on the held-out 500.**

#### Arms and what they hold fixed

- **Factored** (29 logits on this deck: 15 cells + 8 tiles + 6 rotations) and
  **flat** (15 × 8 × 6 = 720 logits). Identical tower, optimiser, epochs, batch
  order, and training positions.
- **Each arm is trained independently, tower and head together** — the deployment
  configuration. This measures *network + head*, not the head in isolation, and
  that is deliberate: the decision adr-005 asks about is the pipeline's, and a
  frozen shared tower would answer a cleaner question that nobody has to act on.
  If the result is ambiguous, a frozen-tower arm is the diagnostic, registered
  then.
- **5 seeds per arm.** The first draft ran one, which is the error adr-005's own
  Phase 2 amendment already did the arithmetic for on the evaluator gate: the
  dominant noise is **training-run variance**, and no number of positions touches
  initialisation and SGD noise. Fixing the position sample and varying only the
  seed, the between-arm gap is compared against the **between-seed spread** — a
  gap smaller than the spread is not a result.
- **The conditioned arm (fallback (b)) is not run speculatively.** If the rule
  fires it is registered as an amendment with its own seeds, rather than being
  judged by the same threshold on the same held-out set — which would be a
  forking path with no multiplicity control.

#### The unit is the position, not the action label

Both the target and the metrics are defined over **distinct resulting
positions**, aggregating aliased actions. The first draft defined the target as
uniform mass over optimal *moves*, which under R13 already assigns up to 6× mass
to positions reachable by six rotations — so the flat head would have been scored
partly on reproducing alias multiplicity, and the measured gap would have been
contaminated by exactly the phenomenon EXP-010 exists to remove. That also
contradicted the first draft's own claim that the two entries are independent.
They are independent **only** under the position-level definition adopted here.

#### Metrics

1. **Primary — top-1 optimality after 400 PUCT simulations**, each head supplying
   the prior, on the held-out 500, at 5 seeds per arm. This is the quantity the
   decision is about, and the only one that can speak to mitigation (a).
2. **Secondary — supervised policy agreement** on the held-out 500: top-1
   agreement with the exact optimal policy, and cross-entropy against it, both at
   the position level. Paired across arms on identical positions; compared with
   McNemar (agreement) and a paired *t* on seed means (cross-entropy), 95%
   intervals on both.
3. **Reported beside both**: the random-legal-move floor per layer, as in
   EXP-010.

#### One number that needs no training at all

Computed first and reported regardless of how everything else turns out: the
fraction of (position, cell, tile) triples in the sample for which **rotation
does not change the resulting board**. adr-005's Phase 3 amendment claims "a
sizeable share of the rotation factor's output is not modelling a choice at all",
and that has never been quantified.

**Reported twice — with and without single-rotation-orbit tiles — and per layer.**
h2's P1 deck holds `P6`, whose orbit is 1, so rotation trivially changes nothing
for it **by orbit, not by the inertness mechanism the ADR describes**. Including
it inflates the headline by a definitional artefact. The number that supports the
ADR's claim is the one over multi-orbit tiles; the other is reported so nobody
recomputes it later and gets a different answer. (This is also why h2 is the
better arm here: 1 single-orbit tile in 8, against h1's 2.)

#### Decision rule

Read on the **primary** metric, on the held-out set, with the between-seed spread
reported alongside:

- Factored within **5 percentage points** of flat, *and* the gap no larger than
  the between-seed spread → the assumption is accepted for v1, adr-005 stands.
- Factored worse by **more than 5 points** *and* the gap exceeding the
  between-seed spread → **mitigation (a) has failed on its own terms**, and
  fallback **(b)** — rotation logits conditioned on the chosen cell — is
  registered as an amendment and run.
- Gap larger than 5 points but **within** the seed spread → not a result. Add
  seeds, do not adopt a fallback.
- If (b) is run and still loses by more than 5 points → fallback **(c)**, the
  flat head. **Recorded now so it cannot be forgotten later: (c) does not fix
  aliasing.** 1,950 logits over 1,450 actions is the same redundancy with more
  parameters; only EXP-010's deduplication addresses it.

#### Anti-circularity — the first draft's clearance did not hold

It argued compliance because "every network trained in this experiment is
discarded". That answers a question adr-005 does not ask. What survives is not
weights but the **architecture decision**, selected by fitting Axis 1 ground
truth on 5×3 positions and scored by agreement with the solver — and H3 later
reports Axis 2's per-variant agreement against Axis 1 on a comparison set that
**includes the 5×3**. The general form of the rule, from adr-004, covers this:
*neither axis may be used to select or terminate the other along the dimension on
which they are later compared.*

The leak is small — one ternary choice among fallbacks adr-005 already
enumerated — and is repaired here rather than argued away, by **both** available
repairs:

1. **H3's 5×3 comparison sample is drawn disjointly** from seeds 17 and 23. Both
   draws are recorded in their artefacts so the disjointness is checkable rather
   than asserted.
2. **If the decision rule fires**, H3's 5×3 member carries an
   architecture-selection caveat in the verdict table's evidence class. If it
   does not fire, no architecture was selected by Axis 1 and no caveat is needed.

The weights are still discarded — no network trained here seeds a self-play run,
initialises a generation, or contributes to a checkpoint. That was never
sufficient on its own.

#### Expected result, recorded before the run

- **Factored loses 0 to 4 points on the primary**, i.e. MCTS largely absorbs the
  prior's weakness, which is mitigation (a)'s claim.
- **Factored loses more on the secondary than on the primary** — 3 to 10 points
  of supervised top-1 agreement — with most of the loss on positions where
  several tiles are legal on the same strong cell. If the primary and secondary
  gaps come out equal, mitigation (a) is doing nothing and that is the more
  interesting finding.
- **Between-seed spread of 2 to 6 points** on the primary, which is the reason
  5 seeds are run.
- **Rotation irrelevant in over 30% of multi-orbit triples**, rising with the
  number of empty neighbours.

#### Threats to validity

- **The capacity ratio here is roughly half the deployed one, and the bias runs
  toward accepting adr-005.** The 5×5 head is 44 logits against 1,950 — **44.3×**.
  On the 5×3 h2 deck it is 29 against 720 — **24.8×**. Fewer cells and tiles means
  less joint cell×tile×rotation structure to lose, so conditional independence is
  a *less* costly assumption here by construction. **A pass at 5×3 does not
  license the 5×5.** Both head geometries go in the artefact so that "the
  factored head lost 2 points" is never quoted as a 5×5 number.
- **Trained against ground truth**, so the supervised metric is an upper bound on
  what self-play could extract; the primary metric is less exposed to this.
- **Reachability**, as in EXP-010: sampled from the configuration space, and the
  5×3's reachable share is unknown.
- **The searcher used for the primary is EXP-010's** — uniform-`c_puct`, rollout
  evaluation, deduplicated expansion. Whatever is wrong with it is wrong here too.

**Artefact.** `results/exp011-policy-head-5x3-h2.json`.

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
| 4 | **Transposition-aware MCTS** — children expanded by position vs by action, against risk R13's measured 4.46× root aliasing (adr-005 Phase 3 amendment) | — |
| 5 | First-player win rate, 20 seeds × 1000 games, Wilson CI | H1 |
| 5 | Joker-less variant, matched protocol | H2 |
| 5 | AZ vs solver at matched depth caps | H3 |
| 5 | Sensitivity: MCTS simulations, `c_puct`, temperature schedule | — |
| 6 | State-space and game-tree bounds; cross-game comparison table | H4 |
| 6 | Archetype placement frequency and win contribution | H5 |
| 6 | **Tile criticality** — for each archetype, the fraction of solved 5×3 positions whose value changes when that tile is removed from the hand | H5 |
| 6 | **Mirror-optimality rate** — on solved positions where the Z/2 mirror is a valid game symmetry (both `P3-y` placed), the fraction of optimal moves whose mirror image is also optimal | H5, H6 |
| 6 | **First-player advantage curve** — fraction of solved positions at each ply `t` won by the player to move, 5×3 | H1 |
