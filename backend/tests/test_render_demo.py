"""Render-specific gates are fail-closed; all records below are synthetic."""

import secrets

import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select

from app.bootstrap import bootstrap
from app.core.config import Settings
from app.demo_db_role import create_app_role
from app.demo_provision import provision_receptionist
from app.main import create_app
from app.models.auth import Throttle
from app.services.auth import COOKIE, digest

ORIGIN = "https://demo.onrender.com"


def demo_settings(database_url, *, enabled=False):
    return Settings(
        _env_file=None,
        database_url=database_url,
        env="production",
        deployment="render_demo",
        public_origin=ORIGIN,
        demo_public_enabled=enabled,
    )


def test_render_mode_rejects_development_and_non_render(monkeypatch, auth_database):
    monkeypatch.delenv("RENDER", raising=False)
    with pytest.raises(ValidationError):
        demo_settings(auth_database)
    monkeypatch.setenv("RENDER", "true")
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url=auth_database,
            env="development",
            deployment="render_demo",
            public_origin="http://127.0.0.1:5173",
        )
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url=auth_database,
            env="production",
            deployment="clinic_lan",
            public_origin=ORIGIN,
        )
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "demo.onrender.com")
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url=auth_database,
            env="production",
            deployment="render_demo",
            public_origin="https://different.onrender.com",
        )


def test_closed_demo_health_only_and_hardened_response(
    monkeypatch, auth_database, tmp_path
):
    monkeypatch.setenv("RENDER", "true")
    (tmp_path / "index.html").write_text("<html>synthetic demo</html>")
    with TestClient(
        create_app(demo_settings(auth_database), frontend_dir=tmp_path),
        base_url=ORIGIN,
    ) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/health/ready").status_code == 200
        for path in ("/app/", "/app/patients", "/api/auth/csrf", "/api/patients"):
            response = client.get(path)
            assert response.status_code == 503
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["x-frame-options"] == "DENY"
            assert (
                "frame-ancestors 'none'" in response.headers["content-security-policy"]
            )
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404
        assert (
            client.get("/api/health", headers={"host": "evil.invalid"}).status_code
            == 400
        )


def test_open_demo_sessions_roles_and_static(
    monkeypatch, auth_db, auth_database, tmp_path
):
    monkeypatch.setenv("RENDER", "true")
    password = secrets.token_urlsafe(24)
    with auth_db() as db:
        bootstrap(db, "synthetic.doctor", password)
        receptionist = provision_receptionist(db, "synthetic.reception", password)
        assert receptionist.role == "receptionist"
        assert receptionist.password_hash != password
        with pytest.raises(ValueError, match="already"):
            provision_receptionist(db, "second.reception", password)
        db.rollback()
    (tmp_path / "index.html").write_text("<html>synthetic demo</html>")
    with TestClient(
        create_app(demo_settings(auth_database, enabled=True), frontend_dir=tmp_path),
        base_url=ORIGIN,
    ) as client:
        client.headers["origin"] = ORIGIN
        assert client.get("/", follow_redirects=False).headers["location"] == "/app/"
        assert client.get("/app", follow_redirects=False).headers["location"] == "/app/"
        assert (
            "synthetic demo"
            in client.get("/app/patients", headers={"accept": "text/html"}).text
        )
        assert client.get("/api/patients").status_code == 401
        assert client.get("/docs").status_code == 404
        csrf = client.get("/api/auth/csrf")
        assert csrf.status_code == 200
        assert COOKIE in csrf.headers["set-cookie"]
        assert all(
            flag in csrf.headers["set-cookie"]
            for flag in ("Secure", "HttpOnly", "SameSite=strict")
        )
        login_body = {"username": "synthetic.reception", "password": password}
        assert client.post("/api/auth/login", json=login_body).status_code == 403
        client.headers["x-csrf-token"] = csrf.json()["csrf_token"]
        assert client.post("/api/auth/login", json=login_body).status_code == 200
        assert client.get("/api/me").json()["role"] == "receptionist"
        for path in ("/api/patients", "/api/appointments", "/api/billing/fees"):
            assert client.get(path).status_code == 200
        assert client.get("/api/visits").status_code == 403
        assert (
            client.get(
                "/api/visits", headers={"x-forwarded-for": "127.0.0.1"}
            ).status_code
            == 403
        )
        client.headers["x-csrf-token"] = client.get("/api/auth/csrf").json()[
            "csrf_token"
        ]
        assert client.post("/api/auth/logout").status_code == 204
        assert client.get("/api/me").status_code == 401
        client.headers["x-csrf-token"] = client.get("/api/auth/csrf").json()[
            "csrf_token"
        ]
        assert (
            client.post(
                "/api/auth/login",
                json={"username": "synthetic.doctor", "password": password},
            ).status_code
            == 200
        )
        assert client.get("/api/visits").status_code == 200
        assert "access-control-allow-origin" not in client.get("/api/me").headers


def test_render_first_forwarded_ip_used_only_for_throttle(
    monkeypatch, auth_db, auth_database
):
    monkeypatch.setenv("RENDER", "true")
    with TestClient(
        create_app(demo_settings(auth_database, enabled=True)), base_url=ORIGIN
    ) as client:
        response = client.get(
            "/api/auth/csrf",
            headers={"origin": ORIGIN, "x-forwarded-for": "203.0.113.8, 10.0.0.2"},
        )
        assert response.status_code == 200
    with auth_db() as db:
        assert (
            db.scalar(
                select(Throttle).where(Throttle.key == digest("csrf:203.0.113.8"))
            )
            is not None
        )


def test_demo_app_role_has_data_grants_without_schema_ownership(auth_database):
    conninfo = auth_database.replace("postgresql+psycopg://", "postgresql://", 1)
    role = "clinic_demo_test_app"
    password = secrets.token_urlsafe(30)
    with psycopg.connect(conninfo) as connection:
        create_app_role(connection, role, password)
    with psycopg.connect(conninfo) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT has_table_privilege(%s, 'users', 'SELECT')", (role,))
            assert cursor.fetchone()[0]
            cursor.execute(
                "SELECT has_table_privilege(%s, 'visits', 'INSERT')", (role,)
            )
            assert cursor.fetchone()[0]
            cursor.execute(
                "SELECT has_table_privilege(%s, 'alembic_version', 'UPDATE')", (role,)
            )
            assert not cursor.fetchone()[0]
            cursor.execute(
                "SELECT has_schema_privilege(%s, 'public', 'CREATE')", (role,)
            )
            assert not cursor.fetchone()[0]
    with psycopg.connect(conninfo, user=role, password=password) as app_connection:
        with app_connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM users")
            assert cursor.fetchone()[0] == 0
