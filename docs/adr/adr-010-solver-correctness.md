# ADR-010 — Solver correctness: verification as an architectural concern

**Status:** Accepted (Phase 2)
**Date:** 2026-08-05
**Deciders:** Bruno Ramos Martins

## Context

[adr-004](adr-004-solver-approach.md) commits Axis 1 to producing **ground
truth**: exact game values that H1, H2 and H3 rest on. It says nothing about how
those values are defended.

That gap is the whole risk. The 4×4 exact solve is a ~9.3 × 10¹⁰-state
enumeration ([adr-009](adr-009-reduced-deck-policy.md) deck) whose visible output
is a *single verdict* — "the first player wins" or "the second player wins".
Nobody can eyeball 10¹¹ entries, and the characteristic failure mode is not a
crash but a **plausible wrong answer**: an off-by-one in the layer sweep, a
Zobrist collision, a misapplied flip at a board edge, a truncated write. All of
these terminate normally and produce a verdict that looks exactly like a correct
one.

Schaeffer (2007) §5 is the precedent and it is deliberately modest. The paper
lists anticipated sources of error (*"algorithm bugs and data transmission
errors"*), *"verifying all computation results and doing consistency checks"*,
and notes that *"some of the computations have been independently verified"* —
only *some*, and §7 concedes that *"although important components of the checkers
proof have been independently verified, there may be skeptics."* If a Science
paper backed by 18 years and ~50 machines writes that sentence, the calibration
for a solo laptop project is set: correctness is established by **converging
independent evidence**, never by a run that finished.

FLIPHEX has two structural advantages checkers did not, and both are cheap enough
that declining to use them would be indefensible: a terminal layer that is small
and decidable **in closed form**, and a per-layer state count that is known **in
closed form** ([adr-003](adr-003-piece-representation.md)).

## Decision

The FLIPHEX solver treats correctness as an explicit architectural concern rather
than an implementation detail. **No computed database or game-theoretic result is
accepted solely on the basis of successful execution.** Correctness is
established through independent verification, global invariant checking,
integrity verification of stored data, and cross-validation against an
independently implemented reference solver on tractable subproblems. A result is
valid only if **all** applicable verification mechanisms agree; any disagreement
invalidates the run rather than being reconciled after the fact.

Six mechanisms, in the order they must pass. `V0` and `V1` are mandatory for
every solve; `V2`–`V4` are mandatory for any result cited in `research.md`; `V5`
is mandatory for any database written to disk.

**V0 — closed-form verification of the terminal layer.** Every position with the
board full is decided by *counting cells*: no search, no recursion, no
recurrence. The layer is small — 2¹⁶ = **65 536** positions on the 4×4 with the
default adr-009 deck, and 2²⁵ = **3.36 × 10⁷** on the 5×5. In both cases every
tile has been played, so the hand dimension collapses to a single point; a
joker-bearing variant multiplies the count by the leftover-tile choices and is
still trivially enumerable. The entire base case of the retrograde pass is
therefore checked exhaustively, in seconds, **against a definition rather than
against another implementation**. This is verification zero because a bug in the
base case silently poisons every layer above it, and no later check would
distinguish it from a genuine result.

**V1 — per-layer state counts against the combinatorial formula.** The number of
positions in layer `t` is known in closed form,
`C(N,t) · 2^t · C(d₁,⌈t/2⌉) · C(d₂,⌊t/2⌋)`, for a board of `N` cells and hands
of `d₁`, `d₂`. The enumerator's actual per-layer output is counted and compared.
This is the FLIPHEX analogue of chess's `perft`, and it catches the most likely
bug class — a generator that drops or duplicates positions — which every
value-level check would otherwise pass. The same run **doubles as the
reachability measurement**: the gap between the formula (which counts
configurations) and the enumeration (which counts positions actually reachable by
legal play) is a quantity `research.md` currently reports only as a bound.

**V2 — the no-draw invariant, asserted as a theorem.** Cell counts are odd
(25 on the 5×5, and any `N` used must be odd for the same reason), so a draw is
arithmetically impossible ([adr-007](adr-007-flip-toggles-colour.md)). **Any draw
value anywhere in the database is a proof of a bug**, not a position to inspect.
This is asserted at every write, not sampled: it is the cheapest possible check
and it is total.

**V3 — two independent methods must agree on the full 3×3.** The 3×3 variant
(2.3 × 10⁹ full deck, 7.1 × 10⁵ reduced) is solved twice, by **fundamentally
different** methods — forward alpha-beta with no database, and retrograde
enumeration — and the game-theoretic value of every position must match. This is
the FLIPHEX analogue of Schaeffer's architectural redundancy, whose real form is
worth stating precisely: his component 3 ran *"two different programs"* on the
same position, *"thus increasing the chances of obtaining a useful result"*.
[adr-004](adr-004-solver-approach.md) already designates the 3×3 as a correctness
fixture rather than a strategy microcosm; this is what it is a fixture *for*.

**V4 — random-sample re-derivation on the 4×4.** A random sample of solved 4×4
positions is re-derived by direct forward search **without consulting the
database**, and the values compared. Sample size and seed are recorded in
`experiments/registry.md` with the run. This is the only check that exercises the
4×4 value recurrence against something other than itself.

**V5 — integrity of stored data.** Every database file carries a checksum,
verified on load. This defends against the failure Schaeffer names explicitly
(*data transmission errors*) and against the mundane version — a truncated write
from a laptop that slept mid-run.

**V6 — mirror consistency in the endgame databases (5×5 only).** Where the mirror
is a valid game symmetry — both `P3-y` placed and inert, which is exactly the
endgame region the databases cover ([adr-008](adr-008-board-mirror-symmetry.md))
— the values of `s` and `M(s)` must be equal. This costs one permutation per
sampled entry and tests the flip rule, the geometry table and the value recurrence
simultaneously. Note it is a **check**, not only the ~2× compression adr-004's
amendment claims: if the databases fold on the mirror, V6 must be run against an
*unfolded* sample, or it verifies nothing.

**Claim wording.** Verification determines what may be written, not only what may
be believed. The strongest sentence a single implementation, run once, by one
person, is entitled to:

> An exhaustive retrograde enumeration of the 4×4 variant (deck per adr-009)
> assigns the initial position the value *W*. The computation passed every
> verification procedure in adr-010 — closed-form terminal-layer check, per-layer
> state counts against the combinatorial formula, the no-draw invariant, and
> agreement with an independent forward solver on the full 3×3 game and on a
> random sample of 4×4 positions. **It has not been independently
> reimplemented.**

The final clause is what makes the rest credible and it costs nothing. It is
also why `research.md`'s verdict column must carry an **evidence class** rather
than a bare verdict.

## Consequences

**Positive**

- The two closed-form checks (`V0`, `V1`) verify against *definitions*, not
  against other code, which is a strictly stronger form of evidence than
  cross-implementation agreement. Checkers had no comparable check; FLIPHEX gets
  it because the board is small and the terminal condition is arithmetic.
- `V1` produces the reachability measurement as a by-product, converting a number
  `research.md` currently reports as a bound into a measured quantity.
- `V3` gives the 3×3 solve a clear job. Without it the 3×3 is an underpowered
  strategic result; with it, it is the reference implementation.
- The claim wording is drafted **before** the result exists, so the verdict cannot
  be talked up after seeing it.

**Negative / accepted costs**

- `V3` requires **two** solver implementations for the 3×3, one of which is
  otherwise redundant. Accepted: it is the only mechanism here that would catch a
  shared misunderstanding of the *rules* rather than of the code.
- `V1` and `V2` run inside the enumeration hot loop. Both are O(1) per position
  and the sweep is storage-bound rather than compute-bound
  ([adr-004](adr-004-solver-approach.md) amendment), so the overhead is accepted
  without measurement; if it ever binds, `V1` may be sampled but `V2` may not.
- **Independent reimplementation is out of scope** for a solo project and is
  therefore a permanent, disclosed gap. It is named in the claim wording rather
  than hidden.

**Neutral**

- These mechanisms verify the *implementation*, never the *rules*. If
  `docs/rules-canonical.md` misdescribes FLIPHEX, every check here passes and the
  answer is still wrong. `OPEN-1` is the live instance.

## Alternatives considered

**Trust a single clean run.** The default, and the position the ADR exists to
reject. A ~10¹¹-state enumeration has no observable surface: silent bugs produce
plausible verdicts, so "it ran and gave an answer" is not evidence.

**Formal verification of the solver.** Proving the value recurrence correct in a
proof assistant. Rejected: it would verify the model, not the ~10¹¹ entries the
implementation actually produced, which is where the risk lives. `V0`–`V6` target
the failure modes that a proved-correct algorithm still suffers.

**Independent reimplementation of the 4×4 solver.** The strongest available
check and the one Schaeffer partially achieved. Rejected on cost for a solo
project; `V3` retains the idea at 3×3 scale, where a second implementation is
days rather than weeks, and the gap at 4×4 is disclosed.

**Sampling `V2` rather than asserting it.** Rejected. The no-draw check is a
single integer comparison and is the only *total* check available; degrading a
total check to a sampled one to save nothing measurable is a bad trade.

## Related

- [adr-004](adr-004-solver-approach.md) — the solver whose results this defends
- [adr-003](adr-003-piece-representation.md) — the closed-form state count `V1` uses
- [adr-007](adr-007-flip-toggles-colour.md) — why draws are impossible (`V2`)
- [adr-008](adr-008-board-mirror-symmetry.md) — the partial mirror `V6` exploits
- [adr-009](adr-009-reduced-deck-policy.md) — the decks these solves use
- `docs/research.md` — H1, H2, H3, and the evidence-class column
- `notes/schaeffer-2007-checkers-is-solved.md` — §5.1, §5.2 (the reading behind this)
