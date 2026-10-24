import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from test_auth import login, token

from app.models.visit import Visit, VisitAddendum, VisitAudit, VisitRevision

pytest_plugins = ["test_auth"]

PRIVATE = "SYNTHETIC_PRIVATE_NOTE_MARKER_4A"


def patient(client, name, phone):
    response = client.post("/api/patients", json={"full_name": name, "phone": phone})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def visit(client, patient_id, **changes):
    response = client.post(
        "/api/visits",
        json={
            "patient_id": patient_id,
            "neurological_note": PRIVATE,
            "psychiatric_note": "Synthetic private psychiatric text",
            "follow_up_plan": "Synthetic follow-up text",
            **changes,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_doctor_lifecycle_revision_history_and_audit(auth, caplog):
    client, password, factory, doctor_id = auth
    caplog.set_level(logging.DEBUG)
    assert client.get("/api/visits").status_code == 401
    assert login(client, password).status_code == 200
    token(client)
    pid = patient(client, "Synthetic Visit One", "123456789")
    created = visit(client, pid)
    vid = created["id"]
    assert created["status"] == "draft" and created["revision"] == 1
    assert created["neurological_note"] == PRIVATE
    assert (
        client.get(f"/api/visits/{vid}").json()["follow_up_plan"]
        == "Synthetic follow-up text"
    )
    listed = client.get("/api/visits", params={"patient_id": pid}).json()
    assert listed["total"] == 1
    assert "neurological_note" not in listed["items"][0]
    searched = client.post("/api/visits/search", json={"search": PRIVATE})
    assert searched.status_code == 200 and searched.json()["total"] == 1
    assert "neurological_note" not in searched.json()["items"][0]
    updated = client.patch(
        f"/api/visits/{vid}",
        json={"expected_revision": 1, "follow_up_plan": "Synthetic revised plan"},
    )
    assert updated.status_code == 200 and updated.json()["revision"] == 2
    stale = client.patch(
        f"/api/visits/{vid}",
        json={"expected_revision": 1, "follow_up_plan": "Stale draft"},
    )
    assert stale.status_code == 409
    finalized = client.post(
        f"/api/visits/{vid}/finalize", json={"expected_revision": 2}
    )
    assert finalized.status_code == 200 and finalized.json()["revision"] == 3
    assert finalized.json()["status"] == "finalized"
    assert (
        client.patch(
            f"/api/visits/{vid}",
            json={"expected_revision": 3, "neurological_note": "Overwrite"},
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/visits/{vid}/finalize", json={"expected_revision": 3}
        ).status_code
        == 400
    )
    addition = client.post(
        f"/api/visits/{vid}/addenda", json={"body": "Synthetic correction"}
    )
    assert addition.status_code == 201
    history = client.get(f"/api/visits/{vid}/history")
    assert history.status_code == 200
    assert [r["event"] for r in history.json()["revisions"]] == [
        "created",
        "updated",
        "finalized",
    ]
    assert (
        history.json()["revisions"][0]["follow_up_plan"] == "Synthetic follow-up text"
    )
    assert history.json()["revisions"][1]["follow_up_plan"] == "Synthetic revised plan"
    assert history.json()["addenda"][0]["body"] == "Synthetic correction"
    with factory() as db:
        row = db.get(Visit, UUID(vid))
        assert row.created_by == doctor_id and row.finalized_at is not None
        assert db.scalar(select(VisitAddendum).where(VisitAddendum.visit_id == row.id))
        revisions = db.scalars(
            select(VisitRevision).where(VisitRevision.visit_id == row.id)
        ).all()
        assert len(revisions) == 3
        audits = db.scalars(
            select(VisitAudit).where(VisitAudit.visit_id == row.id)
        ).all()
        assert {a.event for a in audits} >= {
            "created",
            "viewed",
            "updated",
            "finalized",
            "addendum_added",
            "history_viewed",
        }
        assert PRIVATE not in repr([(a.event, a.visit_id, a.actor_id) for a in audits])
        revisions[0].neurological_note = "Illicit replacement"
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
        row = db.get(Visit, UUID(vid))
        row.neurological_note = "Illicit finalized edit"
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
    assert PRIVATE not in caplog.text


def test_receptionist_denied_all_clinical_routes_and_admin_projection(auth, caplog):
    client, password, factory, _ = auth
    caplog.set_level(logging.DEBUG)
    assert login(client, password).status_code == 200
    token(client)
    pid = patient(client, "Synthetic Boundary", "987654321")
    vid = visit(client, pid)["id"]
    assert login(client, password, "synthetic.reception").status_code == 200
    token(client)
    guessed = uuid4()
    requests = [
        client.get("/api/visits"),
        client.get("/api/visits", params={"patient_id": pid}),
        client.post("/api/visits/search", json={"search": PRIVATE}),
        client.get(f"/api/visits/{vid}"),
        client.get(f"/api/visits/{guessed}"),
        client.get(f"/api/visits/{vid}/history"),
        client.get(f"/api/visits/{guessed}/history"),
        client.patch(
            f"/api/visits/{vid}",
            json={"expected_revision": 1, "neurological_note": "tamper"},
        ),
        client.patch(
            f"/api/visits/{guessed}",
            json={"expected_revision": 1, "neurological_note": "tamper"},
        ),
        client.post(f"/api/visits/{vid}/finalize", json={"expected_revision": 1}),
        client.post(f"/api/visits/{vid}/addenda", json={"body": "tamper"}),
        client.post("/api/visits", json={"patient_id": pid}),
        client.get("/api/visits/export"),
        client.get(f"/api/visits/{vid}/export"),
        client.get(f"/api/visits/{guessed}/export"),
    ]
    assert all(response.status_code == 403 for response in requests)
    assert all(PRIVATE not in response.text for response in requests)
    for response in [
        client.get("/api/patients"),
        client.get(f"/api/patients/{pid}"),
        client.get("/api/appointments"),
    ]:
        assert response.status_code == 200
        assert PRIVATE not in response.text
        assert "neurological_note" not in response.text
        assert "psychiatric_note" not in response.text
        assert "follow_up_plan" not in response.text
    with factory() as db:
        assert db.get(Visit, UUID(vid)).revision == 1
    assert PRIVATE not in caplog.text


def test_links_validation_and_disabled_export(auth):
    client, password, factory, _ = auth
    assert login(client, password).status_code == 200
    token(client)
    first = patient(client, "Synthetic Link One", "111111111")
    second = patient(client, "Synthetic Link Two", "222222222")
    future = datetime.now(UTC) + timedelta(days=12)
    start = future.replace(hour=8, minute=0, second=0, microsecond=0)
    # The appointment API uses Cairo working hours; choose a weekday and explicit UTC.
    from zoneinfo import ZoneInfo

    cairo = ZoneInfo("Africa/Cairo")
    local = start.astimezone(cairo).replace(hour=10, minute=0)
    while local.weekday() == 4:
        local += timedelta(days=1)
    booking = client.post(
        "/api/appointments",
        json={
            "patient_id": first,
            "kind": "first_visit",
            "start_at": local.isoformat(),
            "end_at": (local + timedelta(minutes=30)).isoformat(),
        },
    )
    assert booking.status_code == 201, booking.text
    aid = booking.json()["id"]
    assert (
        client.post(
            "/api/visits", json={"patient_id": second, "appointment_id": aid}
        ).status_code
        == 400
    )
    linked = visit(client, first, appointment_id=aid)
    assert linked["appointment_id"] == aid
    assert client.post(f"/api/appointments/{aid}/cancel").status_code == 409
    assert (
        client.post(
            f"/api/appointments/{aid}/reschedule",
            json={
                "start_at": (local + timedelta(hours=1)).isoformat(),
                "end_at": (local + timedelta(hours=1, minutes=30)).isoformat(),
            },
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/visits", json={"patient_id": first, "appointment_id": aid}
        ).status_code
        == 409
    )
    assert (
        client.post("/api/visits", json={"patient_id": str(uuid4())}).status_code == 404
    )
    assert (
        client.post(
            "/api/visits", json={"patient_id": first, "appointment_id": str(uuid4())}
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/visits/{linked['id']}", json={"expected_revision": 1}
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f"/api/visits/{linked['id']}",
            json={"expected_revision": 1, "psychiatric_note": None},
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/visits/{linked['id']}/addenda", json={"body": " "}
        ).status_code
        == 422
    )
    assert client.get(f"/api/visits/{uuid4()}").status_code == 404
    assert client.get("/api/visits/export").status_code == 403
    assert client.get(f"/api/visits/{linked['id']}/export").status_code == 403
    with factory() as db:
        from app.models.patient import Patient

        db.get(Patient, UUID(second)).active = False
        db.commit()
    assert client.post("/api/visits", json={"patient_id": second}).status_code == 400
