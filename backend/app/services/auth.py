import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import HTTPException
from sqlalchemy import select, text

from app.models.auth import Audit, LoginSession, Throttle

HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
DUMMY_HASH = HASHER.hash(secrets.token_urlsafe(32))
COOKIE = "__Host-clinic_session"
DEV_COOKIE = "clinic_dev_session"


def cookie_name(settings):
    return DEV_COOKIE if settings.loopback_http else COOKIE


def now():
    return datetime.now(UTC)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def audit(db, event, actor=None):
    db.add(Audit(event=event, actor_id=actor, occurred_at=now()))


def deny(db, status, event, actor=None):
    audit(db, event, actor)
    db.commit()
    raise HTTPException(
        status,
        "Access denied" if status in (401, 403) else "Try again later",
        headers={"Retry-After": "900"} if status == 429 else None,
    )


def throttle(db, keys):
    # Transaction locks serialize each bucket across processes. Order avoids deadlocks.
    for raw, limit in sorted(keys):
        key = digest(raw)
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": key},
        )
        bucket = db.get(Throttle, key)
        if bucket is None:
            bucket = Throttle(key=key, started_at=now(), count=0)
            db.add(bucket)
        elif bucket.started_at + timedelta(minutes=15) <= now():
            bucket.started_at, bucket.count = now(), 0
        if bucket.count >= limit:
            deny(db, 429, "login_throttled")
        bucket.count += 1
        db.flush()


def verify(encoded, password):
    try:
        return HASHER.verify(encoded, password)
    except VerificationError:
        return False


def load_session(db, token):
    if not token or len(token) != 43:
        return None
    session = db.scalar(
        select(LoginSession)
        .where(LoginSession.token_hash == digest(token))
        .with_for_update()
    )
    if session and (
        session.expires_at <= now()
        or session.last_seen + timedelta(minutes=30) <= now()
    ):
        audit(db, "session_expired", session.user_id)
        db.delete(session)
        db.commit()
        return None
    return session


def issue(db, response, user_id=None, *, settings=None):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    seconds = 8 * 3600 if user_id else 300
    db.add(
        LoginSession(
            token_hash=digest(token),
            csrf_hash=digest(csrf),
            user_id=user_id,
            expires_at=now() + timedelta(seconds=seconds),
            last_seen=now(),
        )
    )
    response.set_cookie(
        cookie_name(settings) if settings else COOKIE,
        token,
        max_age=seconds,
        secure=not settings.loopback_http if settings else True,
        httponly=True,
        samesite="strict",
        path="/",
    )
    return csrf
