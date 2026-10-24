from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.api.auth import DB, require_role
from app.models.auth import User
from app.models.billing import Invoice, Payment, PaymentReversal
from app.schemas.billing import (
    Adjustment,
    DailySummary,
    FeeOut,
    FeeSet,
    InvoiceCreate,
    InvoiceOut,
    InvoicePage,
    PaymentCreate,
    PaymentOut,
    PaymentRecord,
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


@router.get("/invoices", response_model=InvoicePage)
def list_invoices(
    db: DB,
    actor: Staff,
    patient_id: UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    query = select(Invoice)
    if patient_id:
        query = query.where(Invoice.patient_id == patient_id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(
        query.order_by(Invoice.created_at.desc(), Invoice.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return dict(
        items=[service.view(db, item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: UUID, db: DB, actor: Staff):
    return service.view(db, service.invoice_lock(db, invoice_id))


@router.get("/invoices/{invoice_id}/payments", response_model=list[PaymentRecord])
def list_payments(invoice_id: UUID, db: DB, actor: Staff):
    service.invoice_lock(db, invoice_id)
    payments = db.scalars(
        select(Payment)
        .where(Payment.invoice_id == invoice_id)
        .order_by(Payment.occurred_at, Payment.id)
    ).all()
    reversed_ids = (
        set(
            db.scalars(
                select(PaymentReversal.payment_id).where(
                    PaymentReversal.payment_id.in_([item.id for item in payments])
                )
            ).all()
        )
        if payments
        else set()
    )
    return [
        dict(
            id=item.id,
            invoice_id=item.invoice_id,
            amount_minor=item.amount_minor,
            occurred_at=item.occurred_at,
            reversed=item.id in reversed_ids,
        )
        for item in payments
    ]


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
