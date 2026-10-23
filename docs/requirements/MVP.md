# Arabic single-doctor clinic MVP

Date: 2026-10-23. This is the original Neurology & Psychiatry clinic's requirements baseline, written in [Task 0A](../tasks/0A.md). [ADR-001](../architecture/ADR-001.md) defines the architecture; the [glossary](../../GLOSSARY.md) defines domain terms. The fixed [product baseline](BASELINE.md) is authoritative. Detailed journeys, billing rules and session/correction policies below remain draft proposals for review; they are not all confirmed user decisions. Requirements below are our design decisions unless explicitly attributed to the reference source in the task report. They are not implemented features.

## Fixed scope

One doctor, one clinic and one central PostgreSQL database. The doctor PC runs FastAPI and the React + TypeScript UI; both Windows PCs run pywebview thin desktop clients over trusted LAN HTTPS. FastAPI and PostgreSQL run as Windows services on the doctor PC; the receptionist PC runs the client only. No third server or Internet connection is needed in normal operation. Ubuntu is for development; Windows packages must be built/tested on Windows using PyInstaller plus selected Windows installer tooling. The doctor and receptionist have independent accounts, with optional additional receptionist users later. All accounts have server-enforced permissions. UI is Arabic-first and RTL, including forms, validation and printable output; mixed Arabic/Latin medication names, phone numbers and identifiers must remain readable. All development and acceptance data is synthetic.

## User journeys and acceptance gates

### Registration and returning patients

Receptionist or doctor searches by clinic identifier, name or phone before creating a patient. A new record captures an Arabic-capable display name, date of birth or explicitly approximate age, and optional contact details. Unknown phone/DOB must not require fabricated values. Address and guardian/contact details are collected only when needed and under a confirmed policy. No national identifier or external identity integration is required for the MVP.

The server assigns a stable clinic identifier. Potential duplicate matches are warnings for review, not proof of identity; shared family phones and similar names must not force merging. Reception may correct administrative data with an audit trail. Clinical information does not belong in registration free text. Automated merging is outside the MVP.

Acceptance: synthetic patients with Arabic names and shared phone numbers remain distinct; searches find the intended record; repeated submission cannot accidentally create duplicate records; invalid fields produce Arabic UI feedback backed by API validation; the clinic identifier survives demographic corrections. Reception responses contain only approved administrative fields.

### Appointments and arrival

For this MVP, a booking references an existing patient. Reception can select a time, reschedule, cancel or mark a patient arrived/no-show. The doctor sees the same schedule. A walk-in is registered, then placed in the day's arrival queue without inventing a past appointment. Administrative scheduling labels must not contain diagnoses or psychiatric narratives.

Planned transitions: `scheduled -> arrived | cancelled | no_show`; rescheduling changes the time of a scheduled booking and retains its audit history. A visit linked to an arrived appointment marks that booking completed when the doctor completes the encounter. Rescheduling/cancelling an already-started encounter is rejected. The server resolves concurrent booking attempts and rejects overlapping active reservations; overbooking is excluded until explicitly specified. Slot length and clinic timezone must be confirmed before implementation.

Acceptance: two clients racing for the same slot yield one accepted reservation and an explicit conflict; a cancelled slot can be reused; no-show/cancellation does not create a clinical visit or payment; repeated arrival does not duplicate queue entries; both PCs reflect saved changes and show a clear connection failure when unavailable. No fake successful save or offline write queue.

### Doctor visit and follow-up

The doctor selects an arrived patient or walk-in, confirms identity and opens the encounter. Only the doctor can read prior clinical history and write complaints, relevant neurological/psychiatric history, examination, assessment, diagnoses, plan, medication instructions and follow-up recommendations. These are documentation functions, not automated clinical advice or diagnostic scoring.

Visit lifecycle: `draft -> finalized`. The doctor can save drafts and finalize the encounter. Finalized content is corrected through attributed addenda retaining the original, not silent replacement. A follow-up is a new encounter linked to the same patient, with an optional previous-visit reference. Appointment and financial state remain distinct from clinical state; unpaid charges must not automatically prohibit documentation or finalize a visit.

