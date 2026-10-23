"""Users, fixed roles, sessions, throttling and authentication audit."""

import sqlalchemy as sa
from alembic import op

revision = "0002_auth"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.CheckConstraint("role IN ('doctor', 'receptionist')", name="valid_role"),
    )
    op.create_index(
        "one_doctor",
        "users",
        ["role"],
        unique=True,
        postgresql_where=sa.text("role = 'doctor'"),
    )
    op.create_table(
        "login_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "auth_throttles",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
    )
    op.create_table(
        "auth_audit",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("event", sa.String(40), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "auth_bootstrap",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.CheckConstraint("id = 1", name="bootstrap_singleton"),
    )
    for table, column in [
        ("login_sessions", "user_id"),
        ("login_sessions", "expires_at"),
        ("auth_throttles", "started_at"),
        ("auth_audit", "actor_id"),
        ("auth_audit", "occurred_at"),
    ]:
        op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade():
    for table in (
        "auth_audit",
        "login_sessions",
        "auth_throttles",
        "auth_bootstrap",
        "users",
    ):
        op.drop_table(table)
