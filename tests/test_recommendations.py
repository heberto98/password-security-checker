"""Pruebas del flujo de análisis y consejos con datos ficticios."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import unittest
from unittest.mock import patch

from password_security_checker.analyzer import analyze_password
from password_security_checker.recommendations import generate_recommendations


class RecommendationTests(unittest.TestCase):
    def test_short_input_uses_configured_minimum(self):
        messages = generate_recommendations(analyze_password("xQ!", 18))
        self.assertIn("al menos 18 caracteres", messages[0])
        self.assertFalse(any("16 o más" in message for message in messages))

    def test_optional_length_advice_after_meeting_minimum(self):
        messages = generate_recommendations(analyze_password("xQ7!" * 3))
        self.assertIn("16 o más", messages[0])
        self.assertFalse(any("mínimo configurado" in m for m in messages))

    def test_no_length_advice_when_already_long_enough(self):
        messages = generate_recommendations(analyze_password("xQ7!" * 4))
        self.assertFalse(any("Aumenta" in m or "aumentar" in m for m in messages))

    def test_pattern_specific_advice(self):
        cases = [("aaa!xQ7!xQ7!", True, False),
                 ("abc!xQ7!xQ7!", False, True),
                 ("aaa123xQ7!", True, True),
                 ("xQ7!" * 4, False, False)]
        for password, repetition, sequence in cases:
            with self.subTest(password=password):
                messages = generate_recommendations(analyze_password(password))
                self.assertEqual(any("idénticos" in m for m in messages), repetition)
                self.assertEqual(any("secuencias" in m for m in messages), sequence)

    def test_empty_input_has_no_spurious_pattern_advice(self):
        messages = generate_recommendations(analyze_password(""))
        self.assertIn("al menos 12 caracteres", messages[0])
        self.assertFalse(any("idénticos" in m or "secuencias" in m for m in messages))

    def test_general_advice_and_limits_remain_at_high_score(self):
        messages = generate_recommendations(analyze_password("xQ7!" * 5))
        for fragment in ("única", "administrador", "multifactor", "no comprueba"):
            self.assertTrue(any(fragment in message for message in messages))

    def test_no_duplicates_and_stable_order(self):
        result = analyze_password("aaa123bbb456")
        messages = generate_recommendations(result)
        self.assertIsInstance(messages, tuple)
        self.assertEqual(len(messages), len(set(messages)))
        self.assertEqual(messages, generate_recommendations(result))
        self.assertIn("16 o más", messages[0])
        self.assertIn("idénticos", messages[1])
        self.assertIn("secuencias", messages[2])

    def test_diversity_does_not_force_composition_advice(self):
        self.assertEqual(
            generate_recommendations(analyze_password("xq" * 8)),
            generate_recommendations(analyze_password("xQ7!" * 4)),
        )

    def test_full_flow_has_no_output_file_or_network_access(self):
        password = "entrada-ficticia-aaa-123"
        output = StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            with patch("builtins.open", side_effect=AssertionError("File access")):
                with patch("socket.socket", side_effect=AssertionError("Network access")):
                    result = analyze_password(password)
                    messages = generate_recommendations(result)
        self.assertEqual(output.getvalue(), "")
        self.assertNotIn(password, repr(result))
        self.assertNotIn(password, repr(messages))
