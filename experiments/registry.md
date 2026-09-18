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
| EXP-010 | 2026-08-30 | — | 2 | Deduplicated (by-position) MCTS expansion against the naive by-action tree, with a multiplicity-corrected control | 5×3-**h2** (V5 `51192b4d…`), 3,000 WIN positions stratified over `t = 5..14`, uniform prior + rollout leaves, 3 arms, primary at budget 400 | 17 | **complete** | **`B − A = +4.77` pts** [+3.47, +6.06] at the primary budget; falsifier did not fire; every registered prediction held. **The benefit is prior mass, not visit-splitting** — arm C keeps all 540 children, corrects only the priors, and recovers the whole effect (`B − C = −0.77`, not distinguishable from zero). Concentrated where a decision exists: **+8.9** pts on odd layers (floor 16.2%) against **+0.6** on even (floor 66.8%), with layers 12–14 saturated. Aliased mass **27.5%**, tree overhead **+19.6%** (inference cost absent — no network). 22.7 min. [`exp010-mcts-dedup-5x3-h2.json`](../results/exp010-mcts-dedup-5x3-h2.json) |
| EXP-011 | 2026-08-30 | — | 2 | Is the factored policy head too costly *in the pipeline*? (risk R5) | 5×3-**h2** (V5 `51192b4d…`), 2,500 WIN positions, 2,000 train / 500 held out, 5 seeds per arm, primary = top-1 optimality after 400 PUCT sims; arms **34** vs **1,170** logits (amended 2026-08-31) | 23 | **complete** | **The rule fires: fallback (b) is to be registered and run.** Flat beats factored **+7.0** pts on the primary metric (73.7% vs 66.8%, floor 39.6%), paired *t* **+6.96** [+4.81, +9.11], between-seed spread **1.5%** — the five seeds of each arm do not overlap. **Search did not close the gap**: the post-search deficit is +7.0 against a +8.0 supervised one, so mitigation (a) did not rescue the factored head (the 1-point ratio is a point estimate with no registered contrast behind it — see the correction). Factored is worse on *training* loss too (2.616 vs 2.375), so this is expressiveness, not generalisation. **Cannot separate independence from capacity** — 34 logits against 1,170, 0.33 M params against 0.88 M — and EXP-012 establishes that **no head-factorisation experiment can**, since relaxing the factorisation *is* adding output width; the claim that (b) would settle it is withdrawn (see the correction). Rotation is inert on only **11.4%** of multi-orbit (cell, tile) pairs, so the ADR's "sizeable share" claim is *not* the reason. Interval reaches +4.81, just under the 5-pt margin — recorded, not repaired. H3's 5×3 member now carries an architecture-selection caveat. [`exp011-factored-head-5x3-h2.json`](../results/exp011-factored-head-5x3-h2.json) |
| EXP-012 | 2026-09-01 | — | 2 | Fallback (b) — rotation conditioned on cell — and whether the **cell** is what it depends on | 5×3-**h2** (V5 `51192b4d…`), 2,500 WIN positions, 2,000 train / 500 held out, 5 seeds × 5 arms. **B (rot given cell), C (pooled control) and E (rot given tile) are identical in parameters and shape — 373,369 — and differ only in the readout index.** | 29 | **registered; rewritten in full after red-team; not yet run** | |
| EXP-013 | 2026-09-03 | — | 2 | The efficient parameterisation of (b): does sharing rotation weights across cells cost anything? | 5×3-**h2**, 12 seeds × 2 arms; `L_linear` 43,290 rotation parameters against `V_conv` **198** (a 1×1 convolution) | 29 | **complete** | **Adopt the convolutional form.** `V_conv − L_linear = +0.95` pts, lower limit **−0.06%** against a registered margin of −1.70%: non-inferior at 218× fewer parameters in the component the decision is about. On the shipped 5×5 the head drops to **347,887** parameters — below the factored head's own 352,495. Its registered secondary was found broken in two independent ways *before the run* and replaced by a dated amendment. [`exp013-conv-rotation-5x3-h2.json`](../results/exp013-conv-rotation-5x3-h2.json) |
| EXP-014 | 2026-09-04 | — | 2 | Pipeline shakedown before committing ~146 h: does the loop close, and does a `SIGKILL` mid-gate resume byte-equal? | Shipped 5×5, toy scale; four checks C1–C4 | — | **complete** | **All four pass, on the second attempt, and the measurement is the finding.** C4 failed first: a checkpoint written *inside* a gate replayed a finished generation, duplicating self-play and taking 400 more gradient steps, and **nothing raised**. Throughput is **145 games/h composed** against an engine-only 705 — R8's binding number was wrong by **4.9×**, and the gate, never parallelised, was **61%** of a projected 220.9 h. Worker optima differ by activity: self-play **6**, gate **4**. [`exp014-shakedown-5x5.json`](../results/exp014-shakedown-5x5.json) |
| EXP-015 | 2026-09-04 | H3 | 2 | The H3 training run: five seeds against the prior-free UCT floor | Shipped 5×5-`h1`, `ConvRotationNet`, 5 seeds × 30 generations × 200 games, gate every 5 at 400 games | 1–5 | **complete** | **Instability recorded; H3's clause 1 is not satisfied.** Four seeds clear the floor and one does not — seed 4 at **56.0% [49.1%, 62.7%]**, two games short. The five rates are 64.0 / 76.0 / 63.0 / 56.0 / 62.0%, a between-seed `sd` of **7.3%** against the **3.4%** sampling alone predicts, and homogeneity `χ² = 18.52` on 4 df **rejects a common rate**. 135.0 h, against ≈146 h projected. [`exp015-h3-training-5x5.json`](../results/exp015-h3-training-5x5.json) |
| EXP-016 | 2026-09-18 | H1 | 1 + 2 | H1's shipped-board arm: the first-player rate under named, imperfect play | Shipped 5×5-`h1`. Primary: prior-free UCT self-play, 400 simulations, **20 seeds × 250 = 5,000 games** (20.5 h at a measured 14.77 s/game). Secondary: the five EXP-015 champions, 250 games each | 1–20 | **withdrawn before running** | **Withdrawn 2026-09-18, same day, by red-team.** Prior-free UCT at 400 simulations visits **10–18 of 325** root children (4%) and the coverage is seat-dependent, so the design measured cell-enumeration order. Six further blocking findings, including a seed schedule sharing **975 of 5,000** player seeds. No data collected. Superseded by **EXP-017**. |
| EXP-017 | 2026-09-18 | H1 | 1 + 2 | H1's shipped-board arm: the first-player rate under exact endgame play | Shipped 5×5-`h1`. `SolverAgent` both seats (`max_nodes` 2M, `search_below_k` 8, heuristic fallback), **5,000 games, one match seed**, 11.0 h single-worker at a measured 7.95 s/game. Diversity from the heuristic's random tie-break; `proved_rate` ~31% | 1 | **complete** | **First player wins 2,712/5,000 = 54.2% [52.9%, 55.6%]**, interval entirely above 50%, under play that is heuristic for ~17 plies and **exact for the last 8** (`proved_rate` **32.0%**, and no rate may be quoted without it). 5,000/5,000 games distinct; ply accounting closes at 125,000 exactly. All three registered predictions held. **Corroborates H1's direction on a board no solver reaches; does not demonstrate it** — H1's evidence is the four exhaustive solves. [`exp017-first-player-5x5.json`](../results/exp017-first-player-5x5.json) |

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

#### Amendment (2026-09-18) — H2's registered measure has no decision rule, and measures something adjacent to H2

Written at the Phase 5 open, while reading H2 for its verdict. **No new
computation.** Three corrections to this entry's own H2 apparatus, two of them to
sentences written here.

**1. The registered measure was never given a threshold, and the number is
already known.**

This entry is emphatic that H2 must not be read from the roots:

> *"H2 is NOT reported from this. Both arms agreeing on a root value is one bit.
> The registered measure is the **criticality**."*

The reasoning is right — the power caveat about one bit against a 50% prior
stands. But the entry names the measure and **never says what value of it
supports or rejects H2**. The number has been on disk since Phase 3:
**17.069%**, from 1,237,229,498 of 7,248,350,863 positions where P1's extra tile
is still in hand.

So a threshold declared now would be chosen knowing the answer. **It is not
being declared.** This is the same defect EXP-006 recorded for its underived
`0.90`, and unlike that one it cannot be waved past with "the gap was large
anyway", because there is no gap without a bar.

**2. Criticality does not measure what H2 asserts, and the re-scope is a
reduction.**

H2 is *"removing the joker does not change **which player holds the theoretical
advantage**"* — a claim about the root. Criticality measures **positional
sensitivity**: how many individual positions change value when P1's extra tile
is swapped. No threshold on the second decides the first, at any value.

**What criticality actually does is better, and needs no threshold.** It is a
**validity check on the root comparison**. Had it come out near zero, the two
arms would be effectively the same game and their agreeing roots would carry
nothing. At **17.07%** over 7.2 × 10⁹ positions the arms are demonstrably
different games, so the agreement is one bit *about two genuinely distinct
objects* — which is what makes one bit worth having. The cross-arm verification
supports the same reading from the other side: **10,258,229,474 positions
compared, 0 mismatches**, so where the extra tile is already spent the two arms
are identical, exactly as they should be.

The question this re-scope has to answer is only *"is criticality bounded away
from zero?"*, and 17.07% answers it without a bar.

**3. What 17.07% means is deferred to Phase 6, which already plans the
comparison that would settle it.**

The interpretable question is not "is 17% big" but "is the joker more critical
than an ordinary archetype". Phase 6's planned **tile criticality** — the
fraction of solved 5×3 positions whose value changes when *each* archetype is
removed — supplies the reference distribution, and a rank within a measured
distribution needs no post-hoc threshold. Until then **17.07% is reported as a
magnitude and not interpreted**, and no artefact may call the joker "critical"
or "not critical" on the strength of it.

**What H2 can be concluded from, and it is enough for its own statement.**

| board | arm `h1` (extra tile = joker) | arm `h2` (extra tile = `P3-tri`) |
|---|---|---|
| 3×3 | **P1**, `termination: exhausted` | **P1**, `termination: exhausted` |
| 5×3 | **P1**, `termination: exhausted` | **P1**, `termination: exhausted` |

Four exhaustive solves, two boards, both arms, one answer. **Which player holds
the advantage does not change when P1's extra tile stops being the joker** — and
the criticality says the two arms are different enough for that to mean
something.

**4. The shipped 5×5 has no H2 arm, and two places in the code say otherwise.**

`Variant(5, 5, Arm.H2)` raises, correctly: at capacity 12 there is no next
archetype to promote, so on the shipped board the joker is the only tile that can
give P1 the extra ply. But the `ValueError`'s own message, and `Arm.H2`'s
docstring, both end by saying H2 is *"statistical on this one"*. **There is no
joker-less 5×5 to play, so that names no experiment**, and the locked H2 text
does not ask for one — it reads *"exact on 3×3/5×3"*. Both sentences are
corrected to say the shipped board is out of reach by construction.

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

#### Amendment (2026-09-16) — the measure is vacuous on lost positions, and the agent was never named

Amended **before the run**, which is the only time this is allowed. The sampling
design is untouched: same seeds, same 500 + 250 positions, same stratification,
same separation of the two strata, same `0.90` threshold. What changes is the
denominator that threshold is applied to, and three things the 2026-08-05 entry
could not fix because Axis 2 did not exist when it was written.

**1. "Whether the chosen move preserves the value" is vacuous on half the sample.**

Draws are impossible on 25 cells, so a position is a WIN or a LOSS for the side
to move. From a **LOSS**, every legal move leads to a position the opponent wins:
the value is preserved by *every* move, and the learner scores a hit whatever it
plays. Those positions are not measuring the learner. They are measuring the
fraction of the sample that happens to be lost.

Measured on the shipped 5×5 with **seed 99** — deliberately not seed 2 or seed 4,
so the registered samples stay unseen:

| `k` | side to move | positions | mover LOSES |
|--:|---|--:|--:|
| 6 | second | 40 | **13 (32.5%)** |
| 6 | second | 30 | **9 (30.0%)** |
| 7 | first | 40 | **3 (7.5%)** |

Median node counts came in at 6,626 and 16,019, against EXP-003's 6,660 and
20,024 — the cost model this entry was built on reproduces.

**What that does to the registered rule.** The reported rate decomposes as
`loss_fraction + (1 − loss_fraction) × accuracy`. Demanding 0.90 of it therefore
demands **85.2–85.7%** accuracy at `k = 6`'s two measured mixes and **89.2%** at
`k = 7`'s: one
threshold meaning two different things, with the pooled meaning fixed by a mix
the entry never measured. And the measure's floor is not zero — a mover playing
at random scores the whole loss fraction for free.

**The mix is structural, not noise.** `t = 25 − k`, and the side to move
alternates with `t`, so `k ∈ {6, 8}` puts the **second** player on move and
`k = 7` the **first**. The second player is lost about four times as often. That
is consistent with H1 and is **not evidence for it** — these are sampled
positions under a random-playout bias, not game values — but it does mean the
loss fraction swings with `k` parity by construction, which is the worst possible
property for a rate pooled across `k`.

**The fix: the denominator becomes positions the mover wins.** The decision rule
runs on the subset where the root value is **WIN**, where a wrong move actually
throws the game away. Lost positions are **counted and excluded**, never scored
as hits. Per-`k` and pooled rates are reported on this denominator.

**The threshold stays at 0.90** and is therefore *stricter* than registered, not
looser. That direction is deliberate: discovering that a measure was inflated is
not a licence to re-tune the bar to the inflation. The arithmetic above says what
0.90 used to buy.

**One residual, closed by measurement rather than assumption.** A WIN position
where *every* move also wins would be non-discriminating in the same way. In the
30-position probe at `k = 6` there were **zero** such positions, and among the 21
discriminating ones the share of legal moves that throw the win away had a median
of **89.7%** (min 2.8%, max 98.8%) — so a random mover would agree on roughly a
tenth of them. Because zero is a measurement on one `k` at one sample size and
not a proof, the instrument runs the full child sweep on a **pre-declared
calibration subsample of 100 positions** drawn from the registered stratum, and
reports the non-discriminating count and the random-move baseline beside the
headline rate. The remaining positions need only their root value, which keeps
the sweep's cost bounded.

**2. The entry never says which agent "the learned policy" is.**

It could not: it was registered on 2026-08-05, before Axis 2 existed, and that
ordering is the entry's whole point. EXP-015 has since produced **five**
champions and established that they are not interchangeable — one of the five
fails the prior-free floor, and the between-seed spread rejects a single
underlying strength (`χ² = 18.52`, 4 df).

**All five champions are evaluated, and the rule is per seed.** Reporting one
agreement rate would hide exactly the variance EXP-015 measured, and picking the
best seed would select on the outcome. So:

- Each of the five EXP-015 champions plays the whole sample.
- **H3's clause on this member is satisfied only if every seed's Wilson lower
  bound exceeds 0.90.** A seed that fails is recorded, not averaged away — the
  same falsifiability structure EXP-015's clause 1 uses, for the same reason.
- The five rates and their spread are reported whatever happens.

**3. The evaluation budget is pinned at 400 simulations.**

Also unspecified, and it is not a detail: agreement from the raw policy head and
agreement after search are different claims. 400 is what EXP-015's floor matches
and self-play both used, so this measures the agent **as deployed** rather than a
configuration that exists only for this table. `dirichlet_weight = 0` and the
position's ply (17 to 19) is far past `EVALUATION_TEMPERATURE_PLIES = 4`, so
selection is deterministic `argmax` over visit counts; the search seed is
recorded regardless.

**The raw prior is reported beside it, descriptively.** One forward pass, no
search, `argmax` over the masked policy — it costs almost nothing and it is the
quantity EXP-011, EXP-012 and EXP-013 all measured on the 5×3, so it is the only
figure in this entry that can be read against the architecture decisions. It
**gates nothing**: the decision rule is the 400-simulation arm.

**What this amendment does not change.** No sample, no seed, no stratification,
no threshold, and no part of the anti-circularity argument: ground truth is still
produced by `solver/minimax.py`, which proves or raises, and this measurement
still gates nothing in Axis 2 — EXP-015 is finished and its champions are frozen.

#### Result (2026-09-17) — H3 fails on the shipped game, by fourteen points

Two runs. `scripts/exp006_ground_truth.py`, **4.39 h**, artefact
[`5x5-endgame-seed2.json`](../data/ground-truth/5x5-endgame-seed2.json);
`scripts/exp006_agreement.py`, ~40 min, artefact
[`exp006-agreement-5x5.json`](../results/exp006-agreement-5x5.json) with the
per-position rows beside it in `exp006-agreement-5x5.jsonl`.

#### The ground truth

**749 of 750 positions proved**, one excluded at the 20,000,000-node budget and
recorded rather than replaced. The registered stratum is **complete: 500 of 500,
zero exclusions**, so the decision rule's sample is entirely exhaustive under
adr-004 R1.

| stratum | drawn | excluded | won by the mover | denominator |
|---|--:|--:|--:|--:|
| registered | 500 | **0** | 352 | **70.4%** of drawn |
| layer_uniform | 250 | 1 | 158 | 63.2% of drawn |

**The 2026-09-16 amendment was necessary by a wider margin than it argued.** It
was written from probes putting the lost fraction at 30–32.5% (`k = 6`) and 7.5%
(`k = 7`); measured on the real sample it is **39.2%**, **3.6%** and **46.1%** at
`k = 6/7/8`. Under the original rule, **148 of the registered stratum's 500
positions** would have scored a hit before the learner moved.

**The calibration sweep caught what the probe missed.** 100 positions, every
distinct child solved. Its pre-registered check **holds**: on all 26 lost
positions in the subsample, every child is a win for the opponent — the
amendment's central claim is now verified rather than argued. But **3 of the 74
won positions have no losing move at all**, and are vacuous for the same reason.
The probe behind the amendment found zero in 30 and the amendment said so
explicitly — "zero is a measurement on one `k` at one sample size and not a
proof" — which is the only reason the sweep was registered at all.

**The floor the rate sits on.** Median share of legal moves that throw the win
away: **78.1%** (min 2.8%, max 98.8%). **A random mover agrees on 21.9% of won
positions.** No rate below may be quoted without it.

#### The rule: every seed fails

Champion at 400 simulations, registered stratum, 352 positions, agreement scored
by **value preservation** — the chosen move is applied and the child is solved
exactly — never by identity with the solver's move.

| seed | agrees | rate | Wilson 95% | verdict |
|--:|--:|--:|:--|:--|
| 1 | 266/352 | 75.6% | [70.8%, 79.8%] | **FAILS** |
| 2 | 271/352 | 77.0% | [72.3%, 81.1%] | **FAILS** |
| 3 | 267/352 | 75.9% | [71.1%, 80.0%] | **FAILS** |
| 4 | 262/352 | 74.4% | [69.6%, 78.7%] | **FAILS** |
| 5 | 266/352 | 75.6% | [70.8%, 79.8%] | **FAILS** |

> **H3 fails on the shipped game.** All five, against a 0.90 bar. It is not
> marginal: the **upper** limit of the best seed is 81.1%, nine points below the
> threshold. Per the registration the reduced boards cannot rescue this —
> carrying the shipped game is the entire reason this member exists.

**The ladder, which is the useful way to read 75.7%:**

| | rate |
|---|--:|
| random mover | 21.9% |
| raw prior, no search | 53.5% |
| **champion, 400 simulations** | **75.7%** |
| required | 90.0% |

Search is worth **+22 points** over the raw prior and the prior is worth +32 over
random, so the learner is emphatically doing something. It is simply not doing
enough, and the gap is 14 points rather than one or two.

#### Why the measurement is believed

Recorded because a unanimous failure is exactly the shape an instrument defect
takes.

**The depth gradient.** Across all five seeds and **both** arms the rate is
monotone in difficulty:

| arm | `k = 7` (mover has the extra tile) | `k = 6` | `k = 8` |
|---|--:|--:|--:|
| search | 85.7–89.4% | 69.3–78.2% | 51.1–62.2% |
| prior | 68.3–77.0% | 32.7–47.5% | 27.8–44.4% |

A broken scorer does not produce that ordering ten times out of ten.

**Independent re-derivation.** Ten rows drawn at random from seed 1's search arm,
each recomputed with a fresh solver and a fresh transposition table: **10/10**
roots re-solve to WIN, **10/10** moves reproduce from the recorded search seed,
**10/10** verdicts confirm. **Zero** child solves hit the node budget, so no
position went unscored.

**A re-run changed nothing.** The whole measurement was launched a second time
and produced a byte-identical artefact.

#### The two strata: the Takizawa gap is real, and larger than it looks

Gaps are `layer_uniform − registered`, in points; standardised re-weights
`layer_uniform`'s per-`k` rates to the registered stratum's `k` mix.

| seed | registered | layer_uniform | raw gap | standardised | std. gap |
|--:|--:|--:|--:|--:|--:|
| 1 | 75.6% | 69.0% | −6.6 | 66.5% | **−9.1** |
| 2 | 77.0% | 70.9% | −6.1 | 69.6% | **−7.4** |
| 3 | 75.9% | 69.6% | −6.2 | 67.6% | **−8.3** |
| 4 | 74.4% | 70.9% | −3.5 | 69.0% | **−5.5** |
| 5 | 75.6% | 77.2% | **+1.6** | 76.1% | **+0.6** |
| **mean** | **75.7%** | **71.5%** | **−4.2** | **69.8%** | **−5.9** |

Four of five seeds are worse off the play distribution. **And the raw comparison
understates it**, because the two strata do not hold the same mix of `k`:
`layer_uniform` is **easier** by composition — 51.3% of its denominator is
`k = 7` against the registered stratum's 45.7%, and only 19.6% is `k = 8` against
25.6%. Standardising `layer_uniform`'s per-`k` rates to the registered mix moves
the gap from **−4.2 to −5.9 points**.

