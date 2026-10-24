# Project status

Updated: 2026-10-24. **Sprint 5 Task 5A: billing backend implemented. Next task: 5B.**

[Task 5A report](tasks/5A.md) records the EGP billing API, role rules and database evidence. [Task 4B](tasks/4B.md) retains visit UI evidence; [ADR-001](architecture/ADR-001.md), [MVP](requirements/MVP.md) and [baseline](requirements/BASELINE.md) remain product constraints.

| Result | Command/check | Evidence |
| --- | --- | --- |
| PASS | `cd backend && .venv/bin/ruff check app migrations tests` | All checks passed. |
| PASS | `cd backend && .venv/bin/ruff format --check app migrations tests` | Formatting checked. |
| PASS | `cd backend && .venv/bin/pytest -q` | 32 passed on disposable PostgreSQL, including Alembic upgrade/check/downgrade/re-upgrade/check, payment retry, role and concurrent balance tests. |
| NOT TESTED | Windows deployment, live finance data, receipt printing | Outside Task 5A. |

The unrelated pre-existing AGENTS.md edit remains uncommitted. Financial correction, receipt, retention and backup policies require clinic approval before live use. Technical checks do not establish clinical readiness or compliance. Next task: **5B**, only when requested.
