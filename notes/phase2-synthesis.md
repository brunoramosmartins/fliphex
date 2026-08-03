# Phase 2 — cross-source synthesis

Questions that only make sense *across* the phase's sources. Each source's
companion note forward-refs here with 🔄. Answer these after you have read the
relevant pair, in first person, then I refine.

Sources: R&N Ch.5 (adversarial search), Silver 2017 (AlphaGo Zero),
Silver 2018 (AlphaZero), Allis 1994 (complexity), Schaeffer 2007 (retrograde).

## S1 — MCTS: classical vs AlphaZero (R&N ↔ Silver 2017) 🔄
**Prompt.** R&N Ch.5 presents MCTS with *random rollouts* for the default
policy; AlphaGo Zero replaces rollouts with a learned value head and adds a
network prior in selection. Line up the two selection rules (UCB1 vs PUCT) term
by term. Why does perfect information make the learned value trustworthy enough
to drop rollouts — and why would your PTCG (imperfect information) not permit the
same move?

**My take.**

**Refined write-up.**

## S2 — The evaluator gate: kept then dropped (Silver 2017 ↔ 2018) 🔄
**Prompt.** AlphaGo Zero promotes a new network only if it beats the best in
≥55% of games; AlphaZero removes this gate and trains a single continuously
updated network. What changed to make the gate unnecessary, and which regime
(gated / continuous) is safer for a *single-laptop* FLIPHEX run where compute is
scarce and instability is costly?

**My take.**

**Refined write-up.**

## S3 — Symmetry: a tool AGZ has and FLIPHEX lacks (Silver 2017 ↔ board-geometry) 🔄
**Prompt.** AGZ uses Go's 8-fold dihedral symmetry for data augmentation and
evaluation averaging. FLIPHEX's board symmetry group is trivial. Quantify what
this costs us: if AGZ effectively gets 8× the labelled data per game, what does
that imply for the number of self-play games FLIPHEX needs to reach comparable
coverage? Does this strengthen the case for the exact solver (Axis 1) as the
cheaper source of ground truth on small variants?

**My take.**

**Refined write-up.**

## S4 — Two routes to a game's value (Silver ↔ Schaeffer ↔ Allis) 🔄
**Prompt.** Schaeffer *solves* checkers exactly (retrograde + search); AlphaZero
*approximates* the optimal policy by learning. Allis frames when each is feasible
via state-space and game-tree complexity. Place FLIPHEX on that map: for which
variants does Axis 1 give exact truth, and where must Axis 2's learned agent take
over? This is the intellectual spine of H1/H3 — the two axes cross-checking each
other.

**My take.**

**Refined write-up.**