This is the FLIPHEX measurement of Takizawa 2023 §5 — that an evaluator's
systematic errors concentrate where play does not go — and it is what the
2026-08-07 amendment registered the second stratum to find. **The strata are not
pooled**, and seed 5 reversing the sign is reported, not smoothed.

Two limits on it. `layer_uniform` is uniform over the *layer*, not over the
reachable set, which is not implementable at 5.017e16 configurations; the orphan
filter rejected **zero** positions across all 250 draws, which is what a `2**-17`
rate predicts and confirms it is a correctness guard rather than a filter. And
250 positions across five seeds is a small basis for a 5.9-point claim.

#### The seed spread collapsed, and that is a finding

The same five champions, two measurements:

| | mean | sd | range |
|---|--:|--:|--:|
| solver agreement (here) | 75.7% | **0.9%** | 74.4–77.0% |
| prior-free UCT floor (EXP-015) | 64.2% | **7.3%** | 56.0–76.0% |

**The instability EXP-015 measured does not appear here.** Seed 4 — the one that
failed EXP-015's floor and whose `χ² = 18.52` rejected a common rate — is
ordinary in this table, 1.2 points below the best.

**This does not resolve EXP-015's instability; it says the two measures are
measuring different things.** A plausible mechanism is that the floor is a whole
game, where a strength difference compounds over 24 plies, while this is a single
decision in a deep endgame — but that is an inference from two numbers and is
**not measured**. What is established is narrower and still useful: *endgame
value agreement is far more stable across training seeds than head-to-head
strength is*, so a run's seed variance is a property of the measurement as much
as of the learner.

#### A caveat on the threshold, stated rather than left implicit

**The 0.90 was pre-declared on 2026-08-05 and never derived.** The entry fixes it
without an argument from anything measurable, which for a negative verdict would
normally be a serious weakness — a bar set by taste can fail a learner that a
justified bar would pass.

It does not matter here, and the reason is arithmetic rather than rhetorical: the
observed rates are **75.7%**, their best upper limit is **81.1%**, and no
plausible re-derivation moves a threshold far enough to reach that. The caveat is
recorded because the *next* entry to use this bar may land near it, and then the
missing derivation will decide the outcome.

#### What this establishes, and what it does not

**H3's clause 2 fails on the shipped-5×5 member.** The clause names three
members — 3×3, 5×3, and this one. The other two are read separately and are not
touched here; this member alone is decided, and it is decided against.

**Together with EXP-015, both of H3's clauses now have negative verdicts.**
Clause 1 (stability across seeds) was recorded as instability on 2026-09-16;
clause 2 fails on the shipped game here. H3 is not closed by this entry — the
3×3 and 5×3 members remain — but no combination of the remaining reads can
convert either verdict.

**Not established.** That the architecture is wrong, that the budget is wrong, or
that more training would close a 14-point gap: nothing here varies any of those,
and attributing the failure to one of them would be a story, not a measurement.
That the learner is weak in general — it beats prior-free UCT on four seeds of
five and beats a random mover by 54 points here. And nothing about play away from
`k ≤ 8`: these are endgames, sampled at three depths, on one machine.

**No re-run.** Retraining, re-tuning or re-sampling to move 75.7% toward 90%
requires a new registered entry. Selecting on this outcome is precisely what the
pre-registration exists to prevent.

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

#### Result (2026-08-31) — 1,360 s, `B − A = +4.77` pts, and the benefit is prior mass

Artefact [`results/exp010-mcts-dedup-5x3-h2.json`](../results/exp010-mcts-dedup-5x3-h2.json).
3,000 positions, PyPy 3.11.15, 22.7 minutes. **Every pre-registered prediction
held**; the falsifier did not fire.

| budget | A naive | B dedup | C mult-corrected | `B − A` | `B − C` |
|--:|--:|--:|--:|--:|--:|
| 100 | 66.63 | 67.83 | **70.83** | +1.20 [+0.03, +2.37] | **−3.00** [−4.26, −1.74] |
| **400** | 74.17 | **78.93** | 79.70 | **+4.77** [+3.47, +6.06] | −0.77 [−2.11, +0.58] |
| 1600 | 83.30 | **86.33** | 84.43 | +3.03 [+1.88, +4.19] | **+1.90** [+0.74, +3.06] |

Realised discordance put the detectable difference at **1.86 points** against the
registered 2-point margin — the design had the power its falsifier needed, which
the first registration did not.

**The benefit is prior mass, not visit-splitting.** At the primary budget
`C − A = +5.53` [+4.17, +6.90] while `B − C = −0.77` [−2.11, +0.58] is not
distinguishable from zero. Arm C keeps all 540 children and only corrects their
priors, and it recovers the whole effect. This is the case the entry
pre-registered as *"reported as such rather than as a vindication of both
mechanisms"* — mechanism **(ii)** carries the result and mechanism **(i)** is not
shown to contribute at 400 simulations. **The design does not change: adr-005
mandates B**, and B is also the arm that gets there with a quarter of the
children.

**The sign of `B − C` inverts with the budget** — C ahead by 3.00 points at 100,
B ahead by 1.90 at 1600, both intervals excluding zero. A coherent story is
available (few simulations reward keeping more distinct children to explore;
many simulations make split counts start to hurt), and it is **not being told as
a finding**: budgets 100 and 1600 are registered as secondary and descriptive
with no decision rule, precisely so that three tested budgets could not fire
somewhere under the null. Promoting this to a claim requires its own
registration.

**Nearly half the sample could not discriminate, and the per-layer table says
so.** Split by the parity EXP-009 identified:

| | n | random floor | A | B | `B − A` |
|---|--:|--:|--:|--:|--:|
| odd `t` (mover rarely wins) | 1,500 | 16.2% | 54.4 | 63.3 | **+8.9** |
| even `t` | 1,500 | 66.8% | 93.9 | 94.5 | +0.6 |

Layers 12, 13 and 14 are **saturated** — all three arms at ≥ 99%. The pooled
`+4.77` is an average over two populations that have nothing to do with each
other: where a decision exists the effect is roughly nine points, and where a
random move already scores 67% there is nothing left to win. The strongest layer
is `t = 5`: floor 3.0%, A 24.3%, **B 43.7%**, with 55.1% aliased mass. Quoting
the pooled figure without this table would misdescribe the result in both
directions.

**Predictions, checked.** `B > A` by 2–8 points at budget 400 → **+4.77** ✓.
Aliased mass 20–45% → **27.5%** ✓. C between A and B, nearer B → C in fact
*level with or above* B at the primary budget, which is the stronger form of the
same prediction. Tree overhead under 20% → **+19.6%**, held, but only just.
Margin shrinking as budget rises → held for `B − A` from 400 to 1600 (+4.77 to
+3.03), **not** from 100 to 400 (+1.20 to +4.77), which the entry did not
anticipate and which the low-budget inversion above explains.

**Cost, and what it is not.** Tree overhead is **+19.6%** at the primary budget
(25.4 ms → 30.4 ms per search). **Inference cost is absent by construction** —
there is no network here — and in deployment deduplication *reduces* the number
of distinct children to evaluate, so the pipeline's sign is plausibly the other
way. The 19.6% may not be quoted as the pipeline's overhead.

**One thing this does not license.** Cross-parent transposition is deliberately
not implemented, so *"deduplication helps by 4.77 points"* must never become
*"transposition-aware MCTS helps by 4.77 points"*. And the 5×3 at `t ≥ 5` sits
near the 5×5's ply 8 (~1.8× collapse) rather than its root (4.46×): the direction
transfers, the magnitude does not.

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

#### Amendment (2026-08-31) — the arms' logit counts, corrected against the built network

**Nothing has been run. The arms above were written on 2026-08-30, before
`az/network.py` existed; the network as built does not have the shapes they
name.** The registration is amended rather than rewritten, so the drift is
visible.

**The factored head is 34 logits on this deck, not 29.** The tile factor emits
one logit per tile in the *full* set of 13, not one per tile in this variant's
deck, because the Phase 4 amendment to
[adr-005](../docs/adr/adr-005-alphazero-scope-and-network.md) made the layout
variant-independent: plane `k` and logit `k` mean the same thing on the 3×3, the
5×3 and the 5×5, and the hand mask decides which are legal. So the factored arm
is **15 cells + 13 tiles + 6 rotations = 34**.

**The flat head is 1,170 logits, not 720 — and this one is not bookkeeping.**
`15 × 8 × 6 = 720` sizes the flat head to the eight tiles this deck happens to
contain. That would hand the flat arm a piece of information the factored arm is
not given: which tiles exist in this variant. The flat head would enter the
comparison with the action space pre-restricted, which biases the measurement
**toward the flat head** — the arm whose win fires a fallback and amends the
architecture. Being sloppy in that direction is the expensive one. Both arms
therefore span the same action space, `15 × 13 × 6 = **1,170**`.

**What this changes about the question.** The comparison is a ratio of output
widths, and the amendment moves it:

| | registered 2026-08-30 | as built |
|---|--:|--:|
| factored | 29 | **34** |
| flat | 720 | **1,170** |
| ratio | 24.8× | **34.4×** |

The 5×5 figure adr-005 argues from is `44` against `1,950`, a ratio of **44.3×**.
The corrected 5×3 ratio is closer to it than the registered one was, so the
reduced board is now a slightly better proxy for the board the decision is
actually about. That is a happy accident of the repair, not a reason for it.

**Unchanged:** the ground truth and its digest, the seed (23), the sample size
and split, the stratification, the five seeds per arm, every metric, the decision
rule and its 5-point margin, and the anti-circularity repairs. The tower is
measured at **332,965** parameters on the 5×3, which is the "0.33 M" the split
argument above was written against.

**Instrument note.** `az/train.py`'s loss is reusable here unchanged — its policy
term takes any `π` — but this experiment trains **supervised against exact
optimal play**, not on self-play targets, so the batches come from the solved
database rather than from `az/selfplay.py`. The flat head does not exist yet and
is part of the instrument to be built.

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

#### Result (2026-09-01)

Run `scripts/exp011_factored_head.py`, 2h16, artefact
[`exp011-factored-head-5x3-h2.json`](../results/exp011-factored-head-5x3-h2.json),
log [`exp011.log`](../results/exp011.log).

**The registered rule fires. Fallback (b) is to be registered and run.**

| | factored | flat | gap |
|---|--:|--:|--:|
| **Primary — top-1 optimality after 400 PUCT sims** | **66.8%** | **73.7%** | **+7.0** |
| Secondary — supervised top-1 agreement | 58.6–60.8% | 65.6–68.6% | **+8.0** |
| Between-seed spread (max of the two arms) | | | 1.5% |
| Random-legal-move floor | | 39.6% | |

Per seed, primary: factored `67.2, 66.6, 66.2, 65.8, 68.0`; flat
`74.2, 74.2, 75.6, 71.8, 72.8`. **Every one of the five factored seeds is below
every one of the five flat seeds** — the arms do not overlap at all, which is
what the 1.5% spread against a 7.0-point gap says in a different way.

Paired *t* on seed means: **+6.96** [+4.81, +9.11]. Supervised McNemar over all
seeds: **+8.0 points**, 680 discordant.

> **Correction (2026-09-01, red-team).** The interval first published here for the
> supervised McNemar, `[+6.0, +10.0]`, is **wrong and is withdrawn**. It was
> computed with `n = 2500`, but those 2,500 rows are 5 seeds × the *same* 500
> held-out positions — five re-measurements of one sample, not 2,500 independent
> pairs. Treating the position as the independent unit widens the half-width by
> about `sqrt(5)`, from ±2.0 to roughly **±4.6** points. The point estimate of
> **+8.0** stands; the interval does not. The instrument's `mcnemar()` inherits
> the defect and must cluster on positions before it is reused.
>
> **This does not touch the verdict**, which reads on the primary metric's paired
> *t* over seed means — a test whose unit is the seed and which was computed
> correctly. One clause of that is under-stated, though: it is correct
> **conditional on the fixed held-out set**. It contains no position-sampling
> component at all, so `+7.0 [+4.81, +9.11]` is an interval for the difference
> *on these 500 positions*, not for the difference on the 5×3. Generalising it
> carries an unmeasured component; EXP-012 states this estimand distinction for
> itself and this entry should not be read as claiming otherwise.
>
> **It does weaken one sentence below.** See the note under mitigation (a).

#### The sharpest number is the one about mitigation (a)

adr-005's first mitigation is *"rely on MCTS to correct the prior, which is
exactly what MCTS is for"*, and the whole reason this entry was rewritten after
red-team was so the primary metric could speak to it. It does:

- supervised gap: **+8.0** points
- gap after 400 PUCT simulations: **+7.0** points

**Mitigation (a) did not rescue the factored head.** The supervised deficit was
+8.0 and the post-search deficit +7.0: the gap survives the search essentially
intact, and the post-search gap of **+7.0** [+4.81, +9.11] excludes zero
comfortably. That is the finding, and it is a stronger statement than "the flat
head is better".

> **Correction (2026-09-01, red-team).** The first wording said search closed
> "roughly an eighth" of the deficit and called mitigation (a) "close to inert".
> **The ratio is a point estimate with no interval on it.** The supervised gap
> and the post-search gap were never contrasted as a tested difference, and once
> the supervised interval is widened for clustering (above) a 1-point difference
> between +8.0 and +7.0 is well inside the noise. What survives is the robust
> claim — **search did not close the gap** — not the arithmetic of how little it
> closed. A registered contrast of the two gaps would be needed to say more, and
> none was registered.

#### Not overfitting, and not early stopping

Final *training* policy loss: factored **2.616**, flat **2.375**. The factored arm
is worse on the data it was fitted to, not only on the held-out set, so this is
an expressiveness limit rather than a generalisation one. More epochs would not
close it.

#### What this cannot separate, stated plainly

The flat arm carries **879,381** parameters against the factored arm's
**332,965** — the head is 1,170 logits against 34. The experiment therefore
cannot distinguish *"cell, tile and rotation are not conditionally independent"*
from *"44 logits is not enough capacity"*. Both are reasons the factored head
loses, and adr-005's question — is it **too costly** — is answered either way,
which is why the design was written at the pipeline level. But the *mechanism* is
not established here, and no sentence in the write-up may claim it is. The
registration's own contingency applies: a frozen-shared-tower arm is the
diagnostic, registered if it is wanted.

Fallback (b) — rotation logits conditioned on the chosen cell — is the natural
next probe, and is registered as EXP-012.

> **Correction (2026-09-01, red-team pass 2).** The sentence that stood here —
> *"If (b) recovers most of the gap, the mechanism was independence; if it does
> not, it was capacity"* — is **withdrawn as impossible, not merely unproven**.
> In this parameterisation *any* relaxation of the factorisation adds output
> dimensions, because relaxing the factorisation is what adding them means.
> Independence and output-width capacity are **the same axis**, so no experiment
> that varies the head's factorisation can separate them, and (b) cannot settle
> the question this paragraph assigned to it. EXP-012 carries the argument in
> full and replaces the question with one that is answerable: whether the
> **cell** is what rotation depends on, which is what adr-005 actually asserts.

#### Three further corrections (2026-09-01, red-team pass 2)

**The threats section below misdescribes this experiment's own instrument.** It
says the searcher uses rollout evaluation. `search_scores` in
`scripts/exp011_factored_head.py` passes `evaluate=evaluator.evaluate` — the
**network's value head**. The consequence matters: the primary metric is
therefore network-level, not policy-head-level, so a difference between arms
includes whatever their value heads learned.

**The threats section also quotes the withdrawn logit counts** — "29 against 720,
24.8×" — which the 2026-08-31 amendment replaced with 34 against 1,170, a ratio
of 34.4×. The arithmetic in that threat is computed on the superseded figures.

**"More epochs would not close it" is asserted from a single final-loss value**
with no convergence check behind it, and 2.616 against 2.375 are two point
estimates from five seeds each whose spread was not reported. EXP-012 pins a
schedule and reports a convergence criterion precisely because this inference had
nothing behind it.

#### The rule fired on its own terms, and the margin deserves a note

The registered rule reads on the **point estimate** and the between-seed spread:
*"factored worse by more than 5 points and the gap exceeding the between-seed
spread"*. 7.0 > 5 and 7.0 > 1.5, so it fires as written.

**But the paired-*t* interval is [+4.81, +9.11], and 4.81 is below the 5-point
margin.** Under the stricter reading EXP-010's red-team imposed on *its*
falsifier — the interval must exclude the margin, not merely the point estimate
clear it — this would be marginal rather than decisive. That stricter form was
never written into EXP-011's rule.

This is recorded, not repaired. Rewriting a decision rule after seeing the
numbers is precisely what pre-registration exists to prevent, and the direction
of the temptation here is towards the *weaker* conclusion, which makes it no more
legitimate. The verdict stands as the locked rule gives it; a reader who prefers
the stricter criterion has both numbers.

#### The number that needed no training

Over 2,500 positions and 51,250 `(cell, tile)` pairs:

| | |
|---|--:|
| rotation changes nothing, all tiles | **21.6%** |
| rotation changes nothing, multi-orbit tiles only | **11.4%** |

adr-005's Phase 3 amendment claims *"a sizeable share of the rotation factor's
output is not modelling a choice at all"*. **The honest reading is that 11.4% is
not a sizeable share.** The larger figure includes `P6`, whose orbit is 1 and for
which the property is vacuous — a definitional artefact, which is why both were
required. The rotation factor has more to model than the amendment supposed, so
this is *not* the reason the factored head lost.

#### Anti-circularity — the caveat is now live

The rule fired, so repair 2 of the clearance below applies: **H3's 5×3 member
carries an architecture-selection caveat in its evidence class**, because the
architecture was selected by fitting Axis 1 ground truth on 5×3 positions and H3
later reports Axis 2's agreement against Axis 1 on a set including the 5×3.
Repair 1 stands independently — H3's 5×3 comparison sample is drawn disjointly
from seeds 17 and 23.

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

**Artefact.** `results/exp011-factored-head-5x3-h2.json` (this line first
named `exp011-policy-head-…`, which was never the filename the instrument writes;
corrected 2026-09-01).

### EXP-012 — fallback (b), and whether the cell is what rotation depends on

- **Registered.** 2026-09-01. **Two red-team passes, both before any instrument
  existed; nothing has been run.** Pass 1 killed the first draft's central claim
  (see below). Pass 2 found that the repaired design was still biased toward its
  own registered predictions, and added the frozen-tower condition, the
  equivalence test on the control, and the corrections to arm E. Drafts 1 and 2
  are superseded in full.
- **Why it exists.** EXP-011's rule fired. adr-005 lists mitigations in order,
  (a) is refuted, so the next is **(b) — rotation logits conditioned on the
  chosen cell**.
- **Hypothesis.** — none. A result here changes the architecture, not a claim
  about FLIPHEX.

#### What the first draft got wrong, and it was the premise

It promised to separate *"cell, tile and rotation are not conditionally
independent"* from *"34 logits is not enough capacity"*, using a fourth arm that
matched parameter counts while keeping the factored structure. **That cannot
work, and not for want of a better control.**

EXP-011's confound lives on the **output width** — the dimension of the score
function the head can express over the action set — and the first draft's control
held that constant at 34 while the treatment raised it to 118. It varied the
wrong axis. Worse, the repair is not to pick a different control: in this
parameterisation *any* relaxation of the factorisation **adds output dimensions**,
because relaxing the factorisation is what adding them means. Independence and
output-width capacity are **the same axis**, and no experiment that varies the
head's factorisation can separate them.

So the question is replaced by one that can be answered, and which is closer to
what adr-005 actually asserts. The ADR does not say "the head needs more
capacity"; it says **"the best rotation depends heavily on the cell"**. That is a
claim about *which variable* rotation depends on, and it is testable at fixed
capacity.

#### Arms

One rotation tensor of shape `(15, 6)` is shared by three arms. **They are
identical in parameter count and tensor shape, and differ only in the index used
to read a row.**

They do *not* share a loss code path, and an earlier draft claimed they did. A
and C run `az/train.py`'s existing normaliser unchanged; **E needs a shape change**
(the closed form builds a `(B, 13, 6)` tile–rotation block against a `(B, 6)`
rotation vector); **B needs a structural change**, because its score is not
additively separable. Three paths across five arms, each verified separately —
see Correctness preconditions.

| arm | rotation term in the score | total params |
|---|---|--:|
| **A — factored** | `rot[r]`, a 6-vector (the incumbent) | 332,965 |
| **B — rotation given cell** | `rot[cell, r]` — fallback (b) | **373,369** |
| **C — pooled control** | `sqrt(15) × mean over rows of rot[·, r]` | **373,369** |
| **E — rotation given tile** | `rot[tile, r]` — **8 live rows**, see below | 373,369 nominal, **353,167 live** |
| **D — flat** | one logit per triple, 1,170 — fallback (c) | 879,381 |

C carries B's parameters and B's shape while its **function class is exactly
A's**: pooling collapses the 90 weights to a 6-vector, so its expressive
dimension over actions is 32, the same as A's. Gradients still reach all 90
weights. That is the point — C is *"B's parameterisation without the
conditioning"*.

**The `sqrt(15)` is not cosmetic.** `Linear(480, 90)` initialises its rows
independently, so a plain row mean has `1/sqrt(15) = 0.26×` the initial standard
deviation of a single row: C's rotation term would start at a quarter of A's and
B's scale. Identical parameter count and tensor shape do **not** imply identical
initialisation of the *function*, and this is the one place the difference is
systematic rather than random. Scaling by `sqrt(15)` leaves the function class
untouched and matches the initial variance exactly.