Acceptance: receptionist requests to clinical list/detail/search/write/print routes are rejected even with a known identifier; administrative responses and errors leak no clinical fields; draft saving is durable; finalization and corrections preserve authorship and chronology; concurrent edits cannot silently overwrite newer work. Doctor-only clinical printouts render Arabic and mixed scripts correctly.

### Billing and receipts

Reception or doctor records an invoice for a consultation/follow-up using a doctor-maintained fee list, records a payment, and prints a receipt. Administrative descriptions are generic clinic service labels; they must not expose diagnoses, medications or visit notes. Payment records and charge records are separate. The server calculates authoritative totals and balances using exact monetary arithmetic, retains historical prices and binds each payment to its invoice.

Baseline: a single currency (to be confirmed), cash collection, outstanding balances and partial payments. No card gateway, insurer claims or accounting ledger integration. Invoice lifecycle is `draft -> issued -> void` where void is permitted only under doctor-controlled correction rules. Payment-derived states are unpaid/partially-paid/paid, not freely editable labels. Reception cannot discount, refund, reverse payments or void invoices; doctor-authorized corrections require a reason and retain the original records. Doctor corrections must reconcile payments and balances rather than delete history. A refund is a recorded reversal of a received payment, not an invoice deletion.

Acceptance: tampered client totals are rejected or recomputed; retries do not double-charge; partial payments update the balance correctly; overpayment is rejected in the MVP; two payment attempts cannot create an invalid balance; receipt reprint creates no financial transaction; doctor correction and receptionist denial are audited; the daily collection summary reconciles with payment/reversal records. Confirm receipt format/numbering and obligations before billing implementation.

## Role-permission matrix

Allowlist enforced by FastAPI on every route and object, independent of PC, navigation or UI state. No unauthenticated patient/financial/clinical access. Doctor inherits the allowed administrative actions but remains a separately authenticated account.

| Capability / data | Doctor | Receptionist |
| --- | --- | --- |
| Login/logout, own session, own password | Allow | Allow |
| Create/disable receptionist accounts; assign roles | Allow | Deny |
| Search/read/create/correct patient administrative identity/contact fields | Allow; audited | Allow; audited |
| Read prior diagnoses, clinical history, medications or notes | Allow | Deny, including previews/search/export |
| Schedule/reschedule/cancel/arrive/no-show | Allow | Allow within server transition rules |
| See queue, visit occurrence/date and administrative progress | Allow | Allow minimal fields only |
| Start clinical visit, save/finalize note, add correction | Allow | Deny |
| Print clinical summary or prescription | Allow | Deny |
| Read approved fees; issue invoice; record cash payment; print receipt | Allow | Allow |
| See outstanding balance and daily collection totals | Allow | Allow financial fields only |
| Change fees, grant discount, void invoice, reverse/refund payment | Allow with reason/audit | Deny |
| Browse audit history, clinical exports or full data exports | Doctor-only; export policy must be specified before enabling | Deny |
| Backup/restore, migrations, TLS/OS configuration | Local authorized operator procedure, outside routine UI | Deny |
| Permanently delete patient/clinical/payment/audit history | No routine MVP operation | Deny |

An OS administrator can access host resources outside the application permission model. Receptionist accounts must not be given doctor-PC administration or database credentials. Exports are disabled until their policy is approved; a doctor-only designation is not authorization to implement an unspecified export feature.

## Data boundaries and invariants

| Boundary | Owned data | Permitted sharing |
| --- | --- | --- |
| Identity/access | Accounts, password hashes, roles, revocable sessions | Authenticated actor/permissions internally; never hashes/tokens to UI |
| Patients | Stable clinic identity, demographics and necessary contacts | Minimal identity/contact projection to reception, schedule and billing |
| Scheduling | Booking time/status, arrival order, patient reference | Operational queue/progress to both roles; no clinical content |
| Clinical visits | Encounter history, diagnoses, notes, plans, prescriptions/addenda | Doctor only; administrative occurrence/status/reference to other modules |
| Billing | Fee catalog, historical invoice items, payments, reversals, receipts | Approved financial projection to both roles; no clinical free text |
| Audit/operations | Actor/action/object/time/outcome, backup metadata | Doctor-authorized audit views or local operator procedures; no copied patient narrative |

