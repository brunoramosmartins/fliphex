# ex01 — Rules formalization

**Phase 1 problem set**, written retroactively (Phase 2). Four problems, from the
roadmap's *Exercises — After Phase 1*, restated against the engine as it was
actually built.

**How to use this file.** Write **Answer** in first person, showing the work
including the wrong turns. **Refined** is written afterwards: corrections,
completed algebra, and the link back to the code or ADR each result feeds.

**Feeds:** [rules-canonical.md](../docs/rules-canonical.md) §5 (invariants) ·
[adr-003](../docs/adr/adr-003-piece-representation.md) ·
[adr-005](../docs/adr/adr-005-alphazero-scope-and-network.md) (action space) ·
[adr-007](../docs/adr/adr-007-flip-toggles-colour.md)

**Code under discussion:** `fliphex/moves.py` (`legal_moves`, `apply_move`) ·
`fliphex/piece.py` (`distinct_rotations`) · `fliphex/rules.py` (`outcome`)

> **Note on Q2.** The roadmap states it as "cell × piece × rotation", which
> invites the answer $25 \times 13 \times 6 = 1950$. **That number is wrong**, and
> the reason it is wrong is the whole exercise. See Q2(a).

---

## Q1 — The game terminates in exactly 25 plies

**Problem.**

(a) Prove it. The claim is stronger than "terminates": the length is a
**constant**, not a bound and not a distribution. Structure the proof around a
monotone quantity and show it advances by exactly one per ply.

(b) The proof has two obligations most sketches skip. Discharge both:

- **The mover always has a legal move.** Show that no reachable state has the
  mover holding tiles but facing a full board, nor facing empty cells with an
  empty hand. Use [rules-canonical.md](../docs/rules-canonical.md) §5 **I3** —
  and note the two hands have *different* sizes (13 and 12), so the two cases are
  not symmetric.
- **The game cannot end early.** Is there any rule permitting a pass, a
  resignation, or a capture that removes a placed tile? Check §3 and §4 rather
  than assuming.

(c) **The non-obvious dependency.** The monotone quantity in (a) is only monotone
because of [adr-007](../docs/adr/adr-007-flip-toggles-colour.md). State exactly
which alternative flip semantics would break the proof, and say what the game's
length would become under it. (Hint: "flip" could plausibly have meant *remove*
or *capture to hand*; the ADR chose *toggle colour*.)

(d) Where does the fixed depth get used later? Name at least two downstream
places — one in the complexity analysis and one in the AZ design — where "$d$ is
a constant, not a distribution" changes a conclusion.

**Answer.**

**Refined.**

---

## Q2 — Counting legal moves

**Problem.**

**(a) Ply 1.** The naive count is $25 \text{ cells} \times 13 \text{ tiles}
\times 6 \text{ rotations} = 1950$. The true count is **1450**. Explain the gap
*from first principles* before looking at the code:

- A hex tile may be **rotated** freely but never turned face-down. So the set of
  arrow patterns a tile can present is its **rotation orbit** — the orbit of its
  arrow mask under the cyclic group $C_6$ acting on the six direction slots.
- Some orbits are shorter than 6, because some masks are fixed by a non-trivial
  rotation. Identify **which** archetypes those are and **why**, using the
  symmetry of the arrow pattern itself. Work out each orbit size by hand for at
  least `P6`, `P3-tri` and `P2-opp` before checking against
  `Piece.distinct_rotations()`.
- Two distinct (tile, rotation) pairs producing the same pattern would generate
  duplicate moves with identical successors. Explain why move generation must
  deduplicate, and what would go wrong in search if it did not (think about the
  branching factor, the policy target in
  [adr-005](../docs/adr/adr-005-alphazero-scope-and-network.md), and node counts
  in any reported benchmark).

Then: sum the orbit sizes over the 13 tiles Player 1 holds, multiply by 25, and
confirm 1450. Do the same for Player 2, who holds 12 tiles and **no joker** —
the numbers differ, and the difference is not 1×25.

**(b) The joker.** Its orbit size is 1. Explain why from
[rules-canonical.md](../docs/rules-canonical.md) §6 without computing anything.

