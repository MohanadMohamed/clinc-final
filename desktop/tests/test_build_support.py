"""Verify artifact data boundaries without building a Linux substitute EXE."""

import json
import tempfile
import unittest
from pathlib import Path

from desktop.packaging.build_support import manifest, stage_host


class StagingTests(unittest.TestCase):
    def sources(self, root):
        for name in (
            "backend/app/main.py",
            "backend/migrations/env.py",
            "backend/requirements.txt",
            "backend/alembic.ini",
            "frontend/dist/index.html",
            "frontend/dist/assets/app.js",
            "desktop/packaging/doctor-client.example.toml",
            "desktop/packaging/reception-client.example.toml",
        ):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic build input")

    def test_allowlist_excludes_secrets_data_caches_and_maps(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            self.sources(root)
            for name in (
                ".env",
                "backend/.env",
                "backend/app/.env",
                "backend/app/__pycache__/cache.py",
                "backend/backups/patients.sql",
                "backend/server-key.pem",
                "frontend/dist/.env",
                "frontend/dist/assets/debug.js.map",
                "frontend/dist/records.json",
            ):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("MUST NOT SHIP")
            output = Path(directory) / "output"
            stage_host(root, output)
            manifest(output)
            files = json.loads((output / "SHA256SUMS.json").read_text())
            self.assertIn("doctor-host/frontend/dist/index.html", files)
            self.assertIn("doctor-host/backend/app/main.py", files)
            for path in (output / "doctor-host").rglob("*"):
                if path.is_file():
                    self.assertNotIn("MUST NOT SHIP", path.read_text())
            with self.assertRaises(FileExistsError):
                stage_host(root, output)

    def test_symlinked_inputs_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            self.sources(root)
            outside = Path(directory) / "private"
            outside.write_text("MUST NOT SHIP")
            target = root / "backend/app/linked.py"
            try:
                target.symlink_to(outside)
            except OSError:
                self.skipTest("Symlink creation requires Windows privilege")
            with self.assertRaises(ValueError):
                stage_host(root, Path(directory) / "output")

    def test_unbuilt_frontend_refused(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            stage_host(Path(directory), Path(directory) / "output")