One patient can have many appointments and visits; visits may exist without appointments. A linked appointment produces at most one encounter. An invoice references its patient and, when applicable, encounter; neither payment nor invoice creation proves a visit happened. Referential integrity, idempotent mutations and conflict handling must be tested when implemented. No database tables or migrations are specified or created by 0A.

List counts, search hints, receipt templates, print routes, logs, error messages and browser storage must respect the same field boundaries as detail views. Fail closed when authentication or authorization cannot be resolved. No generic object serialization that exposes clinical fields to reception. Use audit events and correction records instead of hard deletion for clinical/financial history; retention policy remains an explicit pre-release decision.

## Non-goals

- Multiple doctors/branches/tenants; inpatient wards, beds, surgery, emergency-department workflows.
- Laboratory/radiology ordering engines, pharmacy inventory, dispensing, insurance claims, payroll or full accounting.
- Cloud services, patient portals, telemedicine, SMS/WhatsApp/email delivery, online payments or remote access outside the clinic LAN.
- Disconnected-from-server writes/offline synchronization (normal LAN operation without Internet is required), receptionist-side database, microservices or additional server machines.
- Automated diagnosis, prescribing recommendations, psychiatric scoring or AI clinical decision support.
- Source/module import or stack migration from the reference EMR; migration of existing patient records; real data in development.
- Attachments/scans, bulk clinical exports, automated patient merging and destructive deletion until separately scoped.

## Next tasks: acceptance criteria, not implementation authorization

**Current authorization: Sprint 0 Task 0A only. Next task: 0B.** An existing partial 0B scaffold is preserved outside this documentation task and must be reviewed against the criteria below when work is requested. Later authentication and Windows deployment topics have acceptance criteria but no authorization to implement them. Their task IDs and sequence will be assigned separately.

| Task | Acceptance criteria |
| --- | --- |
| **0B — Local development scaffold** | Pin compatible Python/Node/PostgreSQL/tool versions and lock dependencies; create original FastAPI and React+TypeScript skeletons plus Alembic wiring; add safe config examples and ignore rules; bind dev servers to loopback with a working `/api` proxy; prove a real UI-to-API request and a real synthetic DB readiness check with useful failure behavior; no patient/appointment/visit/billing features or mock live data. An empty RTL shell and real system health are sufficient. Document and execute exact install/start/lint/typecheck/build/test commands on the available host; migration checks run only against a disposable synthetic DB. Record unsupported platform checks as NOT TESTED. |
| **Identity and permission foundation — unscheduled** | Implement separate accounts, hashed credentials, revocable sessions, secure deployed cookies and CSRF protection; test anonymous denial, valid doctor/reception access, forbidden-role denial, forged role input, logout/expiry/disabled-account revocation; prove API enforcement using integration tests rather than hidden UI; no clinical/billing domain features required. Specify account recovery and timeouts; update docs with evidence. |
| **Two-PC operational baseline — unscheduled** | On approved Windows test machines with synthetic data, verify service installation/reboot, trusted LAN HTTPS, pywebview clients on both PCs, client-only receptionist setup, Windows-built PyInstaller/installer packages, WAN-disconnected normal operation, API authentication, PostgreSQL LAN isolation, firewall restriction, certificate renewal procedure, network/server failure behavior and encrypted backup/isolated restore. Record actual versions and commands, choose recovery objectives/key custody, and test rollback. Windows/browser/LAN checks require execution on the relevant tools/machines; missing access blocks this task's acceptance. No real-PC deployment without approval. |

Business-feature tasks are deliberately not assigned or implemented here. Their acceptance gates are the journeys and permission matrix above, supplemented by risk-based tests. Resolve the relevant [open decisions](../architecture/ADR-001.md) before each feature is authorized. Current progress is in [STATUS](../STATUS.md).
