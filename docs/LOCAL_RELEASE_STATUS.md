# Local release status

Audit date: 2026-10-27. Scope: stabilize the existing application on Ubuntu; cloud work paused. No public deployment, cloud access, database reset, dependency replacement or new module. This is a verified local development slice, not approval for real medical records or a Windows release.

## Actual architecture

React/TypeScript enters through `frontend/src/main.tsx` and `App.tsx`; Vite proxies `/api` to loopback FastAPI. `backend/app/main.py` assembles authentication, patients, appointments, visits and billing routers. Models, allowlisted schemas, repositories and services share PostgreSQL transactions. Alembic revisions `0001`–`0006` implement baseline, authentication, patients, appointments, visits and billing. Normal startup does not migrate or provision accounts.

Built assets are served by FastAPI at `/app/` with history fallback; `/api` and local `/docs` remain separate. The pywebview launcher opens that origin and starts neither a backend nor a database. Final architecture remains two Windows PCs: doctor hosts the sole PostgreSQL and FastAPI services plus a client; reception runs only a client over trusted LAN HTTPS. No Internet service is required in normal operation.

## Verification matrix

All executed checks below used synthetic records and newly created disposable PostgreSQL clusters. No existing development database or account was inspected or changed. No screenshots were produced.

| Feature | Status | Evidence | Remaining Work |
|---------|--------|----------|----------------|
| Ubuntu startup | PASS | `--http-dev-only` now runs the actual `scripts/dev_local.sh` from a temporary working directory; frontend and DB readiness checked before browser actions | Existing user database/configuration deliberately untouched |
| Authentication, expiry, CSRF, throttling | PASS | Backend auth/local-development tests; real browser invalid login, refresh, logout and independent sessions | Operator account recovery/provisioning UX remains a separate release concern |
| Every protected API role policy | PASS | `test_every_api_endpoint_has_explicit_permission_and_csrf` enumerates current OpenAPI routes; unauthenticated 401, receptionist doctor-route 403, mutation CSRF checks | Re-run when adding endpoints |
| Patient administration | PASS | Browser create/search/details/edit/archive, validation, pagination; backend error/duplicate/archive checks | No real-data acceptance claimed |
| Appointments | PASS | Browser reception booking visible to doctor; independent contexts contend for slot, Arabic 409, reschedule and cancellation; DB concurrency/DST tests | Windows LAN latency not exercised |
| Doctor-only visits | PASS | Scheduled visit start, draft save, history, follow-up, unsaved warning, finalization; receptionist route/API denial; backend guesses/search/exports denied | Clinical export disabled; retention/operational policy unresolved |
| Billing and dashboard | PASS | Fees, invoice/payment, exact integer amounts, daily API-backed summary, empty ledger, print CSS/PDF generation, reception fee-change 403 | Physical printer and Windows print output untested |
| Refresh and restart persistence | PASS | Full browser rerun verifies patients, scheduled/cancelled appointment history, finalized visit/follow-up and exact invoice/payment balances after FastAPI restart, then logout 401 | Database-server reboot/power-loss recovery not tested |
| RTL/responsive/error states | PASS | `--qa-only`: Arabic RTL at 1440×900 and 390×844, navigation, network failure/retry, logout isolation, no unexpected console/page errors | Human visual/accessibility review remains advisable; not an exhaustive accessibility audit |
| Frontend production build | PASS | `npm run build`: TypeScript and Vite, exit 0 | None for this slice |
| Vitest | PASS | `npm test`: 7 tests / 4 files, exit 0 | Focused suite, not exhaustive UI coverage |
| Backend regression | PASS | 68 pytest tests, 7 existing deprecation warnings, exit 0; fixture migration upgrade/check/downgrade/upgrade only in new test cluster | Starlette HTTPX and Alembic path-separator deprecations remain |
| Production asset routing | PASS | `--static-only`: FastAPI without Vite, `/app/` deep links, local assets, roles, `/api` and `/docs` isolation | Does not establish Windows runtime acceptance |
| Desktop/config unit checks | PASS | 5 tests and 11 subtests | Unit evidence only |
| Windows services/EXE/pywebview GUI | NOT TESTED | No Windows environment or actual GUI packaging execution | Build/test on Windows; see below |
| Physical security, backup/restore | NOT TESTED | No workstation or backup operations in this task | Encryption, key custody, restore drill and operator policies |
| Cloud deployment | NOT TESTED | Explicitly paused; existing files preserved | No action in this task |

