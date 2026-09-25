"""Arranque reproducible y rechazo de configuraciones de producción inseguras."""

from contextlib import redirect_stderr
from io import StringIO
import unittest
from unittest.mock import patch

from password_security_checker.web.config import Settings
from password_security_checker.web.server import main


PRODUCTION_ENV = {
    "APP_ENV": "production",
    "ALLOWED_HOSTS": "checker.example",
    "PUBLIC_ORIGIN": "https://checker.example",
    "TRUSTED_PROXY_IPS": "127.0.0.1",
}


class SettingsTests(unittest.TestCase):
    def test_safe_development_defaults(self):
        settings = Settings.from_env({})
        self.assertFalse(settings.production)
        self.assertEqual(settings.bind_host, "127.0.0.1")
        self.assertEqual(settings.port, 8000)
        self.assertEqual(settings.allowed_hosts, ("127.0.0.1", "localhost"))
        self.assertEqual(settings.trusted_proxy_ips, ())
        self.assertIsNone(settings.public_origin)

    def test_production_requires_explicit_host_origin_and_proxy(self):
        for field in ("ALLOWED_HOSTS", "PUBLIC_ORIGIN", "TRUSTED_PROXY_IPS"):
            env = PRODUCTION_ENV.copy()
            del env[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                Settings.from_env(env)

    def test_production_settings_and_port(self):
        settings = Settings.from_env({**PRODUCTION_ENV, "PORT": "9010",
                                     "TRUSTED_PROXY_IPS": "10.2.0.0/24,::1"})
        self.assertTrue(settings.production)
        self.assertEqual(settings.bind_host, "0.0.0.0")
        self.assertEqual(settings.port, 9010)
        self.assertEqual(settings.trusted_proxy_ips, ("10.2.0.0/24", "::1/128"))

    def test_invalid_modes_and_development_public_bind_are_rejected(self):
        for env in ({"APP_ENV": "prod"}, {"APP_ENV": ""},
                    {"BIND_HOST": "0.0.0.0"}, {"BIND_HOST": "bad-host"}):
            with self.subTest(env=env), self.assertRaises(ValueError):
                Settings.from_env(env)

    def test_hosts_do_not_allow_wildcards_urls_or_ports(self):
        for host in ("*", "*.example.com", "", "checker.example:443",
                     "https://checker.example", "checker..example", "a/b", "x,y,"):
            with self.subTest(host=host), self.assertRaises(ValueError):
                Settings.from_env({**PRODUCTION_ENV, "ALLOWED_HOSTS": host})

    def test_origin_must_be_https_and_match_a_host(self):
        for origin in ("http://checker.example", "https://other.example",
                       "https://user:secret@checker.example", "https://checker.example/path",
                       "https://checker.example?value=x", "https://checker.example#x",
                       "https://checker.example:0", "https://checker.example:65536"):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                Settings.from_env({**PRODUCTION_ENV, "PUBLIC_ORIGIN": origin})
        settings = Settings.from_env({**PRODUCTION_ENV, "PUBLIC_ORIGIN": "https://checker.example:443/"})
        self.assertEqual(settings.public_origin, "https://checker.example")

    def test_unrestricted_proxy_trust_is_rejected(self):
        for proxies in ("*", "0.0.0.0/0", "::/0", "proxy.example", "127.0.0.1,", ""):
            with self.subTest(proxies=proxies), self.assertRaises(ValueError):
                Settings.from_env({**PRODUCTION_ENV, "TRUSTED_PROXY_IPS": proxies})

    def test_numeric_limits_and_errors_do_not_echo_values(self):
        for name, values in {
            "PORT": ("0", "65536", "not-a-number-marker"),
            "MAX_CONCURRENCY": ("1", "1025", "2.5"),
            "BODY_TIMEOUT_SECONDS": ("0", "31", "nan", "inf"),
        }.items():
            for value in values:
                with self.subTest(name=name, value=value), self.assertRaises(ValueError) as error:
                    Settings.from_env({name: value})
                self.assertNotIn("not-a-number-marker", str(error.exception))

    def test_runner_fixes_logging_and_runtime_controls(self):
        with patch.dict("os.environ", PRODUCTION_ENV, clear=True), patch("uvicorn.run") as run:
            main()
        options = run.call_args.kwargs
        self.assertFalse(options["access_log"])
        self.assertEqual(options["log_level"], "warning")
        self.assertTrue(options["proxy_headers"])
        self.assertEqual(options["forwarded_allow_ips"], "127.0.0.1/32")
        self.assertFalse(options["reload"])
        self.assertEqual(options["workers"], 1)
        self.assertEqual(options["ws"], "none")
        self.assertEqual(options["limit_concurrency"], 64)

    def test_runner_ignores_uvicorn_environment_shortcuts(self):
        env = {"UVICORN_LOG_LEVEL": "trace", "FORWARDED_ALLOW_IPS": "*", "WEB_CONCURRENCY": "8"}
        with patch.dict("os.environ", env, clear=True), patch("uvicorn.run") as run:
            main()
        options = run.call_args.kwargs
        self.assertFalse(options["proxy_headers"])
        self.assertEqual(options["forwarded_allow_ips"], "")
        self.assertEqual(options["log_level"], "warning")
        self.assertEqual(options["workers"], 1)

    def test_runner_fails_without_starting_or_printing_invalid_values(self):
        output = StringIO()
        with patch.dict("os.environ", {"PORT": "config-private-marker"}, clear=True):
            with patch("uvicorn.run") as run, redirect_stderr(output), self.assertRaises(SystemExit):
                main()
        run.assert_not_called()
        self.assertNotIn("config-private-marker", output.getvalue())
