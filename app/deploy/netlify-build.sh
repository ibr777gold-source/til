#!/usr/bin/env bash
set -euo pipefail
python3 app/deploy/wait_for_ci.py
if [[ -z "${TIL_API_ORIGIN:-}" ]]; then
  printf '%s\n' 'Set TIL_API_ORIGIN to the public HTTPS origin of the FastAPI backend.' >&2
  exit 1
fi
api_origin="$(node - "$TIL_API_ORIGIN" <<'NODE'
try {
 const input=process.argv[2], u=new URL(input);
 if(u.protocol!=='https:' || u.username || u.password || u.pathname!=='/' || u.search || u.hash || /[\x00-\x20\x7f]/.test(input)) throw Error();
 process.stdout.write(u.origin);
} catch { console.error('TIL_API_ORIGIN must be an HTTPS origin with no path or credentials.'); process.exit(1); }
NODE
)"
npm ci --prefix app/frontend
npm run build --prefix app/frontend
printf '/api/* %s/api/:splat 200\n/* /index.html 200\n' "$api_origin" > app/frontend/dist/_redirects
