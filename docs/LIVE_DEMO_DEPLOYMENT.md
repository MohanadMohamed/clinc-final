# Render portfolio demo — controlled setup, not clinic deployment

This is an isolated **synthetic-data-only** portfolio environment using **Render Free Web Service + Neon Free PostgreSQL**. It does not change [ADR-001](architecture/ADR-001.md) or the two-Windows-PC LAN deployment. One Render Docker service serves `/app/` and `/api/*`; it connects to the separately created Neon demo database over certificate-verified public TLS. This is **not** Render private-network PostgreSQL: Neon's endpoint is Internet-reachable and protected by database credentials/TLS and any available provider access restrictions. Do not import local clinic/development databases, dumps, backups, credentials, or patient records.

**Current exposure gate:** `CLINIC_DEMO_PUBLIC_ENABLED=false` is the default. When closed, only `/api/health` and `/api/health/ready` respond normally; the app and authentication return 503. The gate must stay closed until the checklist below is verified on Render. No service or database was created by this task.

## Reproducible image and runtime

`Dockerfile.render` builds Vite with `VITE_DEMO_MODE=true`, then copies the production assets, FastAPI code, Alembic scripts and a non-root startup script into one Python image. `.dockerignore` excludes `.env`, local databases, keys, backups, logs, `node_modules` and the local virtualenv. `scripts/render_start.sh` binds only the platform's `PORT` on `0.0.0.0` **inside** the Render web service, uses one Uvicorn worker, disables access logs and ignores untrusted proxy headers. It refuses to run unless `RENDER=true`, `CLINIC_ENV=production` and `CLINIC_DEPLOYMENT=render_demo`. Startup never migrates, seeds or resets a database. The committed app's normal LAN entry point and pywebview clients are unchanged.

Render's edge terminates public HTTPS, redirects incoming HTTP to HTTPS, and forwards to the container over internal HTTP. Do not enable Uvicorn `--proxy-headers` or wildcard `--forwarded-allow-ips`: neither the cookie policy nor role authorization reads forwarded scheme/IP. The configured demo origin must match Render's `RENDER_EXTERNAL_HOSTNAME`; the app accepts only that exact `Host` in demo mode. CSRF checks the exact HTTPS Origin/Referer. The demo response policy uses `Referrer-Policy: strict-origin` because `/api/auth/csrf` needs a same-origin Referer when GET has no Origin; it sends no URL path. A local headless-Chrome test verified this integration. CSP limits scripts, styles, fonts and connections to this origin; framing and MIME sniffing are denied. `/docs` and `/openapi.json` return 404 in demo mode. No wildcard CORS was added.

For throttling **only**, demo mode reads the first IP in `X-Forwarded-For` and validates that it is an IP address; account throttles still apply independently. Render states that its edge places the real client IP first, but this header is never an authorization factor. The actual edge header behavior and resistance to spoofed client prefixes must be checked on Render before opening the gate. Other deployments continue to use the socket peer and do not trust forwarded headers.

## One-time Neon initialization from Ubuntu (before Render)

Use a dedicated empty Neon project/branch/database containing no other clinic records. In Neon **Connect**, disable connection pooling and independently check the project, branch, DIRECT endpoint, database and owner role against the new demo you created. Copy only the hostname/name into the prompts; passwords are entered separately and hidden. The command cannot determine a project's purpose from its name, so this console cross-check and the exact confirmation are required. Never paste credentials into this chat or CI.

From a private local terminal, with the existing Python 3.14 virtualenv and pinned dependencies:

```bash
cd /home/mohanad/Desktop/Clinc-final/backend
.venv/bin/python -m app.neon_setup --help
CLINIC_DEMO_PUBLIC_ENABLED=false .venv/bin/python -m app.neon_setup initialize
```

No `RENDER`, `RENDER_EXTERNAL_HOSTNAME`, `CLINIC_DATABASE_URL` or migration URL is needed locally. Do **not** spoof platform variables or edit your local `.env`. This operator command never reads `.env` or runtime Settings and never starts FastAPI. Its only database target comes from the explicit prompts. It rejects local/pooled hosts and requires `ep-…neon.tech`, port 5432, `sslmode=verify-full`, the pinned certifi CA bundle, SCRAM channel binding, a successful TLS check and exact `current_database()`/`current_user()` identity.

