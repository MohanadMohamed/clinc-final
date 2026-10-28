# Interactive synthetic portfolio demo

Date: 2026-10-28. Scope authorized by the user: public **GitHub Pages frontend-only demo**. No clinic backend/database, Render, Neon or Windows work.

## Implementation

- Separate `frontend/portfolio` entry, landing/role selection, memory-only records/adapters, dashboard and shell styling; shared patient/appointment/visit/billing components are reused without modifying their source.
- `frontend/vite.portfolio.config.ts`: `/clinc-final/` base, hash routes, no environment-file loading, aliases to demo-only adapters, rejection of real auth/network modules, independent ignored `portfolio-dist` output.
- Core simulated actions: patient search/create/edit/archive; appointment create/overlap feedback/reschedule/cancel; scheduled visit/draft/history/finalization; fees/invoices/payments/receipt; derived dashboard/day totals; reset/switch perspective.
- Persistent English/Arabic synthetic notice, explicit simulated-role explanation, GitHub source link and synthetic label in printed receipts. No credential prompt, persistent browser state, data requests or backend connection; CSP blocks data connections.
- `.github/workflows/portfolio-pages.yml` builds/tests/audits and uploads **only** `frontend/portfolio-dist`, then deploys that static artifact. Actions pinned to commit IDs; Pages and OIDC write permission limited to deploy job. Pages source was enabled as `workflow` through the authorized repository setting API; no manual step needed.
- Existing backend, desktop, application source and ordinary Vite configuration are unchanged. Scripts are added to frontend/package.json; generated assets/screenshots are ignored. Four pre-existing user README/image files are untouched.

## Local verification

| Check | Status | Evidence |
|---|---|---|
| `npm --prefix frontend test` | PASS | 11 tests / 5 files, including 4 demo state/workflow tests |
| `npm --prefix frontend run build` | PASS | Current real application TypeScript + Vite build |
| `npm --prefix frontend run build:portfolio` | PASS | Isolated TypeScript + Vite build; real network/auth graph guard passes |
| `npm --prefix frontend run audit:portfolio` | PASS | 4 static HTML/JS/CSS/SVG assets; no API routes, DB URLs, private keys/token patterns or unexpected files |
| `npm --prefix frontend run test:portfolio` | PASS | Real Chrome, independent doctor/reception contexts; full synthetic actions, hash refresh, reset/counters, RTL 1440×900 and 390×844, no persistent storage, API/data requests, missing assets or console/page errors |
| Screenshot review | PASS | Landing, doctor overview, receipt/billing and reception mobile screenshots under ignored frontend/test-results; synthetic only |

An initial smoke-server path guard and test-label selectors were corrected before the passing run. Missing lucide brand export was replaced with the existing external-link icon. Shared app components and security code were not changed to make tests pass. No backend tests/databases were run or modified in this task.

## Hosted verification

Pending workflow publication and live browser verification. Expected Pages origin: `https://mohanadmohamed.github.io/clinc-final/`. This report will record the actual deployment result after the workflow finishes. This public showcase is not real authentication, a medical service or backend security verification. Refresh clears changes; public synthetic bundle content can be inspected regardless of simulated perspective.
