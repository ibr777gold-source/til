"""Back up til_test and restore it to a private, temporary PostgreSQL cluster.

Never restores to the source database or touches the normal PostgreSQL server.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from sqlalchemy import create_engine,text
from sqlalchemy.engine import URL,make_url

source=make_url(os.environ['DATABASE_URL'])
if source.get_backend_name()!='postgresql' or source.database!='til_test' or source.host not in ('localhost','127.0.0.1'):
    raise SystemExit('Use the dedicated local PostgreSQL database til_test.')
pg_config=shutil.which('pg_config')
if not pg_config: raise SystemExit('PostgreSQL development tools are required.')
bindir=Path(subprocess.check_output([pg_config,'--bindir'],text=True).strip())
initdb=bindir/'initdb';pg_ctl=bindir/'pg_ctl';createdb=bindir/'createdb';pg_restore=bindir/'pg_restore'
if not all(path.is_file() for path in (initdb,pg_ctl,createdb,pg_restore)):
    raise SystemExit('PostgreSQL server and client tools are required.')

def run(command,**kwargs):
    subprocess.run([str(part) for part in command],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,**kwargs)

def snapshot(engine):
    tables=('users','attempts','progress','review_items','feedback','demo_checkpoint_results')
    with engine.connect() as connection:
        # The table names are fixed constants, not input.
        counts={name:connection.scalar(text('SELECT count(*) FROM '+name)) for name in tables}
        versions=tuple(connection.execute(text('SELECT version_num FROM alembic_version ORDER BY version_num')).scalars())
        return counts,versions

with tempfile.TemporaryDirectory(prefix='til-restore-') as temporary:
    root=Path(temporary);data=root/'cluster';archive=root/'backup.dump';log=root/'postgres.log';started=False
    source_engine=create_engine(source)
    target_engine=None
    try:
        before=snapshot(source_engine)
        run([sys.executable,'-m','scripts.backup_database',archive])
        run([initdb,'-D',data,'-U','til_scratch','--auth=trust','--no-locale','--encoding=UTF8'])
        # The socket is inside a 0700 temporary directory; no TCP listener is enabled.
        run([pg_ctl,'-D',data,'-l',log,'-o',f"-c listen_addresses='' -k {root} -p 55499",'-w','start'])
        started=True
        scratch_env={**os.environ,'PGHOST':str(root),'PGPORT':'55499','PGUSER':'til_scratch'}
        scratch_env.pop('PGPASSWORD',None);scratch_env.pop('PGSERVICE',None)
        run([createdb,'til_restore'],env=scratch_env)
        run([pg_restore,'--exit-on-error','--no-owner','--no-privileges','--dbname=til_restore',archive],env=scratch_env)
        target=URL.create('postgresql+psycopg',username='til_scratch',database='til_restore',query={'host':str(root),'port':'55499'})
        target_engine=create_engine(target)
        after=snapshot(target_engine)
        if before!=after: raise RuntimeError('Restored schema version or row counts differ from the source snapshot.')
        print('PostgreSQL backup restored to an isolated temporary cluster; schema version and selected row counts match.')
    finally:
        source_engine.dispose()
        if target_engine: target_engine.dispose()
        if started: run([pg_ctl,'-D',data,'-m','fast','-w','stop'])
