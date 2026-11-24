"""
main.py - Console game loop for Connect 4.

Human (H) moves first, computer (C) second. The game continues until the
board is full; the winner is whoever has more connected-fours.
"""

import argparse

from engine import (COLS, EMPTY, HUMAN, COMPUTER, new_board, get_valid_moves,
                    drop_piece, is_full, get_scores, winner)

from ai import choose_move

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


def parse_int(text):
    """Return int(text) for plain ASCII digits, otherwise None (never raises)."""
    text = text.strip()
    if text.isascii() and text.isdigit():
        return int(text)
    return None


def ask_k():
    """Ask the user for the search depth K until a valid integer >= 1 is given."""
    while True:
        k = parse_int(input("Enter K (search depth, e.g. 1-6): "))
        if k is not None and k >= 1:
            return k
        print("K must be an integer >= 1.")


def ask_human_move(board):
    """Ask the human for a column (1..COLS). Returns a 0-based column index."""
    valid = get_valid_moves(board)
    while True:
        number = parse_int(input(f"Your move (column 1-{COLS}): "))
        if number is None:
            print("Please enter a number.")
            continue
        col = number - 1
        if not (0 <= col < COLS):
            print(f"Column must be between 1 and {COLS}.")
        elif col not in valid:
            print("That column is full. Choose another.")
        else:
            return col


def play(tree_depth=None, show_boards=False):
    """
    Run one full game.
    tree_depth limits the console print of the tree (the saved file stays full);
    show_boards prints the board grid under every leaf of the tree.
    """
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
            col, stats = choose_move(board, K, tree_depth=tree_depth,
                                     show_boards=show_boards)
            board, _ = drop_piece(board, col, COMPUTER)
            print(f"Computer plays column {col + 1} "
                  f"(value={stats['value']}, nodes={stats['nodes']}, "
                  f"cut={stats['pruned']}, "
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


def main():
    """Parse the optional command-line flags and start a game."""
    parser = argparse.ArgumentParser(description="Connect 4 vs. a minimax AI (console).")
    parser.add_argument("--tree-depth", type=int, default=None, metavar="N",
                        help="print only the first N levels of the tree in the console "
                             "(the file in trees/ always has the full tree)")
    parser.add_argument("--boards", action="store_true",
                        help="print the board grid under every leaf of the tree")
    args = parser.parse_args()
    try:
        play(tree_depth=args.tree_depth, show_boards=args.boards)
    except (KeyboardInterrupt, EOFError):
        print("\nGame aborted.")


if __name__ == "__main__":
    main()
