# ADR-006 — Flips do not chain

**Status:** Accepted (Phase 0)
**Date:** 2026-07-23
**Deciders:** Bruno Ramos Martins

## Context

When a placed tile's arrow flips a neighbour, that neighbour is itself a tile
with arrows. Whether those arrows fire in turn — a chain reaction — is the
single largest branch point in the game's design, and it is settled explicitly
on the 2017 poster, under *CUIDADOS!*:

> Após uma peça ser virada (flipada) aparecerá um lado com setas, não poderá
> gerar o efeito em cadeia de virar (flipar) as peças adjacentes a essa peça já
> flipada.

So this ADR does not *make* the decision — the designers made it in 2017. It
records it, and records what follows, because almost everything else in the
architecture depends on it.

## Decision

**A flip never propagates. Exactly one tile fires its arrows per ply: the tile
just placed.** Flipped tiles change colour and nothing else.

Equivalently: the recursion depth of `apply_move` is exactly 1.

Any chain-reaction variant is a **different game** and, if ever studied, gets
its own state class and its own hypotheses rather than a flag on this one.

## Consequences

This is the load-bearing decision of Phase 0. Four things follow.

**1. Placed tiles are inert.** A tile's arrows matter on the ply it is placed
and never again, so from the next ply on it is indistinguishable from a bare
coloured token. This is what licenses the state representation in
[adr-003](adr-003-piece-representation.md) and its 19.5-order-of-magnitude
reduction in the state-space bound. Without this ADR, adr-003 is invalid.

**2. Moves are cheap and bounded.** Applying a move is O(6): at most six
neighbour lookups. There is no cascade to simulate, no fixed-point to reach, no
risk of a pathological position where one placement rewrites the board. For a
solver evaluating ~10⁹ nodes, a constant-time move application is the
difference between feasible and not.

**3. The game is not Reversi.** Reversi's captures are long-range and
bracketing-based, producing its characteristic instability where a single move
overturns a whole diagonal. FLIPHEX's flips are strictly local — radius 1,
depth 1. The expected consequences, all testable:

- Positional swings are bounded by 6 per ply, so evaluation is smoother and
  material count is a more reliable heuristic than in Reversi.
- "Mobility" in the Reversi sense is a much weaker concept here, because every
  empty cell is always playable by every tile.
- Move ordering should therefore lean on **flip count** and **cell degree**
  rather than on Reversi-style stability heuristics
  ([adr-004](adr-004-solver-approach.md), `exercises/ex03_alpha_beta.md` Q3).

**4. Tempo matters more than position.** With no chains, the last player to
touch a region owns it. This raises the strategic value of the joker (Player
1's only zero-arrow, tempo-only move) and suggests high-arrow tiles are worth
*saving* rather than spending early — a hypothesis Phase 6's archetype analysis
(H5) can test directly.

**Negative / accepted costs**

- The game is arguably less dramatic than a chaining variant would be. Not our
  call: it is the designers'. Worth one paragraph in the writeup as a design
  observation, since "why the designers ruled out chains" is exactly the kind
  of question the original professor would enjoy.
- Every architectural decision downstream is coupled to this one. If OPEN
  questions ever reopen it, adr-003 and adr-004 must be revisited together.
  Recorded here so that coupling is not discovered by surprise.

## Alternatives considered

**Chain reactions with a visited-set (each tile fires at most once per ply).**
Terminates, but makes move application O(25) with data-dependent cost, destroys
tile inertness, and reinstates orientation in the state — pushing the state
space back to ~10³⁷. Rejected: contradicts the source, and would make the
project's exact-solving axis infeasible.

**Chains capped at depth 2.** A middle ground with no support in the source
material. Rejected as invented design.

**Make it a configurable rule flag.** Superficially attractive, but the state
representation differs between the two games, so the flag would have to reach
into `state.py`, `moves.py`, the Zobrist scheme, and the network encoding. A
flag that changes the state class is not a flag. Rejected — a separate game
gets a separate class.

## Related

- [rules-canonical.md](../rules-canonical.md) §4 — the flip rule
- [adr-003](adr-003-piece-representation.md) — the representation this enables
- [adr-004](adr-004-solver-approach.md) — move ordering consequences
