# Milestone 8A — Windows desktop first-build preparation

Updated 2026-10-28. Preparation only, on Ubuntu. **Windows EXE build: NOT TESTED. GUI launch: NOT TESTED.** No Windows host or PowerShell runtime is available in this session. No installer, service installation, trust-store change, database setup, cloud operation, push or deployment was performed.

## Readiness assessment and package boundaries

Existing work: `/app/` React production serving and SPA history fallback in FastAPI; HTTPS-only pywebview launcher; LAN plan validator; PostgreSQL loopback/HBA, firewall, certificate and WinSW-style service templates. Previously verified Ubuntu workflows are in [local release status](LOCAL_RELEASE_STATUS.md). There was no Windows build script/spec or pinned desktop build environment.

8A adds a Windows-only PyInstaller **onedir console test executable**, pinned/hash-checked desktop dependencies, separate origin profiles, and allowlisted doctor-host staging. The console is intentional for first-build diagnostics. Copy the entire `ClinicClient` directory, including `_internal`; the EXE alone is insufficient. No Windows installer is selected or built in this milestone; final installer/service-wrapper selection remains follow-up work.

| Artifact/responsibility | Doctor PC | Reception PC |
|---|---|---|
| `client/ClinicClient/` | Same client binary | Same client binary |
| Client profile | `doctor-client.example.toml` | `reception-client.example.toml` |
| HTTPS origin | Canonical doctor-host origin | Same canonical doctor-host origin |
| React assets | `doctor-host/frontend/dist/`, served by FastAPI | Downloaded over LAN from doctor; no Vite |
| FastAPI/Python runtime | Doctor only; source payload under `doctor-host/backend/` | None |
| PostgreSQL and credentials | Doctor only, loopback; separate owner/migration and application roles | None |
| Service management | Existing review templates; install/test later | No API or DB service |

Profiles specify only `server_url`, never roles, passwords or DB configuration. API login determines doctor/receptionist permissions independently. The client starts no backend, database, migration or local HTTP server. The launcher explicitly requests `edgechromium`, private mode, no devtools/remote debugging, no certificate bypass and no Python application bridge. The pinned upstream WinForms code can still select MSHTML if WebView2 is missing; the frozen-client spec excludes `webview.platforms.mshtml` so that path must fail rather than render. Missing-runtime failure still requires a native Windows test. Source-mode runs are not protected by that packaging exclusion. Session and CSRF handling remain in the existing same-origin UI/API. Private mode is requested, but Windows cookie/cache cleanup and disk behavior still require measurement.

## Exact Windows build route

Use a **Windows 11 x64 test VM/PC**, standard user, short local checkout path such as `C:\src\Clinc-final` (not a network/OneDrive checkout). Install from official sources, verifying signatures: GIL-enabled CPython **3.14 x64** (record exact patch; Ubuntu baseline is 3.14.4), Node **22.22.x x64** with npm, Git, .NET Framework **4.8** and the x64 **WebView2 Evergreen Runtime**. Pythonnet 3.2.1 metadata includes Python 3.14. This is dependency metadata evidence, not proof that this pywebview combination launches on Windows.

For an offline test machine, transfer the signed Microsoft WebView2 **standalone offline installer**, not its network bootstrapper; install it before disconnecting WAN. Keep its version and installer hash in the test evidence. Windows 11 commonly has WebView2, but Edge browser presence alone does not prove the runtime is installed. Initial dependency downloads require a connected build machine or a vetted package cache; ordinary client use must not require Internet access. Do not install Qt, CEF or unrelated backend packages in the desktop build environment.

To transfer this local work without pushing, after the focused commit run on Ubuntu from the repository root:

```bash
git rev-parse HEAD
git archive --format=zip --output=/tmp/clinc-8a-source.zip HEAD
sha256sum /tmp/clinc-8a-source.zip
```

Transfer that tracked-source archive over approved local media and verify its hash on Windows with `Get-FileHash -Algorithm SHA256`. Extract to `C:\src\Clinc-final`; do not copy the working directory, `.env`, local PostgreSQL files or backups. Record the source commit separately with the build evidence. These transfer commands are instructions, not an upload performed by this task.

In Windows PowerShell 5.1 or newer, from the checkout/extracted source:

```powershell
Set-Location C:\src\Clinc-final
py -3.14 -m venv .build-venv
.\.build-venv\Scripts\python.exe -m pip install --require-hashes -r desktop\packaging\requirements-build-tools.txt
.\.build-venv\Scripts\python.exe -m pip install --require-hashes --no-build-isolation -r desktop\packaging\requirements-windows.txt
.\.build-venv\Scripts\python.exe -m pip check
.\desktop\packaging\Build-Windows.ps1 -BuildId 8a-first
```

Use an approved local script-execution policy; do not disable machine-wide script controls. Build tools are installed first because `proxy-tools` is published as a source archive. `--no-build-isolation` uses the pinned setuptools/wheel rather than downloading unpinned build tooling. Hashes come from exact public PyPI release metadata. Package installation, native hook collection and resulting EXE remain **NOT TESTED on Windows**; if a pin is incompatible, capture the error and review it rather than relaxing hashes or silently upgrading dependencies.

`Build-Windows.ps1` derives the root from its own path, checks Windows/CPython 3.14 x64 and pinned dependencies, runs `npm ci` and the current React build with demo mode false, runs the committed spec, stages the host payload and validates the packaged client's configuration. Every native command is checked for a nonzero exit. An existing BuildId is refused; choose a new ID after a failed build. No existing output or DB is reset. Frontend `node_modules`/`dist` are generated build outputs.

Output layout:

```text
artifacts/windows/8a-first/
  client/ClinicClient/ClinicClient.exe
  client/ClinicClient/_internal/...
  profiles/doctor-client.example.toml
  profiles/reception-client.example.toml
  doctor-host/backend/{app,migrations,alembic.ini,requirements.txt}
  doctor-host/frontend/dist/...
  SHA256SUMS.json
  BUILD-ENVIRONMENT.json
  build.log
  work/                         # build diagnostics only, do not distribute
```

The host stage copies only application/migration Python sources, the exact requirements/Alembic files and approved built asset formats. It excludes `.env`, virtualenvs, private keys, backups, JSON records, caches, source maps and local databases; symlinked inputs fail closed. Client dependencies are collected by PyInstaller/pywebview hooks, not by copying the checkout. `SHA256SUMS.json` covers staged host, profiles and client files; `BUILD-ENVIRONMENT.json` records package names/versions without installation URLs. These checksums detect changes against a trusted manifest, **not publisher authenticity**; binaries are unsigned test artifacts. Preserve build logs, PyInstaller warnings and inventory for review. Bit-for-bit reproducibility and third-party license inventory/signing remain release work.

## Safe doctor-host test environment — operator steps on Windows only

Use **synthetic records only** and a fresh dedicated test PostgreSQL database. These commands are proposed Windows steps, **NOT EXECUTED** here. They never drop/reset a database. If any role/database already exists, stop; do not substitute an existing clinic database or add DROP commands. PostgreSQL 18 must already be installed and listening exclusively on loopback; the existing [LAN plan](../desktop/packaging/README.md) explains the effective listener/HBA checks. No PostgreSQL port is opened to LAN.

