"""
experiments.py - Time and node-count experiments for the K analysis.

Plays full games of "random opponent vs the AI" and records, for every AI move,
how many nodes the search expanded and how long it took. Uses only the agreed
interface: choose_move(board, K, use_pruning, print_tree) -> (col, stats).
"""

import csv
import os
import random

from engine import HUMAN, COMPUTER, new_board, get_valid_moves, drop_piece, is_full
from main import choose_move       # B's AI if ai.py exists, otherwise the random stub


def play_game(K, use_pruning=True, seed=0):
    """
    Play one full game: a random opponent (moves first) against the AI.
    Returns one dict per AI move: {"K", "pruning", "move", "nodes", "time"}.
    The seed makes the opponent's moves repeatable, so runs can be compared fairly.
    """
    rng = random.Random(seed)
    board = new_board()
    rows = []
    human_turn = True
    move_number = 0

    while not is_full(board):
        if human_turn:
            col = rng.choice(get_valid_moves(board))
            board, _ = drop_piece(board, col, HUMAN)
        else:
            move_number += 1
            col, stats = choose_move(board, K, use_pruning=use_pruning, print_tree=False)
            board, _ = drop_piece(board, col, COMPUTER)
            rows.append({"K": K, "pruning": use_pruning, "move": move_number,
                         "nodes": stats["nodes"], "time": stats["time"]})
        human_turn = not human_turn

    return rows



def run_experiments(K_values=range(1, 7), no_prune_max_K=5, seed=0):
    """
    Run one game for every K, with pruning on and off. Returns all rows together.
    Without pruning the search grows like 7^K, so above no_prune_max_K it is skipped.
    """
    all_rows = []
    for K in K_values:
        for use_pruning in (True, False):
            if not use_pruning and K > no_prune_max_K:
                print(f"K={K}, pruning=off: skipped (too slow)")
                continue
            print(f"K={K}, pruning={'on' if use_pruning else 'off'} ...", flush=True)
            all_rows.extend(play_game(K, use_pruning, seed))
    return all_rows


def save_csv(rows, path="results/experiments_raw.csv"):
    """Write the raw rows (one per AI move) to a CSV file, creating the folder if needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["K", "pruning", "move", "nodes", "time"])
        writer.writeheader()
        writer.writerows(rows)

def summarize(rows):
    """
    Collapse the raw rows (one per AI move) into one row per (K, pruning) setting:
    average and total nodes, average and maximum time per move.
    """
    groups = {}
    for r in rows:
        groups.setdefault((r["K"], r["pruning"]), []).append(r)

    summary = []
    # Sort by K, and for each K show pruning ON before OFF
    for (K, pruning), g in sorted(groups.items(), key=lambda kv: (kv[0][0], not kv[0][1])):
        n = len(g)
        summary.append({
            "K": K,
            "pruning": pruning,
            "moves": n,
            "avg_nodes": sum(r["nodes"] for r in g) / n,
            "total_nodes": sum(r["nodes"] for r in g),
            "avg_time": sum(r["time"] for r in g) / n,
            "max_time": max(r["time"] for r in g),
        })
    return summary


def print_summary(summary):
    """Print the summary as an aligned table in the console."""
    print(f"{'K':>2} {'pruning':>7} {'moves':>5} {'avg nodes':>12} {'total nodes':>12} "
          f"{'avg time (s)':>13} {'max time (s)':>13}")
    for s in summary:
        print(f"{s['K']:>2} {'on' if s['pruning'] else 'off':>7} {s['moves']:>5} "
              f"{s['avg_nodes']:>12.1f} {s['total_nodes']:>12} "
              f"{s['avg_time']:>13.4f} {s['max_time']:>13.4f}")


def save_summary_csv(summary, path="results/experiments_summary.csv"):
    """Write the summary table to a CSV file (for the report and the charts)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)

def make_charts(summary, out_dir="results"):
    """
    Draw two charts from the summary and save them as PNG files:
    average nodes per move vs K, and average time per move vs K,
    each with one line for pruning ON and one for pruning OFF.
    """
    import matplotlib
    matplotlib.use("Agg")                 # draw to files only, no window pops up
    import matplotlib.pyplot as plt

    os.makedirs(out_dir, exist_ok=True)
    charts = [
        ("avg_nodes", "Average nodes expanded per move", "nodes_vs_k.png"),
        ("avg_time", "Average time per move (seconds)", "time_vs_k.png"),
    ]
    for key, ylabel, filename in charts:
        fig, ax = plt.subplots(figsize=(7, 4.5))
        for pruning, label, style in [(True, "With alpha-beta pruning", "o-"),
                                      (False, "Without pruning", "s--")]:
            points = [(s["K"], s[key]) for s in summary if s["pruning"] == pruning]
            if points:
                ax.plot([p[0] for p in points], [p[1] for p in points], style, label=label)
        # Log scale shows the exponential growth clearly (only possible if all values > 0)
        if all(s[key] > 0 for s in summary):
            ax.set_yscale("log")
        ax.set_xlabel("Search depth K")
        ax.set_ylabel(ylabel)
        ax.set_xticks(sorted({s["K"] for s in summary}))
        ax.grid(True, alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, filename), dpi=150)
        plt.close(fig)

if __name__ == "__main__":
    rows = run_experiments()
    save_csv(rows)
    summary = summarize(rows)
    print_summary(summary)
    save_summary_csv(summary)
    make_charts(summary)
    print("Saved results/experiments_raw.csv and results/experiments_summary.csv")