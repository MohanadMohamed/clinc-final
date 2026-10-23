# Project status

Updated: 2026-10-23. **Current activity: project-wide baseline review. Implementation is paused.**

The [confirmed product baseline](requirements/BASELINE.md) governs every task: Arabic RTL single-doctor clinic, two Windows PCs, pywebview clients, FastAPI/PostgreSQL Windows services on the doctor PC, central database, LAN HTTPS and no Internet needed in normal operation. Develop on Ubuntu; build/test Windows packages on Windows.

## Existing work

- **0A:** Historical documentation checkpoint `50875ca`. Its browser-only topology and partial stack have been revised to match the confirmed baseline. Reference workflow evidence remains in [0A](tasks/0A.md); its test counts and next-task statements describe that historical checkpoint.
- **0B:** Partial uncommitted scaffold, preserved during review. Backend health/readiness, SQLAlchemy factory, Alembic baseline, frontend RTL shell and development/test configuration exist. It is not complete or accepted. See [review findings](tasks/baseline-review.md).
- **Baseline review:** Governing documents aligned; detailed business rules remain proposals for review. No application changes, database operations or external publishing in this review.

## Verification status

| Area | Evidence / status |
| --- | --- |
| Current documentation | PASS: cross-link/file check and `git diff --check`; commands recorded in the baseline review |
| Existing scaffold preserved | PASS: before/after SHA-256 manifest comparison during this review |
| Earlier backend checks | Historical PASS: 2 pytest tests and disposable PostgreSQL baseline round-trip/readiness; not rerun in this review |
| Earlier frontend checks | Historical PASS: `npm run build` and `npm test` (2 component tests); completed output recovered after interruption; not rerun in this review |
| Browser/Playwright and actual UI → proxy → API → DB | NOT TESTED end to end |
| Windows desktop, installers, services, LAN TLS, Internet-disconnected operation | NOT TESTED |
| Clinical compliance/readiness | Not established by these technical checks |

## Open work and task order

Review the remaining workflow/permission details and incomplete scaffold before resuming implementation. Missing 0B acceptance work includes an Ubuntu README with exact setup/run/check commands, integrated HTTP/browser verification and a task completion report. Desktop packaging, production UI serving, certificate lifecycle and Windows acceptance are future implementation work with scope still to be assigned.

The previous instruction named **1A** after 0B; no 1A scope is confirmed or started. Earlier proposed 0C/0D ordering is withdrawn. **Next task ID: 0B (review outstanding acceptance before any resumption); then 1A when scoped and authorized.**

Links: [AGENTS](../AGENTS.md), [ADR-001](architecture/ADR-001.md), [draft MVP](requirements/MVP.md), [glossary](../GLOSSARY.md).
