# TIL #6 — 580× faster with the same algorithm: what an exhaustive sweep is really paying for

> **Draft.** Written the day the 5×3 sweep went from 108 days to 13 hours. Voice
> and examples still to be tightened before publishing.

I had a retrograde sweep that enumerated 711,963 game configurations in 448
seconds and needed to do the same for 17.5 *billion*. Straight-line
extrapolation: **108 days**. It now runs at a projected **13 hours**, and I did
not change the algorithm. Same sweep, same layer order, byte-identical output —
verified by checksum across two implementations and two interpreters.

Every one of those 580× came from not doing work that was never needed. That is
the part worth writing down, because the moves generalise well beyond my game.

## The four moves

### 1. Stop building objects you immediately throw away

The reference sweep constructed a full immutable `GameState` per configuration:
a tuple of cell colours, two hand bitmasks, and a **Zobrist hash computed over
every cell and every tile**. Then move generation allocated `Move` objects, and
applying a move built another whole state.

The Zobrist hash exists so a *search* can look positions up in a transposition
table. But in an exhaustive sweep, **the index is the key** — I visit
configuration `i`, I write to slot `i`, nothing is ever looked up by hash. The
hash was computed and discarded 17 times per configuration.

Replacing the object with four integers — occupied cells, one colour bitmask,
one spent-tile mask per player — and moving between them with bit operations:
**21×**.

*The general shape:* a data structure carries fields that serve **some**
consumers. In a hot loop that isn't one of them, those fields are pure overhead.
Hashes, provenance, audit trails, string labels, timestamps, anything
"for debugging" — all of it costs on every iteration whether or not anyone
reads it.

### 2. Compute the expensive part at the coarsest level it's constant over

Converting between "a configuration" and "an integer index" is the expensive
operation. The reference did it once per configuration. But the index has
nested structure: a rank for *which cells are filled*, then `2^t` colourings
beneath each of those, then hand-state ranks beneath each of those.

So I compute the cell rank **once per cell-subset** and reuse it across every
colouring below it. The expensive work drops from `layer_size` times to
`C(n, t)` times — on the 3×3, a factor of ~110.

*The general shape:* find the loop nest, then ask of each expensive computation
**which loop it is actually constant over**, and hoist it there. This is
loop-invariant code motion, which compilers do automatically in C and cannot do
in Python across dynamic dispatch — so in Python you do it by hand.

### 3. Tabulate what a runtime is recomputing

`math.comb` was being called once per filled cell, per successor. It became a
precomputed table indexed by list. The flip rule — which board cells each arrow
pattern points at — became a table built once at construction. Ranks of spent-
tile subsets fit in 8,192 entries, so all of them are precomputed.

*The general shape:* any pure function with a small domain, called in a hot
loop, should be a lookup. The test is *small domain*, not *expensive function* —
`comb` is cheap, and tabulating it still mattered because it ran billions of
times.

### 4. Then, and only then, change the runtime

After (1)–(3), the hot loop was pure integer arithmetic with no allocation.
That is precisely what a tracing JIT compiles well, so PyPy gave another **8×**
with zero code changes.

The ordering matters and is the least obvious lesson here. Had I reached for
PyPy first, it would have helped far less — a loop dominated by object
allocation and dictionary lookups is exactly where a JIT has least room. The
runtime switch paid *because* the code already had the right shape.

## How to spot this in a pipeline you didn't write

I've started asking five questions of any simulation loop, in this order:

1. **What is constructed per iteration, and who reads all of it?** Print the
   type. Count its fields. Ask which are read inside the loop. This is where
   the biggest wins hide, and it needs no profiler.
2. **Is there a key being computed that something else already knows?** Hashes,
   UUIDs, string keys, serialised identifiers. If the loop is already indexed
   by position, the key is redundant.
3. **What is recomputed at a deeper loop level than it varies?** Look for any
   expression inside the innermost loop whose inputs all come from outer loops.
4. **What pure function has a small domain?** Tabulate it.
5. **Is the hot loop allocation-free yet?** If not, a JIT or a rewrite in a
   faster language will disappoint. Fix the shape first.

Notice that four of the five are read from the source, not from a profiler. A
profiler tells you *where* time goes; it does not tell you that the work was
never needed. For that you have to know what the consumers actually read.

