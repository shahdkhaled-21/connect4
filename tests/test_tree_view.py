"""Tests for tree_view.py, the tree.py helpers and four_cells."""

from engine import COMPUTER, HUMAN, drop_piece, four_cells, new_board
from ai import choose_move
from tree import count_nodes, count_pruned, tree_to_text
from tree_view import default_expanded, expand_all, principal_path, visible_rows


def build(moves):
    board = new_board()
    for col, player in moves:
        board, _ = drop_piece(board, col, player)
    return board


MIDGAME = build([(3, HUMAN), (3, COMPUTER), (2, HUMAN),
                 (4, COMPUTER), (2, HUMAN), (2, COMPUTER)])


def test_principal_path_starts_with_the_chosen_move():
    col, stats = choose_move(MIDGAME, 3, print_tree=True, tree_depth=0)
    root = stats["root"]
    path = principal_path(root)
    assert path[0] is root
    assert path[1].move == col                    # first step = the AI's move
    assert all(not n.pruned for n in path)
    assert path[1].value == root.value


def test_visible_rows_follow_the_expanded_set():
    _, stats = choose_move(MIDGAME, 2, print_tree=True, tree_depth=0)
    root = stats["root"]
    assert len(visible_rows(root, set())) == 1                    # collapsed root
    assert len(visible_rows(root, {root})) == 1 + len(root.children)
    everything = visible_rows(root, expand_all(root))
    assert len(everything) == 1 + count_nodes(root)
    assert len(visible_rows(root, default_expanded(root))) > 1


def test_stats_report_cut_branches():
    _, stats = choose_move(MIDGAME, 3, print_tree=True, tree_depth=0)
    assert stats["pruned"] == count_pruned(stats["root"]) > 0
    _, no_tree = choose_move(MIDGAME, 3, print_tree=False)
    assert no_tree["pruned"] is None and no_tree["root"] is None


def test_depth_limit_hides_nodes_and_says_so():
    _, stats = choose_move(MIDGAME, 3, print_tree=True, tree_depth=0)
    text = tree_to_text(stats["root"], max_depth=1)
    assert "nodes hidden" in text
    assert len(text.splitlines()) < len(tree_to_text(stats["root"]).splitlines())


def test_full_board_leaves_are_labelled_final():
    """With one empty cell left, the only child is a full board: FINAL, not LEAF."""
    board, player = new_board(), HUMAN
    for i in range(41):                              # fill 41 of the 42 cells
        open_cols = [c for c in range(7) if board[0][c] == 0]
        col = open_cols[i % 3 % len(open_cols)]
        board, _ = drop_piece(board, col, player)
        player = COMPUTER if player == HUMAN else HUMAN
    assert sum(cell == 0 for row in board for cell in row) == 1
    _, stats = choose_move(board, 3, print_tree=True, tree_depth=0)
    text = tree_to_text(stats["root"])
    assert "[FINAL]" in text and "score=" in text


def test_four_cells_marks_exactly_the_four():
    board = build([(0, COMPUTER), (1, COMPUTER), (2, COMPUTER), (3, COMPUTER),
                   (0, HUMAN)])
    assert four_cells(board) == {(5, 0), (5, 1), (5, 2), (5, 3)}
    assert four_cells(new_board()) == set()
