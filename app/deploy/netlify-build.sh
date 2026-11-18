#!/usr/bin/env bash
set -euo pipefail
if [[ -z "${TIL_API_ORIGIN:-}" ]]; then
  printf '%s\n' 'Set TIL_API_ORIGIN to the public HTTPS origin of the FastAPI backend.' >&2
  exit 1
fi
node - "$TIL_API_ORIGIN" <<'NODE'
try {
 const u=new URL(process.argv[2]);
 if(u.protocol!=='https:' || u.username || u.password || u.pathname!=='/' || u.search || u.hash) throw Error();
} catch { console.error('TIL_API_ORIGIN must be an HTTPS origin with no path or credentials.'); process.exit(1); }
NODE
npm ci --prefix app/frontend
npm run build --prefix app/frontend
printf '/api/* %s/api/:splat 200\n/* /index.html 200\n' "${TIL_API_ORIGIN%/}" > app/frontend/dist/_redirects