**C's equivalence to A depends on the optimiser being Adam**, and that is
load-bearing rather than incidental. Pooling gives each of C's 15 rows
`1/15` of the gradient A's single row receives; Adam's per-parameter
normalisation is scale-invariant, so all 15 rows take identical steps and the
pooled logit moves at A's rate. Under plain SGD the pooled logit would train 15×
slower and `C − A` would fail for a reason having nothing to do with the design.
The rotation tensor sits in a `weight_decay = 0` parameter group in **every** arm,
so that decay-to-signal ratios do not differ across parameterisations.

**Arm E is not capacity-matched to B, and an earlier draft said it was.** The
tensor has 15 rows; the 5×3-h2 deck holds **8 tiles**, so rows 7, 8, 9, 10 and 12
are never in any hand and rows 13–14 are not tile ids at all. **Seven of fifteen
rows receive no gradient**: 7 × 6 × 481 = **20,202 dead parameters, 5.4% of the
total.** Free score dimensions differ too — B has `15×6 + 13 − 1 = 102`, E has
`15 + 13×6 − 1 = 92`, so B is 11% more expressive.

`B − E` is therefore **confounded**, and the direction is not obvious: B is more
expressive, which helps when the sample suffices, and has 15 live rows to fit
against E's 8, which hurts when it does not. The training-loss diagnostic
registered below is what distinguishes the two readings. Stating the confound is
the repair; pretending to an exact match, as the previous draft did, is what is
being corrected. The previous draft was criticised for resting a design on a
0.12% parameter match — this deficit is 45× larger.

| contrast | what it asks |
|---|---|
| **B − C** | Does conditioning on the cell help, at identical parameters and shape? **adr-005's named mechanism.** |
| **E − C** | Does conditioning on the *tile* help, on identical terms? |
| **B − E** | Is the **cell** specifically the right conditioner, as the ADR claims? |
| **D − B** | Adoption: does (b) reach the flat head? |
| **C − A** | **Validity precondition** — see below. |

**C − A is a precondition, not a finding — and it is an equivalence test, not a
null test.** C and A have the same function class, so C − A should be
indistinguishable from zero. If C is materially *worse* than A, the control is
handicapped by its own parameterisation and `B − C` is positive by that handicap
alone, firing the mechanism branch on an artefact.

The obvious form — "the interval must contain zero" — is worthless here, and an
earlier draft used it. With a ±2.1-point half-width the interval contains zero
unless `|C − A|` exceeds 2.1, so **the noisier the run, the more certainly the
check passes**. A gate satisfied by failing to measure is not a gate, and a real
1.5-point handicap sits comfortably inside the band that would pass.

**The registered form is TOST at δ = 2 points**: the *entire* `C − A` interval
must lie within ±2. That is the right shape for "these should be the same", and
it fails when the run is underpowered instead of passing. δ = 2 because it is
about the half-width and about half the adoption margin. **If it fails, every
mechanism contrast is recorded as unresolved regardless of what it shows.**

Identical tower, optimiser, epochs, batch order and training positions across all
five. Trained jointly, tower and head together — the deployment configuration.

#### The frozen-tower condition

**Added after red-team pass 2.** Every arm above trains tower and head jointly,
which is right for the *adoption* decision — that is a pipeline decision and must
be measured in the deployment configuration. It is wrong for the **mechanism**
contrasts: a jointly trained tower can compensate for a head's structural
limitation, which shrinks `B − C` and `E − C` **toward zero**, which is the
direction of the registered predictions.

EXP-011 pre-registered a frozen-shared-tower arm as the diagnostic for exactly
this contingency, and two earlier drafts of this entry declined it. It is
included.

**Procedure.** At each seed, arm A's tower and `policy_conv` are trained as
usual, then **frozen**; the heads of B, C and E are fitted on the frozen
features. All three then see literally the same tower, so their difference is a
difference between heads and nothing else.

**Cost is small on the training side and not on the evaluation side.** With
everything up to the 480-dimensional features frozen, those features are computed
once per seed and cached, so the 15 head fits are close to free. The 400-simulation
search evaluation is not cached and adds 15 × 500 position-searches, about 1.9 h.

**How the two conditions are read together.** The frozen contrasts are the
head-level mechanism result; the joint contrasts are the deployment-level one. If
they agree, the mechanism claim is on firm ground. **If they disagree — the
mechanism visible frozen and absent jointly — that is itself the finding**: the
tower absorbs the head's limitation, which is an argument for the factored head
that adr-005 never made and which would be worth more than either contrast alone.

#### Arm B is one implementation of fallback (b), and not the efficient one

`Linear(480, 90)` is fifteen independent 480→6 maps with **no weight sharing
across cells** — 43,290 parameters to learn "which rotation, given which cell"
fifteen separate times.

The tower is convolutional and `policy_conv` already produces a `(32, 15)`
spatial map before its `Flatten`. A **1×1 convolution from 32 to 6 channels** on
that map gives per-cell rotation logits from shared weights over each cell's own
features: **198 parameters**, fully cell-conditioned, and statistically efficient
in precisely the way arm B is not. It would also not carry the data-efficiency
handicap recorded below, since the handicap is caused by the unshared
parameterisation.

**Recorded so the conclusion cannot overreach: a null on B is a null on *this* B.**
Neither branch of the decision rule licenses a statement about fallback (b) in
general. The convolutional form is the obvious follow-up and is not run here.
#### Ground truth and sample

`data/subgame-solutions/5x3-h2.json`, V5 digest
`51192b4d403ac1cb45c22d92ce58bab215843f457f245e7aca6d18744f8a3f43`, verified
before drawing.

- **2,500 positions, seed 29**, stratified uniformly across `t = 5..14`,
  restricted to WIN positions for the side to move.
- **2,000 train / 500 held out. Every reported number is on the held-out 500.**
- **5 seeds per arm**, 25 training runs, plus 15 frozen-tower head fits and 5
  convergence re-runs. EXP-011 took 2h16 for 10 runs. **Budget ~8 h**, of which
  about 1.9 h is the frozen condition's search evaluation.
- **Disjointness is measured, not asserted.** The artefact records a sorted list
  of the drawn layer indices and the measured intersection with EXP-010's seed-17
  and EXP-011's seed-23 draws. Both prior entries claimed checkable disjointness
  while recording only the seed, which makes the check depend on `draw_layer`
  never changing.

#### Schedule, pinned

EXP-011 left these to the instrument. With five arms whose heads span 16k to 563k
parameters at one fixed schedule, "capacity" and "optimisation budget at this
schedule" are not separable unless the schedule is fixed and convergence is
shown.

**40 epochs, batch 64, Adam at lr 1e-3, weight decay 1e-4** — EXP-011's values, so
the two entries are readable together.

**Convergence is reported, not assumed.** The criterion is the **training-loss
trajectory** — mean per-epoch improvement over the final five epochs, per arm and
seed — because that is what "under-trained" means and it is orders of magnitude
less noisy than the held-out metric.

One seed per arm is re-run at 80 epochs. That comparison is **paired on the same
500 positions and the same seed** (McNemar on per-position hits), which removes
position variance. An earlier draft triggered on "the held-out primary moves by
more than 2 points" *unpaired* — one seed's held-out primary has a Wilson
half-width of about ±4 points, so a 2-point movement is inside noise in both
directions and the trigger would have fired or not essentially at random, with
the power to void the whole run. EXP-011 inferred "more epochs would not close
it" from a final loss value with no convergence check behind it at all.

#### Metrics

1. **Primary — top-1 optimality after 400 PUCT simulations**, each head supplying
   the prior, on the held-out 500, 5 seeds per arm.
2. **Secondary — supervised top-1 agreement and cross-entropy**, position level.
3. **Reported beside both** — the random-legal-move floor, and a **pre-registered
   stratified read by layer parity**. EXP-010 measured the effect concentrated on
   odd layers (+8.9) against even ones (+0.6, floor 66.8%), where a random move
   is already optimal two thirds of the time. Against contrasts expected at 2–3
   points, pooling the two dilutes the signal. Registered here so it is a planned
   read and not a subgroup hunt.

The unit is the **position**, not the action label.

#### The test, named

EXP-011 said "the interval" without saying which, and two candidates in its own
artefact differ by more than 2×.

- **Adoption and mechanism are read on the paired *t* over the 5 seed means**,
  `t(4) = 2.776`, **conditional on the fixed held-out set**. This interval
  captures training-seed variance only.
- **The position-sampling component is reported separately** as a bootstrap
  **clustered on the 500 positions**, and the write-up quotes the wider of the
  two.
- **EXP-011's `mcnemar()` is not reused as written.** It divided by `n = 2500`
  where those rows are 5 seeds × the same 500 positions, understating the
  half-width by about `sqrt(5)`. The correction is recorded in EXP-011's result
  section; the instrument here clusters on positions.

#### Decision rule

**Adoption**, read on `D − B` at α = 0.05, following adr-005's order:

- **Interval entirely below 5 points** → **adopt (b)**. The architecture record
  is amended to the conditioned head; (c) is not run.
- **Interval entirely above 5 points** → (b) is refuted; **adopt (c)**, the flat
  head. Recorded now: **(c) does not fix action aliasing** — 1,170 logits over
  540 legal moves is the same redundancy with more parameters.
- **Interval spanning 5** → **not a result**; see the extension rule.

**Operating characteristics, computed in advance.** At the half-width EXP-011
observed (≈2.1 points on seed means):

| `D − B` | verdict |
|---|---|
| < 2.9 | adopt (b) |
| 2.9 – 7.1 | **not a result** |
| > 7.1 | refute (b), adopt (c) |

Two things follow and are accepted deliberately rather than discovered later.
The expected `D − B` is roughly 1 to 3.5, so **"not a result" is a likely
outcome**. And the refutation branch needs B to trail D by more than A did
(`D − A` was 7.0) — B strictly contains A, so **that branch is close to
unreachable**. This experiment is powered to *adopt or fail to decide*, not to
refute.

**Extension, bounded.** If the rule does not resolve at 5 seeds, **exactly one**
extension to **12 seeds** is run and the rule re-read **once**, at Bonferroni
α = 0.025. At 12 seeds the half-width falls to ≈1.27 and the indecision band
narrows from 2.9–7.1 to roughly **3.7–6.3** — tabulated here because the
extension is now the registered path for the *modal* outcome, not a remote
contingency. No further extension. Unbounded "add seeds until it clears" is
optional stopping, and it is also the channel by which the mechanism read leaks
into adoption — when the adoption interval straddles 5, the mechanism contrasts
are already visible and would inform how hard one pushes.

**Arm C is not adoptable.** It exists to be a control. If C is the strongest arm,
that is recorded and a new entry is registered; nothing is adopted from this one.
Arm E is likewise diagnostic — it is not one of adr-005's fallbacks.

**Mechanism**, exploratory, **never used to adopt**, and void unless the C − A
equivalence precondition passes.

**Only two of the three contrasts are independent**: `B − E = (B − C) − (E − C)`
exactly. The Bonferroni divisor is therefore **2**, giving α = 0.025 per contrast
and `t(4) = 3.169`, half-width **≈2.4** points. An earlier draft used 0.025 as if
for a family of two without noticing that three contrasts were registered; the
divisor is right and the *reason* was missing. A reader must also not treat three
agreeing contrasts as three pieces of evidence — the third is a linear
combination of the other two.

- `B − C` above zero → conditioning on the cell helps at fixed capacity; the
  ADR's named mechanism is supported.
- `B − C` containing zero → it is not supported at this sample.
- `E − C` above zero **and** `B − E` containing zero → conditioning helps but
  **the cell is not what matters** — the tile does as well. That would leave
  adr-005's remedy standing and its stated reason wrong, which is the outcome
  this design exists to be able to see.

**Power, stated in advance and at the corrected level.** Adoption is read at
α = 0.05 (half-width ≈2.1); the mechanism contrasts at α = 0.025 (half-width
≈2.4). At the mechanism level that is roughly 80% power at a true **3.4**-point
difference and about 55% at 2.4 points. **A true `B − C` below ~3.4 points will
not resolve**, and "not resolved" is then the reported outcome. An earlier draft
quoted a 3-point MDE computed at the uncorrected α; the corrected figure is worse.

The split one might most expect — "conditioning explains 2 points, the rest is
width" — sits below the detectable range **by design**, and no reinterpretation
after the fact changes that.

**The pairing buys nothing, and that is measured.** Backing the correlation out of
EXP-011's numbers gives ≈ −0.05 between arms across seeds: despite a shared
position sample, batch order and MCTS seeds, the paired design produced no
variance reduction. The power figures above assume independence and are correct
on that basis, but this design must not be described as paired-and-therefore-
powered. One repair is available and is taken: `FlipHexNet` constructs the value
head **after** the policy heads, so a change in head size shifts the RNG stream
and the value head initialises differently across arms at the same seed.
Constructing it first makes the entire non-policy network bit-identical across
arms. The artefact reports `sd(differences)` and the implied correlation.

#### Every registered prediction is a null, and the instrument leans that way

This is the structural finding of red-team pass 2 and it is recorded here because
no local repair removes it.

Predictions 1, 3 and 4 are all nulls, and **four independent properties of the
design push the contrasts toward zero**:

| force | effect |
|---|---|
| joint tower training lets the tower absorb a head's limitation | mechanism contrasts → 0 |
| B's rotation row `c` gets gradient only when cell `c` is empty — **36.7%** of positions against C's 100%, a 2.7× data-efficiency handicap | `B − C` → 0 |
| B has 15 live rows to fit against E's 8, from the same 2,000 positions | `B − E` → 0 |
| Bonferroni widening | all → 0 |

The frozen-tower condition removes the first. The other three remain.

None of this is misconduct — the biases are conservative rather than
self-serving, and the predictions were registered before any data existed. But it
means **a null confirms a prediction the design was going to produce anyway**.

Two consequences are registered now, so they cannot be forgotten when the numbers
are in:

1. **A null mechanism contrast is reported as "not detected", never as "absent".**
   No sentence in any artefact, note or write-up may convert one into the other.
2. **Per-arm final training loss is reported beside the held-out primary**, which
   is the diagnostic that separates the two readings. If B fits the *training* set
   better than C while not beating it on held-out, the limit is data efficiency
   and not the absence of the mechanism. This is exactly the move that let EXP-011
   say "expressiveness, not generalisation"; it costs nothing, since the loss is
   already logged.

#### Correctness preconditions

Both must pass before the run counts as evidence.

1. **Each arm's normaliser is verified against brute force.** Arm B's score is
   **not additively separable**, so the closed form `az/train.py` uses is invalid
   for it; the correct one is nested,
   `Z = LSE over empty c of ( cell[c] + LSE over available (t,r) of (tile[t] + rot[c,r]) )`.
   A and C are separable (a pooled rotation row is a 6-vector); E is separable
   too, since `rot[tile, r]` folds into the tile-rotation factor. Only B changes.
   A wrong normaliser does not raise — it optimises the wrong distribution and
   reads as a slightly worse arm, and it would land on **B specifically**, in the
   direction that refutes (b). Each arm must reproduce a
   `logsumexp`-over-generated-moves equivalence on three variants and three
   depths, matching the existing test's coverage.
2. **The C − A precondition above.**

#### Threats to validity

EXP-011 had a threats section; this inherits it and adds to it.

- **The targets are exact optimal play; deployment trains on MCTS visit counts.**
  EXP-011 framed this as a bound on *level*. The sharper risk is a **rank
  inversion between arms**: a constrained head is a regulariser, and against
  clean near-deterministic labels extra capacity is pure gain, while against
  noisy non-stationary self-play targets the ordering can change. Every arm here
  trains on labels the pipeline never sees. **If the ordering inverts under
  self-play targets, the architecture shipped by this entry is wrong in the
  deployed condition while the measurement reads clean.**
- **The sample is the low-branching tail.** Layers 5–14 of 16, WIN-for-mover
  only. The factored head's weakness should be largest where the joint
  cell×tile×rotation structure is richest — near the root, at 540 moves on this
  board and 1,450 on the 5×5. This measures it where it is **least** stressed,
  which biases toward accepting the factored family.
- **`dirichlet_weight = 0` at evaluation.** Deployment puts noise at the root,
  which partially masks prior differences, so this overstates the prior's
  influence relative to deployment.
- **The 5×3 understates (b) specifically.** B's conditioning is 15×6 here and
  25×6 on the 5×5, and cell–rotation interaction grows with the board. A
  (b)-loses result here would not license refuting (b) on the 5×5 — which is one
  more reason the refutation branch is not the one to lean on.
- **Mechanism claims are network-level, not head-level.** All arms train tower
  and head jointly, so `B − C` is a difference between two networks whose heads
  differ, not the isolated effect of a head term. **EXP-011 pre-registered a
  frozen-shared-tower arm as the diagnostic for exactly this**, and it is
  declined here deliberately: the adoption decision is a pipeline decision and
  must be measured in the deployment configuration. The cost is that the
  mechanism contrasts carry this limitation, and the C arm — identical shapes,
  identical parameters, same code path — is the mitigation, not a substitute.
- **Nothing here is evidence about the 5×5.**

#### Anti-circularity

The first draft claimed this entry "does not deepen the leak". **That was wrong
in three ways** and is replaced by a count.

1. The choice set is not adr-005's three fallbacks. Arms C and E are
   architectures invented for this experiment; C is explicitly not adoptable and
   E is diagnostic, but the enumeration is larger than the ADR's.
2. The selection is **cumulative and conditioned**: EXP-012's arms were chosen
   after seeing EXP-011's numbers. What adr-004 R1 protects is how much of the
   deployed architecture is a function of Axis 1's answers on a variant inside
   H3's comparison set, and that grows with each *decision*, not with each
   dataset.
3. Drawing seed 29 disjointly prevents statistical overlap between the selection
   sample and H3's evaluation sample. It does **not** touch the mechanism of the
   rule — the architecture is a function of solver labels on the 5×3, and H3
   reports agreement with the solver on a set including the 5×3. Disjointness is
   necessary and nowhere near sufficient.

**Therefore:** H3's 5×3 evidence class records **the number of architecture
decisions taken against 5×3 ground truth** — after this entry, **two**, over an
*adoptable* choice set of **three** (A stands, B, D). Five architectures are
trained; C and E are declared non-adoptable in this entry and are diagnostics.
The adoptable count is the one that measures the leak. The caveat scales with the thing it qualifies
instead of being a fixed sentence. The clean escape, if one is wanted later, is
to select on something that is not solver agreement: final self-play training
loss, or the plain-UCT floor adr-005's Phase 2 amendment already defines.

#### Expected result

Stated as interval claims the design can adjudicate, rather than point guesses
inside its own blind spot.

1. **The `C − A` interval contains zero.** If it does not, the precondition fails
   and the mechanism contrasts are void — this is the prediction whose failure
   costs the most.
2. **`D − B` lands in the "not a result" band (2.9–7.1).** Registered as the
   modal outcome so that indecision is not later reported as a surprise.
3. **The `B − C` interval contains zero.** The rotation-inertness measurement in
   EXP-011 — 11.4% over multi-orbit pairs — already undercut the ADR's claim that
   much of the rotation factor models no choice; this predicts its other claim,
   that rotation depends heavily on the *cell*, is also weaker than stated.
4. **`B − E` contains zero** — cell and tile work about as well as each other as
   conditioners.

Predictions 3 and 4 together say the ADR's stated mechanism is not what is
happening. If they hold while `D − B` is small, the honest reading is that the
flat head's advantage in EXP-011 was width, the conditioning recovers part of it
for reasons the ADR did not name, and the write-up must say so.

#### Artefact

`results/exp012-conditioned-head-5x3-h2.json`, written by
`scripts/exp012_conditioned_head.py`. Both named here so the provenance drift in
EXP-011's entry — which registered a filename the instrument never wrote — is not
repeated.

#### Result (2026-09-02) — the rule does not resolve at 5 seeds

Run `scripts/exp012_conditioned_head.py`, 8h50 (31,815 s), artefact
[`exp012-conditioned-head-5x3-h2.json`](../results/exp012-conditioned-head-5x3-h2.json),
log [`exp012-run.log`](../results/exp012-run.log). The verdict below is applied
by a separate script, `scripts/exp012_analysis.py`, so that it is reproducible
from the raw artefact rather than from an 8.8-hour run.

| arm | params | top-1 after 400 sims | sd | supervised | final train loss |
|---|--:|--:|--:|--:|--:|
| A_factored | 332,965 | 68.0% | 1.6 | 60.1% | 2.5787 |
| B_cell | 373,369 | **73.4%** | 1.8 | 66.1% | 2.4918 |
| C_pooled | 373,369 | 70.0% | 1.4 | 61.3% | 2.5853 |
| E_tile | 373,369 | 69.9% | 1.7 | 60.4% | 2.5126 |
| D_flat | 879,381 | **77.1%** | 1.6 | 69.7% | 2.3334 |
| random legal | — | 39.4% | — | — | — |

`D − B = +3.76 pts [+1.78, +5.74]` at t(4), α = 0.05. **The interval spans the
5-point margin: not a result.** That was registered as the modal outcome, and the
branch it selects is the one bounded extension — reported below.

**The pairing worked this time, and that was a registered repair.** `sd(differences)`
is 1.60 against arm sds of 1.6–1.8, implying a between-arm correlation of
**+0.554**. EXP-011 measured ≈ −0.05 and this entry recorded that its power
figures therefore assume independence. Constructing the value head **before** the
policy heads, so the entire non-policy network is bit-identical across arms at
one seed, is what changed, and it is now measured rather than argued.

#### The validity precondition failed, and it could not have passed

`C − A = +2.00 pts [−0.43, +4.43]`, half-width 2.43. TOST at δ = 2: **FAIL**.

