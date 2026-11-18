"""Exercise demo practice and feedback against the dedicated PostgreSQL test DB."""
import os
from uuid import uuid4
from sqlalchemy.engine import make_url

url=make_url(os.environ['DATABASE_URL'])
if url.get_backend_name()!='postgresql' or url.database!='til_test':
    raise SystemExit('Use a dedicated PostgreSQL database named til_test.')
if os.getenv('ENABLE_DEMO_CONTENT','').lower()!='true':
    raise SystemExit('Set ENABLE_DEMO_CONTENT=true for this test.')

from fastapi.testclient import TestClient
from app.main import app,engine,Feedback,course_demo_exercises,module_demo_exercises
from sqlalchemy.orm import Session

with TestClient(app) as learner,TestClient(app) as guest:
    registered=learner.post('/api/auth/register',json={'email':f'practice-{uuid4().hex}@example.com','password':'longpassword'})
    assert registered.status_code==200,registered.text
    module=learner.get('/api/demo-module/uz-ru/5')
    assert module.status_code==200 and len(module.json()['exercises'])>=3,module.text
    with Session(engine) as session: module_answers={e['id']:e['answers'][0] for e in module_demo_exercises('uz-ru',5,session)[1]}
    result=learner.post('/api/demo-module/uz-ru/5',json={'content_version':module.json()['content_version'],'responses':module_answers})
    assert result.status_code==200 and result.json()['score']==100,result.text
    with Session(engine) as session: answers={e['id']:e['answers'][0] for e in course_demo_exercises('uz-ru',session)}
    version=learner.get('/api/demo-course/uz-ru').json()['content_version']
    result=learner.post('/api/demo-course/uz-ru',json={'content_version':version,'responses':answers})
    assert result.status_code==200 and result.json()['score']==100,result.text
    overview=learner.get('/api/progress/overview').json()
    course=next(item for item in overview['courses'] if item['course']=='uz-ru')
    assert course['course_practice']['score']==100 and course['modules'][4]['practice']['score']==100
    assert guest.get('/api/progress/overview').status_code==401
    report=guest.post('/api/preview/uz-ru/feedback',json={'lesson_id':'uz-ru-greetings','category':'content','message':'PostgreSQL smoke test feedback','clarity_rating':5})
    assert report.status_code==200,report.text
    with Session(engine) as session:
        saved=session.get(Feedback,report.json()['id']);assert saved.user_id is None and saved.clarity_rating==5
    print('PostgreSQL sample module and course practice, progress isolation, and guest feedback ratings: passed')
