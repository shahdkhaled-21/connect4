"""
main.py - Console game loop for Connect 4.

Human (H) moves first, computer (C) second. The game continues until the
board is full; the winner is whoever has more connected-fours.
"""

import random

from engine import (COLS, EMPTY, HUMAN, COMPUTER, new_board, get_valid_moves,
                    drop_piece, is_full, get_scores, winner)

# Use B's AI when it exists; until then fall back to a random-move stub
# so the game loop can be tested on its own.
try:
    from ai import choose_move
except ImportError:
    def choose_move(board, K, use_pruning=True, print_tree=True):
        """Stub: pick a random valid column. Same signature as B's version."""
        col = random.choice(get_valid_moves(board))
        return col, {"nodes": 0, "time": 0.0, "value": 0}


def print_board(board):
    """Print the board with column numbers 1..7 on top."""
    symbols = {EMPTY: ".", HUMAN: "H", COMPUTER: "C"}
    print()
    print("  " + " ".join(str(c + 1) for c in range(COLS)))
    for row in board:
        print("  " + " ".join(symbols[cell] for cell in row))
    print()


def print_scores(board):
    """Show how many connected-fours each player has."""
    h, c = get_scores(board)
    print(f"Score -> Human: {h} | Computer: {c}")


def ask_k():
    """Ask the user for the search depth K until a valid integer >= 1 is given."""
    while True:
        text = input("Enter K (search depth, e.g. 1-6): ").strip()
        if text.isdigit() and int(text) >= 1:
            return int(text)
        print("K must be an integer >= 1.")


def ask_human_move(board):
    """Ask the human for a column (1..COLS). Returns a 0-based column index."""
    valid = get_valid_moves(board)
    while True:
        text = input(f"Your move (column 1-{COLS}): ").strip()
        if not text.isdigit():
            print("Please enter a number.")
            continue
        col = int(text) - 1
        if not (0 <= col < COLS):
            print(f"Column must be between 1 and {COLS}.")
        elif col not in valid:
            print("That column is full. Choose another.")
        else:
            return col


def play():
    """Run one full game."""
    K = ask_k()
    board = new_board()
    print_board(board)

    human_turn = True                       # human moves first
    while not is_full(board):
        if human_turn:
            col = ask_human_move(board)
            board, _ = drop_piece(board, col, HUMAN)
            print(f"Human plays column {col + 1}")
        else:
            col, stats = choose_move(board, K)
            board, _ = drop_piece(board, col, COMPUTER)
            print(f"Computer plays column {col + 1} "
                  f"(value={stats['value']}, nodes={stats['nodes']}, "
                  f"time={stats['time']:.4f}s)")

        print_board(board)
        print_scores(board)
        human_turn = not human_turn

    # Board is full: decide the winner by number of fours
    print("\n=== GAME OVER ===")
    print_scores(board)
    w = winner(board)
    if w == HUMAN:
        print("You win!")
    elif w == COMPUTER:
        print("The computer wins!")
    else:
        print("It's a tie!")


if __name__ == "__main__":
    play()