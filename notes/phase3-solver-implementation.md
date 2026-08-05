# Phase 3 — Axis 1: Exact Solver (implementation notes)

**Objective.** Produce *ground truth*: the exact game value of reduced FLIPHEX
variants, and exact values for the last `k` plies of the shipped 5×5 game. This
is the axis that can be wrong without crashing, so correctness apparatus is a
first-class deliverable, not an afterthought.

**Dates.** None — sequenced by dependency. Opened 2026-08-05.

**Governing decisions.** Read before writing code:

- [adr-004](../docs/adr/adr-004-solver-approach.md) — alpha-beta + TT + retrograde
  endgames, and its **Phase 2 amendment**: 4×4 is the primary exact-solve target,
  the problem is storage-bound rather than search-bound, Zobrist needs **76**
  words, and rules **R1/R2/R3** govern what an Axis-1 run may be seeded by.
- [adr-010](../docs/adr/adr-010-solver-correctness.md) — the six verification
  mechanisms **V0–V6**. No Axis-1 number reaches `docs/research.md` before its
  V-checks pass.
- [adr-009](../docs/adr/adr-009-reduced-deck-policy.md) — reduced decks keep `P6`
  and `P3-y`, then fill by ascending arrow count; 4×4 uses `a = 8`. Reduced
  boards are a computational device, not a physical variant.
- [adr-003](../docs/adr/adr-003-piece-representation.md) — the search state is
  colours + hand bitmasks + side to move. Never a tile identity or rotation.
- [adr-008](../docs/adr/adr-008-board-mirror-symmetry.md) — the Z/2 mirror is a
  *partial* game symmetry, valid only once both `P3-y` are placed. Folding it is
  legitimate inside the endgame databases and nowhere else.

**The shape of the problem, from Phase 2.** Depth is a constant (exactly `N`
plies on an `N`-cell board) and the layer profile is a **hump**, not a funnel —
the widest layer is the middle, so there is no convergence to exploit and
meeting in the middle is the worst available meeting point. Reference figures
from `scripts/layer_profile.py`:

| Board | cells | deck | bound | terminal layer |
|---|--:|---|--:|--:|
| 3×3 | 9 | full | 2.3 × 10⁹ | 512 |
| 4×4 | 16 | adr-009 (`a=8`) | 9.3 × 10¹⁰ | 65,536 |
| 5×5 | 25 | full (13 + 12) | 4.9 × 10¹⁷ | 33,554,432 |

Implementation order follows the dependency chain:
`reduced boards → transposition → minimax → ordering → 3×3 → retrograde → 4×4`.

## Reduced-variant framework

Parameterise the board by `(n_cols, cells_per_col)` and the deck by an
adr-009 composition, so that a "variant" is data rather than a code path. Every
solver artefact must carry its board size *and* its deck composition explicitly
— a bare "4×4 result" is ambiguous and adr-009 exists because of that.

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

## 3×3 — exhaustive solve

Correctness fixture, not a strategy microcosm. Record the game value and one
optimal principal variation.

## 4×4 — the strategically meaningful solve

## `solver/retrograde.py` — endgame databases on 5×5

Target `k ≤ 5` empty cells. The terminal layer is the closed-form base case
(adr-010 V0). Mirror folding is available here and only here.

## Verification — adr-010 V0–V6

V0 terminal layer in closed form · V1 per-layer counts against
`scripts/layer_profile.py` (the `perft` analogue, and the measurement of the
gap between the bound and reachability) · V2 the no-draw invariant asserted
totally · V3 3×3 solved twice by different methods · V4 random-sample
re-derivation on 4×4 · V5 checksums · V6 mirror consistency, against an
**unfolded** sample.

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
