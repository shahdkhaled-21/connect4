"""
tree_view.py - Pure logic behind the GUI's collapsible minimax-tree panel.

No pygame in here, so it can be unit-tested without a window.
The panel shows the tree as a flat list of visible rows; a node's children
are visible only while the node is in the `expanded` set.
"""


def principal_path(root):
    """
    The chosen line of play: from the root, repeatedly follow the first child
    (in move order) that was really searched and whose value equals its
    parent's value. At the root this is exactly the column the AI plays.
    Returns the list of nodes [root, ..., last].
    """
    path = [root]
    node = root
    while node.children:
        step = next((c for c in node.children
                     if not c.pruned and c.value == node.value), None)
        if step is None:
            break
        path.append(step)
        node = step
    return path


def default_expanded(root):
    """Initial view: the root and every node on the chosen path are open."""
    return set(principal_path(root)[:-1])


def expand_all(root):
    """Every node that has children."""
    opened, stack = set(), [root]
    while stack:
        node = stack.pop()
        if node.children:
            opened.add(node)
            stack.extend(node.children)
    return opened


def visible_rows(root, expanded):
    """
    Flat, depth-first list of (node, has_children, is_open) for every row the
    panel should show, given the set of expanded nodes.
    """
    rows = []

    def walk(node):
        has_children = bool(node.children)
        is_open = node in expanded
        rows.append((node, has_children, is_open))
        if is_open:
            for child in node.children:
                walk(child)

    walk(root)
    return rows
