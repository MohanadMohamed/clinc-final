# Project status

Updated: 2026-10-23. **Sprint 2 Task 2A: administrative patient backend implemented. Next task: 2B.**

[Task 2A report](tasks/2A.md) gives the API contract, duplicate handling, files and exact checks. [ADR-001](architecture/ADR-001.md), [MVP](requirements/MVP.md) and [baseline](requirements/BASELINE.md) remain product constraints. Earlier [Task 1A](tasks/1A.md) backend authorization evidence remains in its report. Unfinished frontend and AGENTS.md working-tree edits predate this task and were preserved outside the Task 2A checkpoint.

| Result | Command/check | Evidence |
| --- | --- | --- |
| PASS | `cd backend && .venv/bin/pytest -q` | 17 passed, one known Starlette TestClient deprecation warning. Disposable PostgreSQL fixture checks Alembic migration round trip and schema drift. |
| PASS | `cd backend && .venv/bin/ruff check app migrations tests` | All checks passed. |
| PASS | `cd backend && .venv/bin/ruff format --check app migrations tests` | 28 files formatted. |
| NOT TESTED | Persistent/live database migration, Windows deployment, frontend patient UI | Not part of backend Task 2A; no live database changed. |

No clinical records or patient data were introduced. Technical checks do not establish clinical readiness or compliance. Next task: **2B**, only when requested.
