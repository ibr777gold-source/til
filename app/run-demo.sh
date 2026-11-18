#!/usr/bin/env bash
# Local-only demo launcher. Starts and stops only the two processes it creates.
set -Eeuo pipefail
app_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root_dir="$(dirname -- "$app_dir")"
backend_dir="$app_dir/backend"
frontend_dir="$app_dir/frontend"
python="$root_dir/.venv/bin/python"
api_port="${TIL_API_PORT:-8000}"
web_port="${TIL_WEB_PORT:-5173}"
api_pid=''
web_pid=''
cleanup() {
  trap - EXIT INT TERM
  for pid in "$web_pid" "$api_pid"; do
    if [[ -n "$pid" ]]; then kill "$pid" 2>/dev/null || true; fi
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
if [[ ! -x "$python" ]] || [[ ! -f "$frontend_dir/node_modules/vite/bin/vite.js" ]]; then
  printf '%s\n' 'Dependencies are missing. Follow the setup steps in README.md first.' >&2
  exit 1
fi
if ! command -v node >/dev/null; then printf '%s\n' 'Node.js is required.' >&2; exit 1; fi
"$python" - "$api_port" "$web_port" <<'PY'
import socket,sys
ports=[]
for value in sys.argv[1:]:
    try: port=int(value)
    except ValueError: raise SystemExit(f'Invalid port: {value}')
    if not 1 <= port <= 65535: raise SystemExit(f'Invalid port: {value}')
    ports.append(port)
if len(set(ports)) != len(ports): raise SystemExit('API and web ports must be different.')
for port in ports:
    with socket.socket() as sock:
        try: sock.bind(('127.0.0.1',port))
        except OSError: raise SystemExit(f'Port {port} is unavailable. Set TIL_API_PORT or TIL_WEB_PORT to an unused port.')
PY
export WEB_ORIGIN="http://127.0.0.1:$web_port"
export ENABLE_DEMO_CONTENT="${ENABLE_DEMO_CONTENT:-true}"
export TIL_API_TARGET="http://127.0.0.1:$api_port"
printf '%s\n' 'Checking database migrations...'
(cd "$backend_dir" && "$root_dir/.venv/bin/alembic" upgrade head)
(cd "$backend_dir" && exec "$python" -m uvicorn app.main:app --host 127.0.0.1 --port "$api_port") &
api_pid=$!
# Confirm the API is responding before opening the frontend.
if ! "$python" - "$api_port" <<'PY'
import sys,time,urllib.request
url=f'http://127.0.0.1:{sys.argv[1]}/api/ready'
for _ in range(50):
    try:
        with urllib.request.urlopen(url,timeout=1) as response:
            if response.status == 200: break
    except Exception: time.sleep(.1)
else: raise SystemExit('Backend did not become ready. Check database settings and the logs above.')
PY
then exit 1; fi
(cd "$frontend_dir" && exec node node_modules/vite/bin/vite.js --host 127.0.0.1 --port "$web_port" --strictPort) &
web_pid=$!
printf '\nOpen %s\nPress Ctrl+C to stop this demo.\n\n' "$WEB_ORIGIN"
wait -n "$api_pid" "$web_pid"
