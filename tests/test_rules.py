"""Pruebas de reglas con entradas ficticias."""

import unittest

from password_security_checker.rules import check_length


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
