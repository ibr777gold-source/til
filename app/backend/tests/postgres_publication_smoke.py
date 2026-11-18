"""Exercise publication against a dedicated migrated PostgreSQL test database."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from app import main

url=make_url(os.environ['DATABASE_URL'])
if url.get_backend_name()!='postgresql' or url.database!='til_test':
    raise SystemExit('Use a dedicated PostgreSQL database named til_test.')
with TemporaryDirectory() as media_dir:
    main.MEDIA_ROOT=Path(media_dir)
    with TestClient(main.app) as author, TestClient(main.app) as reviewer, TestClient(main.app) as learner:
        def signup(client):
            r=client.post('/api/auth/register',json={'email':f'{uuid4().hex}@example.com','password':'longpassword'})
            assert r.status_code==200,r.text
            return r.json()['id']
        aid=signup(author); rid=signup(reviewer); signup(learner)
        with Session(main.engine) as s:
            s.add_all([main.EditorAccess(user_id=aid),main.EditorAccess(user_id=rid),main.PublisherAccess(user_id=rid)]); s.commit()
        r=author.post('/api/admin/media?attribution=Original',content=b'RIFF'+b'\0'*4+b'WAVEdata'); assert r.status_code==200,r.text
        asset=r.json()['id']
        r=reviewer.post('/api/admin/media/'+asset+'/reviews',json={'decision':'approved','notes':'Test rights review'}); assert r.status_code==200,r.text
        content={'course':'uz-ru','title':'Original','objective':'Test','minutes':8,'module_number':1,'words':[{'target':'А','meaning':'A','media_id':asset}],'exercises':[{'id':'q1','type':'text','prompt':'Type','options':[],'answers':['А'],'explanation':'Original feedback'}]}
        r=author.post('/api/admin/drafts',json=content); assert r.status_code==200,r.text
        path=f"/api/admin/drafts/{r.json()['id']}"
        assert reviewer.post(path+'/reviews',json={'version':1,'decision':'approved','notes':'Test review'}).status_code==200
        r=reviewer.post(path+'/publish',json={'expected_version':1}); assert r.status_code==200,r.text
        lesson=r.json()['lesson_id']; first=learner.post('/api/lessons/'+lesson+'/attempts').json()
        content['title']='Updated'; content['exercises'][0]['answers']=['Б']
        assert author.patch(path+'?expected_version=1',json=content).status_code==200
        assert reviewer.post(path+'/reviews',json={'version':2,'decision':'approved','notes':'Test review'}).status_code==200
        assert reviewer.post(path+'/publish',json={'expected_version':2}).status_code==200
        assert learner.post('/api/lessons/'+lesson+'/attempts').json()['lesson']['title']=='Original'
        answer=learner.post(f"/api/attempts/{first['id']}/answers",json={'exercise_id':'q1','response':'А'})
        assert answer.status_code==200 and answer.json()['correct'],answer.text
        assert learner.post(f"/api/attempts/{first['id']}/complete").status_code==200
        status=next(x for x in learner.get('/api/progress').json() if x['lesson_id']==lesson)
        assert not status['completed'] and status['revision_changed'],status
        second=learner.post('/api/lessons/'+lesson+'/attempts').json()
        assert second['lesson']['title']=='Updated'
        current=reviewer.get(path).json()['published_revision_id']
        r=reviewer.post(path+'/withdraw',json={'expected_revision_id':current,'reason':'Test withdrawal'})
        assert r.status_code==200,r.text
        assert learner.get('/api/lessons/'+lesson).status_code==404
        assert learner.post('/api/lessons/'+lesson+'/attempts').json()['id']==second['id']
        assert learner.get('/api/media/'+asset).status_code==200
        with TestClient(main.app) as outsider:
            assert outsider.get('/api/media/'+asset).status_code==404
        assert reviewer.get(path+'/publications').json()[0]['action']=='withdrawn'
        assert learner.get(f"/api/attempts/{second['id']}/results").status_code==409
        results=learner.get(f"/api/attempts/{first['id']}/results").json()
        assert results['lesson']['title']=='Original' and results['exercises'][0]['explanation']=='Original feedback'
        assert reviewer.get(f"/api/attempts/{first['id']}/results").status_code==404
        assert reviewer.post(path+'/safety-block',json={'reason':'Test urgent issue'}).status_code==200
        assert learner.post('/api/lessons/'+lesson+'/attempts').status_code==410
        assert learner.post(f"/api/attempts/{second['id']}/answers",json={'exercise_id':'q1','response':'Б'}).status_code==410
        assert learner.get(f"/api/attempts/{first['id']}/results").status_code==410
        assert learner.get('/api/media/'+asset).status_code==404
        assert reviewer.post(path+'/safety-unblock',json={'reason':'Test resolved'}).status_code==200
        assert learner.post('/api/lessons/'+lesson+'/attempts').json()['id']==second['id']
        assert learner.get('/api/media/'+asset).status_code==200
        assert learner.get('/api/lessons/'+lesson).status_code==404
        print('PostgreSQL publication, progress, withdrawal, safety block and pinned access: passed')
