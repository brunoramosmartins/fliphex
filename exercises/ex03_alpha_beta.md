# ex03 — Alpha-beta, transposition, and retrograde analysis

**Phase 3 problem set.** Six problems, from the roadmap's *Exercises — After
Phase 3*, restated against what Phase 3 actually built and measured.

**How to use this file.** Write **Answer** in first person, showing the work
including the wrong turns. **Refined** is written afterwards: corrections,
completed algebra, and the link back to the ADR each result feeds. Same loop as
the lit-notes and ex02.

**Feeds:** [adr-004](../docs/adr/adr-004-solver-approach.md) (Q1, Q2, Q3, Q4) ·
[adr-010](../docs/adr/adr-010-solver-correctness.md) (Q5, Q6) ·
[adr-012](../docs/adr/adr-012-endgame-database-storage.md) (Q5) ·
[experiments/registry.md](../experiments/registry.md) EXP-001, EXP-003, EXP-007

**Reading:** [R&N Ch.6](../notes/russell-norvig-aima-ch6-adversarial-search.md)
§6.2 · [Schaeffer 2007](../notes/schaeffer-2007-checkers-is-solved.md) §5 ·
[phase3-solver-implementation.md](../notes/phase3-solver-implementation.md)

**Code under discussion:** [`solver/minimax.py`](../solver/minimax.py) ·
[`solver/transposition.py`](../solver/transposition.py) ·
[`solver/retrograde.py`](../solver/retrograde.py) ·
[`solver/packed_sweep.py`](../solver/packed_sweep.py)

> **Three corrections to the roadmap's statements**, all established during
> Phase 3. They are kept visible rather than silently patched, because
> diagnosing them is part of the exercise.
>
> 1. **Q4's premise is inverted.** It asks for the *maximum depth reachable* on
>    the 5×5 under a node budget. On FLIPHEX depth is not a free parameter — it
>    is exactly `N = 25`, and adr-004 gives the solver no evaluation function to
>    truncate with. `solver/minimax.py` proves or raises; there is no shallow
>    answer to return. The useful question is the inverse one, and Q4 asks it.
> 2. **`b_avg = 30` is wrong by more than an order of magnitude.** Ply 1 of the
>    5×5 has **1,450** legal moves (25 empty cells × 58 distinct (tile, rotation)
>    pairs). Any budget computed from `b = 30` is answering about a different
>    game.
> 3. **Q1's "α = −∞, β = +∞"** is `(LOSS, WIN) = (−1, +1)` here, and on a
>    two-valued objective that has a consequence the textbook proof does not
>    prepare you for. Q6 is about the consequence.

---

## Q1 — Alpha-beta returns the minimax value

**Problem.**

(a) **Prove** that alpha-beta called at the root with the full window returns
exactly what plain minimax returns. State the induction hypothesis explicitly —
it is not "the two agree at every node", because that is false, and finding the
correct hypothesis is most of the work. (Hint: the right statement is about what
the returned score tells you *relative to the window*, and it has three cases.)

(b) The proof gives you a licence and takes one away. Alpha-beta agrees with
minimax **at the root**, and at an interior node it may return a *bound* instead.
Which nodes are guaranteed exact, and why is that guarantee not inherited by a
node's children?

(c) Distinguish **fail-hard** from **fail-soft** and say which
`solver/minimax.py` implements — read `_negamax`, don't guess. Then: on a
two-valued objective, does the distinction have any observable consequence at
all? Justify either way.

(d) The pruning condition is `alpha >= beta`. `solver/minimax.py` guards it with
`if self.prune and alpha >= beta`. Explain precisely what `prune=False` must
*also* stop doing for the run to remain a faithful measuring instrument, and what
goes wrong if it does not. (This is the Phase 3 bug; reconstruct it before
reading the answer in the phase note.)

**Answer.**

**Refined.**

---

## Q2 — Iterative deepening with a transposition table

**Problem.**

(a) The standard argument: re-searching shallower depths is bounded because the
work forms a geometric series dominated by its last term. **State the series,
state the condition on `b` under which it converges to a small constant factor,
and give the factor** for `b = 30` and for `b = 1450`.

(b) FLIPHEX breaks the usual motivation for iterative deepening. Depth is a
constant, there is no evaluation function, and a partial search returns nothing
citable (adr-004 R1). So: **is iterative deepening worth anything here at all?**
Argue both sides, then commit. If your answer is "yes, for move ordering", say
exactly what the shallower searches provide that the transposition table's
`best` move does not already.

(c) A transposition table changes the accounting in (a), and not only by a
constant. Explain why the re-search is *not* simply repeated work when a table is
present, and identify the one condition under which the table's help collapses.
Q6 measures that condition.

**Answer.**

**Refined.**

---

## Q3 — A move-ordering heuristic for FLIPHEX

**Problem.**

(a) Propose an ordering. The roadmap's candidates are: moves that flip many
pieces, moves toward the centre, and low-arrow tiles played early. Evaluate each
against the actual rules — in particular, note that a flip **inverts** a
neighbour's colour regardless of whose piece it is (adr-007), so "flips many"
is not obviously "good". Say which of the three survive contact with that.

(b) Degree is not uniform on this board: interior cells have 6 neighbours,
boundary cells fewer. Get the degree histogram from
[`docs/board-geometry.md`](../docs/board-geometry.md) and say what it implies for
ordering on the 5×5 versus on the 3×3, where 8 of 9 cells are boundary cells.