**(c) Ply 12, best and worst case.** At ply 12 it is Player 2 to move. Work out,
in order: how many cells are filled, how many are empty, and how many tiles the
mover still holds. Then bound the move count:

$$
|\text{ACTIONS}(s)| \;=\; (\text{empty cells}) \times \sum_{\text{tiles held}} |\text{orbit}(\text{tile})|
$$

**Worst case** = the mover holds the tiles with the *smallest* orbits; **best
case** = the largest. Compute both. State clearly which parts of your answer are
forced by the rules and which depend on *which* tiles happen to remain — the
second part is a fact about the deck, and it is why the branching factor decays
unevenly rather than smoothly.

**(d) Sanity check against the engine.** Verify (a) and (c) with `legal_moves`.
If your hand-derived worst case disagrees with a hand you can actually construct,
say which is wrong and why.

**(e) The action space is not the move count.**
[adr-005](../docs/adr/adr-005-alphazero-scope-and-network.md) sizes the policy
head over $25 \times 13 \times 6 = 1950$ slots even though at most 1450 are ever
legal. Is that a bug, a deliberate slack, or a consequence of the factored head?
Answer from the ADR, and say what the masking step has to do.

**Answer.**

**Refined.**

---

## Q3 — Draws are impossible

**Problem.**

(a) Prove it. The usual one-liner is "25 is odd, so the counts cannot be equal" —
which is **not a complete proof**. It needs two more facts. Name them and prove
each:

- every cell is occupied at the end (this is Q1, so state the dependency
  explicitly rather than assuming it), and
- every occupied cell carries exactly one of **two** colours, with no third state
  and no neutral cell ([adr-007](../docs/adr/adr-007-flip-toggles-colour.md)).

Only then does parity close the argument.

(b) Write the conclusion as a statement about the codomain of the value function,
and locate it in `fliphex/rules.py` — which function, and what does it return?

(c) **The invariant as a test.** A draw appearing anywhere is a *proof of a bug*,
not a position to inspect. That is `V2` in
[adr-010](../docs/adr/adr-010-solver-correctness.md). Where should the assertion
live so that it is **total** rather than sampled — in `outcome`, at every database
write, or both? Justify.

(d) **The trade.** No draws is not purely a gift. Name one thing it makes easier
for a *backward* (retrograde) computation and one thing it makes harder for a
*forward* proof. ([S4](../notes/phase2-synthesis.md) has the full answer; try
first — the forward half is the counter-intuitive one.)

**Answer.**

**Refined.**

---

## Q4 — The invariants

**Problem.**

(a) The roadmap asks for *the* invariant preserved by every move: pieces on the
board = ply number. State it precisely, then prove it is preserved by
`apply_move` — including the flip step, which touches cells it did not place on.

(b) [rules-canonical.md](../docs/rules-canonical.md) §5 lists **I1–I6**.
Reproduce them, then classify each as either an **inductive invariant** (must be
re-established by every move, and the proof of preservation is real work) or a
**consequence** (follows from the others plus the rules, and needs no separate
argument). This distinction is what decides which ones deserve an `assert`.

(c) **I3 is the load-bearing one.** It fixes both hand sizes as a function of the
ply. Show how it makes Q1(b) immediate, and show how it makes the hand a
*derived* quantity in principle — then explain why the state still stores hands
explicitly rather than recomputing them from the ply
([adr-003](../docs/adr/adr-003-piece-representation.md)). The answer is not
"performance".

(d) **What is deliberately *not* invariant.** `GameState` records `history`, and
`fliphex/state.py` documents it as "metadata only — never read by search". Argue
that dropping `history` preserves every invariant in §5, and connect this to
adr-003's claim that the state is a **sufficient statistic**. Then the sharp
version: name one rule that, if FLIPHEX had it, would make `history` load-bearing
and invalidate the transposition table.

**Answer.**

**Refined.**

---

## Lessons Learned

_(first-person, at phase close — not ghost-written)_

## Failed Attempts

_(first-person, at phase close — not ghost-written)_
