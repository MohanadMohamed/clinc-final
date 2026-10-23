"""Exercise real Vite -> FastAPI -> disposable PostgreSQL requests."""

import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


def check_web(env, log_path):
    for port in (8000, 5173):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", port))  # Refuse to interact with existing servers.
    backend = Path(__file__).resolve().parents[1]
    frontend = backend.parent / "frontend"
    commands = [
        (
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
                "--no-access-log",
            ],
            backend,
        ),
        (["node", "node_modules/vite/bin/vite.js"], frontend),
    ]
    processes = []
    with log_path.open("w") as log:
        try:
            for command, cwd in commands:
                processes.append(
                    subprocess.Popen(
                        command,
                        cwd=cwd,
                        env=env,
                        stdout=log,
                        stderr=log,
                    )
                )
            for url in ("http://127.0.0.1:8000/api/health", "http://127.0.0.1:5173/"):
                for attempt in range(100):
                    if any(p.poll() is not None for p in processes):
                        raise RuntimeError("Development server exited")
                    try:
                        with urlopen(url, timeout=1):
                            break
                    except URLError, TimeoutError:
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Development server startup timed out")
            with urlopen("http://127.0.0.1:5173/", timeout=5) as response:
                html = response.read().decode()
                assert 'lang="ar" dir="rtl"' in html
            for path, status in (("/api/health", "ok"), ("/api/health/ready", "ready")):
                with urlopen(f"http://127.0.0.1:5173{path}", timeout=5) as response:
                    assert json.load(response) == {"status": status}
            print("PASS: real Vite proxy -> FastAPI -> PostgreSQL; Arabic HTML shell")
        finally:
            for process in reversed(processes):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
