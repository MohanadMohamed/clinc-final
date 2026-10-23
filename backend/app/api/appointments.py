from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import AwareDatetime

from app.api.auth import DB, require_role
from app.models.appointment import Appointment
from app.models.auth import User
from app.repositories.appointments import page as list_page
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentOut,
    AppointmentPage,
    Slot,
)
from app.services import appointments as service
from app.services.auth import now

router = APIRouter(prefix="/api/appointments", tags=["appointments"])
Actor = Annotated[User, Depends(require_role("doctor", "receptionist"))]


@router.post("", response_model=AppointmentOut, status_code=201)
def create(data: AppointmentCreate, request: Request, db: DB, actor: Actor):
    service.patient_lock(db, data.patient_id)
    service.validate_slot(
        data, data.kind, request.app.state.settings.appointment_policy
    )
    appt = Appointment(**data.model_dump())
    db.add(appt)
    return service.save(db, appt, actor, "created")


@router.get("", response_model=AppointmentPage)
def list_appointments(
    db: DB,
    actor: Actor,
    start: AwareDatetime | None = None,
    end: AwareDatetime | None = None,
    patient_id: UUID | None = None,
    status: Literal["scheduled", "cancelled"] | None = None,
    kind: Literal["first_visit", "follow_up"] | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    if start and end and end <= start:
        raise HTTPException(400, "Invalid filter interval")
    return list_page(db, start, end, patient_id, status, kind, page, page_size)


@router.post("/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel(appointment_id: UUID, db: DB, actor: Actor):
    appt = service.appointment_lock(db, appointment_id, require_active=False)
    old = appt.start_at, appt.end_at
    appt.status, appt.updated_at = "cancelled", now()
    return service.save(db, appt, actor, "cancelled", old)


@router.post("/{appointment_id}/reschedule", response_model=AppointmentOut)
def reschedule(
    appointment_id: UUID, data: Slot, request: Request, db: DB, actor: Actor
):
    appt = service.appointment_lock(db, appointment_id)
    service.validate_slot(
        data, appt.kind, request.app.state.settings.appointment_policy
    )
    if (appt.start_at, appt.end_at) == (data.start_at, data.end_at):
        raise HTTPException(400, "Appointment already occupies this slot")
    old = appt.start_at, appt.end_at
    appt.start_at, appt.end_at, appt.updated_at = data.start_at, data.end_at, now()
    return service.save(db, appt, actor, "rescheduled", old)
