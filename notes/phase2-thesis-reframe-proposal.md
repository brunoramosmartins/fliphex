# Phase 2 — proposal: reframe the thesis around computational game-design analysis

**Status:** proposal, for discussion before the hypotheses lock (`v0.3-hypotheses`).
Freely editable. Changing `docs/research.md`'s thesis is ADR-gated, so this note
is the draft that feeds that decision — nothing here is locked yet.

**Origin.** Emerged from reading Silver 2018 (AlphaZero) and reflecting that the
project's centre of gravity could shift from *"apply AlphaZero to an original
game"* to *"use self-play (and the exact solver) as a computational tool to
analyse and validate an original game's design."* See
[notes/silver-2018-alphazero.md](silver-2018-alphazero.md) §2.1/§4.2 and the
author's reading TODOs.

## The shift, in one line

- **Current framing:** build a solver + an AlphaZero agent + complexity metrics
  *for* FLIPHEX; strong play is the deliverable.
- **Proposed framing:** treat self-play and the solver as a **methodology for
  understanding an original game** — its balance, first-player advantage, board
  geometry, tile distribution, and strategic depth. Strong play becomes the
  *means*; the *understanding of the design* is the deliverable.

## Why it is stronger (and honest about why)

- **Novelty / portfolio.** "I implemented AlphaZero on a board game" is a
  well-trodden exercise. "I used self-play + exact search to characterise the
  design of an original, IP-owned game that had never been analysed" is rarer and
  more defensible as a research contribution.
- **It is not a pivot.** H1 (first-player advantage), H2 (joker balance), and H5
  (archetype balance) are *already* game-analysis questions. The reframe just
  promotes them from side-questions to the **spine** and states the unifying
  thesis explicitly.
- **It fits the two-axis design.** The solver gives exact truth on small variants;
  self-play gives strong policy on the full game; complexity situates FLIPHEX
  among known games. All three already point at "understand the game," not
  "beat a benchmark."

## Guardrails (so this elevates instead of ballooning)

1. **Analyse / validate, not redesign.** The physical FLIPHEX is a USP artifact
   on display and the author's IP. The compelling story is *validating* the
   design, not changing it. Frame variants (alt tile distributions, alt
   geometries, rule tweaks) as a **stretch** that tests robustness of the
   findings — never the spine.
2. **Existing design first.** Fully characterise the shipped 5×5 game before any
   variant. A variant matrix multiplies experiments and directly threatens the
   registered compute-budget risk.
3. **Keep a fixed benchmark.** Agent-strength evaluation (Elo vs baselines) stays
   — you still need a stable target to measure learning against. The reframe
   *adds* design-analysis outputs; it does not remove strength measurement.
4. **Respect the ADR gate.** This changes `docs/research.md`'s thesis, so it is
   decided at the hypotheses lock, deliberately, not edited in silently.

## Concrete changes to the hypotheses (proposed)

| ID | Change | Rationale |
|---|---|---|
| **H1** first-player advantage | **Keep, promote to spine.** | Already the core design question; now explicitly central. Note: adr-008's mirror does **not** help here (it preserves the mover), so H1 stays a computational question. |
| **H2** joker balance | **Keep, promote to spine.** | A design-balance question by nature. |
| **H3** AZ convergence + solver agreement | **Keep scope, make rigour explicit.** Add: ≥5 seeds, Wilson/bootstrap CIs, variance across runs. | This rigour is already *latent* in H3's wording; make it a stated requirement. Do **not** overload H3 with game-property analysis — that is H1/H2/H5's job. |
| **H4** complexity vs known games | **Keep.** | Situates the game; unchanged. |
| **H5** archetype distribution well-designed | **Keep, promote to spine.** | The clearest "is the design good?" hypothesis. |
| **H6 (new, optional / stretch)** | *"The board's mirror symmetry (adr-008), conditional on OPEN-2, yields a measurable self-play sample-efficiency gain (≈2× augmentation)."* | Turns the adr-008 finding into a testable claim. Mark optional so it does not gate the lock. |

## Blocking dependency (unchanged, now doubled)

**OPEN-2 must resolve before the lock.** It was already required (chiral seat
asymmetry confounds H1). Per [adr-008](../docs/adr/adr-008-board-mirror-symmetry.md)
it now *also* decides whether the game inherits the board's mirror (and hence H6
and the augmentation/canonicalisation payoffs). One physical check settles both.

## If accepted

- Rewrite the thesis paragraph and Research Question in `docs/research.md` around
  computational game-design analysis.
- Lock H1–H5 (+ optional H6) with the rigour notes above at `v0.3-hypotheses`.
- Record the thesis change via ADR (research.md is protected).
