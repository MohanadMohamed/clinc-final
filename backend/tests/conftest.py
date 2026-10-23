import getpass
import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import text

from app.core.db import build_engine, build_session_factory


@pytest.fixture(scope="session")
def auth_database(tmp_path_factory):
    # Always create a private cluster; never use an environment DB URL.
    root = tmp_path_factory.mktemp("auth-cluster")
    pg = Path(os.environ.get("PG_BIN", "/usr/lib/postgresql/18/bin"))
    if not (pg / "initdb").exists():
        pytest.fail("PostgreSQL binaries required; auth DB tests were NOT TESTED")
    subprocess.run(
        [
            str(pg / "initdb"),
            "-D",
            str(root / "data"),
            "-A",
            "trust",
            "--no-locale",
            "-E",
            "UTF8",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    ctl = [str(pg / "pg_ctl"), "-D", str(root / "data")]
    subprocess.run(
        ctl
        + [
            "-l",
            str(root / "db.log"),
            "-o",
            f"-h '' -k {root} -p 55441",
            "-w",
            "start",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    url = f"postgresql+psycopg://{getpass.getuser()}@/postgres?host={root}&port=55441"
    try:
        env = {
            **os.environ,
            "CLINIC_DATABASE_URL": url,
            "CLINIC_MIGRATION_DATABASE_URL": url,
        }
        alembic = str(Path(__file__).resolve().parents[1] / ".venv/bin/alembic")
        for args in (
            ["upgrade", "head"],
            ["check"],
            ["downgrade", "0001_baseline"],
            ["upgrade", "head"],
            ["check"],
        ):
            subprocess.run([alembic, *args], env=env, check=True)
        yield url
    finally:
        subprocess.run(
            ctl + ["-m", "fast", "-w", "stop"], check=True, stdout=subprocess.DEVNULL
        )


@pytest.fixture
def auth_db(auth_database):
    engine = build_engine(auth_database)
    factory = build_session_factory(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE auth_audit, login_sessions, auth_throttles, "
                "auth_bootstrap, users"
            )
        )
    yield factory
    engine.dispose()
