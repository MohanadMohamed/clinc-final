# Project status

Updated: 2026-10-27. **Render image vulnerability remediation verified in CI; public demo remains closed.** The [focused report](tasks/render-base-image.md) records the original Debian/Python HIGH findings, official Python 3.14 Alpine runtime change, and unchanged [CI verification run](https://github.com/MohanadMohamed/clinc-final/actions/runs/40494296645) with zero HIGH/CRITICAL image findings. Live Render TLS, database isolation, migrations and restricted staging remain **NOT TESTED**. The two-Windows-PC LAN design and next planned clinic task **8A** are unchanged.

Earlier 2026-10-27 handoff: [Local verification report](tasks/live-demo-verification.md) covers build/browser/backend checks and dependency audits before the CI image scan ran. Its Docker/image **NOT TESTED** entry is superseded by the focused image report above; actual Render restrictions/TLS/database isolation remain **NOT TESTED**.

Updated: 2026-10-25. **Render portfolio demo preparation is implemented locally; public exposure is blocked pending image/security and live platform checks. Next planned clinic task remains 8A.** The [deployment guide](LIVE_DEMO_DEPLOYMENT.md) and [demo preparation report](tasks/live-demo.md) cover the closed-by-default, separate synthetic-only Render design. No Render resource, public deployment, Git push or real-data copy was made. The two-Windows-PC LAN architecture is unchanged.

Updated: 2026-10-24. **Ubuntu loopback development fix complete; no new sprint started. Next planned task remains 8A.**

[Local development fix](tasks/local-development-fix.md) adds explicit HTTP loopback mode, a local startup script, safe example configuration, and real disposable-DB/browser verification. The existing local doctor bootstrap marker and account were checked read-only; no credentials or records were displayed or changed. Production HTTPS defaults remain. Pre-existing 6A working-tree edits remain separate.

[Task 7B report](tasks/7B.md) records the deployment design, Windows review templates, verified local HTTPS/session checks and offline-write replay prevention. Windows-specific acceptance remains **NOT TESTED**. No real/development records or machine network settings changed.

[Task 7A report](tasks/7A.md) records the FastAPI `/app/` static route, local `/docs`, thin pywebview launcher, exact commands and test evidence. The built React app passed real Chrome tests without Vite and with disposable PostgreSQL. An actual pywebview window was **NOT TESTED** because pywebview is not installed; Windows packaging and LAN deployment are **NOT TESTED**. The pre-existing 6A audit changes remain uncommitted outside the 7A checkpoint.

[Task 6B report](tasks/6B.md) records exact commands and evidence. On disposable PostgreSQL, the backend suite passed 41 tests, Vitest passed 6 tests, the frontend production build passed, the existing Playwright flows passed through restart/persistence, and a separate Playwright QA run passed at 1440×900 and 390×844. Separate disposable browser clusters keep the five-attempt account throttle enabled. No real or development records were changed; these checks do not establish clinical or legal readiness.

Task 6A audit edits existed before 6B and remain uncommitted outside this checkpoint. The [appointment deadlock fix](tasks/appointment-deadlock-fix.md) was previously verified. [Task 5B](tasks/5B.md) and [Task 5A](tasks/5A.md) record billing implementation. [ADR-001](architecture/ADR-001.md), [MVP](requirements/MVP.md), and [product baseline](requirements/BASELINE.md) remain constraints.
