"""Interactive, explicit setup of a NEW isolated Neon synthetic demo database.

Never loads .env, runtime Settings, or a local database URL. No secret arguments.
"""

import argparse
import getpass
import os
import re
import sys
import warnings
from pathlib import Path

import certifi
import psycopg
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from psycopg import sql
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.bootstrap import bootstrap
from app.core.db import Base
from app.demo_db_role import create_app_role, valid_role_name
from app.demo_provision import provision_receptionist
from app.models.auth import User
from app.services.auth import HASHER

BACKEND = Path(__file__).resolve().parents[1]


def validate_target(host: str, database: str, owner: str) -> None:
    if (
        not re.fullmatch(r"ep-[a-z0-9-]+\.(?:[a-z0-9-]+\.)*neon\.tech", host)
        or "-pooler" in host.split(".")[0]
    ):
        raise ValueError("Use the exact Neon DIRECT ep-...neon.tech hostname")
    if not database or not owner or any(c in database + owner for c in "\r\n\x00"):
        raise ValueError("Database and owner role must be explicitly named")


def tls_options() -> dict:
    return {
        "sslmode": "verify-full",
        "sslrootcert": certifi.where(),
        "channel_binding": "require",
        "connect_timeout": 20,
        "options": (
            "-c statement_timeout=120000 -c lock_timeout=10000 "
            "-c timezone=UTC -c search_path=public"
        ),
    }


def migration_config(connection) -> Config:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "migrations"))
    config.attributes["connection"] = connection
    return config


def validate_connection(connection, database: str, owner: str) -> None:
    identity = connection.execute(text("SELECT current_database(), current_user")).one()
    if tuple(identity) != (database, owner):
        raise ValueError(
            "Connected database identity differs from the confirmed target"
        )
    if not connection.execute(
        text("SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()")
    ).scalar_one():
        raise ValueError("The setup connection must use TLS")


def require_empty_database(connection) -> None:
    # Extension-owned objects may be provider defaults; application/user objects
    # anywhere outside system schemas mean this is not a fresh demo target.
    if connection.execute(
        text("""
        SELECT EXISTS (
          SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
          WHERE n.nspname <> 'information_schema' AND n.nspname !~ '^pg_'
          AND NOT EXISTS (SELECT 1 FROM pg_depend d
            WHERE d.classid = 'pg_class'::regclass AND d.objid = c.oid
              AND d.deptype = 'e')
          UNION ALL
          SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
          WHERE n.nspname <> 'information_schema' AND n.nspname !~ '^pg_'
          AND NOT EXISTS (SELECT 1 FROM pg_depend d
            WHERE d.classid = 'pg_proc'::regclass AND d.objid = p.oid
              AND d.deptype = 'e')
          UNION ALL
          SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
          WHERE n.nspname <> 'information_schema' AND n.nspname !~ '^pg_'
          AND t.typtype IN ('d', 'e')
          AND NOT EXISTS (SELECT 1 FROM pg_depend d
            WHERE d.classid = 'pg_type'::regclass AND d.objid = t.oid
              AND d.deptype = 'e')
        )
    """)
    ).scalar_one():
        raise ValueError("Target is not empty; initialize refuses to modify it")


def restrict_role(connection, role: str) -> None:
    raw = connection.connection.driver_connection
    with raw.cursor() as cursor:
        cursor.execute(
            sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(
                sql.Identifier(connection.engine.url.database)
            )
        )
        cursor.execute("REVOKE ALL ON SCHEMA public FROM PUBLIC")
        # Touch only our objects, not Neon-owned extension views/functions.
        for table in (*sorted(Base.metadata.tables), "alembic_version"):
            cursor.execute(
                sql.SQL("REVOKE ALL ON public.{} FROM PUBLIC").format(
                    sql.Identifier(table)
                )
            )
        cursor.execute(
            "REVOKE ALL ON FUNCTION public.clinic_reject_billing_history_change() "
            "FROM PUBLIC"
        )
        cursor.execute(
            sql.SQL("REVOKE ALL ON auth_bootstrap FROM {}").format(sql.Identifier(role))
        )
        cursor.execute(
            sql.SQL("REVOKE INSERT, UPDATE, DELETE ON users FROM {}").format(
                sql.Identifier(role)
            )
        )
        # The login path may rehash a password; it cannot create/change roles.
        cursor.execute(
            sql.SQL("GRANT UPDATE (password_hash) ON users TO {}").format(
                sql.Identifier(role)
            )
        )


