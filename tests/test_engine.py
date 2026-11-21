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



# ---------- Full board and end-of-game tests ----------

def fill_board(pattern):
    """Fill every column by dropping discs; pattern(col, i) gives the player for the i-th disc."""
    b = new_board()
    for col in range(COLS):
        for i in range(ROWS):
            b, _ = drop_piece(b, col, pattern(col, i))
    return b


def test_is_full_false_until_last_disc():
    b = new_board()
    for col in range(COLS):
        for i in range(ROWS):
            assert not is_full(b)            # still room before this drop
            b, _ = drop_piece(b, col, HUMAN if i % 2 == 0 else COMPUTER)
    assert is_full(b)
    assert get_valid_moves(b) == []


def test_tie_when_scores_equal():
    # One horizontal four each, nothing else, so scores are 1-1.
    b = board_from([
        ".......",
        ".......",
        ".......",
        ".......",
        "CCCC...",
        "HHHH...",
    ])
    assert get_scores(b) == (1, 1)
    assert winner(b) == 0


def test_more_fours_wins_even_if_both_scored():
    # Human has 2 fours (five in a row), computer has 1.
    b = board_from([
        ".......",
        ".......",
        ".......",
        ".......",
        "CCCC...",
        "HHHHH..",
    ])
    assert get_scores(b) == (2, 1)
    assert winner(b) == HUMAN



# ---------- Edge cases for counting ----------

def test_full_board_of_one_player_counts_every_window():
    # 24 horizontal + 21 vertical + 12 + 12 diagonal windows = 69
    b = fill_board(lambda col, i: HUMAN)
    assert is_full(b)
    assert count_fours(b, HUMAN) == 69
    assert count_fours(b, COMPUTER) == 0
    assert winner(b) == HUMAN


def test_vertical_five_counts_two():
    b = board_from([
        ".......",
        "C......",
        "C......",
        "C......",
        "C......",
        "C......",
    ])
    assert count_fours(b, COMPUTER) == 2


def test_three_in_a_row_is_not_a_four():
    b = board_from(["......."] * 5 + ["HHH...."])
    assert count_fours(b, HUMAN) == 0


def test_players_are_counted_separately():
    # H and C discs side by side must not be mixed up.
    b = board_from(["......."] * 5 + ["HHHCCCC"])
    assert count_fours(b, HUMAN) == 0
    assert count_fours(b, COMPUTER) == 1


def test_new_fours_after_move_diagonal():
    # A disc at either end of the diagonal sees the same single four.
    b = board_from([
        ".......",
        ".......",
        "...H...",
        "..H....",
        ".H.....",
        "H......",
    ])
    assert new_fours_after_move(b, 2, 3, HUMAN) == 1
    assert new_fours_after_move(b, 5, 0, HUMAN) == 1


def test_new_fours_after_move_ignores_far_fours():
    # The four on the bottom row does not include the disc at (4, 6).
    b = board_from([
        ".......",
        ".......",
        ".......",
        ".......",
        "......H",
        "HHHH...",
    ])
    assert new_fours_after_move(b, 4, 6, HUMAN) == 0