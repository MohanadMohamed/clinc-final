# Project status

Updated: 2026-10-24. **Sprint 3 Task 3B: Arabic appointment frontend verified. Next task: 4A.**

[Task 3B report](tasks/3B.md) documents the UI contract and actual browser evidence. [Task 3A](tasks/3A.md) retains backend overlap and authorization evidence; [ADR-001](architecture/ADR-001.md), [MVP](requirements/MVP.md) and [baseline](requirements/BASELINE.md) remain product constraints.

| Result | Command/check | Evidence |
| --- | --- | --- |
| PASS | `cd frontend && npm run build` | TypeScript/Vite production build completed; 2087 modules transformed. |
| PASS | `cd frontend && npm test` | Vitest: 3 passed. |
| PASS | `python3 frontend/tests/run_browser.py` | Disposable PostgreSQL and real local HTTPS Chrome: two independent role sessions, reception-to-doctor visibility, one 409 conflict with Arabic UI feedback, refreshed count, reschedule, cancel, anonymous 401, no unexpected browser errors. Existing patient regression and persistence check passed. |
| NOT TESTED | Windows desktop package, production TLS, real clinic data | Outside this task. |

Frontend changes only; backend authorization and exclusion constraint remain unchanged. The unrelated pre-existing AGENTS.md edit remains uncommitted. Technical checks do not establish clinical readiness or compliance. Next task: **4A**, only when requested.
