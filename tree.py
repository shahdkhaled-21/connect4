"""
tree.py - Minimax tree node, console printer, and file export.

kind   = who moves NEXT from this node ("MAX" or "MIN").
player = who made the move that led here (None at the root).
Columns are printed 1..7 to match what the user types.

Leaf labels:
    LEAF  - the search reached depth K; the value is the heuristic (h=).
    FINAL - the board is full; the value is the exact final score
            (1000 per connected-four of difference), not a heuristic guess.
"""

import os

from engine import HUMAN

INF = float("inf")

# Trees are saved next to the code, whatever folder the program is started from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TREES_DIR = os.path.join(BASE_DIR, "trees")

SYMBOLS = {0: ".", 1: "H", 2: "C"}


class Node:
    """One state in the search tree."""

    def __init__(self, board, move, player, kind, depth):
        self.board = board
        self.move = move            # column played to reach this node (None = root)
        self.player = player        # piece that played it
        self.kind = kind            # "MAX" or "MIN"
        self.depth = depth          # 0 at the root
        self.value = None           # minimax value, or heuristic value at a leaf
        self.alpha = -INF           # final alpha / beta when the node finished
        self.beta = INF
        self.is_leaf = False        # True if the search stopped here
        self.final = False          # True if the leaf is a full board (exact score)
        self.pruned = False         # True if cut off and never expanded
        self.children = []


def fmt_bound(x):
    """Format alpha/beta: +inf, -inf or the number."""
    if x == INF:
        return "+inf"
    if x == -INF:
        return "-inf"
    return str(x)


_fmt = fmt_bound  # backwards-compatible alias


def node_tag(node):
    """The bracketed label of a node: MAX, MIN, LEAF or FINAL."""
    if node.is_leaf:
        return "FINAL" if node.final else "LEAF"
    return node.kind


def node_label(node):
    """Short description of how a node was reached, e.g. '[MIN] col=4 (comp)'."""
    if node.move is None:
        return f"[{node.kind}] root"
    who = "human" if node.player == HUMAN else "comp"
    return f"[{node_tag(node)}] col={node.move + 1} ({who})"


def node_tail(node):
    """The value part of a node line: PRUNED, h=..., score=... or value=..."""
    if node.pruned:
        return "PRUNED"
    if node.is_leaf:
        return f"score={node.value}" if node.final else f"h={node.value}"
    return f"value={node.value}"


def node_line(node):
    """One printed line for a node, indented by depth."""
    text = "  " * node.depth + node_label(node)
    bounds = f"a={fmt_bound(node.alpha)} b={fmt_bound(node.beta)}"
    return f"{text:<44}{bounds:<22}{node_tail(node)}"


def board_lines(board, indent):
    """ASCII grid of a board, each row prefixed by `indent` spaces."""
    pad = " " * indent
    return [pad + " ".join(SYMBOLS[cell] for cell in row) for row in board]


def count_nodes(node):
    """Number of nodes in the subtree below `node` (not counting `node`)."""
    return sum(1 + count_nodes(child) for child in node.children)


def count_pruned(node):
    """Number of PRUNED (cut-off) nodes in the tree rooted at `node`."""
    return int(node.pruned) + sum(count_pruned(child) for child in node.children)


def tree_to_text(root, show_boards=False, max_depth=None):
    """
    The whole tree as a string, one node per line, depth-first.
    show_boards=True: each leaf is followed by its board grid.
    max_depth=N: nodes deeper than N are hidden and replaced by a
    "... (k nodes hidden)" line; None prints everything.
    """
    lines = []

    def walk(node):
        lines.append(node_line(node))
        if show_boards and node.is_leaf and node.board is not None:
            lines.extend(board_lines(node.board, 2 * node.depth + 4))
        if max_depth is not None and node.depth >= max_depth and node.children:
            hidden = count_nodes(node)
            lines.append("  " * (node.depth + 1) + f"... ({hidden} nodes hidden)")
            return
        for child in node.children:
            walk(child)

    walk(root)
    return "\n".join(lines)


def save_tree(root, turn, folder=None, show_boards=False):
    """Write the full tree of one computer turn to trees/turn_<n>.txt."""
    folder = folder or TREES_DIR
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"turn_{turn}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(tree_to_text(root, show_boards=show_boards) + "\n")
    return path


def tree_to_dict(node):
    """Nested dict of the tree (for JSON export)."""
    return {
        "move": None if node.move is None else node.move + 1,
        "player": node.player,
        "kind": node.kind,
        "depth": node.depth,
        "value": node.value,
        "alpha": fmt_bound(node.alpha),      # strings, since JSON has no infinity
        "beta": fmt_bound(node.beta),
        "is_leaf": node.is_leaf,
        "final": node.final,
        "pruned": node.pruned,
        "children": [tree_to_dict(c) for c in node.children],
    }
