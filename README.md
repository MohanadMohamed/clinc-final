<<<<<<< HEAD
# Arabic Neurology & Psychiatry clinic — development scaffold

## Current Ubuntu loopback development

PostgreSQL must already be running with the existing migrated **development** database. Keep its credentials in the untracked root `.env` (copy the placeholder-only `.env.example` only when setting up a new environment). From the repository root, after installing dependencies as below:

```bash
./scripts/dev_local.sh
```

Open `http://127.0.0.1:5173/login` and sign in with an existing authorized account. The script binds FastAPI to `127.0.0.1:8000` and Vite to `127.0.0.1:5173`; Vite proxies `/api` to FastAPI. It sets `CLINIC_ENV=development` and `CLINIC_PUBLIC_ORIGIN=http://127.0.0.1:5173` for these processes, without changing `.env`, creating accounts, migrating, or resetting data. You may instead run two terminals:

```bash
cd backend
CLINIC_ENV=development CLINIC_PUBLIC_ORIGIN=http://127.0.0.1:5173 .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --no-access-log --no-proxy-headers
```

```bash
cd frontend
npm run dev -- --host 127.0.0.1
```

Check `http://127.0.0.1:5173/api/health/ready` for `{"status":"ready"}`. The initial doctor bootstrap marker and a doctor account were confirmed present in the currently configured local database by a read-only existence query; **do not bootstrap it again**. For a *different fresh database* only, after applying its migrations and ensuring no doctor exists, use `cd backend && .venv/bin/python -m app.bootstrap --username YOUR_DOCTOR_USERNAME` in an interactive local terminal with a DB role permitted to insert the initial user. It prompts for a unique password and has no default. Existing account credentials are never reset by startup.

Loopback HTTP is accepted only with explicit `CLINIC_ENV=development` and an exact `127.0.0.1`, `localhost`, or `::1` public origin. The API also rejects non-loopback peers in this mode. Session cookies remain HttpOnly and SameSite Strict, with a distinct HTTP-development cookie name; CSRF and server-side roles remain enforced. Production is the default: `CLINIC_ENV=production` requires a bare HTTPS public origin and retains the Secure `__Host-clinic_session` cookie. Windows LAN deployment still requires trusted HTTPS and separate doctor/receptionist accounts. Never bind the development processes or PostgreSQL to a LAN address.

The old sprint setup notes below are historical; this section is the current Ubuntu startup path. [Local development fix report](docs/tasks/local-development-fix.md) has verification commands and limits.

Current prototype: FastAPI serves a Vite production build at `/app/`; the thin source-run pywebview launcher is described in [desktop/README.md](desktop/README.md). See [Task 7A](docs/tasks/7A.md) and [STATUS](docs/STATUS.md) for current checks and limits. The older sprint instructions below are retained as historical setup notes.

Task 0B supplies system health only. No authentication or patient functionality exists. Fixed architecture: [ADR-001](docs/architecture/ADR-001.md); [product baseline](docs/requirements/BASELINE.md). Use synthetic data only.

## Ubuntu prerequisites and locked installation

Verified toolchain: Python 3.14.4, Node 22.22.1, npm 9.2.0 and PostgreSQL 18 (see the task report for the tested patch). Install Python 3.14 with venv support, Node 22 and PostgreSQL 18 from your approved Ubuntu package sources before running these commands. The commands below assume PostgreSQL binaries at `/usr/lib/postgresql/18/bin`; override `PG_BIN` for another local installation. They do not install or modify Windows services.

From this repository root:

```bash
python3.14 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
cd frontend
npm ci
cd ..
```

`requirements.txt` and `package-lock.json` pin resolved dependencies. `requirements.in` records direct Python dependencies; do not regenerate pins incidentally. The shadcn CLI is an authoring tool, not a runtime dependency. Configuration is in `frontend/components.json` (Tailwind v4, alias `@`, RTL); utility composition is in `src/lib/utils.ts`. No unused UI widgets or fake workflows are supplied. Query and Zod validate real health responses; Hook Form is installed for later forms.

## Safe disposable verification — no existing database required

Run as an ordinary Ubuntu user, not root. This creates a new private temporary cluster, exposes no TCP database listener, runs baseline migrations, checks real database readiness and starts temporary loopback web servers to verify the Vite proxy. Ports 8000 and 5173 must be free. It refuses to reuse existing web servers. It stops its processes and removes only its own temporary cluster. No existing database URL is used for these checks.

```bash
cd backend
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
PG_BIN=/usr/lib/postgresql/18/bin PYTHONPATH=. .venv/bin/python scripts/check_disposable_db.py
cd ../frontend
npm run typecheck
npm run build
npm test
cd ..
```

