"""Local interactive bootstrap. No public registration route or password argument."""

import argparse
import getpass
import re
import sys

from sqlalchemy import select, text

from app.core.config import Settings
from app.core.db import build_engine, build_session_factory
from app.models.auth import Bootstrap, User
from app.services.auth import HASHER, audit


def bootstrap(db, username, password):
    username = username.lower()
    if (
        not re.fullmatch(r"[a-z0-9_.-]{3,64}", username)
        or not 15 <= len(password) <= 128
    ):
        raise ValueError("Use a valid username and a password of 15–128 characters")
    db.execute(text("SELECT pg_advisory_xact_lock(170001)"))
    if db.get(Bootstrap, 1) or db.scalar(select(User.id).where(User.role == "doctor")):
        raise ValueError("Doctor bootstrap has already been used")
    user = User(username=username, password_hash=HASHER.hash(password), role="doctor")
    db.add(user)
    db.flush()
    db.add(Bootstrap(id=1))
    audit(db, "doctor_bootstrapped", user.id)
    db.commit()
    return user


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    args = parser.parse_args()
    if not sys.stdin.isatty():
        sys.exit("Bootstrap requires a local interactive terminal")
    password = getpass.getpass("New doctor password (15–128 characters): ")
    if password != getpass.getpass("Confirm password: "):
        sys.exit("Passwords did not match")
    engine = None
    try:
        config = Settings()
        engine = build_engine(config.database_url.get_secret_value())
        with build_session_factory(engine)() as db:
            bootstrap(db, args.username, password)
        print("Initial doctor created")
    except ValueError as error:
        sys.exit(str(error))
    except Exception:
        sys.exit("Bootstrap failed; verify local database configuration and migrations")
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