## Exact local commands

From the repository root, install dependencies once as described in [README](../README.md). Keep the existing untracked local configuration; never overwrite it with demo settings. PostgreSQL must already run locally with the intended development database. Use existing named synthetic accounts. Do not rerun bootstrap against an existing doctor account. Initial account setup for a genuinely new database is documented in [1A](tasks/1A.md).

```bash
./scripts/dev_local.sh
```

Open `http://127.0.0.1:5173/login`; DB readiness is `/api/health/ready` on the same origin. The script binds both development servers to loopback, uses explicit development HTTP and does not migrate, seed or reset anything. Stop with Ctrl-C. Network/production mode still requires HTTPS. No Docker, proxy, public hostname, cloud credential or Internet connection is required after local prerequisites are installed.

Run browser commands sequentially with development servers stopped (ports 5173, 8000 and 8443 must be free). PostgreSQL 18 binaries and Chrome at `/usr/bin/google-chrome` are current test prerequisites.

```bash
cd backend
CLINIC_ENV=production CLINIC_DEPLOYMENT=clinic_lan CLINIC_PUBLIC_ORIGIN=https://clinic.local .venv/bin/pytest -q --tb=short
cd ../frontend
npm test
npm run build
cd ..
backend/.venv/bin/python frontend/tests/run_browser.py
backend/.venv/bin/python frontend/tests/run_browser.py --http-dev-only
backend/.venv/bin/python frontend/tests/run_browser.py --qa-only
backend/.venv/bin/python frontend/tests/run_browser.py --static-only
backend/.venv/bin/python -m pytest desktop/tests -q
bash -n scripts/dev_local.sh
```

## Fixes and security boundaries

No reproducible product startup/authentication/workflow failure was found in the executed checks, so no application functionality was rewritten. Closed a verification gap: the HTTP browser harness now tests the actual local launcher from outside the checkout, waits for database readiness, and cleans up its dedicated process group including the reload child. Expanded restart assertions across saved appointments, visits and billing. Updated the README to separate paused cloud work and provide current test commands.

The server, not route visibility, enforces roles. Clinical models/endpoints are separate from administrative schemas; billing serializations exclude clinical text. Current frontend source search found no localStorage/sessionStorage, console logging, raw HTML injection or eval sinks. Auth/visit regression tests also check sensitive logging. This focused review is not a new penetration test or dependency vulnerability scan.

Existing HTTPS browser fixtures use self-signed test-certificate acceptance and Chrome's test-only no-sandbox flag; those passes do not prove deployed certificate trust or browser process isolation. No production TLS behavior was weakened. Loopback HTTP tests explicitly verify CSRF and role denial; production config tests reject HTTP. Review historical [security findings](security/FINDINGS.md) with later implementation evidence: some historical statements predate static serving/desktop templates and are not current feature inventories.

## Release limits and next work

Windows templates exist for service supervision, PostgreSQL loopback binding, firewall rules and certificate provisioning. They are review templates, not an installed/tested release. `desktop/launcher.py` validates an HTTPS origin and opens `/app/`; final PyInstaller packages, installer tooling, actual WebView runtime, reboot/service recovery, LAN trust, printing and offline Windows operation remain unverified. See [desktop instructions](../desktop/README.md) and [LAN templates](../desktop/packaging/README.md).

Before real records: decide backup/retention/recovery policies, verify restricted service/database accounts, encrypt workstations/backups, test restoration and account recovery, and obtain appropriate privacy/security review. No certification or clinical readiness is claimed.

Recommended next clinic milestone: **8A**, a separately authorized Windows build/test milestone after reviewing this local evidence; not started here. Optional future task: clearly labeled static synthetic portfolio showcase, with no backend or real records. No showcase was built. Render/Neon configuration remains intact and paused.
