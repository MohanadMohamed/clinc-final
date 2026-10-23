# Project status

Updated: 2026-10-23.

**Sprint 0 / Task 0A: COMPLETE — documentation scope only. Next task: 0B.** No backend/frontend business features have been implemented. Checkpoint: the commit containing these documents, titled `docs: establish Sprint 0 Task 0A clinic foundation` (resolve with `git log -1 --oneline` at handoff).

The product is an original Arabic RTL Neurology & Psychiatry clinic system for one doctor. Fixed stack: React + TypeScript, FastAPI, PostgreSQL. The doctor PC hosts the application and sole database; the receptionist PC is browser-only over LAN HTTPS. Permissions are enforced by the API using separate accounts. Development and acceptance data must be synthetic.

- [Completion contract](../AGENTS.md)
- [ADR-001: architecture, secrets and development/deployment decisions](architecture/ADR-001.md)
- [MVP: journeys, role matrix, boundaries and next-task acceptance criteria](requirements/MVP.md)
- [Task 0A report: verified reference workflows, evidence and exact check commands](tasks/0A.md)
- [Domain glossary](../GLOSSARY.md)

## Verification

| Check | Status / evidence |
| --- | --- |
| Public source inspection | PASS: four controllers inspected at commit `99638225ba0876261c2c16c3bd2f9b83f4abbc19`; claim-specific links in 0A report |
| Documentation and local cross-links | PASS: first Python command in the 0A report checked 6 UTF-8 documents, 26 local links, balanced fences and next task 0B |
| Direct GitHub HTML link check | FAIL: initial Python `urllib` HEAD requests timed out; no claim of HTML/browser verification |
| External evidence source fallback | PASS: second Python command in the 0A report fetched 4 commit-pinned raw files with HTTP 200 and validated all 14 line references |
| Git diff and staged scope | PASS: `git diff --check`, `git diff --cached --check`, `git diff --cached --name-only` and `git diff --cached --stat`; exactly 6 Markdown files, no application/secret/data files |
| Application/browser/database/reference runtime | NOT TESTED: no application or database execution in this task |
| Windows services, LAN HTTPS, printing and restore | NOT TESTED: future deployment acceptance requires actual execution |

## Open gates

No architecture blocker to completing 0A. Runtime pins, authentication library/timeouts, Windows service/TLS choices, recovery objectives/key custody, timezone/currency and retention/correction/export policies need resolution at the deadlines in ADR-001. No real data or live deployment is authorized.

The direct HTML-link network failure does not block source evidence: the identical commit/path contents and referenced line bounds were verified using the raw-content host. The initial fence-check implementation counted a code literal; it was corrected to count line-start fences and rerun successfully. Exact final commands and limitations are in the 0A report.

## Next task

**0B — Local development scaffold.** Acceptance criteria are in the MVP. Establish reproducible tool versions, safe configuration, the original application skeleton, Alembic wiring and a real localhost UI/API/database health path. Do not add registration, appointments, visits or billing features in 0B. Proposed 0C/0D criteria are planning only; no future task has started.
