"""Tests for the console input helpers in main.py."""

from main import parse_int


def test_parse_int_accepts_plain_digits():
    assert parse_int("4") == 4
    assert parse_int("  12 ") == 12


def test_parse_int_rejects_everything_else_without_crashing():
    for bad in ("", " ", "abc", "-3", "2.5", "\u00b2", "\u0663", "1 2"):
        assert parse_int(bad) is None
