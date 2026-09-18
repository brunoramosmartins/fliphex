# TIL #5 — AlphaZero in 500 lines, and the 1,200 that actually cost me

> **Skeleton only.** The prompts below are questions to write *from*, not an
> outline to fill in — the content is first-person and is deliberately not
> drafted here. Delete each prompt as you replace it.

## The hook — what surprised you

<!--
The title is a claim you can check, so check it. Measured on `az/` at the end of
Phase 4:

  core algorithm   1,040 lines of code   (mcts, network, train, selfplay,
                                          player, encoding, replay_buffer)
  infrastructure     649 lines of code   (checkpoint, gate, loop)
  docstrings       1,377 lines
  ------------------------------------------------------------------
  total            1,689 code, 3,554 raw

"AlphaZero in 500 lines" is roughly true of the part the papers describe, and
says nothing about the part that took the time. Candidate hooks — pick the one
that surprised *you*, not the one that sounds best:

- The algorithm was never the hard part. Which part was, and did you believe
  that before Phase 4?
- 649 lines exist only because the machine hibernates at night and a run takes
  135 hours. None of that is in either paper.
- Docstrings are 45% of the file volume. Is that a project-style artefact, or
  did writing the "why" first actually change what you built? You have evidence
  either way — cite it.
-->

## The mechanism — what the 500 lines are

<!--
The closed loop, stated so a reader who has not read the papers can follow it:
search generates data, data trains the network, the network guides the next
search. Search is not only the decision algorithm; it is the data-generation
mechanism. Your own Phase 2 Lessons Learned says this changed what you thought
AlphaZero *was* — that is the honest version of this section.

The one piece of real mathematics worth carrying, parked here from the Silver
2017 note: `π` is a stronger training target than the game outcome `z` because
MCTS runs lookahead and evaluates its leaves with the *same network's* value
head, so `π` aggregates many `v`-estimates into one lower-variance,
deeper-informed target. Search is a policy-improvement operator, and training on
`π` is what closes the loop. This is ex04 Q1(c); do the algebra there and quote
the conclusion here, not the reverse.
-->

## Where it bites in FLIPHEX — the 1,200 lines nobody writes about

<!--
Four candidates, all measured, all from the phase note. Two or three is plenty;
choosing which to drop is part of the writing.

- **Byte-equal resume.** A checkpoint written *inside* a gate carries a
  generation whose self-play and training already happened. The loop replayed
  both on resume, put the same games in the buffer twice, took another 400
  gradient steps — and nothing raised. Weights diverge silently. The existing
  test could not have caught it, and two probes had already shown that
  comparison passes on broken code. What does that say about what a test is for?

- **A gate that reports n = 400 while measuring a sample of size one.** Two
  searchers at temperature zero with no root noise are pure functions of the
  position, so they play the same game every time. The win rate comes out 100%
  and looks decisive. The fix is four plies of sampled opening.

- **`spawn` re-imports `__main__`.** So a harness whose scale lives in module
  constants silently runs at full scale in its workers, and a test of the
  spawned path written as a heredoc dies with `FileNotFoundError: '<stdin>'` —
  once per worker, in 21 MB of tracebacks.

- **A bug unreachable at `workers = 1`.** Workers rebuilt every network as the
  wrong class, so parallel self-play could not drive the adopted architecture.
  No single-process test could reach it. What is the general shape of that
  defect class?
-->

## The measurement that made the code worth writing

<!--
Optional but strong: the code is not the result. Phase 4's numbers are
14 points short of the bar, both of H3's clauses came back negative, and the
run cost 135 hours. Write two or three sentences on what a negative
pre-registered result is worth compared to a positive un-registered one — you
have the material, and this is the part of the project that is actually
unusual.

Resist the temptation to make it a redemption arc. "We failed but learned so
much" is a worse ending than "the bar was set in August, the agent scored 75.7%
in September, and that is the finding."
-->

## What you would tell someone starting

<!-- Two or three sentences. The thing you would put on a slide. -->

## Sources

<!--
- notes/silver-2017-alphago-zero.md — the loss, and why π beats z
- notes/silver-2018-alphazero.md
- notes/phase4-network-design-log.md — every measured number above
- exercises/ex04_alphazero_math.md — Q1 (the loss), Q3 (the temperature trap)
- experiments/registry.md — EXP-014 (the resume defect), EXP-015 (the run)
-->
