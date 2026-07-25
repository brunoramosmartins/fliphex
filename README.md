# FLIPHEX

**Computational analysis and self-play learning of an original hexagonal board
game.**

FLIPHEX is a 2-player, perfect-information, deterministic board game designed in
2017 by students of IME-USP and FAU-USP in the course *MAP 2001 — Matemática,
Arquitetura e Design*. It exists as a laser-cut wooden board with 25 hexagonal
tiles. This repository is its digital counterpart: a formalised rule engine and
three complementary technical analyses of the game's strategic structure.

The game is original, and the author is one of its designers.

## The game in one paragraph

25 hexagonal cells, 25 two-sided tiles (purple on one face, green on the other).
Each player holds 12 tiles carrying 1 to 6 outward-pointing arrows; Player 1 also
holds the arrowless joker. On your turn you place one tile on any empty cell at
any rotation, and every arrow pointing at an occupied neighbour flips that
neighbour to your colour. Flips do not chain. All 25 cells fill, and whoever
shows more of their colour wins — 25 is odd, so there are no draws.

Full rules: [`docs/rules-canonical.md`](docs/rules-canonical.md).

## Research question

> Does the first player have a provable advantage, does the joker break game
> balance, and does the game admit an efficient learned policy that approaches
> optimal play?

Answered along three axes that are built to fail differently, so their agreement
is evidence:

| Axis | Method | Produces |
|---|---|---|
| **1 — Exact solver** | Alpha-beta with transposition tables; retrograde endgame databases | Exact game values on reduced variants and endgames |
| **2 — Self-play** | AlphaZero-style policy/value network with PUCT MCTS | A strong learned policy on the full game |
| **3 — Complexity** | State-space and game-tree bounds, branching analysis | Where FLIPHEX sits among known games |

Hypotheses are pre-registered and locked before the experiments run; each gets a
verdict of supported, rejected, or inconclusive. See
[`docs/research.md`](docs/research.md).

## Two things Phase 0 found

**The deck is a theorem.** The poster specifies 1 tile with 1 arrow, 3 with 2,
3 with 3, 3 with 4, 1 with 5, 1 with 6. That shape is not arbitrary: it is
exactly the number of distinct arrow patterns possible on a two-sided hexagonal
tile — binary bracelets of length 6 — so the deck is the *complete enumeration*
of possible pieces. See
[`docs/piece-archetypes.md`](docs/piece-archetypes.md).

**Placed tiles are inert.** Because flips never chain, a tile's arrows fire once
and never again, so the game state does not need to store orientation. This cuts
the reachable state-space bound from ~10³⁷ to ~10¹⁷ and is what makes exact
analysis viable at all. See
[`docs/adr/adr-003-piece-representation.md`](docs/adr/adr-003-piece-representation.md).

## Status

**Phase 0 — Foundation.** Rules canonicalised, geometry and archetypes derived
from the physical artifact, six ADRs written, repository scaffolded. The engine
(Phase 1) is not implemented yet.

Phases are sequenced by dependency, not by calendar.

## Layout

```
docs/          rules, geometry, archetypes, ADRs, research question
fliphex/       the game engine                    (Phase 1)
solver/        Axis 1 — exact analysis            (Phase 3)
az/            Axis 2 — AlphaZero self-play       (Phase 4)
complexity/    Axis 3 — structural analysis       (Phase 6)
agents/        random, heuristic, solver, AZ
stats/         Wilson intervals, bootstrap, paired tests
ui/            CLI, pygame, replay viewer         (Phase 7)
scripts/       experiment entry points and doc generators
experiments/   the experiment registry
writeup/       decision journal and portfolio article
```

## Reproducing the generated documents

`docs/board-geometry.md` and `docs/piece-archetypes.md` are generated, so they
cannot drift from the definitions the engine uses:

```bash
python scripts/build_docs.py
```

The generators are standalone and assert their own correctness — the adjacency
table is checked for symmetry, and the deck is checked to be exactly the 12
bracelet classes.

## Credits

FLIPHEX was designed by students of IME-USP and FAU-USP under Prof. Dr. Artur
Simões Rozestraten (FAU), Profa. Dra. Deborah Raphael (IME), and Prof. Dr.
Eduardo Colli (IME) in MAP 2001, with technical support from LAME.

This analysis is by [Bruno Ramos Martins](https://github.com/brunoramosmartins).

## License

[MIT](LICENSE).