The number that matters is not the estimate. **The half-width alone (2.43)
exceeds δ (2.00)**, so no point estimate whatsoever — not even exactly zero —
could have cleared this gate at five seeds. The test was unpassable before any
data existed.

The cause is in this entry's own text. δ was set at 2 points *because* that was
the forecast half-width. An equivalence test whose δ equals its expected
half-width passes only if the estimate lands near-exactly on zero **and** the
noise comes in under its own forecast. The observed `sd(differences)` was 1.95
against the ~1.5 the forecast implied, and the gate closed. **This is a design
defect, not a property of the arms**, and it is the second time in two entries
that a validity check has been written in a form that could not do its job — the
first was the "interval contains zero" form this TOST replaced.

Consequence, applied without discretion: **every mechanism contrast is
UNRESOLVED, regardless of what it shows.**

One observation is recorded and explicitly does **not** rescue the entry. The
gate's stated rationale above is that *if C is materially worse than A, the
control is handicapped and `B − C` is positive by that handicap alone*. C came
out **+2.0 points better** than A. The violation is in the opposite direction to
the artefact the gate exists to prevent, which makes `B − C` conservative rather
than inflated. That is post-hoc reasoning about a failed gate; it is a candidate
for a future registered entry and it changes nothing here.

#### Mechanism: joint and frozen disagree, and not in the anticipated direction

Recorded for completeness. **All six intervals are void** under the precondition.

| contrast | joint (deployment) | frozen tower (head-level) |
|---|--:|--:|
| B − C | +3.32 [+2.18, +4.46] | +0.88 [−1.10, +2.86] |
| E − C | −0.12 [−2.71, +2.47] | +1.16 [−0.53, +2.85] |
| B − E | +3.44 [+0.29, +6.59] | −0.28 [−1.94, +1.38] |

Frozen, the three arms land at **68.5% / 67.6% / 68.8%** — on top of A's own
joint 68.0%. **On a tower trained for the factored head, no head architecture
makes any difference at all.**

This entry registered the disagreement case in advance and named the direction it
expected: *"the mechanism visible frozen and absent jointly"*, the tower absorbing
a head's limitation. **The observed disagreement is the exact inverse.** Two
readings fit and neither is decided here:

1. The head only pays when it can rewrite the features — conditioning is a
   property of the co-adapted network, not of the head.
2. An A-optimal tower supplies no cell-conditional features, so a real mechanism
   would be invisible under freezing regardless.

The frozen condition was added after red-team pass 2 to *remove* a confound. It
introduced a different one, and the honest statement is that it did not resolve
what it was added to resolve.

#### The training-loss diagnostic, registered for exactly this

Registered so that "no mechanism" could be told apart from "not enough data":

- **B** fits the training set better than C (2.4918 vs 2.5853) **and** beats it
  held-out. Not a data-efficiency limit — expressiveness that realises.
- **E** fits better than C (2.5126) but is level with it held-out (69.9 vs 70.0).
  That is fitting without generalising, and it is where the data-efficiency
  reading applies.
- **D** is far below all of them at 2.3334 and best held-out, consistent with
  EXP-011: width.

#### Layer parity — the effect is on the odd layers

| arm | odd | even |
|---|--:|--:|
| A_factored | 48.2% | 86.3% |
| B_cell | 56.3% | 89.1% |
| C_pooled | 50.9% | 87.7% |
| E_tile | 51.2% | 87.2% |
| D_flat | 61.0% | 92.0% |

`B − A` is **+8.1** on odd layers against +2.8 on even; `D − B` is **+4.7**
against +2.9. The pooled figures are a mixture, and where the position actually
carries a decision the flat head's lead is larger than the headline.

#### Two registered reads the instrument never wrote

Both were recovered offline by `scripts/exp012_analysis.py`, because per-position
hits were saved:

- **The bootstrap clustered on the 500 positions.** For `D − B` its half-width is
  1.98, indistinguishable from the seed-mean interval's 1.98; for `C − A` it is
  **narrower** (1.64 vs 2.43). The registered rule is to quote the wider, so the
  seed-mean interval stands in both cases. The dominant variance is training-seed
  variance, not position sampling — which is what a fixed shared held-out set
  should produce.
- **`sd(differences)` and the implied correlation**, reported above.

A third registered read — the 80-epoch re-run — was **not** recoverable and had
never been implemented. It is discharged in the next section.

#### Result — convergence (2026-09-02): 40 epochs is the generalisation limit

Run `scripts/exp012_followup.py --leg convergence`, 1h53 (6,797 s), artefact
[`exp012-convergence-5x3-h2.json`](../results/exp012-convergence-5x3-h2.json).
Seed 0 per arm at 80 epochs, paired by McNemar against the 40-epoch row on the
same 500 positions. The registry does not name a seed; seed 0, the first
registered, is named here.

| arm | 40 ep | 80 ep | McNemar | train loss 40 → 80 |
|---|--:|--:|--:|--:|
| A_factored | 69.6% | 67.4% | −2.2 [−5.6, +1.2] | 2.5685 → 2.5387 |
| B_cell | 74.8% | 73.6% | −1.2 [−4.3, +1.9] | 2.4901 → 2.4437 |
| C_pooled | 71.4% | 71.4% | +0.0 [−3.4, +3.4] | 2.5738 → 2.5423 |
| E_tile | 70.8% | 71.0% | +0.2 [−2.8, +3.2] | 2.5062 → 2.4698 |
| D_flat | 79.6% | 76.4% | −3.2 [−6.4, +0.0] | 2.3315 → 2.2984 |

**Every interval contains zero: doubling the schedule moves no arm.** But
training loss fell in all five while held-out rose in none, and four of five
point estimates are negative. That is the signature of the arms sitting **at or
past** their generalisation optimum at 40 epochs, not short of it.

**This corrects a reading taken from the trajectory alone.** The per-epoch
improvement over the final five epochs was 0.0060–0.0087 across arms at 40
epochs on seed 0 and is still 0.0014–0.0032 at 80, so by the registered criterion
the loss is indeed descending throughout — and the first reading of that was "no
arm converged". (The 5-seed means at 40 epochs are lower, 0.0029–0.0043; seed 0
sits at the high end, which makes it the harder seed on which to argue that more
epochs would not help.) The trajectory answers
whether *optimisation* has finished, not whether *generalisation* has, and
generalisation finished first. The 40-epoch schedule is defensible and `D − B` is
not an artefact of the optimisation budget.

Two further readings, both weak and labelled as such. D degrades most (−3.2, the
only interval touching zero at its upper end), so on seed 0 `D − B` narrows from
+4.8 to +2.8 with more training — the opposite of "D leads because it needs more
epochs than it got". One seed at ±3 is inside noise and this is not treated as a
finding. And the **arm ordering is preserved at 80 epochs** (D > B > C ≈ E > A),
so the ranking-inversion threat did not materialise under more training; it
remains live under self-play targets, which is a different condition.

#### Result — the bounded extension (2026-09-03): adopt (b), by a quarter of a point

Run `scripts/exp012_followup.py --leg extension`, 3h54 (14,017 s), artefact
[`exp012-extension-5x3-h2.json`](../results/exp012-extension-5x3-h2.json). Seeds
5–11 for **B and D only**: adoption is read on `D − B`, and extending arms whose
contrasts are void would spend compute making unresolved numbers precise.

**`D − B = +3.32 pts [+1.88, +4.75]`** at n = 12, t(11) = 2.593, α = 0.025.
Entirely below the 5-point margin.

> **The rule fires: adopt fallback (b).** The architecture record in adr-005 is to
> be amended to the conditioned head. Fallback (c) is not run.

**It clears by 0.25 points**, and that is the number this result should be
remembered by. The indecision band at n = 12 with the observed variance is
3.56–6.44; the estimate landed at 3.32.

The 5-seed projection was optimistic on both axes. It assumed `sd(differences)`
would hold at 1.60 and gave [+2.57, +4.95]; the sd rose to **1.92** — five seeds
understated the variance — and the point estimate fell 0.44. The real interval is
both wider and lower than projected. At an uncorrected α = 0.05 the interval is
[+2.10, +4.54], so the significance level did not decide this; the margin did.

**The merge is guarded, not assumed.** Merging seeds 5–11 with rows 0–4 is only
legitimate if the pipeline still produces those rows, so `B_cell` seed 0 — the
conditioned path with the nested normaliser — was retrained and its hit vector
compared **element-wise**: 500/500 positions identical, training loss matching to
1e-9. A mean comparison would not have been evidence, since two runs can score
74.8% on different positions; the guard's failure path was validated on a
poisoned vector with two positions swapped in opposite directions, leaving the
mean unchanged.

#### What the adoption does not establish

Three limits, each already recorded above this section and none weakened by the
verdict.

1. **D still leads B by 3.3 points** (76.5% vs 73.2% at 12 seeds). The margin is a
   tolerance — the price adr-005 was willing to pay for the factored structure —
   not a claim of equivalence.
2. **The mechanism is unresolved.** adr-005's remedy is adopted while its stated
   reason, *"the best rotation depends heavily on the cell"*, is **not verified**.
   The precondition that would have licensed reading `B − C` failed.
3. **This is an adoption of *this* B.** The entry records above that
   `Linear(480, 90)` is fifteen unshared 480→6 maps at 43,290 parameters, and that
   a 1×1 convolution over `policy_conv`'s spatial map gives full cell
   conditioning in **198**. The entry's own sentence — "a null on B is a null on
   *this* B" — holds symmetrically for an adoption. The efficient form is
   unmeasured and is registered as the follow-up.

#### The margin changed role and was never rejustified

Recorded as the principal threat to this verdict.

Five points was EXP-011's **detection threshold** — a difference smaller than
this is not worth acting on. In this entry it is an **adoption tolerance** — a
loss up to this is an acceptable price for the factored structure. Those are
different quantities and the number was carried across without being rewritten.

Red-team pass 2 raised this and it was left unaddressed, which was a cheap
omission while it was hypothetical. **A decision that closes by a quarter of a
point against that constant makes it load-bearing.** Any future entry that
re-reads adoption on this margin must justify it in its adoption sense first.

#### Every registered prediction, scored

| # | prediction | outcome |
|---|---|---|
| 1 | `C − A` contains zero | The interval does contain zero — but the **registered form is TOST**, and it failed, unpassably. Scored as **failed**: the operative test is the registered one. |
| 2 | `D − B` lands in the 2.9–7.1 "not a result" band | **Correct** (+3.76). Indecision was registered as modal and was not a surprise. |
| 3 | `B − C` contains zero | **Wrong jointly** (+3.32, entirely above zero); right frozen (+0.88). Both void. |
| 4 | `B − E` contains zero | **Wrong jointly** (+3.44); right frozen (−0.28). Both void. |

The entry's own summary of 3 and 4 — *"together they say the ADR's stated
mechanism is not what is happening"* — cannot be claimed. The joint contrasts
point the other way and the frozen ones cannot arbitrate, because the
precondition that made either readable never passed.

#### Anti-circularity — the count after this entry

**Two** architecture decisions have now been taken against 5×3 ground truth
(EXP-011 refuting the factored head as sufficient; EXP-012 adopting the
conditioned head), over an *adoptable* choice set of **three** (A stands, B, D).
Five architectures were trained; C and E were declared non-adoptable in advance
and are diagnostics. H3's 5×3 evidence class carries this count.

#### Threats to validity, added by the result

The entry's own threats stand. These are added by what happened.

- **The verdict is a function of one constant that was reused across roles.** See
  above. The interval's upper limit is +4.75, so the adoption survives any margin
  above 4.75 points and flips below it. A margin of 4.7 — a 6% change in a number
  that was never rejustified for the role it is playing — reverses the verdict.
- **Five seeds understated the variance by 20%** (1.60 → 1.92). Any future power
  calculation on this pipeline that uses a 5-seed sd will be optimistic.
- **The frozen-tower condition introduced a confound while removing one.** It
  cannot distinguish "no head-level mechanism" from "an A-optimal tower supplies
  no features the mechanism could use".
- **Convergence was read on one seed per arm.** The McNemar half-widths are ±3
  points, so the 80-epoch comparison detects only large movements. "No arm moved"
  means no arm moved by more than about 3 points.
- **The adopted head is the inefficient implementation**, and the efficient one
  differs by 218× in parameter count in the part of the network the decision is
  about. It is not obvious that the two behave alike, and nothing here tests it.

#### Artefacts

| file | produced by |
|---|---|
| [`exp012-conditioned-head-5x3-h2.json`](../results/exp012-conditioned-head-5x3-h2.json) | `scripts/exp012_conditioned_head.py` |
| [`exp012-convergence-5x3-h2.json`](../results/exp012-convergence-5x3-h2.json) | `scripts/exp012_followup.py --leg convergence` |
| [`exp012-extension-5x3-h2.json`](../results/exp012-extension-5x3-h2.json) | `scripts/exp012_followup.py --leg extension` |
| [`exp012-guard-receipt.json`](../results/exp012-guard-receipt.json) | the reproduction guard, recording commit and digest |

The verdict is applied by `scripts/exp012_analysis.py` from the artefacts, not by
the run.

#### Follow-ups this entry creates

1. **adr-005 amendment** — the architecture record moves to the conditioned head.
   Required by the decision rule; the Axis 2 architecture may only change by ADR.
2. **A new entry for the convolutional form of (b)** — 198 parameters against
   43,290, full cell conditioning, named in this entry as the obvious follow-up
   and deliberately not run.
3. **An entry that can actually read the mechanism**, if the mechanism is still
   wanted. It needs an equivalence gate whose δ is not equal to its own forecast
   half-width, and a head-level condition that does not freeze the tower into one
   arm's optimum.


### EXP-013 — the efficient parameterisation of (b): does sharing weights across cells cost anything?

**Registered 2026-09-03, before the instrument exists.** Follow-up 2 of EXP-012.

#### What this asks, and what has already been committed

adr-005 now specifies a conditioned policy head, adopted by EXP-012 and amended
into the ADR on 2026-09-03. **That amendment adopted an implementation both it
and EXP-012 record as the inefficient one**, and both name this experiment as the
obligation that follows.

The adopted form is `Linear(policy_features, n_cells × 6)`: as many independent
maps as there are cells, with **no weight sharing**, learning "which rotation,
given which cell" once per cell. The tower is convolutional and `policy_conv`
already produces a `(32, n_cells)` spatial map. A **1×1 convolution from 32 to 6
channels** on that map produces per-cell rotation logits from weights shared
across cells, reading each cell's own 32-dimensional features.

| board | rotation head: factored (superseded) | linear-conditioned (adopted) | **1×1 conv** |
|---|--:|--:|--:|
| 5×5 (shipped) | 4,806 | 120,150 | **198** |
| 5×3 (measured here) | 2,886 | 43,290 | **198** |

The convolutional form is **218× smaller in the component the whole decision is
about**, and on the 5×5 it makes the conditioned network *smaller than the
factored incumbent it replaced* — 347,887 against 352,495. If it is not worse,
adr-005's parameter-efficiency thesis is served better by it than by the head
currently written into the ADR.

**The question is narrow and it is a parameterisation question, not a
mechanism question.** Both arms compute the same score,
`cell[c] + tile[t] + rotation[c, r]`, over the same nested normaliser. They
differ only in how `rotation[c, r]` is produced.

#### The two arms

| arm | rotation rows from | rotation parameters (5×3) |
|---|---|--:|
| **L_linear** | `Linear(480, 15 × 6)` — the adopted head, EXP-012's arm B | 43,290 |
| **V_conv** | `Conv2d(32, 6, kernel_size=1)` over the pre-flatten `(32, 15)` map | 198 |

**The linear arm is not retrained.** Its twelve rows already exist — EXP-012's
`B_cell` at seeds 0–11, on this sample, this schedule and this code. Reusing them
halves the run, and the reproduction guard built for EXP-012's extension is
exactly the instrument that makes the reuse legitimate rather than assumed.

#### Why the conv form is not obviously equal, and could be better

Two forces pull in opposite directions and the entry does not pre-judge them.

**Against the conv form.** Shared weights cannot express cell-specific behaviour
that is not a function of that cell's own feature vector. If the right rotation
at A1 depends on something the tower does not put into A1's 32 channels, the
unshared form can memorise it and the shared form cannot.

**For the conv form, and this is the sharper one.** EXP-012 recorded that the
adopted head carries a **data-efficiency handicap**: the rotation row for cell `c`
receives gradient only on plies where `c` is empty, about **36.7%** of positions.
Shared weights receive gradient from **every cell on every position**. The conv
form should therefore be better exactly where EXP-012 found the signal
concentrated — the **odd layers**, where `B − A` was +8.1 against +2.8 on even
layers.

The registered prediction is that the conv form is **not worse**, and it is
plausible that it is better. The design is one-sided for that reason; see the
test.

#### The initialisation must be measured, not assumed

EXP-012's pooled control needed a `sqrt(15)` correction because `Linear`
initialises rows independently and a mean of fifteen rows starts at a quarter of
one row's scale. **Identical function class did not imply identical initial
function**, and it was the one systematic difference in that entry.

The same trap is live here and is worse, because the two arms differ in input
dimensionality: the linear form's rotation logit is a dot product over 480
features, the conv form's over **32**. Default initialisation bounds are
`1/sqrt(fan_in)` in both cases, so the two logits start at different scales by
construction.

**Registered as a step, not an assumption.** Before any arm is trained, the
standard deviation of the rotation logit at initialisation is measured for both
forms over 1,000 sampled positions, and the conv form's output is scaled by a
fixed constant chosen to match. The measured constants and the two standard
deviations go in the artefact. Scaling the output leaves the function class
untouched. An unreported mismatch here would read as "the shared form is worse"
for a reason that has nothing to do with sharing.

#### Ground truth and sample

Identical to EXP-011 and EXP-012, so the three entries are readable together, and
required identical because the linear arm's rows are reused rather than retrained.

`data/subgame-solutions/5x3-h2.json`, V5 checksum
`51192b4d403ac1cb45c22d92ce58bab215843f457f245e7aca6d18744f8a3f43`, termination
`exhausted`. Sampler seed **29**, layers 5–14, 250 WIN-for-mover positions per
layer, shuffled, split 2,000 train / 500 held out.

#### Schedule, pinned

**40 epochs, batch 64, Adam at lr 1e-3, weight decay 1e-4**, with the rotation
parameters in a `weight_decay = 0` group in **both** arms — as in EXP-012, so the
decay-to-signal ratio does not differ across parameterisations. That matters more
here than there: decay applied equally to 43,290 and to 198 parameters is not the
same intervention.

**40 epochs is now justified rather than inherited.** EXP-012's convergence leg
re-ran one seed per arm at 80 epochs: every McNemar interval contained zero,
training loss fell in all five arms, and held-out rose in none. The arms sit at
or past their generalisation optimum at 40. **No convergence re-run is registered
here** — the question was asked and answered on this pipeline, this sample and
this schedule.

#### Metrics

1. **Primary — top-1 optimality after 400 PUCT simulations**, each head supplying
   the prior, on the held-out 500, 12 seeds per arm.
2. **Secondary, and non-solver — final training loss**, per arm and seed.
3. **Reported beside both** — the random-legal-move floor, and the stratified
   read by **layer parity**, which is where the registered prediction lives.

The unit is the **position**.

#### The test, named — non-inferiority, not equivalence

Read on the paired *t* over the twelve seed means, conditional on the fixed
held-out set, with the bootstrap clustered on the 500 positions reported beside
it and **the wider of the two quoted** — EXP-012's rule, and its instrument
omitted it, so it is named here as an output the artefact must contain.

**The shape is one-sided.** The hypothesis is directional: the conv form must not
be materially *worse*. An equivalence test would spend power ruling out the
conv form being better, which is an outcome nobody needs protection from.

`V_conv − L_linear`, non-inferiority margin **δ = 1.7 points**, one-sided
α = 0.05, `t(11) = 1.796`.

#### The margin is derived, and its derivation imports an interval

EXP-012's principal threat is that its 5-point margin changed role — detection
threshold to adoption tolerance — and was carried across without being
rejustified. **This entry does not reuse it.**

adr-005 adopted a head that concedes **3.3 points** to the flat head, under a
tolerance of **5.0**. A parameterisation that gives back more than the remaining
**1.7 points** would push the shipped architecture outside the tolerance the
adoption decision was actually taken under. That is the derivation:
`δ = 5.0 − 3.3 = 1.7`.

**And the derivation is not clean, which is stated rather than hidden.** The 3.3
is a point estimate with interval [1.88, 4.75]. A reader who takes the
conservative end derives `δ = 5.0 − 4.75 = 0.25`, which is not measurable at any
affordable seed count; the optimistic end gives `δ = 3.12`. **δ = 1.7 is the
point-estimate derivation and it inherits that uncertainty.** It is registered
with the range visible so that no later write-up can present it as a clean
consequence of the adoption.

#### Feasibility, checked before the fact — the repair for EXP-012's defect

EXP-012's validity gate was **unpassable**: its δ equalled its forecast
half-width, so no point estimate could clear it. That failure mode is checked
here explicitly and the check is registered as a project-wide rule.

Measured on this exact pipeline, `sd(differences)` between arms across seeds is
1.60 (5 seeds), 1.92 (12 seeds) and 1.95. **The conservative figure 1.95 is used.**

| quantity | value |
|---|--:|
| `sd(differences)`, assumed | 1.95 |
| standard error at n = 12 | 0.563 |
| one-sided half-width, `t(11) = 1.796` | **1.011** |
| margin δ | 1.700 |
| **room the point estimate has** | **0.689** |

The test passes when the observed `V_conv − L_linear` exceeds **−0.689 points**.
That number is positive, which is the whole point: the gate is passable, and by
how much is known before the run.

