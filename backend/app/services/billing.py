from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models.appointment import Appointment
from app.models.billing import (
    BillingAudit,
    Fee,
    Invoice,
    InvoiceAdjustment,
    Payment,
    PaymentReversal,
)
from app.models.patient import Patient
from app.models.visit import Visit
from app.services.auth import now


def audit(db, actor, event, invoice_id=None):
    db.add(BillingAudit(actor_id=actor.id, invoice_id=invoice_id, event=event))


def current_fees(db):
    return [
        db.scalar(
            select(Fee)
            .where(Fee.kind == kind)
            .order_by(Fee.occurred_at.desc(), Fee.id.desc())
            .limit(1)
        )
        for kind in ("first_visit", "follow_up")
    ]


def set_fee(db, data, actor):
    fee = Fee(**data.model_dump(), actor_id=actor.id)
    db.add(fee)
    audit(db, actor, "fee_changed")
    db.commit()
    db.refresh(fee)
    return fee


def invoice_lock(db, invoice_id):
    invoice = db.get(Invoice, invoice_id, with_for_update=True, populate_existing=True)
    if invoice is None:
        raise HTTPException(404, "Invoice not found")
    return invoice


def amounts(db, invoice):
    adjustment = (
        db.scalar(
            select(func.coalesce(func.sum(InvoiceAdjustment.amount_minor), 0)).where(
                InvoiceAdjustment.invoice_id == invoice.id
            )
        )
        or 0
    )
    received = (
        db.scalar(
            select(func.coalesce(func.sum(Payment.amount_minor), 0)).where(
                Payment.invoice_id == invoice.id
            )
        )
        or 0
    )
    reversed_amount = (
        db.scalar(
            select(func.coalesce(func.sum(Payment.amount_minor), 0))
            .join(PaymentReversal, PaymentReversal.payment_id == Payment.id)
            .where(Payment.invoice_id == invoice.id)
        )
        or 0
    )
    total = invoice.base_minor + adjustment
    paid = received - reversed_amount
    return adjustment, total, paid


def view(db, invoice):
    adjustment, total, paid = amounts(db, invoice)
    return dict(
        id=invoice.id,
        patient_id=invoice.patient_id,
        appointment_id=invoice.appointment_id,
        visit_id=invoice.visit_id,
        kind=invoice.kind,
        status=invoice.status,
        base_minor=invoice.base_minor,
        adjustment_minor=adjustment,
        total_minor=total,
        paid_minor=paid,
        balance_minor=0 if invoice.status == "void" else total - paid,
        created_at=invoice.created_at,
    )


