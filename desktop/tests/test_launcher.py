import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from desktop.launcher import app_url, configured_url, main


class LauncherUrlTests(unittest.TestCase):
    def test_doctor_and_reception_origins(self):
        self.assertEqual(
            app_url("https://localhost:8443"), "https://localhost:8443/app/"
        )
        self.assertEqual(
            app_url("https://doctor.clinic.lan:8443/"),
            "https://doctor.clinic.lan:8443/app/",
        )

    def test_rejects_unsafe_or_ambiguous_urls(self):
        for value in (
            "http://doctor.clinic.lan:8443",
            "https://user:password@doctor.clinic.lan",
            "https://doctor.clinic.lan/other",
            "https://doctor.clinic.lan?token=secret",
            "https://doctor.clinic.lan#fragment",
            "https://doctor.clinic.lan:invalid",
            "https://doctor.clinic.lan:0",
            " https://doctor.clinic.lan",
            "https://doctor.clinic.lan\n",
            "https://doctor\\clinic.lan",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                app_url(value)

    def test_launcher_only_opens_configured_server(self):
        webview = SimpleNamespace(create_window=Mock(), start=Mock(), settings={})
        with (
            patch(
                "sys.argv", ["launcher", "--server-url", "https://doctor.clinic.lan"]
            ),
            patch.dict("sys.modules", {"webview": webview}),
            patch("sys.platform", "win32"),
        ):
            main()
        webview.create_window.assert_called_once()
        self.assertEqual(
            webview.create_window.call_args.args[1],
            "https://doctor.clinic.lan/app/",
        )
        webview.start.assert_called_once_with(
            gui="edgechromium", private_mode=True, debug=False, http_server=False
        )
        self.assertFalse(webview.settings["IGNORE_SSL_ERRORS"])
        self.assertFalse(webview.settings["ALLOW_FILE_URLS"])
        self.assertIsNone(webview.settings["REMOTE_DEBUGGING_PORT"])

    def test_profiles_reject_secrets_and_do_not_echo_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory) / "client.toml"
            for value in (
                'server_url="https://user:SECRET@localhost"',
                'server_url="https://localhost"\npassword="SECRET"',
                "server_url=123",
                "not TOML SECRET",
                "x" * 4097,
            ):
                profile.write_text(value)
                with (
                    self.subTest(value=value[:40]),
                    self.assertRaises(ValueError) as error,
                ):
                    configured_url(profile)
                self.assertNotIn("SECRET", str(error.exception))
            profile.write_text('server_url="https://localhost:8443"')
            self.assertEqual(configured_url(profile), "https://localhost:8443/app/")

    def test_malformed_origin_does_not_echo_credentials(self):
        with self.assertRaises(ValueError) as error:
            app_url("https://user:SECRET@localhost\uff0f")
        self.assertNotIn("SECRET", str(error.exception))

    def test_check_config_does_not_import_renderer(self):
        with (
            patch("sys.argv", ["launcher", "--check-config"]),
            patch.dict("sys.modules", {"webview": None}),
        ):
            main()

    def test_renderer_failure_does_not_print_sensitive_exception(self):
        webview = SimpleNamespace(
            create_window=Mock(side_effect=RuntimeError("SENSITIVE")), settings={}
        )
        with (
            patch("sys.argv", ["launcher"]),
            patch.dict("sys.modules", {"webview": webview}),
            patch("sys.stderr") as stderr,
            self.assertRaises(SystemExit) as error,
        ):
            main()
        self.assertEqual(error.exception.code, 1)
        self.assertNotIn("SENSITIVE", str(stderr.write.call_args_list))


if __name__ == "__main__":
    unittest.main()
