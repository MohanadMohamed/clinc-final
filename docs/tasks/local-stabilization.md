# Local-first stabilization checkpoint

Date: 2026-10-27. Branch: `codex/local-stabilization`. Scope: audit and verify existing local workflows; pause cloud work. See [release status](../LOCAL_RELEASE_STATUS.md) for architecture, matrix, exact commands, release limits and next milestone 8A (not started).

## Changes

- `frontend/tests/run_browser.py`: HTTP-mode browser check invokes the real `scripts/dev_local.sh` from a temporary directory, waits for DB readiness, terminates its separate process group and waits on cleanup. Other modes retain their existing setup.
- `frontend/tests/after_restart.mjs`: verify scheduled/cancelled appointments, saved finalized visit/follow-up and exact invoice/payment balances after API restart, in addition to patient persistence; verify logout invalidation.
- `README.md`: local-first guidance, reproducible test commands and prerequisites; cloud instructions clearly separated/paused. No conflict markers found.
- `docs/LOCAL_RELEASE_STATUS.md`, `docs/STATUS.md`, this report: current evidence and limitations.

No application code, schema, auth, TLS, role rules or dependencies changed. No reproduced product defect required a fix. The prior HTTP harness launched servers itself, so it did not substantiate the documented launcher; the new path closes that coverage gap. The prior restart test asserted only patient persistence; now all major persisted modules are checked.

## Executed verification

Commands run from repository root except where stated. All finished with exit 0.

| Status | Command | Evidence |
|---|---|---|
| PASS | In `backend`: `CLINIC_ENV=production CLINIC_DEPLOYMENT=clinic_lan CLINIC_PUBLIC_ORIGIN=https://clinic.local .venv/bin/pytest -q --tb=short` | 68 passed, 7 pre-existing deprecation warnings; fresh private PostgreSQL cluster. Existing demo-helper regression tests also use this local cluster, never Neon. |
| PASS | In `frontend`: `npm test && npm run build` | 7 Vitest tests, 4 files; TypeScript and Vite production build completed. |
| PASS | `backend/.venv/bin/python frontend/tests/run_browser.py` | Initial baseline and final strengthened rerun both pass: reception patient management, independent doctor session, concurrent 409 booking, reschedule/cancel, scheduled visit/draft/history/finalize, clinical 403, invoice/payment/receipt/report, refresh, API restart persistence, logout. |
| PASS | `backend/.venv/bin/python frontend/tests/run_browser.py --http-dev-only` | Actual launcher from outside checkout; both roles, invalid login, CSRF, clinical denial, refresh/logout, RTL, no unexpected browser errors. |
| PASS | `backend/.venv/bin/python frontend/tests/run_browser.py --qa-only` | 1440×900/390×844 RTL, responsive pages, independent sessions/logout, network failure and retry. |
| PASS | `backend/.venv/bin/python frontend/tests/run_browser.py --static-only` | Built React on FastAPI without Vite; local assets, deep links, roles, API/docs separation. |
| PASS | `backend/.venv/bin/python -m pytest desktop/tests -q` | 5 tests, 11 subtests; launcher/config unit tests only. |
| PASS | `bash -n scripts/dev_local.sh` | Shell syntax valid. |

No failing application check remains in this slice. Browser test temporary TLS trust/no-sandbox allowances do not establish deployed TLS/Windows security. Existing deprecation warnings remain. No screenshots were saved; receipt PDF rendering is checked in memory.

## Preservation and limits

Dedicated branch created before edits. Four existing untracked user files (`README (1).md`, `clinc-final_README.md`, `mermaid-diagram (1).png`, `mermaid-diagram.png`) left untouched and excluded from checkpoint. No existing database reset, migration or record access; test migrations/truncation/cleanup occur only in newly created disposable clusters. Local `.env` was not displayed. No cloud connection, push or deployment.

Windows GUI/EXE, real LAN operation, physical printing, backup restore and power-loss recovery: **NOT TESTED**. User's existing local database/account configuration: **NOT TESTED**, intentionally preserved. Local operation with supplied disposable configuration is verified. Technical checks do not establish clinical readiness.
