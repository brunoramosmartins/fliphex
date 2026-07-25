# ADR-007 — A flip toggles the tile's colour (turn-over), not an assignment

**Status:** Accepted (Phase 1)
**Date:** 2026-07-25
**Deciders:** Bruno Ramos Martins (co-designer)
**Supersedes:** the flip semantics originally written in
[rules-canonical.md](../rules-canonical.md) §4 during Phase 0.

## Context

The flip rule is the whole game. Phase 0's `rules-canonical.md` §4 described a
flip as an **assignment**: an arrow sets the pointed neighbour to the placing
player's colour, so pointing at one of your own tiles was a no-op. The engine
was built that way and its tests passed.

Play-testing the hotseat CLI (the reason the CLI was built before any agent
training) exposed the error. Placing the 6-arrow tile among the player's own
pieces changed nothing, which contradicts the physical game.

The tiles are **two-sided** — purple on one face, green on the other. On the
2017 poster the rule reads: *"a peça apontada deve ser virada (flipada)
independente de qual deck ela pertença"* — the pointed tile must be **turned
over**, regardless of which deck it belongs to. Turning a two-sided tile over
inverts its colour unconditionally. The "regardless of which deck" clause only
carries meaning if turning over your own tile has an effect; under an assignment
rule it would be a no-op and the clause would be pointless.

## Decision

**A flip is a toggle.** When an arrow of the just-placed tile points at an
occupied neighbour, that neighbour's colour is inverted (purple ⇄ green),
independent of who placed the arrow. Empty cells and off-board directions are
unaffected, and flips still never chain (adr-006).

Concretely, the one line that changed in `apply_move`:

```python
# before (assignment): win the neighbour
new = new.with_colour(target, mover)
# after (toggle): turn the neighbour over
new = new.with_colour(target, other(new.colours[target]))
```

The two rules differ **only when the arrow hits a tile already the mover's
colour**: assignment left it unchanged; toggle hands it to the opponent.

## Consequences

**Positive**

- The engine now matches the physical game, confirmed by its co-designer. Every
  downstream result (solver, self-play, complexity) will study the real game.
- The strategic space is richer and matches the poster's own hint that placing
  where **nothing** flips can be the right move: arrows are double-edged, so a
  player must avoid aiming them at their own pieces.

**Negative / knock-on changes**

- **The greedy baseline had to change.** `HeuristicAgent` maximised the count of
  opponent tiles flipped; under toggle it must maximise the *net* swing
  (opponent tiles flipped minus own tiles flipped), or it would cheerfully
  damage itself. Updated accordingly.
- The Phase 0 rulebook and `engineering.md` prose were corrected, and the flip
  tests were extended with a self-flip case.

**Neutral — nothing structural moved**

- Toggle changes only cell colours, so it does **not** disturb
  [adr-003](adr-003-piece-representation.md): the search state is still a colour
  per cell plus hand masks, with no placed-tile identity or rotation. Zobrist,
  transposition, and the state-space bound are untouched.
- Draws remain impossible (25 cells, odd).

## Alternatives considered

**Keep the assignment rule.** Rejected: it contradicts the physical two-sided
tiles and the poster text, and the co-designer confirmed toggle is intended.
Its only merit was that it was already written and tested — not a reason to keep
a wrong rule.

**Toggle only opponent tiles (win them), leave own untouched.** This is exactly
the assignment rule by another name; same rejection. The whole point of the
correction is that own tiles *can* be turned against you.

## Lesson

This is the error the "play the game before training anything" step existed to
catch. A subtly wrong core rule would have been faithfully learned by every
agent and silently corrupted every hypothesis verdict. Recorded in the decision
journal as the motivating example for validating the engine by hand.

## Related

- [rules-canonical.md](../rules-canonical.md) §4 — the corrected flip rule
- [adr-006](adr-006-no-chain-reaction.md) — flips still never chain
- [adr-003](adr-003-piece-representation.md) — representation is unaffected
