from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.visit import Visit, VisitAddendum, VisitAudit, VisitRevision
from app.services.auth import now


def audit(db, actor, event, visit_id=None):
    # Metadata only: clinical text, search terms and request bodies never enter audit.
    db.add(VisitAudit(visit_id=visit_id, actor_id=actor.id, event=event))


def snapshot(db, visit, actor, event):
    db.add(
        VisitRevision(
            visit_id=visit.id,
            revision=visit.revision,
            actor_id=actor.id,
            event=event,
            neurological_note=visit.neurological_note,
            psychiatric_note=visit.psychiatric_note,
            follow_up_plan=visit.follow_up_plan,
        )
    )
    audit(db, actor, event, visit.id)


def get(db, visit_id, *, lock=False):
    visit = db.get(Visit, visit_id, with_for_update=lock, populate_existing=lock)
    if visit is None:
        raise HTTPException(404, "Visit not found")
    return visit


def create(db, data, actor):
    patient = db.get(Patient, data.patient_id, with_for_update=True)
    if patient is None:
        raise HTTPException(404, "Patient not found")
    if not patient.active:
        raise HTTPException(400, "Archived patient cannot start a visit")
    if data.appointment_id is not None:
        appointment = db.get(Appointment, data.appointment_id, with_for_update=True)
        if appointment is None:
            raise HTTPException(404, "Appointment not found")
        if appointment.patient_id != patient.id or appointment.status != "scheduled":
            raise HTTPException(400, "Appointment does not match an active booking")
    visit = Visit(**data.model_dump(), created_by=actor.id)
    db.add(visit)
    try:
        db.flush()
        snapshot(db, visit, actor, "created")
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if getattr(error.orig, "sqlstate", None) == "23505":
            raise HTTPException(409, "Appointment already has a visit") from None
        raise
    db.refresh(visit)
    return visit


def require_editable(visit, expected_revision):
    if visit.status != "draft":
        raise HTTPException(400, "Finalized visit requires an addendum")
    if visit.revision != expected_revision:
        raise HTTPException(409, "Visit changed; reload before editing")


def update(db, visit_id, data, actor):
    visit = get(db, visit_id, lock=True)
    require_editable(visit, data.expected_revision)
    changes = data.model_dump(exclude_unset=True, exclude={"expected_revision"})
    if all(getattr(visit, key) == value for key, value in changes.items()):
        raise HTTPException(400, "No note changes")
    for key, value in changes.items():
        setattr(visit, key, value)
    visit.revision += 1
    visit.updated_at = now()
    snapshot(db, visit, actor, "updated")
    db.commit()
    db.refresh(visit)
    return visit


def finalize(db, visit_id, expected_revision, actor):
    visit = get(db, visit_id, lock=True)
    require_editable(visit, expected_revision)
    visit.status = "finalized"
    visit.revision += 1
    visit.finalized_at = visit.updated_at = now()
    snapshot(db, visit, actor, "finalized")
    db.commit()
    db.refresh(visit)
    return visit


def addendum(db, visit_id, body, actor):
    visit = get(db, visit_id, lock=True)
    if visit.status != "finalized":
        raise HTTPException(400, "Addenda require a finalized visit")
    item = VisitAddendum(visit_id=visit.id, actor_id=actor.id, body=body)
    db.add(item)
    audit(db, actor, "addendum_added", visit.id)
    db.commit()
    db.refresh(item)
    return item