1. In an operator console, open psql interactively (adjust the install path if needed):

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -h 127.0.0.1 -U postgres -d postgres -W -v ON_ERROR_STOP=1
```

In psql, create **new** named test roles and database. `\password` prompts invisibly; choose distinct strong passwords. The owner credential is for deliberate migration/bootstrap only, never the service or receptionist.

```sql
CREATE ROLE clinic_8a_owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
\password clinic_8a_owner
CREATE ROLE clinic_8a_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
\password clinic_8a_app
CREATE DATABASE clinic_8a_test OWNER clinic_8a_owner;
REVOKE ALL ON DATABASE clinic_8a_test FROM PUBLIC;
GRANT CONNECT ON DATABASE clinic_8a_test TO clinic_8a_owner, clinic_8a_app;
\q
```

2. On doctor test PC only, prepare the staged backend runtime and deliberate migration. Keep all secrets in this private terminal's process environment, never an EXE, profile, command argument or committed file. Do not use shell transcripts or share environment dumps. URL-encode the prompted password without printing it:

```powershell
Set-Location C:\src\Clinc-final\artifacts\windows\8a-first\doctor-host\backend
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:CLINIC_ENV = 'production'
$env:CLINIC_DEPLOYMENT = 'clinic_lan'
$env:CLINIC_DEMO_PUBLIC_ENABLED = 'false'
$env:CLINIC_PUBLIC_ORIGIN = 'https://localhost:8443'
$secret = Read-Host 'New test owner DB password' -AsSecureString
$encoded = [uri]::EscapeDataString(([System.Net.NetworkCredential]::new('', $secret)).Password)
$env:CLINIC_DATABASE_URL = 'postgresql+psycopg://clinic_8a_owner:' + $encoded + '@127.0.0.1:5432/clinic_8a_test'
$env:CLINIC_MIGRATION_DATABASE_URL = $env:CLINIC_DATABASE_URL
Remove-Variable secret, encoded
```

Confirm the selected new test DB, then migrate **explicitly once**. No startup command in this milestone migrates anything:

```powershell
.\.venv\Scripts\python.exe -c "import os; from sqlalchemy.engine import make_url; from app.core.db import build_engine; from sqlalchemy import text; u=make_url(os.environ['CLINIC_DATABASE_URL']); assert u.host=='127.0.0.1' and u.database=='clinic_8a_test' and u.username=='clinic_8a_owner'; e=build_engine(u.render_as_string(hide_password=False)); c=e.connect(); assert c.scalar(text('SELECT current_database()'))=='clinic_8a_test'; assert not c.scalar(text('SELECT count(*) FROM information_schema.tables WHERE table_schema=current_schema()')); c.close(); e.dispose(); print('PASS: empty local test target')"
# STOP if the validation above exits nonzero; do not continue on failure.
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\alembic.exe current
.\.venv\Scripts\python.exe -m app.bootstrap --username synthetic.doctor
```

The doctor's application password is prompted by the existing one-time local CLI. Create the synthetic receptionist through the existing pure provisioning function in an **interactive Python console**; it does not invoke the Render-only CLI or connect to any cloud resource:

```powershell
.\.venv\Scripts\python.exe
```

```python
import getpass, os
from sqlalchemy.engine import make_url
from app.core.db import build_engine, build_session_factory
from app.demo_provision import provision_receptionist
url = os.environ['CLINIC_DATABASE_URL']
assert make_url(url).database == 'clinic_8a_test' and make_url(url).host == '127.0.0.1'
password = getpass.getpass('New synthetic receptionist password (15-128 characters): ')
assert password == getpass.getpass('Confirm: ')
engine = build_engine(url)
with build_session_factory(engine)() as db:
    account = provision_receptionist(db, 'synthetic.reception', password)

del password, url, account
engine.dispose()
exit()
```

This helper refuses an existing receptionist and writes an audit event. Its historical audit name is `demo_receptionist_created`; this is a synthetic test account, not clinic account-administration UI. Do not call it against existing clinic records.

3. Grant the runtime role only the existing application objects. Reopen psql on the **test** DB as its owner using `-W`:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -h 127.0.0.1 -U clinic_8a_owner -d clinic_8a_test -W -v ON_ERROR_STOP=1
```

```sql
SELECT current_database(), current_user;
-- Confirm clinic_8a_test / clinic_8a_owner before applying the grants below.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO clinic_8a_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO clinic_8a_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO clinic_8a_app;
REVOKE ALL ON auth_bootstrap FROM clinic_8a_app;
REVOKE INSERT, UPDATE, DELETE ON users, alembic_version FROM clinic_8a_app;
GRANT UPDATE (password_hash) ON users TO clinic_8a_app;
\q
```

These are test-environment grants over a new schema, not a general clinic security installer. No DB/schema ownership, CREATE, superuser, role administration or migration rights are granted to the app. API role boundaries still separate the two named accounts. Review maintenance/audit retention privileges before real deployment.

Replace the process DB URL with the runtime role and remove the migration URL before running FastAPI:

```powershell
$secret = Read-Host 'New test application DB password' -AsSecureString
$encoded = [uri]::EscapeDataString(([System.Net.NetworkCredential]::new('', $secret)).Password)
$env:CLINIC_DATABASE_URL = 'postgresql+psycopg://clinic_8a_app:' + $encoded + '@127.0.0.1:5432/clinic_8a_test'
Remove-Variable secret, encoded
Remove-Item Env:CLINIC_MIGRATION_DATABASE_URL
```

## Trusted TLS and starting the test host

For the **first single-machine smoke test**, use `https://localhost:8443` with a localhost SAN certificate trusted by the test Windows user. Use a test-only CA in a protected folder outside the checkout, keep its key offline when not signing, and install only the public root after checking its fingerprint. Never bypass certificate validation. Existing [certificate instructions](../desktop/packaging/README.md) apply; do not copy Ubuntu temporary test certificates or real keys into the build.

