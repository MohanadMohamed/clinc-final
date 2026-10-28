# Desktop client — Milestone 8A preparation

`launcher.py` opens the FastAPI-hosted React UI at `/app/`. It starts no backend, PostgreSQL instance or local web server. Login/CSRF and role permissions remain on the same-origin API. Reception runs this client only; doctor hosts the sole FastAPI/PostgreSQL services and also uses the client.

The exact Windows build, isolated test database/TLS setup and GUI acceptance steps are in [WINDOWS_8A_STATUS](../docs/WINDOWS_8A_STATUS.md). **Windows EXE and GUI execution are NOT TESTED.** This is preparation for a console/onedir test build, not an installer or production clinic release.

After installing a supported desktop environment, source-mode invocation remains:

```bash
python -m pip install -r desktop/requirements.txt
python -m desktop.launcher --server-url https://doctor.clinic.home.arpa:8443
python -m desktop.launcher --config desktop/packaging/reception-client.example.toml
python -m desktop.launcher --check-config --config desktop/packaging/doctor-client.example.toml
```

`--check-config` validates without importing pywebview or opening a GUI. Profiles allow only an HTTPS `server_url`, at most 4 KiB; no credentials, paths, queries or fragments. Explicit CLI origin/profile wins over the existing `CLINIC_SERVER_URL` fallback. Profile names confer no API role. Use the same canonical trusted doctor-host origin on both PCs. `https://localhost:8443` is suitable only for the documented single-machine HTTPS smoke environment.

The launcher requests WebView2 (`edgechromium`) explicitly, without devtools, remote debugging or TLS bypass. The Windows spec also excludes the upstream MSHTML fallback module so the frozen client must fail if WebView2 is unavailable; verify this on Windows. Source-mode pywebview is not covered by that exclusion. Private mode is explicit; actual Windows cookies, cache cleanup, Arabic input, printing and window close/reopen require Windows testing. Missing WebView2/.NET or renderer startup failures produce a sanitized console message; never log page content, credentials or raw exceptions. No app credentials, database URL or TLS private key belongs in a client profile or binary.

Windows build tools are separate from backend dependencies. In a clean Windows CPython 3.14 x64 build venv, install the two hash-pinned requirement files as documented, then run:

```powershell
.\desktop\packaging\Build-Windows.ps1 -BuildId 8a-first
```

The script derives the repository root, builds React, creates the PyInstaller onedir client and stages doctor-only source/assets. It refuses an existing output ID. It performs no deployment, service install, database initialization or migration. Transfer the whole `client/ClinicClient` folder to clients, never just the EXE. Copy `doctor-host` only to the doctor's test PC. Keep runtime credentials and key material outside these outputs.

LAN/trust/firewall/service templates remain [review templates](packaging/README.md). Full Windows installers, signing, managed service setup and two-PC acceptance are future work, not verified by Ubuntu checks.
