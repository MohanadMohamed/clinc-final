"""Verify a new temporary cluster only. Never connect to an existing database."""

import getpass
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.core.config import Settings
from app.core.db import build_engine
from app.main import create_app
from scripts.check_web import check_web


def main():
    pg_bin = Path(os.environ.get("PG_BIN", "/usr/lib/postgresql/18/bin"))
    if not (pg_bin / "initdb").exists():
        sys.exit("NOT TESTED: set PG_BIN to local PostgreSQL binaries")
    with tempfile.TemporaryDirectory(prefix="clinic-0b-") as directory:
        root = Path(directory)
        data = root / "data"
        subprocess.run(
            [
                str(pg_bin / "initdb"),
                "-D",
                str(data),
                "-A",
                "trust",
                "--no-locale",
                "-E",
                "UTF8",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        ctl = [str(pg_bin / "pg_ctl"), "-D", str(data)]
        subprocess.run(
            ctl
            + [
                "-l",
                str(root / "postgres.log"),
                "-o",
                f"-h '' -k {root} -p 55439",
                "-w",
                "start",
            ],
            check=True,
        )
        try:
            # No TCP listener; private temporary socket directory only.
            subprocess.run(
                [
                    str(pg_bin / "createdb"),
                    "-h",
                    str(root),
                    "-p",
                    "55439",
                    "clinic_0b_test",
                ],
                check=True,
            )
            url = f"postgresql+psycopg://{getpass.getuser()}@/clinic_0b_test?host={root}&port=55439"
            env = {
                **os.environ,
                "CLINIC_DATABASE_URL": url,
                "CLINIC_MIGRATION_DATABASE_URL": url,
            }
            alembic = str(Path(sys.executable).parent / "alembic")
            for args in (
                ["upgrade", "head"],
                ["current"],
                ["check"],
                ["downgrade", "base"],
                ["upgrade", "head"],
            ):
                subprocess.run([alembic, *args], check=True, env=env)
            engine = build_engine(url)
            try:
                assert set(inspect(engine).get_table_names()) == {
                    "alembic_version",
                    "users",
                    "login_sessions",
                    "auth_throttles",
                    "auth_audit",
                    "auth_bootstrap",
                }
            finally:
                engine.dispose()
            with TestClient(
                create_app(Settings(_env_file=None, database_url=url))
            ) as client:
                assert client.get("/api/health").status_code == 200
                assert client.get("/api/health/ready").json() == {"status": "ready"}
            check_web(env, root / "web.log")
            print("PASS: baseline round-trip, auth tables only, real DB readiness")
        finally:
            subprocess.run(ctl + ["-m", "fast", "-w", "stop"], check=True)


if __name__ == "__main__":
    main()