> **Registered as a standing rule for this project.** No equivalence or
> non-inferiority test may be registered whose δ does not exceed its forecast
> half-width, and the *room* — δ minus that half-width — must be tabulated in the
> entry. A gate that cannot be passed is not a gate.

#### Power, at the registered margin

Approximate, treating the estimated sd as known:

| true `V_conv − L_linear` | probability the gate passes |
|---|--:|
| +1.0 (conv better) | >99% |
| 0.0 (a true tie) | **89%** |
| −0.5 | 63% |
| −1.0 | 29% |
| −1.7 (the margin itself) | 4% — α, which is 5% exactly under the *t*; the gap is the normal approximation |

At a true tie the design resolves nine times in ten, and it correctly refuses
when the conv form is a full point worse. **A true difference between −0.5 and
−1.0 will often not resolve**, and "not resolved" is then the reported outcome.

#### Decision rule

Read on the one-sided interval for `V_conv − L_linear`.

- **Lower limit above −1.7** → **adopt the convolutional form.** adr-005 is
  amended again; the rotation head becomes the 1×1 convolution. Parsimony breaks
  a tie in a decision whose stated purpose is parameter efficiency, and the
  saving is 119,952 parameters on the shipped board.
- **Lower limit at or below −1.7** → **the adopted linear form stands.** Recorded
  as a finding, not a non-result: it would mean unshared per-cell weights buy
  something the shared form cannot express, which contradicts the efficiency
  argument that motivated this entry.
- **Additionally, if the interval lies entirely above zero** → the conv form is
  not merely non-inferior but better, and see below.

**Twelve seeds, and no extension.** EXP-012 ran five and needed its one permitted
extension, at three hours, to clear by a quarter of a point — and its five-seed
`sd` understated the twelve-seed value by 20%. This design is powered at twelve
from the measured variance up front. **If it does not resolve, that is the
result**, and the incumbent stands by incumbency. Registering an extension here
would be registering optional stopping with extra steps.

#### What this entry does not re-read

**It does not re-read EXP-012's adoption.** That rule permitted one extension and
it is spent. If the conv form comes out **materially better** than the linear
form, the 3.3-point gap to the flat head was measured against a parameterisation
that is no longer the shipped one, and a **fresh adoption entry** is required —
registered separately, not read out of this one. This is written down now so that
a favourable result cannot be quietly converted into a stronger claim about the
flat-head comparison.

#### Correctness preconditions

Both must pass before the run counts as evidence.

1. **The reproduction guard runs *after* the `az/network.py` change, not before.**
   Its entire purpose here is to catch that change perturbing the incumbent arm
   whose rows are being reused. `B_cell` seed 0 is retrained and its held-out hit
   vector compared **element-wise** against EXP-012's artefact — a mean
   comparison is not evidence, since two runs can score the same on different
   positions. Any mismatch voids the reuse and the linear arm must be retrained
   in full.
2. **The conv arm's normaliser is verified against brute force.** The score is
   the same non-separable form as the adopted head, so the nested closed form
   applies unchanged — but "applies unchanged" is a claim about code that must be
   checked, on three variants and three depths, matching the existing test's
   coverage. A wrong normaliser does not raise; it optimises the wrong
   distribution and reads as a worse arm, and it would land on **V_conv
   specifically**, in the direction that keeps the incumbent.

Also asserted, as in EXP-012: stem, tower, `policy_conv` and value head are
**bit-identical across both arms at one seed**. Restructuring `policy_conv` to
expose the pre-flatten map must not shift the RNG stream. `nn.Flatten` holds no
parameters, so moving it to the call site should be inert — *should be* is why it
is asserted rather than reasoned about.

#### Threats to validity

Inherits EXP-011's and EXP-012's. Added here:

- **The 5×3 has 15 cells and the shipped board has 25.** Weight sharing gets
  *more* attractive as cells multiply — 25 unshared maps against one shared one —
  so a conv-form win here understates the 5×5 case, and a conv-form loss here
  would be the more transferable result. The asymmetry is in the direction that
  makes a negative result the more informative one, which is unusual and worth
  saying.
- **The two arms are not parameter-matched, deliberately.** Every previous entry
  in this family matched parameters to isolate a mechanism. This one is a
  parameterisation question and matching would destroy it: the 218× difference
  *is* the treatment. It follows that a conv-form win is confounded with
  regularisation-by-fewer-parameters, and the entry cannot separate "sharing is
  the right inductive bias" from "43,290 parameters was too many". **That
  separation is not attempted and no sentence may claim it.**
- **Reusing the linear arm's rows means one arm's numbers predate the other's
  code.** The guard checks reproduction on one cell of twelve. A defect that
  perturbs only seeds 3 and 7 would pass it. The guard is a strong check, not a
  proof.
- **Targets are exact optimal play; deployment trains on MCTS visit counts.** The
  rank-inversion risk EXP-012 records applies unchanged, and applies with more
  force to a regularisation-flavoured comparison: fewer parameters help more
  against noisy targets than against clean ones, so a conv-form tie here could be
  a conv-form win in deployment, unmeasured either way.

#### Anti-circularity

Under [adr-004](../docs/adr/adr-004-solver-approach.md) R1 this is the **third**
architecture decision taken against 5×3 ground truth, over an adoptable choice
set of **four** (factored, linear-conditioned, conv-conditioned, flat).

**The refinement argument does not exempt it.** One could argue this only chooses
between two implementations of a decision already taken, and therefore adds no
new family. It still makes the shipped architecture a function of solver labels
on a variant inside H3's comparison set, and R1 counts *decisions*, not families.
The count is three.

**A partial repair is registered.** Final training loss — a non-solver quantity —
is a pre-registered secondary. **If the two disagree in direction, this entry
adopts nothing** and the disagreement is the finding. That uses the non-solver
signal as a check on the solver-selected decision rather than as a second
selector, which is the only use of it that does not simply move the leak.

#### Amendment (2026-09-03, before the run) — the secondary was not a secondary

Found while building the instrument, with no data in existence. Registered here
rather than fixed silently, because the defect is in the anti-circularity repair
and that is the part of the entry most worth being able to trust.

**Defect 1 — final training loss is not a non-solver quantity.** The training
targets are optimal moves read from the exact solver. A loss computed against
solver labels cannot check a solver-selected decision; it is the same evidence in
a different unit. The section above called it "a non-solver quantity" and it is
not one.

**Defect 2 — the direction rule contradicted this entry's own prediction.** The
repair said the entry adopts nothing if the primary and the secondary "disagree
in direction". Expected result 4 predicts the conv arm fits training **worse**
(198 parameters against 43,290) while generalising **no worse** — the textbook
outcome for a smaller model, and the cleanest possible statement of the entry.
The rule as written would have scored exactly that as a disagreement and refused
to adopt. **The registered rule and the registered prediction could not both be
satisfied.**

**The replacement — head-to-head play.** The two arms at seed 0 play a match of
**200 games**, seats alternating, 400 simulations, temperature for the first four
plies so the games are not replays of one another. The winner is decided by the
game, not by agreement with the solver, which puts it genuinely outside Axis 1.

- **It costs no extra training.** The reproduction guard already trains the
  incumbent at seed 0; its net is kept and played. Only match time is added,
  about 30 minutes.
- **It is one seed pair and therefore weak**, so it is used only as a veto and
  only when decisive: the check fires when the conv arm's Wilson interval lies
  **entirely below 50%**. At 200 games that is roughly a win rate under 43%. A
  single seed pair cannot overturn a twelve-seed primary on noise.

**Training loss stays, as a reported diagnostic and never as a gate.**
Prediction 4 is read against it.

#### A defect in the shipped pipeline, found by building this entry

Not a result of EXP-013 and recorded because it was found here.

`az/network.py::NetworkEvaluator` computes priors through the **factored**
`masked_log_policy`, which expects a 6-wide rotation vector. Handed the
conditioned head adr-005 adopted on 2026-09-03, it raises. Both `az/player.py`
and `az/selfplay.py` constructed it by name, so **self-play, the evaluator gate
and the agents were all still factored-only after the architecture record had
moved.** The adoption changed the ADR and the training path and left the play
path behind.

It fails loudly rather than quietly, which is the only good thing about it. The
repair is a `ConditionedNetworkEvaluator` and an `evaluator_for(net, board)`
factory that both call sites now use, pinned by two tests — one that every head
type gets the right evaluator and produces a normalised prior over legal moves,
and one that the evaluator's distribution matches the one
`conditioned_policy_loss` optimises. Without the second, a network could be
trained on one distribution and played on another with nothing raising.

**This does not perturb the reused rows.** EXP-012's instrument scored arms
through its own `_ArmEvaluator`, never through `NetworkEvaluator`, so the repair
cannot touch the incumbent's twelve rows — and the reproduction guard is what
checks that claim rather than asserting it.

#### One registered precondition turned out to be unnecessary

The correctness preconditions above anticipate restructuring `policy_conv` to
expose its pre-flatten map, and require asserting that the restructuring does not
shift the RNG stream. **No restructuring was needed:** `policy_conv` is a
`Sequential` and the map is available as `policy_conv[:3](features)`, with the
flatten applied as `policy_conv[3]`. `FlipHexNet` is untouched.

That strictly strengthens the reuse argument — the incumbent's class did not
change at all — and the bit-identity assertion is kept anyway, as a test, because
"untouched" is a claim about code.

#### Expected result

1. **The gate passes**: `V_conv − L_linear` lands above −0.689 and the
   convolutional form is adopted.
2. **The point estimate is non-negative**, on the data-efficiency argument: the
   shared weights train on every cell of every position against the unshared
   form's 36.7%.
3. **Any advantage concentrates on the odd layers**, where EXP-012 measured the
   head effect at +8.1 against +2.8.
4. **Training loss is higher for the conv form** — 198 parameters fit the training
   set less well than 43,290 — **while held-out is not worse.** If that pair
   holds, it is the clean statement of the entry: the unshared parameters were
   fitting the training set and not the game.

Prediction 4 is the one that can most cleanly be wrong, and it is the one worth
watching: if the conv form fits training *better*, the data-efficiency story is
doing more work than the capacity story and the entry should say so.

#### Artefact

`results/exp013-conv-rotation-5x3-h2.json`, written by
`scripts/exp013_conv_rotation.py`, with the verdict applied by
`scripts/exp013_analysis.py` from the artefact rather than by the run. The
network class is `az/network.py::ConvRotationNet`. All four named before the
instrument exists.

**Estimated cost.** Twelve training runs plus evaluation at ~920 s each, plus the
reproduction guard at ~770 s: **≈ 3.4 h**. The linear arm's twelve rows are
reused, which is the half that is not paid.

#### Result (2026-09-04) — the rule fires: adopt the convolutional form

Run `scripts/exp013_conv_rotation.py`, 4h20 (15,596 s), artefact
[`exp013-conv-rotation-5x3-h2.json`](../results/exp013-conv-rotation-5x3-h2.json),
log [`exp013-run.log`](../results/exp013-run.log). Verdict applied by
`scripts/exp013_analysis.py`, which recomputes every quantity from `results` and
refuses to print if it disagrees with what the run stored. It agreed.

| arm | rotation params (5×3) | top-1 after 400 sims | sd | supervised | final train loss |
|---|--:|--:|--:|--:|--:|
| L_linear (adopted 2026-09-03) | 43,290 | 73.2% | 1.4 | 66.0% | 2.4967 |
| **V_conv** | **198** | **74.2%** | 1.2 | 67.8% | 2.5068 |
| random legal | — | 39.4% | — | — | — |

**`V_conv − L_linear = +0.95 pts`, lower limit −0.06%** against a margin of
−1.70%, at `t(11) = 1.796`. The clustered bootstrap on the 500 held-out positions
gives −0.05%; the seed-mean interval is the wider and is quoted, and the two
agree on the branch.

> **The rule fires: adopt the convolutional form.** adr-005's rotation head
> becomes a 1×1 convolution. On the shipped 5×5 that is **347,887** parameters
> against the linear-conditioned head's 467,839 and the factored head's 352,495 —
> **full cell conditioning for less than not conditioning**, and 119,952
> parameters saved against the form the ADR carried for one day.

#### The feasibility repair worked on its first use

This is the part worth keeping.

| | forecast | observed |
|---|--:|--:|
| `sd(differences)` | 1.95 | **1.94** |
| one-sided half-width | 1.011 | **1.011** |
| δ | 1.700 | 1.700 |
| **room** | **+0.689** | **+0.689** |

EXP-012's validity gate was **unpassable** — its δ equalled its forecast
half-width, so no point estimate whatsoever could have cleared it, and every
mechanism contrast in that entry is void as a result. The standing rule this
entry introduced — *no equivalence or non-inferiority test may be registered
whose δ does not exceed its forecast half-width, with the room tabulated* — was
applied here for the first time, and the forecast landed to the second decimal.

The analysis script recomputes the room from the **observed** spread and refuses
to print an adoption if it is not positive, so a run that turned out noisier than
forecast could not have produced a verdict at all.

#### What the adoption does not establish

**The convolutional form is not better. It is not worse.** The registered test is
one-sided and it passed; the two-sided read is `+0.95 [−0.29, +2.19]` and
**contains zero**. Seven of twelve seeds favour the conv form, five the linear
one. No sentence in any artefact may say the convolution won.

**The pairing bought nothing here.** Implied between-arm correlation **−0.108**,
against the **+0.554** EXP-012 measured on `D − B`. Constructing the value head
before the policy heads was that entry's registered repair and it is now clear
that it fixed *that pair of arms*, not pairing in general. The forecast `sd` was
taken conservatively and happened to be right anyway; a future entry must not
assume the pairing is worth variance reduction.

**The arms are not parameter-matched, deliberately, so the win is confounded.**
The 218× difference *is* the treatment. This entry cannot separate "sharing is
the right inductive bias" from "43,290 parameters was too many", and it was
registered as unable to.

**It does not re-read EXP-012's adoption.** Descriptively the gap to the flat
head narrows from **+3.32** to **+2.37** points. That number is recorded and
**not acted on**: EXP-012's rule permitted one extension and it is spent, and
this entry registered in advance that a materially better conv form requires a
fresh adoption entry rather than a re-read. The narrowing is a reason to consider
registering one, not a result about it.

#### Every registered prediction, scored — three of four

| # | prediction | outcome |
|---|---|---|
| 1 | the gate passes, above −0.689 | **holds** — +0.95 |
| 2 | the point estimate is non-negative | **holds** — +0.95 |
| 3 | any advantage concentrates on the **odd** layers | **fails** — +0.8 odd against **+1.1 even** |
| 4 | conv fits training worse while generalising no worse | **holds** — 2.5068 vs 2.4967, and +0.95 held-out |

**Prediction 3 is the informative failure.** It was derived from the
data-efficiency argument: shared weights receive gradient from every cell on
every position against the unshared form's 36.7%, so the gain should appear where
the head effect is largest — the odd layers, where EXP-012 measured `B − A` at
+8.1 against +2.8. The advantage came out **flat across parity, marginally
larger on the even layers**.

That weakens data efficiency as the mechanism and **replaces it with nothing.**
The design cannot arbitrate, having been registered as unable to separate sharing
from size. What can be said is that the *reason* given for expecting the
convolution to win is not visible in the place it should have been most visible.

**Prediction 4 holding is the clean statement of the entry:** 198 parameters fit
the training set worse than 43,290 and generalise better. The unshared parameters
were fitting the training set and not the game.

#### The initialisation match was not cosmetic

Measured over 500 held-out positions and three seeds before any training:

```
incumbent rotation-logit sd 0.04354, conv 0.09021 -> scale 0.4826
```

**The conv arm's rotation logits start at 2.07× the incumbent's.** The two heads
differ in input dimensionality — 480 features against 32 — and default
initialisation bounds go as `1/sqrt(fan_in)`, so equal weight scales give unequal
logit scales. Without the constant, the comparison would have measured an
initialisation difference and attributed it to weight sharing. This is the same
trap EXP-012's pooled control hit with its `sqrt(15)`, and larger.

#### The head-to-head did not veto

`conv 106/200 = 53.0% [46.1%, 59.8%]`, seats alternating. The interval crosses
50%, so the veto — registered as firing only when the interval lies **entirely**
below 50% — does not fire. It agrees in direction with the primary without adding
strong evidence, which is what one seed pair is worth.

Recorded plainly: this is the **only** non-solver evidence in the entry, it is
weak, and the amendment that introduced it exists because the originally
registered secondary was neither non-solver nor coherent.

#### The reproduction guard, and what it licensed

```
guard passed in 694s: 500/500 positions identical, digest aa8690a5eee5
```

Run **after** the change to `az/network.py`, retraining EXP-012's `B_cell` at
seed 0 and comparing hit vectors element-wise. All 500 positions identical and
the training loss matching to 1e-9, which is what makes reusing that arm's twelve
rows legitimate rather than assumed — and what halved the run.

The analysis script independently recomputes the digest from the incumbent rows
**as stored in this artefact** and refuses to proceed if it differs from the one
the guard reported. Without that, the guard could have compared against one thing
while something else was written down, and the reuse argument would cover nothing.

#### Threats to validity, added by the result

The entry's own threats stand. These are added by what happened.

- **The mechanism is now doubly unexplained.** EXP-012 could not read why
  conditioning helps; this entry predicted *where* the efficient form's advantage
  should appear and was wrong. Two entries have adopted architecture changes that
  work for reasons neither could establish.
- **The margin is derived from a point estimate that carries an interval.**
  δ = 1.7 comes from 5.0 − 3.3, and the 3.3 carries [1.88, 4.75]. The
  conservative derivation is δ = 0.25, at which the observed lower limit of
  −0.06% would **still** pass — which is worth stating, because it is the one
  place in this family of entries where the conservative reading does not change
  the verdict.
- **Nothing is measured on the 5×5**, where weight sharing should be *more*
  attractive: 25 unshared maps against one shared one. A conv win here understates
  the shipped case, which is the favourable direction, but it remains an argument.
- **The adopted head has never played a full self-play loop.** Building this
  entry exposed that `NetworkEvaluator` could not drive the conditioned head at
  all; the repair is tested but the architecture's first real training run is
  still ahead of it.

#### Artefacts

| file | produced by |
|---|---|
| [`exp013-conv-rotation-5x3-h2.json`](../results/exp013-conv-rotation-5x3-h2.json) | `scripts/exp013_conv_rotation.py` |
| [`exp013-run.log`](../results/exp013-run.log) | the same run |

Verdict applied from the artefact by `scripts/exp013_analysis.py`, which was
smoked on nine synthetic artefacts — the four verdict branches and five guards,
each on an input built to trip it.

#### Follow-ups this entry creates

1. **adr-005 amendment** — the rotation head becomes the 1×1 convolution.
   Required by the decision rule; the Axis 2 architecture may only change by ADR.
2. **A fresh adoption entry against the flat head**, if wanted. The gap narrowed
   to +2.37 and EXP-012's extension is spent, so the question can only be reopened
   by registering it anew.
3. **The first self-play run on the adopted architecture.** Everything measured
   in EXP-011, EXP-012 and EXP-013 trains on exact solver labels; the pipeline the
   architecture was chosen for has never trained on its own visit counts with this
   head.


### EXP-014 — pipeline shakedown: does the loop close on the adopted architecture?

**Registered 2026-09-04, before the run.**

#### What this is, and what it is not

**It is a pre-flight check on the instrument, not evidence about the game.** No
number produced here may be quoted about H1, H2 or H3, and no architecture or
hyperparameter decision may be taken from it. It exists because the training loop
`az/loop.py` was written today, the head it will run was adopted yesterday, and
the two have never met at full scale.

The alternative to running it is committing **≈ 60 hours** to a pipeline whose
first end-to-end execution would be that run.

#### Why it exists — three things are unexercised

1. **The loop has never run at deployment scale.** Its tests use a 3×3 board,
   four games, four simulations and an in-process worker. The real run is a 5×5
   board, 200 games, 400 simulations and eight spawned processes.
2. **`workers > 1` was broken until today.** `_init_worker` rebuilt every network
   as a factored head, which is correct only while the factored head is the only
   head. The repair is tested at two workers on a 3×3; it has not been run at
   eight workers on the shipped board.
3. **R8 carries one figure that was never measured.** Its own text says the
   4.31× parallel speedup and the ~705 games/hour that follow from it were
   measured **engine-only, with torch not yet competing for those cores**. The
   59.6-hour budget for H3's five seeds rests on that figure. This entry closes
   it.

#### Configuration

The **shipped 5×5**, because a shakedown on a smaller board would validate
neither the throughput figure nor the memory profile of the run it is clearing.

| | |
|---|---|
| variant | 5×5, `h1` |
| architecture | `ConvRotationNet`, adr-005 as amended 2026-09-04 |
| generations | 3 |
| games per generation | 20 |
| simulations | **400** — deployment's value, since the point is the real cost |
| gate | every 2 generations, 20 games, threshold 0.55 |
| steps / batch | 400 / 64 |
| buffer capacity | 20,000, crossing generations |
| workers | 8, spawn |
| seed | 1 |

Small in generations and games, **identical in shape** to the registered run.

#### Four checks, each with its pass criterion

| # | check | passes when |
|---|---|---|
| C1 | the loop closes | 3 generations complete; a checkpoint and 3 history rows exist |
| C2 | parallel self-play runs the adopted head | 8 workers produce a full generation with no worker error |
| C3 | the gate decides | both gates return a result with a Wilson interval and a seat split |
| C4 | **a real kill resumes indistinguishably** | see below |

**Any check failing stops the 60-hour run.** That is the entry's only decision
rule and it is one-directional: passing does not license anything, it removes an
objection.

#### C4 — the kill is real, and that is the point

`tests/test_az_loop.py` simulates interruption by calling `run` twice. That
cannot catch a **torn write**: a process killed between writing the payload and
writing the manifest, or halfway through either. `atomic_write` and "manifest
last" exist for exactly that, and **neither has ever been exercised by an actual
kill**.

