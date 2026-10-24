from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from test_auth import login, token

from app.models.billing import (
    BillingAudit,
    Invoice,
    InvoiceAdjustment,
    Payment,
    PaymentReversal,
)

pytest_plugins = ["test_auth"]


def test_invoice_payment_idempotency_adjustment_and_roles(auth):
    client, password, factory, _ = auth
    assert client.get("/api/billing/fees").status_code == 401
    assert client.get("/api/billing/invoices").status_code == 401
    assert login(client, password).status_code == 200
    token(client)
    assert (
        client.post(
            "/api/billing/fees",
            json={
                "kind": "first_visit",
                "amount_minor": 15000,
                "reason": "Synthetic initial fee",
            },
        ).status_code
        == 201
    )
    patient = client.post(
        "/api/patients", json={"full_name": "Synthetic Bill", "phone": "123456789"}
    ).json()["id"]
    key = str(uuid4())
    request = {"idempotency_key": key, "patient_id": patient, "kind": "first_visit"}
    invoice = client.post("/api/billing/invoices", json=request)
    assert invoice.status_code == 201 and invoice.json()["base_minor"] == 15000
    iid = invoice.json()["id"]
    page = client.get("/api/billing/invoices?page=1&page_size=5")
    assert page.status_code == 200
    assert page.json()["total"] == 1 and page.json()["items"][0]["id"] == iid
    assert set(page.json()["items"][0]) == set(invoice.json())
    assert client.get(f"/api/billing/invoices/{iid}/payments").json() == []
    assert client.post("/api/billing/invoices", json=request).json()["id"] == iid
    assert (
        client.post(
            "/api/billing/invoices", json={**request, "patient_id": str(uuid4())}
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/billing/invoices/{iid}/payments",
            json={"idempotency_key": str(uuid4()), "amount_minor": 100},
        ).status_code
        == 400
    )
    assert client.post(f"/api/billing/invoices/{iid}/issue").status_code == 200
    assert login(client, password, "synthetic.reception").status_code == 200
    token(client)
    assert client.get("/api/billing/fees").status_code == 200
    assert client.get("/api/billing/invoices").json()["total"] == 1
    for path, data in [
        (
            "/api/billing/fees",
            {"kind": "follow_up", "amount_minor": 5000, "reason": "Not allowed"},
        ),
        (
            f"/api/billing/invoices/{iid}/adjustments",
            {
                "idempotency_key": str(uuid4()),
                "amount_minor": -100,
                "reason": "Not allowed",
            },
        ),
        (f"/api/billing/invoices/{iid}/void", {"reason": "Not allowed"}),
    ]:
        assert client.post(path, json=data).status_code == 403
    payment_key = str(uuid4())
    pay = client.post(
        f"/api/billing/invoices/{iid}/payments",
        json={"idempotency_key": payment_key, "amount_minor": 5000},
    )
    assert pay.status_code == 201
    pid = pay.json()["id"]
    payment_list = client.get(f"/api/billing/invoices/{iid}/payments")
    assert payment_list.status_code == 200
    assert payment_list.json()[0]["id"] == pid
    assert payment_list.json()[0]["reversed"] is False
    assert (
        client.post(
            f"/api/billing/invoices/{iid}/payments",
            json={"idempotency_key": payment_key, "amount_minor": 5000},
        ).json()["id"]
        == pid
    )
    assert (
        client.post(
            f"/api/billing/invoices/{iid}/payments",
            json={"idempotency_key": payment_key, "amount_minor": 4000},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/billing/invoices/{iid}/payments",
            json={"idempotency_key": str(uuid4()), "amount_minor": 11000},
        ).status_code
        == 400
    )
    assert client.get(f"/api/billing/invoices/{iid}").json()["balance_minor"] == 10000
    assert (
        client.post(
            f"/api/billing/payments/{pid}/reverse", json={"reason": "Not allowed"}
        ).status_code
        == 403
    )
    assert login(client, password).status_code == 200
    token(client)
    assert (
        client.post(
            f"/api/billing/invoices/{iid}/adjustments",
            json={
                "idempotency_key": str(uuid4()),
                "amount_minor": -11000,
                "reason": "Would undercut payment",
            },
        ).status_code
        == 400
    )
    adjustment_key = str(uuid4())
    adjusted = client.post(
        f"/api/billing/invoices/{iid}/adjustments",
        json={
            "idempotency_key": adjustment_key,
            "amount_minor": -2000,
            "reason": "Synthetic approved discount",
        },
    )
    assert adjusted.status_code == 200 and adjusted.json()["balance_minor"] == 8000
    assert (
        client.post(
            f"/api/billing/invoices/{iid}/adjustments",
            json={
                "idempotency_key": adjustment_key,
                "amount_minor": -2000,
                "reason": "Synthetic approved discount",
            },
        ).json()["total_minor"]
        == 13000
    )
    assert (
        client.post(
            f"/api/billing/invoices/{iid}/void", json={"reason": "Incorrect invoice"}
        ).status_code
        == 400
    )
    day = datetime.now(ZoneInfo("Africa/Cairo")).date().isoformat()
    summary = client.get(f"/api/billing/summary/{day}").json()
    assert summary["received_minor"] == 5000 and summary["net_minor"] == 5000
    reversed_invoice = client.post(
        f"/api/billing/payments/{pid}/reverse", json={"reason": "Synthetic correction"}
    )
    assert (
        reversed_invoice.status_code == 200
        and reversed_invoice.json()["paid_minor"] == 0
    )
    assert (
        client.get(f"/api/billing/invoices/{iid}/payments").json()[0]["reversed"]
        is True
    )
    summary = client.get(f"/api/billing/summary/{day}").json()
    assert summary["reversed_minor"] == 5000 and summary["net_minor"] == 0
    assert (
        client.post(
            f"/api/billing/payments/{pid}/reverse", json={"reason": "Repeat"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/billing/invoices/{iid}/void", json={"reason": "Synthetic correction"}
        ).json()["balance_minor"]
        == 0
    )
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Invoice)) == 1
        assert db.scalar(select(func.count()).select_from(Payment)) == 1
        assert db.scalar(select(func.count()).select_from(PaymentReversal)) == 1
        assert db.scalar(select(func.count()).select_from(InvoiceAdjustment)) == 1
        assert {row.event for row in db.scalars(select(BillingAudit)).all()} >= {
            "created",
            "issued",
            "paid",
            "adjusted",
            "payment_reversed",
            "voided",
        }


