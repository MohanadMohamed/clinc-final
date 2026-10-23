# Project status

Updated: 2026-10-23. **Sprint 1 Task 1A: backend authentication implemented. Next task: 1B.**

[1A report](tasks/1A.md) documents sessions, CSRF, roles, audit, throttling, local bootstrap, exact commands and limits. [Baseline](requirements/BASELINE.md) and [ADR-001](architecture/ADR-001.md) remain authoritative. Frontend unchanged; no patient functionality.

## Evidence

Commands below ran from `backend/` on Ubuntu on 2026-10-23:

| Result | Command/check | Evidence |
| --- | --- | --- |
| PASS | `.venv/bin/pytest -q` | 16 passed in 13.60s; one known Starlette TestClient deprecation warning. |
| PASS | Disposable PostgreSQL migrations, executed by pytest fixture | `alembic upgrade head`, `alembic check`, `alembic downgrade 0001_baseline`, `alembic upgrade head`, `alembic check`; no schema drift. No existing database used. |
| PASS | `.venv/bin/ruff check .` | All checks passed. |
| PASS | `.venv/bin/ruff format --check .` | 24 files already formatted. |
| PASS | `.venv/bin/python -m pip check` | No broken requirements found. |
| PASS | Local Markdown link validation; `git diff --check`; `git diff --name-only -- frontend` (repository root) | All 51 local links across 10 documents resolve; no whitespace errors; no frontend changes. |
| NOT TESTED | Real browser, pywebview, Windows, TLS certificates and manual interactive bootstrap UX | Outside this Ubuntu backend run; bootstrap transaction and noninteractive rejection were tested. |

Tests cover unauthenticated 401, wrong-role 403, logout replay, session rotation/expiry, disabled accounts, CSRF/Origin checks, account/IP/concurrent throttling, rejected role injection, fixed database roles, one-time bootstrap and bounded login bodies. Checkpoint: `feat: add backend session authentication for Task 1A`.

## Scope and risks

Public endpoints are health and the CSRF/login handshake. Protected routes use `require_user` / `require_role` and server-authoritative user roles. Receptionist accounts cannot pass doctor-only dependencies; test-only routes verify this without adding clinical features. No public registration or role editing endpoint exists.

TLS cookies are always Secure. The untouched HTTP development frontend cannot yet perform login; browser integration belongs to later scope. Windows, browser/pywebview, real TLS and manual terminal-bootstrap interaction are NOT TESTED. Session/throttle cleanup and audit-retention policy remain operational work. Account throttling can temporarily deny legitimate login under attack. Starlette's HTTPX TestClient deprecation warning remains. Technical checks do not establish clinical readiness or compliance.

**Next task: 1B**, only when requested. Prior [0A](tasks/0A.md) and [0B](tasks/0B.md) reports remain historical evidence.
