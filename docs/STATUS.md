# Project status

Updated: 2026-10-24. **Sprint 4 Task 4A: doctor-only visit backend implemented. Next task: 4B.**

[Task 4A report](tasks/4A.md) records the clinical API, revision policy, retention concerns and actual database evidence. [Task 3B](tasks/3B.md) retains appointment UI evidence; [ADR-001](architecture/ADR-001.md), [MVP](requirements/MVP.md) and [baseline](requirements/BASELINE.md) remain product constraints.

| Result | Command/check | Evidence |
| --- | --- | --- |
| PASS | `cd backend && .venv/bin/ruff check app migrations tests` | All checks passed. |
| PASS | `cd backend && .venv/bin/pytest -q` | 29 passed, one pre-existing Starlette TestClient deprecation warning. Disposable PostgreSQL fixture upgraded, checked, downgraded, re-upgraded and checked Alembic revisions. |
| PASS | `cd backend && .venv/bin/ruff format --check app migrations tests` | Formatting checked after implementation. |
| NOT TESTED | Windows deployment, live-data migration, clinical print/export | Outside Task 4A; exports remain disabled. |

No frontend files changed. The unrelated pre-existing AGENTS.md edit remains uncommitted. Clinical retention, backup and export policies require clinic approval before live use. Technical checks do not establish clinical readiness or compliance. Next task: **4B**, only when requested.
