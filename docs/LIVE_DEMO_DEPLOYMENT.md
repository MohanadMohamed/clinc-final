# Render portfolio demo — controlled setup, not clinic deployment

This is an isolated **synthetic-data-only** portfolio environment. It does not change [ADR-001](architecture/ADR-001.md) or the two-Windows-PC LAN deployment. The public browser talks to one Render web service; that service serves the built React app at `/app/` and the existing `/api/*` routes, then connects to a separate Render Postgres database over Render's private network. Do not import local clinic/development databases, dumps, backups, screenshots, credentials, or patient records. No medical or legal readiness is claimed.

**Current exposure gate:** `CLINIC_DEMO_PUBLIC_ENABLED=false` is the default. When closed, only `/api/health` and `/api/health/ready` respond normally; the app and authentication return 503. The gate must stay closed until the checklist below is verified on Render. No service or database was created by this task.

## Reproducible image and runtime

`Dockerfile.render` builds Vite with `VITE_DEMO_MODE=true`, then copies the production assets, FastAPI code, Alembic scripts and a non-root startup script into one Python image. `.dockerignore` excludes `.env`, local databases, keys, backups, logs, `node_modules` and the local virtualenv. `scripts/render_start.sh` binds only the platform's `PORT` on `0.0.0.0` **inside** the Render web service, uses one Uvicorn worker, disables access logs and ignores untrusted proxy headers. It refuses to run unless `RENDER=true`, `CLINIC_ENV=production` and `CLINIC_DEPLOYMENT=render_demo`. Startup never migrates, seeds or resets a database. The committed app's normal LAN entry point and pywebview clients are unchanged.

Render's edge terminates public HTTPS, redirects incoming HTTP to HTTPS, and forwards to the container over internal HTTP. Do not enable Uvicorn `--proxy-headers` or wildcard `--forwarded-allow-ips`: neither the cookie policy nor role authorization reads forwarded scheme/IP. The configured demo origin must match Render's `RENDER_EXTERNAL_HOSTNAME`; the app accepts only that exact `Host` in demo mode. CSRF checks the exact HTTPS Origin/Referer. The demo response policy uses `Referrer-Policy: strict-origin` because `/api/auth/csrf` needs a same-origin Referer when GET has no Origin; it sends no URL path. A local headless-Chrome test verified this integration. CSP limits scripts, styles, fonts and connections to this origin; framing and MIME sniffing are denied. `/docs` and `/openapi.json` return 404 in demo mode. No wildcard CORS was added.

For throttling **only**, demo mode reads the first IP in `X-Forwarded-For` and validates that it is an IP address; account throttles still apply independently. Render states that its edge places the real client IP first, but this header is never an authorization factor. The actual edge header behavior and resistance to spoofed client prefixes must be checked on Render before opening the gate. Other deployments continue to use the socket peer and do not trust forwarded headers.

## Required Render configuration

1. Create a **new** managed Render Postgres instance in the same account/region as the web service. Choose a supported PostgreSQL version compatible with the Alembic migrations; the test suite currently uses PostgreSQL 18. Disable **all external database access** in its Networking/IP allow list before storing any records. Render's database external access is permissive by default; use only the **internal** hostname/URL from the web service. Do not connect this database to the real clinic or local development database. Do not create backups/exports containing real data.
2. Create a **paid** Render Web Service from this repository with Docker runtime, root build context and Dockerfile path `Dockerfile.render`. Paid shell access is needed for the interactive, one-time bootstrap; Render's Free web service has no shell/one-off jobs. Select the same region as Postgres, one instance initially, health check path `/api/health/ready`, and **Auto-Deploy Off**. Do not set a pre-deploy migration command: migrations are a separate reviewed step. The image's default CMD is the start command. Do not add a public database port, external static site, CDN or extra app service. Set the env values below **before** the first deploy; the default closed gate keeps the app unavailable while setup proceeds. Confirm the service URL first, then set the exact origin.
3. Set these in Render's service Environment page (never in Git, Docker ARGs, frontend variables or a copied `.env`):

   | Name | Value / purpose |
   | --- | --- |
   | `CLINIC_ENV` | `production` — required explicitly |
   | `CLINIC_DEPLOYMENT` | `render_demo` — separate from `clinic_lan` |
   | `CLINIC_PUBLIC_ORIGIN` | Exact `https://YOUR-SERVICE.onrender.com`, no slash or alternate host |
   | `CLINIC_DEMO_PUBLIC_ENABLED` | `false` until every pre-exposure gate passes |
   | `CLINIC_DATABASE_URL` | **Initially** the isolated DB's internal owner URL, with only its scheme changed from `postgresql://` to `postgresql+psycopg://`; later replace with the restricted app-role internal URL |
   | `PORT` | Render supplies this; the script uses it, or 10000 if absent |
   | `RENDER` | Render supplies `true`; do not set manually on the service |

   `CLINIC_MIGRATION_DATABASE_URL` is optional and should **not** remain on the running public service. `CLINIC_APPOINTMENT_POLICY` may be set to the existing valid JSON policy, with no secrets. Keep all passwords and URL values in Render's secret environment controls; never paste them into a shell command, support ticket, issue or screenshot. Render also exposes user-defined variables to Docker builds, so the Dockerfile contains no secret `ARG` or `ENV` references.
