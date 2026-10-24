# Project status

Updated: 2026-10-24. **Sprint 7 Task 7B LAN/TLS design and safe local prototypes complete; next task 8A.**

[Task 7B report](tasks/7B.md) records the deployment design, Windows review templates, verified local HTTPS/session checks and offline-write replay prevention. Windows-specific acceptance remains **NOT TESTED**. No real/development records or machine network settings changed.

[Task 7A report](tasks/7A.md) records the FastAPI `/app/` static route, local `/docs`, thin pywebview launcher, exact commands and test evidence. The built React app passed real Chrome tests without Vite and with disposable PostgreSQL. An actual pywebview window was **NOT TESTED** because pywebview is not installed; Windows packaging and LAN deployment are **NOT TESTED**. The pre-existing 6A audit changes remain uncommitted outside the 7A checkpoint.

[Task 6B report](tasks/6B.md) records exact commands and evidence. On disposable PostgreSQL, the backend suite passed 41 tests, Vitest passed 6 tests, the frontend production build passed, the existing Playwright flows passed through restart/persistence, and a separate Playwright QA run passed at 1440×900 and 390×844. Separate disposable browser clusters keep the five-attempt account throttle enabled. No real or development records were changed; these checks do not establish clinical or legal readiness.

Task 6A audit edits existed before 6B and remain uncommitted outside this checkpoint. The [appointment deadlock fix](tasks/appointment-deadlock-fix.md) was previously verified. [Task 5B](tasks/5B.md) and [Task 5A](tasks/5A.md) record billing implementation. [ADR-001](architecture/ADR-001.md), [MVP](requirements/MVP.md), and [product baseline](requirements/BASELINE.md) remain constraints.