Procedure:

1. Run the shakedown straight through. Record the SHA-256 of the final
   challenger and champion `state_dict`s.
2. Delete the run directory. Run it again, and `kill -9` the process **during the
   first gate** — the longest uninterruptible unit, and the only place the
   mid-match checkpoint path is reachable.
3. Resume. Let it finish.
4. **The two digests must be equal.**

Not "the losses look similar" and not "it continued without crashing". Equal.

A caveat registered in advance so it is not discovered as a surprise: this
compares two runs of the same code, so a defect present in both cancels out. The
loop's unit tests already have that weakness and it was measured — removing
`restore_rng` leaves them green. **C4 tests durability under a real kill, which
those tests cannot reach; it does not re-test determinism, which they can.**

#### The one measurement: throughput, and what may be done with it

Reported: games/hour composed (self-play with the network in the loop, at eight
workers), seconds per generation, and peak resident memory.

This is a **cost** measurement, not a strength one, so acting on it is not
circular. What it may change and what it may not:

- **May change:** `workers`, and the games-per-generation or generation count of
  the registered run, by dated amendment.
- **May not change:** the **five seeds**. If the composed rate makes the schedule
  unaffordable, the seed count is the *last* thing cut and only in an amendment
  that states the power consequence explicitly. Cutting seeds is the cheapest way
  to make a budget work and the fastest way to make a comparison meaningless.

If the composed rate is materially below the engine-only 705 games/hour — and it
will be, since the network is now in the loop — **R8's residual is closed with
the real number** rather than left as a known-optimistic estimate.

#### What may and may not be decided from this

- **May not:** anything about the architecture, the head, the schedule's
  statistical parameters, or the game.
- **May:** whether the 60-hour run starts, and the compute parameters above.

Nothing here is measured against solver ground truth, so **the anti-circularity
count is unchanged at three** (EXP-011, EXP-012, EXP-013). That is deliberate:
the shakedown is the one Phase 4 entry that touches the pipeline without touching
the leak, and keeping it that way is worth more than any sanity check against
known values would have been.

#### Expected result

All four checks pass, and the composed throughput comes in **below** 705
games/hour — the engine-only figure has no network in it. A composed rate near
the engine-only one would be the surprising outcome and would mean the network's
cost is being hidden somewhere.

The registered run's cost is then recomputed from the measured rate, before it
starts rather than after.

#### Artefact

`results/exp014-shakedown-5x5.json`, written by `scripts/exp014_shakedown.py`,
with the run's own per-generation history at `data/az-runs/shakedown/history.jsonl`.
Named before the instrument exists.

#### Result (2026-09-04) — all four checks pass, and the measurement is the finding

Run `scripts/exp014_shakedown.py`, 48 min (2,861 s), artefact
[`exp014-shakedown-5x5.json`](../results/exp014-shakedown-5x5.json), log
[`exp014-run.log`](../results/exp014-run.log). Registered scale, confirmed by the
artefact's own `is_registered_scale` flag.

| check | result |
|---|---|
| C1 the loop closes | **PASS** — 3 generations, 3 history rows, checkpoint at generation 3 |
| C2 eight workers run the adopted head | **PASS** — 500 samples per generation, no worker error |
| C3 the gate decides | **PASS** — interval and seat split present |
| C4 `SIGKILL` mid-gate resumes byte-equal | **PASS** — `1929309feee0` both times |

> **The objection to starting the registered run is removed.** The rule is
> one-directional: this licenses nothing else, and in particular the run it
> clears is **not the run that was budgeted** — see below.

#### C4 failed first, and the defect was real

Recorded because it is the entry's whole justification.

On the first execution, at toy scale, **C4 failed**: `1331009c1664` against
`325477f94bde`. A checkpoint written *inside* a gate carries a generation whose
self-play and training have already happened — they are baked into the buffer and
the challenger it stores. The loop re-entered the generation body on resume and
replayed both, extending the buffer with the same games twice and taking another
400 gradient steps. **Nothing raises.** The weights simply diverge, which is
invisible without a byte comparison against an uninterrupted run.

`tests/test_az_loop.py` could not have caught it: it simulates interruption by
calling `run` twice, and two probes had already shown that comparison passes on
broken code. The defect needed a real kill at a real checkpoint boundary.

Two smaller defects surfaced the same way. The mid-gate checkpoint cadence was a
module constant, so a 20-game gate against the loop's default of 25 would have
written no mid-gate checkpoint at all and the kill would have landed where the
path had never run — C4 would have tested nothing. And the shakedown's scale
lived in module constants while its child is a fresh interpreter, so a smaller
debugging run would silently have been the full one.

All three are fixed and pinned, the mid-gate one by a test probed against the old
behaviour.

#### Throughput: the registered run is not the run that was budgeted

**145 games/hour composed, 0.21× the engine-only 705.** Peak child RSS 385 MB.

The registered prediction was that the composed rate would come in *below* 705,
since that figure has no network in it. It came in at a fifth. R8's likelihood
was dropped to 1 on 2026-08-31 on the grounds that "the binding numbers are now
measured rather than estimated" — **the binding number was wrong by 4.9×**,
because it was measured engine-only with torch not competing for the cores, which
R8's own text says.

**A defect in this entry's metric, stated before its numbers are used.**
`composed_games_per_hour` divides *self-play* games by *total* elapsed, which
includes the gate and training — three activities whose per-game costs differ by
a factor of four. The 145 is not a rate of anything in particular. The
decomposition below is the usable reading.

#### Where the time goes, decomposed from the run's own generations

Generations 0 and 2 are ungated, generation 1 is gated, and training was timed
separately on the run's final state. So the split is arithmetic on measurements,
not an allocation:

| component | cost | per game | rate |
|---|--:|--:|--:|
| ungated generation | 224.5 s | — | — |
| training, 400 steps | 19.7 s | — | 49.3 ms/step |
| self-play, 20 games at 8 workers | 204.8 s | 10.24 s | 352 games/h |
| **gate, 20 games serial** | **808.5 s** | **40.42 s** | **89 games/h** |

**Confirmed by a second route**: a direct serial gate on the 5×5 measured
**39.81 s/game**, against the 40.42 obtained by subtracting the ungated
generations. The decomposition holds.

Projecting the registered run — 5 seeds × 30 generations × 200 games, gate every
5, so 6 gates of 400:

| | h/seed | h total | share |
|---|--:|--:|--:|
| self-play | 17.1 | 85.3 | 39% |
| **gate** | **26.9** | **134.8** | **61%** |
| training | 0.2 | 0.8 | 0% |
| **total** | **44.2** | **220.9** | — |

Budgeted: 59.6 h. **3.7× over**, and **61% of it in the only part that was not
parallelised.**

#### What was done about it, and why that is inside the boundary

The gate now plays in a spawned pool. This is an **engineering** change, not a
schedule one: the entry permits changing `workers` by amendment and forbids
touching the five seeds, and parallelising a sequential loop touches neither.
Cutting scope while 61% of the cost sat in an unnecessary queue would have been
the wrong order — and it is the kind of cut that later reads as "we had to reduce
the experiment" with nobody remembering why.

It is safe because every game's two seeds are already functions of the match seed
and the game index alone, so games are independent and order-free. Verified
identical to the serial path at two, three and four workers, on a chunk that does
not divide the match length, and for a parallel match resumed serially.

**Measuring the speedup found something the engine-only figures had hidden:**

| workers | gate, games/h | self-play, games/h |
|--:|--:|--:|
| 1 | 90 | 88 |
| **4** | **260** (2.87×) | 271 (3.08×) |
| **6** | not measured | **331** (3.76×) |
| 8 | 173 (1.91×) | 327 (3.71×) |

**The gate peaks at four workers and loses 33% at eight, while self-play
saturates at six with eight within 1%.** Six physical cores — and a gate worker
holds *two* networks, challenger and champion, against self-play's one, so twice
the resident model memory and BLAS working set per worker. That mechanism is an
explanation from structure and was **not measured**; the worker counts were.

`LoopConfig` gains `gate_workers` accordingly, because one shared setting would
have to pick a loser.

Revised projection, at the measured optima:

| | h/seed | h total |
|---|--:|--:|
| self-play (6 workers) | 18.1 | 90.6 |
| gate (4 workers) | 9.2 | 46.2 |
| training | 0.2 | 0.8 |
| **total** | **27.5** | **137.6** |

**220.9 h → 137.6 h**, 83 hours recovered without touching scope. Still **2.3×**
the 59.6 h budgeted.

#### The configuration this measured was not the best one, and that is the entry's own doing

Stated plainly rather than smoothed over.

This entry registered `workers: 8`, and the follow-up measurements show 8 is 33%
off the gate's optimum. **The shakedown measured throughput in a configuration it
had itself fixed suboptimally**, so its headline number describes that
configuration and not the machine's capability.

Further, the three scaling measurements above were made **after the run and
outside it**, and were not registered. They are cost measurements, which this
entry permits acting on, and they are reported here rather than folded into the
artefact — the artefact records what the registered run measured, and rewriting
it to describe measurements it did not make would be worse than the asymmetry.

#### One instrument observation that must not be read as a result

Generation 1's gate returned **70.0% [48.1%, 85.5%], promoted**. The interval
spans the 0.55 threshold, so at 20 games this promotion is noise: `run_gate`
promotes on the point estimate, which is the registered design and is calibrated
for **400** games, where this entry's own false-promotion table applies. At 20 it
is not.

Nothing follows from it. It is recorded because a reader scanning the log will
see "promoted=True" and should know it means the plumbing works, not that a
network improved.

#### What this entry decided, and what it did not

- **Decided:** the registered run may start; `gate_workers = 4` and
  `workers = 6`; the gate is parallelised.
- **Not decided, and requiring an amendment:** the schedule. At 137.6 h against
  59.6 h budgeted, generations or games per generation must fall, or the budget
  must rise. **The five seeds are not the lever**, and may only move in an
  amendment that states the power consequence.
- **Not touched:** the architecture, the statistical parameters, anything about
  the game. The anti-circularity count stays at **three**.

#### R8 needs revisiting

Its residual is closed and the answer is bad. R8 dropped to likelihood 1 on the
strength of engine-only numbers that were off by 4.9× on throughput and, it now
turns out, wrong about the worker count too. **The correction is to the row's
reasoning, not only to its numbers**: "measured rather than estimated" is not a
reason to lower a likelihood when the measurement omits the dominant cost.

#### Follow-ups this entry creates

1. **A schedule amendment**, computed from 137.6 h.
2. **R8 revised**, with the composed figure and the reasoning correction.
3. **The gate's saturation mechanism is unmeasured.** Two networks per worker is
   a plausible explanation and nothing here tests it; a worker holding one
   network and swapping weights would distinguish them.


### EXP-015 — the H3 training run: five seeds against the prior-free floor

**Registered 2026-09-04, before the run.** This is Axis 2's evidence for H3 and
the largest single piece of compute in the project.

#### Why this entry exists at all

**The run had no registered entry.** It appeared only in the `## Planned` table,
as *"AZ training run, seed 1, to 1M self-play positions"* — and the plan had
drifted: what R8 has been budgeting is **5 seeds × 30 generations × 200 games**,
which is ~150k positions per seed and 750k in total, at a seed count the sketch
did not mention. The largest thing in the project was the only thing without a
registration, and the sketch and the budget were not the same experiment.

Registering it now also disposes of the 59.6-hour figure cleanly: that was never
a commitment, it was an estimate inside R8, and R8 records its correction. This
entry carries the **measured** cost instead.

#### What H3 asks, and which half this entry answers

H3 has two clauses:

1. *"The learned policy converges to a **stable win-rate across independent
   seeds**"* — measured as *"per-seed win rate with Wilson 95% CI and variance
   reported across seeds"*.
2. *"…and **agrees with the solver's exact verdict** on every member of the
   pre-declared comparison set"* — 3×3, 5×3, and EXP-006's shipped-5×5 endgame
   sample at `k ≤ 8`.

**This entry answers clause 1 and produces the artefacts clause 2 will read.**
The separation is not stylistic; see anti-circularity.

#### The success criterion: the prior-free UCT floor

The reference opponent is **plain UCT with random playouts and no network** —
`agents/az_agent.py::UCTAgent`, whose docstring already states the rule this
entry formalises: *"The learned agent must beat this before any result about it
is reported."* It depends on no training, so a bad run cannot flatter it, and its
playouts terminate and always yield a decided winner because draws are
impossible on an odd cell count.

**Primary — equal simulations.** Both agents at **400 simulations per move**,
**200 games**, seats alternating, per seed. This measures what the *prior* is
worth, which is what EXP-011, EXP-012 and EXP-013 were all about.

**Criterion: every seed's Wilson 95% interval must lie entirely above 50%.**
Not a margin — a margin would turn a floor into a strength claim. But "above
50%" is easier to say than to clear: at 200 games a true **55% gives
[48.1%, 61.7%] and fails**, while 60% gives [53.1%, 66.5%] and passes. The
effective bar is therefore around **58%**, which is low without being trivial.
Recorded because the criterion's wording understates it.

**Stability, made falsifiable.** H3 says "stable across seeds" and its measurement
column says "variance reported". Reported alone is unfalsifiable, so: **if any of
the five seeds fails the floor, that is recorded as instability and is not
averaged away.** The five per-seed rates and their spread go in the artefact
whatever happens.

**Secondary — equal time.** The same 200 games, with UCT given the simulation
count it can complete in the network agent's measured per-move wall clock. The
ratio is measured **before** the match and recorded.

This is the harder bar and it is registered as secondary deliberately, with the
reason in the open: at 400 simulations the network agent costs ~10.9 s/game while
prior-free UCT does no forward passes at all, so equal-simulations flatters the
network by roughly the ratio of those costs. Equal-simulations is the standard
comparison and answers "is the prior worth anything"; equal-time answers "is the
network worth what it costs". **Both go in the artefact and the write-up quotes
both.** Registering only the flattering one is how a floor becomes decoration.

**A reference point, not a criterion.** The generation-0 champion — the
randomly initialised network, before any training — plays the same
equal-simulations floor match. It says where the run started. Nothing branches
on it.

#### What the floor does **not** establish

In the entry rather than in a footnote, because it is the most likely thing to be
overstated later.

**Beating prior-free UCT is a low bar.** It licenses "the learner learned
something". It does not license "the learner is good", and no sentence in any
artefact, note or write-up may convert one into the other. What says how good is
clause 2's agreement rate against the solver, and that is a **measurement, not a
gate** — see below.

#### The schedule, and the cost as measured

| | |
|---|---|
| variant | shipped **5×5**, `h1` |
| architecture | `ConvRotationNet`, adr-005 as amended 2026-09-04 |
| seeds | **5**, run sequentially, one checkpoint root each |
| generations | 30 |
| games per generation | 200 |
| simulations | 400 |
| gradient steps / batch | 400 / 64 |
| replay buffer | 20,000, **crossing generations** |
| gate | every 5 generations, 400 games, threshold 0.55 |
| workers | self-play **6**, gate **4** |

The worker counts are EXP-014's measured optima and differ by activity: self-play
saturates at six with eight within 1%, while the gate peaks at four and loses 33%
at eight.

**Cost, from EXP-014's measurements, not from an estimate:**

| | h/seed | h total |
|---|--:|--:|
| self-play | 18.1 | 90.6 |
| gate | 9.2 | 46.2 |
| training | 0.2 | 0.8 |
| floor matches | ~1.6 | ~8 |
| **total** | **~29** | **≈ 146** |

Machine time, not calendar time. The author's constraint is that the machine runs
during the day and hibernates at night, which is compatible: EXP-014 verified
that a **whole suspended process tree — parent, spawned workers and resource
tracker — resumes to byte-identical weights**, and the loop times with a
monotonic clock, which pauses with the machine.

A hard stop (a reboot, `wsl --shutdown`, power loss) costs at most one unwritten
checkpoint: **≈37 minutes** if it lands in a generation's self-play or training,
**≈5 minutes** inside a gate. About 2% of a seed.

#### Seeds run sequentially, and the first one is a decision point

They are independent, and the machine already saturates at six workers, so two at
once would only halve each. Sequential also means **the first seed is a
go/no-go for the remaining 110 hours** rather than a fifth of a result.

**Registered so it is not optional stopping.** After seed 1 completes, its floor
match is read. If it **fails the floor**, the run stops and this entry reports a
failure. The check is on the floor alone — a pipeline that does not beat
prior-free UCT has not learned, and spending 110 more hours to confirm that five
times is not rigour.

What this explicitly does **not** license: stopping because the result is
unfavourable in any other respect, looking at clause 2's agreement rate before
all five seeds are done, or restarting with different hyperparameters. **A
restart after a floor failure requires a new registered entry**, because
"retrain until it works" selects on the outcome.

#### Anti-circularity — this is the entry where the leak is closed

Three architecture decisions have been taken against 5×3 solver ground truth
(EXP-011, EXP-012, EXP-013), over an adoptable choice set of four. That count
measures how much of Axis 2's *design* is a function of Axis 1's answers.

**This entry adds nothing to it, and the choice of success criterion is why.**
Under [adr-004](../docs/adr/adr-004-solver-approach.md) R1, neither axis may
select or terminate the other along the dimension on which they are later
compared — and H3 *is* the comparison between the solver and the learner on
solver agreement. So:

- **The run's success criterion is the UCT floor**, which contains no solver
  information whatsoever.
- **Solver agreement is H3's measurement**, computed after the run, gating
  nothing. Neither the stopping rule, the gate, nor the floor consults it.

Two alternatives were considered and are recorded as **disqualified**, not merely
weaker:

- **Solver agreement as the success criterion** is the exact circularity R1
  forbids: it would terminate Axis 2 on the dimension of the comparison, and
  would make the whole run — not one more architecture decision — a function of
  Axis 1.
- **Generation-over-generation strength** is a derivative, not a floor: a run
  improving from terrible to slightly less terrible passes it. It is also what
  the gate already measures internally, so it is the training signal read back
  rather than independent evidence.

#### Dependencies and what this cannot close

**H3 cannot close on this entry alone.** Its comparison set includes EXP-006's
shipped-5×5 endgame sample at `k ≤ 8`, which has not been run. This entry
produces the trained agents; the agreement rates are a separate read against
Axis 1 artefacts satisfying R1 (`termination: exhausted`).

#### Threats to validity

- **The architecture has never trained on its own visit counts.** EXP-011,
  EXP-012 and EXP-013 all trained on exact solver labels. The head was chosen
  against clean near-deterministic targets and will now meet noisy
  non-stationary ones, and EXP-012 registered the risk that the ordering between
  head architectures can **invert** under that change. If it does, the shipped
  architecture is wrong in the deployed condition while every measurement behind
  it reads clean.
- **The buffer crossing generations is an off-policy assumption**, deliberate and
  registered: most of what a challenger trains on came from older champions.
  `refresh_fraction` is reported every generation so it stays legible.
- **The gate promotes on the point estimate**, which is calibrated for 400 games;
  EXP-014's 20-game gate promoting at 70% [48.1%, 85.5%] is what that rule looks
  like when the sample is too small, and is recorded there as not a result.
- **Five seeds is the registered count and it is not large.** EXP-013 measured
  the between-arm correlation on this pipeline at −0.108, so pairing buys
  nothing, and EXP-012 found a five-seed `sd` understating the twelve-seed value
  by 20%. Any variance claim from five seeds should be read with that in mind.
- **One machine, one run.** Nothing here separates a property of the learner from
  a property of this laptop's numerics.

#### Expected result

1. **All five seeds clear the equal-simulations floor.** If the prior is worth
   nothing after 30 generations, something upstream is wrong, and the first-seed
   check is there to find it in 29 hours rather than 146.
2. **The equal-time floor is closer, and may not clear.** UCT gets several times
   the simulations there, and this design has never measured what that is worth.
   A failure on the secondary while the primary passes is a legitimate and
   interesting outcome — it would say the network's advantage does not survive
   being charged for.
3. **Between-seed spread is the number to watch**, not the mean. H3's clause 1 is
   about stability, and the mean of five unstable seeds satisfies nothing.

#### Artefact

`results/exp015-h3-training-5x5.json`, written by `scripts/exp015_h3_run.py`,
with each seed's own per-generation history at
`data/az-runs/h3-seed<N>/history.jsonl` and its checkpoint alongside. The floor
matches are written by the same script. Verdict applied from the artefact by
`scripts/exp015_analysis.py`. All named before the instrument exists.

#### Amendment (2026-09-10) — a third artefact, and two corrections to this entry's own text

Written while seed 3 is running, with seeds 1 and 2 complete. **Nothing below
reads a floor result across seeds** — that is refused until all five exist. What
follows concerns where the run's records live and two statements this entry makes
about its own instrument.

**1. The per-generation record was not in the repository.**

The Artefact section above names the per-seed history at
`data/az-runs/h3-seed<N>/history.jsonl`, and `.gitignore:32` ignores
`data/az-runs/`. So everything this entry promises to report *per generation*
lived only in untracked scratch: the training curve, the six gate outcomes per
seed, and `refresh_fraction` — which the threats section commits to reporting
"every generation so it stays legible", a commitment that cannot be met by a file
no reader of the repository can open.

The console logs do not cover the gap. Both were reopened with `>` rather than
`>>` on a resume, so `results/exp015-seed1.log` holds **10** of its 30 generation
lines and `results/exp015-seed2.log` holds **13**.

**What this does not claim.** No measurement is affected and nothing was lost:
every floor match is in the JSON artefact, the weights are in the checkpoints,
and the histories are intact on disk. What was missing is that the repository
could not show them — which for a portfolio-grade public repo is the whole point
of writing them down.