Prompts, in order:

1. Neon DIRECT hostname, exact demo database name, owner database role, and a new `clinic_demo_…` application role name (suffix 3–40 lowercase letters/digits/underscores).
2. Owner password, hidden. The connection and empty-object check occur before any mutation.
3. Type the exact `INITIALIZE SYNTHETIC DEMO HOST/DATABASE` confirmation displayed. A mismatch exits without setup writes.
4. A unique password-manager-generated app database password (20–128 characters), twice; private doctor username + unique password (15–128), twice; private receptionist username + different password (15–128), twice. Save these in your password manager; the command never prints them or a connection URL. Usernames must be distinct, 3–64 letters/digits/`_.-`. There are no defaults or public registration endpoints.

Only after these checks/prompts, a database advisory transaction lock protects the final empty-target check. **One outer PostgreSQL transaction** applies the existing Alembic `upgrade head`, creates the SQL app role/grants, and invokes the existing doctor bootstrap and receptionist provisioner using savepoints. Failure rolls back schema/role/accounts together; there is no downgrade, reset, import or seed. A repeat initialization refuses the now nonempty database. Versioned migration revisions and runtime Settings validation are unchanged.

Neon specifies that SQL-created roles are ordinary roles, while Console/API-created roles receive `neon_superuser` membership. It also states that prehashed role passwords are unsupported. Accordingly this Neon-only role path sends the properly quoted password in SQL **over verified TLS**, rather than the local SCRAM verifier used by the original `demo_db_role` CLI. SQL/driver exceptions and connection URLs are never printed; do not enable SQL tracing, terminal recording or provider query capture for provisioning. Review provider credential/query-log handling as part of hosted acceptance. [Neon role documentation](https://neon.com/docs/manage/roles), [Neon TLS guidance](https://neon.com/docs/connect/connect-securely).

The app role has no superuser/createdb/createrole/replication/bypass-RLS attributes or role memberships, owns no application tables, and cannot create schemas/tables or edit `alembic_version`. The selected demo database's PUBLIC CONNECT/TEMP and public-schema privileges are revoked; explicit runtime table grants are applied. Runtime cannot provision accounts: `auth_bootstrap` has no app grants and `users` permits SELECT plus UPDATE of `password_hash` only (for existing login rehash). Both application roles share the runtime DB connection; clinical separation remains enforced by FastAPI, not separate DB passwords.

The command checks migration head, active account roles and Argon2 password verification, then reconnects as the restricted app role over DIRECT verified TLS, reads table shapes and proves actual DDL, migration-table edits and role-field updates are denied using rolled-back probes. It prints only fixed PASS/error messages. If the connection drops at commit, outcome may be unknown: **do not blindly repeat initialization**. Re-run this verification command with the same identities and passwords:

```bash
CLINIC_DEMO_PUBLIC_ENABLED=false .venv/bin/python -m app.neon_setup verify
```

`verify` applies no migrations or provisioning. It checks the repository head/accounts/grants and runs only rolled-back permission probes. It cannot verify hosted HTTP login while the Render gate is closed. If initialization fails, check the DIRECT endpoint, owner privileges, password, target emptiness and certificate/network prerequisites privately. Never add `sslmode=disable`, allow a pooled/local host, or print exceptions/URLs to troubleshoot. A partial setup requires operator review, not deletion/reset. Future reviewed migrations must be an explicit local operator step with the demo closed; this one-time initializer intentionally cannot upgrade an existing database.

## Exact Render Free configuration (after successful local setup)

Create a **Free** Web Service from this repository, Docker runtime, repository-root build context, Dockerfile `Dockerfile.render`, one instance, **Auto-Deploy Off**, health path `/api/health/ready`, and the image's default CMD. Leave pre-deploy command empty. This needs no shell, one-off job, cron, paid database or extra service. Choose a region near Neon. Creation/deployment is a later explicitly approved operator action; nothing in this preparation performs it.

Set these in Render's service Environment page **before the first deploy** (never in Git, Docker ARGs, frontend variables, CI logs or a copied `.env`):

   | Name | Value / purpose |
   | --- | --- |
   | `CLINIC_ENV` | `production` — required explicitly |
   | `CLINIC_DEPLOYMENT` | `render_demo` — separate from `clinic_lan` |
   | `CLINIC_PUBLIC_ORIGIN` | Exact `https://YOUR-SERVICE.onrender.com`, no slash or alternate host |
   | `CLINIC_DEMO_PUBLIC_ENABLED` | `false` until every pre-exposure gate passes |
   | `CLINIC_DATABASE_URL` | Neon DIRECT TLS URL using **only the SQL-created restricted app role**, never the owner; template below |
   | `PORT` | Render supplies this; the script uses it, or 10000 if absent |
   | `RENDER` | Render supplies `true`; do not set manually on the service |

Connection **template only**, to assemble privately in a password manager and paste directly into Render's Environment editor:

```text
postgresql+psycopg://APP_ROLE:PERCENT_ENCODED_APP_PASSWORD@NEON_DIRECT_HOST:5432/PERCENT_ENCODED_DATABASE?sslmode=verify-full&sslrootcert=/etc/ssl/cert.pem&channel_binding=require
```

Percent-encode password/path characters, particularly `@`, `:`, `/`, `?`, `#`, `%` and `&`. `/etc/ssl/cert.pem` is the CA bundle in the hardened Alpine image, not an Ubuntu path copied into the container. Use the exact confirmed direct Neon endpoint. Do not set `CLINIC_MIGRATION_DATABASE_URL` at all on Render. Owner credentials remain only in the operator's password manager. `CLINIC_APPOINTMENT_POLICY` may contain the existing valid non-secret JSON policy. Render supplies `RENDER=true`, `RENDER_EXTERNAL_HOSTNAME` and `PORT`; do not manufacture them locally. The Dockerfile consumes no database secret at build time.

The one-worker runtime's existing pool is bounded to five connections with no overflow. Direct connections avoid transaction-pooler differences in the current advisory-lock/session SQL. Render and Neon Free can sleep, impose quotas and have cold-start delays; readiness may initially return 503. Wait/recheck reads, never replay writes automatically. Do not use a keep-awake job. Render Free has no durable disk/shell/one-off jobs; PostgreSQL persistence lives only in Neon. Verify current free-plan limits in both dashboards; Free services are for this portfolio demo, not clinic deployment. [Render Free limitations](https://render.com/docs/free), [Neon connection pooling](https://neon.com/docs/connect/connection-pooling).

After a later approved **closed** deploy, confirm liveness/readiness return 200 and `/app/` plus `/api/auth/csrf` return 503. Never open the gate to work around failed readiness or absent migrations. An owner URL must never be present in the Render environment. The application cannot classify real versus synthetic human-entered text; operator access control remains necessary.

## Pre-exposure verification (keep gate closed until complete)

- Build `Dockerfile.render` on a clean Linux/amd64 Docker host and scan the exact resulting base image and pinned Python/npm dependencies for critical/high vulnerabilities. Docker/Podman/Buildah are unavailable on the Ubuntu workstation. The manual, read-only [image verification workflow](../.github/workflows/verify-render-demo.yml) is the reproducible CI alternative; it builds but does **not** push or deploy an image. [Run 40494296645](https://github.com/MohanadMohamed/clinc-final/actions/runs/40494296645) passed on `fix/render-base-image` commit `8bd2c0d`, including a zero HIGH/CRITICAL Trivy scan. Re-run it for the exact commit intended for staging. See the [image-remediation report](tasks/render-base-image.md). A local Vite build is not a substitute.
- On the closed Render service, verify only `/api/health` and `/api/health/ready` respond normally and the running service uses the verified restricted Neon role. Confirm DIRECT TLS parameters, exact demo database/branch and public hostname. Neon is a public database endpoint; do not describe it as private Render networking. If the selected Neon plan offers IP restrictions, verify access from the operator and Render egress before restricting it; do not assume that feature exists on Free.
- Verify real Render HTTP→HTTPS redirect and valid TLS chain while the app gate is closed. The functional checks below require the app gate to be open: perform them only on a separate access-restricted staging service using an isolated synthetic database. Render's native inbound IP rules for web services require a **Scale or Enterprise workspace plan**; a lower plan without an equivalent verified access restriction cannot safely open the staging gate. If such a restriction is unavailable, leave both staging and production closed and record these as blockers. Do not treat a temporary public opening as a safe test. Do not skip certificate errors.
- Under that access restriction, verify Secure/HttpOnly/SameSite Strict cookies, login/logout, CSRF denial, doctor/receptionist role isolation, anonymous 401, and malicious Host rejection. With private authorized test accounts and **synthetic** records only, exercise patient create/edit/archive, concurrent appointment conflict, clinical direct-API 403 for reception, invoice/payment accounting, and deep React routes/assets. Confirm no sensitive request/response bodies in service/platform logs and no browser console/CSP errors.
- Validate Render's first `X-Forwarded-For` address with controlled requests; test malformed/spoofed header handling and rate-limit behavior from two external clients. The per-account throttle remains 5 attempts/15 minutes and per-client throttle 30/15 minutes; do not weaken them for the demo.
- Check deployment rollback, the actual Neon Free restore/retention/quota settings, and operator access to secrets. Do not assume paid backup features; recovery remains NOT TESTED until a synthetic restore drill is performed. No local clinic dump is a demo recovery source.

Only after these checks pass and the production demo database has been reviewed as synthetic-only may the operator change `CLINIC_DEMO_PUBLIC_ENABLED=true` and deliberately redeploy the production service. At that point recheck the exact HTTPS origin, `/app/`, deep links, static assets and both roles. No public deploy or Render resource creation has occurred.

## Restricted staging handoff — commands to run only after approval

First, the operator reviews the exact staging commit and reruns the manual CI workflow on its branch. GitHub requires a `workflow_dispatch` workflow to exist on the default branch, but its `--ref` can select the reviewed feature branch. Do not proceed if any image, Python, npm, inventory or closed-startup step fails. Use a separate empty synthetic Neon target (never a branch copied from real data), initialize it locally as above, then create the closed Render Docker web service with Auto-Deploy Off and only the restricted-role TLS URL. **Free hosting does not itself restrict who can reach the Render URL.** The existing policy still requires verified tester-only network/edge access before opening the staging app gate. Render's native inbound IP allowlist requires a paid workspace feature; on Free, an independently approved and tested equivalent remains a blocker. No such replacement is implemented here. Do not place database URLs/passwords in CLI arguments.

```bash
# Template for the reviewed staging commit; the Render commands below have not run.
gh workflow run verify-render-demo.yml --ref REVIEWED_BRANCH
gh run watch RUN_ID --exit-status
# Only where native allowlisting is available; not a Render Free guarantee:
render services update STAGING_SERVICE_ID \
  --ip-allow-list "cidr=TESTER_EGRESS_IP/32,description=authorized-staging" --output json
render deploys create STAGING_SERVICE_ID --commit REVIEWED_COMMIT_SHA --wait
```

From the allowlisted network, verify the **closed** service using its exact trusted HTTPS hostname. `curl` must validate the certificate normally; never add `-k` or `--insecure`. `CLINIC_PUBLIC_ORIGIN` must exactly match this hostname. Readiness becomes 200 only after the isolated database has been migrated and the app role configured.

```bash
origin=https://STAGING-SERVICE.onrender.com
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' "$origin/api/health"        # 200
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' "$origin/api/health/ready"  # 200 after migration
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' "$origin/app/"             # 503 while closed
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' "$origin/api/auth/csrf"    # 503 while closed
curl --silent --show-error --head "http://STAGING-SERVICE.onrender.com/api/health"                    # HTTPS redirect, inspect Location
```

Confirm a request from an **unlisted** network cannot reach staging. Only after that denial, image/CI success, private-DB checks and operator review may the staging service alone set `CLINIC_DEMO_PUBLIC_ENABLED=true` in Render's secret environment UI and deliberately redeploy. Under the IP restriction, verify `/app/` and deep links return 200, anonymous `/api/patients` returns 401, `/docs` returns 404, and wrong-Host requests are rejected. Use a trusted browser with two private synthetic accounts for login/logout, CSRF, doctor/receptionist RBAC, appointment conflict, visits and billing. Check no console errors or sensitive platform logs. Keep the **production** demo gate closed throughout staging. If the IP restriction cannot be established and tested, stop; do not open either gate.

## Stop and delete

To stop app access, set `CLINIC_DEMO_PUBLIC_ENABLED=false` and redeploy, or suspend the Render service. Revoke demo sessions and rotate the restricted DB password if exposure is suspected. To end the demo, deliberately delete the demo Render service and the isolated Neon demo project/branch/database through their consoles, after checking their identities. Review Neon branches/restore history, exports and stored credentials according to actual retention settings. Confirm the portfolio URL no longer serves the app. These are destructive operator actions; this document does not execute them. Never select the local clinic database or a shared Neon project containing other data.

## Risk-ranked findings and current blockers

- **DEMO-001 — CI gate passed; re-run for staging commit:** the Docker build, pip/npm audits, image-file inventory, closed production startup and HIGH/CRITICAL OS/library Trivy scan passed in [run 40494296645](https://github.com/MohanadMohamed/clinc-final/actions/runs/40494296645) on commit `8bd2c0d`. The [focused report](tasks/render-base-image.md) records the previous Debian findings and remediation. Local Docker remains unavailable; the mutable base tag and vulnerability database require a fresh scan for the exact staging commit. This CI result does not verify the hosted Render runtime.
- **DEMO-002 — HIGH, blocks public enablement:** actual Render HTTPS redirect/proxy headers, Neon TLS/credentials/role behavior, service environment and hosted logs are **NOT TESTED**. Local PostgreSQL tests prove app/setup behavior, not Neon or Render platform behavior. Run the private local Neon setup/verification and then closed-service checks plus access-restricted functional staging before any gate change. Neon Free public TLS is not a private database network.
- **DEMO-003 — HIGH, operational:** any real data typed into the demo would violate the synthetic-only boundary. The app cannot reliably classify names or clinical text as real versus invented; restrict access to authorized reviewers, inspect the fresh isolated DB and train reviewers. Never import local records.
- **DEMO-004 — MEDIUM:** public login can still be availability-targeted. Account and IP throttles exist in PostgreSQL, but a public edge introduces spoofing/shared-proxy and load questions. The first-forwarded-IP rule (`backend/app/api/auth.py:44–54,133`) is used only for throttling; verify it under Render and consider edge controls before a wide audience.
- **DEMO-005 — MEDIUM:** one clinician account and one-time bootstrap have no self-service recovery. The local interactive Neon setup removes the paid shell requirement; secure operator credential custody and a reviewed local revocation/recovery procedure are still required. Never rerun initialization to reset an account.
- **DEMO-006 — HIGH, blocks restricted functional staging on lower plans:** Render's native web-service inbound IP rules require a Scale or Enterprise workspace. Evidence: the [Render inbound IP rules plan table](https://render.com/docs/blueprint-spec) and the conditional staging commands above. Without a verified equivalent access restriction, keep the staging gate closed; local browser tests cannot replace real edge checks.

The previous LAN [findings](security/FINDINGS.md) remain applicable to the intended Windows installation; this demo adds an Internet-facing threat boundary rather than replacing that design.

References: [Render Free limits](https://render.com/docs/free), [web services/TLS](https://render.com/docs/web-services), [Docker services](https://render.com/docs/docker), [auto-deploy controls](https://render.com/docs/deploys), [secret environment settings](https://render.com/docs/configure-environment-variables), [inbound IP plan requirements](https://render.com/docs/blueprint-spec), [CLI commands](https://render.com/docs/cli-reference), [Neon roles](https://neon.com/docs/manage/roles), [Neon secure connections](https://neon.com/docs/connect/connect-securely). The first-XFF-hop rule is based on [Render's published support statement](https://feedback.render.com/features/p/send-the-correct-x-forwarded-for) and still needs live confirmation.
