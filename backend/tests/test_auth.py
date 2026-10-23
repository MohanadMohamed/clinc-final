import secrets
from datetime import timedelta
from typing import Annotated

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.auth import require_role
from app.bootstrap import bootstrap
from app.core.config import Settings
from app.main import create_app
from app.models.auth import Audit, Bootstrap, LoginSession, Throttle, User
from app.services.auth import COOKIE, HASHER, digest, now


@pytest.fixture
def auth(auth_db, auth_database):
    password = secrets.token_urlsafe(24)
    with auth_db() as db:
        doctor = bootstrap(db, "synthetic.doctor", password)
        db.add(
            User(
                username="synthetic.reception",
                password_hash=HASHER.hash(password),
                role="receptionist",
            )
        )
        db.commit()
        doctor_id = doctor.id
    app = create_app(Settings(_env_file=None, database_url=auth_database))

    @app.get("/test/doctor")
    def doctor_only(user: Annotated[User, Depends(require_role("doctor"))]):
        return {"role": user.role}

    @app.post("/test/mutation")
    def mutation(user: Annotated[User, Depends(require_role("doctor"))]):
        return {"ok": True}

    with TestClient(app, base_url="https://clinic.local") as client:
        client.headers["origin"] = "https://clinic.local"
        yield client, password, auth_db, doctor_id


def token(client):
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    client.headers["x-csrf-token"] = response.json()["csrf_token"]
    return response


def login(client, password, username="synthetic.doctor"):
    token(client)
    return client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )


def test_session_rotation_logout_and_no_secrets(auth):
    client, password, factory, _ = auth
    assert client.get("/api/me").status_code == 401
    initial = token(client)
    cookie = initial.headers["set-cookie"]
    assert all(
        flag in cookie for flag in ("Secure", "HttpOnly", "SameSite=strict", "Path=/")
    )
    old = client.cookies.get(COOKIE)
    result = client.post(
        "/api/auth/login", json={"username": "synthetic.doctor", "password": password}
    )
    assert result.status_code == 200
    assert set(result.json()) == {"id", "username", "role"}
    current = client.cookies.get(COOKIE)
    assert current != old
    assert client.get("/api/me").json()["role"] == "doctor"
    assert client.get("/api/auth/session").json()["idle_timeout_seconds"] == 1800
    token(client)
    assert client.post("/api/auth/logout").status_code == 204
    client.cookies.set(COOKIE, current)
    assert client.get("/api/me").status_code == 401
    with factory() as db:
        assert db.get(LoginSession, digest(current)) is None
        events = db.scalars(select(Audit.event)).all()
        assert {"doctor_bootstrapped", "login_succeeded", "logout"} <= set(events)
        assert password not in str(events) and current not in str(events)


def test_csrf_and_privilege_escalation(auth):
    client, password, _, _ = auth
    assert (
        client.post(
            "/api/auth/login",
            json={"username": "synthetic.doctor", "password": password},
        ).status_code
        == 403
    )
    token(client)
    client.headers["origin"] = "https://evil.invalid"
    assert (
        client.post(
            "/api/auth/login",
            json={"username": "synthetic.doctor", "password": password},
        ).status_code
        == 403
    )
    client.headers["origin"] = "https://clinic.local"
    response = client.post(
        "/api/auth/login",
        json={"username": "synthetic.doctor", "password": password, "role": "doctor"},
    )
    assert response.status_code == 422 and password not in response.text
    assert login(client, password, "synthetic.reception").status_code == 200
    assert client.get("/test/doctor").status_code == 403
    assert client.post("/api/register", json={"role": "doctor"}).status_code == 404
    assert client.get("/api/me").json()["role"] == "receptionist"
    assert (
        client.post("/api/auth/logout").status_code == 403
    )  # pre-login CSRF is invalid
    token(client)
    assert client.post("/api/auth/logout").status_code == 204


@pytest.mark.parametrize("field", ["expires_at", "last_seen", "disabled"])
def test_expiry_and_disabled_account(auth, field):
    client, password, factory, user_id = auth
    assert login(client, password).status_code == 200
    with factory() as db:
        if field == "disabled":
            db.get(User, user_id).active = False
        else:
            session = db.get(LoginSession, digest(client.cookies.get(COOKIE)))
            setattr(session, field, now() - timedelta(hours=9))
        db.commit()
    assert client.get("/api/me").status_code == 401


def test_throttling_window_and_generic_failure(auth):
    client, password, factory, _ = auth
    token(client)
    for _ in range(5):
        response = client.post(
            "/api/auth/login",
            json={
                "username": "synthetic.doctor",
                "password": secrets.token_urlsafe(16),
            },
        )
        assert response.status_code == 401
    assert (
        client.post(
            "/api/auth/login",
            json={"username": "synthetic.doctor", "password": password},
        ).status_code
        == 429
    )
    with factory() as db:
        for bucket in db.scalars(select(Throttle)):
            bucket.started_at = now() - timedelta(minutes=16)
        db.commit()
    assert (
        client.post(
            "/api/auth/login",
            json={"username": "synthetic.doctor", "password": password},
        ).status_code
        == 200
    )


