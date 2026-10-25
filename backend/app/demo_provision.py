"""One-time, interactive receptionist provisioning for an isolated Render demo."""

import argparse
import getpass
import re
import sys

from sqlalchemy import select, text

from app.core.config import Settings
from app.core.db import build_engine, build_session_factory
from app.models.auth import User
from app.services.auth import HASHER, audit


def provision_receptionist(db, username: str, password: str) -> User:
    username = username.lower()
    if (
        not re.fullmatch(r"[a-z0-9_.-]{3,64}", username)
        or not 15 <= len(password) <= 128
    ):
        raise ValueError("Use a valid username and a password of 15–128 characters")
    db.execute(text("SELECT pg_advisory_xact_lock(170002)"))
    if db.scalar(select(User.id).where(User.role == "receptionist")):
        raise ValueError("Demo receptionist has already been provisioned")
    user = User(
        username=username,
        password_hash=HASHER.hash(password),
        role="receptionist",
    )
    db.add(user)
    db.flush()
    audit(db, "demo_receptionist_created", user.id)
    db.commit()
    return user


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    args = parser.parse_args()
    if not sys.stdin.isatty():
        sys.exit("Provisioning requires an interactive terminal")
    settings = Settings()
    if settings.deployment != "render_demo" or settings.demo_public_enabled:
        sys.exit("Provision only on a closed Render demo")
    password = getpass.getpass("New receptionist password (15–128 characters): ")
    if password != getpass.getpass("Confirm password: "):
        sys.exit("Passwords did not match")
    engine = None
    try:
        engine = build_engine(settings.database_url.get_secret_value())
        with build_session_factory(engine)() as db:
            provision_receptionist(db, args.username, password)
        print("Demo receptionist created")
    except ValueError as error:
        sys.exit(str(error))
    except Exception:
        sys.exit("Provisioning failed; verify the isolated demo database and grants")
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
