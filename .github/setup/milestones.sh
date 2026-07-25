#!/usr/bin/env bash
# Create one milestone per phase. No due dates: the roadmap is sequenced by
# dependency, not calendar.
set -euo pipefail

REPO="${1:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"

milestone() {
  gh api "repos/${REPO}/milestones" -X POST -f title="$1" -f description="$2" \
    >/dev/null 2>&1 && echo "created: $1" || echo "exists:  $1"
}

milestone "Phase 0 — Foundation" \
  "Canonical rules, board geometry, piece archetypes, six ADRs, repo scaffold. Tag v0.1-foundation."
milestone "Phase 1 — Game Engine" \
  "fliphex/ package, random and heuristic agents, full test suite. Tag v0.2-engine."
milestone "Phase 2 — Game Theory & Hypothesis Pre-Registration" \
  "Study notes, exercises, hypotheses H1-H5 locked. Tag v0.3-hypotheses."
milestone "Phase 3 — Axis 1: Exact Solver" \
  "Alpha-beta with TT, 3x3 solved exactly, retrograde endgames. Tags v0.4/v0.5."
milestone "Phase 4 — Axis 2: AlphaZero-Style Self-Play" \
  "Network, PUCT MCTS, self-play, training loop. Tags v0.6/v0.7."
milestone "Phase 5 — Hypothesis Testing" \
  "H1, H2, H3 verdicts with cross-axis verification."
milestone "Phase 6 — Axis 3: Complexity" \
  "State-space and game-tree bounds, cross-game comparison. H4, H5 verdicts. Tag v0.8."
milestone "Phase 7 — Interface, Writeup, Release" \
  "CLI and pygame UI, portfolio article, TIL series. Tags v0.9 and v1.0.0."
milestone "Paper Fork Decision" \
  "Closes with either 'not pursued' or a link to the paper repository."
