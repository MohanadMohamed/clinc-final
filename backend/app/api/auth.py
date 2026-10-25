import secrets
from ipaddress import ip_address
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.health import get_session
from app.models.auth import User
from app.services.auth import (
    DUMMY_HASH,
    HASHER,
    audit,
    cookie_name,
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


def throttle_client_ip(request: Request) -> str:
    """Use Render's first XFF hop only for throttling, never authorization."""
    peer = request.client.host
    if request.app.state.settings.deployment != "render_demo":
        return peer
    first = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    try:
        return str(ip_address(first))
    except ValueError:
        return peer


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
    session = load_session(
        db, request.cookies.get(cookie_name(request.app.state.settings))
    )
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
    throttle(db, [("csrf:" + throttle_client_ip(request), 60)])
    settings = request.app.state.settings
    session = load_session(db, request.cookies.get(cookie_name(settings)))
    if session:
        token = secrets.token_urlsafe(32)
        session.csrf_hash = digest(token)
    else:
        token = issue(db, response, settings=settings)
    db.commit()
    return {"csrf_token": token}


@router.post("/auth/login", response_model=Me)
def login(data: Login, request: Request, response: Response, db: DB):
    settings = request.app.state.settings
    session = load_session(db, request.cookies.get(cookie_name(settings)))
    csrf_check(request, db, session)
    username = data.username.lower()
    throttle(
        db,
        [("account:" + username, 5), ("login-ip:" + throttle_client_ip(request), 30)],
    )
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
        db, response, user.id, settings=settings
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
    settings = request.app.state.settings
    session = load_session(db, request.cookies.get(cookie_name(settings)))
    if session:
        db.delete(session)
    audit(db, "logout", user.id)
    db.commit()
    response.delete_cookie(
        cookie_name(settings),
        path="/",
        secure=not settings.loopback_http,
        httponly=True,
        samesite="strict",
    )
