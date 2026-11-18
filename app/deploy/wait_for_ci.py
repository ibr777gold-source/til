"""Fail closed unless the exact production commit passes the GitHub workflow."""
import json
import os
import re
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

REPO = 'ibr777gold-source/til'
WORKFLOW = 'ci.yml'
TIMEOUT_SECONDS = 720
POLL_SECONDS = 20


def main():
    if os.environ.get('CONTEXT') != 'production':
        print('Not a production deploy; CI deployment gate is not applied.')
        return
    sha = os.environ.get('COMMIT_REF', '')
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise RuntimeError('Missing or invalid production commit SHA')
    params = urlencode({'head_sha': sha, 'event': 'push', 'per_page': 20})
    url = f'https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW}/runs?{params}'
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'Til-production-gate'}
    token = os.environ.get('CI_STATUS_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer ' + token
    deadline = time.monotonic() + TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            with urlopen(Request(url, headers=headers), timeout=15) as response:
                data = json.load(response)
            runs = [run for run in data.get('workflow_runs', []) if run.get('head_sha') == sha and run.get('head_branch') == 'main' and run.get('event') == 'push']
            if runs:
                run = runs[0]
                print('CI:', run.get('status'), run.get('conclusion') or '', flush=True)
                if run.get('status') == 'completed':
                    if run.get('conclusion') != 'success':
                        raise RuntimeError('CI did not pass for this commit')
                    remote = subprocess.check_output(['git', 'ls-remote', 'https://github.com/' + REPO + '.git', 'refs/heads/main'], text=True, timeout=20).split()
                    if not remote or remote[0] != sha:
                        raise RuntimeError('A newer commit is on main; refusing to publish an older build')
                    print('Exact current main commit passed CI.')
                    return
            else:
                print('Waiting for the CI run to start.', flush=True)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            print(f'Waiting for GitHub CI status ({type(exc).__name__}).', flush=True)
        time.sleep(POLL_SECONDS)
    raise RuntimeError('Timed out waiting for CI; production was not published')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f'Deployment gate: {exc}', file=sys.stderr)
        sys.exit(1)
