#!/usr/bin/env bash
# Create the project's label set. Idempotent: re-running updates colours.
# Requires: gh auth login
set -euo pipefail

label() { gh label create "$1" --color "$2" --description "$3" --force; }

# Phase
label "phase:0" "0E4429" "Foundation — rules, geometry, archetypes, ADRs"
label "phase:1" "006D32" "Game engine"
label "phase:2" "26A641" "Game theory and hypothesis pre-registration"
label "phase:3" "39D353" "Axis 1 — exact solver"
label "phase:4" "56D364" "Axis 2 — AlphaZero self-play"
label "phase:5" "7EE787" "Hypothesis testing and cross-axis verification"
label "phase:6" "A2F2B0" "Axis 3 — complexity analysis"
label "phase:7" "C9F7D4" "Interface, writeup, release"

# Type
label "type:code" "1D76DB" "Implementation"
label "type:theory" "5319E7" "Study, derivation, proof"
label "type:experiment" "B60205" "A registered experimental run"
label "type:writing" "D93F0B" "Writeup, TILs, notes"
label "type:documentation" "0075CA" "Docs, ADRs, rules"

# Axis
label "axis:1" "FBCA04" "Exact solver"
label "axis:2" "FEF2C0" "AlphaZero self-play"
label "axis:3" "F9D0C4" "Complexity analysis"

# Hypothesis
for h in 1 2 3 4 5; do
  label "H${h}" "C5DEF5" "Relates to hypothesis H${h}"
done

# Area
label "area:rules" "E99695" "Rules, geometry, archetypes"
label "area:engine" "BFD4F2" "fliphex/ package"
label "area:infra" "D4C5F9" "CI, tooling, repo scaffolding"

# Status
label "blocked" "000000" "Blocked on an open question or another issue"
label "stretch" "CCCCCC" "Nice to have; not an exit criterion"

echo "labels created"
