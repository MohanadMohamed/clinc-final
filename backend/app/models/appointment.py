import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Appointment(Base):
    __tablename__ = "appointments"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="scheduled")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="appointment_positive_interval"),
        CheckConstraint(
            "isfinite(start_at) AND isfinite(end_at)", name="appointment_finite"
        ),
        CheckConstraint(
            "kind IN ('first_visit', 'follow_up')", name="appointment_kind"
        ),
        CheckConstraint(
            "status IN ('scheduled', 'cancelled')", name="appointment_status"
        ),
        ExcludeConstraint(
            (func.tstzrange(start_at, end_at, "[)"), "&&"),
            using="gist",
            where=text("status = 'scheduled'"),
            name="appointments_no_overlap",
        ),
    )


class AppointmentAudit(Base):
    __tablename__ = "appointment_audit"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("appointments.id"), index=True
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    event: Mapped[str] = mapped_column(String(16))
    old_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    old_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    new_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    new_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
