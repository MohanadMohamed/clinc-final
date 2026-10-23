# Project status

Updated: 2026-10-23. **Sprint 0 Task 0B: COMPLETE — Ubuntu development scaffold. Next task: 1A.**

[Product baseline](requirements/BASELINE.md): Arabic RTL single-doctor clinic; two Windows PCs, pywebview clients, FastAPI/PostgreSQL services on the doctor PC, central database, LAN HTTPS, no Internet needed for normal operation. Ubuntu checks do not establish Windows or clinical readiness.

- **0A:** Documentation/workflow evidence checkpoint `6154589`; [report](tasks/0A.md).
- **0B:** Existing partial scaffold completed and checkpointed; [report](tasks/0B.md), [exact Ubuntu commands](../README.md). No authentication or patient features.

## Current evidence

| Check | Result |
| --- | --- |
| Backend pytest | PASS: 2 tests, readiness success/failure and sanitized errors |
| Ruff lint and formatting | PASS: 16 Python files |
| Disposable PostgreSQL 18.6 migration baseline | PASS: upgrade/current/check/downgrade/upgrade, only Alembic version table, no drift |
| Real Vite → FastAPI → DB HTTP integration | PASS: both health endpoints through proxy, Arabic HTML shell, temporary services cleaned up |
| Locked frontend install, TypeScript, production build | PASS: `npm ci`, `npm run typecheck`, `npm run build` |
| Vitest/Testing Library | PASS: 2 component tests |
| Production dependency audit | PASS: no reported vulnerabilities; not a security certification |
| Documentation/ignore rules/Git whitespace | PASS: commands in 0B report |
| Browser/Playwright, Compose, persistent DB provisioning | NOT TESTED |
| Windows packages, pywebview, services, LAN TLS, printing, backup/restore | NOT TESTED |

Warnings: Starlette HTTPX TestClient deprecation and transitive whatwg-encoding deprecation; tests pass without suppressing warnings. See report for limits and exact commands.

## Remaining decisions

[ADR-001](architecture/ADR-001.md) records the tested development toolchain and open authentication settings, Windows installer/service wrapper, certificate lifecycle, webview provisioning, backup objectives, timezone/currency and clinic policies. Windows packages must be built/tested on Windows. Technical tests do not establish clinical compliance or readiness.

**Next task: 1A**, when explicitly requested and scoped. No next-task implementation is included.
