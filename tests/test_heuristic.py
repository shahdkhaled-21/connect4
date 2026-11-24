"""Tests for heuristic.py: interface, symmetry and sanity properties."""

from engine import new_board, drop_piece, COMPUTER, HUMAN
from heuristic import WINDOWS, h1, h2, h3, h4, other, parity_score, PARITY_BONUS

ALL = [h1, h2, h3, h4]


def build(moves):
    """Play a list of (col, player) moves on a fresh board."""
    board = new_board()
    for col, player in moves:
        board, _ = drop_piece(board, col, player)
    return board


def test_window_count():
    assert len(WINDOWS) == 69


def test_empty_board_is_zero():
    for h in ALL:
        assert h(new_board(), COMPUTER) == 0
        assert h(new_board(), HUMAN) == 0


def test_symmetry():
    """The two players' views of the same board must cancel exactly."""
    board = build([(3, COMPUTER), (2, HUMAN), (4, COMPUTER), (3, HUMAN),
                   (1, COMPUTER), (3, COMPUTER), (0, HUMAN)])
    for h in ALL:
        assert h(board, COMPUTER) == -h(board, HUMAN)


def test_leader_gets_positive_value():
    board = build([(0, COMPUTER), (1, COMPUTER), (2, COMPUTER)])
    for h in ALL:
        assert h(board, COMPUTER) > 0
        assert h(board, HUMAN) < 0


def test_completed_four_beats_three():
    three = build([(0, COMPUTER), (1, COMPUTER), (2, COMPUTER)])
    four = build([(0, COMPUTER), (1, COMPUTER), (2, COMPUTER), (3, COMPUTER)])
    for h in ALL:
        assert h(four, COMPUTER) > h(three, COMPUTER)


def test_playable_threat_adds_bonus():
    board = build([(0, COMPUTER), (1, COMPUTER), (2, COMPUTER)])
    assert h2(board, COMPUTER) > h1(board, COMPUTER)


def test_does_not_mutate_board():
    board = build([(3, COMPUTER), (3, HUMAN)])
    snapshot = [row[:] for row in board]
    for h in ALL:
        h(board, COMPUTER)
    assert board == snapshot

def test_parity_rewards_the_owners_natural_height():
    """Computer owns even heights: a hidden 3-window at height 2 earns the bonus."""
    board = build([(0, HUMAN), (0, COMPUTER), (1, HUMAN), (1, COMPUTER),
                   (2, HUMAN), (2, COMPUTER)])      # C C C on height 2, gap at column 4
    assert parity_score(board, COMPUTER) == PARITY_BONUS
    assert parity_score(board, HUMAN) == -PARITY_BONUS


def test_parity_ignores_the_wrong_height():
    """Human owns odd heights: the same shape at height 2 earns nothing."""
    board = build([(0, COMPUTER), (0, HUMAN), (1, COMPUTER), (1, HUMAN),
                   (2, COMPUTER), (2, HUMAN)])
    assert parity_score(board, HUMAN) == 0
