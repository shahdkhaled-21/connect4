from engine import *


def board_from(rows):
    """Build a board from 6 strings of 7 chars: '.' empty, 'H' human, 'C' computer."""
    m = {'.': EMPTY, 'H': HUMAN, 'C': COMPUTER}
    return [[m[ch] for ch in row] for row in rows]


def test_empty_board():
    b = new_board()
    assert get_valid_moves(b) == list(range(7))
    assert count_fours(b, HUMAN) == 0
    assert not is_full(b)


def test_gravity():
    b, row = drop_piece(new_board(), 3, HUMAN)
    assert row == 5 and b[5][3] == HUMAN
    b, row = drop_piece(b, 3, COMPUTER)
    assert row == 4 and b[4][3] == COMPUTER


def test_no_mutation():
    b = new_board()
    drop_piece(b, 0, HUMAN)
    assert b == new_board()


def test_full_column_rejected():
    b = new_board()
    for i in range(6):
        b, _ = drop_piece(b, 0, HUMAN if i % 2 == 0 else COMPUTER)
    assert 0 not in get_valid_moves(b)
    try:
        drop_piece(b, 0, HUMAN)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_horizontal():
    b = board_from(["......."] * 5 + ["HHHH..."])
    assert count_fours(b, HUMAN) == 1


def test_vertical():
    b = board_from(["......."] * 2 + ["C......"] * 4)
    assert count_fours(b, COMPUTER) == 1


def test_diagonal_down_right():
    b = board_from([
        ".......", ".......",
        "H......", ".H.....", "..H....", "...H...",
    ])
    assert count_fours(b, HUMAN) == 1


def test_diagonal_down_left():
    b = board_from([
        ".......", ".......",
        "...C...", "..C....", ".C.....", "C......",
    ])
    assert count_fours(b, COMPUTER) == 1


def test_overlapping_fours():
    five = board_from(["......."] * 5 + ["HHHHH.."])
    six = board_from(["......."] * 5 + ["HHHHHH."])
    seven = board_from(["......."] * 5 + ["HHHHHHH"])
    assert count_fours(five, HUMAN) == 2
    assert count_fours(six, HUMAN) == 3
    assert count_fours(seven, HUMAN) == 4


def test_winner():
    h = board_from(["......."] * 5 + ["HHHH..."])
    c = board_from(["......."] * 5 + ["CCCC..."])
    assert winner(h) == HUMAN
    assert winner(c) == COMPUTER
    assert winner(new_board()) == 0


def test_new_fours_matches_full_count():
    b = board_from(["......."] * 5 + ["HHHH..."])
    assert new_fours_after_move(b, 5, 3, HUMAN) == 1
    assert new_fours_after_move(b, 5, 0, HUMAN) == 1