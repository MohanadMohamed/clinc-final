"""Neon operator tooling: synthetic data in disposable local PostgreSQL only."""

import secrets
import sys

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app import neon_setup
from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def empty_demo(auth_database):
    admin_url = make_url(auth_database)
    name = "synthetic_neon_" + secrets.token_hex(6)
    role = "clinic_demo_" + secrets.token_hex(6)
    operator = "synthetic_operator_" + secrets.token_hex(6)
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(
            text(f'CREATE ROLE "{operator}" LOGIN CREATEROLE NOSUPERUSER')
        )
        connection.execute(text(f'CREATE DATABASE "{name}" OWNER "{operator}"'))
    # The initializer must work for a database owner with CREATEROLE, not just
    # a local superuser. Neon-only platform behavior still needs hosted testing.
    engine = create_engine(
        admin_url.set(database=name, username=operator), hide_parameters=True
    )
    try:
        yield engine, role
    finally:
        engine.dispose()
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
            connection.execute(text(f'DROP ROLE IF EXISTS "{role}"'))
            connection.execute(text(f'DROP ROLE "{operator}"'))
        admin.dispose()


def synthetic_accounts():
    return [
        ("synthetic.doctor", secrets.token_urlsafe(24), "doctor"),
        ("synthetic.reception", secrets.token_urlsafe(24), "receptionist"),
    ]


@pytest.mark.parametrize(
    "host",
    [
        "localhost",
        "127.0.0.1",
        "ep-demo-pooler.us-east-2.aws.neon.tech",
        "ep-demo.neon.tech.attacker.invalid",
        "postgresql://ep-demo.neon.tech",
        "ep-demo.neon.tech?sslmode=disable",
        "ep-demo.neon.tech,localhost",
    ],
)
def test_rejects_local_pooler_and_host_injection(host):
    with pytest.raises(ValueError):
        neon_setup.validate_target(host, "synthetic_demo", "owner")


def test_fixed_tls_no_runtime_environment_bypass(monkeypatch):
    neon_setup.validate_target(
        "ep-synthetic.us-east-2.aws.neon.tech", "neondb", "owner"
    )
    assert neon_setup.tls_options()["sslmode"] == "verify-full"
    assert neon_setup.tls_options()["channel_binding"] == "require"
    monkeypatch.delenv("RENDER", raising=False)
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            database_url="postgresql+psycopg://localhost/demo",
            deployment="render_demo",
        )


def test_noninteractive_refused_before_any_connection(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["neon_setup", "initialize"])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(
        neon_setup, "create_engine", lambda *a, **k: pytest.fail("connected")
    )
    with pytest.raises(SystemExit, match="interactive"):
        neon_setup.main()
    assert not capsys.readouterr().out


def test_empty_setup_real_migrations_accounts_and_restricted_role(
    empty_demo,
    monkeypatch,
    caplog,
    capsys,
):
    engine, role = empty_demo
    accounts = synthetic_accounts()
    password = secrets.token_urlsafe(30)
    # Programmatic Alembic must not load .env or use any runtime/local URL.
    monkeypatch.setenv("CLINIC_DATABASE_URL", "not-a-database-url")
    monkeypatch.setenv("CLINIC_DEPLOYMENT", "render_demo")
    monkeypatch.delenv("RENDER", raising=False)
    with engine.begin() as connection:
        neon_setup.initialize(connection, role, password, accounts)
    with engine.begin() as connection:
        neon_setup.verify_state(connection, role, accounts)
        assert (
            connection.execute(text("SELECT count(*) FROM patients")).scalar_one() == 0
        )
        assert (
            connection.execute(text("SELECT count(*) FROM auth_audit")).scalar_one()
            == 2
        )
        assert connection.execute(text("SELECT count(*) FROM users")).scalar_one() == 2
    # Use the actual role in a separate PostgreSQL connection. This private test
    # cluster uses Unix socket trust; Neon TLS/password authentication is separate.
    url = engine.url.set(username=role, password=password, drivername="postgresql")
    with psycopg.connect(url.render_as_string(hide_password=False)) as connection:
        neon_setup.verify_app_connection(connection, role, engine.url.database)
        with connection.cursor() as cursor:
            cursor.execute("UPDATE users SET password_hash = password_hash WHERE false")
    output = caplog.text + capsys.readouterr().out
    for secret in (password, accounts[0][1], accounts[1][1]):
        assert secret not in output
    with engine.begin() as connection:
        with pytest.raises(ValueError, match="not empty"):
            neon_setup.initialize(connection, role, password, accounts)


