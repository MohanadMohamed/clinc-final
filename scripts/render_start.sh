#!/bin/sh
set -eu
port="${PORT:-10000}"
case "$port" in
  ''|*[!0-9]*) echo 'PORT must be a TCP port number' >&2; exit 1 ;;
esac
if [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then
  echo 'PORT must be between 1 and 65535' >&2
  exit 1
fi
if [ "${RENDER:-}" != true ] || [ "${CLINIC_ENV:-}" != production ] || [ "${CLINIC_DEPLOYMENT:-}" != render_demo ]; then
  echo 'Explicit Render production demo configuration is required' >&2
  exit 1
fi
exec python -m uvicorn app.main:app \
  --host 0.0.0.0 --port "$port" --no-proxy-headers --no-access-log --workers 1