**The addition: `results/exp015-histories.json`**, consolidated from the per-seed
JSONL by `scripts/exp015_analysis.py`. Three properties, because a copy that
behaves carelessly is worse than no copy:

- **A completed seed's rows are immutable.** If the snapshot and a live file with
  all 30 generations disagree, the script stops rather than re-syncing. A record
  that silently adopts whatever is on disk records nothing.
- **The scan is wider than the artefact.** A seed's artefact entry is written only
  once its 30 generations finish, so a seed that is running — or one killed
  halfway — has a history and no entry. Those are precisely the rows worth
  keeping.
- **It tolerates a half-written final line**, because the file may be read while a
  seed is appending to it. Any earlier line failing to parse is a hard error.

**2. The effective bar is 57.0%, not "around 58%".**

The success-criterion section computes the bar as a quotation. `smallest_clearing`
computes it: at 200 games the smallest clearing count is **114 = 57.0%**, whose
interval is [50.1%, 63.7%]. One win fewer, 113 = 56.5%, gives [49.6%, 63.2%] and
fails. The entry's substantive point stands unchanged and is if anything
understated — "entirely above 50%" is a 57-point bar, not a 50-point one — but the
number is now computed by `scripts/exp015_analysis.py` rather than asserted, and
it is pinned by a test so a change to the interval cannot move it silently.

**3. "UCT gets several times the simulations" was wrong: it gets 1.03–1.15×.**

The secondary's justification predicts that at equal time "UCT gets several times
the simulations", and expected result 2 leans on it to argue the equal-time floor
is the harder bar and "may not clear". Measured, the ratio is **1.15×** (462
simulations) on seed 1 and **1.03×** (411) on seed 2.

**Mechanism, and it was foreseeable from this entry's own text.** The entry
reasons from the network agent costing ~10.9 s/game while prior-free UCT "does no
forward passes at all", and infers a large ratio. That compares the network's cost
against zero rather than against what UCT actually does: a random playout runs to
the end of the game — up to 25 plies of move generation and application — where a
network evaluation is one forward pass on a static position. The two per-move
costs land within 15% of each other, so equal-time and equal-simulations are
nearly the same experiment on this board at this budget.

**Consequences, and they cut against the run, not for it.** The secondary charges
the network far less for its cost than registered, so a seed clearing the
equal-time floor establishes correspondingly less. It stays secondary and stays
reported; the write-up must quote the measured ratio beside it and may not repeat
the "several times" framing. A design that genuinely charges for compute would
have to equalise something other than wall-clock per move, and that would be a new
entry, not a reinterpretation of this one.

**A second-order effect, recorded now so it is not discovered in the Result.** The
ratio is measured per seed against whatever the machine is doing at the time, so
UCT's budget differs seed to seed (411 and 462 so far). The equal-time arm is
therefore not a constant-difficulty bar and its rates are not strictly comparable
between seeds. The primary is unaffected: both agents there are pinned to 400
simulations.

**What this amendment does not change.** No criterion, no schedule, no decision
rule, no stopping rule, and no seed count. It adds one tracked artefact and
corrects two descriptive statements. The floor is still read per seed on the
Wilson interval at equal simulations, and solver agreement still gates nothing.

#### Result (2026-09-16) — four of five clear, and the spread is not sampling noise

Five runs of `scripts/exp015_h3_run.py`, one seed per invocation, 2026-09-05 to
2026-09-16. **135.0 h of machine time**, artefact
[`exp015-h3-training-5x5.json`](../results/exp015-h3-training-5x5.json),
per-generation histories
[`exp015-histories.json`](../results/exp015-histories.json), logs
`exp015-seed<N>.log`. Every interval below is recomputed from the win counts by
`scripts/exp015_analysis.py`, which also refuses to combine seeds until all five
exist and cross-checks each recomputation against what the run stored.

#### The primary: the equal-simulations floor

Champion against prior-free UCT, both at 400 simulations, 200 games, seats
alternating.

| seed | wins | rate | Wilson 95% | seats (first/second) | verdict |
|--:|--:|--:|:--|--:|:--|
| 1 | 128/200 | 64.0% | [57.1%, 70.3%] | 91/37 | CLEARS |
| 2 | 152/200 | 76.0% | [69.6%, 81.4%] | 97/55 | CLEARS |
| 3 | 126/200 | 63.0% | [56.1%, 69.4%] | 89/37 | CLEARS |
| **4** | **112/200** | **56.0%** | **[49.1%, 62.7%]** | 75/37 | **fails** |
| 5 | 124/200 | 62.0% | [55.1%, 68.4%] | 90/34 | CLEARS |

> **INSTABILITY RECORDED. H3's clause 1 is not satisfied.** The criterion is
> per-seed — every Wilson interval entirely above 50% — and seed 4's includes it.
> The registration's falsifiability clause says a failing seed is recorded as
> instability and never averaged away, so that is what this entry reports.

**The mean is 64.2% and it is not the result.** It is in the artefact because the
entry promised the five rates and their spread whatever happened, and it is the
number most likely to be quoted in place of the verdict. Nothing in this run
licenses "the learner beats prior-free UCT at 64%".

**Seed 4 missed by two games.** The bar at 200 games is 114 wins — computed, not
quoted; the registration's "around 58%" is 57.0% — and seed 4 returned 112. That
is recorded and it changes nothing: a pre-registered rule that bends for a
two-game miss is not a rule, and the same two games of noise would equally have
carried a genuinely unstable seed over the line. The fragility is the argument
for reporting all five rates, not for reinterpreting one.

#### The spread is a measurement, not one unlucky seed

This is the part that gives H3's clause 1 more than a shrug. The clause's
measurement column said "variance reported", and reported alone cannot be wrong.

| | |
|---|--:|
| rates | 64.0%, 76.0%, 63.0%, 56.0%, 62.0% |
| mean, sd | 64.2%, **7.3%** |
| range | 56.0% – 76.0% |
| sd expected from sampling alone at the pooled rate | **3.4%** |
| homogeneity χ² (4 df, 0.05 critical 9.488) | **18.52** |

**The seeds differ by more than the 200-game samples can explain.** Observed
spread is 2.2× the binomial expectation and the homogeneity test rejects a single
underlying rate. So the failure is not "one seed drew badly": training runs that
differ only in seed end up at genuinely different strengths, and 56% and 76% are
both things this pipeline produces.

**What the χ² does not do.** It gates nothing — the registered criterion is
per-seed precisely because a homogeneity test can pass while a seed sits below
50%. It also names no cause: nothing here separates seed-dependent training
dynamics from seed-dependent self-play data, and with five seeds nothing could.

#### The secondary, and a defect that costs it one of its five points

UCT receives the simulation count it can complete in the network agent's measured
per-move wall clock. Reported, gating nothing.

| seed | UCT sims | wins | rate | Wilson 95% | verdict |
|--:|--:|--:|--:|:--|:--|
| 1 | 462 | 121/200 | 60.5% | [53.6%, 67.0%] | CLEARS |
| 2 | 411 | 147/200 | 73.5% | [67.0%, 79.1%] | CLEARS |
| 3 | 470 | 111/200 | 55.5% | [48.6%, 62.2%] | fails |
| 4 | 425 | 106/200 | 53.0% | [46.1%, 59.8%] | fails |
| 5 | **400** | 124/200 | 62.0% | [55.1%, 68.4%] | **not a measurement — see below** |

**Seed 5's secondary is a byte-for-byte duplicate of its own primary.** The
measured ratio was **0.98** — the network came out *cheaper* per move than plain
UCT — and `equal_time_simulations` clamps with `max(SIMULATIONS, ...)`, so UCT
was given 400. With the same match seed and the same simulation count, the match
replayed identically: 124/200, seats 90/34, every field equal.

The clamp itself is defensible (never hand UCT *fewer* simulations than the
primary). What is not defensible is that the arm then reports as an independent
result that "clears". **The honest count is 2 of 4**, not 3 of 5. The instrument
should have detected `ratio <= 1` and recorded the arm as inapplicable, with the
reason — that at this budget the network is not the expensive agent — which is
itself the finding.

This is the second consequence of the same mistaken forecast the 2026-09-10
amendment corrects. The entry predicted UCT would get "several times" the
simulations at equal time; measured across five seeds it got **0.98× to 1.17×**,
and on one seed it got nothing at all. The secondary was registered as the harder
bar and it is barely a different bar.

#### The reference: generation 0

| seed | 1 | 2 | 3 | 4 | 5 |
|---|--:|--:|--:|--:|--:|
| rate | 12.5% | 13.5% | 6.0% | 11.0% | **3.0%** |

All five fail, none close. **The untrained prior is much worse than no prior** —
a randomly initialised network does not merely fail to help, it lands **36.5 to
47 points below the 50% an even match would give**. The obvious mechanism is
that an unformed prior steers PUCT away from what plain UCT would have explored,
but that is an inference from one number and is **not measured here**.

Two things this is good for and one it is not: it shows the floor is not
trivially passable, and it bounds what training moved — **45 to 62.5 points** per
seed, from the generation-0 rate to the trained one. It says nothing about how
good the trained agent is, since a terrible starting point is not evidence about
the destination.

#### Training, and what it does not explain

| seed | policy loss | best | value loss | promotions | champion |
|--:|:--|:--|:--|--:|:--|
| 1 | 5.204 → 3.879 | 3.734 @ 24 | 0.485 → 0.444 | 5/6 | gen 24 |
| 2 | 5.128 → 3.777 | 3.768 @ 27 | 0.613 → 0.440 | 5/6 | gen 29 |
| 3 | 5.162 → 3.735 | 3.719 @ 28 | 0.547 → 0.435 | 5/6 | gen 24 |
| 4 | 5.052 → 3.868 | 3.751 @ 24 | 0.585 → 0.420 | **4/6** | gen 24 |
| 5 | 5.148 → 3.838 | 3.823 @ 28 | 0.495 → 0.427 | 5/6 | gen 29 |

Gate trajectories, `+` promoted:

```
seed 1  g4:87.8%+  g9:59.8%+  g14:61.5%+  g19:60.2%+  g24:55.8%+  g29:54.8%-
seed 2  g4:91.8%+  g9:70.2%+  g14:61.3%+  g19:57.0%+  g24:53.8%-  g29:63.2%+
seed 3  g4:91.8%+  g9:84.5%+  g14:61.8%+  g19:60.5%+  g24:58.0%+  g29:49.8%-
seed 4  g4:90.0%+  g9:72.8%+  g14:60.0%+  g19:48.5%-  g24:63.2%+  g29:49.5%-
seed 5  g4:91.8%+  g9:74.0%+  g14:68.2%+  g19:57.2%+  g24:49.8%-  g29:64.2%+
```

**Improvement decays into the threshold.** The three early gates average **75.1%**
and the three late ones **56.4%**, with 6 of 15 late gates below the 55% line
against 0 of 15 early. By generation 19 the challenger is winning close matches,
which is what a run approaching the capacity of its budget looks like — and it is
also what a run whose gate has stopped discriminating looks like. This entry
cannot tell those apart.

**A correlation that is reported and not explained.** Seed 4 has the fewest
promotions (4 of 6) and the lowest floor rate, which is the story one wants. It
does not survive the other rows: seeds 1 and 3 also froze their champion at
generation 24 and landed at 64.0% and 63.0%, while seeds 2 and 5 both carried
generation 29 champions and landed 14 points apart. At five seeds, with one
failure, no such relationship is identifiable, and fitting one to this table
would be reading the outcome backwards.

**The gate's own discipline, as registered.** 30 gates at 400 games promoting on
a 55% point estimate promote an exactly-equal challenger 2.55% of the time, so
there is a **54.0% chance of at least one false promotion across the run**. That
is a coin flip on whether some champion in this table was promoted on noise. It
never touches the floor, which is read on an interval and against an opponent the
gate never sees — but it does mean "champion" in the table above is a weaker label
than it looks.

#### Cost

**135.0 h of machine time, 27.0 h per seed** (124.5 h training, 10.5 h floor
matches), against the **≈146 h** this entry projected from EXP-014. The
projection was 8% high — the first cost estimate in this project to land, and it
landed because it was built from a measured decomposition rather than from a
composed rate. Eleven calendar days, with the machine hibernating overnight; no
resume cost a generation.

#### Predictions, scored

1. **"All five seeds clear the equal-simulations floor" — FAILED.** Four did.
   The registration added "if the prior is worth nothing after 30 generations,
   something upstream is wrong", which is *not* what happened: seed 4's prior is
   worth something, just not reliably enough to clear a 57% bar.
2. **"The equal-time floor is closer, and may not clear" — held, for the wrong
   reason.** It did fail twice. But the prediction's mechanism — UCT getting
   several times the simulations — is wrong: measured, UCT got **0.98× to
   1.17×**. The arm is close to the primary because the two agents cost nearly
   the same per move, not because the network is being charged heavily for its
   compute.
3. **"Between-seed spread is the number to watch, not the mean" — held, and it
   is the entry's most useful line.** The spread is what carries the verdict.

#### What this establishes

**That the learner learned something on four of five seeds, and that it does not
do so reliably.** Nothing more. Three boundaries, stated here because they are
what a reader will be tempted to cross:

- **Not "the learner is good".** Prior-free UCT with random playouts is a low
  bar by construction. How good the learner is comes from H3's clause 2.
- **H3 cannot be closed.** Clause 2 — agreement with the solver's exact verdict
  on the pre-declared comparison set — needs EXP-006's shipped-5×5 endgame sample
  at `k ≤ 8`, which has not been run. This entry produces the trained agents that
  read will consume; it computes no agreement rate and consults no solver output,
  which is what keeps adr-004 R1 intact.
- **One machine, one run.** Nothing separates a property of the learner from a
  property of this laptop's numerics.

And one boundary in the other direction: **the seat splits are not evidence for
H1.** They are large and consistent (75–97 wins as first against 34–55 as second)
and they are confounded, because the two seats are held by different agents. H1
is measured in Phase 5 under a matched protocol.

#### What follows

- **R6 has materialised** — "AZ training unstable or non-convergent", scored 2×2
  at registration. One seed in five failing a floor, with the between-seed spread
  rejecting homogeneity, is that risk biting. The row needs the measured numbers
  and a revised likelihood.
- **The instrument defect is recorded, not repaired.** Fixing
  `equal_time_simulations` to record `ratio <= 1` as inapplicable is a change to a
  finished instrument; it belongs to whatever entry next runs an equal-time arm,
  and this entry's secondary must be quoted as 2 of 4 until then.
- **No restart.** Retraining with different hyperparameters to convert seed 4
  requires a new registered entry, as this one states. The instability is the
  result.

### EXP-016 — H1's shipped-board arm: the first-player rate under named, imperfect play

**Registered 2026-09-18, before the instrument exists.** The first Phase 5 entry,
and the first to carry the eight measurement-gate answers required by
[`docs/measurement-gates.md`](../docs/measurement-gates.md).

#### What H1 already has, and what this cannot add

H1 is *"with perfect play the first player wins (strictly, since draws are
impossible)"*, tested by exhaustive solve of the 3×3 and 5×3 plus a self-play win
rate on the full game.

**The exact half is finished and it is decisive.** Four exhaustive solves — 3×3
and 5×3, both deck arms — all return **P1**, all at `termination: exhausted`
(EXP-001, EXP-002). On every board where "perfect play" is computable, H1 holds.

**On the shipped 5×5, perfect play is not computable and this entry does not
pretend otherwise.** No self-play arm can establish a claim about perfect play
using an agent that does not play perfectly, and Phase 4 measured exactly how far
from perfect the best available agent is: EXP-006 puts the five champions 14
points below the solver-agreement bar. So what this entry produces is a different
quantity, stated in its title: **the first-player win rate under a named,
reproducible level of play**. It corroborates or it flags. **H1's verdict rests
on the exact arms**, and no sentence in any artefact may convert this arm into
evidence about perfect play.

Recorded this prominently because it is the single most likely misreading, and
because gate 1 is what forced it to be written down before the run.

#### The gates

**1 — the decision, and the number that changes it.** The verdict this arm feeds
is directional: is the shipped board's first-player rate above 50% under strong
play? The MDE is **2 points** — a true 52%. Below that the effect is smaller than
the gap between any two agent choices this project could have made, so resolving
it would buy a number nobody could act on. 2 points is therefore the threshold,
and the interval must exclude 50% to report a direction at all.

**2 — endpoints and labelling cost.** One endpoint, deterministic: who won. No
annotation, no grader. The cost is compute, priced in gate 3.

**3 — sizing, under the clustering unit actually in force.** This is the gate
that reshaped the entry, and the reshaping is a *reduction*.

The roadmap sketches "20 seeds × 1000 games". Under the **learner**, the training
seed is a clustering unit — EXP-015 measured a between-seed `sd` of **7.3%**
against a binomial 3.4% and rejected a common rate at `χ² = 18.52` — and the
arithmetic is brutal:

| design | half-width | cost |
|---|--:|--:|
| 5 existing champions | **9.06%** | 0 h |
| 20 training seeds | 3.42% | **540 h** |
| 60 training seeds | 1.89% | 1,620 h |

**The learner cannot carry this arm at any affordable resolution.** Five
champions resolve ±9 points; twenty seeds cost four times the entire Phase 4
budget.

**So the primary arm uses prior-free UCT, which has no training seed at all.**
It depends on no training, so its first-player rate is a property of the game and
the search budget alone — the learner's run-to-run variability cannot leak into
it. That is not a cost dodge: it is the better instrument for a claim *about the
game*, and it is the same reason EXP-015 used prior-free UCT for its floor.

Measured throughput, 2026-09-18, 24 games at six workers: **14.77 s/game, 244
games/h**. UCT self-play is *more* expensive per game than champion self-play
(10.24 s/game) because random playouts run to the end of the game while the
network does one forward pass — the same inversion EXP-015's equal-time arm found.

| games | half-width | cost |
|---|--:|--:|
| 1,250 | 2.77% | 5.1 h |
| **5,000** | **1.39%** | **20.5 h** |
| 20,000 | 0.69% | 82.1 h |

**Registered: 20 seeds × 250 games = 5,000 games, 20.5 h.** This honours the
roadmap's "20 seeds" literally while spending the games where they buy something.
At a true 52% the interval is [50.6%, 53.4%] and excludes 50%, so the 2-point MDE
is met. 20,000 games would buy a 1-point MDE for 62 additional hours, and gate 1
already says 1 point is not worth acting on.

**The twenty seeds are also the over-dispersion check, not decoration.** Under a
fixed agent the games should be i.i.d. and the seeds should *not* cluster; the
expected `sd` across 20 seeds of 250 games is **3.16%** if that holds. The
per-seed rates are reported and compared against it. **If they over-disperse, the
pooled interval is wrong and the entry says so** rather than quoting it — that is
gate 3 applied to this entry's own assumption rather than to someone else's.

**4 — the grader's ceiling.** Not applicable. The outcome is the final cell
count, computed by the engine; there is no judge.

**5 — superiority or equivalence.** Superiority, one-sided in interest but
reported as a two-sided interval against 50%. Declared now: a rate whose interval
contains 50% is reported as **no detected direction**, never as evidence that the
seats are equivalent. That claim would need an equivalence margin and this entry
does not have one.

**6 — the pilot estimates noise, never effect.** The 24-game timing probe above
established **throughput only**. Its win counts are not reported anywhere and do
not inform the design: at 24 games the half-width is ±20 points. Stated because
the probe exists and someone will find it.

**7 — the instrument runs against a known answer first.** `run_gate` counts
*challenger* wins with seats alternating, which is **not** the first-player rate:
recovering it needs `as_first + (games/2 − as_second)`. That arithmetic is where
this entry would silently produce a plausible wrong number, so
`scripts/eval_first_player_advantage.py` is a purpose-built self-play harness,
and before it reports anything it reproduces two known answers — a 5×1 board
where the value is exactly solvable, and a rigged agent that always loses as
first, which must return 0%.

**8 — the abort criterion.** The sizing fits: 20.5 h against a phase that has no
deadline and a machine that delivered 135 h in Phase 4. Had the honest sizing
exceeded the budget — which it does for the learner arm, at 540 h — the registered
response is to **report that the comparison is not affordable**, not to run 20
training seeds and quote an interval that cannot see its own effect.

#### Configuration

| | |
|---|---|
| variant | shipped **5×5**, `h1` |
| primary arm | prior-free UCT self-play, **400 simulations**, both seats |
| games | **20 seeds × 250 = 5,000** |
| opening | `EVALUATION_TEMPERATURE_PLIES = 4`, sampled from visit counts |
| secondary arm | the five EXP-015 champions, self-play, **250 games each = 1,250**, ~3.6 h |
| measure | fraction of games won by the player who moved first |
| interval | Wilson 95%, pooled, **reported with the per-seed dispersion check** |

**Why the opening is sampled.** At temperature zero a searcher is a pure function
of the position, so self-play replays one game. EXP-015 recorded that trap for
the evaluator gate; it applies with more force here, where both players *are* the
same agent.

#### Decision rule, fixed before the run

**The pooled Wilson 95% interval is computed on the 5,000 UCT games.**

- Interval entirely **above 50%** → the shipped board's first-player rate under
  prior-free UCT is above even, consistent with H1's exact verdicts.
- Interval entirely **below 50%** → **the informative outcome.** Four exact
  solves say P1 wins with perfect play; a shipped-board rate below even under
  strong play would say the advantage does not survive imperfect play, and that
  is a finding about the game's design, reported as such.
- Interval **containing 50%** → no detected direction at a 2-point MDE. Not
  evidence of equivalence.

**The secondary arm gates nothing** and is reported per champion with its own
interval. At five champions it resolves ±9 points and cannot decide anything; it
is there to say whether a stronger agent moves the number, and the two arms are
**never pooled**.

