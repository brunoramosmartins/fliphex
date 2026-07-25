# Decision Journal

Chronological record of decisions that were not obvious, and what they cost.
Distinct from the ADRs: ADRs record *what* was decided and are stable; this
journal records *why it was live at the time*, including things that turned out
to be wrong. Freely editable, append-only.

Raw material for `writeup/main-writeup.md`.

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
