# Project status

Updated: 2026-10-23. **Sprint 2 Task 2B: Arabic patients frontend slice implemented. Next task: 3A.**

[Task 2B report](tasks/2B.md) gives the UI contract, files and exact checks. [Task 2A](tasks/2A.md) remains backend evidence; [Task 1A](tasks/1A.md) documents server authorization. [ADR-001](architecture/ADR-001.md), [MVP](requirements/MVP.md) and [baseline](requirements/BASELINE.md) remain product constraints.

| Result | Command/check | Evidence |
| --- | --- | --- |
| PASS | `cd frontend && npm run build` | TypeScript and Vite build completed, 2084 modules transformed. |
| PASS | `cd frontend && npm test` | 3 tests passed. |
| PASS | `python3 frontend/tests/run_browser.py` | Real Chrome/local HTTPS/disposable PostgreSQL; patient interactions, anonymous denial, invalid login, roles, refresh, RTL, mobile menu and persistence after FastAPI restart passed. |
| NOT TESTED | Windows pywebview and real clinic deployment | Out of scope. |

The pre-existing AGENTS.md working-tree edit remains uncommitted. No clinical data was used. Technical checks do not establish clinical readiness or compliance. Next task: **3A**, only when requested.
