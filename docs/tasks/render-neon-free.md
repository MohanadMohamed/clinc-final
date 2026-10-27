# Render Free + Neon Free preparation — 2026-10-27

Prepared a local interactive operator workflow; **no Neon setup or Render deployment was performed**. This work does not change the Windows LAN clinic architecture or any business feature. The public demo gate remains false. Existing untracked README drafts and diagram files were preserved.

## Files and behavior

- `backend/app/neon_setup.py`: `initialize` and `verify`, with no password/URL arguments. Ignores `.env` and local runtime DB configuration. Requires a private TTY, a DIRECT Neon hostname, certificate/hostname verification, channel binding, exact target identity, an empty database and explicit typed confirmation. Initialization atomically runs the existing Alembic revisions, SQL app-role creation/grants and existing doctor/receptionist provisioning. Errors suppress connection details; commit uncertainty requires verification before retry.
- `backend/migrations/env.py`: accepts the validated SQLAlchemy connection/outer transaction from operator tooling. Ordinary Alembic CLI Settings validation is preserved; no platform environment spoofing or startup migrations.
- `backend/app/demo_db_role.py`: explicit Neon-only cleartext-password-over-TLS SQL path because Neon documents that prehashed role passwords are unsupported. Existing non-Neon callers still send a locally derived SCRAM verifier. No password is logged by the tooling; provider query/log handling still needs hosted review.
- `backend/tests/test_neon_setup.py`: rejects local/pooled/injected hosts, asserts TLS requirements and noninteractive refusal, and exercises real migrations, atomic rollback, wrong confirmation, nonempty/repeated setup denial, password/role verification, SQL privileges and HTTP authorization on disposable PostgreSQL.
- `docs/LIVE_DEMO_DEPLOYMENT.md` and `docs/STATUS.md`: free-plan procedure, restricted app-role TLS URL, exact settings, verification and unresolved hosted gates.

Runtime grants exclude account provisioning and schema/migration administration. The app may update only the `users.password_hash` column for existing password rehash; clinical access still depends on FastAPI doctor/receptionist authorization. The app role has no privileged role membership, object ownership or role/database creation rights. The isolated demo's PUBLIC database/schema/application-object access is revoked without changing Neon-owned extension objects. No data is imported or automatically seeded.

## Exact private operator commands

```bash
cd /home/mohanad/Desktop/Clinc-final/backend
.venv/bin/python -m app.neon_setup --help
CLINIC_DEMO_PUBLIC_ENABLED=false .venv/bin/python -m app.neon_setup initialize
# Later, or after an uncertain connection outcome; applies no migrations:
CLINIC_DEMO_PUBLIC_ENABLED=false .venv/bin/python -m app.neon_setup verify
```

Use the existing pinned Python 3.14 environment and follow the [prompt sequence and Render environment table](../LIVE_DEMO_DEPLOYMENT.md). Enter credentials only in the hidden local prompts, and store them privately. Do not provide them to chat, command arguments, CI or source control. Render Free uses `Dockerfile.render`, the default CMD, readiness `/api/health/ready`, Auto-Deploy Off and no pre-deploy command. Set `CLINIC_ENV=production`, `CLINIC_DEPLOYMENT=render_demo`, the exact HTTPS origin and `CLINIC_DEMO_PUBLIC_ENABLED=false`; only the SQL-created app-role verified-TLS Neon URL belongs in `CLINIC_DATABASE_URL`. Never set an owner or migration URL on Render.

## Verification evidence

| Result | Check and exact command |
| --- | --- |
| PASS | From `backend/`: `CLINIC_ENV=production CLINIC_PUBLIC_ORIGIN=https://clinic.local .venv/bin/pytest -q --tb=short` — **68 passed**, exit 0. Existing authentication, CSRF, role separation, booking concurrency, patients, visits, billing and Render gates remained covered. New setup tests run under a non-superuser database owner with CREATEROLE and use a separate restricted app connection. |
| PASS | `.venv/bin/ruff check app/neon_setup.py app/demo_db_role.py migrations/env.py tests/test_neon_setup.py` — exit 0. |
| PASS | `CLINIC_ENV=production CLINIC_PUBLIC_ORIGIN=https://clinic.local .venv/bin/pytest -q --tb=short tests/test_neon_setup.py tests/test_render_demo.py` — **19 passed**, exit 0, including added restricted-role patient writes/billing-trigger execution and receptionist fee-change denial. |
| PASS | `.venv/bin/python -m app.neon_setup --help` — exit 0; only `initialize`/`verify` actions exposed, no secret arguments. |
| PASS | `git diff --check` and a Python/Path check of local Markdown targets in the deployment guide, status and this report — exit 0; all local links resolve. |
| NOT TESTED | Actual Neon endpoint/TLS/SCRAM password authentication, provider SQL-role behavior, migrations and private demo accounts: no Neon connection details/credentials were supplied to an interactive local operator session. **No Neon connection was attempted.** The local integration cluster uses Unix-socket trust, so its role-selection tests do not establish hosted password authentication. |
| NOT TESTED | Actual Render Free deployment, TLS/proxy behavior, Neon reconnect/cold-start behavior and hosted browser flows. No Render resource, secret update, migration or public exposure was performed. |

The first sandboxed focused test attempt passed nine unit cases but could not start PostgreSQL because its temporary Unix socket was denied. An authorized retry using the same disposable-only fixture passed the focused tests; the full-suite result above is from actual successful execution. Approval review also timed out before some test commands started; these were retried once, not bypassed. Existing Starlette TestClient and Alembic configuration deprecation warnings remain non-failing.

## Remaining deployment blockers

1. Run `initialize` and `verify` privately against the independently confirmed empty Neon demo target and retain only sanitized PASS/FAIL evidence. No live Neon result is claimed here.
2. Re-run the existing image/security CI on the exact reviewed staging commit before a later deployment. No push/deployment is authorized by this preparation.
3. Render's URL remains publicly reachable even with the app gate closed. Existing staging policy requires a verified tester-only network/edge restriction before opening that gate; Render Free does not supply the native paid-workspace allowlist. No equivalent was implemented or verified. Keep the gate closed until this is resolved.
4. On a later approved closed deploy, verify readiness, origin/Host, HTTPS redirect/chain, environment role/TLS settings and safe hosted logs. Under verified staging access, check actual login/logout, CSRF, both roles, patients, conflict booking, clinical 403, billing, deep links and restart/persistence without replaying writes. Check actual Neon Free quotas/retention and Render sleep/egress limits; no paid backup or private-network claim applies to this design.

Local checkpoint only; no push, merge or deployment. Next planned clinic task remains **8A**, outside this request.
