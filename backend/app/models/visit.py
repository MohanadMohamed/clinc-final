import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Visit(Base):
    __tablename__ = "visits"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("appointments.id"), unique=True, nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(16), default="draft")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    neurological_note: Mapped[str] = mapped_column(Text, default="")
    psychiatric_note: Mapped[str] = mapped_column(Text, default="")
    follow_up_plan: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'finalized')", name="visit_status"),
        CheckConstraint("revision >= 1", name="visit_revision_positive"),
        Index("ix_visits_patient_created", "patient_id", "created_at", "id"),
    )


class VisitRevision(Base):
    __tablename__ = "visit_revisions"
    visit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("visits.id"), primary_key=True
    )
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    event: Mapped[str] = mapped_column(String(16))
    neurological_note: Mapped[str] = mapped_column(Text)
    psychiatric_note: Mapped[str] = mapped_column(Text)
    follow_up_plan: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    __table_args__ = (
        CheckConstraint(
            "event IN ('created', 'updated', 'finalized')", name="visit_revision_event"
        ),
    )


class VisitAddendum(Base):
    __tablename__ = "visit_addenda"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("visits.id"), index=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    __table_args__ = (
        CheckConstraint("length(body) > 0", name="visit_addendum_nonempty"),
    )


class VisitAudit(Base):
    __tablename__ = "visit_audit"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    visit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("visits.id"), index=True
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    event: Mapped[str] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
