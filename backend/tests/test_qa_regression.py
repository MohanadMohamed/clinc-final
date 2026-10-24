"""Cross-role HTTP regression on the disposable PostgreSQL fixture."""

from uuid import uuid4

from fastapi.testclient import TestClient
from test_auth import login, token

pytest_plugins = ["test_auth"]


def test_independent_sessions_admin_clinical_and_billing(auth):
    doctor, password, _, _ = auth
    reception = TestClient(doctor.app, base_url="https://clinic.local")
    reception.headers["origin"] = "https://clinic.local"
    try:
        assert doctor.get("/api/me").status_code == 401
        assert reception.get("/api/me").status_code == 401
        assert login(doctor, password).status_code == 200
        assert login(reception, password, "synthetic.reception").status_code == 200
        token(doctor)
        token(reception)
        assert doctor.get("/api/me").json()["role"] == "doctor"
        assert reception.get("/api/me").json()["role"] == "receptionist"

        assert (
            reception.post(
                "/api/patients", json={"full_name": "Synthetic", "phone": 123}
            ).status_code
            == 422
        )
        patient_response = reception.post(
            "/api/patients",
            json={"full_name": "Synthetic QA Patient", "phone": "120000001"},
        )
        assert patient_response.status_code == 201
        patient_id = patient_response.json()["id"]
        assert doctor.get(f"/api/patients/{patient_id}").status_code == 200

        marker = "SYNTHETIC_QA_PRIVATE_NOTE"
        visit_response = doctor.post(
            "/api/visits", json={"patient_id": patient_id, "neurological_note": marker}
        )
        assert visit_response.status_code == 201
        visit_id = visit_response.json()["id"]
        assert (
            doctor.get(f"/api/visits/{visit_id}").json()["neurological_note"] == marker
        )
        for response in (
            reception.get("/api/visits"),
            reception.get(f"/api/visits/{visit_id}"),
            reception.get(f"/api/visits/{uuid4()}"),
            reception.post("/api/visits/search", json={"search": marker}),
        ):
            assert response.status_code == 403
            assert marker not in response.text
        assert marker not in reception.get(f"/api/patients/{patient_id}").text

        fee = doctor.post(
            "/api/billing/fees",
            json={
                "kind": "first_visit",
                "amount_minor": 10000,
                "reason": "Synthetic QA fee",
            },
        )
        assert fee.status_code == 201
        invoice = reception.post(
            "/api/billing/invoices",
            json={
                "idempotency_key": str(uuid4()),
                "patient_id": patient_id,
                "kind": "first_visit",
            },
        )
        assert invoice.status_code == 201
        assert marker not in invoice.text
        invoice_id = invoice.json()["id"]
        assert doctor.get(f"/api/billing/invoices/{invoice_id}").status_code == 200
        assert reception.get(f"/api/billing/invoices/{invoice_id}").status_code == 200
        assert doctor.post("/api/auth/logout").status_code == 204
        assert doctor.get("/api/me").status_code == 401
        assert reception.get("/api/me").json()["role"] == "receptionist"
    finally:
        reception.close()
