"""Open the clinic's same-origin web UI in a desktop webview."""

import argparse
import os
from urllib.parse import urlsplit, urlunsplit


def app_url(server_url: str) -> str:
    """Accept only a bare HTTPS server origin; never accept URL credentials."""
    url = urlsplit(server_url)
    try:
        port = url.port
    except ValueError as exc:
        raise ValueError("Invalid server port") from exc
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Clinic desktop client")
    parser.add_argument(
        "--server-url",
        default=os.environ.get("CLINIC_SERVER_URL", "https://localhost:8443"),
        help="Doctor PC HTTPS origin; no path, query, or credentials",
    )
    args = parser.parse_args()
    try:
        url = app_url(args.server_url)
    except ValueError as exc:
        parser.error(str(exc))

    import webview  # Installed for the desktop prototype, never on the server.

    webview.create_window(
        "عيادة المخ والأعصاب والطب النفسي", url, width=1280, height=800
    )
    webview.start()


if __name__ == "__main__":
    main()
