# Live-demo local verification handoff — 2026-10-27

This pass changed only the public `README.md`, a manual CI image-verification workflow, deployment handoff documentation and status. The pre-existing edit to `frontend/src/main.tsx`, the untracked `clinc-final_README.md` draft and two untracked diagram images were preserved. No Render service/database was created; no Git push, public gate change, migration or real-data operation was performed. The original Windows LAN architecture is unchanged.

## Passed locally

| Check | Exact command / evidence |
| --- | --- |
| React demo build and Vitest | `cd frontend && VITE_DEMO_MODE=true npm run build && npm test` — exit 0; 2,092 modules built, 4 files / 7 tests passed. |
| Render-specific backend | `cd backend && CLINIC_ENV=production CLINIC_PUBLIC_ORIGIN=https://clinic.local .venv/bin/pytest -q --tb=short tests/test_render_demo.py` — exit 0; 5 tests passed on disposable PostgreSQL, one Starlette deprecation warning. Covers default-closed gate, liveness/readiness, Host/docs, Secure/HttpOnly/SameSite cookies, CSRF, roles, static routing and restricted DB-role grants. The prior full-suite result of 54 passes was not rerun in this documentation-only pass. |
| Real local browser | `backend/.venv/bin/python frontend/tests/run_browser.py --render-demo-only` — exit 0; disposable PostgreSQL + local TLS Chrome checked Arabic RTL, deep links, assets, login/logout, invalid password, sessions, doctor/reception separation, clinical 403 and no relevant console errors. Its local self-signed certificate is accepted by the test; this does not verify Render TLS. |
| Frontend dependency audit | `cd frontend && npm audit --omit=dev --audit-level=high` — exit 0, `found 0 vulnerabilities` against the npm registry. |
| Pinned Python advisories | Python standard-library `urllib` queried PyPI's release-specific JSON advisory endpoint for all 36 `backend/requirements.txt` pins — exit 0; 0 active advisories, 0 lookup errors. This checks PyPI's known release advisories; it does not inspect OS packages or replace `pip-audit` on the built image. |
| Static deployment checks | `sh -n scripts/render_start.sh`; Python/PyYAML parsed `.github/workflows/verify-render-demo.yml` and `bash -n` checked every embedded run block; Dockerfile `COPY` sources and `.dockerignore` private-file exclusions were checked without reading local secrets. README has no conflict markers; local links resolve. These checks do not establish image contents. |

## Failed attempts and blocked checks

- `docker build --pull -f Dockerfile.render -t clinic-render-demo:verify .` exited **127**: `docker: command not found`. Podman and Buildah are also absent. No software was installed.
- `trivy image --exit-code 1 --severity HIGH,CRITICAL clinic-render-demo:verify` exited **127**: `trivy: command not found`; there is no built image to scan. No critical/high image finding can be ruled out.
- `python -m pip_audit` is unavailable locally. The PyPI release check above is a narrower standard-library audit; the manual CI workflow runs the official pinned pip-audit action on the same requirements file.
- The first unprivileged `npm audit` attempt failed DNS (`EAI_AGAIN`); the network-authorized retry above passed. The application tests did not fail.

## Still requires approved CI and Render

The [manual CI workflow](../../.github/workflows/verify-render-demo.yml) uses read-only GitHub permissions and `workflow_dispatch` only. It builds the exact Dockerfile, inventories `/srv/clinic` for private file names, starts the production container with a deliberately unreachable synthetic DB to assert the gate remains closed, audits Python/npm pins and scans the built image for high/critical OS and library vulnerabilities. **The workflow itself has not run**: it requires an approved push to the default branch. Review and triage any findings before deployment; do not loosen scans to make them green.

Actual Render HTTPS/HTTP redirect, proxy forwarded-IP contract, Postgres private access, runtime secrets, restricted app-role behavior, backups/logs, and access-restricted staging flows are **NOT TESTED**. Render's native web-service inbound IP rules require a Scale or Enterprise workspace; otherwise obtain and verify an equivalent restriction or keep both gates closed. No public exposure is approved by this report. The [deployment guide](../LIVE_DEMO_DEPLOYMENT.md#restricted-staging-handoff--commands-to-run-only-after-approval) contains the exact conditional `gh`, `render` and `curl` commands, account/migration steps, and stop/delete instructions. Next planned clinic task: **8A**, not started.
