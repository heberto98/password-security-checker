"""Contrato HTTP y privacidad con entradas ficticias, nunca credenciales reales."""

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict
from io import StringIO
import json
import logging
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from password_security_checker.analyzer import analyze_password
from password_security_checker.recommendations import generate_recommendations
from password_security_checker.web.app import app, MAX_BODY_BYTES


class WebTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, base_url="http://127.0.0.1")
        self.addCleanup(self.client.close)

    def assert_private(self, response, marker):
        self.assertNotIn(marker, response.text)
        self.assertNotIn(marker, str(response.headers))
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertNotIn("set-cookie", response.headers)

    def test_home_and_static_assets(self):
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn('lang="es"', home.text)
        self.assertIn('type="password"', home.text)
        for asset, content_type in (("styles.css", "text/css"),
                                    ("app.js", "javascript"),
                                    ("favicon.svg", "image/svg+xml")):
            with self.subTest(asset=asset):
                response = self.client.get("/static/" + asset)
                self.assertEqual(response.status_code, 200)
                self.assertIn(content_type, response.headers["content-type"])
                self.assertEqual(response.headers["cache-control"], "no-store")

    def test_valid_analysis_matches_existing_core(self):
        password = "ficticia-aaa-123-X7!"
        response = self.client.post("/api/analyze", json={"password": password})
        self.assertEqual(response.status_code, 200)
        expected = analyze_password(password)
        self.assertEqual(response.json(), {
            "analysis": asdict(expected),
            "recommendations": list(generate_recommendations(expected)),
        })
        self.assert_private(response, password)

    def test_response_contract_contains_only_results(self):
        response = self.client.post("/api/analyze", json={"password": "xQ7!" * 4})
        data = response.json()
        self.assertEqual(set(data), {"analysis", "recommendations"})
        self.assertEqual(set(data["analysis"]), {
            "length", "minimum_length", "meets_minimum", "diversity",
            "has_repetition", "has_sequence", "score", "level",
        })
        self.assertNotIn("password", response.text)
        self.assertIsInstance(data["analysis"]["score"], int)
        self.assertEqual(set(data["analysis"]["diversity"]), {
            "has_lowercase", "has_uppercase", "has_digit", "has_symbol",
        })

    def test_empty_and_invalid_inputs(self):
        cases = [{}, {"password": ""}, {"password": None}, {"password": 123},
                 {"password": True}, {"password": ["private-marker"]},
                 {"password": {"value": "private-marker"}}, [], None,
                 {"password": "private-marker", "minimum_length": 1},
                 {"private-marker": "value"}]
        for payload in cases:
            with self.subTest(payload_type=type(payload).__name__):
                response = self.client.post(
                    "/api/analyze", content=json.dumps(payload),
                    headers={"content-type": "application/json"},
                )
                self.assertEqual(response.status_code, 422)
                self.assertEqual(set(response.json()), {"error"})
                self.assert_private(response, "private-marker")

    def test_malformed_json_and_encoding_are_sanitized(self):
        for body in (b'{"password":"private-marker"', b'\xffprivate-marker', b''):
            response = self.client.post(
                "/api/analyze", content=body, headers={"content-type": "application/json"}
            )
            self.assertEqual(response.status_code, 400)
            self.assert_private(response, "private-marker")

    def test_deep_json_is_rejected_without_exception_details(self):
        response = self.client.post(
            "/api/analyze", content="[" * 1500 + '"private-marker"' + "]" * 1499,
            headers={"content-type": "application/json"},
        )
        self.assertEqual(response.status_code, 400)
        self.assert_private(response, "private-marker")

    def test_web_length_limits_and_unicode(self):
        for password, status in (("ñ🔐 ", 200), (" " * 3, 200),
                                 ("🔐" * 1024, 200), ("x" * 1025, 422)):
            with self.subTest(length=len(password)):
                response = self.client.post("/api/analyze", json={"password": password})
                self.assertEqual(response.status_code, status)
                if status == 200:
                    self.assertEqual(response.json()["analysis"]["length"], len(password))

    def test_oversized_body_is_rejected_before_analysis(self):
        with patch("password_security_checker.web.app.analyze_password") as analyze:
            response = self.client.post(
                "/api/analyze", content=b"x" * (MAX_BODY_BYTES + 1),
                headers={"content-type": "application/json"},
            )
        self.assertEqual(response.status_code, 413)
        analyze.assert_not_called()

    def test_unsupported_content_type_and_query(self):
        response = self.client.post("/api/analyze", content="private-marker")
        self.assertEqual(response.status_code, 415)
        self.assert_private(response, "private-marker")
        response = self.client.post(
            "/api/analyze?password=private-marker", json={"password": "example"}
        )
        self.assertEqual(response.status_code, 400)
        self.assert_private(response, "private-marker")

    def test_origin_and_host_restrictions(self):
        for origin in ("https://example.com", "null", "http://localhost"):
            response = self.client.post(
                "/api/analyze", json={"password": "example"}, headers={"origin": origin}
            )
            self.assertEqual(response.status_code, 403)
            self.assertNotIn("access-control-allow-origin", response.headers)
        response = self.client.post(
            "/api/analyze", json={"password": "example"},
            headers={"origin": "http://127.0.0.1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/", headers={"host": "evil.example"}).status_code, 400)
        self.assertEqual(self.client.get("/", headers={"host": "localhost"}).status_code, 200)

    def test_fetch_metadata_rejects_cross_site(self):
        response = self.client.post(
            "/api/analyze", json={"password": "example"},
            headers={"sec-fetch-site": "cross-site"},
        )
        self.assertEqual(response.status_code, 403)

    def test_security_headers_on_success_and_error(self):
        for path in ("/", "/not-found", "/api/analyze"):
            response = self.client.get(path)
            self.assertEqual(response.headers["x-content-type-options"], "nosniff")
            self.assertEqual(response.headers["referrer-policy"], "no-referrer")
            self.assertEqual(response.headers["x-frame-options"], "DENY")
            self.assertIn("form-action 'none'", response.headers["content-security-policy"])
            self.assertEqual(response.headers["cache-control"], "no-store")

    def test_no_get_analysis_or_interactive_docs(self):
        self.assertEqual(self.client.get("/api/analyze").status_code, 405)
        for path in ("/docs", "/redoc", "/openapi.json", "/static/missing.js"):
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_multiple_requests_do_not_share_password_or_results(self):
        first = self.client.post("/api/analyze", json={"password": "aaa"})
        second = self.client.post("/api/analyze", json={"password": "xQ7!" * 5})
        self.assertEqual(first.json()["analysis"]["score"], 0)
        self.assertEqual(second.json()["analysis"]["score"], 100)
        self.assertFalse(second.json()["analysis"]["has_repetition"])

    def test_unexpected_errors_do_not_leak_or_log_sensitive_details(self):
        marker = "fictional-private-marker-7X!"
        output = StringIO()
        handler = logging.StreamHandler(output)
        logger = logging.getLogger()
        self.addCleanup(logger.setLevel, logger.level)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)
        for target in ("analyze_password", "generate_recommendations"):
            with self.subTest(target=target):
                with patch("password_security_checker.web.app." + target,
                           side_effect=RuntimeError(marker)):
                    with redirect_stdout(output), redirect_stderr(output):
                        response = self.client.post("/api/analyze", json={"password": marker})
                self.assertEqual(response.status_code, 500)
                self.assert_private(response, marker)
                self.assertNotIn("RuntimeError", response.text)
        self.assertNotIn(marker, output.getvalue())

    def test_valid_and_invalid_bodies_are_not_logged(self):
        marker = "fictional-log-marker-7X!"
        output = StringIO()
        handler = logging.StreamHandler(output)
        logger = logging.getLogger()
        self.addCleanup(logger.setLevel, logger.level)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)
        with redirect_stdout(output), redirect_stderr(output):
            self.client.post("/api/analyze", json={"password": marker})
            self.client.post("/api/analyze", json={"password": [marker]})
            self.client.post("/api/analyze", content=marker,
                             headers={"content-type": "application/json"})
        self.assertNotIn(marker, output.getvalue())
