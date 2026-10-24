# Project status

Updated: 2026-10-24. **Sprint 4 Task 4B: doctor visit UI verified. Next task: 5A.**

[Task 4B report](tasks/4B.md) records the doctor UI and browser evidence. [Task 4A](tasks/4A.md) retains clinical API and database evidence; [ADR-001](architecture/ADR-001.md), [MVP](requirements/MVP.md) and [baseline](requirements/BASELINE.md) remain product constraints.

| Result | Command/check | Evidence |
| --- | --- | --- |
| PASS | `cd frontend && npm run build` | TypeScript/Vite production build completed. |
| PASS | `cd frontend && npm test` | Vitest: 3 passed. |
| PASS | `python3 frontend/tests/run_browser.py` | Disposable PostgreSQL and local HTTPS Chrome: doctor scheduled visit, draft save, history, unsaved warning, finalize; receptionist route hidden and direct visit API returned 403. Existing patient/appointment regressions passed. |
| NOT TESTED | Windows desktop deployment, live clinical data | Outside Task 4B. |

The unrelated pre-existing AGENTS.md edit remains uncommitted. Clinical retention, backup and export policies require clinic approval before live use. Technical checks do not establish clinical readiness or compliance. Next task: **5A**, only when requested.
