# Project status

Updated: 2026-10-24. **Focused appointment deadlock fix verified; Task 6A audit remains in progress.**

[Deadlock fix report](tasks/appointment-deadlock-fix.md): one transaction lock now orders all one-doctor calendar writes before row locks. The raw PostgreSQL race still verifies that overlapping writes cannot both commit. Appointment suite: 14 passed; full backend suite: 40 passed on disposable PostgreSQL. The pending Task 6A audit changes are separate from this checkpoint. Next task ID: **6A** (resume audit only when requested).

[Task 5B report](tasks/5B.md) records the Arabic invoice, cash payment, receipt and daily summary UI. [Task 5A](tasks/5A.md) describes the authoritative billing service and accounting rules. [ADR-001](architecture/ADR-001.md), [MVP](requirements/MVP.md) and [baseline](requirements/BASELINE.md) remain product constraints.

| Result | Command/check | Evidence |
| --- | --- | --- |
| PASS | `cd frontend && npm run build` | TypeScript and Vite production build completed, exit 0. |
| PASS | `cd frontend && npm run test` | Vitest: 2 files, 5 tests passed, including exact money entry validation. |
| PASS | `cd backend && .venv/bin/pytest -q tests/test_billing.py` | 3 passed on disposable PostgreSQL, including new authorized invoice/payment reads. |
| PASS | `python3 frontend/tests/run_browser.py` | Existing patient/appointment/visit browser flows, Task 5B billing flow and restart check passed on disposable PostgreSQL and local HTTPS. Billing test checked empty state, invoice/payment balances, PDF receipt generation/print CSS, dashboard summary, reload, and receptionist API 403. |
| PASS | `backend/.venv/bin/ruff check backend/app/api/billing.py backend/app/schemas/billing.py backend/tests/test_billing.py` and `backend/.venv/bin/ruff format --check backend/app/api/billing.py backend/app/schemas/billing.py backend/tests/test_billing.py` | All changed backend files passed. |
| NOT TESTED | Physical receipt printer and Windows packages | Requires Windows/printer validation; outside Task 5B local browser verification. |

Only synthetic patients and payments were used. The unrelated pre-existing `AGENTS.md` edit remains outside the task checkpoint. Financial correction, receipt numbering, tax, retention and backup policies still require clinic decisions before live use. Tests do not establish accounting or clinical compliance. Next task: **6A**, only when requested.
