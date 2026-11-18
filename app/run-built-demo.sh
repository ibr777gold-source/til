#!/usr/bin/env bash
# Local single-origin demo; serves the already-built frontend from FastAPI.
set -Eeuo pipefail
app_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root_dir="$(dirname -- "$app_dir")"
python="$root_dir/.venv/bin/python"
port="${TIL_DEMO_PORT:-8000}"
if [[ ! -x "$python" ]] || [[ ! -f "$app_dir/frontend/dist/index.html" ]]; then
  printf '%s\n' 'Backend dependencies or frontend build missing. Follow the setup steps in README.md.' >&2
  exit 1
fi
"$python" - "$port" <<'PY'
import socket,sys
try: port=int(sys.argv[1])
except ValueError: raise SystemExit('TIL_DEMO_PORT must be a valid port.')
if not 1 <= port <= 65535: raise SystemExit('TIL_DEMO_PORT must be a valid port.')
with socket.socket() as sock:
    try: sock.bind(('127.0.0.1',port))
    except OSError: raise SystemExit(f'Port {port} is unavailable. Set TIL_DEMO_PORT to an unused port.')
PY
export WEB_ORIGIN="http://127.0.0.1:$port"
export SERVE_BUILT_FRONTEND=true
export ENABLE_DEMO_CONTENT="${ENABLE_DEMO_CONTENT:-true}"
printf '%s\n' 'Checking database migrations...'
(cd "$app_dir/backend" && "$root_dir/.venv/bin/alembic" upgrade head)
printf '\nOpen %s\nPress Ctrl+C to stop this demo.\n\n' "$WEB_ORIGIN"
cd "$app_dir/backend"
exec "$python" -m uvicorn app.main:app --host 127.0.0.1 --port "$port"
