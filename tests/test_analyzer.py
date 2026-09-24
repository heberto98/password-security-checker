"""Pruebas del análisis integrado con entradas exclusivamente ficticias."""

from dataclasses import FrozenInstanceError, asdict
import unittest

from password_security_checker.analyzer import analyze_password
from password_security_checker.models import CharacterDiversity, StrengthLevel


class AnalyzerTests(unittest.TestCase):
    def test_empty_input(self):
        result = analyze_password("")
        self.assertEqual(result.length, 0)
        self.assertEqual(result.score, 0)
        self.assertEqual(result.level, StrengthLevel.LOW)
        self.assertFalse(result.meets_minimum)
        self.assertFalse(result.has_repetition)
        self.assertFalse(result.has_sequence)

    def test_minimum_and_level_boundaries(self):
        cases = [(7, 35, StrengthLevel.LOW), (8, 39, StrengthLevel.LOW),
                 (11, 39, StrengthLevel.LOW), (12, 60, StrengthLevel.MEDIUM),
                 (13, 65, StrengthLevel.MEDIUM), (14, 70, StrengthLevel.HIGH),
                 (20, 100, StrengthLevel.HIGH), (24, 100, StrengthLevel.HIGH)]
        for length, score, level in cases:
            with self.subTest(length=length):
                result = analyze_password(("xQ7!" * 6)[:length])
                self.assertEqual(result.score, score)
                self.assertEqual(result.level, level)
                self.assertEqual(result.meets_minimum, length >= 12)

    def test_custom_minimum(self):
        result = analyze_password("xQ7!xQ7!", minimum_length=8)
        self.assertEqual(result.minimum_length, 8)
        self.assertTrue(result.meets_minimum)
        self.assertEqual(result.score, 40)
        self.assertEqual(result.level, StrengthLevel.MEDIUM)
        self.assertEqual(analyze_password("xQ7!" * 5, 21).score, 39)

    def test_each_pattern_lowers_score(self):
        for password in ("aaa" + "xQ7!" * 3, "abc" + "xQ7!" * 3):
            with self.subTest(password=password):
                self.assertEqual(analyze_password(password).score, 50)

    def test_patterns_are_penalized_once_each(self):
        result = analyze_password("aaa!bbb!ccc!ddd!")
        self.assertTrue(result.has_repetition)
        self.assertFalse(result.has_sequence)
        self.assertEqual(result.score, 55)

    def test_both_patterns_and_score_floor(self):
        result = analyze_password("aaa123" + "xQ7!" * 2)
        self.assertTrue(result.has_repetition)
        self.assertTrue(result.has_sequence)
        self.assertEqual(result.score, 20)
        self.assertEqual(analyze_password("aaa123").score, 0)

    def test_long_patterned_inputs_cannot_reach_high_level(self):
        for password in ("a" * 1000, "abc" + "xQ7!" * 250):
            with self.subTest(pattern=password[:3]):
                result = analyze_password(password)
                self.assertEqual(result.score, 69)
                self.assertEqual(result.level, StrengthLevel.MEDIUM)

    def test_diversity_is_reported_without_bonus(self):
        self.assertEqual(
            analyze_password("ñQ3!").diversity,
            CharacterDiversity(True, True, True, True),
        )
        self.assertEqual(analyze_password("xq" * 6).score,
                         analyze_password("xQ7!" * 3).score)

    def test_unicode_and_spaces_are_preserved_in_length(self):
        self.assertEqual(analyze_password(" ñ🔐 ").length, 4)
        self.assertEqual(analyze_password("e\u0301").length, 2)

    def test_invalid_inputs(self):
        for password in (None, 123, b"example", ["x"]):
            with self.subTest(input_type=type(password).__name__):
                with self.assertRaises(TypeError):
                    analyze_password(password)
        for minimum in (True, 2.5, "12", None):
            with self.assertRaises(TypeError):
                analyze_password("example", minimum)
        for minimum in (0, -1):
            with self.assertRaises(ValueError):
                analyze_password("example", minimum)

    def test_result_is_immutable_and_contains_no_password(self):
        password = "ficticia-X7!entrada"
        result = analyze_password(password)
        self.assertNotIn(password, repr(result))
        self.assertNotIn("password", asdict(result))
        self.assertEqual(result, analyze_password(password))
        with self.assertRaises(FrozenInstanceError):
            result.score = 100
        with self.assertRaises(FrozenInstanceError):
            result.diversity.has_digit = False

    def test_calls_do_not_share_results(self):
        first = analyze_password("aaa")
        second = analyze_password("xQ7!" * 5)
        self.assertTrue(first.has_repetition)
        self.assertFalse(second.has_repetition)
        self.assertEqual(first.score, 0)
        self.assertEqual(second.score, 100)
