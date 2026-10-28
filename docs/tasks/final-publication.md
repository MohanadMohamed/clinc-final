# Final development snapshot handoff

Date: 2026-10-28. Scope: user-authorized GitHub publication and project pause, with no new features, database changes, cloud access or deployment.

## Included work

- `35744b9`: local Ubuntu stabilization, actual startup verification, complete synthetic workflows, strengthened restart/persistence evidence and local-running documentation.
- `5ddc17d`: all Milestone 8A preparation: Windows build script/spec, hash-pinned desktop build requirements, separate origin-only client profiles, doctor-host staging, launcher safeguards and tests, exact Windows instructions.
- Earlier completed work/history, including preserved cloud preparation, remains in the snapshot. Render/Neon work is paused; those files are not instructions to deploy now.
- This final handoff changes only README/status/report wording to make the current release limits prominent.

## Fresh lightweight checks

| Status | Command/check | Evidence |
|---|---|---|
| PASS | `git fetch origin --prune` and `git rev-list --left-right --count origin/main...HEAD` | At review: 0 remote-only / 3 local-only commits; safe fast-forward route available |
| PASS | `backend/.venv/bin/python -m pytest desktop/tests -q` | 12 tests, 19 subtests, exit 0 |
| PASS | `backend/.venv/bin/ruff check desktop/launcher.py desktop/packaging/build_support.py desktop/tests` | All checks passed |
| PASS | In `frontend`: `npm test && npm run build` | 7 Vitest tests / 4 files; TypeScript + Vite production build, exit 0 |
| PASS | `bash -n scripts/dev_local.sh` | Shell syntax valid |
| PASS | `git diff --check` and documentation link/conflict-marker review | No whitespace errors or unresolved merge markers; final links checked |
| PASS | Tracked snapshot/reachable-history filename and bounded secret-format review | 471 historical text blobs reviewed before this documentation commit; no sensitive/generated paths, private-key/token patterns or unclassified credentialed DB URLs. Nine credentialed URL occurrences were placeholders/runtime interpolation. Final snapshot checked again before push. |

No `.env`, credentials, private keys, certificates, database records/backups, build outputs, virtualenvs or unrelated untracked files were added. The scan reads Git objects, not local secret files. No standalone secret-scanning tool was installed; this is a bounded source/history inspection, not certification.

Backend PostgreSQL and full browser suites were **not rerun in this publication task** because no application code changed and the task prohibits database operations. The actual previous 68-test backend, static/TLS browser and complete synthetic-workflow evidence remains in [local release status](../LOCAL_RELEASE_STATUS.md), [local stabilization report](local-stabilization.md) and [8A report](8A.md).

## Publication and preservation

Integrate the reviewed snapshot into `main` preserving history, fetch again before publishing, and use an ordinary non-force push. If GitHub branch protection blocks the direct update, publish a branch and prepare a PR instead. The remote branch SHA is verified after publication and reported in the final response; this committed report does not claim a push before it happens.

Unrelated untracked user files excluded from publication and left untouched:

- `README (1).md`
- `clinc-final_README.md`
- `mermaid-diagram (1).png`
- `mermaid-diagram.png`

## Current limits and stop condition

Ubuntu local application verification is recorded; Windows desktop packaging is prepared. Actual Windows EXE build, installer, GUI launch, physical printing and two-PC production deployment remain **NOT TESTED**. Cloud deployment work is paused. This is not an approved application for real patient records or a certified medical release.

Exact future Windows instructions are in [WINDOWS_8A_STATUS](../WINDOWS_8A_STATUS.md). No next milestone is started or scheduled. Work stops after remote publication verification.
