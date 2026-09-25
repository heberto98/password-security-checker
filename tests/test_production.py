"""Controles de producción, frontera del proxy y lectura acotada de cuerpos."""

import asyncio
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from password_security_checker.web.app import create_app, MAX_BODY_BYTES
from password_security_checker.web.config import Settings


def production_settings():
    return Settings.from_env({
        "APP_ENV": "production", "ALLOWED_HOSTS": "checker.example",
        "PUBLIC_ORIGIN": "https://checker.example", "TRUSTED_PROXY_IPS": "127.0.0.1",
    })


class ProductionTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(production_settings())
        self.client = TestClient(self.app, base_url="https://checker.example")
        self.addCleanup(self.client.close)

    def test_https_analysis_keeps_core_behavior_and_privacy(self):
        response = self.client.post("/api/analyze", json={"password": "aaa123xQ7!"},
                                    headers={"origin": "https://checker.example"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["analysis"]["score"], 0)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["strict-transport-security"], "max-age=86400")
        self.assertNotIn("aaa123xQ7!", response.text)
        self.assertNotIn("set-cookie", response.headers)

    def test_http_is_rejected_without_reading_or_redirecting_sensitive_body(self):
        with patch("password_security_checker.web.app.analyze_password") as analyze:
            response = self.client.post("http://checker.example/api/analyze",
                                        json={"password": "fictional-marker"})
        analyze.assert_not_called()
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("location", response.headers)
        self.assertNotIn("strict-transport-security", response.headers)
        self.assertNotIn("fictional-marker", response.text)

    def test_health_is_cheap_and_available_to_internal_http_probes(self):
        with patch("password_security_checker.web.app.analyze_password") as analyze:
            response = self.client.get("http://checker.example/healthz")
        analyze.assert_not_called()
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(self.client.head("/healthz").content, b"")
        self.assertEqual(self.client.post("/healthz").status_code, 405)
        self.assertEqual(self.client.get("/healthz", headers={"host": "other.example"}).status_code, 400)

    def test_untrusted_forwarded_headers_do_not_enable_https(self):
        wrapped = ProxyHeadersMiddleware(self.app, trusted_hosts=["127.0.0.1"])
        with TestClient(wrapped, base_url="http://checker.example", client=("192.0.2.20", 1000)) as client:
            response = client.post("/api/analyze", json={"password": "fictional-marker"},
                                   headers={"x-forwarded-proto": "https"})
        self.assertEqual(response.status_code, 400)

    def test_only_trusted_proxy_can_supply_scheme_and_must_preserve_host(self):
        wrapped = ProxyHeadersMiddleware(self.app, trusted_hosts=["127.0.0.1"])
        with TestClient(wrapped, base_url="http://checker.example", client=("127.0.0.1", 1000)) as client:
            headers = {"x-forwarded-proto": "https", "origin": "https://checker.example"}
            response = client.post("/api/analyze", json={"password": "fictional-marker"}, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertIn("strict-transport-security", response.headers)
            response = client.post("/api/analyze", json={"password": "fictional-marker"},
                                   headers={**headers, "host": "evil.example", "x-forwarded-host": "checker.example"})
            self.assertEqual(response.status_code, 400)

    def test_origin_is_exact_and_cors_is_not_enabled(self):
        for origin in ("http://checker.example", "https://checker.example:8443",
                       "https://other.example", "null"):
            with self.subTest(origin=origin):
                response = self.client.post("/api/analyze", json={"password": "example"},
                                            headers={"origin": origin})
                self.assertEqual(response.status_code, 403)
                self.assertNotIn("access-control-allow-origin", response.headers)
        preflight = self.client.options("/api/analyze", headers={
            "origin": "https://other.example", "access-control-request-method": "POST"})
        self.assertEqual(preflight.status_code, 405)
        self.assertNotIn("access-control-allow-origin", preflight.headers)

    def test_no_redirects_or_reflection_of_queries(self):
        for path in ("/?password=fictional-marker", "/api/analyze/?password=fictional-marker",
                     "/static?password=fictional-marker", "/healthz?password=fictional-marker"):
            response = self.client.get(path, follow_redirects=False)
            self.assertEqual(response.status_code, 400)
            self.assertNotIn("fictional-marker", response.text + str(response.headers))
            self.assertNotIn("location", response.headers)
        self.assertEqual(self.client.post("/api/analyze/", follow_redirects=False).status_code, 404)

    def test_minimal_public_surface_and_security_headers(self):
        for path, status in (("/", 200), ("/static/app.js", 200), ("/docs", 404),
                             ("/redoc", 404), ("/openapi.json", 404), ("/missing", 404)):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.headers["cache-control"], "no-store")
                self.assertEqual(response.headers["x-frame-options"], "DENY")
                self.assertEqual(response.headers["referrer-policy"], "no-referrer")
                csp = response.headers["content-security-policy"]
                self.assertIn("connect-src 'self'", csp)
                self.assertNotIn("unsafe-inline", csp)
                self.assertIn("strict-transport-security", response.headers)
        for method in ("GET", "HEAD", "PUT", "PATCH", "DELETE", "TRACE"):
            self.assertEqual(self.client.request(method, "/api/analyze").status_code, 405)

    def test_hsts_is_not_sent_in_development(self):
        with TestClient(create_app(Settings.from_env({})), base_url="http://localhost") as client:
            self.assertNotIn("strict-transport-security", client.get("/").headers)
            self.assertEqual(client.get("/healthz").json(), {"status": "ok"})

    def test_errors_do_not_include_input_and_keep_headers(self):
        marker = "production-private-marker"
        with patch("password_security_checker.web.app.analyze_password", side_effect=RuntimeError(marker)):
            response = self.client.post("/api/analyze", json={"password": marker})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn(marker, response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertIn("strict-transport-security", response.headers)

    def test_compressed_and_declared_oversized_bodies_are_rejected(self):
        response = self.client.post("/api/analyze", content=b"not-gzip", headers={
            "content-type": "application/json", "content-encoding": "gzip"})
        self.assertEqual(response.status_code, 415)
        response = self.client.post("/api/analyze", content=b"{}", headers={
            "content-type": "application/json", "content-length": str(MAX_BODY_BYTES + 1)})
        self.assertEqual(response.status_code, 413)


class BodyReadingTests(unittest.IsolatedAsyncioTestCase):
    async def request_chunks(self, chunks, delay=0):
        timeout = 0.02 if delay else 5
        application = create_app(replace(production_settings(), body_timeout_seconds=timeout))
        messages = []
        iterator = iter(chunks)

        async def receive():
            if delay:
                await asyncio.sleep(delay)
            try:
                return next(iterator)
            except StopIteration:
                await asyncio.Future()

        async def send(message):
            messages.append(message)

        scope = {
            "type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1", "method": "POST", "scheme": "https",
            "path": "/api/analyze", "raw_path": b"/api/analyze", "query_string": b"",
            "root_path": "", "headers": [(b"host", b"checker.example"),
                                           (b"content-type", b"application/json")],
            "client": ("127.0.0.1", 1000), "server": ("checker.example", 443),
        }
        await application(scope, receive, send)
        status = next(message["status"] for message in messages if message["type"] == "http.response.start")
        body = b"".join(message.get("body", b"") for message in messages)
        return status, body

    async def test_chunked_body_without_content_length_cannot_bypass_limit(self):
        chunks = [{"type": "http.request", "body": b"x" * MAX_BODY_BYTES, "more_body": True},
                  {"type": "http.request", "body": b"x", "more_body": False}]
        with patch("password_security_checker.web.app.analyze_password") as analyze:
            status, _ = await self.request_chunks(chunks)
        self.assertEqual(status, 413)
        analyze.assert_not_called()

    async def test_slow_body_times_out_without_analysis(self):
        with patch("password_security_checker.web.app.analyze_password") as analyze:
            status, body = await self.request_chunks([], delay=0.05)
        self.assertEqual(status, 408)
        self.assertEqual(set(json.loads(body)), {"error"})
        analyze.assert_not_called()

    async def test_valid_fragmented_json_is_accepted(self):
        chunks = [{"type": "http.request", "body": b'{"password":', "more_body": True},
                  {"type": "http.request", "body": b'"aaa123xQ7!"}', "more_body": False}]
        status, body = await self.request_chunks(chunks)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["analysis"]["score"], 0)
        self.assertNotIn(b"aaa123xQ7!", body)
