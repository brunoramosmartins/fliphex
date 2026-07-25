# Glossary

Freely editable. Terms are added as they first appear in the work.

## The game

| Term | Meaning |
|---|---|
| **Archetype** | One of the 12 distinct arrow patterns, i.e. an equivalence class of 6-bit patterns under rotation and reflection. See [piece-archetypes.md](piece-archetypes.md). |
| **Arrow slot** | One of a tile's six edge positions, indexed clockwise from North (`N=0 … NW=5`). |
| **Bracelet** | Combinatorics: a binary necklace considered up to reflection as well as rotation. One bracelet = one physical two-sided tile. |
| **Cell** | One of the 25 board sockets, named `A1`–`E5`. |
| **Chiral** | A pattern not equal to its own mirror image. `P3-y` is FLIPHEX's only chiral tile. |
| **Deck** | A player's 12 tiles. Purple's are holed, Green's are not. |
| **Flip** | Setting an occupied cell's colour to the mover's colour. Unconditional, never chained. |
| **Inert** | Property of a placed tile: its arrows have already fired and can never fire again. |
| **Joker** (*coringa*) | The 25th tile. No arrows, starts as Player 1's colour, gives Player 1 the 13th ply. |
| **Necklace** | Combinatorics: a binary pattern up to rotation only. One necklace = one *face* of a tile. |
| **Ply** | A single move by one player. A FLIPHEX game is exactly 25 plies. |
| **Rotation** | `k ∈ {0..5}`, turning a tile `k × 60°` clockwise. Slot `i` becomes direction `(i+k) mod 6`. |

## Search and learning

| Term | Meaning |
|---|---|
| **Alpha-beta** | Minimax with pruning of branches that cannot affect the root value. |
| **Killer move** | A move that caused a cutoff at the same depth elsewhere; tried early in move ordering. |
| **PUCT** | AlphaZero's selection rule: `Q(s,a) + c·P(s,a)·√ΣN(s,b)/(1+N(s,a))`. |
| **Retrograde analysis** | Computing exact values backwards from terminal positions to build an endgame database. |
| **Transposition table** | Cache mapping a position hash to its computed value, so positions reached by different move orders are searched once. |
| **Weakly solved** | The game-theoretic value from the initial position is known, with a strategy to achieve it. |
| **Zobrist hashing** | Position hash as an XOR of random words, updatable in O(1) per change. |

## Statistics

| Term | Meaning |
|---|---|
| **Bonferroni correction** | Dividing the significance level by the number of hypotheses tested. |
| **McNemar's test** | Paired test for two agents on the same set of positions. |
| **Wilson interval** | Confidence interval for a proportion; well behaved near 0 and 1, unlike the normal approximation. |