4. Deploy the **closed** service once. Confirm only liveness and readiness return 200; `/app/` and `/api/auth/csrf` must return 503. If readiness fails, inspect sanitized service diagnostics without printing env values. Do not enable the gate to bypass a failed readiness check.

## Explicit migration, database role and accounts

Use the paid service's interactive Shell while the public gate is closed. Shell commands run in `/srv/clinic/backend` in the built image. Run these commands **only against the newly created demo database**:

```bash
python -m alembic upgrade head
python -m alembic current
python -m alembic check
python -m app.demo_db_role --create --role YOUR_CHOSEN_CLINIC_DEMO_DB_ROLE
python -m app.bootstrap --username YOUR_CHOSEN_DOCTOR_USERNAME
python -m app.demo_provision --username YOUR_CHOSEN_RECEPTION_USERNAME
```

The role command prompts twice for a unique app-database password, creates the operator-chosen `clinic_demo_…` role with no superuser/DDL capability, and grants runtime CRUD only on application tables. It does not grant access to `alembic_version`. It requires PostgreSQL SCRAM-SHA-256 password encryption and uses libpq to derive the verifier locally, so plaintext does not enter SQL text. Store that password securely, then set `CLINIC_DATABASE_URL` to the **internal** URL for the chosen role (URL-encode password characters). Remove any owner/migration URL from the running web-service environment and redeploy **still closed**. Verify readiness, then use the shell to confirm the app role cannot create tables and can access application tables. Do not run migrations as the app role. After later reviewed migrations, close the gate, temporarily supply the owner URL to an interactive shell as `CLINIC_MIGRATION_DATABASE_URL`, run Alembic, then `python -m app.demo_db_role --grant-existing --role YOUR_CHOSEN_CLINIC_DEMO_DB_ROLE`; remove the owner URL before reopening. A migration failure or missing grant keeps the gate closed.

The existing doctor bootstrap is single-use, interactive and has no default password. The new receptionist provisioner is also interactive, one-time and refuses to run with the public gate open. Neither creates a public registration route. Choose private account names and unique strong passwords; give access only to authorized demo reviewers through a separate trusted channel. Do not publish shared demo credentials. No automatic seed records are created. If demonstration records are entered, they must be clearly synthetic; the UI labels this build as a demo and warns against real data. Technical validation cannot determine whether a human-entered name is real: operator review of the empty isolated DB and access practices remains mandatory.

## Pre-exposure verification (keep gate closed until complete)

- Build `Dockerfile.render` on a clean Linux/amd64 Docker host and scan the exact resulting base image and pinned Python/npm dependencies for critical/high vulnerabilities. Build/test was **NOT TESTED** here because Docker/Podman/Buildah are unavailable. The local Vite production build is not a substitute.
- On the closed Render service, verify the only normal responses are `/api/health` and `/api/health/ready`, the DB external IP allow list is empty, and the running service uses the restricted app role. Confirm the exact public hostname and no alternative custom-domain origin.
- Verify real Render HTTP→HTTPS redirect and valid TLS chain while the app gate is closed. The functional checks below require the app gate to be open: perform them only on a separate access-restricted staging service using an isolated synthetic database, or after an operator has established an equivalent platform-side access restriction. If such a restriction is unavailable, leave the production demo closed and record these as blockers. Do not treat a temporary public opening as a safe test. Do not skip certificate errors.
- Under that access restriction, verify Secure/HttpOnly/SameSite Strict cookies, login/logout, CSRF denial, doctor/receptionist role isolation, anonymous 401, and malicious Host rejection. With private authorized test accounts and **synthetic** records only, exercise patient create/edit/archive, concurrent appointment conflict, clinical direct-API 403 for reception, invoice/payment accounting, and deep React routes/assets. Confirm no sensitive request/response bodies in service/platform logs and no browser console/CSP errors.
- Validate Render's first `X-Forwarded-For` address with controlled requests; test malformed/spoofed header handling and rate-limit behavior from two external clients. The per-account throttle remains 5 attempts/15 minutes and per-client throttle 30/15 minutes; do not weaken them for the demo.
- Check deployment rollback, database backup/retention settings, and operator access to secrets. A paid database has managed recovery; do not claim it has been tested until a synthetic restore drill is performed.

