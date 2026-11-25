"""
ai.py - Minimax with alpha-beta pruning for Connect 4.

The player we choose a move for (`me`) is MAX, the opponent is MIN.
The search stops at depth K or at a full board. Pass node=None to search
without building the tree (used for the big experiments).
"""

import time

from engine import COMPUTER, EMPTY, count_fours, drop_piece, get_valid_moves, is_full
from heuristic import h4, other
from tree import INF, Node, count_pruned, save_tree, tree_to_text

# Centre columns first (0-based). Good moves found early => more cut-offs.
MOVE_ORDER = [3, 2, 4, 1, 5, 0, 6]

# Value per four of a finished game. A full board is an exact result, so it is
# worth 10x more per four than the heuristic's guess (FOUR_WEIGHT = 100 in
# heuristic.py) and is shown as FINAL / score= in the tree, not LEAF / h=.
FINAL_WEIGHT = 1000


def ordered_moves(board):
    """Valid columns in MOVE_ORDER."""
    valid = set(get_valid_moves(board))
    return [c for c in MOVE_ORDER if c in valid]


def final_value(board, me):
    """Exact value of a full board: 1000 x (my fours - their fours)."""
    return FINAL_WEIGHT * (count_fours(board, me) - count_fours(board, other(me)))


def _next_kind(kind):
    """MAX nodes have MIN children and vice versa."""
    return "MIN" if kind == "MAX" else "MAX"


def _mark_pruned(parent, columns, mover, alpha, beta):
    """Add the skipped children as PRUNED nodes (never searched, never counted)."""
    for col in columns:
        skipped = Node(None, col, mover, _next_kind(parent.kind), parent.depth + 1)
        skipped.pruned = True
        skipped.alpha, skipped.beta = alpha, beta
        parent.children.append(skipped)


def minimax(board, depth, K, maximizing, me, heuristic,
            alpha, beta, use_pruning, counter, node):
    """
    Search below `board`. Returns (value, best_col); best_col is None at leaves.
    counter[0] counts visited nodes; `node` is the tree node to fill (or None).
    """
    counter[0] += 1

    full = is_full(board)
    if full or depth == K:                      # leaf: exact score or heuristic
        value = final_value(board, me) if full else heuristic(board, me)
        if node is not None:
            node.value, node.is_leaf, node.final = value, True, full
            node.alpha, node.beta = alpha, beta
        return value, None

    mover = me if maximizing else other(me)
    moves = ordered_moves(board)
    best = -INF if maximizing else INF
    best_col = None

    for i, col in enumerate(moves):
        child_board, _ = drop_piece(board, col, mover)
        child_node = None
        if node is not None:
            child_node = Node(child_board, col, mover, _next_kind(node.kind), depth + 1)
            node.children.append(child_node)

        value, _ = minimax(child_board, depth + 1, K, not maximizing, me, heuristic,
                           alpha, beta, use_pruning, counter, child_node)

        if maximizing:
            if value > best:                    # strict: first best move wins ties
                best, best_col = value, col
            alpha = max(alpha, best)
        else:
            if value < best:
                best, best_col = value, col
            beta = min(beta, best)

        if use_pruning and alpha >= beta:       # the other player will avoid this branch
            if node is not None:
                _mark_pruned(node, moves[i + 1:], mover, alpha, beta)
            break

    if node is not None:
        node.value, node.alpha, node.beta = best, alpha, beta
    return best, best_col


def _emit_tree(root, board, tree_depth=None, show_boards=False):
    """
    Print the tree and save it to trees/turn_<n>.txt (n = computer's turn number).
    tree_depth limits only the console print; the saved file always has the full tree.
    """
    discs = sum(cell != EMPTY for row in board for cell in row)
    turn = (discs + 1) // 2                     # human moves first
    print(f"\n===== Minimax tree, computer turn {turn} =====")
    print(tree_to_text(root, show_boards=show_boards, max_depth=tree_depth))
    path = save_tree(root, turn, show_boards=show_boards)
    print(f"===== (full tree saved to {path}) =====\n")


def choose_move(board, K, use_pruning=True, print_tree=True,
                heuristic=None, player=COMPUTER, tree_depth=None, show_boards=True):
    """
    Best column for `player` after a K-level search.
    Returns (col, stats), stats = {"nodes", "time", "value", "pruned", "root"}:
    "pruned" is the number of cut-off branches and "root" the tree (both None
    when print_tree=False, because no tree is built then).
    Tie rule: the first column in MOVE_ORDER among equally good moves.
    print_tree=False also skips building the tree (faster, less memory).
    tree_depth limits how deep the CONSOLE print goes (the file stays full);
    show_boards adds the board grid under every leaf.
    """
    if K < 1:
        raise ValueError("K must be at least 1")
    heuristic = heuristic or h4                 # best heuristic in compare.py

    counter = [0]
    root = Node(board, None, None, "MAX", 0) if print_tree else None

    start = time.perf_counter()
    value, col = minimax(board, 0, K, True, player, heuristic,
                         -INF, INF, use_pruning, counter, root)
    elapsed = time.perf_counter() - start       # timer excludes printing

    if print_tree:
        _emit_tree(root, board, tree_depth, show_boards)
    return col, {"nodes": counter[0], "time": elapsed, "value": value,
                 "pruned": count_pruned(root) if root is not None else None,
                 "root": root}
