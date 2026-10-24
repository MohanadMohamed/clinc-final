"""Task 6A: enumerate the real API; never replace authorization dependencies."""

import asyncio
import re
from uuid import uuid4

from test_auth import login, token

from app.core.request_limits import RequestBodyLimit

pytest_plugins = ["test_auth"]

PUBLIC = {
    ("GET", "/api/health"),
    ("GET", "/api/health/ready"),
    ("GET", "/api/auth/csrf"),
    ("POST", "/api/auth/login"),
}
STAFF = {
    ("GET", "/api/me"),
    ("GET", "/api/auth/session"),
    ("POST", "/api/auth/logout"),
    ("GET", "/api/patients"),
    ("POST", "/api/patients"),
    ("GET", "/api/patients/{patient_id}"),
    ("PATCH", "/api/patients/{patient_id}"),
    ("POST", "/api/patients/{patient_id}/archive"),
    ("GET", "/api/appointments"),
    ("POST", "/api/appointments"),
    ("POST", "/api/appointments/{appointment_id}/cancel"),
    ("POST", "/api/appointments/{appointment_id}/reschedule"),
    ("GET", "/api/billing/fees"),
    ("GET", "/api/billing/invoices"),
    ("POST", "/api/billing/invoices"),
    ("GET", "/api/billing/invoices/{invoice_id}"),
    ("GET", "/api/billing/invoices/{invoice_id}/payments"),
    ("POST", "/api/billing/invoices/{invoice_id}/payments"),
    ("POST", "/api/billing/invoices/{invoice_id}/issue"),
    ("GET", "/api/billing/summary/{day}"),
}
DOCTOR = {
    ("POST", "/api/billing/fees"),
    ("POST", "/api/billing/invoices/{invoice_id}/adjustments"),
    ("POST", "/api/billing/invoices/{invoice_id}/void"),
    ("POST", "/api/billing/payments/{payment_id}/reverse"),
    ("GET", "/api/visits"),
    ("POST", "/api/visits"),
    ("POST", "/api/visits/search"),
    ("GET", "/api/visits/export"),
    ("GET", "/api/visits/{visit_id}"),
    ("PATCH", "/api/visits/{visit_id}"),
    ("GET", "/api/visits/{visit_id}/history"),
    ("GET", "/api/visits/{visit_id}/export"),
    ("POST", "/api/visits/{visit_id}/finalize"),
    ("POST", "/api/visits/{visit_id}/addenda"),
}


def url(path):
    return re.sub(r"\{[^}]+\}", str(uuid4()), path.replace("{day}", "2026-10-24"))


def test_every_api_endpoint_has_explicit_permission_and_csrf(auth):
    client, password, _, _ = auth
    actual = {
        (method.upper(), path)
        for path, operations in client.app.openapi()["paths"].items()
        if path.startswith("/api/")
        for method in operations
        if method.upper() in {"GET", "POST", "PATCH", "DELETE", "PUT"}
    }
    assert actual == PUBLIC | STAFF | DOCTOR  # New endpoints require a policy decision.
    for method, path in sorted(STAFF | DOCTOR):
        assert client.request(method, url(path), json={}).status_code == 401, (
            method,
            path,
        )
    for username, role in [
        ("synthetic.reception", "receptionist"),
        ("synthetic.doctor", "doctor"),
    ]:
        assert login(client, password, username).status_code == 200
        token(client)
        for method, path in sorted(STAFF | DOCTOR):
            if path == "/api/auth/logout":
                continue
            response = client.request(method, url(path), json={})
            denied = (method, path) in DOCTOR and role == "receptionist"
            if denied or path.endswith("/export"):
                assert response.status_code == 403, (role, method, path)
            else:
                assert response.status_code in {200, 400, 404, 422}, (
                    role,
                    method,
                    path,
                    response.status_code,
                )
            if method not in {"GET", "HEAD"}:
                assert (
                    client.request(
                        method, url(path), json={}, headers={"x-csrf-token": "invalid"}
                    ).status_code
                    == 403
                )
        assert (
            client.post(
                "/api/auth/logout", headers={"x-csrf-token": "invalid"}
            ).status_code
            == 403
        )
        assert client.post("/api/auth/logout").status_code == 204
        assert client.get("/api/me").status_code == 401


def test_body_limit_precedes_parsing_and_auth(auth):
    client, _, _, _ = auth
    for path in ["/api/visits", "/api/patients", "/api/billing/invoices"]:
        response = client.post(path, content=b"x" * 1048577)
        assert response.status_code == 413
        assert response.headers["cache-control"] == "no-store"
        assert len(response.content) < 100


def test_chunked_body_limit_without_content_length():
    async def scenario():
        called, responses = [], []

        async def app(scope, receive, send):
            called.append(True)

        chunks = iter(
            [{"type": "http.request", "body": b"x" * 600000, "more_body": True}] * 2
        )

        async def receive():
            return next(chunks)

        async def send(message):
            responses.append(message)

        await RequestBodyLimit(app)(
            {"type": "http", "method": "PATCH", "path": "/api/visits/example"},
            receive,
            send,
        )
        assert not called
        assert responses[0]["status"] == 413

    asyncio.run(scenario())
