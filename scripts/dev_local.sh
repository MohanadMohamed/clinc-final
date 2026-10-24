#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ! -x "$root/backend/.venv/bin/uvicorn" || ! -d "$root/frontend/node_modules" ]]; then
  echo 'Install backend and frontend dependencies as described in README.md.' >&2
  exit 1
fi
if [[ ! -f "$root/.env" && -z "${CLINIC_DATABASE_URL:-}" ]]; then
  echo 'Set up the untracked .env or CLINIC_DATABASE_URL first; see README.md.' >&2
  exit 1
fi
export CLINIC_ENV=development
export CLINIC_PUBLIC_ORIGIN=http://127.0.0.1:5173
unset CLINIC_TEST_CERT CLINIC_TEST_KEY
(
  cd "$root/backend"
  exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --no-access-log --no-proxy-headers
) &
api_pid=$!
cleanup() {
  kill "$api_pid" "${vite_pid:-}" 2>/dev/null || true
  wait "$api_pid" "${vite_pid:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
(
  cd "$root/frontend"
  exec npm run dev -- --host 127.0.0.1
) &
vite_pid=$!
wait -n "$api_pid" "$vite_pid"
