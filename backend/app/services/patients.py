from fastapi import HTTPException
from sqlalchemy import select, text

from app.models.appointment import Appointment
from app.models.patient import PatientAudit
from app.repositories.patients import find_duplicate
from app.services.auth import now


def check_duplicate(db, name, phone, exclude=None):
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"patient:{name.lower()}:{phone}"},
    )
    if find_duplicate(db, name, phone, exclude):
        raise HTTPException(400, "Possible duplicate registration; confirm explicitly")


def record(db, patient, actor, event):
    db.add(PatientAudit(patient_id=patient.id, actor_id=actor.id, event=event))


def archive(db, patient, actor):
    if not patient.active:
        raise HTTPException(400, "Patient already archived")
    if db.scalar(
        select(Appointment.id)
        .where(
            Appointment.patient_id == patient.id,
            Appointment.status == "scheduled",
            Appointment.end_at > now(),
        )
        .limit(1)
    ):
        raise HTTPException(409, "Cancel upcoming appointments before archiving")
    patient.active = False
    patient.archived_at = now()
    patient.updated_at = now()
    record(db, patient, actor, "archived")
    db.commit()
    return patient
