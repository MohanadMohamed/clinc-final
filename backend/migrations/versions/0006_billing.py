"""EGP fees, invoices, cash payments and immutable correction ledger."""

import sqlalchemy as sa
from alembic import op

revision = "0006_billing"
down_revision = "0005_visits"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "fees",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(200), nullable=False),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind IN ('first_visit', 'follow_up') AND amount_minor > 0",
            name="fee_valid",
        ),
    )
    op.create_index("ix_fees_kind", "fees", ["kind"])
    op.create_table(
        "invoices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("idempotency_key", sa.Uuid(), unique=True, nullable=False),
        sa.Column(
            "patient_id", sa.Uuid(), sa.ForeignKey("patients.id"), nullable=False
        ),
        sa.Column("appointment_id", sa.Uuid(), sa.ForeignKey("appointments.id")),
        sa.Column("visit_id", sa.Uuid(), sa.ForeignKey("visits.id")),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("base_minor", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("issued_at", sa.DateTime(timezone=True)),
        sa.Column("voided_at", sa.DateTime(timezone=True)),
        sa.Column("void_reason", sa.String(200)),
        sa.CheckConstraint(
            "kind IN ('first_visit', 'follow_up') AND base_minor > 0",
            name="invoice_base_valid",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'issued', 'void')", name="invoice_status_valid"
        ),
    )
    op.create_index("ix_invoices_patient_id", "invoices", ["patient_id"])
    op.create_index(
        "uq_active_invoice_appointment",
        "invoices",
        ["appointment_id"],
        unique=True,
        postgresql_where=sa.text("appointment_id IS NOT NULL AND status <> 'void'"),
    )
    op.create_index(
        "uq_active_invoice_visit",
        "invoices",
        ["visit_id"],
        unique=True,
        postgresql_where=sa.text("visit_id IS NOT NULL AND status <> 'void'"),
    )
    op.create_table(
        "invoice_adjustments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("idempotency_key", sa.Uuid(), unique=True, nullable=False),
        sa.Column(
            "invoice_id", sa.Uuid(), sa.ForeignKey("invoices.id"), nullable=False
        ),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(200), nullable=False),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("amount_minor <> 0", name="adjustment_nonzero"),
    )
    op.create_index(
        "ix_invoice_adjustments_invoice_id", "invoice_adjustments", ["invoice_id"]
    )
    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("idempotency_key", sa.Uuid(), unique=True, nullable=False),
        sa.Column(
            "invoice_id", sa.Uuid(), sa.ForeignKey("invoices.id"), nullable=False
        ),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("amount_minor > 0", name="payment_positive"),
    )
    op.create_index("ix_payments_invoice_id", "payments", ["invoice_id"])
    op.create_table(
        "payment_reversals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "payment_id",
            sa.Uuid(),
            sa.ForeignKey("payments.id"),
            unique=True,
            nullable=False,
        ),
        sa.Column("reason", sa.String(200), nullable=False),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "billing_audit",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("invoice_id", sa.Uuid(), sa.ForeignKey("invoices.id")),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event", sa.String(32), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.execute(
        """CREATE FUNCTION clinic_reject_billing_history_change() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
          RAISE EXCEPTION 'Billing history is append-only';
        END $$"""
    )
    for table in (
        "fees",
        "invoice_adjustments",
        "payments",
        "payment_reversals",
        "billing_audit",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_preserve_history "
            f"BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION clinic_reject_billing_history_change()"
        )


def downgrade():
    for table in (
        "billing_audit",
        "payment_reversals",
        "payments",
        "invoice_adjustments",
        "invoices",
        "fees",
    ):
        op.drop_table(table)
    op.execute("DROP FUNCTION clinic_reject_billing_history_change()")
