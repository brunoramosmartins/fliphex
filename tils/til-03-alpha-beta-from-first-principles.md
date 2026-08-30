# TIL #3 — Alpha-beta from first principles

> **Skeleton only.** The prompts below are questions to write *from*, not an
> outline to fill in — the content is first-person and is deliberately not
> drafted here. Delete each prompt as you replace it.

## The hook — what surprised you

<!--
Candidates from Phase 3, pick what actually surprised you:

- A solver's alpha-beta has no evaluation function and no depth limit. It either
  proves the position or returns nothing. That is a different animal from the
  textbook depth-limited search, and agents/solver_agent.py exists because of it.
- Move ordering is an *agent* concern and a *proof* concern, and adr-004 splits
  them: ordering that makes the agent strong may use anything; ordering inside a
  run cited as a proof is constrained by R1-R3. Why does the distinction matter?
-->

## The mechanism

<!--
Why the cutoff is sound: what alpha and beta actually bound, and why a pruned
subtree cannot change the root value. Then the part that is easy to state wrong
— what a transposition table stores when the search is a *proof*, and why
verify=True (full state keys) rather than trusting the hash.
-->

## Where it bites in FLIPHEX

<!--
Two measured things from the phase:

- The short-circuit `while remaining and slot == SLOT_LOSS` in
  solver/packed_sweep.py:385 is alpha-beta's idea inside a retrograde sweep: a
  WIN stops at its first winning child, a LOSS must enumerate everything. The
  runtime profile reads that mix straight off — 785k cfg/s at t=10 against 84.9k
  at t=9. Four instruments now show the same parity split.
- EXP-003's medians: 480 nodes to prove k=5 on the 5x5, 806,474 at k=8. What
  does that say about where exhaustive search is and is not a tool?
-->

## What you would tell someone starting

<!-- Two or three sentences. The thing you would put on a slide. -->

## Sources

<!--
- notes/russell-norvig-aima-ch6-adversarial-search.md
- notes/allis-1994-searching-for-solutions.md
- docs/adr/adr-004-solver-approach.md
- docs/adr/adr-010-solver-correctness.md
-->
