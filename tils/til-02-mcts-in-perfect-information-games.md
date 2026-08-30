# TIL #2 — MCTS in perfect-information games

> **Skeleton only.** The prompts below are questions to write *from*, not an
> outline to fill in — the content is first-person and is deliberately not
> drafted here. Delete each prompt as you replace it.

## The hook — what surprised you

<!--
What did you actually not know before Phase 3? Candidates from the phase, but
pick the one that surprised *you*:

- MCTS is usually introduced as the answer to "no good evaluation function", but
  FLIPHEX's solver has no evaluation function either and does not use MCTS. What
  distinguishes the two situations?
- Phase 2's adr-005 amendment argued PUCT is *required* rather than inherited,
  because UCB1 is infinite at n(a) = 0 and must visit every child once. On the
  5x5 that is 1450 children — except it is 325 positions (adr-005 Phase 3
  amendment). Does that change the argument, and by how much?
-->

## The mechanism

<!--
Rollouts vs. a learned value head. R&N 6.4's early-playout-termination machinery
is void for FLIPHEX: playouts are <= 25 plies, always terminate, always yield a
decided winner. What follows from that?
-->

## Where it bites in FLIPHEX

<!--
The measured aliasing: 1450 root actions reach 325 distinct positions (4.46x),
2.28x over a whole game. Naive MCTS expands aliases as separate nodes and splits
one position's visit counts across up to six labels. Why is that a search-quality
problem and not a speed problem? What does transposition-aware expansion cost?
See docs/adr/adr-005 Phase 3 amendment and risk R13.
-->

## What you would tell someone starting

<!-- Two or three sentences. The thing you would put on a slide. -->

## Sources

<!--
- notes/silver-2017-alphago-zero.md
- notes/silver-2018-alphazero.md
- notes/russell-norvig-aima-ch6-adversarial-search.md
- docs/adr/adr-005-alphazero-scope-and-network.md
-->
