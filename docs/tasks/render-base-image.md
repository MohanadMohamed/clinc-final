# Render runtime image vulnerability remediation — 2026-10-27

Scope: final image only. No application feature, authentication/authorization, scanner threshold, deployment or Windows LAN setting changed. The original failing [run 40479848717](https://github.com/MohanadMohamed/clinc-final/actions/runs/40479848717) built `python:3.14-slim-trixie` and failed Trivy with **44 OS HIGH rows** (eight distinct CVEs, repeated across Debian split packages) and **four Python HIGH rows**. Its build, image-file inventory, closed-gate startup, pip-audit and npm audit steps passed.

Changed files: `Dockerfile.render`, `docs/STATUS.md`, `docs/LIVE_DEMO_DEPLOYMENT.md`, and this report. Pre-existing untracked README drafts and diagram images were left untouched.

## Findings and disposition

The failing Trivy table had **no fixed Trixie version** for these OS rows. Debian's tracker marks the current Trixie source packages vulnerable; the `util-linux` issues are `no-dsa`, and the Perl issue is postponed. These statuses are not claims of safety. All OS rows disappeared after moving the final image to official `python:3.14-alpine3.23`; no Debian unstable packages were mixed into Trixie.

| CVE | Affected packages in old image; installed version | Trivy status / fixed version | Vulnerable behavior and old-container reachability |
| --- | --- | --- | --- |
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) | `util-linux` family: `bsdutils`, `libblkid1`, `liblastlog2-2`, `libmount1`, `libsmartcols1`, `libuuid1`, `login`, `mount`, `util-linux`; `2.41.5-0+deb13u1` except `bsdutils`/`login` with Debian epoch/version prefixes | affected / none for Trixie | Privileged mount helper/post-hook path. No app path invokes mounts; the old container ran the API as `clinic`, without a user-authorized fstab mount flow. |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) | Same `util-linux` family/version | affected / none for Trixie | Privileged `nsenter --join-cgroup` path. The app never invokes `nsenter`; requires a privileged operator and attacker-controlled target. |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) | Same `util-linux` family/version | affected / none for Trixie | `X-mount.subdir` plus an authorized fstab entry and intermediate symlinks; absent from the API runtime path. |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) | Same `util-linux` family/version | affected / none for Trixie | Restricted bind mount source race with privileged mount and writable source path; absent from the API runtime path. |
| [CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369) | `libacl1` `2.3.2-2+b1` | affected / none for Trixie | Local symlink substitution during privileged pathname-based ACL calls. The app does not perform ACL administration. |
| [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720) | `libncursesw6`, `libtinfo6`, `ncurses-base`, `ncurses-bin` `6.5+20250216-2` | affected / none for Trixie | Crafted input to the `infocmp` command. The API never runs `infocmp`. |
| [CVE-2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742) | `libsystemd0`, `libudev1` `257.13-1~deb13u1` | affected / none for Trixie | Requires `systemd-homed` managing a local login; the old container did not run `systemd-homed`. |
| [CVE-2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538) | `perl-base` `5.40.1-6+deb13u1` | fix_deferred / none for Trixie | Crafted tar header consumed by Perl `Archive::Tar`; the API does not invoke Perl or parse tar uploads. |

The four Python findings in the old image were `msgpack` [GHSA-6v7p-g79w-8964](https://github.com/advisories/GHSA-6v7p-g79w-8964) `1.1.2` (fixed `1.2.1`), `setuptools` [CVE-2025-47273](https://github.com/pypa/setuptools/security/advisories/GHSA-5rjg-fvgr-3xxf) `70.3.0` (fixed `78.1.1`), and `urllib3` [CVE-2026-97687](https://github.com/advisories/ghsa-8988-9cw3-xx77) / [CVE-2026-97689](https://github.com/advisories/ghsa-vxq7-64xx-v4gw) `2.7.0` (fixed `2.8.0`), all Trivy status `fixed`. These were not direct entries in `backend/requirements.txt`; the scanner grouped them under Python tooling. The image now uninstalls `pip` and `setuptools` after installing pinned, binary-only runtime dependencies. The new scan finds zero HIGH/CRITICAL Python findings.

Bookworm was considered but Debian also marks these `util-linux` issues vulnerable there, and its older util-linux package lacks some Trixie security fixes. A blanket Trivy exception or unstable Debian package mixing would preserve the affected code. Official Python 3.14 Alpine is a narrower runtime: all 36 pinned Python packages had CPython 3.14 musllinux wheels in the local download check, including `psycopg-binary` and `pydantic_core`. The final image retains CA certificates, FastAPI and Alembic files, the production frontend, and a non-root `clinic` account.

## Verification

| Result | Exact command / evidence |
| --- | --- |
| PASS | `backend/.venv/bin/python -m pip download --only-binary=:all: --platform musllinux_1_2_x86_64 --platform musllinux_1_1_x86_64 --python-version 3.14 --implementation cp --abi cp314 --no-deps --dest /tmp/clinic-musl-wheels -r backend/requirements.txt --quiet` — exit 0, 36 wheels. No package was installed into the project. |
| PASS | `git diff --check` — exit 0 before the Dockerfile commit. |
| PASS | The **unchanged** [workflow run 40494296645](https://github.com/MohanadMohamed/clinc-final/actions/runs/40494296645) on commit `8bd2c0d` — exit 0. Docker build, pip-audit, npm audit, private-file inventory, production startup/health/closed gate, and Trivy HIGH/CRITICAL OS+library scan all passed. Trivy identified Alpine 3.23.7, 30 OS packages, **0 OS vulnerabilities** at the configured severities and **0 Python findings**. |
| NOT TESTED locally | `docker build --pull --file Dockerfile.render --tag clinic-render-demo:verify .` — Docker/Podman/Buildah are not installed here. CI built the exact Dockerfile instead. |
| NOT TESTED | Live Render TLS/proxy behavior, private database networking, migrations against a separate Render database, and restricted staging flows. No Render deployment occurred. |

The new scan is a time-bound HIGH/CRITICAL scan, not proof that lower-severity or future advisories are absent. There are **no unresolved HIGH findings in the scanned final image** and no exception is proposed. Keep the public demo gate closed; restricted staging is reasonable only after the other deployment-guide controls are verified on Render. Re-run the existing workflow on each image/dependency update. No public deploy or merge was performed. The next planned clinic task remains **8A**, outside this focused remediation.
