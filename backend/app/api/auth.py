import secrets
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.health import get_session
from app.models.auth import User
from app.services.auth import (
    COOKIE,
    DUMMY_HASH,
    HASHER,
    audit,
    deny,
    digest,
    issue,
    load_session,
    now,
    throttle,
    verify,
)

DB = Annotated[Session, Depends(get_session)]
router = APIRouter(prefix="/api")


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: SecretStr = Field(min_length=1, max_length=128)


class Me(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    username: str
    role: Literal["doctor", "receptionist"]


def origin(request, db):
    from urllib.parse import urlsplit

    expected = request.app.state.settings.public_origin
    supplied = request.headers.get("origin")
    if supplied is None and request.method == "GET":
        # Same-origin browser GET fetches commonly omit Origin but send Referer.
        referrer = urlsplit(request.headers.get("referer", ""))
        supplied = f"{referrer.scheme}://{referrer.netloc}"
    if supplied != expected or request.headers.get("sec-fetch-site") == "cross-site":
        deny(db, 403, "csrf_denied")


def csrf_check(request, db, session):
    origin(request, db)
    token = request.headers.get("x-csrf-token", "")
    if (
        not session
        or len(token) != 43
        or not secrets.compare_digest(session.csrf_hash, digest(token))
    ):
        deny(db, 403, "csrf_denied")


def require_user(request: Request, db: DB):
    session = load_session(db, request.cookies.get(COOKIE))
    user = db.get(User, session.user_id) if session and session.user_id else None
    if not user or not user.active:
        if session:
            db.delete(session)
        deny(db, 401, "authentication_denied")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        csrf_check(request, db, session)
    session.last_seen = now()
    request.state.login_session = session
    db.commit()
    return user


def require_role(*roles: Literal["doctor", "receptionist"]):
    if not roles or not set(roles) <= {"doctor", "receptionist"}:
        raise ValueError("Explicit supported roles required")

    def dependency(db: DB, user: Annotated[User, Depends(require_user)]):
        if user.role not in roles:
            deny(db, 403, "authorization_denied", user.id)
        return user

    return dependency


@router.get("/auth/csrf")
def csrf(request: Request, response: Response, db: DB):
    # Origin is required here too, preventing cross-site token churn.
    origin(request, db)
    throttle(db, [("csrf:" + request.client.host, 60)])
    session = load_session(db, request.cookies.get(COOKIE))
    if session:
        token = secrets.token_urlsafe(32)
        session.csrf_hash = digest(token)
    else:
        token = issue(db, response)
    db.commit()
    return {"csrf_token": token}


@router.post("/auth/login", response_model=Me)
def login(data: Login, request: Request, response: Response, db: DB):
    session = load_session(db, request.cookies.get(COOKIE))
    csrf_check(request, db, session)
    username = data.username.lower()
    throttle(db, [("account:" + username, 5), ("login-ip:" + request.client.host, 30)])
    user = db.scalar(select(User).where(User.username == username))
    valid = verify(
        user.password_hash if user else DUMMY_HASH, data.password.get_secret_value()
    )
    if not valid or not user or not user.active:
        deny(db, 401, "login_failed")
    if HASHER.check_needs_rehash(user.password_hash):
        user.password_hash = HASHER.hash(data.password.get_secret_value())
    db.delete(session)
    issue(
        db, response, user.id
    )  # Rotate both secrets; obtain new CSRF via GET afterwards.
    audit(db, "login_succeeded", user.id)
    db.commit()
    return user


@router.get("/me", response_model=Me)
def me(user: Annotated[User, Depends(require_user)]):
    return user


@router.get("/auth/session")
def session_info(request: Request, user: Annotated[User, Depends(require_user)]):
    return {
        "expires_at": request.state.login_session.expires_at,
        "idle_timeout_seconds": 1800,
    }


@router.post("/auth/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    db: DB,
    user: Annotated[User, Depends(require_user)],
):
    session = load_session(db, request.cookies.get(COOKIE))
    if session:
        db.delete(session)
    audit(db, "logout", user.id)
    db.commit()
    response.delete_cookie(
        COOKIE, path="/", secure=True, httponly=True, samesite="strict"
    )
