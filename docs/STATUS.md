# Project status

Updated: 2026-10-23. **Sprint 3 Task 3A: one-doctor appointment backend implemented. Next task: 3B.**

[Task 3A report](tasks/3A.md) records the API contract, GiST exclusion design, Cairo/DST policy, configuration, migration and deployment limits. [2B](tasks/2B.md), [2A](tasks/2A.md) and [1A](tasks/1A.md) retain earlier evidence. [ADR-001](architecture/ADR-001.md), [MVP](requirements/MVP.md) and [baseline](requirements/BASELINE.md) remain the wider constraints; Cairo is now explicitly selected by the Task 3A request.

Commands below ran from `backend/` on Ubuntu:

| Result | Command/check | Evidence |
| --- | --- | --- |
| PASS | `.venv/bin/pytest -q` | 26 passed in 16.30s; one known Starlette TestClient deprecation warning. Disposable PostgreSQL migration upgrade/check/downgrade/re-upgrade/check included. |
| PASS | Concurrent database insert and reschedule tests | Two distinct `pg_backend_pid()` connections synchronized at a barrier; exactly one commit and one exclusion violation (`23P01`) in each case. |
| PASS | `PYTHONTZPATH="" .venv/bin/pytest -q tests/test_appointments.py::test_cairo_dst_and_hours` | 1 passed; pinned tzdata fallback validates skipped/repeated Cairo DST hours. |
| PASS | `.venv/bin/ruff check .` | All checks passed. |
| PASS | `.venv/bin/ruff format --check .` | 38 Python files already formatted. |
| PASS | `.venv/bin/python -m pip check` | No broken requirements found. |
| NOT TESTED | Persistent database migration, Windows deployment, frontend appointment UI | No live database changed. No frontend changes. |

The development scheduling policy needs clinic review before deployment. The unrelated pre-existing AGENTS.md edit remains uncommitted. No real patient data was used. Technical checks do not establish clinical readiness or compliance. Next task: **3B**, only when requested.