def test_cancelled_booking_keeps_invoice_and_rejects_new_link(auth):
    from test_appointments import future_slot

    client, password, _, _ = auth
    assert login(client, password).status_code == 200
    token(client)
    client.post(
        "/api/billing/fees",
        json={
            "kind": "follow_up",
            "amount_minor": 8000,
            "reason": "Synthetic follow-up fee",
        },
    )
    patient = client.post(
        "/api/patients", json={"full_name": "Synthetic Cancel", "phone": "222222222"}
    ).json()["id"]
    booking = client.post(
        "/api/appointments",
        json={"patient_id": patient, "kind": "follow_up", **future_slot(duration=15)},
    )
    assert booking.status_code == 201
    aid = booking.json()["id"]
    data = {
        "idempotency_key": str(uuid4()),
        "patient_id": patient,
        "kind": "follow_up",
        "appointment_id": aid,
    }
    invoice = client.post("/api/billing/invoices", json=data)
    assert invoice.status_code == 201
    assert (
        client.post(
            "/api/billing/invoices", json={**data, "idempotency_key": str(uuid4())}
        ).status_code
        == 409
    )
    assert client.post(f"/api/appointments/{aid}/cancel").status_code == 200
    assert (
        client.post(f"/api/billing/invoices/{invoice.json()['id']}/issue").status_code
        == 409
    )
    assert (
        client.get(f"/api/billing/invoices/{invoice.json()['id']}").json()["base_minor"]
        == 8000
    )
    assert (
        client.post(
            "/api/billing/invoices", json={**data, "idempotency_key": str(uuid4())}
        ).status_code
        == 400
    )
    second_booking = client.post(
        "/api/appointments",
        json={
            "patient_id": patient,
            "kind": "follow_up",
            **future_slot(11, duration=15),
        },
    )
    assert second_booking.status_code == 201
    second_invoice = client.post(
        "/api/billing/invoices",
        json={
            **data,
            "idempotency_key": str(uuid4()),
            "appointment_id": second_booking.json()["id"],
        },
    )
    assert second_invoice.status_code == 201
    second_id = second_invoice.json()["id"]
    assert client.post(f"/api/billing/invoices/{second_id}/issue").status_code == 200
    assert (
        client.post(
            f"/api/appointments/{second_booking.json()['id']}/cancel"
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/billing/invoices/{second_id}/payments",
            json={"idempotency_key": str(uuid4()), "amount_minor": 100},
        ).status_code
        == 409
    )
    assert client.get(f"/api/billing/invoices/{second_id}").json()["paid_minor"] == 0


def test_concurrent_payments_cannot_overpay(auth):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from fastapi import HTTPException

    from app.models.auth import User
    from app.schemas.billing import PaymentCreate
    from app.services import billing as service

    client, password, factory, doctor_id = auth
    assert login(client, password).status_code == 200
    token(client)
    assert (
        client.post(
            "/api/billing/fees",
            json={
                "kind": "first_visit",
                "amount_minor": 10000,
                "reason": "Synthetic fee",
            },
        ).status_code
        == 201
    )
    patient = client.post(
        "/api/patients", json={"full_name": "Synthetic Race Bill", "phone": "333333333"}
    ).json()["id"]
    invoice = client.post(
        "/api/billing/invoices",
        json={
            "idempotency_key": str(uuid4()),
            "patient_id": patient,
            "kind": "first_visit",
        },
    ).json()
    iid = invoice["id"]
    assert client.post(f"/api/billing/invoices/{iid}/issue").status_code == 200
    barrier = Barrier(2)

    def attempt(_):
        with factory() as db:
            actor = db.get(User, doctor_id)
            barrier.wait(timeout=10)
            try:
                service.payment(
                    db,
                    iid,
                    PaymentCreate(idempotency_key=uuid4(), amount_minor=8000),
                    actor,
                )
                return 201
            except HTTPException as error:
                db.rollback()
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert sorted(results) == [201, 400]
    assert client.get(f"/api/billing/invoices/{iid}").json()["paid_minor"] == 8000