## The trade-offs, honestly

**You lose legibility.** The reference sweep says `apply_move(board, state,
move)`. The fast one says `purple ^ (flip[cell][pattern] & occupied)`. The
second is not readable as the rules of a game.

I handled that by keeping **both** and treating the reference as the definition:
it stays in the repo, it is what the correctness cross-check runs against, and
the fast path is compared against it byte for byte on every layer of every board
where both are affordable. If they ever disagree, the fast one is wrong.

**You risk quietly re-implementing the thing you were checking against.** This
is the subtle one. My project's strongest correctness argument is that two
independent solvers agree — which is only evidence *while they can disagree*.
Had I hand-copied the flip rule into the fast path, that argument would have
silently evaporated while every test still passed.

So the fast path does not restate the rule: it *tabulates* it by asking the
engine, once, at construction. And a test walks every (cell, tile, rotation) of
a real board asserting that the table predicts exactly what the engine does. If
someone "optimises" by inlining the rule later, that test fails.

**Memory and speed are not always a trade.** I packed the value table from 8
bits to 2 bits per entry to fit the sweep in RAM (10.05 GB → 2.51 GB) and
expected to pay for it. Measured, it cost **~2% on CPython and nothing at all on
PyPy** — see below.

## The measurement lesson, which cost me the most surprise

I benchmarked the packed read in isolation first: `(a[i >> 2] >> ((i & 3) << 1))
& 3` against `a[i]`. Result: **3.18× slower on CPython, 0.97× on PyPy** — free
under the JIT, because it folds the shift and mask into native instructions that
vanish beside the memory access.

Then I measured the actual sweep end to end. The cost was **2%**.

The micro-benchmark overstated the real cost by more than 150×, because it
isolated an operation that isn't the bottleneck — the rank arithmetic dominates,
and the extra shift disappears into it. If I had trusted it, I'd have rejected a
4× memory saving that was free.

Two things I now hold onto:

- **A micro-benchmark measures an operation. A decision needs the system.**
  Isolating something makes it *measurable*, which is not the same as making it
  *relevant*.
- **The same optimisation has different economics on different runtimes.** Bit
  packing is a real cost in an interpreter and free under a JIT. Any advice of
  the form "packing is/isn't worth it" is incomplete without naming the runtime.

## The takeaway

An exhaustive simulation spends most of its time on bookkeeping that exists for
consumers who aren't in the loop. Before optimising the algorithm, or reaching
for a faster language, ask what the loop constructs and who reads it. Then keep
the slow version as the definition of correct, and make the fast one prove it
agrees.

---

## Worth reading

**John Ousterhout, "Always Measure One Level Deeper", *Communications of the
ACM* 61(7), 2018, pp. 74–83.** DOI [10.1145/3213770](https://dl.acm.org/doi/10.1145/3213770) ·
[free PDF](https://rcs.uwaterloo.ca/~ali/cs854-f23/papers/onelevel.pdf)

Short, practical, and directly about the trap above: measuring only the number
you care about gives you no way to tell whether the number is *right*. His rule
is to also measure the level below, so that the top-line figure can be predicted
from underlying quantities — a discipline that would have caught my
micro-benchmark's irrelevance immediately. Read this one first; it is the one
that changes how you work.

**Leiserson, Thompson, Emer, Kuszmaul, Lampson, Sanchez & Schardl, "There's
plenty of room at the Top: What will drive computer performance after Moore's
law?", *Science* 368(6495), eaam9744, 2020.**
DOI [10.1126/science.aam9744](https://www.science.org/doi/10.1126/science.aam9744)

The argument for why this kind of work matters now: with miniaturisation ending,
performance has to come from software, algorithms and hardware architecture
instead. Their worked example is a matrix multiply taken from Python to tuned C,
gaining ~62,000× **without changing the algorithm** — the same phenomenon as
mine, four orders of magnitude further along. Read it for the framing, not for
technique.

---

**Related:** [`solver/packed_sweep.py`](../solver/packed_sweep.py) ·
[`solver/retrograde.py`](../solver/retrograde.py) (the reference) ·
[`tests/test_packed_sweep.py`](../tests/test_packed_sweep.py) ·
[`docs/adr/adr-010-solver-correctness.md`](../docs/adr/adr-010-solver-correctness.md) (why two implementations)
