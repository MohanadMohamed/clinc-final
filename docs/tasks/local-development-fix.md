# Local Ubuntu development fix (post-7B)

Root cause: `Settings.public_origin` rejected every HTTP origin, so Vite's loopback browser requests to `/api/auth/csrf` failed before login. The session cookie was also unconditionally Secure with a `__Host-` prefix, which is unsuitable for ordinary HTTP development.

Changed: `backend/app/core/config.py`, `backend/app/api/auth.py`, `backend/app/services/auth.py`, `backend/app/main.py`, `backend/tests/test_local_development.py`, `frontend/tests/run_browser.py`, `frontend/tests/http_dev.mjs`, `.env.example`, `scripts/dev_local.sh`, `README.md`, and `docs/STATUS.md`. The pre-existing changes to `AGENTS.md`, `backend/app/core/request_limits.py`, `backend/app/main.py`, `backend/tests/test_security.py`, and `docs/security/` were preserved. `.env.example` contained credential-like values before this task; it now has placeholders only. No `.env` content was printed or changed.

Development requires explicit `CLINIC_ENV=development` and an exact loopback HTTP public origin. FastAPI rejects non-loopback peers in that mode. The HTTP cookie has a separate name and remains HttpOnly/SameSite Strict. HTTPS production remains the default, with a Secure `__Host-` cookie, exact origin validation, CSRF, and role checks. No database schema or frontend business feature changed.

Run locally from the repository root: `./scripts/dev_local.sh`, then open `http://127.0.0.1:5173/login` and use an existing account. The script needs installed backend/frontend dependencies and the configured migrated local PostgreSQL database. It does not apply migrations or create users. Bootstrap marker and doctor-account existence in the currently configured database were **true**, based on a read-only query; bootstrap is unnecessary there. For a different fresh database, use the interactive bootstrap command in [README](../../README.md) only after migrations and only once.

Verification (all tests used a separate disposable PostgreSQL cluster and synthetic users; the read-only bootstrap existence check was the sole query against the configured local DB):

- **PASS** — `cd backend && CLINIC_ENV=development CLINIC_PUBLIC_ORIGIN=http://127.0.0.1:5173 .venv/bin/pytest -q --tb=short tests/test_local_development.py`: 7 passed. Covers origin validation, CSRF, invalid login, session rotation/logout, role denial and remote-peer denial.
- **PASS** — `cd backend && CLINIC_ENV=production CLINIC_PUBLIC_ORIGIN=https://clinic.local .venv/bin/pytest -q --tb=short`: 49 passed, including patient/appointment/security regressions. The suite's existing HTTPS fixtures require these explicit test defaults if a developer `.env` selects HTTP development.
- **PASS** — `cd frontend && npm run build && npm test`: production build succeeded; Vitest 4 files/7 tests passed.
- **PASS** — `backend/.venv/bin/python frontend/tests/run_browser.py --http-dev-only`: real headless Chrome through Vite and FastAPI on HTTP loopback; CSRF handshake, missing CSRF 403, invalid login, doctor/receptionist login, receptionist clinical 403, patient/appointment reads, logout, refresh, Arabic RTL and no relevant console errors.
- **PASS** — `backend/.venv/bin/python frontend/tests/run_browser.py --tls-only`: existing HTTPS trust/SAN, Secure cookie, CSRF, logout and proxy-hardening checks still pass on a disposable database.
- **PASS** — `cd backend && .venv/bin/ruff check app/core/config.py app/services/auth.py app/api/auth.py app/main.py tests/test_local_development.py`.
- **PASS** — `bash -n scripts/dev_local.sh` and `git diff --check`.
- **NOT TESTED** — Windows service, certificate and installer behavior (outside this local fix).

Known limits: the separate HTML browser flows do not exercise every business mutation; the full backend suite covers those APIs. The current local database's doctor username/password were neither inspected nor reset. Browser verification used synthetic accounts in an isolated database. Existing uncommitted security-audit changes are excluded from this task checkpoint.

Next planned task: **8A**, only when requested.
