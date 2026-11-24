"""
engine.py - Connect 4 game engine.

Board: 2D list board[row][col], row 0 = top, row ROWS-1 = bottom.
Cell values: 0 = empty, 1 = human, 2 = computer.
All functions are pure: drop_piece returns a NEW board, so the minimax
search can explore moves without having to undo them.
"""

ROWS, COLS = 6, 7
EMPTY, HUMAN, COMPUTER = 0, 1, 2

# (row step, col step): horizontal, vertical, diagonal down-right, diagonal down-left
DIRECTIONS = [(0, 1), (1, 0), (1, 1), (1, -1)]


def new_board():
    """Return an empty ROWS x COLS board."""
    return [[EMPTY] * COLS for _ in range(ROWS)]


def get_valid_moves(board):
    """Return the columns that are not full (the top cell is empty)."""
    return [c for c in range(COLS) if board[0][c] == EMPTY]


def drop_piece(board, col, player):
    """
    Drop a disc for `player` into column `col`.
    Returns (new_board, row) where row is where the disc landed.
    Raises ValueError if the column is full or out of range.
    """
    if not (0 <= col < COLS) or board[0][col] != EMPTY:
        raise ValueError(f"Invalid move: column {col}")
    new = [row[:] for row in board]            # copy, do not mutate the input
    for r in range(ROWS - 1, -1, -1):          # find the lowest empty cell
        if new[r][col] == EMPTY:
            new[r][col] = player
            return new, r


def count_fours(board, player):
    """
    Count every group of four consecutive discs of `player`
    (horizontal, vertical, both diagonals).
    Overlapping fours count separately: 5 in a row = 2 fours.
    """
    count = 0
    for r in range(ROWS):
        for c in range(COLS):
            for dr, dc in DIRECTIONS:
                end_r, end_c = r + 3 * dr, c + 3 * dc
                if not (0 <= end_r < ROWS and 0 <= end_c < COLS):
                    continue                    # window would leave the board
                if all(board[r + i * dr][c + i * dc] == player for i in range(4)):
                    count += 1
    return count


def four_cells(board):
    """
    Return the set of (row, col) cells that belong to at least one
    connected-four of either player (used by the GUI to highlight fours).
    """
    cells = set()
    for r in range(ROWS):
        for c in range(COLS):
            first = board[r][c]
            if first == EMPTY:
                continue
            for dr, dc in DIRECTIONS:
                end_r, end_c = r + 3 * dr, c + 3 * dc
                if not (0 <= end_r < ROWS and 0 <= end_c < COLS):
                    continue
                if all(board[r + i * dr][c + i * dc] == first for i in range(4)):
                    cells.update((r + i * dr, c + i * dc) for i in range(4))
    return cells


def new_fours_after_move(board, row, col, player):
    """
    Count only the fours that include the disc at (row, col).
    Faster than count_fours when scoring a single move.
    """
    count = 0
    for dr, dc in DIRECTIONS:
        for k in range(4):                      # position of the disc inside the window
            sr, sc = row - k * dr, col - k * dc  # window start
            er, ec = sr + 3 * dr, sc + 3 * dc    # window end
            if not (0 <= sr < ROWS and 0 <= sc < COLS and
                    0 <= er < ROWS and 0 <= ec < COLS):
                continue
            if all(board[sr + i * dr][sc + i * dc] == player for i in range(4)):
                count += 1
    return count


def is_full(board):
    """True when no column can accept another disc."""
    return all(board[0][c] != EMPTY for c in range(COLS))


def get_scores(board):
    """Return (human_fours, computer_fours)."""
    return count_fours(board, HUMAN), count_fours(board, COMPUTER)


def winner(board):
    """Return HUMAN, COMPUTER, or 0 for a tie, by number of fours."""
    h, c = get_scores(board)
    if h > c:
        return HUMAN
    if c > h:
        return COMPUTER
    return 0
