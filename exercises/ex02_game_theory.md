# ex02 — Game theory foundations

**Phase 2 problem set.** Six problems, from the roadmap's *Exercises — After
Phase 2*, restated against what the Phase 2 reading actually established.

**How to use this file.** Write **Answer** in first person, showing the work
including the wrong turns. **Refined** is written afterwards: corrections,
completed algebra, and the link back to the ADR each result feeds. Same loop as
the lit-notes.

**Feeds:** [research.md](../docs/research.md) H4 (Q6) ·
[adr-004](../docs/adr/adr-004-solver-approach.md) (Q2, Q3, Q4) ·
[adr-005](../docs/adr/adr-005-alphazero-scope-and-network.md) (Q5) ·
[adr-010](../docs/adr/adr-010-solver-correctness.md) (Q6c)

**Reading:** [R&N Ch.6](../notes/russell-norvig-aima-ch6-adversarial-search.md) ·
[Allis 1994](../notes/allis-1994-searching-for-solutions.md) ·
[Schaeffer 2007](../notes/schaeffer-2007-checkers-is-solved.md) ·
[Silver 2017](../notes/silver-2017-alphago-zero.md) /
[2018](../notes/silver-2018-alphazero.md) ·
[phase2-synthesis.md](../notes/phase2-synthesis.md)

> **Three corrections to the roadmap's original statements**, all established
> during Phase 2. They are kept visible rather than silently patched, because
> the corrections are themselves part of the answer.
>
> 1. Adversarial search is **Chapter 6** in AIMA 4th ed, not Chapter 5.
> 2. Q3's `O(b^{d/2})` is the *asymptotic* form. The exact Knuth–Moore count is
>    $b^{\lceil d/2 \rceil} + b^{\lfloor d/2 \rfloor} - 1$, and for FLIPHEX the
>    difference between the two is the whole point.
> 3. **Q6's formula as written in the roadmap is wrong** — three separate errors.
>    Diagnosing them *is* the exercise; see Q6.

---

## Q1 — The minimax theorem, and which theorem it actually is

**Problem.**

(a) State precisely what is guaranteed for a finite, two-player, zero-sum game of
perfect information, and **name the right theorem**. Careful: "the minimax
theorem" usually means von Neumann's result about *mixed* strategies in
simultaneous zero-sum games, which needs randomisation. The result that applies
to FLIPHEX is the backward-induction one (Zermelo / Kuhn) and it gives something
stronger — say what, and say why the extra strength comes from *sequential*
perfect information rather than from being zero-sum.

(b) Sketch the proof by induction on tree depth. Base case: terminal nodes. Step:
assume every child of $s$ has a well-defined value; construct the value of $s$.
State the induction hypothesis explicitly — most sketches skip it and the proof
does not survive.

(c) FLIPHEX is a clean instance. Justify each condition against the code, not
against intuition: **finite** (what bounds the depth, exactly?), **perfect
information** ([rules-canonical.md](../docs/rules-canonical.md) §2.4),
**deterministic**, **zero-sum**. Then: where does zero-sum enter the engine
concretely — which function, and what would break if a rule change made the game
non-zero-sum?

(d) Draws are impossible (25 cells, odd). What does that do to the *codomain* of
the value function, and name one thing it makes easier and one thing it makes
harder. (The second half is the trap; [S4](../notes/phase2-synthesis.md) has the
answer if you get stuck, but try first.)

**Answer.**

**Refined.**

---

## Q2 — Deriving alpha-beta, and what it returns when it prunes

**Problem.**

(a) Derive alpha-beta from minimax. Define $\alpha$ and $\beta$ as *invariants*
maintained on the path from the root — "the best value MAX can already guarantee"
and its dual — not as parameters that happen to get passed down.

(b) Prove the root value is unchanged. The argument is: whenever a branch is cut,
show the cut branch could not have influenced the root. Do this for a MAX node
and let the MIN case follow by symmetry.

(c) **The part that matters for this project.** After a cutoff, `MAX-VALUE`
does not return the minimax value of the node — it returns a **bound**. Write the
three cases:

$$
\text{ALPHA-BETA}(s,\alpha,\beta)
\begin{cases}
\le \alpha & \text{fail-low} \\
= v(s) & \alpha < v < \beta \\
\ge \beta & \text{fail-high}
\end{cases}
$$

