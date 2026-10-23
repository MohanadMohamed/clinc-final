"""One-doctor appointments with PostgreSQL-enforced half-open exclusion."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ExcludeConstraint

revision = "0004_appointments"
down_revision = "0003_patients"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "appointments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "patient_id", sa.Uuid(), sa.ForeignKey("patients.id"), nullable=False
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("end_at > start_at", name="appointment_positive_interval"),
        sa.CheckConstraint(
            "isfinite(start_at) AND isfinite(end_at)", name="appointment_finite"
        ),
        sa.CheckConstraint(
            "kind IN ('first_visit', 'follow_up')", name="appointment_kind"
        ),
        sa.CheckConstraint(
            "status IN ('scheduled', 'cancelled')", name="appointment_status"
        ),
        ExcludeConstraint(
            (sa.text("tstzrange(start_at, end_at, '[)')"), "&&"),
            using="gist",
            where=sa.text("status = 'scheduled'"),
            name="appointments_no_overlap",
        ),
    )
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"])
    op.create_index("ix_appointments_start_at", "appointments", ["start_at"])
    op.create_table(
        "appointment_audit",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "appointment_id",
            sa.Uuid(),
            sa.ForeignKey("appointments.id"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event", sa.String(16), nullable=False),
        sa.Column("old_start", sa.DateTime(timezone=True)),
        sa.Column("old_end", sa.DateTime(timezone=True)),
        sa.Column("new_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("new_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_appointment_audit_appointment_id", "appointment_audit", ["appointment_id"]
    )
    op.create_index("ix_appointment_audit_actor_id", "appointment_audit", ["actor_id"])


def downgrade():
    op.drop_table("appointment_audit")
    op.drop_table("appointments")