def verify_grants(connection, role: str) -> None:
    row = connection.execute(
        text("""
        SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls
        FROM pg_roles WHERE rolname = :role
    """),
        {"role": role},
    ).one()
    if (
        any(row)
        or connection.execute(
            text("""
        SELECT EXISTS (SELECT 1 FROM pg_auth_members m JOIN pg_roles r
          ON r.oid = m.member WHERE r.rolname = :role)
    """),
            {"role": role},
        ).scalar_one()
    ):
        raise ValueError("Application role has elevated attributes or memberships")
    for query in (
        "SELECT has_schema_privilege(:role, 'public', 'CREATE')",
        "SELECT has_database_privilege(:role, current_database(), 'CREATE')",
        "SELECT has_database_privilege(:role, current_database(), 'TEMP')",
        "SELECT has_table_privilege(:role, 'alembic_version', 'UPDATE')",
        "SELECT has_table_privilege(:role, 'alembic_version', 'SELECT')",
        "SELECT has_table_privilege(:role, 'auth_bootstrap', 'INSERT')",
        "SELECT has_table_privilege(:role, 'users', 'INSERT')",
        "SELECT has_table_privilege(:role, 'users', 'DELETE')",
        "SELECT has_column_privilege(:role, 'users', 'role', 'UPDATE')",
        "SELECT EXISTS (SELECT 1 FROM pg_class c JOIN pg_roles r "
        "ON r.oid = c.relowner WHERE r.rolname = :role)",
    ):
        if connection.execute(text(query), {"role": role}).scalar_one():
            raise ValueError(
                "Application role has forbidden DDL/provisioning privileges"
            )
    for table in sorted(Base.metadata.tables):
        if table == "auth_bootstrap":
            continue
        if not connection.execute(
            text("SELECT has_table_privilege(:role, :table, 'SELECT')"),
            {"role": role, "table": table},
        ).scalar_one():
            raise ValueError("Application role is missing runtime read privileges")
        privilege = "UPDATE" if table == "users" else "INSERT"
        query = (
            "SELECT has_column_privilege(:role, :table, 'password_hash', 'UPDATE')"
            if table == "users"
            else "SELECT has_table_privilege(:role, :table, :p)"
        )
        if not connection.execute(
            text(query),
            {
                "role": role,
                "table": table,
                "p": privilege,
            },
        ).scalar_one():
            raise ValueError("Application role is missing runtime write privileges")


def verify_state(connection, role: str, accounts: list[tuple[str, str, str]]) -> None:
    config = migration_config(connection)
    if set(MigrationContext.configure(connection).get_current_heads()) != set(
        ScriptDirectory.from_config(config).get_heads()
    ):
        raise ValueError("Database is not at the repository migration head")
    verify_grants(connection, role)
    with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
        for username, password, expected_role in accounts:
            user = db.scalar(select(User).where(User.username == username.lower()))
            if (
                user is None
                or not user.active
                or user.role != expected_role
                or not HASHER.verify(user.password_hash, password)
            ):
                raise ValueError("Demo account verification failed")


def initialize(connection, role: str, role_password: str, accounts) -> None:
    valid_role_name(role)
    connection.execute(text("SELECT pg_advisory_xact_lock(170003)"))
    require_empty_database(connection)
    command.upgrade(migration_config(connection), "head")
    create_app_role(
        connection.connection.driver_connection, role, role_password, neon=True
    )
    restrict_role(connection, role)
    with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
        bootstrap(db, accounts[0][0], accounts[0][1])
        provision_receptionist(db, accounts[1][0], accounts[1][1])
    verify_state(connection, role, accounts)


def verify_app_login(host, database, role, password) -> None:
    with psycopg.connect(
        host=host,
        port=5432,
        dbname=database,
        user=role,
        password=password,
        **tls_options(),
    ) as connection:
        verify_app_connection(connection, role, database)


