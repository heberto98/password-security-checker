"""Pruebas de reglas con entradas ficticias."""

import unittest

from password_security_checker.rules import check_character_diversity, check_length


class CheckLengthTests(unittest.TestCase):
    def test_length_boundaries(self):
        cases = [
            ("", (0, False)),
            ("abcdefg", (7, False)),
            ("abcdefgh", (8, True)),
            ("abcdefghi", (9, True)),
        ]
        for password, expected in cases:
            with self.subTest(password=password):
                self.assertEqual(check_length(password, 8), expected)

    def test_minimum_is_configurable(self):
        self.assertEqual(check_length("abc", 3), (3, True))
        self.assertEqual(check_length("abc", 4), (3, False))

    def test_spaces_are_counted(self):
        self.assertEqual(check_length(" a ", 3), (3, True))

    def test_unicode_code_points_are_counted(self):
        self.assertEqual(check_length("ñ🔐", 2), (2, True))
        self.assertEqual(check_length("e\u0301", 2), (2, True))

    def test_non_positive_minimum_is_rejected(self):
        for minimum in (0, -1):
            with self.subTest(minimum=minimum):
                with self.assertRaises(ValueError):
                    check_length("example", minimum)


    def test_non_integer_minimum_is_rejected(self):
        for minimum in (2.5, "8", None, True, False):
            with self.subTest(minimum=minimum):
                with self.assertRaises(TypeError):
                    check_length("example", minimum)


class CheckCharacterDiversityTests(unittest.TestCase):
    def assert_categories(
        self, password, *, lower=False, upper=False, digit=False, symbol=False
    ):
        self.assertEqual(
            check_character_diversity(password),
            {
                "has_lowercase": lower,
                "has_uppercase": upper,
                "has_digit": digit,
                "has_symbol": symbol,
            },
        )

    def test_empty_input(self):
        self.assert_categories("")

    def test_each_category_independently(self):
        self.assert_categories("abc", lower=True)
        self.assert_categories("ABC", upper=True)
        self.assert_categories("123", digit=True)
        self.assert_categories("!_+", symbol=True)

    def test_mixed_categories(self):
        self.assert_categories(
            "Ab3!", lower=True, upper=True, digit=True, symbol=True
        )

    def test_unicode_letters_digits_and_symbols(self):
        self.assert_categories("ñ", lower=True)
        self.assert_categories("Ñ", upper=True)
        self.assert_categories("٣", digit=True)
        self.assert_categories("🔐", symbol=True)

    def test_whitespace_and_controls_are_not_symbols(self):
        self.assert_categories(" \t\n\x00\u200b")

    def test_combining_marks_and_uncased_letters(self):
        self.assert_categories("e\u0301", lower=True)
        self.assert_categories("中")

    def test_non_decimal_numbers_are_not_digits(self):
        self.assert_categories("²½")
