# Project status

Updated: 2026-10-23. **Sprint 0 Task 0A: COMPLETE — documentation scope only. Next task: 0B.**

The [confirmed product baseline](requirements/BASELINE.md) remains authoritative: original Arabic RTL single-doctor Neurology & Psychiatry clinic, two Windows PCs, pywebview clients, FastAPI/PostgreSQL Windows services on the doctor PC, one central database, LAN HTTPS and no Internet required during normal operation. Independent accounts and API-enforced role/field permissions protect clinical notes. All development data is synthetic. Ubuntu development does not establish Windows acceptance.

## This checkpoint

Updated the five requested documents: [AGENTS](../AGENTS.md), [ADR-001](architecture/ADR-001.md), [MVP](requirements/MVP.md), this status and [0A report](tasks/0A.md). The report contains verified registration, appointment, visit and billing source behavior at pinned commit `99638225ba0876261c2c16c3bd2f9b83f4abbc19`, distinguished from inferences and original clinic proposals.

Git already existed. The pre-existing untracked `.env.example`, `.gitignore`, `backend/`, `compose.yaml` and `frontend/` partial 0B work is preserved and excluded from this documentation commit. No application code or database was changed in this task. Prior [baseline review](tasks/baseline-review.md) remains historical context.

## Verification

| Check | Result / evidence |
| --- | --- |
| Local Markdown links and fenced blocks | PASS: first Python block in the 0A report checks 8 documents and all local links |
| Public workflow source targets | PASS: second Python block fetched 4 commit-pinned files with HTTP 200; all 14 line references valid |
| Source interpretation | PASS: relevant executable methods inspected; limits and proposed clinic behavior labelled separately in 0A |
| Documentation whitespace and staged scope | PASS: `git diff --check`, `git diff --cached --check`, `git diff --cached --name-only`; only the 5 requested Markdown files staged |
| Preserved scaffold | PASS: SHA-256 comparison against prior review manifest for 34 source/config/lock files; no implementation changes |
| Reference application/runtime workflows | NOT TESTED: source inspection only |
| Application, browser, migrations, Windows, LAN HTTPS and backup/restore | NOT TESTED in this documentation task; earlier smoke results are not current deployment evidence |

Exact reproduction/checkpoint commands are in the 0A report. Original GitHub HTML HEAD checks timed out in the earlier task; the current raw-source checks succeeded. Technical verification does not establish clinical compliance or readiness.

## Open architecture decisions

Runtime pins and reproducibility remain 0B acceptance work. Authentication library/settings and session durations, Windows installer/service wrapper, webview runtime provisioning, TLS hostname/trust/renewal, backup recovery objectives/key custody, clinic timezone/currency and retention/correction/export policy remain open with owners/deadlines in ADR-001. These do not block the 0A documentation deliverables; they gate later implementation and deployment.

## Next task

**0B — Local development scaffold.** Review the preserved partial work, resolve its outstanding acceptance criteria and document exact Ubuntu setup/run/check commands. Require actual UI/API/database integration evidence and migration checks on a disposable synthetic database. Do not add authentication, patients, appointments, visits or billing features as part of the scaffold. Work resumes only when requested; this task ends at the documentation checkpoint.