(c) **The constraint that actually binds.** adr-004 R1–R3 govern what an Axis-1
*proof* run may be ordered by. Read them, then state which of your heuristics may
be used in a run whose value is cited in `docs/research.md`, and which may only
be used by the agent. Explain why the distinction exists — what would a
learner-seeded ordering do to the standing of an exact result?

(d) `SearchStats.ordering` records `internal | external`. What would have to be
true for that field to be *sufficient* provenance, and is it? (Consider: does the
field distinguish two internal heuristics from each other?)

**Answer.**

**Refined.**

---

## Q4 — What the 5×5 would actually cost

**Problem.**

The roadmap asks for the maximum depth reachable under a $10^9$-node budget with
$b_{\text{avg}} = 30$ and perfect ordering. Both premises are wrong here (see the
corrections above), so answer the corrected question.

(a) Derive the **exact** Knuth–Moore count for a uniform tree of branching $b$ and
depth $d$ under perfect ordering:
$$b^{\lceil d/2 \rceil} + b^{\lfloor d/2 \rfloor} - 1$$
and say in one sentence why it is not simply $b^{d/2}$.

(b) FLIPHEX's branching is **not** uniform. At ply $t$ it is
(empty cells) × (distinct (tile, rotation) pairs still in the mover's hand), so
it decays on both factors at once. Write $b(t)$ explicitly for the 5×5 and
compute the **geometric mean** over $t = 0 \dots 24$. Compare it to 30 and to
1,450, and say which of the two the naive figure is closer to.

(c) Using your $\bar b$ and $d = 25$, compute the perfectly-ordered node count.
Compare it to $10^9$, to the state-space bound $4.89 \times 10^{17}$, and to the
number of nodes EXP-001 actually spent proving the **3×3** (26,287,459 unpruned
at $2^{24}$ table slots, 115,615 pruned). Then answer: **is the 5×5 within reach
by forward search at all**, and if not, by what factor?

(d) EXP-003 measured the real thing at the other end: the median subtree below a
5×5 position with `k = 8` empty cells is **806,474** nodes, and with `k = 5` it
is **480**. Fit those two points against your $\bar b$ model and say whether the
model over- or under-predicts. A model that misses by 10× is still useful here —
say what for.

**Answer.**

**Refined.**

---

## Q5 — Retrograde analysis, and why it is a different program

**Problem.**

(a) **State and prove** the correctness of retrograde analysis: starting from
terminal positions of known value and sweeping backwards by layer, every
position's value is correct. Be explicit about what the induction is on and about
the property of FLIPHEX that makes "layer" a legitimate induction variable at
all. (What would break on a game where a move can *remove* a piece?)

(b) The sweep computes a value for **every** configuration in the space,
including ones no game can reach. Forward search computes values only for what it
reaches. Show that this is not a contradiction, and say which of the two is
computing something the other is not.

(c) EXP-007 measured the reachable closure on the 3×3: **27,860 of 711,963
configurations (3.91%) are unreachable**, and the two arms disagree (3.9131%
against 3.8866%). EXP-005 measured a *different* quantity — configurations with
no legal **predecessor** — and got 3.28% on both arms, identically. **Prove** the
identity behind that second number:
$$\text{orphans}(t) = \frac{\text{layer\_size}(t)}{2^t}$$
(Hint: characterise exactly which configurations have no predecessor, in terms of
the colour of the occupied cells. Then count.) Then explain why the identity
makes the count independent of the deck, and why the closure is not.

(d) adr-012 decision 7 allows don't-cares only from configurations with no legal
predecessor. Given (c), argue whether that clause is well-chosen, and what it
should say instead if it is not.

**Answer.**

**Refined.**

---

## Q6 — The transposition table is a lossy record

**Problem.**

This one has no textbook answer; it is what Phase 3 found by getting it wrong
three times.

(a) On a two-valued objective searched at `(LOSS, WIN)`, show that **no entry is
ever flagged `EXACT`** — every stored value is `UPPER` of `LOSS` or `LOWER` of
`WIN`. Then show that an extremal bound on a two-valued quantity *is* the value,
which is the licence adr-010 V3 uses to compare a stored bound against the sweep.

(b) Now break it. With `prune=False` but the window still narrowing, derive the
sequence of calls that produces an entry flagged `UPPER` with value `WIN`. How
many plies below the first node whose alpha reaches `WIN` does it first appear?
Explain why such an entry is *vacuous* and why V3 must refuse it rather than
compare it.

(c) `TranspositionTable` is direct-indexed: `self._slots[zobrist & mask]`, one
entry per slot. For `R` distinct positions in `C` slots under uniform hashing,
derive the expected number of occupied slots. Evaluate for the 3×3 at
$C = 2^{21}$ and $C = 2^{24}$ with $R = 684{,}103$, and compare against the
measured **604,347** and **679,202**.

(d) `store` keeps the deeper entry on a conflict and **returns without storing**
otherwise, incrementing no counter. Show that `replacements` is therefore a
*lower* bound on positions the table failed to retain, not a measure of it. Then
account exactly for the 3×3's residue at $2^{24}$: 684,103 reachable, 679,202
compared, 3,300 replacements, 511 reachable terminal configurations. The four
numbers close to the unit — show it.

(e) **The general lesson.** V3 reads the table as a *record of what the search
did*. List every way in which the table is not that record, and say what an
instrument would have to report for a coverage shortfall to be attributable
rather than merely disclosed. Compare your list against the three numbers adr-010
V3 now requires.

**Answer.**

**Refined.**
