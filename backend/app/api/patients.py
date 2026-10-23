from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import DB, require_role
from app.models.auth import User
from app.models.patient import Patient
from app.repositories.patients import list_page
from app.schemas.patient import PatientCreate, PatientOut, PatientPage, PatientPatch
from app.services.auth import now
from app.services.patients import archive, check_duplicate, record

router = APIRouter(prefix="/api/patients", tags=["patients"])
Actor = Annotated[User, Depends(require_role("doctor", "receptionist"))]


def get_patient(db, patient_id):
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(404, "Patient not found")
    return patient


@router.post("", response_model=PatientOut, status_code=201)
def create(data: PatientCreate, db: DB, actor: Actor):
    if not data.confirm_duplicate:
        check_duplicate(db, data.full_name, data.phone)
    patient = Patient(
        full_name=data.full_name, phone=data.phone, birth_date=data.birth_date
    )
    db.add(patient)
    db.flush()
    record(db, patient, actor, "created")
    db.commit()
    db.refresh(patient)
    return patient


@router.get("", response_model=PatientPage)
def list_patients(
    db: DB,
    actor: Actor,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=100)] = None,
):
    items, total = list_page(db, search, page, page_size)
    return PatientPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/{patient_id}", response_model=PatientOut)
def get(patient_id: UUID, db: DB, actor: Actor):
    return get_patient(db, patient_id)


@router.patch("/{patient_id}", response_model=PatientOut)
def update(patient_id: UUID, data: PatientPatch, db: DB, actor: Actor):
    patient = get_patient(db, patient_id)
    if not patient.active:
        raise HTTPException(400, "Archived patient cannot be edited")
    values = data.model_dump(exclude_unset=True)
    name, phone = (
        values.get("full_name", patient.full_name),
        values.get("phone", patient.phone),
    )
    if name != patient.full_name or phone != patient.phone:
        check_duplicate(db, name, phone, patient.id)
    for key, value in values.items():
        setattr(patient, key, value)
    patient.updated_at = now()
    record(db, patient, actor, "updated")
    db.commit()
    db.refresh(patient)
    return patient


@router.post("/{patient_id}/archive", response_model=PatientOut)
def archive_patient(patient_id: UUID, db: DB, actor: Actor):
    return archive(db, get_patient(db, patient_id), actor)
