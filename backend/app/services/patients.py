from fastapi import HTTPException
from sqlalchemy import text

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
    patient.active = False
    patient.archived_at = now()
    patient.updated_at = now()
    record(db, patient, actor, "archived")
    db.commit()
    return patient
