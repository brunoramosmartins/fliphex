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

This phase changed what I think AlphaZero *is*. I began with "MCTS guided by a
neural network" and ended with a closed learning system — one where search
continuously improves the policy and value functions that will guide the next
search. Search is not only a decision algorithm; it is also the data-generation
mechanism.

Separating the two networks was the next step. Early on I lumped them together as
"neural guidance". They solve different problems: the policy biases exploration
toward promising actions, while the value network replaces rollout-based
evaluation with an estimate of the state's value under increasingly strong play.

Reading AlphaGo Zero and AlphaZero side by side taught an engineering lesson as
much as a technical one: architectural decisions are contextual, not universally
optimal. The evaluator gate and symmetry augmentation are not features to copy —
each has to earn its place against my compute budget, this game's properties, and
what the experiment is trying to establish.

The largest change, though, was methodological rather than algorithmic. I set out
to implement AlphaZero for FLIPHEX; I now see the project as an experimental
framework for understanding the game. The learner, the exact solver and the
design hypotheses answer different questions, and their value depends on staying
complementary rather than competing.

Last, the phase reinforced a research habit: literature should challenge design
decisions, not merely ratify them. Several ADRs predate the papers, and treating
them as hypotheses to confront — rather than assumptions to defend — is what made
the study worth the week.

## Failed Attempts

Several assumptions recorded in Phase 0 turned out to be incomplete or simply
wrong.

I underestimated the distance between classical UCT and AlphaZero's PUCT, filing
the latter as a better exploration strategy. The deeper innovation is coupling
search to learning through visit-count supervision — not swapping one exploration
formula for another.

I also read the value network as a computational optimization over rollouts. Read
more carefully, the substantive change is *what is being estimated*: rollout
values reflect random play, learned evaluations reflect increasingly strong
policies. The compute saving follows from that choice; it is not the motivation
for it.

I treated board symmetry as equivalent to game symmetry. Revisiting FLIPHEX's
state representation showed the chiral `P3-y` tile breaks the mirror for most of
the game, which leaves AlphaGo Zero's augmentation largely inapplicable even
though the board does carry a mirror automorphism.

And I entered the phase believing that reproducing AlphaZero's architecture as
faithfully as possible was the safe strategy. I now think it is a poor default.
Several choices in the papers are engineering decisions taken under DeepMind's
constraints rather than justified principles, and each should be adopted only
where it serves this project's goals.

The biggest failed assumption was that solving FLIPHEX was the point. By the end
of the phase I understood the solver as an instrument for evaluating the game's
design, not as the research outcome.
