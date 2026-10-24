# Task 6A endpoint permission matrix

Enumerated against the application OpenAPI in `tests/test_security.py`; new API paths fail the policy inventory test. Both roles use real sessions. Anonymous calls must return 401 on every protected route; reception gets 403 on every doctor route; invalid CSRF gets 403 on every authenticated mutation. Allowed-role empty-body/unknown-ID probes may return 400/404/422: existing workflow tests supply valid records and verify successful operations. Clinical export remains forbidden to both roles.

| Method | Path | Policy |
| --- | --- | --- |
| GET | `/api/auth/csrf` | PUBLIC |
| GET | `/api/health` | PUBLIC |
| GET | `/api/health/ready` | PUBLIC |
| POST | `/api/auth/login` | PUBLIC |
| GET | `/api/appointments` | STAFF |
| GET | `/api/auth/session` | STAFF |
| GET | `/api/billing/fees` | STAFF |
| GET | `/api/billing/invoices` | STAFF |
| GET | `/api/billing/invoices/{invoice_id}` | STAFF |
| GET | `/api/billing/invoices/{invoice_id}/payments` | STAFF |
| GET | `/api/billing/summary/{day}` | STAFF |
| GET | `/api/me` | STAFF |
| GET | `/api/patients` | STAFF |
| GET | `/api/patients/{patient_id}` | STAFF |
| PATCH | `/api/patients/{patient_id}` | STAFF |
| POST | `/api/appointments` | STAFF |
| POST | `/api/appointments/{appointment_id}/cancel` | STAFF |
| POST | `/api/appointments/{appointment_id}/reschedule` | STAFF |
| POST | `/api/auth/logout` | STAFF |
| POST | `/api/billing/invoices` | STAFF |
| POST | `/api/billing/invoices/{invoice_id}/issue` | STAFF |
| POST | `/api/billing/invoices/{invoice_id}/payments` | STAFF |
| POST | `/api/patients` | STAFF |
| POST | `/api/patients/{patient_id}/archive` | STAFF |
| GET | `/api/visits` | DOCTOR |
| GET | `/api/visits/export` | DOCTOR |
| GET | `/api/visits/{visit_id}` | DOCTOR |
| GET | `/api/visits/{visit_id}/export` | DOCTOR |
| GET | `/api/visits/{visit_id}/history` | DOCTOR |
| PATCH | `/api/visits/{visit_id}` | DOCTOR |
| POST | `/api/billing/fees` | DOCTOR |
| POST | `/api/billing/invoices/{invoice_id}/adjustments` | DOCTOR |
| POST | `/api/billing/invoices/{invoice_id}/void` | DOCTOR |
| POST | `/api/billing/payments/{payment_id}/reverse` | DOCTOR |
| POST | `/api/visits` | DOCTOR |
| POST | `/api/visits/search` | DOCTOR |
| POST | `/api/visits/{visit_id}/addenda` | DOCTOR |
| POST | `/api/visits/{visit_id}/finalize` | DOCTOR |

PUBLIC means no authenticated user is required; CSRF origin/throttle and login credentials still apply. STAFF means doctor and receptionist. DOCTOR means doctor only, with clinical exports disabled for everyone.

Additional public framework routes: GET `/openapi.json`, `/docs`, `/docs/oauth2-redirect`, `/redoc`. These expose metadata/help, not patient records. No public account-registration or runtime provisioning endpoint exists. Local bootstrap requires operator trust. Object policy: one clinic/doctor; both staff roles share administrative objects, the doctor owns clinical access. Guessing IDs does not alter role authorization.
