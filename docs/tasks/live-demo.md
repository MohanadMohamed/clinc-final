# Render portfolio demo preparation — local checkpoint

Scope: separate, synthetic-only public portfolio environment. The clinic's two-Windows-PC LAN deployment remains the product architecture. The Render service has **not** been created or exposed. The public gate defaults closed. See [controlled setup, threat boundary and blockers](../LIVE_DEMO_DEPLOYMENT.md).

Changed files: `Dockerfile.render`, `.dockerignore`, `scripts/render_start.sh`, `backend/app/core/config.py`, `backend/app/main.py`, `backend/app/api/auth.py`, `backend/app/demo_db_role.py`, `backend/app/demo_provision.py`, `backend/tests/test_render_demo.py`, `frontend/src/App.tsx`, `frontend/tests/run_browser.py`, `frontend/tests/render_demo.mjs`, `docs/LIVE_DEMO_DEPLOYMENT.md`, `docs/STATUS.md`, and this report. Pre-existing edits to `frontend/src/main.tsx` and `clinc-final_README.md` are untouched.

| Result | Exact command / scope | Evidence |
| --- | --- | --- |
| PASS | `cd frontend && VITE_DEMO_MODE=true npm run build` | TypeScript and Vite production build completed, 2,092 modules. |
| PASS | `cd frontend && npm test` | Vitest: 4 files, 7 tests. |
| PASS | `cd backend && CLINIC_ENV=production CLINIC_PUBLIC_ORIGIN=https://clinic.local .venv/bin/pytest -q --tb=short` | Disposable PostgreSQL: 54 tests passed; one Starlette TestClient deprecation warning. Includes migrations, auth/CSRF/RBAC, patients, appointments/concurrency, visits and billing. |
| PASS | `cd backend && CLINIC_ENV=production CLINIC_PUBLIC_ORIGIN=https://clinic.local .venv/bin/pytest -q --tb=short tests/test_render_demo.py` | Five Render-specific tests passed after the final relative `/app` redirect change; one Starlette deprecation warning. |
| PASS | `cd backend && .venv/bin/ruff check app/api/auth.py app/core/config.py app/main.py app/demo_db_role.py app/demo_provision.py tests/test_render_demo.py && .venv/bin/ruff format --check app/api/auth.py app/core/config.py app/main.py app/demo_db_role.py app/demo_provision.py tests/test_render_demo.py` | Lint and formatting completed. |
| PASS | `sh -n scripts/render_start.sh && bash -n scripts/render_start.sh` | Startup script parses; missing Render marker exits 1 before launching Uvicorn. |
| PASS | `cd frontend && npm audit --omit=dev --audit-level=high` | Production npm dependency audit returned exit 0, high=0, critical=0 (networked registry check). |
| PASS | `backend/.venv/bin/python frontend/tests/run_browser.py --render-demo-only` | Local bundled-app Chrome/TLS probe against disposable PostgreSQL: deep links, Arabic RTL/demo banner, login/logout, Secure cookie, both roles, patient/appointment/billing reads, clinical 403, headers, no external requests or console errors. Browser test accepts its local self-signed certificate; Render certificate validity is NOT TESTED. |
| NOT TESTED | `docker build -f Dockerfile.render .`, image/CVE scan, actual Render service, edge HTTP→HTTPS/TLS/forwarded-IP, managed DB private network and backup/restore | Docker/Podman/Buildah absent; no Render resource or external publication authorized in this preparation step. Python dependency CVE scan also unavailable. These block public exposure. |

The browser probe initially failed because a normal `npm run build` overwrote `frontend/dist` without the demo compile flag; the Dockerfile uses `VITE_DEMO_MODE=true`. The correct demo build and probe passed. The backend suite initially could not start disposable PostgreSQL because the sandbox denied its Unix socket; it passed when run with local socket permission. No production or development database was modified.

Run steps: build the demo assets with `cd frontend && VITE_DEMO_MODE=true npm run build`; run the disposable browser probe from the repository root as shown above. For actual Render setup, follow [LIVE_DEMO_DEPLOYMENT.md](../LIVE_DEMO_DEPLOYMENT.md) in order and keep `CLINIC_DEMO_PUBLIC_ENABLED=false` until every blocker is cleared. The next planned clinic task is **8A**, not started here.