def create(db, data, actor):
    existing = db.scalar(
        select(Invoice).where(Invoice.idempotency_key == data.idempotency_key)
    )
    if existing:
        if (
            existing.patient_id,
            existing.appointment_id,
            existing.visit_id,
            existing.kind,
        ) == (data.patient_id, data.appointment_id, data.visit_id, data.kind):
            return view(db, existing)
        raise HTTPException(409, "Idempotency key reused for another invoice")
    patient = db.get(Patient, data.patient_id, with_for_update=True)
    if patient is None:
        raise HTTPException(404, "Patient not found")
    if not patient.active:
        raise HTTPException(400, "Archived patient")
    existing = db.scalar(
        select(Invoice).where(Invoice.idempotency_key == data.idempotency_key)
    )
    if existing:
        if (
            existing.patient_id,
            existing.appointment_id,
            existing.visit_id,
            existing.kind,
        ) == (data.patient_id, data.appointment_id, data.visit_id, data.kind):
            return view(db, existing)
        raise HTTPException(409, "Idempotency key reused for another invoice")
    if data.appointment_id:
        appt = db.get(Appointment, data.appointment_id)
        if (
            not appt
            or appt.patient_id != patient.id
            or appt.kind != data.kind
            or appt.status != "scheduled"
        ):
            raise HTTPException(400, "Active matching appointment required")
    if data.visit_id:
        visit = db.get(Visit, data.visit_id)
        if (
            not visit
            or visit.patient_id != patient.id
            or (data.appointment_id and visit.appointment_id != data.appointment_id)
        ):
            raise HTTPException(400, "Matching visit required")
    fee = db.scalar(
        select(Fee)
        .where(Fee.kind == data.kind)
        .order_by(Fee.occurred_at.desc(), Fee.id.desc())
        .limit(1)
    )
    if fee is None:
        raise HTTPException(400, "Fee is not configured")
    invoice = Invoice(
        **data.model_dump(), base_minor=fee.amount_minor, created_by=actor.id
    )
    db.add(invoice)
    try:
        db.flush()
        audit(db, actor, "created", invoice.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Invoice creation conflict") from None
    db.refresh(invoice)
    return view(db, invoice)


def issue(db, invoice_id, actor):
    invoice = invoice_lock(db, invoice_id)
    if invoice.appointment_id and not invoice.visit_id:
        appointment = db.get(Appointment, invoice.appointment_id)
        if appointment.status == "cancelled":
            raise HTTPException(
                409, "Cancelled appointment requires invoice correction"
            )
    if invoice.status != "draft":
        raise HTTPException(400, "Only draft invoices can be issued")
    invoice.status, invoice.issued_at = "issued", now()
    audit(db, actor, "issued", invoice.id)
    db.commit()
    return view(db, invoice)


def payment(db, invoice_id, data, actor):
    invoice = invoice_lock(db, invoice_id)
    existing = db.scalar(
        select(Payment).where(Payment.idempotency_key == data.idempotency_key)
    )
    if existing:
        if (
            existing.invoice_id == invoice.id
            and existing.amount_minor == data.amount_minor
        ):
            return existing
        raise HTTPException(409, "Idempotency key reused for another payment")
    if invoice.appointment_id and not invoice.visit_id:
        appointment = db.get(Appointment, invoice.appointment_id)
        if appointment.status == "cancelled":
            raise HTTPException(409, "Cancelled appointment cannot be collected")
    _, total, paid = amounts(db, invoice)
    if invoice.status != "issued" or data.amount_minor > total - paid:
        raise HTTPException(
            400, "Payment exceeds payable balance or invoice is not issued"
        )
    item = Payment(
        invoice_id=invoice.id,
        idempotency_key=data.idempotency_key,
        amount_minor=data.amount_minor,
        actor_id=actor.id,
    )
    db.add(item)
    try:
        db.flush()
        audit(db, actor, "paid", invoice.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Payment submission conflict") from None
    db.refresh(item)
    return item


def adjust(db, invoice_id, data, actor):
    invoice = invoice_lock(db, invoice_id)
    existing = db.scalar(
        select(InvoiceAdjustment).where(
            InvoiceAdjustment.idempotency_key == data.idempotency_key
        )
    )
    if existing:
        if (
            existing.invoice_id == invoice.id
            and existing.amount_minor == data.amount_minor
            and existing.reason == data.reason
        ):
            return view(db, invoice)
        raise HTTPException(409, "Idempotency key reused for another adjustment")
    _, total, paid = amounts(db, invoice)
    if (
        invoice.status != "issued"
        or data.amount_minor == 0
        or not (0 <= total + data.amount_minor <= 2_000_000_000)
        or total + data.amount_minor < paid
    ):
        raise HTTPException(400, "Adjustment would invalidate invoice balance")
    db.add(
        InvoiceAdjustment(
            invoice_id=invoice.id,
            idempotency_key=data.idempotency_key,
            amount_minor=data.amount_minor,
            reason=data.reason,
            actor_id=actor.id,
        )
    )
    audit(db, actor, "adjusted", invoice.id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Adjustment submission conflict") from None
    return view(db, invoice)


def reverse(db, payment_id, reason, actor):
    item = db.get(Payment, payment_id)
    if item is None:
        raise HTTPException(404, "Payment not found")
    invoice = invoice_lock(db, item.invoice_id)
    if db.scalar(
        select(PaymentReversal.id).where(PaymentReversal.payment_id == item.id)
    ):
        raise HTTPException(400, "Payment already reversed")
    db.add(PaymentReversal(payment_id=item.id, reason=reason, actor_id=actor.id))
    audit(db, actor, "payment_reversed", invoice.id)
    db.commit()
    return view(db, invoice)


def void(db, invoice_id, reason, actor):
    invoice = invoice_lock(db, invoice_id)
    _, _, paid = amounts(db, invoice)
    if invoice.status == "void" or paid:
        raise HTTPException(400, "Reverse payments before voiding")
    invoice.status, invoice.voided_at, invoice.void_reason = "void", now(), reason
    audit(db, actor, "voided", invoice.id)
    db.commit()
    return view(db, invoice)


def daily(db, day: date):
    cairo = ZoneInfo("Africa/Cairo")
    start = datetime.combine(day, datetime.min.time(), cairo).astimezone(UTC)
    end = datetime.combine(
        day + timedelta(days=1), datetime.min.time(), cairo
    ).astimezone(UTC)
    received = (
        db.scalar(
            select(func.coalesce(func.sum(Payment.amount_minor), 0)).where(
                Payment.occurred_at >= start, Payment.occurred_at < end
            )
        )
        or 0
    )
    reversed_amount = (
        db.scalar(
            select(func.coalesce(func.sum(Payment.amount_minor), 0))
            .join(PaymentReversal, PaymentReversal.payment_id == Payment.id)
            .where(
                PaymentReversal.occurred_at >= start, PaymentReversal.occurred_at < end
            )
        )
        or 0
    )
    return dict(
        day=day.isoformat(),
        received_minor=received,
        reversed_minor=reversed_amount,
        net_minor=received - reversed_amount,
    )
