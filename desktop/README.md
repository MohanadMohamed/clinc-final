# Desktop prototype (Task 7A)

`launcher.py` opens the FastAPI-hosted React UI at `/app/` in pywebview. It opens no backend, PostgreSQL process or local server. Login remains in the server-rendered browser session; the launcher accepts only a bare HTTPS origin and rejects URL credentials, paths, queries and fragments. No app credentials belong in launcher config.

On the doctor PC, use the trusted local HTTPS origin; on reception, use the doctor PC's trusted LAN hostname. For example, from the repository root after installing pywebview into an isolated Python environment:

```bash
python -m pip install -r desktop/requirements.txt
python -m desktop.launcher --server-url https://localhost:8443
python -m desktop.launcher --server-url https://doctor.clinic.lan:8443
```

The first command is a doctor-PC example; the second URL is a receptionist-PC example, not a resolvable demo host. The receptionist must reach the doctor's HTTPS server; it does not install or start the FastAPI application or PostgreSQL. The doctor PC must separately run the backend and sole PostgreSQL database. Browser certificate warnings are not bypassed by this launcher.

Before Windows GUI validation, choose a supported Windows version and pywebview renderer, install that renderer's runtime (for example WebView2 if selected), install pywebview in a test environment, and establish trusted CA material for the doctor-host certificate on both PCs. Check TLS hostname validation, keyboard/Arabic input, session cookies, printing, window close/reopen and loss/recovery of LAN connectivity on Windows. Use synthetic data and a disposable test database. Task 7B must pin/package dependencies, choose installer tooling and run Windows acceptance; this Ubuntu prototype is not an EXE.