#### Threats to validity

- **Neither agent plays perfectly**, so neither arm speaks to H1's actual claim.
  This is stated in the entry's second section and repeated here because it is the
  failure mode that would survive review.
- **The rate is a property of the search budget too.** 400 simulations is
  inherited from EXP-015 so the two are comparable; a different budget could give
  a different rate, and nothing here measures that dependence.
- **The sampled opening weakens both players identically**, which keeps the
  comparison fair but means the measured rate is not the rate at full strength.
- **One machine, one engine.** The same limit every other entry in this registry
  carries.

#### Expected result, recorded before the run

1. **The interval clears 50%**, because four exact solves agree on the direction
   and nothing in Phase 4 suggested the shipped board reverses it.
2. **The magnitude is small — 52% to 56%.** A large advantage would likely have
   shown up in EXP-015's seat splits, and those, while large, are confounded and
   are not evidence here.
3. **The twenty seeds do not over-disperse.** A fixed agent should produce i.i.d.
   games. If they do, that is a quiet confirmation that the training seed — not
   the match seed — was the clustering unit all along.

#### Artefact

`results/exp016-first-player-5x5.json`, written by
`scripts/eval_first_player_advantage.py`. Verdict applied from the artefact by
the same script, and the per-seed rates go in whatever the pooled interval says.

#### Amendment (2026-09-18, same day) — **withdrawn before running**, and the gates are what withdrew it

Red-teamed the day it was registered, before the instrument existed. **Seven
blocking findings.** No data was ever collected; the total cost of the error is
this section. Superseded by **EXP-017**, which takes a new ID rather than
amending this one, because the *agent* changes and therefore the measured
quantity does — the same reason EXP-007 was not folded into EXP-005.

**The finding that withdrew it, and it was measured rather than argued.** The
primary arm gave prior-free UCT **400 simulations** against a root that
`ExpansionMode.POSITION` collapses to **325 distinct children** — 1.23
simulations per child. Measured on the shipped 5×5, three seeds per ply:

| ply | mover | distinct children | children visited at all | busiest child |
|--:|---|--:|--:|--:|
| 0 | P1 | 325 | **10–18 (4%)** | 288–373 of 400 |
| 1 | P2 | 343 | 32–91 (20%) | 39–247 |
| 2 | P1 | 346 | 9–56 (8%) | 231–366 |
| 6 | P1 | 397 | **3–19 (3%)** | 268–376 |

At that ratio PUCT is not searching, it is walking `board.cells` in order — an
unvisited child scores `1.5·√N/325`, which is 0.005 at the first simulation, so
one early rollout win holds the budget until its mean decays. `_select_child`
breaks ties with a strict `>` on generation order, `legal_moves` is cell-major,
and `group_by_position`'s own docstring warns that *"a fixed seed pins the child
ordering, which PUCT's tie-breaking reads at low visit counts."*

**The coverage is seat-dependent** — 20% at ply 1 against 3–8% at even plies —
and the two seats never face the same move list: P1 opens into 25 empty cells
and holds the joker throughout. So the registered design would have produced a
**tight, perfectly reproducible ±1.39% interval around a property of the cell
enumeration order**, and its second decision branch would have published that as
*"a finding about the game's design"*.

**Six further blocking findings, all sound, three verified here directly.**

- **The seed schedule collides.** `game_players` derives seats from
  `seed·2_000_003 + index` and `seed·3_000_017 + index`. Under the registered
  20 seeds × 250 games those families share **975 of 5,000** values — the
  challenger's RNG in match seed 3 game 25 is byte-identical to the champion's in
  match seed 2 game 0. One match seed × 5,000 games collides **zero** times.
- **No branch of the decision rule changed anything.** H1's verdict is fixed by
  the exact solves, the secondary gates nothing, and branch 3 gates nothing — so
  all three outcomes ship the same artefact. That is gate 1's own failure mode:
  a threshold with no decision behind it.
- **The entry violated its own boundary.** Section 2 forbade converting an
  imperfect-play measurement into a claim about perfect play; branch 2 called
  prior-free UCT "strong play" and promised "a finding about the game's design",
  and expected result 1 predicted the imperfect-play quantity *because* the exact
  solves agree.
- **"Honours the roadmap's 20 seeds literally" was false.** Match seeds over an
  agent with no training seed partition one i.i.d. stream and buy no
  independence; 20 × 250 and 1 × 5,000 are the same experiment.
- **`GateResult` mislabels its fields for this use** — `summary()` prints the
  challenger's two seat totals as "P1" and "P2", and `win_rate`/`ci_*`/`promoted`
  sit at ~50% by construction in a self-play match.
- **The 2-point MDE confused half-width with power.** At a true 52% the interval
  excludes 50% about **80%** of the time, not always. The registered `n` survives
  by coincidence — 5,000 games gives 80.4% power against 52.0% — but the
  justification was a narrative, which is EXP-006's underived-threshold defect in
  better clothes.

**What survived, recorded because a review that only reports failures is not a
review.** The seat arithmetic `as_first + (games/2 − as_second)` is correct
against `az/gate.py` line by line. The i.i.d. claim is correct. Gate 5
(superiority declared, equivalence refused for want of a margin) and gate 8 (a
real abort branch with the unaffordable arm priced at 540 h) both hold. Gate 6
applied EXP-014's precedent properly.

**What this cost, and what it bought.** One red-team pass and four short
measurements, against a 20.5-hour run that would have produced a publishable-
looking wrong number. This is the first entry written under
`docs/measurement-gates.md`, and the gates found the defect the author did not.

### EXP-017 — H1's shipped-board arm: the first-player rate under exact endgame play

**Registered 2026-09-18, before the instrument exists.** Replaces EXP-016,
withdrawn the same day. Everything EXP-016's red-team found is either fixed here
or recorded as a threat; the findings are not restated, only their consequences.

#### The subject, named honestly

The agent is `agents/solver_agent.py` in **both seats**: `max_nodes = 2,000,000`,
`search_below_k = 8`, falling back to `HeuristicAgent`. That is **not** a strong
player and the entry does not call it one. It is:

> **the heuristic for roughly seventeen plies, then perfect play for the last
> eight.**

Measured on this configuration, twelve self-play games: `proved_rate` **31%**,
reproducing EXP-008's independently measured 32%. So about a third of the plies
are proved and the rest are the fallback's, and **no rate below may be quoted
without that number** — the agent's own module docstring makes this a standing
requirement, and EXP-008 established the precedent.

**Why this agent rather than the learner or prior-free UCT.** Three properties,
and the third is the one EXP-016 lacked:

1. **No training seed.** Its output is a function of the game and the tie-break
   seed alone, so the learner's measured between-seed `sd` of 7.3% cannot leak
   in. A learner-based arm needs 20 training seeds — **540 h** — to resolve
   anything, which gate 8 already priced as unaffordable.
2. **Defined strength, already characterised.** EXP-008 measured it at 98.0%
   [96.4, 98.9] against random and 61.0% [56.7, 65.2] against the heuristic it
   falls back on.
3. **Its move choice is not an artefact of enumeration order.** `HeuristicAgent`
   takes the maximum net flip and breaks ties with `rng.choice`, not with the
   first element of a cell-major list. This is what EXP-016 failed, and it is why
   the substitution is a repair rather than a second guess.

**And it plays the last eight plies exactly** — which is where a first-player
advantage on a filling board actually resolves, since the winner is a cell count.

#### The gates

**1 — the decision, and the consequence attached to it.** EXP-016 answered this
in form and failed it in substance: all three branches shipped the same artefact.
Here the branches differ.

H1's verdict is **not** at stake — four exhaustive solves (3×3 and 5×3, both deck
arms, all `termination: exhausted`) already return P1, and that is H1's evidence.
What this entry decides is **whether Phase 5 must run a strength-dependence
sweep**: if the shipped board's first-player rate under exact endgame play does
*not* clear 50%, the direction is not robust to the level of play, and the
registered consequence is that the planned sensitivity sweep over simulations and
`c_puct` becomes **mandatory rather than optional**, with a risk-register row
opened for it. That is a real consequence, declared before the run.

**MDE: 2 points.** Derived as power, not as half-width: at `se = 0.5/√5000 =
0.707 pp`, 80% power at two-sided α = 0.05 needs `δ = 2.80·se = 1.98 pp`. So
**5,000 games gives 80.4% power against a true 52.0%, and 29% against 51.0%.**
Below 52% this design is not expected to resolve direction, and that is the
registered limit rather than a hope.

**2 — endpoints and labelling cost.** One deterministic endpoint: who won, from
the final cell count. No annotation. The cost is compute, priced next.

**3 — sizing under the clustering unit actually in force.** There is no training
seed, so the only unit is the game. Measured 2026-09-18, twelve games, CPython,
one worker: **7.95 s/game**, and `pypy3` is available at `/usr/bin/pypy3` — the
interpreter EXP-008 used, where the same work ran roughly 2.4× faster.

| games | half-width | power at 52% | cost, 1 worker CPython |
|--:|--:|--:|--:|
| 1,250 | 2.77% | 29% | 2.8 h |
| **5,000** | **1.39%** | **80%** | **11.0 h** |
| 20,000 | 0.69% | >99% | 44.2 h |

**Registered: 5,000 games, one match seed.** One seed and not twenty, because
twenty buy no independence over a fixed agent and **do** collide: EXP-016's
schedule shared 975 of 5,000 player seeds across match seeds, while `index <
5000 < 1_000_014` cannot collide. The harness asserts all 10,000 derived player
seeds are distinct at startup and aborts otherwise, rather than trusting the
arithmetic.

**4 — the grader's ceiling.** Not applicable: the outcome is the engine's own
cell count. The endgame half of the agent is exact by construction under
adr-004, and `proved_rate` says how much of the game that covers.

**5 — superiority or equivalence.** Superiority, reported as a two-sided Wilson
interval against 50%. An interval containing 50% is reported as **no detected
direction at a 2-point MDE** and is explicitly **not** evidence that the seats
are equivalent — that claim needs a margin declared in advance and this entry
does not have one.

**6 — the pilot estimates noise, never effect.** The twelve-game probe
established **cost, game diversity and `proved_rate` only**. Its win count is not
recorded anywhere in this entry and informs nothing: at twelve games the
half-width is ±28 points.

**7 — the instrument runs against a known answer first.** Two probes before any
number is reported, and both check the **artefact fields**, not only a return
value — EXP-016's registered probes would have passed through its labelling
defect:

- A **5×1 board**, where the game value is exactly solvable, so the harness's
  notion of "the first player won" is checked against a proof.
- A **rigged agent that always loses as first**, which must produce
  `first_player_rate == 0.0` in the written artefact.

`GateResult` is **not** persisted. Its `win_rate`, `ci_low`, `ci_high` and
`promoted` are challenger quantities that sit near 50% by construction in
self-play, and its `summary()` prints the challenger's seat totals labelled "P1"
and "P2". The artefact's own fields are named in the Artefact section below.

**8 — the abort criterion.** 11.0 h single-worker, less parallelised, against a
phase with no deadline. It fits. Had it not, the registered response is the one
EXP-016 wrote and kept: report that the comparison is not affordable rather than
run a study that cannot see its own effect.

#### Configuration

| | |
|---|---|
| variant | shipped **5×5**, `h1` |
| agent, both seats | `SolverAgent(max_nodes=2_000_000, search_below_k=8)`, fallback `HeuristicAgent` |
| games | **5,000**, one match seed, per-seat tie-break seeds derived from the game index |
| diversity | from the heuristic's random tie-break — **no artificial random opening** |
| measure | fraction of games won by the player who moved first |
| interval | Wilson 95%, quoted only beside `proved_rate` and the distinct-game count |

**Diversity is measured, not assumed.** EXP-016's red-team raised the nominal-`n`
trap: a deterministic agent replays one game while the artefact reports `n =
5,000`. Measured here, twelve games produced **twelve distinct games**. The
harness counts distinct complete games anyway and **the interval is quoted
against the distinct count** if it falls below the nominal one.

No random opening is imposed. EXP-016's replacement design considered forcing
`R` random plies, which would have had to be even to stay seat-symmetric and
would have changed the estimand to "from a random opening". The heuristic's
tie-break supplies diversity without that cost.

#### Decision rule, fixed before the run

On the 5,000 games, pooled Wilson 95%:

- **Entirely above 50%** → the first-player advantage survives this level of
  play. Descriptive; changes nothing; H1's verdict still rests on the exact arms.
- **Entirely below 50%** → the advantage does not survive play that is heuristic
  for seventeen plies and exact for eight. **The sensitivity sweep becomes
  mandatory** and a risk row is opened. Whether this is about the game or about
  the level of play is *not answered here*.
- **Containing 50%** → no detected direction at a 2-point MDE. Not equivalence.

#### Threats to validity

- **This says nothing about perfect play, and no artefact may claim it does.**
  The agent proves 31% of its plies. H1 is a claim about perfect play, and its
  evidence is the four exact solves.
- **The rate is substantially a property of `HeuristicAgent`**, which chooses by
  maximum net flip this ply — a one-ply greedy rule. EXP-008 recorded the same
  caveat for the same reason.
- **The 8-ply exact window is seat-neutral, but the heuristic phase is not.**
  Branching differs by ply and P1 carries the joker throughout, so the two seats
  face different move sets at every ply. Unmeasured, and plausibly of order the
  MDE.
- **`search_below_k = 8` is inherited from EXP-003's measurement, not tuned
  here.** A larger exact window would be a different agent and a different entry.
- **One machine, one engine, one interpreter.**

#### Expected result, recorded before the run

1. **The interval clears 50%.** Stated as a **prior, not as evidence**: the four
   exact solves are about a different quantity on different boards, and using
   them to predict this one is the inference this entry forbids in the other
   direction.
2. **The magnitude is small, 51–55%**, and may fall below the 2-point MDE, in
   which case branch 3 fires and the honest report is that the design could not
   resolve it.
3. **`proved_rate` lands near 31%**, reproducing the probe and EXP-008.

#### Artefact

`results/exp017-first-player-5x5.json`, written by
`scripts/eval_first_player_advantage.py`. Fields, named before the run:
`games`, `first_player_wins`, `first_player_rate`, `wilson_low`, `wilson_high`,
`distinct_games`, `proved_plies`, `unattempted_plies`, `proved_rate`,
`match_seed`, `simulations_not_applicable`, `search_below_k`, `max_nodes`,
`variant`, `deck_arm`, `workers`, `interpreter`, `seconds`.

**The verdict is applied by a separate script**, `scripts/exp017_analysis.py`,
reading only the artefact — the EXP-015 split, which is what let that entry's
analysis refuse to combine seeds and cross-check its own recomputation. Per-seat
and per-group rates are reported **unconditionally**, whatever the pooled
interval says.

#### Result (2026-09-18) — 54.2%, and the first entry whose three predictions all held

Run `scripts/eval_first_player_advantage.py` under **PyPy 3.11.15**, 5,000
games, artefact
[`exp017-first-player-5x5.json`](../results/exp017-first-player-5x5.json), log
[`exp017-first-player.log`](../results/exp017-first-player.log). Verdict applied
by `scripts/exp017_analysis.py`, which reads only the artefact.

#### The rate

| | |
|---|--:|
| first player wins | **2,712 / 5,000** |
| rate | **54.24%** |
| Wilson 95% | **[52.86%, 55.62%]** |
| distinct games | **5,000 / 5,000** |
| `proved_rate` | **32.0%** |

> **The interval is entirely above 50%.** Under play that is heuristic for
> roughly seventeen plies and **exact for the last eight**, the first player wins
> the shipped 5×5 more often than not.

**And that is all it is.** H1 is a claim about *perfect* play; its evidence is
the four exhaustive solves — 3×3 and 5×3, both deck arms, every one returning
**P1** at `termination: exhausted`. This entry corroborates the direction on a
board no solver reaches. It does not demonstrate it, and the registered
consequence of the other branch does not fire: **the Phase 5 sensitivity sweep
stays optional.**

**No rate here may be quoted without the 32%.** Roughly a third of the plies are
proved and the rest are a one-ply greedy heuristic's, so this is substantially a
fact about `HeuristicAgent` — the caveat EXP-008 established for the same agent,
enforced here by an analysis script that prints `proved_rate` above the rate and
refuses to print one without it.

#### All three registered predictions held

The first time in this project. Recorded because the failures have been recorded
throughout, and a register that only notes misses is as biased as one that only
notes hits.

| prediction | outcome |
|---|---|
| the interval clears 50% | **held** — lower limit 52.86% |
| the magnitude is small, 51–55% | **held** — 54.24% |
| `proved_rate` lands near 31% | **held** — 32.0%, against EXP-008's independently measured 32% |

#### What was checked before the number was believed

**The gate-7 self-check ran before any measurement and is stored in the
artefact** with the values it reached: perfect self-play on the 5×1 returned
**1.0** against an expected 1.0 — the 5×1's first player wins with perfect play,
proved in 216 nodes — and a rigged first player that hands the opponent a win
returned **0.0** against an expected 0.0. The analysis refuses to emit a verdict
if either had diverged, and a probe on the instrument confirmed the check can
fail: inverting the seat attribution turns four tests red.

**The ply accounting closes exactly.** 39,967 proved + 85,000 not attempted +
**33** over budget = **125,000 = 5,000 × 25**. No ply is unaccounted for, and the
33 are the "we tried and could not" category the agent keeps separate from "we
did not try" — 0.03%, reported rather than discovered later.

**The interval was recomputed from the win count** by the analysis and matched
the stored one to four decimal places.

**Every game is distinct**, so the denominator is the nominal one. The
heuristic's random tie-break supplied full diversity without an imposed random
opening, as the twelve-game pilot indicated. The registered shortfall rule —
quote the interval against the distinct count — did not need to fire.

#### Cost, and the interpreter

**5,000 games under PyPy 3.11 against a measured 2.16 s/game**, roughly three
hours single-process. CPython measured **7.95 s/game** on the same twelve-game
pilot, a **3.7×** difference, and **both interpreters produced identical games
and identical winners** — a determinism check the cost measurement gave away for
free.

Deliberately not parallelised. At three hours there was nothing to buy, and
EXP-014 is this project's record of what parallelising costs to get right.

#### What this does not establish

- **Nothing about perfect play**, which is H1's actual subject.
- **Nothing about a different level of play.** The rate is a property of this
  agent at `search_below_k = 8`; a wider exact window is a different agent and a
  different entry.
- **The seat asymmetry in the heuristic phase is unmeasured.** The 8-ply exact
  window is seat-neutral, but branching differs by ply and P1 carries the joker
  throughout, so the two seats face different move sets at every heuristic ply.
  Plausibly of order the 2-point MDE, and not separated here.
- **One machine, one engine, one interpreter** — though the CPython/PyPy
  agreement narrows the last of those slightly.

#### Why this entry is short and the one above it is long

EXP-016 registered the same question with prior-free UCT and was withdrawn the
same day, before running, when the red-team measured that 400 simulations visit
**10–18 of 325** root children in board-cell order. That design would have
produced a tight, reproducible interval around a property of the enumeration
order. The cost of catching it was one review and four short measurements; the
cost of not catching it would have been 20.5 hours and a number that looked
publishable.

**This entry is what the gates bought.** It is the first registration written
under `docs/measurement-gates.md`, and the gates found the defect the author did
not.


## Planned

Sketched in Phase 0 so the phases have targets. IDs are allocated on
registration, not here.

> **Gate before you register.** From 2026-09-18, no Phase 5 or Phase 6
> experiment below is registered until its eight measurement-gate answers are
> written into its entry — see [`docs/measurement-gates.md`](../docs/measurement-gates.md).
> A gate answered "not applicable" says why in one line; a gate that cannot be
> answered is itself the finding, and the experiment is not run until it is.
>
> Two of the planned rows already fail a gate as sketched, and the file says so
> with the arithmetic: **H1's "20 seeds × 1000 games"** resolves ±3.42% at
> EXP-015's measured between-seed `sd`, so it cannot see a 2-point first-player
> advantage, and "20 seeds" is ambiguous between 540 h and 57 h of compute. **The
> joker-less variant** is an equivalence claim and needs a margin declared in
> advance, which a superiority test cannot supply afterwards.

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
| 6 | Archetype **win contribution** — the frequency half is withdrawn, see below | H5 |
| 6 | **Tile criticality** — for each archetype, the fraction of solved 5×3 positions whose value changes when that tile is removed from the hand | H5 |
| 6 | **Mirror-optimality rate** — on solved positions where the Z/2 mirror is a valid game symmetry (both `P3-y` placed), the fraction of optimal moves whose mirror image is also optimal | H5, H6 |
| 6 | **First-player advantage curve** — fraction of solved positions at each ply `t` won by the player to move, 5×3 | H1 |

> **Withdrawn 2026-09-18 — archetype placement frequency, before any entry was
> written.** The quantity is forced by the rules and cannot vary: 25 cells, no
> passing, both hands exhausting exactly, so every game places **each of the 12
> archetypes twice and the joker once**, for any agent and any strategy. Checked
> on 500 recorded games from EXP-017 — the count vector is `[2]×12 + [1]` in
> every one. A frequency analysis would therefore report a constant and read as
> a finding about the deck.
>
> This is the third measure in this project that the game's own structure fixes,
> after EXP-006's lost positions (every move preserves a loss) and EXP-016's root
> coverage. The pattern is worth stating for Phase 6: **before registering a
> measure, ask what the rules force it to be.** Gate 7 catches an instrument that
> computes the wrong thing; nothing in the eight gates catches a *quantity* that
> was never free to vary, and that gap is now three for three.
>
> **Win contribution survives** — it is not forced — and so do placement
> *timing*, cell choice and rotation choice. Each needs a dominance threshold
> declared before looking. See `docs/research.md`, H5.
