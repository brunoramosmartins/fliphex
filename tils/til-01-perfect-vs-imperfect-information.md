# TIL #1 — Perfect vs imperfect information: what changes when you can see everything

> **Draft.** Written at the close of Phase 2. Voice and examples still to be
> tightened before publishing.

Hiding information from a player does not make a game imperfect-information. I
learned this by proposing a variant of my own game that turned out not to be a
variant at all.

## The setup

FLIPHEX is a two-player game I designed as a student: 25 hexagonal cells, tiles
carrying arrows that flip adjacent pieces when placed. It is
**perfect-information** — the rulebook is explicit that both hands, every placed
tile, its orientation and the joker's colour are public at all times.

That felt like a limitation. Most of my previous work was on a Pokémon TCG agent,
where the whole difficulty is not knowing what the opponent holds. So the obvious
enrichment came up: what if the hands were hidden? Same board, same arrows, but
you cannot see what your opponent still has to play. That sounds like it should
turn a solved-in-principle game into something much richer.

It doesn't, and working out why is the actual lesson.

## Why the hidden-hand variant is not imperfect information

Imperfect information is not about what a player *sees*. It is about what a
player can **distinguish**. The formal object is the **information set**: the
collection of game states a player cannot tell apart when it is their turn to
move. A game is imperfect-information when some information set contains more
than one state, because then a strategy cannot be a function of the state — there
is no single state to be a function of.

Now apply that to hidden-hand FLIPHEX:

- Both decks are **fixed and published**. Each player starts with one tile of
  each of the 12 arrow patterns; Player 1 additionally holds the joker.
- Every placement is **public**. A tile that hits the board is visible forever,
  and its identity is unambiguous.

So at any point I can compute the opponent's hand exactly: it is the published
deck minus everything they have already played. The information set has **one
element**. My belief about their hand is a point mass, not a distribution.

Hiding the hand hides nothing. It just makes me do subtraction.

That is the test I now apply, and it generalises well beyond this game:

> **Concealment only creates imperfect information when the concealed thing is
> not derivable from public history.**

Poker qualifies — the shuffle is a genuine random variable and no amount of
public history pins down the hole cards. Pokémon TCG qualifies, for the same
reason: deck order is randomised, so the top card is a real distribution. FLIPHEX
with hidden hands does not qualify. It is a memory exercise wearing a game-theory
costume.

## What perfect information actually buys you

Once I stopped trying to escape it, the property turned out to be doing a lot of
load-bearing work in my design decisions:

| | perfect information | imperfect information |
|---|---|---|
| **A strategy is** | a function of the state | a function of the information set |
| **Solution concept** | pure-strategy equilibrium by backward induction (Zermelo/Kuhn) | generally requires *mixed* strategies; the target is an ε-Nash |
| **A leaf's value** | `v(s)`, a function of the state alone | must be defined over a belief, not a state |
| **Search operates on** | states — minimax, alpha-beta | information sets — CFR, ISMCTS |
| **Transposition table** | sound: the state is a sufficient statistic | the key you can observe is not the state you are in |
| **"The value of the game"** | a single number | a strategy profile, not a number |

The row that surprised me most is the third one, because it is what licenses
AlphaZero's most famous simplification. AlphaZero drops random rollouts and
trusts a learned value network at the leaf. That is only defensible because in a
perfect-information game the leaf's value *is* a function of the state — there is
no hidden variable left to average over. Take the same trick to an
imperfect-information game and you get **strategy fusion**: the search quietly
assumes it will be allowed to play a different move in each possible world, which
is exactly the thing the opponent's uncertainty was supposed to prevent.

So "perfect information" is not a limitation to be designed around. It is the
precondition for an entire family of methods — exact solving, transposition
tables, learned state values — that simply do not transfer.

## The takeaway

I went looking for a way to make my game harder and found a sharper question
instead: *is the hidden thing derivable?* If yes, you have added bookkeeping. If
no, you have changed the mathematics of the game, and most of your algorithmic
toolbox no longer applies.

Worth checking before designing the variant, not after.

---

**Related:** [`docs/adr/adr-001-perfect-information-scope.md`](../docs/adr/adr-001-perfect-information-scope.md) ·
[`docs/rules-canonical.md`](../docs/rules-canonical.md) §2 ·
[`notes/russell-norvig-aima-ch6-adversarial-search.md`](../notes/russell-norvig-aima-ch6-adversarial-search.md) §6.5.1
