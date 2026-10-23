from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from test_auth import login, token

from app.core.scheduling import SchedulingPolicy
from app.models.appointment import Appointment, AppointmentAudit
from app.models.patient import Patient
from app.schemas.appointment import CAIRO, Slot
from app.services import appointments as service

pytest_plugins = ["test_auth"]


def future_slot(hour=10, minute=0, duration=30):
    day = datetime.now(CAIRO) + timedelta(days=10)
    while day.weekday() == 4:
        day += timedelta(days=1)
    start = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return {
        "start_at": start.isoformat(),
        "end_at": (start + timedelta(minutes=duration)).isoformat(),
    }


def setup_patient(auth, role="synthetic.reception"):
    client, password, _, _ = auth
    assert login(client, password, role).status_code == 200
    token(client)
    response = client.post(
        "/api/patients", json={"full_name": "Synthetic Schedule", "phone": "123456789"}
    )
    assert response.status_code == 201
    return client, response.json()["id"]


def test_api_lifecycle_filters_and_archive(auth):
    client, _, factory, _ = auth
    assert client.get("/api/appointments").status_code == 401
    client, patient_id = setup_patient(auth)
    data = {"patient_id": patient_id, "kind": "first_visit", **future_slot()}
    response = client.post("/api/appointments", json=data)
    assert response.status_code == 201, response.text
    a = response.json()
    assert a["start_at"].endswith("Z")
    assert client.post("/api/appointments", json=data).status_code == 409
    assert (
        client.post(
            "/api/appointments", json={**data, **future_slot(10, 15)}
        ).status_code
        == 409
    )
    adjacent = client.post("/api/appointments", json={**data, **future_slot(10, 30)})
    assert adjacent.status_code == 201
    assert client.post(f"/api/patients/{patient_id}/archive").status_code == 409
    assert (
        client.post(
            f"/api/appointments/{a['id']}/reschedule", json=future_slot(10, 30)
        ).status_code
        == 409
    )
    moved = client.post(f"/api/appointments/{a['id']}/reschedule", json=future_slot(11))
    assert moved.status_code == 200
    listed = client.get(
        "/api/appointments",
        params={
            "patient_id": patient_id,
            "status": "scheduled",
            "kind": "first_visit",
            "page_size": 1,
        },
    ).json()
    assert listed["total"] == 2 and len(listed["items"]) == 1
    assert (
        client.get(
            "/api/appointments",
            params={"start": data["end_at"], "end": future_slot(11)["start_at"]},
        ).json()["total"]
        == 1
    )
    for appointment_id in [a["id"], adjacent.json()["id"]]:
        assert (
            client.post(f"/api/appointments/{appointment_id}/cancel").status_code == 200
        )
    assert client.post(f"/api/appointments/{a['id']}/cancel").status_code == 400
    assert (
        client.post(
            f"/api/appointments/{a['id']}/reschedule", json=future_slot(12)
        ).status_code
        == 400
    )
    # Cancellation frees the original slot; audit and cancelled row remain.
    replacement = client.post("/api/appointments", json=data)
    assert replacement.status_code == 201
    assert (
        client.post(f"/api/appointments/{replacement.json()['id']}/cancel").status_code
        == 200
    )
    assert client.post(f"/api/patients/{patient_id}/archive").status_code == 200
    assert (
        client.post("/api/appointments", json={**data, **future_slot(13)}).status_code
        == 400
    )
    with factory() as db:
        events = db.scalars(
            select(AppointmentAudit)
            .where(AppointmentAudit.appointment_id == UUID(a["id"]))
            .order_by(AppointmentAudit.occurred_at)
        ).all()
        assert [e.event for e in events] == ["created", "rescheduled", "cancelled"]
        assert events[1].old_start != events[1].new_start
        assert db.get(Appointment, UUID(a["id"])).status == "cancelled"