def verify_app_connection(connection, role: str, database: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_user, current_database()")
        if cursor.fetchone() != (role, database):
            raise ValueError("Restricted connection identity mismatch")
        for table in sorted(Base.metadata.tables):
            if table != "auth_bootstrap":
                cursor.execute(
                    sql.SQL("SELECT 1 FROM public.{} LIMIT 0").format(
                        sql.Identifier(table)
                    )
                )
        for statement in (
            "CREATE TABLE public.clinic_permission_probe (id integer)",
            "CREATE SCHEMA clinic_permission_probe",
            "UPDATE public.alembic_version SET version_num = version_num",
            "UPDATE public.users SET role = role WHERE false",
            "CREATE ROLE clinic_permission_probe NOLOGIN",
            "DELETE FROM public.auth_bootstrap WHERE false",
        ):
            try:
                with connection.transaction():
                    cursor.execute(statement)
                    # Even unexpected success must roll back the probe.
                    raise ValueError(
                        "Restricted role unexpectedly allowed a forbidden write"
                    )
            except psycopg.errors.InsufficientPrivilege:
                pass
    connection.rollback()


def prompt_password(label: str, minimum: int, *, confirm: bool) -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        password = getpass.getpass(f"{label} (hidden): ")
        if confirm and password != getpass.getpass("Confirm (hidden): "):
            raise ValueError("Passwords did not match")
    if not minimum <= len(password) <= 128:
        raise ValueError(f"Password must contain {minimum}–128 characters")
    return password


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("initialize", "verify"))
    args = parser.parse_args()
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        sys.exit("A private interactive terminal is required; no piped secrets")
    if os.environ.get("RENDER") == "true" or os.environ.get(
        "CLINIC_DEMO_PUBLIC_ENABLED", "false"
    ).lower() not in {"false", "0"}:
        sys.exit("Run locally with the demo exposure gate closed")
    engine = None
    setup_attempted = False
    try:
        host = input("Neon DIRECT hostname (no URL): ").strip()
        database = input("Exact new demo database name: ").strip()
        owner = input("Neon owner role: ").strip()
        validate_target(host, database, owner)
        role = valid_role_name(input("Restricted clinic_demo_... role: ").strip())
        owner_password = prompt_password("Owner database password", 1, confirm=False)
        engine = create_engine(
            URL.create(
                "postgresql+psycopg",
                username=owner,
                password=owner_password,
                host=host,
                port=5432,
                database=database,
            ),
            connect_args=tls_options(),
            poolclass=NullPool,
            hide_parameters=True,
        )
        with engine.connect() as connection:
            validate_connection(connection, database, owner)
            if args.action == "initialize":
                require_empty_database(connection)
            connection.rollback()
            print(
                "PASS: verified TLS and target identity; no local configuration loaded"
            )
            confirmation = f"{args.action.upper()} SYNTHETIC DEMO {host}/{database}"
            if input(f"Type exactly '{confirmation}': ") != confirmation:
                raise ValueError("Target confirmation did not match; nothing changed")
            new = args.action == "initialize"
            role_password = prompt_password(
                "App database role password", 20, confirm=new
            )
            accounts = []
            for kind in ("doctor", "receptionist"):
                name = input(f"Private demo {kind} username: ").strip()
                if not re.fullmatch(r"[A-Za-z0-9_.-]{3,64}", name):
                    raise ValueError("Use a valid account username")
                password = prompt_password(f"Demo {kind} password", 15, confirm=new)
                accounts.append((name, password, kind))
            if len({item[0].lower() for item in accounts}) != 2:
                raise ValueError("Doctor and receptionist usernames must differ")
            if len({role_password, *(item[1] for item in accounts)}) != 3:
                raise ValueError(
                    "Use a different password for each account and DB role"
                )
            with connection.begin():
                if new:
                    setup_attempted = True
                    initialize(connection, role, role_password, accounts)
                else:
                    verify_state(connection, role, accounts)
        verify_app_login(host, database, role, role_password)
        print(
            "PASS: migration head, account hashes/roles, app TLS login, "
            "grants and DDL denial"
        )
        print(
            "This tool never opens a demo gate or deploys Render. No URL was printed."
        )
    except Exception, KeyboardInterrupt:
        message = (
            "Setup transaction was attempted; verify its outcome before any retry. "
            "Use verify; do not blindly initialize again."
            if setup_attempted
            else "Setup/verification stopped; no setup transaction committed. "
            "Check the target, inputs and prerequisites."
        )
        sys.exit(message)
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
