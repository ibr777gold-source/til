"""Run against an explicitly dedicated migrated PostgreSQL database, not production."""
import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from sqlalchemy.engine import make_url
from fastapi.testclient import TestClient
from app.main import app

url=make_url(os.environ['DATABASE_URL'])
if url.get_backend_name()!='postgresql' or url.database!='til_test':
    raise SystemExit('Use a dedicated PostgreSQL database named til_test.')

with TestClient(app) as client:
    email=f'smoke-{uuid4().hex}@example.com'
    register=client.post('/api/auth/register',json={'email':email,'password':'longpassword'})
    assert register.status_code==200, register.text
    token=client.cookies.get('til_session')

    def post(path,payload=None):
        with TestClient(app) as other:
            other.cookies.set('til_session',token)
            return other.post(path,json=payload)

    with ThreadPoolExecutor(max_workers=4) as pool:
        starts=list(pool.map(lambda _:post('/api/lessons/uz-ru-greetings/attempts'),range(4)))
    assert all(r.status_code==200 for r in starts), [r.text for r in starts]
    ids={r.json()['id'] for r in starts}
    assert len(ids)==1, ids
    attempt=ids.pop()
    answers=[('g1','Привет'),('g2','спасибо'),('g3','До свидания')]
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(lambda pair:post(f'/api/attempts/{attempt}/answers',{'exercise_id':pair[0],'response':pair[1]}),answers))
    assert all(r.status_code==200 and r.json()['correct'] for r in results), [r.text for r in results]
    with ThreadPoolExecutor(max_workers=3) as pool:
        completed=list(pool.map(lambda _:post(f'/api/attempts/{attempt}/complete'),range(3)))
    assert all(r.status_code==200 and r.json()['score']==100 for r in completed), [r.text for r in completed]
    progress=client.get('/api/progress').json()
    assert len(progress)==1 and progress[0]['completed'] and progress[0]['best_score']==100, progress
    print('PostgreSQL concurrent start, answers, completion, and persisted progress: passed')
