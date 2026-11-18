"""Write and inspect a local PostgreSQL custom-format archive without overwriting files."""
import argparse
import os
from pathlib import Path
import subprocess
from sqlalchemy.engine import make_url


def main():
    parser=argparse.ArgumentParser(description='Create a private PostgreSQL archive. Does not back up media files.')
    parser.add_argument('output',type=Path,help='New archive path; an existing file is never overwritten')
    args=parser.parse_args()
    database_url=os.getenv('DATABASE_URL','postgresql+psycopg://til:til_dev_password@localhost:5432/til')
    try: url=make_url(database_url)
    except Exception: raise SystemExit('Invalid DATABASE_URL.') from None
    if url.get_backend_name()!='postgresql' or not url.database:
        raise SystemExit('DATABASE_URL must name a PostgreSQL database.')
    if set(url.query)-{'sslmode'}: raise SystemExit('Unsupported DATABASE_URL options for backup; configure your PostgreSQL client explicitly.')
    environment=os.environ.copy()
    if url.password is not None: environment['PGPASSWORD']=url.password
    if 'sslmode' in url.query: environment['PGSSLMODE']=url.query['sslmode']
    command=['pg_dump','--format=custom','--no-owner','--no-privileges',f'--dbname={url.database}']
    if url.host: command.append(f'--host={url.host}')
    if url.port: command.append(f'--port={url.port}')
    if url.username: command.append(f'--username={url.username}')
    try: descriptor=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError: raise SystemExit('Output already exists; choose a new path.') from None
    except OSError: raise SystemExit('Could not create the output file.') from None
    try:
        with os.fdopen(descriptor,'wb') as output:
            result=subprocess.run(command,stdout=output,stderr=subprocess.PIPE,env=environment,check=False)
        if result.returncode!=0: raise RuntimeError('Database backup failed; check database connectivity and client tools.')
        verification=subprocess.run(['pg_restore','--list',str(args.output)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=False)
        if verification.returncode!=0: raise RuntimeError('Backup archive could not be read by pg_restore.')
    except (OSError,RuntimeError) as exc:
        try: args.output.unlink()
        except OSError: pass
        raise SystemExit(str(exc) if isinstance(exc,RuntimeError) else 'PostgreSQL client tools are unavailable.') from None
    print(f'Created and inspected archive: {args.output}')
    print('Uploaded media files are not included; back them up separately.')

if __name__=='__main__': main()
