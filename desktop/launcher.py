"""Open the clinic's same-origin web UI in a desktop webview."""

import argparse
import os
import sys
import tomllib
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


def app_url(server_url: str) -> str:
    """Accept only a bare HTTPS server origin; never accept URL credentials."""
    if not isinstance(server_url, str) or any(
        char.isspace() or ord(char) < 32 or char == "\\" for char in server_url
    ):
        raise ValueError("Use a bare HTTPS server origin without credentials")
    try:
        url = urlsplit(server_url)
        port = url.port
    except ValueError:
        # urllib errors can embed malformed netlocs, including supplied secrets.
        raise ValueError("Use a valid bare HTTPS server origin") from None
    if (
        url.scheme != "https"
        or not url.hostname
        or url.username is not None
        or url.password is not None
        or url.path not in ("", "/")
        or url.query
        or url.fragment
        or port == 0
    ):
        raise ValueError("Use a bare HTTPS server origin without credentials")
    return urlunsplit(("https", url.netloc, "/app/", "", ""))


def configured_url(path: Path) -> str:
    """Profiles contain an origin only; never application or database secrets."""
    try:
        with path.open("rb") as stream:
            raw = stream.read(4097)
        if len(raw) > 4096:
            raise ValueError
        data = tomllib.loads(raw.decode("utf-8"))
        if set(data) != {"server_url"}:
            raise ValueError
        return app_url(data["server_url"])
    except (OSError, ValueError, TypeError):
        raise ValueError(
            "Invalid client profile: expected only an HTTPS server_url"
        ) from None


def main() -> None:
    parser = argparse.ArgumentParser(description="Clinic desktop client")
    target = parser.add_mutually_exclusive_group()
    target.add_argument(
        "--server-url",
        help="Doctor PC HTTPS origin; no path, query, or credentials",
    )
    target.add_argument("--config", type=Path, help="Non-secret client TOML profile")
    parser.add_argument(
        "--check-config", action="store_true", help="Validate without opening a GUI"
    )
    args = parser.parse_args()
    try:
        url = (
            configured_url(args.config)
            if args.config
            else app_url(
                args.server_url
                or os.environ.get("CLINIC_SERVER_URL", "https://localhost:8443")
            )
        )
    except ValueError as exc:
        parser.error(str(exc))

    if args.check_config:
        print("PASS: HTTPS client configuration; no server or database started")
        return

    try:
        import webview  # Client-only dependency; never imports the backend.

        webview.settings.update(
            {
                "IGNORE_SSL_ERRORS": False,
                "ALLOW_FILE_URLS": False,
                "ALLOW_DOWNLOADS": False,
                "REMOTE_DEBUGGING_PORT": None,
                "OPEN_DEVTOOLS_IN_DEBUG": False,
            }
        )
        webview.create_window(
            "عيادة المخ والأعصاب والطب النفسي", url, width=1280, height=800
        )
        webview.start(
            gui="edgechromium" if sys.platform == "win32" else None,
            private_mode=True,
            debug=False,
            http_server=False,
        )
    except Exception:  # noqa: BLE001 -- sanitize third-party GUI startup failures
        # No exception details: renderer failures can contain URLs or page data.
        print(
            "Desktop startup failed. Check WebView2/.NET, trusted TLS and server readiness; see desktop/README.md.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
