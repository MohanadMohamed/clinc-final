import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from desktop.launcher import app_url, main


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
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                app_url(value)

    def test_launcher_only_opens_configured_server(self):
        webview = SimpleNamespace(create_window=Mock(), start=Mock())
        with (
            patch(
                "sys.argv", ["launcher", "--server-url", "https://doctor.clinic.lan"]
            ),
            patch.dict("sys.modules", {"webview": webview}),
        ):
            main()
        webview.create_window.assert_called_once()
        self.assertEqual(
            webview.create_window.call_args.args[1],
            "https://doctor.clinic.lan/app/",
        )
        webview.start.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
