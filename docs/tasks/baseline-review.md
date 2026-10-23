# Project-wide baseline review

Date: 2026-10-23. Scope: reconcile the existing work with the user's restated product decisions, preserving the partial scaffold. Implementation remains paused. Authoritative requirements: [BASELINE](../requirements/BASELINE.md).

## Findings and disposition

| Finding | Evidence | Disposition |
| --- | --- | --- |
| Earlier documents specified browser-only clients | Prior AGENTS, ADR-001, MVP and STATUS | Corrected to two Windows pywebview clients; doctor PC also runs both Windows services |
| Full stack, Ubuntu/Windows boundary and Internet-independent LAN operation were incomplete | Earlier ADR/MVP omitted parts of the confirmed stack and packaging constraints | Recorded the complete baseline and Windows-only package build/test gate |
| Business details went beyond fixed user decisions | Earlier MVP specified partial payments, overbooking policy and clinical finalization; ADR selected session/TLS approaches | Retained for review as proposals, not additional confirmed user decisions |
| Earlier task sequence was stale | STATUS said 0B unstarted; MVP still proposed 0C/0D | Recorded partial 0B, paused implementation and prior next-ID instruction 1A; withdrew 0C/0D ordering |
| Backend scaffold broadly matches stack/layout | `backend/app/{api,core,models,schemas,repositories,services}`, health router, config, SQLAlchemy session factory and Alembic baseline | Preserved; empty layer folders do not establish implemented business architecture |
| Frontend dependencies broadly match stack | `frontend/package.json`, `components.json`, `index.html`, `App.tsx`, `vite.config.ts` | React/Vite/Tailwind/shadcn configuration, Router, Query, Hook Form, Zod and test dependencies present; library installation is not feature acceptance |
| Completion artifacts/integration evidence missing | No root README, no 0B report, no Playwright tests/config or executed complete browser flow in inspected scaffold | Record as pending 0B acceptance; do not mark complete |
| Deployment implementation absent | No `desktop/` launcher; `backend/app/main.py` includes health routes only, no built-UI serving | Packaging/runtime implementation remains future scoped work; do not present this as a deployable desktop system |
| Roles not implemented | Only health/readiness API routes currently exist | Expected for initial scaffold; permission requirements must be tested when business/auth routes are introduced |
| Optional reference unreviewed | No review of `morluto/rea` conducted | No approval to use it and no runtime dependency allowed; security/license review required before optional use |

## Changed files

- `AGENTS.md`: project-wide contract and preservation rules.
- `docs/requirements/BASELINE.md`: confirmed requirements in one place.
- `docs/architecture/ADR-001.md`: revised topology, stack, deployment and proposal boundaries.
- `docs/requirements/MVP.md`: fixed scope corrected; detailed journeys marked as draft proposals; stale sequencing removed.
- `docs/STATUS.md`: current state and evidence limits.
- `docs/tasks/baseline-review.md`: this review record.

The existing `.env.example`, `.gitignore`, `backend/`, `compose.yaml` and `frontend/` work remains uncommitted and is excluded from this documentation checkpoint. No existing edits were discarded. No database was started, changed or reset in this review. No reference source/assets were imported or published.

## Verification and reproduction

From the repository root:

```bash
python3 - <<'PY'
from pathlib import Path
import re
files = [Path('AGENTS.md'), Path('docs/requirements/BASELINE.md'),
         Path('docs/architecture/ADR-001.md'), Path('docs/requirements/MVP.md'),
         Path('docs/STATUS.md'), Path('docs/tasks/baseline-review.md')]
count = 0
for file in files:
    content = file.read_text()
    assert len(re.findall(r'^```', content, re.M)) % 2 == 0, file
    for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', content):
        if target.startswith(('https://', 'http://')):
            continue
        assert (file.parent / target.split('#')[0]).is_file(), (file, target)
        count += 1
print(f'PASS: {len(files)} documents, {count} local links, balanced fences')
PY
git diff --check
git diff --stat
git status --short
```

PASS: documentation links/fences and whitespace checked. PASS: source preservation checked against `/tmp/clinic-baseline-source-hashes.json`, generated before editing documentation and compared afterwards. It covers scaffold source/config/lock files and excludes generated dependencies/build/cache directories; it is a temporary local verification artifact, not committed project content. The safe example file was left untouched.

Historical evidence recovered from the interrupted task: `cd backend && .venv/bin/pytest -q` passed 2 tests; `PYTHONPATH=. .venv/bin/python scripts/check_disposable_db.py` passed baseline upgrade/current/check/downgrade/upgrade and real readiness against a new temporary PostgreSQL cluster. That cluster was stopped and removed by the script. A Starlette HTTPX deprecation warning was reported. `cd frontend && npm run build && npm test` passed production compilation and 2 component tests. These checks were not rerun during this review and do not prove end-to-end or Windows behavior.

NOT TESTED: Playwright/browser flow, Windows packages/services, pywebview, LAN HTTPS, Internet-disconnected operation, install/upgrade/rollback, printing and backup restore. No clinical compliance or readiness claim.

## Open decisions and next step

Select Windows installer tooling, service wrapper, webview runtime provisioning, certificate lifecycle and supported Windows versions in the packaging scope. Confirm runtime pins, backup objectives/key custody and relevant business policies before their implementation. Prior detailed workflows need review against the doctor's requirements.

Checkpoint: documentation-only commit titled `docs: align project-wide clinic baseline`; existing scaffold remains preserved and uncommitted. **Next task ID: 0B review/resumption when requested; 1A follows only after its scope is confirmed.**