Now the consequence: a transposition table storing these results must store a
*flag* alongside each value. Which flags, and what goes wrong if you store the
number alone? Then the bigger consequence — does an alpha-beta search over the
whole game tree yield a **strong** solution in Allis's sense, a **weak** one, or
neither? Justify from (c), not from the size of the tree.

**Answer.**

**Refined.**

---

## Q3 — Perfect ordering: the exact count, not the asymptotic one

**Problem.**

(a) Derive the best-case node count under perfect move ordering. Sketch the
structure: at a node on the principal variation all $b$ children must be
examined; at a node one ply below, a single child suffices to produce the cutoff.
Alternating those two levels gives the **Knuth–Moore** result

$$
N_{\min}(b,d) = b^{\lceil d/2 \rceil} + b^{\lfloor d/2 \rfloor} - 1 .
$$

Derive it; do not quote it. Then show it is $\Theta(b^{d/2})$ so the roadmap's
form is the asymptotic shadow of this.

(b) Apply it to FLIPHEX. Note $d$ is a **constant**, not a distribution: 25
cells, exactly one placement per ply, no passes and no captures, so every game is
exactly 25 plies. With $b_0 = 1450$ falling as cells fill and hands empty, the
game-tree complexity is ~$10^{61}$. Compute $N_{\min}$ for the 5×5 and for the
4×4 (adr-009 deck), using a sensible average $b$ for each — state the averaging
assumption you make and why it is defensible.

