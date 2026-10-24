"""Doctor-only visits, immutable revisions and addenda."""

import sqlalchemy as sa
from alembic import op

revision = "0005_visits"
down_revision = "0004_appointments"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "visits",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "patient_id", sa.Uuid(), sa.ForeignKey("patients.id"), nullable=False
        ),
        sa.Column(
            "appointment_id", sa.Uuid(), sa.ForeignKey("appointments.id"), unique=True
        ),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("neurological_note", sa.Text(), nullable=False),
        sa.Column("psychiatric_note", sa.Text(), nullable=False),
        sa.Column("follow_up_plan", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finalized_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('draft', 'finalized')", name="visit_status"),
        sa.CheckConstraint("revision >= 1", name="visit_revision_positive"),
    )
    op.create_index("ix_visits_patient_id", "visits", ["patient_id"])
    op.create_index(
        "ix_visits_patient_created", "visits", ["patient_id", "created_at", "id"]
    )
    op.create_table(
        "visit_revisions",
        sa.Column("visit_id", sa.Uuid(), sa.ForeignKey("visits.id"), primary_key=True),
        sa.Column("revision", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event", sa.String(16), nullable=False),
        sa.Column("neurological_note", sa.Text(), nullable=False),
        sa.Column("psychiatric_note", sa.Text(), nullable=False),
        sa.Column("follow_up_plan", sa.Text(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event IN ('created', 'updated', 'finalized')", name="visit_revision_event"
        ),
    )
    op.create_table(
        "visit_addenda",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("visit_id", sa.Uuid(), sa.ForeignKey("visits.id"), nullable=False),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("length(body) > 0", name="visit_addendum_nonempty"),
    )
    op.create_index("ix_visit_addenda_visit_id", "visit_addenda", ["visit_id"])
    op.create_table(
        "visit_audit",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("visit_id", sa.Uuid(), sa.ForeignKey("visits.id")),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event", sa.String(32), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_visit_audit_visit_id", "visit_audit", ["visit_id"])
    op.create_index("ix_visit_audit_actor_id", "visit_audit", ["actor_id"])
    op.execute(
        """CREATE FUNCTION clinic_reject_visit_history_change() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
          RAISE EXCEPTION 'Visit history is append-only';
        END $$"""
    )
    for table in ("visits", "visit_revisions", "visit_addenda", "visit_audit"):
        operation = "DELETE" if table == "visits" else "UPDATE OR DELETE"
        op.execute(
            f"CREATE TRIGGER {table}_preserve_history BEFORE {operation} ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION clinic_reject_visit_history_change()"
        )
    op.execute(
        """CREATE FUNCTION clinic_protect_finalized_visit() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
          IF OLD.status = 'finalized' THEN
            RAISE EXCEPTION 'Finalized visit cannot be changed';
          END IF;
          RETURN NEW;
        END $$"""
    )
    op.execute(
        "CREATE TRIGGER visits_finalized_guard BEFORE UPDATE ON visits "
        "FOR EACH ROW EXECUTE FUNCTION clinic_protect_finalized_visit()"
    )


def downgrade():
    op.drop_table("visit_audit")
    op.drop_table("visit_addenda")
    op.drop_table("visit_revisions")
    op.drop_table("visits")
    op.execute("DROP FUNCTION clinic_protect_finalized_visit()")
    op.execute("DROP FUNCTION clinic_reject_visit_history_change()")
