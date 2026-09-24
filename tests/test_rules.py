"""Pruebas de reglas con entradas ficticias."""

import unittest

from password_security_checker.rules import (
    check_character_diversity,
    check_length,
    has_repeated_characters,
    has_simple_sequence,
)


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


class RepeatedCharactersTests(unittest.TestCase):
    def test_short_inputs_and_threshold(self):
        for password, expected in [("", False), ("a", False), ("aa", False),
                                   ("aaa", True), ("aaaa", True)]:
            with self.subTest(password=password):
                self.assertEqual(has_repeated_characters(password), expected)

    def test_repetition_at_any_position(self):
        for password in ("aaaXY", "XaaaY", "XYaaa"):
            with self.subTest(password=password):
                self.assertTrue(has_repeated_characters(password))

    def test_separated_characters_and_repeated_blocks(self):
        for password in ("aabaa", "ababab", "abcabc"):
            with self.subTest(password=password):
                self.assertFalse(has_repeated_characters(password))

    def test_case_is_significant(self):
        self.assertFalse(has_repeated_characters("aAa"))
        self.assertTrue(has_repeated_characters("AAA"))

    def test_unicode_spaces_and_symbols(self):
        for password in ("ñññ", "🔐🔐🔐", "   ", "!!!"):
            with self.subTest(password=password):
                self.assertTrue(has_repeated_characters(password))

    def test_combining_sequences_are_not_normalized(self):
        self.assertFalse(has_repeated_characters("e\u0301e\u0301e\u0301"))


class SimpleSequenceTests(unittest.TestCase):
    def test_short_inputs(self):
        for password in ("", "a", "ab", "12"):
            with self.subTest(password=password):
                self.assertFalse(has_simple_sequence(password))

    def test_ascending_and_descending_sequences(self):
        for password in ("abc", "xyz", "cba", "zyx", "012", "789",
                         "210", "987", "abcdef", "654321"):
            with self.subTest(password=password):
                self.assertTrue(has_simple_sequence(password))

    def test_case_is_ignored(self):
        for password in ("ABC", "aBc", "CbA"):
            with self.subTest(password=password):
                self.assertTrue(has_simple_sequence(password))

    def test_sequence_at_any_position(self):
        for password in ("abc!X", "!abcX", "!Xabc", "ñ123🔐"):
            with self.subTest(password=password):
                self.assertTrue(has_simple_sequence(password))

    def test_gaps_repetitions_and_direction_changes(self):
        for password in ("a-b-c", "135", "aaa", "aba", "121", "abd"):
            with self.subTest(password=password):
                self.assertFalse(has_simple_sequence(password))

    def test_no_wrapping_or_mixed_categories(self):
        for password in ("890", "901", "109", "zab", "yza", "azy", "89a"):
            with self.subTest(password=password):
                self.assertFalse(has_simple_sequence(password))

    def test_keyboard_patterns_are_out_of_scope(self):
        for password in ("qwerty", "asdf", "!@#"):
            with self.subTest(password=password):
                self.assertFalse(has_simple_sequence(password))

    def test_non_ascii_sequences_are_out_of_scope(self):
        for password in ("αβγ", "١٢٣", "ａｂｃ", "jKl", "ñop"):
            with self.subTest(password=password):
                self.assertFalse(has_simple_sequence(password))