(c) **The punchline.** Compare each $N_{\min}$ to the corresponding *state count*
(4×4: $9.3 \times 10^{10}$; 5×5: $4.9 \times 10^{17}$). One of the two variants
is search-bound and the other is not. Which, by how many orders of magnitude, and
what does that imply about where engineering effort should go for the 4×4 exact
solve? Check your conclusion against
[adr-004's 2026-08-05 amendment](../docs/adr/adr-004-solver-approach.md) item 2 —
it should be the same finding, derived independently.

(d) Where does *iterative deepening* fit, given it re-searches shallower depths
repeatedly? Quantify the waste for $b$ in the hundreds, and say what it buys that
makes the waste worth paying (R&N §6.2.4 is explicit).

**Answer.**

**Refined.**

---

## Q4 — Transposition tables and Zobrist hashing

**Problem.**

(a) Explain why Zobrist hashing is $O(1)$-updatable per move. The property doing
the work is that XOR is its own inverse and is commutative/associative — show how
that turns "recompute the hash" into "toggle the changed components".

(b) Count the random words FLIPHEX needs, given the key is
`(cell, colour)` and `(player, tile)` per
[adr-003](../docs/adr/adr-003-piece-representation.md). *(The original adr-004
said 50; the 2026-08-05 amendment corrects it. Derive the number yourself before
looking.)* Then write the exact XOR sequence for one ply: purple places a tile on
cell $c$ whose arrows flip two enemy cells. How many XORs total, and what does
each one toggle?

(c) **Sufficiency, which is the real correctness question.** A TT is sound only
if the key is a *sufficient statistic*: two states with the same key must have
identical futures. Argue this for FLIPHEX from adr-003's inertness result — what
is deliberately **not** in the key, and why is leaving it out safe here when it
would not be in a game where placed pieces retain state? What would break if
[adr-006](../docs/adr/adr-006-no-chain-reaction.md) (flips never chain) were
false?

(d) Two pitfalls. **Collisions:** with a 64-bit key and $n$ stored entries,
estimate the collision probability by the birthday bound for $n$ at the 4×4
scale, and say whether it matters given
[adr-010](../docs/adr/adr-010-solver-correctness.md). **Replacement policy:**
name two policies and say which suits a *depth-limited search* versus a
*retrograde enumeration* — and whether the second even needs a TT.

**Answer.**

**Refined.**

---

## Q5 — PUCT against UCB1: derive one, and explain why the other cannot be

**Problem.** The formula:

$$
a^* = \arg\max_a\left[Q(s,a) + c_{\text{puct}} \cdot P(s,a) \cdot \frac{\sqrt{\sum_b N(s,b)}}{1 + N(s,a)}\right]
$$

(a) Identify each term's role (exploitation, prior, exploration) and write the
UCB1 selection rule beside it.

(b) **Derive UCB1** from Hoeffding's inequality: for a mean of $n$ bounded i.i.d.
samples, get the confidence radius, choose the confidence level that yields the
$\sqrt{\ln N / n}$ form, and state what "optimism in the face of uncertainty"
means once you have it.

(c) Now show that **PUCT is not derivable the same way** — it is not a
concentration bound on anything. Compare the two exploration terms on three
points: their value at $n(a) = 0$; their decay in $n(a)$ at fixed total $N$
($1/n$ versus $1/\sqrt{n}$); and what each one's guarantee is *conditional on*.
State plainly what is traded.

(d) **The FLIPHEX question.** $b_0 = 1450$. Show that plain UCT must spend its
first 1450 simulations before its formula distinguishes any child, and conclude
whether the UCT → PUCT substitution is *required* here or merely convenient.
Then the other half: AlphaZero also removes the rollout — is *that* required for
FLIPHEX? (Consider: playout length, termination, and whether R&N §6.4's
early-playout-termination machinery has anything to do here.) The two answers
differ; that difference is the point of the question and it is what
[adr-005's amendment](../docs/adr/adr-005-alphazero-scope-and-network.md) item 3
turns on.

(e) The substitution nobody lists: search visit counts become the policy training
target, $\pi \propto N^{1/\tau}$. Why is *that* the change that makes AlphaZero
more than guided MCTS?

**Answer.**

**Refined.**

---

## Q6 — The state-space bound: find the errors, then derive it properly

**Problem.** The roadmap poses this exercise as:

> Estimate a preliminary upper bound for FLIPHEX's state-space size, using
> $\binom{25}{12} \times \binom{13}{12}$ (choice of empty cell × player-1 pieces
> × player-2 pieces) × orientations $(6^{25})$ × joker states (2).

**(a) That expression is wrong in three independent ways. Find them before
reading on.** One is a **modelling error** that an ADR overturned; one is a
**double-count**; and the combinatorial core is **mis-stated** — both in what it
claims to be choosing and in what it silently omits (there is a factor missing
that has nothing to do with the other two). For each: name it, say what the
correct treatment is, and cite the document that settles it.

**(b) Derive the corrected bound.** Sum over the number of filled cells $t$:

$$
\sum_{t=0}^{25} \binom{25}{t} \cdot 2^{t} \cdot \binom{13}{\lceil t/2 \rceil} \cdot \binom{12}{\lfloor t/2 \rfloor} \;\approx\; 4.89 \times 10^{17}
$$

Justify **every factor**: why $\binom{25}{t}$, why $2^t$ and not $3^t$, why the
two hand terms have different upper indices (13 and 12 — see
[rules-canonical.md](../docs/rules-canonical.md) §2, and note both players play
*all* their tiles), and why the ceiling/floor split is forced. Then state what
the expression **over-counts** — it is an upper bound on reachable states, not a
count of them — and name the mechanism by which a counted configuration can fail
to be reachable.

**(c) The layer profile, which is where the exercise earns its keep.** Evaluate
the summand as a function of $t$ and plot or tabulate it. Answer:

- Where does it peak, and what fraction of the total sits in that layer?
- What is the terminal layer $t = 25$, in closed form? (You should get a number
  small enough to enumerate in seconds — this is exactly why
  [adr-010](../docs/adr/adr-010-solver-correctness.md) makes `V0` verification
  zero.)
- The shape is a **hump**, not a funnel. Contrast with checkers, where captures
  are irreversible. Why does that shape mean FLIPHEX has no *early* convergence
  to exploit, and why does it kill meet-in-the-middle enumeration?

**(d) Place FLIPHEX on both Allis axes, for H4.** State-space and game-tree
complexity are independent. Fill in the row for FLIPHEX 5×5 and 4×4 against
Nine Men's Morris ($10^{11}$), Awari ($10^{12}$), Connect Four ($10^{14}$) and
checkers ($5 \times 10^{20}$). Then answer the question H4 now asserts: **checkers
has ~1000× more states than FLIPHEX 5×5 and was solved — why will FLIPHEX 5×5
not be?** The answer must use both axes, and it must name the quantity that
actually binds.

**Answer.**

**Refined.**

---

## Lessons Learned

_(first-person, at phase close — not ghost-written)_

## Failed Attempts

_(first-person, at phase close — not ghost-written)_
