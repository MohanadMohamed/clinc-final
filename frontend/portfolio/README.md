# Isolated synthetic portfolio

This folder is an explicitly requested, frontend-only exception to the clinic's no-live-mocks rule. It is not used by the real application. No FastAPI, database, credentials or real records are involved.

- Separate HTML/React entry and `vite.portfolio.config.ts`; base `/clinc-final/`, HashRouter routes such as `/clinc-final/#/patients` work on GitHub Pages without a server fallback.
- Reuses the actual patient, appointment, visit and billing components and CSS. The demo config aliases only their client imports to `adapters.ts`. Type-only imports disappear at compilation. A build guard rejects the real authentication/network modules. Two server-specific explanatory sentences are adapted only in the demo build.
- `state.ts` seeds clearly labeled synthetic records with deterministic identities and relative-to-today appointment timestamps. All edits are in memory; refresh resets data and perspective. No localStorage/sessionStorage, service worker, fetch/XHR, authentication or API emulation server.
- Doctor/reception are **simulated perspectives**, never a security boundary. All bundled data is public and synthetic. UI limits illustrate the real product's roles without claiming authorization.
- CSP `connect-src 'none'` blocks data connections. No CDN; icons are bundled, fonts use the existing local/system stack.
- The print receipt includes a synthetic-demo label. No real payment or appointment is created.

From the repository root:

```bash
npm --prefix frontend test
npm --prefix frontend run build             # real clinic build, unchanged entry/security
npm --prefix frontend run build:portfolio   # isolated output: frontend/portfolio-dist
npm --prefix frontend run audit:portfolio
npm --prefix frontend run test:portfolio
```

Browser test prerequisites: installed frontend dependencies and Chrome at `/usr/bin/google-chrome` locally; override with `PLAYWRIGHT_EXECUTABLE_PATH`. CI installs pinned Playwright Chromium. The browser script starts only a static loopback asset server with no SPA fallback. It exercises both perspectives, writes synthetic screenshots under ignored `frontend/test-results`, asserts no real API/data/external requests, no missing assets/console errors and zero persistent browser storage. To verify a deployed copy: `PORTFOLIO_URL=https://mohanadmohamed.github.io/clinc-final/ npm --prefix frontend run test:portfolio`.

Only `frontend/portfolio-dist` may be uploaded by `portfolio-pages.yml`. Never upload the checkout, `frontend/dist`, `.env`, backend files, private keys, databases or backups. The ordinary `npm run build`, `/app/` base, doctor/reception authentication, CSRF and backend permissions stay independent.
