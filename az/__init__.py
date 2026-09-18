"""Axis 2 — the AlphaZero-style learner.

Imports ``fliphex`` and nothing else from the project (docs/engineering.md).
In particular it never imports ``solver``: the two axes are compared against
each other, and adr-004/adr-005 forbid either from selecting or terminating the
other along the dimension on which they are later compared. Experiment scripts
may read both; this package may not.
"""
