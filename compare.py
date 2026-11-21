"""
compare.py - AI vs AI harness: compares heuristics by playing them
against each other at the same depth K.

Each pair plays twice with the sides swapped, so neither heuristic
gets the first-move advantage both times.
"""

import csv
import itertools
import random

from engine import (HUMAN, COMPUTER, new_board, get_valid_moves,
                    drop_piece, is_full, get_scores)

from heuristic import h1, h2, h3

HEURISTICS = {"h1": h1, "h2": h2, "h3": h3}

# Use B's AI when it exists; until then fall back to a random-move stub.
# `heuristic` is a function board -> number; `player` is the piece the
# search plays for (needed because both sides are AIs here).
try:
    from ai import choose_move
except ImportError:
    def choose_move(board, K, use_pruning=True, print_tree=True,
                    heuristic=None, player=COMPUTER):
        """Stub: random valid column, same signature as B's version."""
        col = random.choice(get_valid_moves(board))
        return col, {"nodes": 0, "time": 0.0, "value": 0}


# Placeholders until B's heuristic.py exists. Each maps board -> score.
# Replace with: from heuristic import h1, h2, h3
def _placeholder(board):
    return 0


HEURISTICS = {
    "h1": _placeholder,
    "h2": _placeholder,
    "h3": _placeholder,
}

def play_match(K, name_first, name_second, seed=0):
    """
    Play one full game. `name_first` moves first (as HUMAN's piece),
    `name_second` moves second (as COMPUTER's piece).
    Returns a dict with both names and the final four-counts.
    """
    random.seed(seed)
    pieces = {name_first: HUMAN, name_second: COMPUTER}
    heuristics = {HUMAN: HEURISTICS[name_first],
                  COMPUTER: HEURISTICS[name_second]}

    board = new_board()
    player = HUMAN                      # piece to move; HUMAN goes first
    while not is_full(board):
        col, _ = choose_move(board, K, print_tree=False,
                             heuristic=heuristics[player], player=player)
        board, _ = drop_piece(board, col, player)
        player = COMPUTER if player == HUMAN else HUMAN

    first_fours, second_fours = get_scores(board)
    return {
        "K": K,
        "first": name_first,
        "second": name_second,
        "first_fours": first_fours,
        "second_fours": second_fours,
    }

def run_comparison(K=3, seed=0):
    """
    Every pair of heuristics plays twice (sides swapped) at depth K.
    Returns a list of result dicts, one per game.
    """
    rows = []
    for a, b in itertools.combinations(HEURISTICS, 2):
        rows.append(play_match(K, a, b, seed))      # a moves first
        rows.append(play_match(K, b, a, seed))      # b moves first
    return rows


def save_csv(rows, path="results/comparison.csv"):
    """Write one row per game."""
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows):
    """
    Per heuristic: games won, tied, lost, and total fours scored/conceded.
    Returns a dict name -> stats dict.
    """
    stats = {n: {"won": 0, "tied": 0, "lost": 0, "for": 0, "against": 0}
             for n in HEURISTICS}
    for r in rows:
        f, s = r["first"], r["second"]
        ff, sf = r["first_fours"], r["second_fours"]
        stats[f]["for"] += ff
        stats[f]["against"] += sf
        stats[s]["for"] += sf
        stats[s]["against"] += ff
        if ff > sf:
            stats[f]["won"] += 1
            stats[s]["lost"] += 1
        elif sf > ff:
            stats[s]["won"] += 1
            stats[f]["lost"] += 1
        else:
            stats[f]["tied"] += 1
            stats[s]["tied"] += 1
    return stats


def print_summary(stats):
    """Print the comparison table, best heuristic first."""
    print(f"{'heuristic':<10}{'won':>5}{'tied':>6}{'lost':>6}"
          f"{'fours for':>11}{'against':>9}")
    ranked = sorted(stats.items(),
                    key=lambda kv: (kv[1]["won"], kv[1]["for"] - kv[1]["against"]),
                    reverse=True)
    for name, s in ranked:
        print(f"{name:<10}{s['won']:>5}{s['tied']:>6}{s['lost']:>6}"
              f"{s['for']:>11}{s['against']:>9}")


if __name__ == "__main__":
    import os
    import sys
    K = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    os.makedirs("results", exist_ok=True)
    rows = run_comparison(K)
    save_csv(rows)
    print_summary(summarize(rows))