def test_bootstrap_single_use_and_fixed_roles(auth_db):
    password = secrets.token_urlsafe(24)
    with auth_db() as db:
        user = bootstrap(db, "synthetic.doctor", password)
        assert user.password_hash.startswith("$argon2id$")
        with pytest.raises(ValueError):
            bootstrap(db, "second.doctor", password)
        db.rollback()
        assert db.get(Bootstrap, 1)
        db.add(
            User(username="bad.role", password_hash=HASHER.hash(password), role="admin")
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_unsafe_role_routes_require_csrf(auth):
    client, password, _, _ = auth
    assert login(client, password).status_code == 200
    assert client.post("/test/mutation").status_code == 403
    token(client)
    assert client.post("/test/mutation").status_code == 200
    assert client.get("/api/me").headers["cache-control"] == "no-store"


def test_unknown_user_forged_cookie_and_session_binding(auth):
    client, password, factory, _ = auth
    assert login(client, password, "unknown.account").status_code == 401
    old_csrf = client.headers["x-csrf-token"]
    old_cookie = client.cookies.get(COOKIE)
    assert login(client, password).status_code == 200
    new_cookie = client.cookies.get(COOKIE)
    with factory() as db:
        assert db.get(LoginSession, digest(old_cookie)) is None
        assert new_cookie != db.get(LoginSession, digest(new_cookie)).token_hash
    client.headers["x-csrf-token"] = old_csrf
    assert client.post("/api/auth/logout").status_code == 403
    client.cookies.clear()
    client.cookies.set(COOKIE, old_cookie)
    assert client.get("/api/me").status_code == 401
    client.cookies.set(COOKIE, secrets.token_urlsafe(32))
    assert client.get("/api/me").status_code == 401


def test_parallel_throttle_cannot_bypass_limit(auth_db):
    from concurrent.futures import ThreadPoolExecutor

    from fastapi import HTTPException

    from app.services.auth import throttle

    def attempt(_):
        with auth_db() as db:
            try:
                throttle(db, [("account:synthetic.concurrent", 5)])
                db.commit()
                return 200
            except HTTPException as error:
                return error.status_code

    with ThreadPoolExecutor(max_workers=6) as workers:
        results = list(workers.map(attempt, range(6)))
    assert results.count(200) == 5 and results.count(429) == 1


def test_ip_limit_is_independent_of_username(auth_db):
    from fastapi import HTTPException

    from app.services.auth import throttle

    with auth_db() as db:
        for attempt in range(30):
            throttle(
                db, [(f"account:synthetic.{attempt}", 5), ("login-ip:synthetic", 30)]
            )
            db.commit()
        with pytest.raises(HTTPException) as error:
            throttle(db, [("account:another", 5), ("login-ip:synthetic", 30)])
        assert error.value.status_code == 429


def test_bootstrap_password_policy_and_noninteractive_cli(auth_db):
    import subprocess
    import sys

    with auth_db() as db:
        with pytest.raises(ValueError):
            bootstrap(db, "synthetic.doctor", secrets.token_hex(2))
        assert db.get(Bootstrap, 1) is None
    result = subprocess.run(
        [sys.executable, "-m", "app.bootstrap", "--username", "synthetic.doctor"],
        input="",
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "interactive terminal" in result.stderr


def test_browser_csrf_get_referrer_and_missing_origin_post(auth):
    client, password, _, _ = auth
    del client.headers["origin"]
    assert client.get("/api/auth/csrf").status_code == 403
    client.headers["referer"] = "https://clinic.local/"
    token(client)
    assert (
        client.post(
            "/api/auth/login",
            json={"username": "synthetic.doctor", "password": password},
        ).status_code
        == 403
    )
    client.headers["sec-fetch-site"] = "cross-site"
    assert client.get("/api/auth/csrf").status_code == 403


def test_login_body_is_bounded_without_echo(auth):
    client, _, _, _ = auth
    response = client.post(
        "/api/auth/login",
        content=b"x" * 8193,
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json() == {"detail": "Request too large"}


def test_patient_administration_roles_validation_and_archive(auth):
    client, password, factory, _ = auth
    assert client.get("/api/patients").status_code == 401
    assert login(client, password, "synthetic.reception").status_code == 200
    token(client)
    bad = {"full_name": "", "phone": "12345"}
    assert client.post("/api/patients", json=bad).status_code == 422
    data = {"full_name": "Synthetic Patient", "phone": "+201001234567"}
    created = client.post("/api/patients", json=data)
    assert created.status_code == 201
    patient_id = created.json()["id"]
    assert set(created.json()) == {
        "id",
        "full_name",
        "phone",
        "birth_date",
        "active",
        "created_at",
        "updated_at",
        "archived_at",
    }
    assert client.post("/api/patients", json=data).status_code == 400
    confirmed = client.post("/api/patients", json={**data, "confirm_duplicate": True})
    assert confirmed.status_code == 201
    assert confirmed.json()["id"] != patient_id
    assert (
        client.get(
            "/api/patients", params={"search": "Synthetic", "page_size": 1}
        ).json()["total"]
        == 2
    )
    assert (
        client.get("/api/patients/00000000-0000-0000-0000-000000000000").status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/patients/{patient_id}", json={"diagnosis": "forbidden"}
        ).status_code
        == 422
    )
    assert client.patch(f"/api/patients/{patient_id}", json={}).status_code == 422
    assert (
        client.patch(
            f"/api/patients/{patient_id}", json={"full_name": "Updated Synthetic"}
        ).status_code
        == 200
    )
    assert client.post(f"/api/patients/{patient_id}/archive").status_code == 200
    assert client.post(f"/api/patients/{patient_id}/archive").status_code == 400
    assert (
        client.patch(
            f"/api/patients/{patient_id}", json={"phone": "1234567"}
        ).status_code
        == 400
    )
    assert client.get(f"/api/patients/{patient_id}").json()["active"] is False
    assert client.get("/api/patients").json()["total"] == 1
    from app.models.patient import PatientAudit

    with factory() as db:
        events = db.scalars(
            select(PatientAudit.event).where(PatientAudit.patient_id == patient_id)
        ).all()
        assert events == ["created", "updated", "archived"]
    assert login(client, password).status_code == 200
    assert client.get(f"/api/patients/{patient_id}").status_code == 200
