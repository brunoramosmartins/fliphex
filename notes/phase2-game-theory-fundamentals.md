# Phase 2 — Game Theory Foundations (study notes)

**Objective.** Acquire the vocabulary to reason rigorously about
perfect-information, deterministic, zero-sum games: minimax and its proof,
alpha-beta and its optimality, transposition tables + Zobrist hashing,
retrograde analysis, and state-space / game-tree complexity. This note backs
the Axis 1 (solver) and Axis 3 (complexity) design decisions and feeds
`exercises/ex02_game_theory.md`.

**Dates.** None — sequenced by dependency. Opened 2026-07-25.

**Sources (each gets a `lit-note` companion, written before reading):**
Russell & Norvig 4e Ch.5 (adversarial search); Allis 1994 (game-tree
complexity); Schaeffer et al. 2007 (Checkers is solved — retrograde). The
AlphaZero papers live in the companion note
[phase2-alphazero-paper-notes.md](phase2-alphazero-paper-notes.md).

**ADR posture.** The six Phase 0 ADRs were written from first principles before
the literature pass (a conscious exception, see the roadmap's Phase 1 note). Any
source here that contradicts an ADR triggers an **ADR amendment**, not a silent
edit — `rules-canonical`, `board-geometry`, and `piece-archetypes` remain the
protected documents. Watch especially adr-004 (solver approach) and adr-005
(AZ scope) against R&N Ch.5 and the AZ papers.

## Minimax on finite zero-sum perfect-information games

Pre-reading prompt: what exactly does the minimax theorem guarantee, and why do
perfect information + determinism + finiteness make FLIPHEX a clean instance?
Where does the "zero-sum" assumption enter our engine (`rules.outcome`)?

## Alpha-beta pruning and its optimality

Pre-reading prompt: why does alpha-beta return the *same* root value as plain
minimax, and where does the O(b^{d/2}) best-case come from? What is the concrete
move-ordering signal for FLIPHEX (flip count, centre, low-arrow-first)?

## Transposition tables and Zobrist hashing

Pre-reading prompt: our `GameState.key()` already carries an incremental Zobrist
hash (adr-003). What makes Zobrist O(1)-updatable per move, and what has to be in
the key for FLIPHEX given placed tiles are inert (colour + hands + turn, never
rotation)? What are the collision and replacement-policy pitfalls?

## Retrograde analysis (endgame databases)

Pre-reading prompt: Schaeffer's checkers result works backward from terminal
positions. For FLIPHEX, what makes a position enumerable backward given the flip
rule is not reversible? What "k pieces remaining" horizon is realistic on 5×5?

## State-space and game-tree complexity

Pre-reading prompt: Allis distinguishes state-space from game-tree complexity.
Write the naive FLIPHEX upper bound and the inertness-corrected one (adr-003
drops the 6^25 rotation factor). Where do Reversi 6×6/8×8 and Hex sit, for H4?

## Exercise ex02 — game-theory problem set

Pre-reading prompt: the six problems in `exercises/ex02_game_theory.md`
(minimax theorem, alpha-beta derivation, O(b^{d/2}), TT/Zobrist, PUCT, FLIPHEX
state-space estimate). Draft answers here first, then transcribe.

## Hypothesis lock (H1–H5)

Pre-reading prompt: refine each placeholder in `docs/research.md` into a
falsifiable statement with a named test and decision rule. **Blocker: OPEN-2
(chiral tile mirroring) must be resolved on the physical board before locking —
it confounds H1.** Record the pre-registration rationale here; the lock itself
is the tagged commit `v0.3-hypotheses`.

## Lessons Learned

_(first-person, written by the author at phase close — not ghost-written)_

## Failed Attempts

_(first-person, written by the author at phase close — not ghost-written)_