@pytest.mark.parametrize("role", ["synthetic.doctor", "synthetic.reception"])
def test_permissions_errors_and_configuration(auth, role):
    client, patient_id = setup_patient(auth, role)
    data = {"patient_id": patient_id, "kind": "follow_up", **future_slot(duration=15)}
    header = client.headers.pop("x-csrf-token")
    assert client.post("/api/appointments", json=data).status_code == 403
    client.headers["x-csrf-token"] = header
    assert client.post("/api/appointments", json=data).status_code == 201
    assert (
        client.post(
            "/api/appointments", json={**data, "patient_id": str(uuid4())}
        ).status_code
        == 404
    )
    assert client.post(f"/api/appointments/{uuid4()}/cancel").status_code == 404
    assert (
        client.post("/api/appointments", json={**data, "kind": "diagnosis"}).status_code
        == 422
    )
    assert (
        client.post(
            "/api/appointments", json={**data, "notes": "not allowed"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/appointments", json={**data, "start_at": "2030-01-01T10:00:00"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/appointments", json={**data, **future_slot(8, duration=15)}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/appointments", json={**data, **future_slot(duration=30)}
        ).status_code
        == 400
    )
    yesterday = datetime.now(UTC) - timedelta(days=1)
    assert (
        client.post(
            "/api/appointments",
            json={
                **data,
                "start_at": yesterday.isoformat(),
                "end_at": (yesterday + timedelta(minutes=15)).isoformat(),
            },
        ).status_code
        == 400
    )
    assert client.get("/api/appointments?page_size=101").status_code == 422
    assert (
        client.get(
            "/api/appointments",
            params={"start": data["end_at"], "end": data["start_at"]},
        ).status_code
        == 400
    )
    client.app.state.settings.appointment_policy.follow_up_minutes = 20
    assert (
        client.post(
            "/api/appointments", json={**data, **future_slot(12, duration=20)}
        ).status_code
        == 201
    )


@pytest.mark.parametrize("operation", ["insert", "reschedule"])
def test_database_exclusion_under_true_concurrency(auth_db, operation):
    with auth_db() as db:
        patient = Patient(full_name="Synthetic Race", phone="12345678")
        db.add(patient)
        db.commit()
        pid = patient.id
        ids = [uuid4(), uuid4()]
        if operation == "reschedule":
            for i, aid in enumerate(ids):
                slot = Slot(**future_slot(12 + i))
                db.add(
                    Appointment(
                        id=aid, patient_id=pid, kind="first_visit", **slot.model_dump()
                    )
                )
            db.commit()
    barrier = Barrier(2)

    def book(i):
        with auth_db() as db:
            connection_pid = db.scalar(text("SELECT pg_backend_pid()"))
            slot = Slot(**future_slot())
            if operation == "insert":
                db.add(
                    Appointment(
                        id=ids[i],
                        patient_id=pid,
                        kind="first_visit",
                        **slot.model_dump(),
                    )
                )
            else:
                appt = db.get(Appointment, ids[i])
                appt.start_at, appt.end_at = slot.start_at, slot.end_at
            barrier.wait(timeout=10)
            try:
                db.commit()
                return connection_pid, "committed"
            except IntegrityError as error:
                db.rollback()
                return connection_pid, error.orig.sqlstate

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(book, range(2)))
    assert len({r[0] for r in results}) == 2
    assert sorted(r[1] for r in results) == ["23P01", "committed"]
    with auth_db() as db:
        rows = db.scalars(
            select(Appointment).where(
                Appointment.start_at == Slot(**future_slot()).start_at
            )
        ).all()
        assert len(rows) == 1


def test_cairo_dst_and_hours(monkeypatch):
    monkeypatch.setattr(service, "now", lambda: datetime(2027, 1, 1, tzinfo=UTC))
    policy = SchedulingPolicy(opens="00:00", closes="23:59", weekdays=list(range(7)))
    # Cairo spring gap: 00:15 at +02 never occurred on 30 April 2027.
    with pytest.raises(ValidationError):
        Slot(start_at="2027-04-30T00:15:00+02:00", end_at="2027-04-30T00:45:00+02:00")
    spring = Slot(
        start_at="2027-04-30T01:15:00+03:00", end_at="2027-04-30T01:45:00+03:00"
    )
    service.validate_slot(spring, "first_visit", policy)
    # Repeated autumn hour is unambiguous with explicit offsets.
    early = Slot(
        start_at="2027-10-28T23:15:00+03:00", end_at="2027-10-28T23:45:00+03:00"
    )
    late = Slot(
        start_at="2027-10-28T23:15:00+02:00", end_at="2027-10-28T23:45:00+02:00"
    )
    assert late.start_at - early.start_at == timedelta(hours=1)
    for slot in [early, late]:
        service.validate_slot(slot, "first_visit", policy)
    with pytest.raises(HTTPException):
        service.validate_slot(
            spring, "first_visit", SchedulingPolicy()
        )  # Friday closed
    with pytest.raises(ValidationError):
        SchedulingPolicy(opens="17:00", closes="09:00")


def test_database_rejects_empty_interval_and_bad_status(auth_db):
    with auth_db() as db:
        patient = Patient(full_name="Synthetic Constraints", phone="12345678")
        db.add(patient)
        db.commit()
        pid = patient.id
        start = Slot(**future_slot()).start_at
        for end, status in [
            (start, "scheduled"),
            (start + timedelta(minutes=30), "invalid"),
        ]:
            db.add(
                Appointment(
                    patient_id=pid,
                    kind="first_visit",
                    start_at=start,
                    end_at=end,
                    status=status,
                )
            )
            with pytest.raises(IntegrityError) as error:
                db.commit()
            assert error.value.orig.sqlstate == "23514"
            db.rollback()


def test_archived_patient_reschedule_denied_and_cancel_allowed(auth):
    client, pid = setup_patient(auth)
    created = client.post(
        "/api/appointments",
        json={"patient_id": pid, "kind": "first_visit", **future_slot()},
    )
    aid = created.json()["id"]
    # Simulate legacy/operator archive; the ordinary archive API refuses upcoming slots.
    with auth[2]() as db:
        db.get(Patient, UUID(pid)).active = False
        db.commit()
    assert (
        client.post(
            f"/api/appointments/{aid}/reschedule", json=future_slot(12)
        ).status_code
        == 400
    )
    assert client.post(f"/api/appointments/{aid}/cancel").status_code == 200


def test_closed_hours_and_invalid_lengths(monkeypatch):
    monkeypatch.setattr(service, "now", lambda: datetime(2027, 1, 1, tzinfo=UTC))
    for start, end in [
        ("2030-01-05T17:00:00+02:00", "2030-01-05T17:30:00+02:00"),
        ("2030-01-05T10:00:00+02:00", "2030-01-05T10:00:00+02:00"),
        ("2030-01-05T10:00:00+02:00", "2030-01-05T09:30:00+02:00"),
    ]:
        with pytest.raises(HTTPException):
            service.validate_slot(
                Slot(start_at=start, end_at=end), "first_visit", SchedulingPolicy()
            )
