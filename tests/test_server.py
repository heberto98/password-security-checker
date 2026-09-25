"""HTTP real en loopback: simula el tramo interno de un proxy, no certificados TLS."""

import http.client
import json
import os
import socket
import subprocess
import sys
import time
import unittest


MARKER = "fictional-production-marker-7X!"


class ServerTests(unittest.TestCase):
    def start_server(self, health_host="checker.example", **overrides):
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        environment = {
            **os.environ,
            "APP_ENV": "production", "BIND_HOST": "127.0.0.1", "PORT": str(port),
            "ALLOWED_HOSTS": "checker.example", "PUBLIC_ORIGIN": "https://checker.example",
            "TRUSTED_PROXY_IPS": "127.0.0.1", "BODY_TIMEOUT_SECONDS": "0.2",
            "MAX_CONCURRENCY": "64", **overrides,
        }
        environment = {key: value for key, value in environment.items() if value is not None}
        process = subprocess.Popen(
            [sys.executable, "-B", "-m", "password_security_checker.web.server"],
            env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        self.addCleanup(self.stop_and_check_logs, process)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                self.fail("El servidor terminó antes del health check.")
            try:
                status, _, _ = self.request(port, "GET", "/healthz", Host=health_host)
                if status == 200:
                    return port
            except OSError:
                pass
            time.sleep(0.05)
        self.fail("El servidor no arrancó a tiempo.")

    def stop_and_check_logs(self, process):
        if process.poll() is None:
            process.terminate()
        try:
            output, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate(timeout=5)
        self.assertNotIn(MARKER.encode(), output)
        self.assertNotIn(b"Traceback", output)

    def request(self, port, method, path, body=None, **headers):
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        try:
            connection.request(method, path, body=body, headers={"Host": "checker.example", **headers})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_real_proxy_request_serves_ui_and_analysis(self):
        port = self.start_server()
        headers = {"X-Forwarded-Proto": "https", "Origin": "https://checker.example"}
        status, response_headers, body = self.request(port, "GET", "/", **headers)
        self.assertEqual(status, 200)
        self.assertIn(b"Sin historial", body)
        self.assertEqual(response_headers["strict-transport-security"], "max-age=86400")
        self.assertNotIn("server", response_headers)
        for _ in range(2):
            status, response_headers, body = self.request(
                port, "POST", "/api/analyze", json.dumps({"password": MARKER}),
                **headers, **{"Content-Type": "application/json"},
            )
            self.assertEqual(status, 200)
            self.assertEqual(set(json.loads(body)), {"analysis", "recommendations"})
            self.assertNotIn(MARKER.encode(), body)
            self.assertEqual(response_headers["cache-control"], "no-store")

    def test_spoofed_proxy_from_untrusted_peer_is_rejected(self):
        port = self.start_server(TRUSTED_PROXY_IPS="192.0.2.15")
        status, headers, body = self.request(
            port, "POST", "/api/analyze", json.dumps({"password": MARKER}),
            **{"Content-Type": "application/json", "X-Forwarded-Proto": "https"},
        )
        self.assertEqual(status, 400)
        self.assertNotIn("strict-transport-security", headers)
        self.assertNotIn("location", headers)
        self.assertNotIn(MARKER.encode(), body)

    def test_real_errors_and_queries_never_echo_input(self):
        port = self.start_server()
        headers = {"X-Forwarded-Proto": "https", "Content-Type": "application/json"}
        cases = [
            ("POST", "/api/analyze", '{"password":"' + MARKER, 400),
            ("POST", "/api/analyze", json.dumps({"password": [MARKER]}), 422),
            ("POST", "/api/analyze?password=" + MARKER, "{}", 400),
            ("POST", "/api/analyze", "x" * 16385, 413),
            ("GET", "/api/analyze", None, 405),
            ("GET", "/docs", None, 404),
        ]
        for method, path, body, expected in cases:
            with self.subTest(status=expected):
                status, received_headers, received_body = self.request(port, method, path, body, **headers)
                self.assertEqual(status, expected)
                self.assertEqual(received_headers["cache-control"], "no-store")
                self.assertNotIn(MARKER.encode(), received_body)
                self.assertNotIn(MARKER, str(received_headers))

    def test_incomplete_upload_times_out_on_real_connection(self):
        port = self.start_server()
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        self.addCleanup(connection.close)
        connection.putrequest("POST", "/api/analyze", skip_host=True)
        for name, value in {"Host": "checker.example", "X-Forwarded-Proto": "https",
                            "Content-Type": "application/json", "Content-Length": "200"}.items():
            connection.putheader(name, value)
        connection.endheaders()
        connection.send(('{"password":"' + MARKER).encode())
        response = connection.getresponse()
        self.assertEqual(response.status, 408)
        self.assertEqual(response.getheader("cache-control"), "no-store")
        self.assertNotIn(MARKER.encode(), response.read())

    def test_concurrency_limit_rejects_excess_connections(self):
        port = self.start_server(MAX_CONCURRENCY="2", BODY_TIMEOUT_SECONDS="2")
        held = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        self.addCleanup(held.close)
        held.putrequest("POST", "/api/analyze", skip_host=True)
        for name, value in {"Host": "checker.example", "X-Forwarded-Proto": "https",
                            "Content-Type": "application/json", "Content-Length": "200"}.items():
            held.putheader(name, value)
        held.endheaders()
        held.send(('{"password":"' + MARKER).encode())
        status, _, body = self.request(port, "GET", "/healthz")
        self.assertEqual(status, 503)
        self.assertNotIn(MARKER.encode(), body)

    def test_real_render_bootstrap_ignores_wildcard_env_and_forwarding(self):
        host = "checker-test.onrender.com"
        port = self.start_server(
            health_host=host, DEPLOYMENT_TARGET="render-free", RENDER="true",
            RENDER_SERVICE_TYPE="web", RENDER_EXTERNAL_HOSTNAME=host,
            RENDER_EXTERNAL_URL=f"https://{host}", BIND_HOST="0.0.0.0",
            ALLOWED_HOSTS=None, PUBLIC_ORIGIN=None, TRUSTED_PROXY_IPS=None,
            FORWARDED_ALLOW_IPS="*",
        )
        for forwarded in ({}, {"X-Forwarded-Proto": "http", "X-Forwarded-Host": "evil.example",
                               "X-Forwarded-For": "203.0.113.70"}):
            status, headers, body = self.request(
                port, "POST", "/api/analyze", json.dumps({"password": MARKER}),
                Host=host, Origin=f"https://{host}",
                **{"Content-Type": "application/json", **forwarded},
            )
            self.assertEqual(status, 200)
            self.assertEqual(headers["cache-control"], "no-store")
            self.assertEqual(headers["strict-transport-security"], "max-age=86400")
            self.assertNotIn(MARKER.encode(), body)
        status, _, _ = self.request(port, "GET", "/", Host="evil.example",
                                   **{"X-Forwarded-Host": host, "X-Forwarded-Proto": "https"})
        self.assertEqual(status, 400)