def test_account_failure_rolls_back_migrations_role_and_first_account(empty_demo):
    engine, role = empty_demo
    accounts = synthetic_accounts()
    accounts[1] = ("bad username", accounts[1][1], "receptionist")
    with pytest.raises(ValueError):
        with engine.begin() as connection:
            neon_setup.initialize(connection, role, secrets.token_urlsafe(30), accounts)
    with engine.connect() as connection:
        neon_setup.require_empty_database(connection)
        assert not connection.execute(
            text("SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :role)"),
            {"role": role},
        ).scalar_one()


def test_restricted_runtime_role_supports_login_csrf_logout_and_clinical_rbac(
    empty_demo,
):
    engine, role = empty_demo
    accounts = synthetic_accounts()
    password = secrets.token_urlsafe(30)
    with engine.begin() as connection:
        neon_setup.initialize(connection, role, password, accounts)
    config = Settings(
        _env_file=None,
        database_url=engine.url.set(username=role, password=password).render_as_string(
            hide_password=False
        ),
        env="production",
        public_origin="https://clinic.local",
    )
    with TestClient(create_app(config), base_url=config.public_origin) as client:
        client.headers["origin"] = config.public_origin
        assert client.get("/api/patients").status_code == 401
        for username, account_password, expected_role in accounts:
            csrf = client.get("/api/auth/csrf")
            client.headers["x-csrf-token"] = csrf.json()["csrf_token"]
            response = client.post(
                "/api/auth/login",
                json={
                    "username": username,
                    "password": account_password,
                },
            )
            assert response.status_code == 200
            assert client.get("/api/me").json()["role"] == expected_role
            assert client.get("/api/patients").status_code == 200
            assert client.get("/api/visits").status_code == (
                200 if expected_role == "doctor" else 403
            )
            client.headers["x-csrf-token"] = client.get("/api/auth/csrf").json()[
                "csrf_token"
            ]
            # The app role can still insert administrative/audit records and
            # invoke billing history triggers without EXECUTE granted on them.
            assert (
                client.post(
                    "/api/patients",
                    json={
                        "full_name": "Synthetic " + expected_role,
                        "phone": "01000000000",
                    },
                ).status_code
                == 201
            )
            assert client.post(
                "/api/billing/fees",
                json={
                    "kind": "first_visit",
                    "amount_minor": 100,
                    "reason": "Synthetic permission test",
                },
            ).status_code == (201 if expected_role == "doctor" else 403)
            assert (
                client.post(
                    "/api/auth/logout",
                    headers={
                        "x-csrf-token": "invalid",
                    },
                ).status_code
                == 403
            )
            client.headers["x-csrf-token"] = client.get("/api/auth/csrf").json()[
                "csrf_token"
            ]
            assert client.post("/api/auth/logout").status_code == 204
            assert client.get("/api/me").status_code == 401


def test_wrong_confirmation_does_not_initialize(empty_demo, monkeypatch, capsys):
    engine, role = empty_demo
    answers = iter(
        [
            "ep-synthetic.us-east-2.aws.neon.tech",
            engine.url.database,
            engine.url.username,
            role,
            "WRONG TARGET",
        ]
    )
    monkeypatch.setattr(sys, "argv", ["neon_setup", "initialize"])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stderr, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(
        neon_setup, "prompt_password", lambda *a, **k: secrets.token_urlsafe(30)
    )
    monkeypatch.setattr(neon_setup, "create_engine", lambda *a, **k: engine)
    monkeypatch.setattr(neon_setup, "validate_connection", lambda *a: None)
    monkeypatch.setattr(neon_setup, "initialize", lambda *a: pytest.fail("mutated"))
    monkeypatch.delenv("RENDER", raising=False)
    with pytest.raises(SystemExit, match="no setup transaction committed"):
        neon_setup.main()
    with engine.connect() as connection:
        neon_setup.require_empty_database(connection)


def test_nonempty_other_schema_refused_without_modification(empty_demo):
    engine, role = empty_demo
    with engine.begin() as connection:
        connection.execute(text("CREATE SCHEMA pgexisting"))
        connection.execute(text("CREATE TABLE pgexisting.keep (id integer)"))
        connection.execute(text("INSERT INTO pgexisting.keep VALUES (7)"))
    with pytest.raises(ValueError, match="not empty"):
        with engine.begin() as connection:
            neon_setup.initialize(
                connection, role, secrets.token_urlsafe(30), synthetic_accounts()
            )
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT id FROM pgexisting.keep")).scalar_one() == 7
        )