With an operator-approved Windows OpenSSL installation, an example test-only provisioning sequence in an ACL-restricted `C:\Clinic8ATest\tls` directory is:

```powershell
$ErrorActionPreference = 'Stop'
# Refuse an existing directory; choose another fresh test directory if needed.
New-Item -ItemType Directory -Path C:\Clinic8ATest\tls -ErrorAction Stop
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
icacls C:\Clinic8ATest\tls /inheritance:r
if ($LASTEXITCODE -ne 0) { throw 'TLS ACL setup failed' }
icacls C:\Clinic8ATest\tls /grant:r "${identity}:(OI)(CI)F" 'SYSTEM:(OI)(CI)F'
if ($LASTEXITCODE -ne 0) { throw 'TLS ACL setup failed' }
Set-Location C:\Clinic8ATest\tls
# CA key is encrypted; OpenSSL prompts. No password command arguments.
openssl req -x509 -newkey rsa:3072 -days 7 -keyout test-ca-key.pem -out test-ca.pem -subj '/CN=Clinic 8A Test CA' -addext 'basicConstraints=critical,CA:TRUE' -addext 'keyUsage=critical,keyCertSign,cRLSign'
# The unattended server key is protected by the folder ACL; only test operator can read it.
openssl req -new -newkey rsa:3072 -noenc -keyout server-key.pem -out server.csr -subj '/CN=localhost'
@'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:localhost
'@ | Set-Content -Encoding ascii server-extensions.cnf
openssl x509 -req -in server.csr -CA test-ca.pem -CAkey test-ca-key.pem -CAcreateserial -out server-chain.pem -days 3 -sha256 -extfile server-extensions.cnf
openssl x509 -in test-ca.pem -outform der -out test-ca.cer
certutil -hashfile test-ca.cer SHA256
# Check this expected test-CA fingerprint before explicitly trusting it.
Import-Certificate -FilePath .\test-ca.cer -CertStoreLocation Cert:\CurrentUser\Root
```

Stop on any OpenSSL error. Never run in a folder containing existing keys. Provision/review the folder's Windows ACL before key generation; do not rely on its name to protect it. Removing the test root afterward is an explicit operator action against that certificate's recorded thumbprint, not a blanket trust-store cleanup. These commands are Windows instructions, **NOT TESTED here**.

Return to the staged backend directory **in the same private process environment configured above** and start the test server in the foreground:

```powershell
Set-Location C:\src\Clinc-final\artifacts\windows\8a-first\doctor-host\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8443 --ssl-certfile C:\Clinic8ATest\tls\server-chain.pem --ssl-keyfile C:\Clinic8ATest\tls\server-key.pem --no-access-log --no-proxy-headers --no-server-header
```

This smoke command is loopback HTTPS, not a Windows service or LAN rollout. It runs the current FastAPI app with packaged React assets; no Vite or Node server is needed. The existing WinSW review template describes the future restricted service account, PostgreSQL dependency and restart policy. Installing/validating that service is **NOT TESTED** and remains outside first-EXE preparation.

## Client launch and acceptance on Windows

In a second standard-user PowerShell window:

```powershell
Set-Location C:\src\Clinc-final
.\desktop\packaging\Test-ClinicHttps.ps1 -Origin https://localhost:8443
$client = '.\artifacts\windows\8a-first\client\ClinicClient\ClinicClient.exe'
& $client --check-config --server-url https://localhost:8443
& $client --server-url https://localhost:8443
```

Login as `synthetic.reception` using the privately chosen password, create a clearly synthetic patient, book a future valid appointment, and logout. Open a second client as `synthetic.doctor`, verify appointment visibility, save/finalize a synthetic visit, inspect billing/receipt and refresh. Reception must have no clinical menu and direct receptionist `/api/visits` requests must return 403. Verify missing CSRF is denied and logout invalidates the server session. Verify back/refresh under `/app/`, Arabic typing, unsaved-note warning, payment totals, receipt printing and no unexpected renderer errors. Close/reopen and check private-mode login behavior and absence of residual clinical storage; session expiry remains enforced by FastAPI, not window lifetime.

For later **two-PC testing**, replace the profile origins with the chosen doctor's canonical LAN hostname matching its SAN; both clients use that exact origin. Copy only `client/ClinicClient/` and the reception profile to reception, then:

```powershell
.\ClinicClient\ClinicClient.exe --config .\reception-client.toml
```

The doctor's corresponding invocation uses `--config .\doctor-client.toml`. The names grant no role. No DB URL, Python backend, migration command, private key or PostgreSQL install belongs on reception. Validate existing firewall/DNS/trust templates before LAN exposure; this milestone does not change them automatically. Test denied DB access from reception, wrong-SAN/untrusted/expired certificates, two independent sessions, network loss/recovery without duplicate writes and WAN disconnected while LAN remains up.

## Diagnostics and evidence to capture

- `artifacts/windows/<BuildId>/build.log`, `work/ClinicClient/warn-ClinicClient.txt`, build environment, source commit and checksums. Review PyInstaller missing-module warnings; don't blindly suppress them.
- Client console reports a sanitized startup failure without exception/page data. Check WebView2/.NET prerequisites and run `--check-config`; no debug browser or TLS bypass flags are supported. Do not turn on pywebview debug logging with clinical records.
- `/api/health` is process liveness; `/api/health/ready` must be ready. A 503 requires checking PostgreSQL service/listener, runtime grants and migration revision. Diagnose only in the isolated test DB; never log full connection strings, cookies, request bodies or clinical text.
- Uvicorn runs with access logs/proxy trust disabled. Capture sanitized startup errors only. No migration/reseed/repair loop is included.
- For a blank window, verify `/app/login` in a trusted Windows browser and check the staged `doctor-host/frontend/dist/index.html`; backend assets and the EXE are separate artifacts.

## Verification and remaining gates

| Check | Status | Evidence / blocker |
|---|---|---|
| Ubuntu desktop/config tests | PASS | 12 tests, 19 subtests |
| Python lint, profile checks and spec syntax | PASS | Ruff, both HTTPS profiles and existing LAN validator |
| Real host staging / data boundary | PASS | Temporary staged source imports FastAPI and locates built assets; exclusion/symlink tests |
| Declared Windows dependency closure | PASS | All 16 pins satisfy public package metadata for Python 3.14/Windows; no software installed |
| Existing backend regression | PASS | 68 tests on disposable PostgreSQL; 7 existing deprecation warnings |
| React build / Vitest | PASS | TypeScript + Vite; 7 tests |
| Built app without Vite | PASS | Static Playwright: deep links, local assets, Arabic RTL, roles, API/docs isolation |
| Local trusted HTTPS/session probe | PASS | CA/SAN verification, wrong-host/untrusted rejection, Secure cookies, CSRF/logout, forwarded-header rejection |
| Windows dependency installation / PowerShell execution | NOT TESTED | Windows/PowerShell unavailable |
| Windows PyInstaller EXE build | NOT TESTED | Must execute on Windows; Ubuntu is not a cross-compiler |
| Actual WebView2 GUI / cookies / printing | NOT TESTED | No Windows GUI/runtime |
| Windows test DB grants, TLS/store and host commands above | NOT TESTED | Proposed operator steps only |
| Services, offline Windows/two-PC LAN acceptance | NOT TESTED | Requires Windows machines and operator-approved configuration |

See [8A task report](tasks/8A.md) for executed commands/results. Ubuntu can test URL/profile validation, mocked launcher parameters, staging boundaries, Python/spec syntax, frontend production assets and existing API regressions. It cannot prove Windows hooks, PowerShell execution, WebView2, native DLLs, GUI, trust store, cookies, printing, services or EXE compatibility.

**Next step: 8A-WIN-SMOKE**, explicitly on a Windows 11 x64 test VM: install prerequisites, execute the exact build above, launch against the isolated HTTPS synthetic host and record results before any installer/production milestone. Resolve native packaging failures there without disabling security. No automatic updater, Windows installer, signed release, actual two-PC deployment or clinical readiness is claimed.

Sources consulted for preparation: [PyInstaller platform rules](https://www.pyinstaller.org/en/stable/), [pywebview freezing/hooks guidance](https://pywebview.flowrl.com/guide/freezing.html), [pywebview API/private mode](https://pywebview.flowrl.com/api/), [pythonnet metadata](https://pypi.org/project/pythonnet/3.2.1/), [pinned WinForms renderer selection](https://github.com/r0x0r/pywebview/blob/6.2.1/webview/platforms/winforms.py), [Microsoft WebView2 offline/runtime distribution](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution).
