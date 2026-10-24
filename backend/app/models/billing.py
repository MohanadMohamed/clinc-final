import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Fee(Base):
    __tablename__ = "fees"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(16), index=True)
    amount_minor: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(200))
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    __table_args__ = (
        CheckConstraint(
            "kind IN ('first_visit', 'follow_up') AND amount_minor > 0",
            name="fee_valid",
        ),
    )


class Invoice(Base):
    __tablename__ = "invoices"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    idempotency_key: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("appointments.id")
    )
    visit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("visits.id"))
    kind: Mapped[str] = mapped_column(String(16))
    base_minor: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    void_reason: Mapped[str | None] = mapped_column(String(200))
    __table_args__ = (
        CheckConstraint(
            "kind IN ('first_visit', 'follow_up') AND base_minor > 0",
            name="invoice_base_valid",
        ),
        CheckConstraint(
            "status IN ('draft', 'issued', 'void')", name="invoice_status_valid"
        ),
        Index(
            "uq_active_invoice_appointment",
            "appointment_id",
            unique=True,
            postgresql_where=text("appointment_id IS NOT NULL AND status <> 'void'"),
        ),
        Index(
            "uq_active_invoice_visit",
            "visit_id",
            unique=True,
            postgresql_where=text("visit_id IS NOT NULL AND status <> 'void'"),
        ),
    )


class InvoiceAdjustment(Base):
    __tablename__ = "invoice_adjustments"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    idempotency_key: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"), index=True)
    amount_minor: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(200))
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    __table_args__ = (CheckConstraint("amount_minor <> 0", name="adjustment_nonzero"),)


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    idempotency_key: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"), index=True)
    amount_minor: Mapped[int] = mapped_column(Integer)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    __table_args__ = (CheckConstraint("amount_minor > 0", name="payment_positive"),)


class PaymentReversal(Base):
    __tablename__ = "payment_reversals"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payments.id"), unique=True
    )
    reason: Mapped[str] = mapped_column(String(200))
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class BillingAudit(Base):
    __tablename__ = "billing_audit"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("invoices.id"))
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    event: Mapped[str] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
