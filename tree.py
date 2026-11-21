"""
tree.py - Minimax tree node, console printer, and file export.

kind  = who moves NEXT from this node ("MAX" or "MIN").
player = who made the move that led here (None at the root).
Columns are printed 1..7 to match what the user types.
"""

import os

from engine import HUMAN

INF = float("inf")


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
        self.is_leaf = False        # True if evaluated by the heuristic
        self.pruned = False         # True if cut off and never expanded
        self.children = []


def _fmt(x):
    """Format alpha/beta: +inf, -inf or the number."""
    if x == INF:
        return "+inf"
    if x == -INF:
        return "-inf"
    return str(x)


def node_line(node):
    """One printed line for a node, indented by depth."""
    indent = "  " * node.depth
    if node.move is None:
        label = f"[{node.kind}] root"
    else:
        who = "human" if node.player == HUMAN else "comp"
        tag = "LEAF" if node.is_leaf else node.kind
        label = f"[{tag}] col={node.move + 1} ({who})"
    bounds = f"a={_fmt(node.alpha)} b={_fmt(node.beta)}"
    if node.pruned:
        tail = "PRUNED"
    elif node.is_leaf:
        tail = f"h={node.value}"
    else:
        tail = f"value={node.value}"
    text = indent + label
    return f"{text:<44}{bounds:<22}{tail}"


def tree_to_text(root):
    """The whole tree as a string, one node per line, depth-first."""
    lines = []

    def walk(node):
        lines.append(node_line(node))
        for child in node.children:
            walk(child)

    walk(root)
    return "\n".join(lines)


def save_tree(root, turn, folder="trees"):
    """Write the tree of one computer turn to trees/turn_<n>.txt."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"turn_{turn}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(tree_to_text(root) + "\n")
    return path

SYMBOLS = {0: ".", 1: "H", 2: "C"}


def board_lines(board, indent):
    """ASCII grid of a board, each row prefixed by `indent` spaces."""
    pad = " " * indent
    return [pad + " ".join(SYMBOLS[cell] for cell in row) for row in board]


def tree_to_text(root, show_boards=False):
    """
    The whole tree as a string, one node per line, depth-first.
    With show_boards=True, each leaf is followed by its board grid.
    """
    lines = []

    def walk(node):
        lines.append(node_line(node))
        if show_boards and node.is_leaf and node.board is not None:
            lines.extend(board_lines(node.board, 2 * node.depth + 4))
        for child in node.children:
            walk(child)

    walk(root)
    return "\n".join(lines)


def tree_to_dict(node):
    """Nested dict of the tree (for the GUI panel or JSON export)."""
    return {
        "move": None if node.move is None else node.move + 1,
        "player": node.player,
        "kind": node.kind,
        "depth": node.depth,
        "value": node.value,
        "alpha": _fmt(node.alpha),      # strings, since JSON has no infinity
        "beta": _fmt(node.beta),
        "is_leaf": node.is_leaf,
        "pruned": node.pruned,
        "children": [tree_to_dict(c) for c in node.children],
    }

