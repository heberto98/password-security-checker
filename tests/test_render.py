"""Contrato de ingreso exclusivo de Render Free; no requiere cuenta ni red externa."""

from contextlib import redirect_stderr
from io import StringIO
import unittest
from unittest.mock import patch

from fastapi import Request
from fastapi.testclient import TestClient

from password_security_checker.web.app import create_app
from password_security_checker.web.config import Settings
from password_security_checker.web.server import main


RENDER_ENV = {
    "APP_ENV": "production",
    "DEPLOYMENT_TARGET": "render-free",
    "RENDER": "true",
    "RENDER_SERVICE_TYPE": "web",
    "RENDER_EXTERNAL_HOSTNAME": "checker-test.onrender.com",
    "RENDER_EXTERNAL_URL": "https://checker-test.onrender.com",
    "PORT": "10000",
}


class RenderSettingsTests(unittest.TestCase):
    def test_bootstrap_uses_automatic_hostname_origin_and_port(self):
        settings = Settings.from_env(RENDER_ENV)
        self.assertTrue(settings.production)
        self.assertTrue(settings.render_free)
        self.assertEqual(settings.bind_host, "0.0.0.0")
        self.assertEqual(settings.port, 10000)
        self.assertEqual(settings.allowed_hosts, ("checker-test.onrender.com",))
        self.assertEqual(settings.public_origin, "https://checker-test.onrender.com")
        self.assertEqual(settings.trusted_proxy_ips, ())
        self.assertEqual(Settings.from_env({**RENDER_ENV, "PORT": "12345"}).port, 12345)

    def test_render_metadata_does_not_activate_platform_trust_by_itself(self):
        env = {key: value for key, value in RENDER_ENV.items() if key != "DEPLOYMENT_TARGET"}
        with self.assertRaises(ValueError):
            Settings.from_env(env)  # Generic production still needs explicit hosts/proxies.
        self.assertFalse(Settings.from_env({"RENDER": "true"}).render_free)

    def test_requires_production_web_service_and_all_metadata(self):
        for key in ("RENDER", "RENDER_SERVICE_TYPE", "RENDER_EXTERNAL_HOSTNAME",
                    "RENDER_EXTERNAL_URL", "PORT"):
            env = {name: value for name, value in RENDER_ENV.items() if name != key}
            with self.subTest(missing=key), self.assertRaises(ValueError):
                Settings.from_env(env)
        for extra in ({"APP_ENV": "development"}, {"RENDER": "false"},
                      {"RENDER_SERVICE_TYPE": "pserv"}, {"RENDER_SERVICE_TYPE": "static"},
                      {"DEPLOYMENT_TARGET": "render"}, {"BIND_HOST": "127.0.0.1"}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                Settings.from_env({**RENDER_ENV, **extra})

    def test_rejects_non_https_mismatched_or_malformed_platform_identity(self):
        for host, origin in (
            ("checker-test.onrender.com", "http://checker-test.onrender.com"),
            ("checker-test.onrender.com", "https://other.onrender.com"),
            ("checker-test.onrender.com", "https://user:private-marker@checker-test.onrender.com"),
            ("checker-test.onrender.com", "https://checker-test.onrender.com/path"),
            ("checker-test.onrender.com", "https://checker-test.onrender.com?private-marker"),
            ("checker-test.onrender.com", "https://checker-test.onrender.com:8443"),
            ("onrender.com.evil.example", "https://onrender.com.evil.example"),
            ("*.onrender.com", "https://*.onrender.com"),
            ("", ""),
        ):
            with self.subTest(host=host), self.assertRaises(ValueError) as error:
                Settings.from_env({**RENDER_ENV, "RENDER_EXTERNAL_HOSTNAME": host,
                                   "RENDER_EXTERNAL_URL": origin})
            self.assertNotIn("private-marker", str(error.exception))

    def test_no_proxy_allowlist_is_accepted_in_render_mode(self):
        for proxies in ("*", "0.0.0.0/0", "127.0.0.1", "10.0.0.0/8"):
            with self.subTest(proxies=proxies), self.assertRaises(ValueError):
                Settings.from_env({**RENDER_ENV, "TRUSTED_PROXY_IPS": proxies})

    def test_explicit_hosts_and_origin_are_still_validated(self):
        for extra in ({"ALLOWED_HOSTS": "*"}, {"ALLOWED_HOSTS": ""},
                      {"PUBLIC_ORIGIN": ""}, {"PUBLIC_ORIGIN": "http://checker-test.onrender.com"},
                      {"PUBLIC_ORIGIN": "https://foreign.example"},
                      {"ALLOWED_HOSTS": "custom.example", "PUBLIC_ORIGIN": "https://custom.example"}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                Settings.from_env({**RENDER_ENV, **extra})
        settings = Settings.from_env({
            **RENDER_ENV, "ALLOWED_HOSTS": "checker-test.onrender.com,custom.example",
            "PUBLIC_ORIGIN": "https://custom.example",
        })
        self.assertEqual(settings.public_origin, "https://custom.example")

    def test_runner_disables_forwarding_despite_render_python_default(self):
        env = {**RENDER_ENV, "FORWARDED_ALLOW_IPS": "*", "UVICORN_PROXY_HEADERS": "true",
               "UVICORN_LOG_LEVEL": "trace", "WEB_CONCURRENCY": "8"}
        with patch.dict("os.environ", env, clear=True), patch("uvicorn.run") as run:
            main()
        options = run.call_args.kwargs
        self.assertFalse(options["proxy_headers"])
        self.assertEqual(options["forwarded_allow_ips"], "")
        self.assertFalse(options["access_log"])
        self.assertEqual(options["log_level"], "warning")
        self.assertEqual(options["workers"], 1)
        self.assertEqual(options["port"], 10000)

    def test_invalid_render_startup_does_not_leak_environment(self):
        output = StringIO()
        env = {**RENDER_ENV, "RENDER_EXTERNAL_URL": "private-config-marker"}
        with patch.dict("os.environ", env, clear=True), patch("uvicorn.run") as run:
            with redirect_stderr(output), self.assertRaises(SystemExit):
                main()
        run.assert_not_called()
        self.assertNotIn("private-config-marker", output.getvalue())


class RenderRequestTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(Settings.from_env(RENDER_ENV))
        # Simula HTTP interno DESPUÉS de la terminación TLS de la plataforma.
        self.client = TestClient(self.app, base_url="http://checker-test.onrender.com",
                                 client=("192.0.2.50", 4567))
        self.addCleanup(self.client.close)

    def test_internal_http_works_without_forwarded_headers(self):
        response = self.client.post("/api/analyze", json={"password": "aaa123xQ7!"},
                                    headers={"origin": RENDER_ENV["RENDER_EXTERNAL_URL"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["analysis"]["score"], 0)
        self.assertNotIn("aaa123xQ7!", response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["strict-transport-security"], "max-age=86400")
        self.assertNotIn("set-cookie", response.headers)

    def test_forwarding_headers_cannot_change_scheme_client_or_host(self):
        # Endpoint de diagnóstico SOLO en este test, nunca en la aplicación real.
        @self.app.get("/test-scope")
        async def inspect_scope(request: Request):
            return {"scheme": request.url.scheme, "client": request.client.host,
                    "host": request.url.hostname}
        baseline = self.client.get("/test-scope").json()
        for proto in ("http", "https", "https,http", "garbage"):
            response = self.client.get("/test-scope", headers={
                "x-forwarded-proto": proto, "x-forwarded-for": "203.0.113.70",
                "x-forwarded-host": "evil.example",
                "forwarded": "for=203.0.113.70;proto=https;host=evil.example",
            })
            self.assertEqual(response.json(), baseline)
        self.assertEqual(baseline, {"scheme": "http", "client": "192.0.2.50",
                                    "host": "checker-test.onrender.com"})

    def test_spoofed_forwarding_does_not_bypass_host_or_origin(self):
        with patch("password_security_checker.web.app.analyze_password") as analyze:
            response = self.client.post("/api/analyze", json={"password": "private-marker"},
                headers={"host": "evil.example", "x-forwarded-host": "checker-test.onrender.com",
                         "x-forwarded-proto": "https"})
            self.assertEqual(response.status_code, 400)
            for origin in ("http://checker-test.onrender.com", "https://evil.example", "null"):
                response = self.client.post("/api/analyze", json={"password": "private-marker"},
                    headers={"origin": origin, "x-forwarded-proto": "https"})
                self.assertEqual(response.status_code, 403)
            analyze.assert_not_called()

    def test_render_health_uses_public_host_without_proxy_headers(self):
        with patch("password_security_checker.web.app.analyze_password") as analyze:
            response = self.client.get("/healthz")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"status": "ok"})
            self.assertEqual(self.client.head("/healthz").content, b"")
            self.assertEqual(self.client.post("/healthz").status_code, 405)
            self.assertEqual(self.client.get("/healthz", headers={"host": "bad.example"}).status_code, 400)
            analyze.assert_not_called()

    def test_privacy_limits_and_disabled_endpoints_survive_render_mode(self):
        cases = [
            ("POST", "/api/analyze", b'{"password":"private-marker', 400),
            ("POST", "/api/analyze", b'{"password":["private-marker"]}', 422),
            ("POST", "/api/analyze", b"x" * 16385, 413),
            ("GET", "/?password=private-marker", None, 400),
            ("GET", "/docs", None, 404),
            ("GET", "/redoc", None, 404),
            ("GET", "/openapi.json", None, 404),
            ("GET", "/api/analyze", None, 405),
        ]
        for method, path, body, status in cases:
            with self.subTest(path=path, status=status):
                response = self.client.request(method, path, content=body,
                                               headers={"content-type": "application/json"})
                self.assertEqual(response.status_code, status)
                self.assertNotIn("private-marker", response.text + str(response.headers))
                self.assertEqual(response.headers["cache-control"], "no-store")
                self.assertNotIn("unsafe-inline", response.headers["content-security-policy"])
                self.assertNotIn("access-control-allow-origin", response.headers)
