from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import DB, require_role
from app.models.auth import User
from app.repositories import visits as repository
from app.schemas.visit import (
    AddendumCreate,
    AddendumOut,
    VisitCreate,
    VisitFinalize,
    VisitHistory,
    VisitOut,
    VisitPage,
    VisitPatch,
    VisitSearch,
)
from app.services import visits as service

router = APIRouter(prefix="/api/visits", tags=["visits"])
Doctor = Annotated[User, Depends(require_role("doctor"))]


@router.get("/export")
def export_disabled(actor: Doctor):
    # Export/print policy is unresolved. Keep the path closed to every role.
    raise HTTPException(403, "Clinical export disabled")


@router.post("/search", response_model=VisitPage)
def search_visits(data: VisitSearch, db: DB, actor: Doctor):
    result = repository.page(
        db, data.patient_id, data.search, data.page, data.page_size
    )
    service.audit(db, actor, "searched")
    db.commit()
    return result


@router.get("/{visit_id}/export")
def visit_export_disabled(visit_id: UUID, actor: Doctor):
    raise HTTPException(403, "Clinical export disabled")


@router.post("", response_model=VisitOut, status_code=201)
def create(data: VisitCreate, db: DB, actor: Doctor):
    return service.create(db, data, actor)


@router.get("", response_model=VisitPage)
def list_visits(
    db: DB,
    actor: Doctor,
    patient_id: UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    result = repository.page(db, patient_id, None, page, page_size)
    service.audit(db, actor, "listed")
    db.commit()
    return result


@router.get("/{visit_id}", response_model=VisitOut)
def get(visit_id: UUID, db: DB, actor: Doctor):
    visit = service.get(db, visit_id)
    service.audit(db, actor, "viewed", visit.id)
    db.commit()
    return visit


@router.get("/{visit_id}/history", response_model=VisitHistory)
def history(visit_id: UUID, db: DB, actor: Doctor):
    service.get(db, visit_id)
    result = repository.history(db, visit_id)
    service.audit(db, actor, "history_viewed", visit_id)
    db.commit()
    return result


@router.patch("/{visit_id}", response_model=VisitOut)
def update(visit_id: UUID, data: VisitPatch, db: DB, actor: Doctor):
    return service.update(db, visit_id, data, actor)


@router.post("/{visit_id}/finalize", response_model=VisitOut)
def finalize(visit_id: UUID, data: VisitFinalize, db: DB, actor: Doctor):
    return service.finalize(db, visit_id, data.expected_revision, actor)


@router.post("/{visit_id}/addenda", response_model=AddendumOut, status_code=201)
def addendum(visit_id: UUID, data: AddendumCreate, db: DB, actor: Doctor):
    return service.addendum(db, visit_id, data.body, actor)
