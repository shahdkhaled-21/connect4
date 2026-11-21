"""Tests for ai.py: pruning correctness, tactics, and interface."""

from engine import new_board, drop_piece, get_valid_moves, COMPUTER, HUMAN
from ai import choose_move


def build(moves):
    """Play a list of (col, player) moves on a fresh board."""
    board = new_board()
    for col, player in moves:
        board, _ = drop_piece(board, col, player)
    return board


MIDGAME = build([(3, HUMAN), (3, COMPUTER), (2, HUMAN),
                 (4, COMPUTER), (2, HUMAN), (2, COMPUTER)])


def test_pruning_gives_same_value():
    """Alpha-beta must not change the minimax value at the root."""
    for board in (new_board(), MIDGAME):
        for K in (1, 2, 3, 4):
            _, with_p = choose_move(board, K, use_pruning=True, print_tree=False)
            _, without = choose_move(board, K, use_pruning=False, print_tree=False)
            assert with_p["value"] == without["value"], f"K={K}"


def test_pruning_expands_fewer_nodes():
    _, with_p = choose_move(new_board(), 4, use_pruning=True, print_tree=False)
    _, without = choose_move(new_board(), 4, use_pruning=False, print_tree=False)
    assert with_p["nodes"] < without["nodes"]


def test_takes_a_winning_four():
    """Computer has 3 in a row on the bottom; column 4 completes the four."""
    board = build([(0, COMPUTER), (4, HUMAN), (1, COMPUTER),
                   (5, HUMAN), (2, COMPUTER)])
    col, _ = choose_move(board, 1, print_tree=False)
    assert col == 3


def test_plays_for_the_given_player():
    """With player=HUMAN the search maximises for HUMAN, not COMPUTER."""
    board = build([(0, HUMAN), (4, COMPUTER), (1, HUMAN),
                   (5, COMPUTER), (2, HUMAN)])
    col, _ = choose_move(board, 1, print_tree=False, player=HUMAN)
    assert col == 3


def test_never_picks_a_full_column():
    # column 3 filled with alternating discs (no vertical four)
    board = build([(3, COMPUTER), (3, HUMAN), (3, COMPUTER),
                   (3, HUMAN), (3, COMPUTER), (3, HUMAN)])
    assert 3 not in get_valid_moves(board)
    for K in (1, 2, 3):
        col, _ = choose_move(board, K, print_tree=False)
        assert col in get_valid_moves(board)


def test_returns_stats():
    col, stats = choose_move(MIDGAME, 2, print_tree=False)
    assert 0 <= col <= 6
    assert set(stats) >= {"nodes", "time", "value"}
    assert stats["nodes"] > 0
    assert stats["time"] >= 0


def test_does_not_mutate_board():
    snapshot = [row[:] for row in MIDGAME]
    choose_move(MIDGAME, 3, print_tree=False)
    assert MIDGAME == snapshot