Only after these checks pass and the production demo database has been reviewed as synthetic-only may the operator change `CLINIC_DEMO_PUBLIC_ENABLED=true` and deliberately redeploy the production service. At that point recheck the exact HTTPS origin, `/app/`, deep links, static assets and both roles. No public deploy, Render resource creation or Git push is part of this task.

## Stop and delete

To stop public app access, set `CLINIC_DEMO_PUBLIC_ENABLED=false` and redeploy, or use Render maintenance/suspend controls while doing so. Revoke demo users/sessions and rotate DB credentials if exposure is suspected. To end the demo, delete the **demo web service**, then the **separate demo Postgres instance** in the Render dashboard; review and delete any demo exports, recovery instances, external backups and stored credentials according to Render retention controls. Confirm the portfolio URL no longer serves the app. These are deliberate destructive operator actions; this document does not execute them. Never select the clinic's real database.

## Risk-ranked findings and current blockers

- **DEMO-001 — HIGH, blocks public enablement:** the Docker image and its dependency/base-image vulnerability scan have not been executed in this environment; image tags and hosted runtime remain unverified. Evidence: `Dockerfile.render:2,10–21`; local `docker`/`podman`/`buildah` unavailable. Build and scan before deploying.
- **DEMO-002 — HIGH, blocks public enablement:** actual Render HTTPS redirect, proxy IP-header contract, database network isolation, service env and log behavior are **NOT TESTED**. Evidence: local-only `backend/tests/test_render_demo.py` and `frontend/tests/render_demo.mjs`; host gate `backend/app/main.py:97–120` and client-IP selection `backend/app/api/auth.py:44–54`. Local TLS/Chrome tests prove app behavior, not platform behavior. Verify closed-service controls plus access-restricted functional staging before setting the public gate true.
- **DEMO-003 — HIGH, operational:** any real data typed into the demo would violate the synthetic-only boundary. The app cannot reliably classify names or clinical text as real versus invented; restrict access to authorized reviewers, inspect the fresh isolated DB and train reviewers. Never import local records.
- **DEMO-004 — MEDIUM:** public login can still be availability-targeted. Account and IP throttles exist in PostgreSQL, but a public edge introduces spoofing/shared-proxy and load questions. The first-forwarded-IP rule (`backend/app/api/auth.py:44–54,133`) is used only for throttling; verify it under Render and consider edge controls before a wide audience.
- **DEMO-005 — MEDIUM:** one clinician account and one-time bootstrap have no self-service recovery; paid shell/operator access, credential custody and revocation procedure are required. This is an existing product constraint, not a public registration feature.

The previous LAN [findings](security/FINDINGS.md) remain applicable to the intended Windows installation; this demo adds an Internet-facing threat boundary rather than replacing that design.

Render references: [Web services and TLS/port behavior](https://render.com/docs/web-services), [Docker services](https://render.com/docs/docker), [Postgres internal URLs and external access](https://render.com/docs/postgresql-creating-connecting), [paid shell availability](https://render.com/docs/ssh), [auto-deploy controls](https://render.com/docs/deploys), [secret environment settings](https://render.com/docs/configure-environment-variables), [database backups/recovery](https://render.com/docs/postgresql-backups), [Render client-IP guidance](https://render.com/articles/how-render-handles-ddos-attacks). The first-XFF-hop rule is based on [Render's published support statement](https://feedback.render.com/features/p/send-the-correct-x-forwarded-for) and still needs live confirmation.
