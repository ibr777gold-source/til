"""Restore an archive into a disposable, socket-only PostgreSQL cluster."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile


def run(command, **kwargs):
    return subprocess.run([str(part) for part in command], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path, help='PostgreSQL custom-format archive to verify')
    args = parser.parse_args()
    archive = args.archive.resolve(strict=True)
    if not archive.is_file():
        raise SystemExit('Archive must be a regular file.')
    if os.geteuid() == 0:
        raise SystemExit('Run as an unprivileged user, not root.')
    if not shutil.which('pg_config'):
        raise SystemExit('PostgreSQL server and client tools are required.')
    bindir = Path(run(['pg_config', '--bindir'], text=True).stdout.strip())
    names = ('initdb', 'pg_ctl', 'createdb', 'pg_restore', 'psql')
    if not all((bindir / name).is_file() for name in names):
        raise SystemExit('PostgreSQL server and client tools are required.')

    with tempfile.TemporaryDirectory(prefix='til-restore-') as temporary:
        root = Path(temporary)
        data = root / 'cluster'
        started = False
        env = {key: value for key, value in os.environ.items() if not key.startswith('PG')}
        env.update(PGHOST=str(root), PGPORT='55498', PGUSER='til_restore')
        try:
            run([bindir/'initdb', '-D', data, '-U', 'til_restore', '--auth=trust', '--no-locale', '--encoding=UTF8'], env=env)
            run([bindir/'pg_ctl', '-D', data, '-l', root/'postgres.log', '-o',
                 f"-c listen_addresses='' -k {shlex.quote(str(root))} -p 55498", '-w', 'start'], env=env)
            started = True
            run([bindir/'createdb', 'til_restore'], env=env)
            run([bindir/'pg_restore', '--exit-on-error', '--no-owner', '--no-privileges',
                 '--dbname=til_restore', archive], env=env)
            result = run([bindir/'psql', '-X', '-v', 'ON_ERROR_STOP=1', '-A', '-t', '-d', 'til_restore',
                          '-c', "SELECT version_num FROM alembic_version ORDER BY version_num"], env=env, text=True)
            versions = result.stdout.strip()
            if not versions:
                raise RuntimeError('Restored database has no migration version.')
            print('Archive restored successfully to an isolated temporary database.')
            print('Migration version(s): ' + versions.replace('\n', ', '))
            print('This does not validate every record or any uploaded media.')
        finally:
            if started:
                run([bindir/'pg_ctl', '-D', data, '-m', 'fast', '-w', 'stop'], env=env)


if __name__ == '__main__':
    main()
