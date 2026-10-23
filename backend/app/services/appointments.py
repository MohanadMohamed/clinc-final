from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models.appointment import Appointment, AppointmentAudit
from app.models.patient import Patient
from app.schemas.appointment import CAIRO
from app.services.auth import now


def validate_slot(slot, kind, policy):
    start, end = slot.start_at, slot.end_at
    minutes = (
        policy.first_visit_minutes
        if kind == "first_visit"
        else policy.follow_up_minutes
    )
    if start <= now() or end - start != timedelta(minutes=minutes):
        raise HTTPException(400, "Future slot with configured duration required")
    local_start, local_end = start.astimezone(CAIRO), end.astimezone(CAIRO)
    if (
        start.second
        or start.microsecond
        or end.second
        or end.microsecond
        or local_start.date() != local_end.date()
        or local_start.weekday() not in policy.weekdays
        or local_start.time() < policy.opens
        or local_end.time() > policy.closes
        or local_end.time() <= local_start.time()
    ):
        raise HTTPException(400, "Slot outside Cairo working hours")


def patient_lock(db, patient_id, require_active=True):
    patient = db.get(Patient, patient_id, with_for_update=True, populate_existing=True)
    if patient is None:
        raise HTTPException(404, "Patient not found")
    if require_active and not patient.active:
        raise HTTPException(400, "Archived patient cannot be scheduled")
    return patient


def appointment_lock(db, appointment_id, require_active=True):
    appt = db.get(Appointment, appointment_id)
    if appt is None:
        raise HTTPException(404, "Appointment not found")
    patient_lock(db, appt.patient_id, require_active)
    appt = db.get(
        Appointment, appointment_id, with_for_update=True, populate_existing=True
    )
    if appt.status != "scheduled" or appt.start_at <= now():
        raise HTTPException(400, "Only future scheduled appointments may change")
    return appt


def save(db, appt, actor, event, old=None):
    try:
        db.flush()
        db.add(
            AppointmentAudit(
                appointment_id=appt.id,
                actor_id=actor.id,
                event=event,
                old_start=old[0] if old else None,
                old_end=old[1] if old else None,
                new_start=appt.start_at,
                new_end=appt.end_at,
            )
        )
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if getattr(error.orig, "sqlstate", None) == "23P01":
            raise HTTPException(
                409, "Appointment overlaps an existing reservation"
            ) from None
        raise
    db.refresh(appt)
    return appt
