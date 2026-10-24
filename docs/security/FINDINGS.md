# Task 6A risk-ranked findings

## SEC-001 — HIGH — Fixed: unbounded pre-auth request buffering

Evidence at base commit `85a1f55`: `backend/app/core/request_limits.py:10–16` bypassed the limiter unless the request was POST `/api/auth/login`; `main.py:51` installed that limiter. Other JSON routes accepted arbitrary body lengths before FastAPI dependency authorization. An unauthenticated LAN client could consume memory with large requests against the sole clinic server. Existing Pydantic character limits run after parsing and are not a transport limit.

Fix: `core/request_limits.py:10–29` now counts actual bytes for every HTTP body, including chunked requests and trailing-slash login. Login remains 8 KiB; other paths are 1 MiB (supports the existing three 20k-character note fields even with JSON escaping). Excess returns generic 413/no-store before parser/auth/database; content is not echoed or logged. `main.py:16,51` installs RequestBodyLimit. Regression: tests/test_security.py body-limit and chunked tests; normal auth/visit/billing workflows still pass. Residual: this bounds one request, not connections, slow streams or total load. No destructive load testing was conducted.

## SEC-002 — HIGH conditional deployment risk — Unverified host/backup/artifact protections

Evidence: ADR-001:44–48,63 specifies key custody, trusted TLS, encrypted backups and Windows packaging, but no `desktop/` implementation or Windows evidence exists. This is an implementation/evidence gap, not a confirmed vulnerable installation. Theft of an unlocked/unencrypted doctor PC, theft of an unencrypted backup, or a tampered privileged installer can bypass all API role checks. Before installation: validate restricted service and DB accounts, loopback PostgreSQL, firewall scope, BitLocker and auto-lock, trusted TLS without certificate bypass, signed/verifiable offline packages, encrypted offline backups with separate keys and a restore drill. These require Windows/clinic operator inputs and were not changed by this bounded audit.

## SEC-003 — MEDIUM — Operational availability/recovery gaps

Evidence: `api/auth.py:98,114` applies per-IP/per-account fixed-window throttles. A shared proxy can aggregate clients; token rotation can invalidate a concurrent tab's CSRF token. `services/auth.py:35–60` persists throttle buckets and audits without a cleanup job. `repositories/visits.py:32–48` returns unpaginated history. `bootstrap.py:16–34` supports a single initial doctor; no receptionist provisioning/password-recovery/revocation workflow exists. Document explicit authorized local provisioning/recovery and test shared-origin proxy behavior before deployment; add bounded history and retention maintenance in an authorized follow-up. None is a demonstrated role escalation.

## SEC-004 — LOW — Public API metadata and pending browser hardening

Evidence: `main.py:31` retains FastAPI docs/OpenAPI/redoc defaults; API JSON has no-store (`main.py:45–49`) but there is no production HTML server/CSP or frame policy yet. Public schema exposes route structure, not patient records. Review production documentation exposure and set CSP/frame/referrer policy on the actual HTML origin during deployment. Reviewed frontend text paths have no raw HTML, eval, browser storage or console sink for clinical content. No XSS chain was confirmed.

## Verification limitation

The initial full backend run reproduced PostgreSQL SQLSTATE `40P01` in the concurrent rescheduling test (34 passed, 1 failed). The focused [appointment deadlock fix](../tasks/appointment-deadlock-fix.md) now orders API calendar writes and the subsequent full backend suite passed 40 tests on disposable PostgreSQL. Raw writers that bypass the API lock may still receive 40P01; neither transaction may double-book. No current dependency-CVE scan, Windows attack simulation, physical theft exercise or backup restore was executed.
