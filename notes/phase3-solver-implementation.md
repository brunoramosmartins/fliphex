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

## `solver/minimax.py` — alpha-beta with TT

Alpha-beta returns **bounds**, not values, outside the initial window. TT
entries therefore need a flag (`exact` / `lower` / `upper`); storing a bound as
if it were exact is the defect that produces a plausible wrong answer rather
than a crash.

## Iterative deepening and move ordering

Ordering is an *agent* concern and a *proof* concern, and adr-004 splits them:
ordering that makes the agent strong is free to use anything; ordering inside a
run that will be cited as a proof is constrained by R1–R3.

## 3×3 — exhaustive solve (EXP-001)

Correctness fixture, not a strategy microcosm — and the adr-010 V3 artefact: the
same variant solved twice, forward and retrograde, agreeing on every position.
Record the game value and one optimal principal variation.

## 5×3 — the strategically meaningful solve (EXP-002)

## `solver/retrograde.py` — endgame on 5×5 (EXP-003)

The roadmap's `k ≤ 5` target is ~1.2 × 10¹⁵ positions, ~150 TB at one bit. Per
adr-012 the first question is not the format but whether storing beats searching
at all: the subtree below a `k = 5` node is order 10⁵–10⁷ nodes. The terminal
layer (4 MB) is built regardless — it is adr-010 V0's base case.

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

## H1 / H2 partial verdicts

Partial: on reduced variants only, with the evidence class stated per
`docs/research.md` (`exact`, qualified by verification status).

## Experiment registration

Every run in this phase has an `EXP-NNN` row in
[`experiments/registry.md`](../experiments/registry.md) **before** it starts.

## TIL drafts

TIL #2 — MCTS in perfect-information games. TIL #3 — alpha-beta from first
principles.

## Lessons Learned

## Failed Attempts
