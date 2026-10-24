from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.auth import DB, require_role
from app.models.auth import User
from app.schemas.billing import (
    Adjustment,
    DailySummary,
    FeeOut,
    FeeSet,
    InvoiceCreate,
    InvoiceOut,
    PaymentCreate,
    PaymentOut,
    Reason,
)
from app.services import billing as service

router = APIRouter(prefix="/api/billing", tags=["billing"])
Staff = Annotated[User, Depends(require_role("doctor", "receptionist"))]
Doctor = Annotated[User, Depends(require_role("doctor"))]


@router.get("/fees", response_model=list[FeeOut])
def fees(db: DB, actor: Staff):
    return [fee for fee in service.current_fees(db) if fee]


@router.post("/fees", response_model=FeeOut, status_code=201)
def set_fee(data: FeeSet, db: DB, actor: Doctor):
    return service.set_fee(db, data, actor)


@router.post("/invoices", response_model=InvoiceOut, status_code=201)
def create_invoice(data: InvoiceCreate, db: DB, actor: Staff):
    return service.create(db, data, actor)


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: UUID, db: DB, actor: Staff):
    return service.view(db, service.invoice_lock(db, invoice_id))


@router.post("/invoices/{invoice_id}/issue", response_model=InvoiceOut)
def issue(invoice_id: UUID, db: DB, actor: Staff):
    return service.issue(db, invoice_id, actor)


@router.post(
    "/invoices/{invoice_id}/payments", response_model=PaymentOut, status_code=201
)
def pay(invoice_id: UUID, data: PaymentCreate, db: DB, actor: Staff):
    return service.payment(db, invoice_id, data, actor)


@router.post("/invoices/{invoice_id}/adjustments", response_model=InvoiceOut)
def adjust(invoice_id: UUID, data: Adjustment, db: DB, actor: Doctor):
    return service.adjust(db, invoice_id, data, actor)


@router.post("/payments/{payment_id}/reverse", response_model=InvoiceOut)
def reverse(payment_id: UUID, data: Reason, db: DB, actor: Doctor):
    return service.reverse(db, payment_id, data.reason, actor)


@router.post("/invoices/{invoice_id}/void", response_model=InvoiceOut)
def void(invoice_id: UUID, data: Reason, db: DB, actor: Doctor):
    return service.void(db, invoice_id, data.reason, actor)


@router.get("/summary/{day}", response_model=DailySummary)
def daily(day: date, db: DB, actor: Staff):
    return service.daily(db, day)
