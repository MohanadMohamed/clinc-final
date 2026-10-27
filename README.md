# Clinc Final

**Arabic-first Clinic Management System for Neurology & Psychiatry**

A full-stack application for managing the day-to-day workflow of a **single-doctor clinic**: patient registration, appointment scheduling, clinical visits, and billing. It features a right-to-left Arabic interface and separate access permissions for the doctor and reception staff.

> **Current status:** The application runs locally on Ubuntu for development and testing. The planned two-computer Windows deployment and a public online demo are **not released or verified yet**. Use synthetic data only.

## Features

| Area | Implemented functionality |
| --- | --- |
| **Authentication & access** | Individual accounts, session-based login/logout, CSRF protection, and backend-enforced doctor/receptionist permissions. |
| **Patients** | Registration, search, administrative details, editing, and archival. |
| **Appointments** | First visits and follow-ups; daily schedule, booking, rescheduling, cancellation, Cairo time handling, and database-backed conflict prevention. |
| **Clinical visits** | Doctor-only visit history, draft clinical notes, saving, finalization, revision history, and follow-up planning. |
| **Billing** | Consultation fees, invoices, cash payments, balances, administrative printable receipts, and daily collection summaries in EGP. |
| **Arabic UI** | RTL pages, validation feedback, responsive layouts, and role-aware navigation. |

### Access control

- **Doctor:** Authorized clinical records and notes, appointment management, and permitted administrative/billing actions.
- **Receptionist:** Patient registration, scheduling, and permitted billing tasks; **no access to private clinical notes or diagnoses**.

Access restrictions are enforced by FastAPI, not only by hiding frontend navigation.

## Technology stack

| Layer | Technology |
| --- | --- |
| Frontend | React, TypeScript, Vite, Tailwind CSS, TanStack Query, React Hook Form, Zod |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy |
| Database | PostgreSQL, Alembic |
| Testing | pytest, Vitest, browser-based integration tests |
| Desktop prototype | pywebview launcher (source-run prototype; no released Windows installer) |

## Architecture

```text
React + TypeScript (Arabic RTL)
           |
           | HTTP on loopback in explicit development mode
           v
     FastAPI REST API
       |          |
 Authentication  Application services
                  |
            SQLAlchemy
                  |
             PostgreSQL
```

The intended clinic installation uses the **doctor's Windows PC** to host the backend and the single PostgreSQL database, while a **receptionist PC** connects over a trusted local network. That Windows/LAN installation is a deployment target, **not a completed release**.

## Run locally (Ubuntu)

### Prerequisites

- Python **3.14** with `venv` support
- Node.js **22** and npm
- PostgreSQL **18** (local service or the optional development-only Docker Compose database)

Install dependencies:

```bash
git clone https://github.com/MohanadMohamed/clinc-final.git
cd clinc-final

python3.14 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt

cd frontend
npm ci
cd ..
```

Configure a **separate development database** and its restricted application/migration accounts. Copy the example settings and replace the placeholders locally:

```bash
cp .env.example .env
chmod 600 .env
```

Set the actual `CLINIC_DATABASE_URL` and `CLINIC_MIGRATION_DATABASE_URL` values in `.env`. Never commit this file or use real patient data. See the [configuration example](.env.example) and [project documentation](docs/) for database setup details.

Apply the existing migrations to **your development database only**:

```bash
cd backend
.venv/bin/alembic upgrade head
cd ..
```

Run the local development app from the repository root:

```bash
./scripts/dev_local.sh
```

Open **http://127.0.0.1:5173/login** and sign in with an existing authorized account.

The script starts Vite and FastAPI on `127.0.0.1` only. It does **not** create accounts, reset data, or apply migrations. On a **new, empty database**, the initial doctor account is created once via the documented interactive `app.bootstrap` procedure; there are no default credentials.

## Tests

After configuring the required local test dependencies, you can run:

```bash
# Backend tests (use disposable test PostgreSQL fixtures)
cd backend
.venv/bin/pytest -q
cd ..

# Frontend checks
cd frontend
npm run typecheck
npm run build
npm test
```

Additional browser checks and test evidence are recorded in [docs/tasks](docs/tasks/) and the [project status](docs/STATUS.md). Never run test-database lifecycle or destructive migration commands against a real clinic database.

## Repository layout

```text
backend/       FastAPI app, models, migrations, and backend tests
frontend/      React application, components, and frontend tests
desktop/       Experimental desktop launcher and related tests
scripts/       Local development scripts
docs/          Architecture, implementation notes, security, and test reports
.env.example   Placeholder-only environment configuration
```

## Security and current limitations

- Development HTTP is restricted to explicit **loopback** mode; network deployments require properly configured **HTTPS**.
- Sessions, CSRF validation, and doctor/receptionist authorization remain server-enforced.
- The Windows desktop installers, physical two-PC LAN operation, backup/recovery process, and real-world clinical deployment **have not completed acceptance testing**.
- **No public live-demo URL is available yet.** A future portfolio demo must use its own database containing synthetic records only.
- This software is **not certified or approved for use with real patient records**. Further operational, security, and privacy reviews are required.

## Documentation

- [Architecture](docs/architecture/ADR-001.md)
- [Product requirements](docs/requirements/MVP.md)
- [Implementation status](docs/STATUS.md)
- [Desktop prototype](desktop/README.md)

---

**Repository:** [MohanadMohamed/clinc-final](https://github.com/MohanadMohamed/clinc-final)  
**Author:** [MohanadMohamed](https://github.com/MohanadMohamed)
