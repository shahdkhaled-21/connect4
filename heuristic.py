"""
heuristic.py - Evaluation functions for Connect 4.

Every heuristic has the signature  h(board, me) -> int  and scores the
board from `me`'s point of view: larger = better for `me`.
"""

from engine import ROWS, COLS, EMPTY, HUMAN, COMPUTER, count_fours


def _build_windows():
    """All 69 windows of 4 cells, as lists of (row, col). Built once."""
    windows = []
    for r in range(ROWS):
        for c in range(COLS):
            for dr, dc in [(0, 1), (1, 0), (1, 1), (1, -1)]:
                end_r, end_c = r + 3 * dr, c + 3 * dc
                if 0 <= end_r < ROWS and 0 <= end_c < COLS:
                    windows.append([(r + i * dr, c + i * dc) for i in range(4)])
    return windows


WINDOWS = _build_windows()


def other(player):
    """The opponent's piece."""
    return COMPUTER if player == HUMAN else HUMAN

# Tunable weights. A completed four is permanent, so it is worth much more
# than a window that is only a potential four and may still be blocked.
FOUR_WEIGHT = 100
WINDOW_WEIGHT = {1: 1, 2: 5, 3: 20}     # discs in an otherwise-open window


def window_score(cells, me):
    """
    Score one 4-cell window for `me`.
    A window holding both colors is dead (0). A window holding only one
    side's discs scores by how many it has. Four discs is a completed four,
    which is already counted by count_fours, so it is skipped here.
    """
    opp = other(me)
    mine = cells.count(me)
    theirs = cells.count(opp)
    if mine and theirs:
        return 0
    if mine == 4 or theirs == 4:
        return 0
    return WINDOW_WEIGHT.get(mine, 0) - WINDOW_WEIGHT.get(theirs, 0)


def windows_score(board, me):
    """Sum window_score over all 69 windows."""
    total = 0
    for window in WINDOWS:
        cells = [board[r][c] for r, c in window]
        total += window_score(cells, me)
    return total


def evaluate(board, me=COMPUTER):
    """
    Heuristic 1: four-count difference plus potential-four windows.
    Positive = good for `me`.
    """
    fours = count_fours(board, me) - count_fours(board, other(me))
    return FOUR_WEIGHT * fours + windows_score(board, me)

THREAT_BONUS = 15                       # 3-in-window whose gap is playable now
CENTER_WEIGHT = [0, 1, 2, 3, 2, 1, 0]   # per disc, by column


def threat_score(board, me):
    """
    Bonus for each window with 3 discs of one side and one empty cell that
    can be filled on the next move (bottom row or disc below). Counted for
    `me` positively and for the opponent negatively.
    """
    total = 0
    for window in WINDOWS:
        cells = [board[r][c] for r, c in window]
        for owner, sign in ((me, 1), (other(me), -1)):
            if cells.count(owner) == 3 and cells.count(EMPTY) == 1:
                r, c = window[cells.index(EMPTY)]
                if r == ROWS - 1 or board[r + 1][c] != EMPTY:
                    total += sign * THREAT_BONUS
    return total


def center_score(board, me):
    """Discs in central columns are worth more (they join more windows)."""
    total = 0
    for r in range(ROWS):
        for c in range(COLS):
            if board[r][c] == me:
                total += CENTER_WEIGHT[c]
            elif board[r][c] == other(me):
                total -= CENTER_WEIGHT[c]
    return total


def h1(board, me):
    """Fours difference + window potential."""
    return evaluate(board, me)


def h2(board, me):
    """h1 + playable-threat bonus."""
    return h1(board, me) + threat_score(board, me)


def h3(board, me):
    """h2 + center-column bonus."""
    return h2(board, me) + center_score(board, me)