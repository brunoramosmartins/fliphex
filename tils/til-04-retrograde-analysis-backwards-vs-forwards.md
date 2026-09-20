# TIL #4 — Retrograde analysis: when backwards beats forwards

> **Skeleton only.** The prompts below are questions to write *from*, not an
> outline to fill in — the content is first-person and is deliberately not
> drafted here. Delete each prompt as you replace it.
>
> One structural warning before you start. The title states a direction, and
> this project **measured the opposite on its own main board**. Do not write
> around that. It is the most interesting thing in the piece, and a TIL that
> confirms its own title is worth less than one that had to correct it.

## The hook — what surprised you

<!--
Candidates, pick the one that actually surprised you at the time:

- Retrograde analysis is the technique that solved checkers and Awari, and the
  roadmap scheduled an endgame database for the 5x5 as a matter of course. The
  first question adr-012 asked was not "what format" but "does storing beat
  searching at all". It does not. Median nodes to prove one 5x5 position:
  480 at k=5, 806,474 at k=8. Under a second, every time, with no database.

- The version of that surprise that generalises: I was ready to build the
  artefact before I had checked that the artefact was cheaper than not having
  it. The measurement took an afternoon; the database was 150 TB.

- Or the other direction entirely: on the 5x3, backwards did not just win, it
  was the only thing that finished. Which is the real shape of the answer.
-->

## The mechanism — why the direction reverses

<!--
Forward search proves the root. Retrograde analysis proves everything.

Write the mechanism plainly: a sweep walks layers backwards from the terminal
positions, and each layer's values are a function only of the layer below, so
nothing is ever revisited and no search tree is built. The consequence is the
one that matters for Allis's taxonomy and it is worth stating explicitly —
forward alpha-beta from the opening, exhausted and proved, gives a *weak*
solution; the same game swept backwards gives a *strong* one. Both terminate,
both agree on who wins, and only one of them can answer a question about a
position you hand it.

Then the cost side, which is the whole trade: forward search pays per query and
touches only what it must; the sweep pays for the entire state space once,
whether or not anyone ever asks about most of it.

Do NOT re-derive the 580x speedup here. That is TIL #6 and it is a different
lesson (what an exhaustive sweep is paying for). One sentence and a link.
-->

## The answer is an interval, and reading Takizawa is what showed me that

<!--
This is the section the piece exists for.

EXP-003 looked for a single crossover k*. That was the wrong shape. The Othello
solve has *two* cuts with different justifications:

  - enumerable above:  can I hold the layer at all?   (a storage question)
  - solvable below:    can I prove a node on demand?  (a search question)

Backwards wins strictly between them. So the honest question is not "which is
faster" but "is the interval non-empty".

On the shipped 5x5, by empty cells k, at 2 bits per configuration:

  | k | layer size          | stored  |
  |---|--------------------:|--------:|
  | 1 | 5,452,595,200       | 1.4 GB  |
  | 2 | 392,586,854,400     | 98 GB   |
  | 3 | 9,029,497,651,200   | 2.3 TB  |
  | 8 | 50,173,893,918,720,000 | 12.5 PB |

Enumerable at k <= 1. Solvable on demand at k > 8. The cuts do not meet: across
k = 3..8 nothing is enumerable and everything is provable in under a second.
**The interval is empty**, and adr-012 Option B is closed by arithmetic rather
than by EXP-003's sampled medians alone.

Say what the empty interval means and resist making it sound like a defeat: it
is a positive result about the shape of this game.
-->

## The hump, and the part no instrument reaches

<!--
Layers are small at *both* ends and enormous in the middle — the opening is
enumerable to t <= 5 (8.0 GB), the endgame to k <= 2, and between them sit
eleven layers from t = 6 to t = 16, peaking at 1.09 x 10^17 configurations at
t = 15.

That interval is exactly where Takizawa's Algorithm 1 does its work, and it is
the part FLIPHEX has no instrument for: bridging it needs an evaluator whose
predictions are almost always right, which is Axis 2's job and Axis 2 did not
deliver one (H3 rejected, both clauses).

Worth two or three sentences on the shape: a game whose layer profile is a hump
rather than a funnel does not converge, and that is the opposite of checkers.
The three axes meet here and it is the only place in the project where they do.
-->

## Where backwards did win, and what it cost

<!--
The 5x3. 17,506,580,337 configurations, both arms, termination: exhausted, and
the result is a *strong* solution — the value of every position, not just the
opening. H1 and H2 rest on it.

Then the part Phase 7 made tangible, and which is the best concrete ending
available: the pygame window can seat the solver on top of that sweep instead of
a search, and then every move is a table lookup. proved_rate goes to 1.0 from
the opening rather than from the last eight cells. The cost, measured on a full
game: peak resident 3.0 GB, worst single move 4.9 s, 4.1 GB read from disk
across sixteen plies, because layer 9 alone is 1.2 GB.

So "solved" became something you can lose a game to, and the price of perfect
play turned out to be memory bandwidth. Two sentences, no more — the temptation
is to make this the whole piece.
-->

## The counting identity, if you want one more

<!--
Optional; include only if the piece is short without it.

EXP-005 was registered to *measure* the fraction of configurations with no legal
predecessor. Both 3x3 arms returned identical counts at every layer despite
different decks, which is not a coincidence:

    orphans(t) = layer_size(t) / 2^t, exactly

A configuration has no predecessor precisely when every occupied cell shows the
colour of the player who did *not* just move, because a tile's own arrows never
point at the cell it occupies. One colouring out of 2^t. It does not depend on
the arrow patterns at all, which is why the decks made no difference.

The lesson is not the identity, it is that an experiment ran for hours before
anyone noticed the quantity was closed form. Same shape as Q3 of ex05. If you
already made that point in TIL #6, cut this section.
-->

## What you would tell someone starting

<!--
Two or three sentences. The thing you would put on a slide.

The candidate, if you agree with it: before building the database, measure the
cost of not having one. The interesting number is not how fast the sweep runs,
it is whether the interval where it wins is non-empty at all.
-->

## Sources

<!--
- notes/phase3-solver-implementation.md — EXP-003, the two cuts, the layer table
- notes/phase6-complexity-log.md — the layer profile and the hump
- notes/schaeffer-2007-checkers-is-solved.md — retrograde at scale
- notes/takizawa-2023-othello-is-solved.md — the two cuts, Algorithm 1
- notes/allis-1994-searching-for-solutions.md — weak vs strong, quoted verbatim
  in complexity/comparison.py
- docs/adr/adr-012-endgame-database-storage.md — Option B, and decision 7
- experiments/registry.md — EXP-001, EXP-002, EXP-003, EXP-005
- tils/til-06-the-index-is-the-key.md — the 580x, which is NOT this piece
- exercises/ex05_complexity_analysis.md — Q6, on what "solved" licenses
-->
