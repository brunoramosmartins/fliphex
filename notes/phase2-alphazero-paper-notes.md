# Phase 2 — AlphaZero paper notes (study notes)

**Objective.** Understand the AlphaGo Zero / AlphaZero self-play pipeline well
enough to implement it from first principles in Axis 2 (Phase 4): PUCT MCTS with
network priors, the self-play → train → evaluate loop, the policy/value loss, and
the temperature schedule. This note backs adr-005 (AZ scope + network) and feeds
`exercises/ex04_alphazero_math.md` and TIL #5.

**Dates.** None — sequenced by dependency. Opened 2026-07-25.

**Sources (each gets a `lit-note` companion, written before reading):**
Silver et al. 2017 (*Mastering the game of Go without human knowledge*, Nature)
and Silver et al. 2018 (*A general reinforcement learning algorithm…*, Science).
The classical-search background lives in
[phase2-game-theory-fundamentals.md](phase2-game-theory-fundamentals.md).

**ADR posture.** adr-005 fixed a small factored (cell × tile × rotation) policy
head and a compact network from first principles, flagged as the least-evidenced
Phase 0 decision (R5). This is the phase to confront it with the papers. A
contradiction triggers an adr-005 amendment, not a silent change.

## PUCT selection in MCTS

Pre-reading prompt: write the PUCT formula and identify exploitation vs prior vs
exploration terms. How does it differ from UCB1, and why does a *perfect-
information* game need no determinization (unlike PTCG's IS-MCTS)?

## Self-play as a policy-improvement operator

Pre-reading prompt: why is the MCTS visit-count policy π a strictly stronger
training target than the network's own policy p? This is the crux of the whole
method — state the improvement-operator argument precisely.

## Network architecture and the state encoding

Pre-reading prompt: for FLIPHEX, what channels does the input tensor need
(own / opponent / empty / joker, hand bitmasks) — and crucially, does adr-003's
inertness mean we do *not* encode per-tile rotation? Reconcile with adr-005.

## The loss, training loop, and replay buffer

Pre-reading prompt: derive L = (z−v)² − πᵀlog p + c‖θ‖². What buffer capacity and
refresh fraction make sense at ~25 positions/game on a laptop GPU?

## Temperature schedule and exploration

Pre-reading prompt: why τ=1 early and τ→0 late? How does this interact with the
absence of board symmetry in FLIPHEX (no data augmentation available)?

## Exercise ex04 + TIL #5

Pre-reading prompt: draft the ex04 derivations and the "AlphaZero in 500 lines"
TIL skeleton here before transcribing.

## Lessons Learned

_(first-person, written by the author at phase close — not ghost-written)_

## Failed Attempts

_(first-person, written by the author at phase close — not ghost-written)_
