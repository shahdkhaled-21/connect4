"""
compare.py - AI vs AI harness: compares heuristics by playing them
against each other at the same depth K.

Every pair plays from the same random openings twice, with the sides
swapped, so neither heuristic gets the first-move advantage both times.
The AI itself is deterministic, so the random openings are what makes
the games different from each other.

Usage: python compare.py 2 3 4      (one run per K, all rows in one CSV)
"""

import csv
import itertools
import os
import random
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "results")      # always next to the code

from engine import (HUMAN, COMPUTER, new_board, get_valid_moves,
                    drop_piece, is_full, get_scores)
from heuristic import h1, h2, h3, h4
from ai import choose_move

HEURISTICS = {"h1": h1, "h2": h2, "h3": h3, "h4": h4}

OPENINGS = 15           # different random openings per pair and per K
RANDOM_PLIES = 2        # the first plies of every game are random


def play_match(K, name_first, name_second, seed=0, random_plies=RANDOM_PLIES):
    """
    Play one full game. `name_first` moves first (uses the HUMAN piece),
    `name_second` moves second (COMPUTER piece). The first `random_plies`
    plies are random (same for the same seed), then both sides use the AI.
    """
    rng = random.Random(seed)
    heuristics = {HUMAN: HEURISTICS[name_first], COMPUTER: HEURISTICS[name_second]}

    board = new_board()
    player = HUMAN
    ply = 0
    while not is_full(board):
        if ply < random_plies:
            col = rng.choice(get_valid_moves(board))
        else:
            col, _ = choose_move(board, K, print_tree=False,
                                 heuristic=heuristics[player], player=player)
        board, _ = drop_piece(board, col, player)
        player = COMPUTER if player == HUMAN else HUMAN
        ply += 1

    first_fours, second_fours = get_scores(board)
    return {"K": K, "seed": seed, "first": name_first, "second": name_second,
            "first_fours": first_fours, "second_fours": second_fours}


def run_comparison(K=3, openings=OPENINGS):
    """Every pair, both side orders, `openings` random openings. One dict per game."""
    rows = []
    for seed in range(openings):
        for a, b in itertools.combinations(HEURISTICS, 2):
            rows.append(play_match(K, a, b, seed))      # a moves first
            rows.append(play_match(K, b, a, seed))      # b moves first
    return rows


def save_csv(rows, path=os.path.join(RESULTS_DIR, "comparison.csv")):
    """Write one row per game."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows):
    """Per heuristic: games won / tied / lost and total fours scored / conceded."""
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


def save_summary_csv(per_k_stats, path=os.path.join(RESULTS_DIR, "comparison_summary.csv")):
    """Write one row per (K, heuristic): won / tied / lost and fours for / against."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fields = ["K", "heuristic", "won", "tied", "lost", "fours_for", "fours_against"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for K, stats in per_k_stats.items():
            for name, s in stats.items():
                writer.writerow({"K": K, "heuristic": name, "won": s["won"],
                                 "tied": s["tied"], "lost": s["lost"],
                                 "fours_for": s["for"], "fours_against": s["against"]})


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
    ks = [int(a) for a in sys.argv[1:]] or [3]
    all_rows = []
    per_k_stats = {}
    for K in ks:
        rows = run_comparison(K)
        all_rows.extend(rows)
        per_k_stats[K] = summarize(rows)
        print(f"\n--- K={K} ({len(rows)} games) ---")
        print_summary(per_k_stats[K])
        # Save after every K, so an interrupted run still keeps finished results.
        save_csv(all_rows)
        save_summary_csv(per_k_stats)
        print(f"(saved so far to {RESULTS_DIR})", flush=True)