The migration check performs `upgrade head`, `current`, `check`, `downgrade base`, `upgrade head` on its disposable database only. The baseline creates no business tables; Alembic owns its version table. Never run this downgrade sequence on an existing development or clinic database. Pytest uses an intentionally unavailable endpoint and test-only mocks to verify failures; live UI uses real API requests.

## Persistent localhost development database (optional)

Use a dedicated empty synthetic development database. With a locally installed PostgreSQL 18 service, open its administration shell:

```bash
sudo -u postgres psql
```

Inside psql, create dedicated development roles and set unique passwords interactively (no passwords in command history):

```text
CREATE ROLE clinic_dev_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
\password clinic_dev_migrator
CREATE ROLE clinic_dev_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
\password clinic_dev_app
CREATE DATABASE clinic_dev OWNER clinic_dev_migrator;
GRANT CONNECT ON DATABASE clinic_dev TO clinic_dev_app;
\q
```

Do not execute creation commands against an existing clinic installation. Restrict PostgreSQL to loopback with password authentication. Future migrations must grant the application only required table privileges; the readiness query currently needs no business tables.

Create configuration locally:

```bash
umask 077
cp .env.example .env
editor .env
```

Replace placeholders with the development role values and generated passwords. URL-encode reserved characters in passwords. `CLINIC_DATABASE_URL` uses the application role; `CLINIC_MIGRATION_DATABASE_URL` uses the migration role. Both point to `127.0.0.1:5432/clinic_dev`. Never print, commit or upload `.env`. Frontend configuration contains no database credentials. Settings load the root `.env` independently of the working directory and redact secret fields; readiness failures return only a generic status.

Alternatively, Docker Compose is an **optional development-only** PostgreSQL provider. Configure the three `POSTGRES_*` placeholders in the untracked `.env`, then run:

```bash
docker compose up -d db
```

The container's `POSTGRES_USER` is its bootstrap administrator: use it locally to create a separate application role as above, then set the application's URL accordingly. Do not use that bootstrap role for the application. Do not start Compose on a port already occupied by native PostgreSQL. No volume reset/removal command is required or provided. Compose itself was not executed in the recorded checks.

Apply migrations to the dedicated development database:

```bash
cd backend
.venv/bin/alembic upgrade head
.venv/bin/alembic current
```

Start API in terminal one (from `backend/`):

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --no-access-log
```

Start UI in terminal two (from the repository root):

```bash
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173/`. It has `lang="ar" dir="rtl"`, React Router, and a visible real connection result. Vite forwards `/api` to `http://127.0.0.1:8000`. Check the proxy without a browser:

```bash
curl --fail http://127.0.0.1:5173/api/health
curl --fail http://127.0.0.1:5173/api/health/ready
```

Liveness is `200 {"status":"ok"}` even if PostgreSQL is unavailable. Readiness executes `SELECT 1`, returning `200 {"status":"ready"}` or sanitized `503 {"status":"unavailable"}`. Neither endpoint exposes credentials or patient information. Connections are bounded and sessions close after each request; application startup never creates tables or runs migrations. HTTP is permitted only on loopback for development. LAN deployment requires HTTPS.

## Deployment boundary and test limits

The doctor Windows PC will host FastAPI and PostgreSQL as services plus the pywebview doctor client; reception has the thin desktop client only. Docker and Node development servers are not final-runtime requirements. Built React assets are local; normal clinic operation must not depend on Internet services. Production static serving, TLS/service management and desktop packaging belong to later tasks. Build/test PyInstaller and installer packages on Windows, not Ubuntu.

Vitest/Testing Library component tests are not browser acceptance. Playwright is installed for later browser tests; no browser or Windows packaging check is claimed by this task. Technical results do not establish clinical compliance or readiness. See [0B report](docs/tasks/0B.md) and [STATUS](docs/STATUS.md). **Next task: 1A**, only when requested.

## Task 1A backend authentication

Server-side login/logout/session and `/api/me` are now available. See [1A contract, bootstrap and secrets](docs/tasks/1A.md) for the CSRF handshake, mandatory HTTPS cookies, local one-time doctor creation and least-privilege DB grants. No public registration or frontend login UI exists. Apply `alembic upgrade head` before using auth. Backend `pytest -q` now starts its own disposable PostgreSQL fixture, requiring local PostgreSQL binaries and no existing database credentials. The current next task is **1B**, superseding the scaffold-only handoff above.
=======
# clinc-final
>>>>>>> origin/main
