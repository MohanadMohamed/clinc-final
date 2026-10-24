"""The HTTP loopback path uses the same CSRF and role checks as HTTPS."""

import secrets

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.bootstrap import bootstrap
from app.core.config import Settings
from app.main import create_app
from app.models.auth import User
from app.services.auth import DEV_COOKIE, HASHER


@pytest.mark.parametrize("origin", ["http://127.0.0.1:5173", "http://localhost:5173"])
def test_explicit_loopback_settings(auth_database, origin):
    settings = Settings(
        _env_file=None,
        database_url=auth_database,
        env="development",
        public_origin=origin,
    )
    assert settings.loopback_http


@pytest.mark.parametrize(
    "environment,origin",
    [
        ("production", "http://127.0.0.1:5173"),
        ("development", "http://192.168.1.5:5173"),
        ("development", "http://clinic.local:5173"),
        ("development", "http://127.0.0.1:5173/path"),
    ],
)
def test_insecure_settings_rejected(auth_database, environment, origin):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url=auth_database,
            env=environment,
            public_origin=origin,
        )


def test_browser_loopback_login_csrf_logout_and_roles(auth_db, auth_database):
    password = secrets.token_urlsafe(24)
    with auth_db() as db:
        bootstrap(db, "synthetic.doctor", password)
        db.add(
            User(
                username="synthetic.reception",
                role="receptionist",
                password_hash=HASHER.hash(password),
            )
        )
        db.commit()
    settings = Settings(
        _env_file=None,
        database_url=auth_database,
        env="development",
        public_origin="http://127.0.0.1:5173",
    )
    with TestClient(
        create_app(settings),
        base_url="http://127.0.0.1:5173",
        client=("127.0.0.1", 50000),
    ) as client:
        client.headers["referer"] = "http://127.0.0.1:5173/login"
        csrf = client.get("/api/auth/csrf")
        assert csrf.status_code == 200
        assert DEV_COOKIE in csrf.headers["set-cookie"]
        assert "HttpOnly" in csrf.headers["set-cookie"]
        assert "SameSite=strict" in csrf.headers["set-cookie"]
        assert "Secure" not in csrf.headers["set-cookie"]
        client.headers["origin"] = "http://127.0.0.1:5173"
        body = {"username": "synthetic.doctor", "password": password}
        assert client.post("/api/auth/login", json=body).status_code == 403
        client.headers["x-csrf-token"] = csrf.json()["csrf_token"]
        assert (
            client.post(
                "/api/auth/login", json={**body, "password": "wrong"}
            ).status_code
            == 401
        )
        assert client.post("/api/auth/login", json=body).status_code == 200
        assert client.get("/api/me").json()["role"] == "doctor"
        assert client.post("/api/auth/logout").status_code == 403  # rotated CSRF
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
                "/api/auth/login", json={**body, "username": "synthetic.reception"}
            ).status_code
            == 200
        )
        assert client.get("/api/visits").status_code == 403
    with TestClient(
        create_app(settings),
        base_url="http://127.0.0.1:5173",
        client=("192.0.2.5", 50000),
    ) as remote:
        assert remote.get("/api/auth/csrf").status_code == 403
