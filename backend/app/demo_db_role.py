"""One-time Render demo app role and post-migration grant maintenance."""

import argparse
import getpass
import re
import sys

import psycopg
from psycopg import sql

from app.core.config import Settings
from app.core.db import Base
from app.models import appointment, auth, billing, patient, visit  # noqa: F401


def valid_role_name(role: str) -> str:
    if not re.fullmatch(r"clinic_demo_[a-z0-9_]{3,40}", role):
        raise ValueError("Use a dedicated clinic_demo_ database role name")
    return role


def grant_app_tables(connection: psycopg.Connection, role: str) -> None:
    role = valid_role_name(role)
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database()")
        database_name = cursor.fetchone()[0]
        cursor.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                sql.Identifier(database_name), sql.Identifier(role)
            )
        )
        cursor.execute(
            sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(role))
        )
        for table_name in sorted(Base.metadata.tables):
            cursor.execute(
                sql.SQL(
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.{} TO {}"
                ).format(sql.Identifier(table_name), sql.Identifier(role))
            )
        cursor.execute(
            "SELECT sequence_name FROM information_schema.sequences "
            "WHERE sequence_schema = 'public'"
        )
        for (sequence_name,) in cursor.fetchall():
            cursor.execute(
                sql.SQL("GRANT USAGE, SELECT ON SEQUENCE public.{} TO {}").format(
                    sql.Identifier(sequence_name), sql.Identifier(role)
                )
            )


def create_app_role(
    connection: psycopg.Connection, role: str, password: str, *, neon: bool = False
) -> None:
    role = valid_role_name(role)
    if not 20 <= len(password) <= 128:
        raise ValueError("Use a unique role password of 20–128 characters")
    with connection.cursor() as cursor:
        cursor.execute("SHOW password_encryption")
        if cursor.fetchone()[0] != "scram-sha-256":
            raise ValueError("SCRAM-SHA-256 password encryption is required")
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
        if cursor.fetchone():
            raise ValueError("Demo app role already exists; use --grant-existing")
        # Neon explicitly does not support prehashed role passwords. Its local
        # setup command validates TLS and suppresses SQL/error logging. Ordinary
        # LAN/Render Postgres role setup continues to send only a SCRAM verifier.
        verifier = (
            password
            if neon
            else connection.pgconn.encrypt_password(
                password.encode(), role.encode(), b"scram-sha-256"
            ).decode("ascii")
        )
        cursor.execute(
            sql.SQL(
                "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}"
            ).format(sql.Identifier(role), sql.Literal(verifier))
        )
    grant_app_tables(connection, role)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--create", action="store_true")
    group.add_argument("--grant-existing", action="store_true")
    parser.add_argument("--role", required=True)
    args = parser.parse_args()
    if not sys.stdin.isatty():
        sys.exit("Role management requires an interactive terminal")
    settings = Settings()
    if settings.deployment != "render_demo" or settings.demo_public_enabled:
        sys.exit("Manage grants only on a closed Render demo")
    try:
        role = valid_role_name(args.role)
    except ValueError as error:
        sys.exit(str(error))
    password = None
    if args.create:
        password = getpass.getpass("Unique app DB role password (20–128 characters): ")
        if password != getpass.getpass("Confirm app DB role password: "):
            sys.exit("Passwords did not match")
    secret = (
        settings.migration_database_url or settings.database_url
    ).get_secret_value()
    if not secret.startswith("postgresql+psycopg://"):
        sys.exit("The migration URL must use postgresql+psycopg")
    try:
        with psycopg.connect(
            secret.replace("postgresql+psycopg://", "postgresql://", 1)
        ) as connection:
            if args.create:
                create_app_role(connection, role, password)
            else:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
                    if not cursor.fetchone():
                        raise ValueError("Demo app role does not exist")
                grant_app_tables(connection, role)
        print("Demo app role and grants ready")
    except ValueError as error:
        sys.exit(str(error))
    except Exception:
        sys.exit(
            "Role setup failed; verify the isolated demo database and admin grants"
        )


if __name__ == "__main__":
    main()
