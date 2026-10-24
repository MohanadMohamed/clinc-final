"""Local HTTPS checks with explicit trust, hostname validation and real API login."""

import os
import socket
import ssl

import httpx

origin = "https://localhost:8443"
trusted = ssl.create_default_context(cafile=os.environ["CLINIC_TEST_CERT"])
with httpx.Client(
    base_url=origin, verify=trusted, trust_env=False, timeout=5
) as client:
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/health/ready").json() == {"status": "ready"}
    response = client.get(
        "/app",
        headers={
            "X-Forwarded-Proto": "http",
            "X-Forwarded-Host": "evil.invalid",
            "X-Forwarded-For": "203.0.113.9",
        },
    )
    assert response.status_code in (307, 308)
    assert response.headers["location"] == origin + "/app/"
    csrf = client.get("/api/auth/csrf", headers={"origin": origin})
    cookie = csrf.headers["set-cookie"]
    assert all(
        flag in cookie for flag in ("Secure", "HttpOnly", "SameSite=strict", "Path=/")
    )
    assert "Domain=" not in cookie
    login = client.post(
        "/api/auth/login",
        headers={"origin": origin, "x-csrf-token": csrf.json()["csrf_token"]},
        json={"username": "synthetic.doctor", "password": os.environ["TEST_PASSWORD"]},
    )
    assert login.status_code == 200
    assert client.get("/api/me").json()["role"] == "doctor"
    token = client.get("/api/auth/csrf", headers={"origin": origin}).json()[
        "csrf_token"
    ]
    assert (
        client.post(
            "/api/auth/logout",
            headers={"origin": "https://evil.invalid", "x-csrf-token": token},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/auth/logout", headers={"origin": origin, "x-csrf-token": token}
        ).status_code
        == 204
    )
    assert client.get("/api/me").status_code == 401
for context, hostname in [
    (ssl.create_default_context(), "localhost"),
    (trusted, "wrong.invalid"),
]:
    try:
        with (
            socket.create_connection(("127.0.0.1", 8443), timeout=5) as sock,
            context.wrap_socket(sock, server_hostname=hostname),
        ):
            raise AssertionError("Untrusted chain or wrong SAN was accepted")
    except ssl.SSLCertVerificationError:
        pass
print(
    "PASS TLS: explicit trust and SAN, untrusted/wrong-host rejection, forwarded headers ignored, health/readiness, Secure cookies, CSRF and logout"
)
