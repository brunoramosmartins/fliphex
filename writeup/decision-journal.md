# Decision Journal

Chronological record of decisions that were not obvious, and what they cost.
Distinct from the ADRs: ADRs record *what* was decided and are stable; this
journal records *why it was live at the time*, including things that turned out
to be wrong. Freely editable, append-only.

Raw material for `writeup/main-writeup.md`.

---

## 2026-07-25 — Phase 1 closing: scope calls

Engine, both baseline agents, and the full test suite are done, and the flip
rule was validated by hand-play (see the toggle entry below). Two closing
decisions:

- **CI landed now** (`.github/workflows/ci.yml`): ruff, pytest, and a
  generated-docs-clean check. Worth having before the Phase 2 study work so the
  branch stays honest.
- **The `01_rules_and_geometry` notebook (#12) is deferred to Phase 7.** The
  hotseat CLI already gives interactive visual inspection of geometry and the
  flip rule, so the notebook's value now is presentational, not correctness. It
  travels with the UI/portfolio work.
- The "1000 random games" exit criterion is covered by
  `scripts/smoke_selfplay.py` (run once: 1000 games, all invariants held, ~11s)
  rather than a slow pytest case, keeping the suite fast.

---

## 2026-07-25 — Play-testing caught a wrong core rule: flip is a toggle

Building the hotseat CLI before training any agent paid off on day one. Playing
a two-human game, the co-designer noticed the 6-arrow tile placed among his own
pieces changed nothing, and questioned whether an arrow should flip a same-colour
tile.

Investigation confirmed the engine did exactly what Phase 0's `rules-canonical.md`
§4 told it to: a flip was an **assignment** to the placing player's colour, so
aiming at your own tile was a no-op. That was my error. The tiles are two-sided;
the poster says the pointed tile is *"virada (flipada)"* — **turned over** —
which inverts its colour unconditionally. An arrow at your own tile therefore
hands it to the opponent.

Fixed as a **toggle** (adr-007): one line in `apply_move`, plus the rulebook,
`engineering.md`, the greedy heuristic (now maximises net swing = opponent flips
minus self-flips, or it would damage itself), and the flip tests. Nothing
structural moved — toggle only changes colours, so adr-003's representation and
the state-space bound are untouched.

The lesson is the whole reason the CLI came before the solver and the network: a
subtly wrong core rule would have been learned faithfully by every agent and
silently poisoned every hypothesis verdict. "Play the game by hand first" earned
its place in the plan.

---

## 2026-07-25 — Phase 1 opened

Phase 0 shipped (tag `v0.1-foundation`, clean linear history). Gate check for
Phase 1 passed with no carry-overs — all 16 Phase 0 deliverables present.

Scope decision: keep the roadmap, `.claude/` config, and `FLIPHEX.pdf` local
only (gitignored, purged from remote history via force-push). The remote is the
public artifact; the project direction and tooling are not part of it.

No open technique decision enters Phase 1 — the six ADRs already fix the engine
design — so no `literature-scout` dispatch here. Literature grounding (and any
ADR rebuttal) is deferred to Phase 2, as recorded in the roadmap's Phase 1
`lit-note` note.

---

## 2026-07-23 — Phase 0

### The physical artifact outranks the written rules

The 2017 poster carries both photographs and a prose rulebook, and the author
flagged the prose as out of date. Set an explicit precedence order in
`rules-canonical.md`: photographs > author's decisions > poster prose. Every
divergence is tabulated in §9 of the rulebook rather than silently resolved.

This mattered immediately — the roadmap described a "5-row zigzag", but the
photographs show flat-top hexagons in five *columns*. Same 25 cells, transposed,
different direction indexing. Reading the rules text alone would have produced
a subtly wrong engine.

### The deck turned out to be a theorem

The roadmap deferred "3 distinct archetypes — TBD" for the 2-, 3-, and 4-arrow
pieces, and the plan was to pick them by inspecting the physical tiles.

Counting first was better. Arrow patterns on a *two-sided* hexagonal tile are
equivalence classes under rotation **and** reflection — binary bracelets of
length 6 — and there are exactly 1, 3, 3, 3, 1, 1 of them with 1 to 6 arrows.
That is the poster's deck composition, term for term. The deck is not a
selection; it is the complete enumeration. Nothing was left to choose.

The reflection step is what makes it work, and it is physically motivated: the
tiles are purple on one face and green on the other, so turning one over both
changes its colour and mirrors its arrows. Under rotation alone there would be
13 classes and the design would need an arbitrary omission.

Left one thing open (`OPEN-2`): if both decks are the *same* physical object,
the two players hold mirror-image versions of the single chiral tile, and the
seats are not equivalent. That is a confound for H1 and has to be settled with
a photograph before hypotheses lock.

### Noticing that placed tiles are inert

The largest decision of the phase, and it came from reading the poster's
*CUIDADOS!* section: flips do not chain. Therefore a placed tile's arrows fire
once and never again, so from the next ply onward it is just a coloured token —
its pattern and rotation cannot affect anything.

So the state does not need to store orientation. The reachable state-space bound
drops from ~1.4 × 10³⁷ to ~4.9 × 10¹⁷, about 19.5 orders of magnitude, and
transposition tables go from decorative to essential (with rotation stored,
almost nothing would ever transpose).

This contradicts the roadmap's own Phase 2 exercise, which puts a `6^25` factor
in the state-space bound. Left the exercise in place but reframed: derive the
naive bound, find the inertness argument, derive the corrected one. Better
exercise than the original.

### The roadmap says 8 archetypes; there are 12

The roadmap says "the 8 arrow archetypes" and then enumerates 1+3+3+3+1+1 = 12
in the same sentence. 12 is right — one per piece per player. Corrected in
`piece-archetypes.md` rather than silently.

### The board has no symmetry at all

Expected some symmetry to exploit for transposition-table canonicalisation and
for network data augmentation. There is none: columns A/C/E and B/D sit at
different vertical centres, so the symmetry group is trivial.

Two consequences, both accepted: no free 2–8× augmentation in Axis 2 (unlike Go
or Connect Four), and no strategy-stealing argument available for H1, which now
*must* be settled computationally. The second is arguably good news — it makes
H1 a real question rather than a formality.

### Deferred: chose a factored policy head without evidence

`adr-005` picks a factored (cell × tile × rotation) policy head over a flat
1950-logit one, on parameter-efficiency grounds. The factorisation assumes
conditional independence, which is *false* — the best rotation obviously depends
on the cell. Went with it anyway because MCTS exists to correct a bad prior, and
wrote both fallbacks into the ADR.

Flagging it here because it is the decision in Phase 0 with the least evidence
behind it. It is R5 in the risk register and must be tested in Phase 4, not
assumed.
