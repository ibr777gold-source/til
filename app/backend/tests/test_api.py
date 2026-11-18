import os
os.environ['DATABASE_URL'] = 'sqlite:///./test_til.db'
from fastapi.testclient import TestClient
from app.main import app, Base, engine


def test_learning_flow():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as client:
        assert client.post('/api/auth/register', json={'email':'learner@example.com','password':'longpassword','name':'Learner'}).status_code == 200
        assert client.patch('/api/me',json={'course':'ru-uz'}).json()['course'] == 'ru-uz'
        lesson = client.get('/api/lessons/ru-uz-greetings').json()
        assert all('answers' not in item for item in lesson['exercises'])
        attempt = client.post('/api/lessons/ru-uz-greetings/attempts').json()['id']
        assert client.post(f'/api/attempts/{attempt}/complete').status_code == 400
        for exercise, answer in [('g1','Salom'),('g2','rahmat'),('g3','Assalomu alaykum')]:
            assert client.post(f'/api/attempts/{attempt}/answers',json={'exercise_id':exercise,'response':answer}).json()['correct']
        assert client.post(f'/api/attempts/{attempt}/complete').json() == {'score':100,'passed':True}
        assert client.get('/api/progress').json()[0]['completed']
        assert client.post('/api/auth/logout').status_code == 200
        assert client.get('/api/progress').status_code == 401
    Base.metadata.drop_all(engine)


def test_attempt_ownership_and_origin():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as first, TestClient(app) as second:
        first.post('/api/auth/register',json={'email':'one@example.com','password':'longpassword'})
        attempt=first.post('/api/lessons/uz-ru-greetings/attempts').json()['id']
        second.post('/api/auth/register',json={'email':'two@example.com','password':'longpassword'})
        assert second.post(f'/api/attempts/{attempt}/answers',json={'exercise_id':'g1','response':'Привет'}).status_code == 404
        assert first.post('/api/auth/logout',headers={'Origin':'https://evil.example'}).status_code == 403
    Base.metadata.drop_all(engine)


def test_resume_and_review():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as learner, TestClient(app) as other:
        learner.post('/api/auth/register', json={'email':'resume@example.com','password':'longpassword'})
        a=learner.post('/api/lessons/uz-ru-greetings/attempts').json()
        assert a['answered'] == []
        assert not learner.post(f"/api/attempts/{a['id']}/answers",json={'exercise_id':'g1','response':'Спасибо'}).json()['correct']
        resumed=learner.post('/api/lessons/uz-ru-greetings/attempts').json()
        assert resumed['id']==a['id'] and resumed['answered']==['g1']
        items=learner.get('/api/review').json()
        assert len(items)==1 and 'answers' not in items[0]['exercise']
        other.post('/api/auth/register',json={'email':'other@example.com','password':'longpassword'})
        assert other.post(f"/api/review/{items[0]['id']}/answer",json={'response':'Привет'}).status_code == 404
        assert learner.post(f"/api/review/{items[0]['id']}/answer",json={'response':'Привет'}).json()['correct']
        assert learner.get('/api/review').json()==[]
        upcoming=learner.get('/api/review?include_upcoming=true').json()
        assert len(upcoming)==1 and not upcoming[0]['due']
        early=learner.post(f"/api/review/{items[0]['id']}/answer",json={'response':'Привет'})
        assert early.status_code==200 and early.json()['practiced_early']
        assert learner.get('/api/review?include_upcoming=true').json()[0]['due_at']==upcoming[0]['due_at']
        assert not learner.post(f"/api/review/{items[0]['id']}/answer",json={'response':'Спасибо'}).json()['correct']
        assert len(learner.get('/api/review').json())==1
    Base.metadata.drop_all(engine)


def test_editor_drafts_are_private_and_validated():
    from sqlalchemy.orm import Session
    from app.main import EditorAccess
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    content={'course':'uz-ru','title':'Draft','objective':'Practice','teaching_note':'Explain the pattern.','minutes':8,
             'words':[{'target':'Привет','meaning':'Salom'}],
             'exercises':[{'id':'one','type':'choice','prompt':'Choose','options':['a','b'],'answers':['a'],'explanation':'Explanation'}]}
    with TestClient(app) as editor, TestClient(app) as learner:
        uid=editor.post('/api/auth/register',json={'email':'editor@example.com','password':'longpassword'}).json()['id']
        learner.post('/api/auth/register',json={'email':'reader@example.com','password':'longpassword'})
        assert editor.get('/api/admin/drafts').status_code==403
        with Session(engine) as session:
            session.add(EditorAccess(user_id=uid)); session.commit()
        assert learner.post('/api/admin/drafts',json=content).status_code==403
        draft=editor.post('/api/admin/drafts',json=content)
        assert draft.status_code==200 and draft.json()['status']=='draft'
        assert draft.json()['content']['teaching_note']=='Explain the pattern.'
        assert editor.get('/api/admin/drafts').json()[0]['content']['title']=='Draft'
        assert len(learner.get('/api/courses/uz-ru/lessons').json())==1
        content['exercises'][0]['answers']=['missing']
        assert editor.patch(f"/api/admin/drafts/{draft.json()['id']}?expected_version=1",json=content).status_code==422
        assert editor.get(f"/api/admin/drafts/{draft.json()['id']}").json()['content']['title']=='Draft'
        content['exercises'][0]['answers']=['a']; content['title']='Revised'
        path=f"/api/admin/drafts/{draft.json()['id']}"
        assert editor.patch(path+'?expected_version=1',json=content).json()['version']==2
        assert editor.patch(path+'?expected_version=1',json=content).status_code==409
        history=editor.get(path+'/revisions').json()
        assert [v['content']['title'] for v in history]==['Revised','Draft']
        assert all(v['content']['teaching_note']=='Explain the pattern.' for v in history)
        assert learner.get(path+'/revisions').status_code==403
    Base.metadata.drop_all(engine)


def test_feedback_is_authenticated_and_editor_only():
    from sqlalchemy.orm import Session
    from app.main import EditorAccess
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    payload={'lesson_id':'uz-ru-greetings','category':'content','message':'Please check this phrase.'}
    with TestClient(app) as learner, TestClient(app) as editor:
        assert learner.post('/api/feedback',json=payload).status_code==401
        learner.post('/api/auth/register',json={'email':'feedback@example.com','password':'longpassword'})
        editor_id=editor.post('/api/auth/register',json={'email':'feedback-editor@example.com','password':'longpassword'}).json()['id']
        assert learner.post('/api/feedback',json={**payload,'message':'   '}).status_code==422
        item=learner.post('/api/feedback',json=payload).json()
        assert learner.get('/api/admin/feedback').status_code==403
        with Session(engine) as session:
            session.add(EditorAccess(user_id=editor_id)); session.commit()
        report=editor.get('/api/admin/feedback').json()[0]
        assert report['message']==payload['message'] and 'user_id' not in report
        assert editor.patch(f"/api/admin/feedback/{item['id']}",json={'status':'resolved'}).json()['status']=='resolved'
    Base.metadata.drop_all(engine)


def test_password_reset_is_single_use_and_revokes_sessions(monkeypatch):
    from app import main
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    mail=[]
    monkeypatch.setattr(main,'send_reset_email',lambda address,token: mail.append((address,token)))
    with TestClient(app) as client:
        client.post('/api/auth/register',json={'email':'reset@example.com','password':'longpassword'})
        known=client.post('/api/auth/password-reset/request',json={'email':'reset@example.com'})
        unknown=client.post('/api/auth/password-reset/request',json={'email':'missing@example.com'})
        assert known.json()==unknown.json() and len(mail)==1
        token=mail[0][1]
        assert client.post('/api/auth/password-reset/confirm',json={'token':token,'password':'newlongpassword'}).status_code==200
        assert client.get('/api/me').status_code==401
        assert client.post('/api/auth/password-reset/confirm',json={'token':token,'password':'newlongpassword'}).status_code==400
        assert client.post('/api/auth/login',json={'email':'reset@example.com','password':'longpassword'}).status_code==401
        assert client.post('/api/auth/login',json={'email':'reset@example.com','password':'newlongpassword'}).status_code==200
    Base.metadata.drop_all(engine)


def test_profile_settings_and_deletion_request():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as client:
        assert client.get('/api/profile').status_code==401
        client.post('/api/auth/register',json={'email':'profile@example.com','password':'longpassword','name':'Initial'})
        assert client.get('/api/profile').json()['daily_goal'] is None
        assert client.patch('/api/profile',json={'name':'   ','daily_goal':10}).status_code==422
        assert client.patch('/api/profile',json={'name':' Updated ','daily_goal':20}).json()=={'name':'Updated','daily_goal':20}
        assert client.post('/api/profile/deletion-request').json()['status']=='pending'
        assert client.post('/api/profile/deletion-request').json()['status']=='pending'
        assert client.get('/api/profile').json()['deletion_requested']
    Base.metadata.drop_all(engine)


def test_course_maps_distinguish_planned_content_from_demo():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as client:
        for course in ('uz-ru','ru-uz'):
            modules=client.get(f'/api/courses/{course}/modules').json()
            assert len(modules)==10
            assert [m['number'] for m in modules]==list(range(1,11))
            assert all(m['status']=='planned' and not m['lessons'] for m in modules if m['number']!=3)
            assert modules[2]['status']=='demo' and modules[2]['lessons'][0]['id']==course+'-greetings'
        assert client.get('/api/courses/unknown/modules').status_code==404


def test_draft_reviews_are_versioned_and_require_another_editor():
    from sqlalchemy.orm import Session
    from app.main import EditorAccess
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    content={'course':'uz-ru','title':'Draft','objective':'Practice','minutes':8,'words':[{'target':'А','meaning':'A'}],
             'exercises':[{'id':'q1','type':'text','prompt':'Type','options':[],'answers':['А'],'explanation':'A'}]}
    with TestClient(app) as author, TestClient(app) as reviewer, TestClient(app) as learner:
        author_id=author.post('/api/auth/register',json={'email':'author@example.com','password':'longpassword'}).json()['id']
        reviewer_id=reviewer.post('/api/auth/register',json={'email':'reviewer@example.com','password':'longpassword'}).json()['id']
        learner.post('/api/auth/register',json={'email':'learner@example.com','password':'longpassword'})
        with Session(engine) as session:
            session.add_all([EditorAccess(user_id=author_id),EditorAccess(user_id=reviewer_id)]); session.commit()
        draft=author.post('/api/admin/drafts',json=content).json(); path=f"/api/admin/drafts/{draft['id']}/reviews"
        decision={'version':1,'decision':'approved','notes':'Checked meaning and wording.'}
        assert author.post(path,json=decision).status_code==403
        assert learner.post(path,json=decision).status_code==403
        assert reviewer.post(path,json={**decision,'version':2}).status_code==404
        assert reviewer.post(path,json=decision).json()['version']==1
        content['title']='Changed'; author.patch(f"/api/admin/drafts/{draft['id']}?expected_version=1",json=content)
        assert reviewer.get(path).json()[0]['version']==1
        assert len(learner.get('/api/courses/uz-ru/lessons').json())==1
    Base.metadata.drop_all(engine)


def test_answer_retry_is_idempotent_and_does_not_reset_review():
    from sqlalchemy.orm import Session
    from app.main import ReviewItem
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as client:
        client.post('/api/auth/register',json={'email':'retry@example.com','password':'longpassword'})
        attempt=client.post('/api/lessons/uz-ru-greetings/attempts').json()['id']
        path=f'/api/attempts/{attempt}/answers'
        first=client.post(path,json={'exercise_id':'g1','response':'Спасибо'})
        assert first.status_code==200 and not first.json()['correct']
        item=client.get('/api/review').json()[0]
        client.post(f"/api/review/{item['id']}/answer",json={'response':'Привет'})
        assert client.post(path,json={'exercise_id':'g1','response':'  СПАСИБО  '}).json()==first.json()
        assert client.get('/api/review').json()==[]
        assert client.post(path,json={'exercise_id':'g1','response':'Привет'}).status_code==409
        # A retry after a lost response must not create another answer or remediation item.
        from app.main import AnswerReceipt,LessonRemediation
        from sqlalchemy import func,select
        with Session(engine) as session:
            assert session.scalar(select(func.count()).select_from(AnswerReceipt).where(AnswerReceipt.attempt_id==attempt))==1
            assert session.scalar(select(func.count()).select_from(LessonRemediation).where(LessonRemediation.attempt_id==attempt))==1
        with Session(engine) as session:
            assert session.get(ReviewItem,item['id']).stage==1
    Base.metadata.drop_all(engine)


def test_auth_rate_limit_is_shared_between_clients():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as first, TestClient(app) as second:
        payload={'email':'missing@example.com','password':'longpassword'}
        for _ in range(5):
            assert first.post('/api/auth/login',json=payload).status_code==401
            assert second.post('/api/auth/login',json=payload).status_code==401
        blocked=first.post('/api/auth/login',json=payload)
        assert blocked.status_code==429 and int(blocked.headers['retry-after'])>0
        assert first.post('/api/auth/password-reset/request',json={'email':'missing@example.com'}).status_code==200
    Base.metadata.drop_all(engine)


def test_review_queue_can_be_filtered_by_track():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as client:
        client.post('/api/auth/register',json={'email':'tracks@example.com','password':'longpassword'})
        for course in ('uz-ru','ru-uz'):
            attempt=client.post(f'/api/lessons/{course}-greetings/attempts').json()['id']
            client.post(f'/api/attempts/{attempt}/answers',json={'exercise_id':'g1','response':'wrong'})
        assert len(client.get('/api/review').json())==2
        assert [x['course'] for x in client.get('/api/review?course=ru-uz').json()]==['ru-uz']
        assert [x['course'] for x in client.get('/api/review?course=uz-ru').json()]==['uz-ru']
        assert client.get('/api/review?course=other').status_code==422
    Base.metadata.drop_all(engine)


def test_analytics_count_once_and_exclude_answers():
    from sqlalchemy.orm import Session
    from sqlalchemy import select
    from app.main import AnalyticsEvent, EditorAccess
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as learner, TestClient(app) as editor:
        learner.post('/api/auth/register',json={'email':'learner-analytics@example.com','password':'longpassword'})
        editor_id=editor.post('/api/auth/register',json={'email':'editor-analytics@example.com','password':'longpassword'}).json()['id']
        with Session(engine) as session:
            session.add(EditorAccess(user_id=editor_id)); session.commit()
        a=learner.post('/api/lessons/uz-ru-greetings/attempts').json()['id']
        learner.post('/api/lessons/uz-ru-greetings/attempts')
        for exercise, answer in [('g1','Привет'),('g2','спасибо'),('g3','До свидания')]:
            learner.post(f'/api/attempts/{a}/answers',json={'exercise_id':exercise,'response':answer})
        learner.post(f'/api/attempts/{a}/answers',json={'exercise_id':'g1','response':'Привет'})
        learner.post(f'/api/attempts/{a}/complete'); learner.post(f'/api/attempts/{a}/complete')
        assert learner.get('/api/admin/analytics/overview').status_code==403
        summary=editor.get('/api/admin/analytics/overview').json()
        assert summary['learners_completing_practice']==1
        assert summary['events']['lesson_started']==1 and summary['events']['exercise_answered']==3 and summary['events']['lesson_completed']==1
        with Session(engine) as session:
            assert all('Привет' not in e.properties and 'longpassword' not in e.properties for e in session.scalars(select(AnalyticsEvent)))
    Base.metadata.drop_all(engine)


def test_review_session_requires_scored_answer_and_counts_once():
    from sqlalchemy.orm import Session
    from app.main import EditorAccess
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as learner, TestClient(app) as editor:
        learner.post('/api/auth/register',json={'email':'review-session@example.com','password':'longpassword'})
        editor_id=editor.post('/api/auth/register',json={'email':'review-admin@example.com','password':'longpassword'}).json()['id']
        with Session(engine) as s:
            s.add(EditorAccess(user_id=editor_id)); s.commit()
        attempt=learner.post('/api/lessons/uz-ru-greetings/attempts').json()['id']
        learner.post(f'/api/attempts/{attempt}/answers',json={'exercise_id':'g1','response':'wrong'})
        item=learner.get('/api/review').json()[0]['id']
        session=learner.post('/api/review/sessions',json={'course':'uz-ru'}).json()['id']
        path=f'/api/review/sessions/{session}/complete'
        assert learner.post(path).status_code==400
        assert editor.post(path).status_code==404
        assert learner.post(f'/api/review/{item}/answer',json={'response':'Привет','session_id':session}).json()['correct']
        assert learner.post(path).json()['answer_count']==1
        assert learner.post(path).json()['completed']
        summary=editor.get('/api/admin/analytics/overview').json()
        assert summary['learners_completing_practice']==1 and summary['events']['review_completed']==1
    Base.metadata.drop_all(engine)


def test_media_is_private_bounded_and_attachable(tmp_path,monkeypatch):
    from sqlalchemy.orm import Session
    from app import main
    from app.main import EditorAccess
    monkeypatch.setattr(main,'MEDIA_ROOT',tmp_path)
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as editor, TestClient(app) as learner:
        editor_id=editor.post('/api/auth/register',json={'email':'audio-editor@example.com','password':'longpassword'}).json()['id']
        learner.post('/api/auth/register',json={'email':'audio-learner@example.com','password':'longpassword'})
        with Session(engine) as s:
            s.add(EditorAccess(user_id=editor_id)); s.commit()
        data=b'RIFF'+b'\x00'*4+b'WAVE'+b'example'
        assert learner.post('/api/admin/media',content=data).status_code==403
        assert editor.post('/api/admin/media',content=b'not audio').status_code==415
        assert editor.post('/api/admin/media',content=b'x'*(5*1024*1024+1)).status_code==413
        asset=editor.post('/api/admin/media?attribution=Original',content=data).json()
        assert asset['rights_status']=='unverified' and editor.get('/api/admin/media/'+asset['id']).content==data
        assert learner.get('/api/admin/media/'+asset['id']).status_code==403
        content={'course':'uz-ru','title':'Audio draft','objective':'Practice','minutes':8,'words':[{'target':'А','meaning':'A','media_id':asset['id']}],
                 'exercises':[{'id':'q1','type':'text','prompt':'Type','options':[],'answers':['А'],'explanation':'A'}]}
        assert editor.post('/api/admin/drafts',json=content).status_code==200
        content['words'][0]['media_id']='missing'
        assert editor.post('/api/admin/drafts',json=content).status_code==422
    Base.metadata.drop_all(engine)


def test_audio_rights_review_is_separate_and_auditable(tmp_path,monkeypatch):
    from sqlalchemy.orm import Session
    from app import main
    from app.main import EditorAccess
    monkeypatch.setattr(main,'MEDIA_ROOT',tmp_path)
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as uploader, TestClient(app) as reviewer:
        uid=uploader.post('/api/auth/register',json={'email':'audio-owner@example.com','password':'longpassword'}).json()['id']
        rid=reviewer.post('/api/auth/register',json={'email':'audio-review@example.com','password':'longpassword'}).json()['id']
        with Session(engine) as s:
            s.add_all([EditorAccess(user_id=uid),EditorAccess(user_id=rid)]); s.commit()
        asset=uploader.post('/api/admin/media?attribution=Original+recording',content=b'RIFF'+b'\0'*4+b'WAVEdata').json()
        path='/api/admin/media/'+asset['id']+'/reviews'
        decision={'decision':'approved','notes':'Checked source and license evidence.'}
        assert uploader.post(path,json=decision).status_code==403
        assert reviewer.post(path,json=decision).json()['rights_status']=='approved'
        assert reviewer.get(path).json()[0]['reviewer_id']==rid
        assert reviewer.get('/api/admin/media').json()[0]['rights_status']=='approved'
    Base.metadata.drop_all(engine)


def test_publication_pins_attempt_and_review_to_reviewed_revision(tmp_path,monkeypatch):
    from sqlalchemy.orm import Session
    from app import main
    from app.main import EditorAccess, PublisherAccess
    monkeypatch.setattr(main,'MEDIA_ROOT',tmp_path)
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as author, TestClient(app) as reviewer, TestClient(app) as learner:
        aid=author.post('/api/auth/register',json={'email':'publish-author@example.com','password':'longpassword'}).json()['id']
        rid=reviewer.post('/api/auth/register',json={'email':'publish-reviewer@example.com','password':'longpassword'}).json()['id']
        learner.post('/api/auth/register',json={'email':'publish-learner@example.com','password':'longpassword'})
        with Session(engine) as s:
            s.add_all([EditorAccess(user_id=aid),EditorAccess(user_id=rid),PublisherAccess(user_id=rid)]); s.commit()
        asset=author.post('/api/admin/media?attribution=Original',content=b'RIFF'+b'\0'*4+b'WAVEdata').json()['id']
        content={'course':'uz-ru','title':'Original','objective':'Practice','minutes':8,'module_number':1,'words':[{'target':'А','meaning':'A','media_id':asset}],
                 'exercises':[{'id':'q1','type':'text','prompt':'Type A','options':[],'answers':['А'],'explanation':'Old explanation'}]}
        draft=author.post('/api/admin/drafts',json=content).json(); path=f"/api/admin/drafts/{draft['id']}"
        assert learner.get('/api/lessons/draft-'+str(draft['id'])).status_code==404
        assert author.post(path+'/publish',json={'expected_version':1}).status_code==403
        assert reviewer.post(path+'/publish',json={'expected_version':1}).status_code==409
        reviewer.post(path+'/reviews',json={'version':1,'decision':'approved','notes':'Checked language.'})
        assert reviewer.post(path+'/publish',json={'expected_version':1}).status_code==409
        reviewer.post('/api/admin/media/'+asset+'/reviews',json={'decision':'approved','notes':'Source and rights checked.'})
        published=reviewer.post(path+'/publish',json={'expected_version':1}).json(); lesson_id=published['lesson_id']
        assert reviewer.post(path+'/publish',json={'expected_version':1}).json()['revision_id']==published['revision_id']
        assert learner.get('/api/media/'+asset).status_code==200
        first=learner.post(f'/api/lessons/{lesson_id}/attempts').json()
        assert 'answers' not in first['lesson']['exercises'][0]
        content['title']='Revised'; content['exercises'][0]['answers']=['Б']; content['exercises'][0]['explanation']='New explanation'
        assert author.patch(path+'?expected_version=1',json=content).json()['version']==2
        assert reviewer.post(path+'/publish',json={'expected_version':2}).status_code==409
        reviewer.post(path+'/reviews',json={'version':2,'decision':'approved','notes':'Checked revision.'})
        assert reviewer.post(path+'/publish',json={'expected_version':2}).status_code==200
        assert learner.get(f'/api/lessons/{lesson_id}').json()['title']=='Revised'
        resumed=learner.post(f'/api/lessons/{lesson_id}/attempts').json()
        assert resumed['lesson']['title']=='Original' and resumed['id']==first['id']
        answer=learner.post(f"/api/attempts/{first['id']}/answers",json={'exercise_id':'q1','response':'wrong'}).json()
        assert answer['correct_answer']=='А' and answer['explanation']=='Old explanation'
        item=learner.get('/api/review?course=uz-ru').json()[0]
        review=learner.post(f"/api/review/{item['id']}/answer",json={'response':'А'}).json()
        assert review['correct'] and review['explanation']=='Old explanation'
        assert learner.post(f"/api/attempts/{first['id']}/remediation/q1",json={'response':'А'}).json()['correct']
        assert learner.post(f"/api/attempts/{first['id']}/complete").json()['score']==0
        old_result=learner.get(f"/api/attempts/{first['id']}/results").json()
        assert old_result['lesson']['title']=='Original' and old_result['exercises'][0]['explanation']=='Old explanation'
        second=learner.post(f'/api/lessons/{lesson_id}/attempts').json()
        assert second['lesson']['title']=='Revised'
        assert learner.post(f"/api/attempts/{second['id']}/answers",json={'exercise_id':'q1','response':'Б'}).json()['correct']
        current=reviewer.get(path).json()['published_revision_id']
        assert reviewer.post(path+'/withdraw',json={'expected_revision_id':current+1,'reason':'Correction'}).status_code==409
        assert author.post(path+'/withdraw',json={'expected_revision_id':current,'reason':'Correction'}).status_code==403
        assert reviewer.post(path+'/withdraw',json={'expected_revision_id':current,'reason':'Correction'}).status_code==200
        assert learner.get(f'/api/lessons/{lesson_id}').status_code==404
        assert reviewer.post(f'/api/lessons/{lesson_id}/attempts').status_code==404
        assert any(x['lesson_id']==lesson_id for x in learner.get('/api/continue').json())
        assert learner.post(f'/api/lessons/{lesson_id}/attempts').json()['id']==second['id']
        assert learner.get('/api/media/'+asset).status_code==200
        with TestClient(app) as outsider:
            assert outsider.get('/api/media/'+asset).status_code==404
        assert reviewer.get(path+'/publications').json()[0]['action']=='withdrawn'
        assert learner.post(f"/api/attempts/{second['id']}/complete").json()['score']==100
        reviewer.post('/api/admin/media/'+asset+'/reviews',json={'decision':'rejected','notes':'Permission withdrawn.'})
        assert learner.get('/api/media/'+asset).status_code==404
    Base.metadata.drop_all(engine)


def test_word_order_validates_tokens_and_scores_without_exposing_answers(monkeypatch):
    from sqlalchemy.orm import Session
    from app import main
    from app.main import EditorAccess
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    lesson={'course':'uz-ru','title':'Order','objective':'Practice','eyebrow':'DRAFT','minutes':8,'words':[{'target':'А','meaning':'A'}],
            'exercises':[{'id':'q1','type':'order','prompt':'Order','options':['мир','Привет'],'answers':['Привет мир'],'explanation':'Greeting first.'}]}
    monkeypatch.setitem(main.LESSONS,'order-demo',lesson)
    with TestClient(app) as editor:
        uid=editor.post('/api/auth/register',json={'email':'order@example.com','password':'longpassword'}).json()['id']
        with Session(engine) as s:
            s.add(EditorAccess(user_id=uid)); s.commit()
        draft={'course':'uz-ru','title':'Order','objective':'Practice','minutes':8,'words':lesson['words'],'exercises':lesson['exercises']}
        assert editor.post('/api/admin/drafts',json=draft).status_code==200
        invalid={**draft,'exercises':[{**lesson['exercises'][0],'answers':['Привет привет']}]}
        assert editor.post('/api/admin/drafts',json=invalid).status_code==422
        attempt=editor.post('/api/lessons/order-demo/attempts').json()
        assert 'answers' not in attempt['lesson']['exercises'][0]
        result=editor.post(f"/api/attempts/{attempt['id']}/answers",json={'exercise_id':'q1','response':'Привет мир'}).json()
        assert result['correct']
    Base.metadata.drop_all(engine)


def test_listening_exercise_requires_reviewed_audio_and_hides_answers(tmp_path,monkeypatch):
    from sqlalchemy.orm import Session
    from app import main
    from app.main import EditorAccess, PublisherAccess
    monkeypatch.setattr(main,'MEDIA_ROOT',tmp_path)
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as author, TestClient(app) as reviewer, TestClient(app) as learner:
        aid=author.post('/api/auth/register',json={'email':'listen-author@example.com','password':'longpassword'}).json()['id']
        rid=reviewer.post('/api/auth/register',json={'email':'listen-reviewer@example.com','password':'longpassword'}).json()['id']
        learner.post('/api/auth/register',json={'email':'listen-learner@example.com','password':'longpassword'})
        with Session(engine) as s:
            s.add_all([EditorAccess(user_id=aid),EditorAccess(user_id=rid),PublisherAccess(user_id=rid)]); s.commit()
        wav=b'RIFF'+b'\0'*4+b'WAVEdata'
        word_audio=author.post('/api/admin/media?attribution=Word',content=wav).json()['id']
        question_audio=author.post('/api/admin/media?attribution=Question',content=wav).json()['id']
        content={'course':'uz-ru','title':'Listening','objective':'Listen','minutes':8,'module_number':1,'words':[{'target':'А','meaning':'A','media_id':word_audio}],
                 'exercises':[{'id':'q1','type':'listen_choice','prompt':'Listen and choose','options':['A','B'],'answers':['A'],'explanation':'A','media_id':question_audio}]}
        missing={**content,'exercises':[{**content['exercises'][0],'media_id':None}]}
        assert author.post('/api/admin/drafts',json=missing).status_code==422
        draft=author.post('/api/admin/drafts',json=content).json(); path=f"/api/admin/drafts/{draft['id']}"
        reviewer.post(path+'/reviews',json={'version':1,'decision':'approved','notes':'Checked.'})
        reviewer.post('/api/admin/media/'+word_audio+'/reviews',json={'decision':'approved','notes':'Reviewed.'})
        assert reviewer.post(path+'/publish',json={'expected_version':1}).status_code==409
        reviewer.post('/api/admin/media/'+question_audio+'/reviews',json={'decision':'approved','notes':'Reviewed.'})
        lesson_id=reviewer.post(path+'/publish',json={'expected_version':1}).json()['lesson_id']
        attempt=learner.post(f'/api/lessons/{lesson_id}/attempts').json()
        exercise=attempt['lesson']['exercises'][0]
        assert exercise['media_id']==question_audio and 'answers' not in exercise
        assert learner.get('/api/media/'+question_audio).status_code==200
        assert learner.post(f"/api/attempts/{attempt['id']}/answers",json={'exercise_id':'q1','response':'A'}).json()['correct']
    Base.metadata.drop_all(engine)


def test_guided_dialogue_validates_context_and_supports_review(monkeypatch):
    from sqlalchemy.orm import Session
    from app import main
    from app.main import EditorAccess
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    exercise={'id':'q1','type':'dialogue','prompt':'What do you say?','options':['Hello','Goodbye'],'answers':['Hello'],
              'explanation':'A greeting fits.','dialogue':[{'speaker':'A','text':'Hello!'}]}
    lesson={'course':'uz-ru','title':'Dialogue','objective':'Practice','eyebrow':'DRAFT','minutes':8,'words':[{'target':'A','meaning':'A'}],'exercises':[exercise]}
    monkeypatch.setitem(main.LESSONS,'dialogue-demo',lesson)
    with TestClient(app) as editor:
        uid=editor.post('/api/auth/register',json={'email':'dialogue@example.com','password':'longpassword'}).json()['id']
        with Session(engine) as s:
            s.add(EditorAccess(user_id=uid)); s.commit()
        draft={'course':'uz-ru','title':'Dialogue','objective':'Practice','minutes':8,'words':lesson['words'],'exercises':[exercise]}
        assert editor.post('/api/admin/drafts',json=draft).status_code==200
        invalid={**draft,'exercises':[{**exercise,'dialogue':[]}]}
        assert editor.post('/api/admin/drafts',json=invalid).status_code==422
        attempt=editor.post('/api/lessons/dialogue-demo/attempts').json()
        public=attempt['lesson']['exercises'][0]
        assert public['dialogue']==exercise['dialogue'] and 'answers' not in public
        result=editor.post(f"/api/attempts/{attempt['id']}/answers",json={'exercise_id':'q1','response':'Goodbye'}).json()
        assert not result['correct']
        item=editor.get('/api/review?course=uz-ru').json()[0]
        assert item['exercise']['dialogue']==exercise['dialogue']
        assert editor.post(f"/api/review/{item['id']}/answer",json={'response':'Hello'}).json()['correct']
    Base.metadata.drop_all(engine)


def test_private_vocabulary_staging_is_read_only_and_paginated(tmp_path,monkeypatch):
    import json
    from sqlalchemy.orm import Session
    from app import main
    from app.main import EditorAccess
    path=tmp_path/'staging.jsonl'
    records=[{'entry_id':1,'source_sha256':'a'*64,'candidate_headword':'Привет','raw_heading':'Привет','flags':[],'review_status':'unreviewed','rights_status':'unverified'},
             {'entry_id':2,'source_sha256':'b'*64,'candidate_headword':'Мир','raw_heading':'Мир','flags':['check'],'review_status':'unreviewed','rights_status':'unverified'}]
    path.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in records),encoding='utf-8')
    monkeypatch.setattr(main,'STAGED_VOCABULARY',path)
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as editor, TestClient(app) as learner:
        uid=editor.post('/api/auth/register',json={'email':'vocab-editor@example.com','password':'longpassword'}).json()['id']
        learner.post('/api/auth/register',json={'email':'vocab-learner@example.com','password':'longpassword'})
        with Session(engine) as s:
            s.add(EditorAccess(user_id=uid)); s.commit()
        assert learner.get('/api/admin/vocabulary').status_code==403
        assert editor.get('/api/admin/vocabulary?query=привет').json()['items'][0]['entry_id']==1
        assert editor.get('/api/admin/vocabulary?flagged=true').json()['items'][0]['entry_id']==2
        assert editor.get('/api/admin/vocabulary?offset=1&limit=1').json()['items'][0]['entry_id']==2
        assert editor.get('/api/admin/vocabulary?limit=101').status_code==422
        assert editor.post('/api/admin/vocabulary',json={}).status_code==405
        assert json.loads(path.read_text(encoding='utf-8').splitlines()[0])==records[0]
        payload={'source_sha256':'a'*64,'disposition':'candidate','level':'a1','topic':'greetings','part_of_speech':'interjection','notes':'Review in context.'}
        assert learner.post('/api/admin/vocabulary/1/assessments',json=payload).status_code==403
        assert editor.post('/api/admin/vocabulary/1/assessments',json={**payload,'source_sha256':'b'*64}).status_code==409
        assert editor.post('/api/admin/vocabulary/1/assessments',json=payload).status_code==200
        assert editor.post('/api/admin/vocabulary/1/assessments',json={**payload,'disposition':'needs_review','notes':'Check translation.'}).status_code==200
        history=editor.get('/api/admin/vocabulary/1/assessments').json()
        assert [r['disposition'] for r in history]==['needs_review','candidate']
        assert editor.get('/api/admin/vocabulary?query=привет').json()['items'][0]['assessment']['disposition']=='needs_review'
        assert json.loads(path.read_text(encoding='utf-8').splitlines()[0])==records[0]
    Base.metadata.drop_all(engine)


def test_curriculum_outlines_are_editor_only_and_not_published():
    from sqlalchemy.orm import Session
    from app.main import EditorAccess
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as editor, TestClient(app) as learner:
        uid=editor.post('/api/auth/register',json={'email':'curriculum-editor@example.com','password':'longpassword'}).json()['id']
        learner.post('/api/auth/register',json={'email':'curriculum-learner@example.com','password':'longpassword'})
        with Session(engine) as session:
            session.add(EditorAccess(user_id=uid)); session.commit()
        assert learner.get('/api/admin/curriculum/uz-ru').status_code==403
        for course in ('uz-ru','ru-uz'):
            outline=editor.get('/api/admin/curriculum/'+course).json()
            assert outline['course']==course and outline['status']=='draft_unreviewed'
            assert [m['number'] for m in outline['modules']]==list(range(1,11))
            assert all([l['number'] for l in m['lessons']]==list(range(1,7)) for m in outline['modules'])
            assert all(all(l['title'] and l['objective'] and l['practice'] for l in m['lessons']) for m in outline['modules'])
            assert len(learner.get('/api/courses/'+course+'/lessons').json())==1
        assert editor.get('/api/admin/curriculum/other').status_code==422
    Base.metadata.drop_all(engine)


def test_draft_outline_provenance_checks_source_and_stays_private():
    from sqlalchemy.orm import Session
    from app.main import EditorAccess, public_lesson
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as editor:
        uid=editor.post('/api/auth/register',json={'email':'outline-editor@example.com','password':'longpassword'}).json()['id']
        with Session(engine) as s:
            s.add(EditorAccess(user_id=uid)); s.commit()
        outline=editor.get('/api/admin/curriculum/uz-ru').json()
        ref={'course':'uz-ru','module_number':1,'lesson_number':1,'source_sha256':outline['source_sha256']}
        content={'course':'uz-ru','title':'Draft','objective':'Practice','minutes':8,'module_number':1,'outline_ref':ref,
                 'words':[{'target':'А','meaning':'A'}],
                 'exercises':[{'id':'q1','type':'text','prompt':'Type','options':[],'answers':['А'],'explanation':'A'}]}
        assert editor.post('/api/admin/drafts',json={**content,'module_number':2}).status_code==422
        assert editor.post('/api/admin/drafts',json={**content,'outline_ref':{**ref,'source_sha256':'0'*64}}).status_code==409
        draft=editor.post('/api/admin/drafts',json=content)
        assert draft.status_code==200 and draft.json()['content']['outline_ref']==ref
        public=public_lesson('example',draft.json()['content'])
        assert 'outline_ref' not in public and 'answers' not in public['exercises'][0]
    Base.metadata.drop_all(engine)


def test_curriculum_outlines_show_linked_revision_review_and_source_drift(tmp_path,monkeypatch):
    import json
    from sqlalchemy.orm import Session
    from app import main
    from app.main import EditorAccess
    source=main.CURRICULUM_ROOT/'uz-ru.json'; copy=tmp_path/'uz-ru.json'; copy.write_bytes(source.read_bytes())
    monkeypatch.setattr(main,'CURRICULUM_ROOT',tmp_path)
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as author, TestClient(app) as reviewer:
        aid=author.post('/api/auth/register',json={'email':'map-author@example.com','password':'longpassword'}).json()['id']
        rid=reviewer.post('/api/auth/register',json={'email':'map-reviewer@example.com','password':'longpassword'}).json()['id']
        with Session(engine) as s:
            s.add_all([EditorAccess(user_id=aid),EditorAccess(user_id=rid)]); s.commit()
        outline=author.get('/api/admin/curriculum/uz-ru').json()
        ref={'course':'uz-ru','module_number':1,'lesson_number':1,'source_sha256':outline['source_sha256']}
        content={'course':'uz-ru','title':'Draft','objective':'Practice','minutes':8,'module_number':1,'outline_ref':ref,'words':[{'target':'А','meaning':'A'}],
                 'exercises':[{'id':'q1','type':'text','prompt':'Type','options':[],'answers':['А'],'explanation':'A'}]}
        draft=author.post('/api/admin/drafts',json=content).json(); path=f"/api/admin/drafts/{draft['id']}"
        entry=author.get('/api/admin/curriculum/uz-ru').json()['modules'][0]['lessons'][0]['drafts'][0]
        assert entry['version']==1 and entry['review'] is None and not entry['source_changed']
        assert reviewer.post(path+'/reviews',json={'version':1,'decision':'approved','notes':'Reviewed.'}).status_code==200
        assert author.get('/api/admin/curriculum/uz-ru').json()['modules'][0]['lessons'][0]['drafts'][0]['review']=='approved'
        content['title']='Changed'; assert author.patch(path+'?expected_version=1',json=content).status_code==200
        entry=author.get('/api/admin/curriculum/uz-ru').json()['modules'][0]['lessons'][0]['drafts'][0]
        assert entry['version']==2 and entry['review'] is None
        data=json.loads(copy.read_text(encoding='utf-8')); data['modules'][0]['title']+=' updated'
        copy.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
        assert author.get('/api/admin/curriculum/uz-ru').json()['modules'][0]['lessons'][0]['drafts'][0]['source_changed']
    Base.metadata.drop_all(engine)


def test_published_lessons_follow_module_and_lesson_order():
    import json
    from datetime import datetime, timezone
    from sqlalchemy.orm import Session
    from app.main import DraftLesson, PublishedRevision, PublishedLesson
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as client:
        uid=client.post('/api/auth/register',json={'email':'ordering@example.com','password':'longpassword'}).json()['id']
        with Session(engine) as s:
            for module,position,title in [(3,1,'Published greeting'),(1,2,'Second'),(1,1,'First')]:
                content={'course':'uz-ru','title':title,'objective':'Practice','minutes':8,'module_number':module,'lesson_number':position,'words':[],'exercises':[]}
                draft=DraftLesson(author_id=uid,data=json.dumps(content),updated_at=datetime.now(timezone.utc).replace(tzinfo=None));s.add(draft);s.flush()
                pub=PublishedRevision(draft_id=draft.id,draft_version=1,lesson_id=f'draft-{draft.id}',course='uz-ru',module_number=module,data=json.dumps(content),publisher_id=uid,created_at=datetime.now(timezone.utc).replace(tzinfo=None));s.add(pub);s.flush()
                s.add(PublishedLesson(lesson_id=pub.lesson_id,revision_id=pub.id))
            s.commit()
        items=client.get('/api/courses/uz-ru/lessons').json()
        assert [x['title'] for x in items[:3]]==['First','Second','Published greeting']
        assert items[3]['demo'] is True and items[2]['demo'] is False
        modules=client.get('/api/courses/uz-ru/modules').json()
        assert [x['title'] for x in modules[0]['lessons']]==['First','Second']
        assert modules[2]['status']=='available' and modules[2]['lessons'][1]['demo']
    Base.metadata.drop_all(engine)


def test_results_are_private_and_only_available_after_completion():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as learner, TestClient(app) as other:
        learner.post('/api/auth/register',json={'email':'results@example.com','password':'longpassword'})
        other.post('/api/auth/register',json={'email':'other-results@example.com','password':'longpassword'})
        a=learner.post('/api/lessons/uz-ru-greetings/attempts').json()['id']
        assert learner.get(f'/api/attempts/{a}/results').status_code==409
        assert other.get(f'/api/attempts/{a}/results').status_code==404
        assert learner.get('/api/lessons/uz-ru-greetings/results').status_code==404
        for question,response in [('g1','Привет'),('g2','wrong'),('g3','До свидания')]:
            learner.post(f'/api/attempts/{a}/answers',json={'exercise_id':question,'response':response})
        assert learner.post(f'/api/attempts/{a}/remediation/g2',json={'response':'спасибо'}).json()['correct']
        learner.post(f'/api/attempts/{a}/complete')
        result=learner.get(f'/api/attempts/{a}/results').json()
        assert result['score']==67 and not result['passed']
        assert result['exercises'][0]['correct'] and not result['exercises'][1]['correct']
        assert result['exercises'][1]['correct_answer']=='спасибо' and result['exercises'][1]['explanation']
        assert 'answers' not in result['lesson']['exercises'][0]
        assert learner.get('/api/lessons/uz-ru-greetings/results').json()['attempt_id']==a
        assert other.get('/api/lessons/uz-ru-greetings/results').status_code==404
    Base.metadata.drop_all(engine)


def test_answer_normalization_policies_preserve_meaningful_differences(monkeypatch):
    from app import main
    from app.main import normalized
    assert normalized(" Oʻzbek ")==normalized('o‘zbek')
    assert normalized('O‘')!=normalized('O')
    assert normalized('ёлка')!=normalized('елка')
    assert normalized('Salom!')!=normalized('Salom')
    assert normalized('Salom!',{'punctuation_tolerant':True})==normalized('salom',{'punctuation_tolerant':True})
    assert normalized('a.b',{'punctuation_tolerant':True})!=normalized('ab',{'punctuation_tolerant':True})
    assert normalized('Salom',{'case_sensitive':True})!=normalized('salom',{'case_sensitive':True})
    assert normalized("O'zbek",{'apostrophe_variants':False})!=normalized('O‘zbek',{'apostrophe_variants':False})
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    lesson={'course':'uz-ru','title':'Policies','objective':'Practice','eyebrow':'DRAFT','minutes':8,'words':[{'target':'A','meaning':'A'}],
            'exercises':[{'id':'case','type':'text','prompt':'Case','answers':['Salom'],'explanation':'Case matters','normalization':{'case_sensitive':True}},
                         {'id':'punct','type':'text','prompt':'Punctuation','answers':['Rahmat'],'explanation':'Punctuation','normalization':{'punctuation_tolerant':True}},
                         {'id':'apostrophe','type':'text','prompt':'Apostrophe','answers':['O‘zbek'],'explanation':'Letter'}]}
    monkeypatch.setitem(main.LESSONS,'policy-demo',lesson)
    with TestClient(app) as client:
        client.post('/api/auth/register',json={'email':'policy@example.com','password':'longpassword'})
        attempt=client.post('/api/lessons/policy-demo/attempts').json()['id']
        path=f'/api/attempts/{attempt}/answers'
        assert not client.post(path,json={'exercise_id':'case','response':'salom'}).json()['correct']
        assert client.post(path,json={'exercise_id':'punct','response':'rahmat!'}).json()['correct']
        first=client.post(path,json={'exercise_id':'apostrophe','response':"O'zbek"}).json()
        assert first['correct'] and client.post(path,json={'exercise_id':'apostrophe','response':'O‘zbek'}).json()==first
        item=client.get('/api/review?course=uz-ru').json()[0]
        assert not client.post(f"/api/review/{item['id']}/answer",json={'response':'salom'}).json()['correct']
        assert client.post(f"/api/review/{item['id']}/answer",json={'response':'Salom'}).json()['correct']
    Base.metadata.drop_all(engine)


def test_matching_hides_answer_key_and_scores_complete_pairs(monkeypatch):
    import json
    from sqlalchemy.orm import Session
    from app import main
    from app.main import EditorAccess
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    pairs=[{'left':'one','right':'bir'},{'left':'two','right':'ikki'},{'left':'three','right':'uch'}]
    exercise={'id':'q1','type':'match','prompt':'Match','answers':[],'explanation':'Review the pairs.','match_pairs':pairs}
    lesson={'course':'uz-ru','title':'Matching','objective':'Practice','eyebrow':'DRAFT','minutes':8,'words':[{'target':'A','meaning':'A'}],'exercises':[exercise]}
    monkeypatch.setitem(main.LESSONS,'match-demo',lesson)
    with TestClient(app) as editor:
        uid=editor.post('/api/auth/register',json={'email':'matching@example.com','password':'longpassword'}).json()['id']
        with Session(engine) as s:
            s.add(EditorAccess(user_id=uid)); s.commit()
        draft={'course':'uz-ru','title':'Matching','objective':'Practice','minutes':8,'words':lesson['words'],'exercises':[exercise]}
        assert editor.post('/api/admin/drafts',json=draft).status_code==200
        invalid={**draft,'exercises':[{**exercise,'match_pairs':[pairs[0],{'left':'one','right':'other'}]}]}
        assert editor.post('/api/admin/drafts',json=invalid).status_code==422
        attempt=editor.post('/api/lessons/match-demo/attempts').json()
        public=attempt['lesson']['exercises'][0]
        assert 'answers' not in public and 'match_pairs' not in public and 'explanation' not in public
        assert set(public['match_left'])=={'one','two','three'} and set(public['match_right'])=={'bir','ikki','uch'}
        path=f"/api/attempts/{attempt['id']}/answers"
        wrong={'one':'ikki','two':'bir','three':'uch'}
        first=editor.post(path,json={'exercise_id':'q1','response':json.dumps(wrong)}).json()
        assert not first['correct'] and 'one → bir' in first['correct_answer']
        assert editor.post(path,json={'exercise_id':'q1','response':json.dumps(dict(reversed(list(wrong.items()))))}).json()==first
        item=editor.get('/api/review?course=uz-ru').json()[0]
        assert 'match_pairs' not in item['exercise']
        response=json.dumps({'one':'bir','two':'ikki','three':'uch'})
        assert editor.post(f"/api/review/{item['id']}/answer",json={'response':response}).json()['correct']
        assert editor.post(f"/api/attempts/{attempt['id']}/remediation/q1",json={'response':response}).json()['correct']
        assert editor.post(f"/api/attempts/{attempt['id']}/complete").status_code==200
        assert 'one → bir' in editor.get(f"/api/attempts/{attempt['id']}/results").json()['exercises'][0]['correct_answer']
    Base.metadata.drop_all(engine)


def test_onboarding_saves_track_goal_and_is_idempotent():
    from sqlalchemy.orm import Session
    from sqlalchemy import select
    from app.main import AnalyticsEvent
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as client:
        assert client.get('/api/onboarding').status_code==401
        uid=client.post('/api/auth/register',json={'email':'onboarding@example.com','password':'longpassword'}).json()['id']
        assert not client.get('/api/onboarding').json()['completed']
        payload={'course':'ru-uz','motivation':'travel','daily_goal':None}
        assert client.post('/api/onboarding',json={**payload,'daily_goal':2}).status_code==422
        assert client.post('/api/onboarding',json=payload).json()=={'completed':True,**payload}
        assert client.get('/api/me').json()['course']=='ru-uz'
        assert client.get('/api/profile').json()['daily_goal'] is None
        assert client.post('/api/onboarding',json=payload).status_code==200
        with Session(engine) as s:
            names=[x.event_name for x in s.scalars(select(AnalyticsEvent).where(AnalyticsEvent.user_id==uid))]
            assert names.count('onboarding_completed')==1 and names.count('course_selected')==1
        assert client.post('/api/onboarding',json={**payload,'daily_goal':15}).json()['daily_goal']==15
        assert client.get('/api/profile').json()['daily_goal']==15
        assert client.patch('/api/profile',json={'name':'Learner','daily_goal':None}).json()['daily_goal'] is None
    Base.metadata.drop_all(engine)


def test_progress_counts_current_revision_and_limits_visibility():
    import json
    from datetime import datetime, timezone
    from sqlalchemy.orm import Session
    from app.main import DraftLesson, PublishedRevision, PublishedLesson, Attempt, AttemptContent, Progress
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as learner, TestClient(app) as other:
        uid=learner.post('/api/auth/register',json={'email':'version-progress@example.com','password':'longpassword'}).json()['id']
        other.post('/api/auth/register',json={'email':'other-progress@example.com','password':'longpassword'})
        now=datetime.now(timezone.utc).replace(tzinfo=None)
        data={'course':'uz-ru','title':'Lesson','objective':'Practice','eyebrow':'DRAFT','minutes':8,'module_number':1,'lesson_number':1,'words':[{'target':'А','meaning':'A'}],
              'exercises':[{'id':'q1','type':'text','prompt':'Type','answers':['А'],'explanation':'A'}]}
        with Session(engine) as s:
            draft=DraftLesson(author_id=uid,data=json.dumps(data),updated_at=now);s.add(draft);s.flush(); lesson_id=f'draft-{draft.id}'
            v1=PublishedRevision(draft_id=draft.id,draft_version=1,lesson_id=lesson_id,course='uz-ru',module_number=1,data=json.dumps(data),publisher_id=uid,created_at=now);s.add(v1);s.flush()
            v2=PublishedRevision(draft_id=draft.id,draft_version=2,lesson_id=lesson_id,course='uz-ru',module_number=1,data=json.dumps(data),publisher_id=uid,created_at=now);s.add(v2);s.flush()
            s.add(PublishedLesson(lesson_id=lesson_id,revision_id=v1.id))
            a=Attempt(user_id=uid,lesson_id=lesson_id,answers=json.dumps({'q1':True}),finished=True);s.add(a);s.flush()
            s.add(AttemptContent(attempt_id=a.id,data=json.dumps(data),published_revision_id=v1.id))
            s.add(Progress(user_id=uid,lesson_id=lesson_id,best_score=100,completed=True));s.commit()
            v2_id=v2.id; draft_id=draft.id
        before=learner.get('/api/progress/overview').json()['courses'][0]
        assert before['available']==2 and before['completed']==1 and before['modules'][0]['completed']==1
        assert other.get('/api/progress/overview').json()['courses'][0]['completed']==0
        with Session(engine) as s:
            s.get(PublishedLesson,lesson_id).revision_id=v2_id;s.commit()
        status=learner.get('/api/progress').json()[0]
        assert not status['completed'] and status['revision_changed'] and status['best_score']==0
        assert learner.get('/api/progress/overview').json()['courses'][0]['completed']==0
        attempt=learner.post(f'/api/lessons/{lesson_id}/attempts').json()['id']
        assert learner.post(f'/api/attempts/{attempt}/answers',json={'exercise_id':'q1','response':'А'}).json()['correct']
        assert learner.post(f'/api/attempts/{attempt}/complete').json()['passed']
        status=learner.get('/api/progress').json()[0]
        assert status['completed'] and not status['revision_changed'] and status['best_score']==100
        with Session(engine) as s:
            republished=PublishedRevision(draft_id=draft_id,draft_version=2,lesson_id=lesson_id,course='uz-ru',module_number=1,data=json.dumps(data),publisher_id=uid,created_at=now);s.add(republished);s.flush()
            s.get(PublishedLesson,lesson_id).revision_id=republished.id;s.commit()
        assert learner.get('/api/progress').json()[0]['completed']
    Base.metadata.drop_all(engine)


def test_safety_block_stops_existing_attempts_reviews_and_media(tmp_path,monkeypatch):
    from sqlalchemy.orm import Session
    from app import main
    from app.main import EditorAccess, PublisherAccess
    monkeypatch.setattr(main,'MEDIA_ROOT',tmp_path)
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as author, TestClient(app) as publisher, TestClient(app) as learner, TestClient(app) as outsider:
        aid=author.post('/api/auth/register',json={'email':'safety-author@example.com','password':'longpassword'}).json()['id']
        pid=publisher.post('/api/auth/register',json={'email':'safety-publisher@example.com','password':'longpassword'}).json()['id']
        learner.post('/api/auth/register',json={'email':'safety-learner@example.com','password':'longpassword'})
        outsider.post('/api/auth/register',json={'email':'safety-other@example.com','password':'longpassword'})
        with Session(engine) as s:
            s.add_all([EditorAccess(user_id=aid),EditorAccess(user_id=pid),PublisherAccess(user_id=pid)]);s.commit()
        asset=author.post('/api/admin/media?attribution=Original',content=b'RIFF'+b'\0'*4+b'WAVEdata').json()['id']
        publisher.post('/api/admin/media/'+asset+'/reviews',json={'decision':'approved','notes':'Reviewed rights.'})
        content={'course':'uz-ru','title':'Test','objective':'Practice','minutes':8,'module_number':1,'words':[{'target':'А','meaning':'A','media_id':asset}],
                 'exercises':[{'id':'q1','type':'text','prompt':'One','answers':['А'],'explanation':'First'}, {'id':'q2','type':'text','prompt':'Two','answers':['Б'],'explanation':'Second'}]}
        draft=author.post('/api/admin/drafts',json=content).json(); path=f"/api/admin/drafts/{draft['id']}"
        publisher.post(path+'/reviews',json={'version':1,'decision':'approved','notes':'Reviewed.'})
        lesson_id=publisher.post(path+'/publish',json={'expected_version':1}).json()['lesson_id']
        attempt=learner.post(f'/api/lessons/{lesson_id}/attempts').json()['id']
        learner.post(f'/api/attempts/{attempt}/answers',json={'exercise_id':'q1','response':'wrong'})
        item=learner.get('/api/review?course=uz-ru').json()[0]['id']
        assert outsider.get('/api/media/'+asset).status_code==200
        assert author.post(path+'/safety-block',json={'reason':'Urgent issue'}).status_code==403
        assert publisher.post(path+'/safety-block',json={'reason':'Urgent issue'}).status_code==200
        assert publisher.get(path).json()['safety_blocked']
        assert all(x['id']!=lesson_id for x in learner.get('/api/courses/uz-ru/lessons').json())
        assert learner.get(f'/api/lessons/{lesson_id}').status_code==410
        assert learner.post(f'/api/lessons/{lesson_id}/attempts').status_code==410
        assert learner.post(f'/api/attempts/{attempt}/answers',json={'exercise_id':'q2','response':'Б'}).status_code==410
        assert learner.post(f'/api/attempts/{attempt}/complete').status_code==410
        assert learner.get(f'/api/attempts/{attempt}/results').status_code==410
        assert learner.get('/api/review?course=uz-ru').json()==[]
        assert learner.post(f'/api/review/{item}/answer',json={'response':'А'}).status_code==410
        assert not any(x['lesson_id']==lesson_id for x in learner.get('/api/continue').json())
        assert learner.get('/api/media/'+asset).status_code==404
        assert publisher.post(path+'/publish',json={'expected_version':1}).status_code==410
        assert author.post(path+'/safety-unblock',json={'reason':'Resolved'}).status_code==403
        assert publisher.post(path+'/safety-unblock',json={'reason':'Resolved'}).json()=={'blocked':False,'published':False}
        assert learner.post(f'/api/lessons/{lesson_id}/attempts').json()['id']==attempt
        assert outsider.post(f'/api/lessons/{lesson_id}/attempts').status_code==404
        assert learner.get('/api/media/'+asset).status_code==200 and outsider.get('/api/media/'+asset).status_code==404
        assert learner.post(f'/api/attempts/{attempt}/answers',json={'exercise_id':'q2','response':'Б'}).json()['correct']
        assert learner.post(f'/api/review/{item}/answer',json={'response':'А'}).json()['correct']
        history=publisher.get(path+'/publications').json()
        assert [x['action'] for x in history[:2]]==['unblocked','blocked']
    Base.metadata.drop_all(engine)


def test_pending_account_deletion_is_atomic_and_preserves_others(monkeypatch):
    import pytest
    from sqlalchemy import func,select
    from sqlalchemy.orm import Session
    from app import main
    from app.deletion import DeletionBlocked,deletion_plan,fulfill_deletion
    from app.main import AnalyticsEvent,AnswerReceipt,Attempt,AttemptContent,DeletionAudit,EditorAccess,Feedback,ReviewContent,ReviewItem,User
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    monkeypatch.setattr(main,'send_reset_email',lambda *_:None)
    with TestClient(app) as learner, TestClient(app) as other, TestClient(app) as editor:
        uid=learner.post('/api/auth/register',json={'email':'delete-me@example.com','password':'longpassword'}).json()['id']
        other_id=other.post('/api/auth/register',json={'email':'keep@example.com','password':'longpassword'}).json()['id']
        editor_id=editor.post('/api/auth/register',json={'email':'keep-editor@example.com','password':'longpassword'}).json()['id']
        learner.post('/api/onboarding',json={'course':'uz-ru','motivation':'study','daily_goal':10})
        attempt=learner.post('/api/lessons/uz-ru-greetings/attempts').json()['id']
        learner.post(f'/api/attempts/{attempt}/answers',json={'exercise_id':'g1','response':'wrong'})
        learner.post('/api/feedback',json={'lesson_id':'uz-ru-greetings','category':'content','message':'Check this.'})
        learner.post('/api/auth/password-reset/request',json={'email':'delete-me@example.com'})
        version=learner.get('/api/demo-checkpoint/uz-ru').json()['content_version']
        learner.post('/api/demo-checkpoint/uz-ru',json={'content_version':version,'responses':{'g1':'Привет','g2':'спасибо','g3':'До свидания'}})
        learner.post('/api/profile/deletion-request'); editor.post('/api/profile/deletion-request')
        with Session(engine) as s:
            s.add(EditorAccess(user_id=editor_id));s.commit()
        with Session(engine) as s:
            with pytest.raises(DeletionBlocked): deletion_plan(s,other_id)
            with pytest.raises(DeletionBlocked): fulfill_deletion(s,editor_id)
            _,counts=deletion_plan(s,uid)
            assert counts['attempts']==1 and counts['answer_receipts']==1 and counts['review_items']==1 and counts['feedback']==1 and counts['demo_checkpoint_results']==1
            pending=fulfill_deletion(s,uid);s.rollback()
        assert learner.get('/api/me').status_code==200
        with Session(engine) as s:
            completed=fulfill_deletion(s,uid);s.commit(); receipt=completed['receipt']
        assert learner.get('/api/me').status_code==401 and other.get('/api/me').status_code==200 and editor.get('/api/me').status_code==200
        with Session(engine) as s:
            assert s.get(User,uid) is None and s.get(User,other_id) is not None and s.get(User,editor_id) is not None
            assert s.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id==uid))==0
            assert s.scalar(select(func.count()).select_from(AnswerReceipt))==0
            assert s.scalar(select(func.count()).select_from(AttemptContent))==0
            assert s.scalar(select(func.count()).select_from(ReviewItem).where(ReviewItem.user_id==uid))==0
            assert s.scalar(select(func.count()).select_from(ReviewContent))==0
            assert s.scalar(select(func.count()).select_from(Feedback).where(Feedback.user_id==uid))==0
            assert s.scalar(select(func.count()).select_from(AnalyticsEvent).where(AnalyticsEvent.user_id==uid))==0
            audit=s.get(DeletionAudit,receipt)
            assert audit and 'delete-me@example.com' not in audit.counts and pending['receipt']!=receipt
    Base.metadata.drop_all(engine)


def test_default_local_origin_is_accepted_and_other_origins_rejected(monkeypatch):
    monkeypatch.delenv('WEB_ORIGIN',raising=False)
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as client:
        body={'email':'origin-test@example.com','password':'longpassword'}
        assert client.post('/api/auth/register',json=body,headers={'Origin':'http://127.0.0.1:5173'}).status_code==200
        assert client.post('/api/auth/logout',headers={'Origin':'https://untrusted.invalid'}).status_code==403
        assert client.get('/api/me').status_code==200
        assert client.post('/api/auth/logout',headers={'Origin':'http://127.0.0.1:5173'}).status_code==200
    Base.metadata.drop_all(engine)


def test_missed_exercises_are_retried_before_completion_and_keep_first_score():
    from datetime import datetime, timedelta, timezone
    from sqlalchemy.orm import Session
    from app.main import ReviewItem
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as learner, TestClient(app) as other:
        learner.post('/api/auth/register',json={'email':'retry-lesson@example.com','password':'longpassword'})
        other.post('/api/auth/register',json={'email':'retry-other@example.com','password':'longpassword'})
        a=learner.post('/api/lessons/uz-ru-greetings/attempts').json()['id']
        for question,response in [('g1','Привет'),('g2','wrong'),('g3','До свидания')]:
            learner.post(f'/api/attempts/{a}/answers',json={'exercise_id':question,'response':response})
        assert learner.post(f'/api/attempts/{a}/complete').status_code==409
        assert other.get(f'/api/attempts/{a}/remediation').status_code==404
        queue=learner.get(f'/api/attempts/{a}/remediation').json()
        assert [x['id'] for x in queue]==['g2'] and 'answers' not in queue[0]
        retry=f'/api/attempts/{a}/remediation/g2'
        assert not learner.post(retry,json={'response':'wrong again'}).json()['correct']
        assert learner.post(retry,json={'response':'спасибо'}).json()['correct']
        assert learner.post(retry,json={'response':'СПАСИБО'}).json()['correct']
        assert learner.get(f'/api/attempts/{a}/remediation').json()==[]
        assert learner.get('/api/review?course=uz-ru').json()==[]
        with Session(engine) as s:
            item=s.query(ReviewItem).filter_by(lesson_id='uz-ru-greetings',exercise_id='g2').one()
            delta=item.due_at-datetime.now(timezone.utc).replace(tzinfo=None)
            assert item.stage==1 and timedelta(hours=23)<delta<=timedelta(days=1)
        assert learner.post(f'/api/attempts/{a}/complete').json()=={'score':67,'passed':False}
        result=learner.get(f'/api/attempts/{a}/results').json()
        assert not result['exercises'][1]['correct']
    Base.metadata.drop_all(engine)


def test_private_original_lesson_templates_are_traceable_and_unpublished(tmp_path,monkeypatch):
    import hashlib,json,shutil
    from sqlalchemy.orm import Session
    from app import main
    from app.main import EditorAccess, DraftContent, answer_matches, validate_draft, public_lesson
    source=main.LESSON_TEMPLATE_ROOT
    for path in source.glob('*.json'): shutil.copy(path,tmp_path/path.name)
    monkeypatch.setattr(main,'LESSON_TEMPLATE_ROOT',tmp_path)
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as editor, TestClient(app) as learner:
        uid=editor.post('/api/auth/register',json={'email':'templates-editor@example.com','password':'longpassword'}).json()['id']
        learner.post('/api/auth/register',json={'email':'templates-learner@example.com','password':'longpassword'})
        with Session(engine) as s:
            s.add(EditorAccess(user_id=uid));s.commit()
        assert learner.get('/api/admin/lesson-templates').status_code==403
        entries=editor.get('/api/admin/lesson-templates').json()
        assert len(entries)==len(list(tmp_path.glob('*.json'))) and len(entries)>=32 and all(x['status']=='draft_unreviewed' for x in entries)
        for entry in entries:
            template=editor.get('/api/admin/lesson-templates/'+entry['id']).json()
            content=DraftContent.model_validate(template['content'])
            with Session(engine) as s: validate_draft(content,s)
            assert content.outline_ref is not None
            main.verify_outline_ref(content)
            for exercise in content.model_dump()['exercises']:
                response=json.dumps({p['left']:p['right'] for p in exercise['match_pairs']},ensure_ascii=False) if exercise['type']=='match' else exercise['answers'][0]
                assert answer_matches(exercise,response)
            assert len(learner.get('/api/courses/'+content.course+'/lessons').json())==1
        entry=entries[0];template=editor.get('/api/admin/lesson-templates/'+entry['id']).json()
        payload={**template['content'],'template_ref':{'template_id':entry['id'],'source_sha256':entry['source_sha256']}}
        draft=editor.post('/api/admin/drafts',json=payload)
        assert draft.status_code==200 and draft.json()['content']['template_ref']['template_id']==entry['id']
        assert 'template_ref' not in public_lesson('example',draft.json()['content'])
        path=tmp_path/(entry['id']+'.json');path.write_text(path.read_text(encoding='utf-8')+' ',encoding='utf-8')
        assert hashlib.sha256(path.read_bytes()).hexdigest()!=entry['source_sha256']
        assert editor.post('/api/admin/drafts',json=payload).status_code==409
        assert editor.get('/api/admin/lesson-templates/invalid').status_code==404
    Base.metadata.drop_all(engine)


def test_local_preview_lessons_are_playable_and_clearly_separate(monkeypatch):
    from app import main
    previews=main.load_local_preview_lessons()
    assert len(previews)>=32
    for lesson_id, content in previews.items():
        monkeypatch.setitem(main.LESSONS,lesson_id,content)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as client:
        client.post('/api/auth/register',json={'email':'preview@example.com','password':'longpassword'})
        for course in ('uz-ru','ru-uz'):
            lessons=client.get(f'/api/courses/{course}/lessons').json()
            assert len(lessons)==1+sum(content['course']==course for content in previews.values()) and all(item['demo'] for item in lessons)
            modules=client.get(f'/api/courses/{course}/modules').json()
            assert len(modules[0]['lessons'])==sum(content['course']==course and content['module_number']==1 for content in previews.values()) and modules[0]['status']=='demo'
            preview=client.get('/api/lessons/'+lessons[0]['id']).json()
            assert 'outline_ref' not in preview
            assert all('answers' not in exercise for exercise in preview['exercises'])
            attempt=client.post('/api/lessons/'+lessons[0]['id']+'/attempts')
            assert attempt.status_code==200
            sample=client.post('/api/lessons/preview-'+course+'-03-02/attempts').json()
            attempt_id=sample['id']
            dialogue='Привет!' if course=='uz-ru' else 'Salom!'
            order='Меня зовут Аня' if course=='uz-ru' else 'Mening ismim Anya'
            ending='Xayr!' if course=='uz-ru' else 'До свидания!'
            for question,response in [('q1',dialogue),('q2',order),('q3',ending)]:
                assert client.post(f'/api/attempts/{attempt_id}/answers',json={'exercise_id':question,'response':response}).json()['correct']
            assert client.post(f'/api/attempts/{attempt_id}/complete').json()['passed']
    Base.metadata.drop_all(engine)


def test_reset_email_capability_reports_configuration(monkeypatch):
    monkeypatch.delenv('SMTP_HOST',raising=False)
    monkeypatch.delenv('SMTP_FROM',raising=False)
    with TestClient(app) as client:
        assert client.get('/api/capabilities').json()['password_reset_email'] is False
        monkeypatch.setenv('SMTP_HOST','smtp.example.test')
        assert client.get('/api/capabilities').json()['password_reset_email'] is False
        monkeypatch.setenv('SMTP_FROM','noreply@example.test')
        assert client.get('/api/capabilities').json()['password_reset_email'] is True


def test_guest_preview_is_limited_and_checks_both_directions():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as client:
        for course,answer in [('uz-ru','Привет'),('ru-uz','Salom')]:
            preview=client.get('/api/preview/'+course)
            assert preview.status_code==200
            exercise=preview.json()['exercise']
            assert 'answers' not in exercise and 'explanation' not in exercise
            wrong=client.post('/api/preview/'+course+'/answer',json={'exercise_id':exercise['id'],'response':'wrong'})
            assert wrong.status_code==200 and not wrong.json()['correct']
            correct=client.post('/api/preview/'+course+'/answer',json={'exercise_id':exercise['id'],'response':answer})
            assert correct.status_code==200 and correct.json()['correct']
            assert client.post('/api/preview/'+course+'/answer',json={'exercise_id':'g2','response':answer}).status_code==404
        assert client.get('/api/progress').status_code==401
    Base.metadata.drop_all(engine)


def test_guest_preview_feedback_is_anonymous_and_visible_only_to_editors():
    from sqlalchemy.orm import Session
    from app.main import EditorAccess,Feedback
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    with TestClient(app) as guest, TestClient(app) as editor:
        payload={'lesson_id':'uz-ru-greetings','category':'content','message':'Please explain the greeting.'}
        assert guest.post('/api/preview/ru-uz/feedback',json=payload).status_code==404
        result=guest.post('/api/preview/uz-ru/feedback',json=payload)
        assert result.status_code==200
        with Session(engine) as s: assert s.get(Feedback,result.json()['id']).user_id is None
        assert guest.get('/api/admin/feedback').status_code==401
        uid=editor.post('/api/auth/register',json={'email':'guest-feedback-editor@example.com','password':'longpassword'}).json()['id']
        with Session(engine) as s: s.add(EditorAccess(user_id=uid));s.commit()
        assert editor.get('/api/admin/feedback').json()[0]['message']==payload['message']
    Base.metadata.drop_all(engine)


def test_demo_checkpoint_checks_and_privately_saves_scores():
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    with TestClient(app) as learner, TestClient(app) as guest:
        assert guest.get('/api/demo-checkpoint/uz-ru').status_code==401
        learner.post('/api/auth/register',json={'email':'checkpoint@example.com','password':'longpassword'})
        for course,answers in [('uz-ru',{'g1':'Привет','g2':'спасибо','g3':'До свидания'}),('ru-uz',{'g1':'Salom','g2':'rahmat','g3':'Assalomu alaykum'})]:
            loaded=learner.get('/api/demo-checkpoint/'+course).json();questions=loaded['exercises'];version=loaded['content_version']
            assert len(questions)==3 and all('answers' not in q for q in questions)
            assert learner.post('/api/demo-checkpoint/'+course,json={'content_version':version,'responses':{'g1':'x'}}).status_code==422
            result=learner.post('/api/demo-checkpoint/'+course,json={'content_version':version,'responses':answers}).json()
            assert result['score']==100 and all(r['correct'] for r in result['results'])
            answers['g1']='wrong'
            result=learner.post('/api/demo-checkpoint/'+course,json={'content_version':version,'responses':answers}).json()
            assert result['score']==67 and not result['results'][0]['correct']
        assert learner.get('/api/progress').json()==[]
        assert [item['score'] for item in learner.get('/api/demo-checkpoint/uz-ru/history').json()]==[67,100]
        assert guest.get('/api/demo-checkpoint/uz-ru/history').status_code==401
    Base.metadata.drop_all(engine)


def test_alphabet_samples_enforce_requested_letter_case():
    from app.main import load_local_preview_lessons,answer_matches
    lessons=load_local_preview_lessons()
    for lesson_id,exercise_id in [('preview-uz-ru-01-02','q3'),('preview-uz-ru-02-01','q1'),('preview-uz-ru-02-01','q2'),('preview-uz-ru-02-01','q3'),('preview-uz-ru-02-01','q4')]:
        exercise=next(e for e in lessons[lesson_id]['exercises'] if e['id']==exercise_id)
        answer=exercise['answers'][0]
        assert answer_matches(exercise,answer)
        assert not answer_matches(exercise,answer.swapcase())


def test_local_feedback_report_lists_open_reports_without_user_ids(tmp_path):
    import json,os,subprocess,sys
    from datetime import datetime
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.main import Feedback,User
    path=tmp_path/'feedback.db'
    test_engine=create_engine('sqlite:///'+str(path))
    Base.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        user=User(email='private@example.com',password_hash='unused',name='Private')
        session.add(user);session.flush()
        session.add_all([Feedback(user_id=user.id,lesson_id='uz-ru-greetings',category='content',message='Needs context',status='open',created_at=datetime(2026,1,1)),Feedback(user_id=None,lesson_id='ru-uz-greetings',category='other',message='Resolved',status='resolved',created_at=datetime(2026,1,2))]);session.commit()
    env={**os.environ,'DATABASE_URL':'sqlite:///'+str(path),'PYTHONPATH':'.'}
    result=subprocess.run([sys.executable,'-m','scripts.list_feedback'],env=env,text=True,capture_output=True,check=True)
    records=[json.loads(line) for line in result.stdout.splitlines()]
    assert len(records)==1 and records[0]['message']=='Needs context'
    assert 'private@example.com' not in result.stdout and 'user_id' not in records[0]
    result=subprocess.run([sys.executable,'-m','scripts.list_feedback','--status','all'],env=env,text=True,capture_output=True,check=True)
    assert len(result.stdout.splitlines())==2
    test_engine.dispose()


def test_module_practice_covers_demo_modules_and_saves_private_results(monkeypatch):
    from app import main
    for lesson_id,content in main.load_local_preview_lessons().items(): monkeypatch.setitem(main.LESSONS,lesson_id,content)
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    with TestClient(app) as client, TestClient(app) as guest:
        assert guest.get('/api/demo-module/uz-ru/1').status_code==401
        client.post('/api/auth/register',json={'email':'modules@example.com','password':'longpassword'})
        for course in ('uz-ru','ru-uz'):
            for module in range(1,11):
                result=client.get(f'/api/demo-module/{course}/{module}')
                assert result.status_code==200
                public=result.json()['exercises']
                assert 3<=len(public)<=10 and any(e['type']=='text' for e in public) and all('answers' not in e for e in public)
                assert any(e['type']=='listen_choice' and e.get('audio_src') for e in public)
                expected={key for key,lesson in main.LESSONS.items() if lesson['course']==course and lesson.get('module_number',3)==module}
                assert {e['practice_lesson_id'] for e in public if 'practice_lesson_id' in e}==expected
                with main.Session(engine) as session: _,exercises=main.module_demo_exercises(course,module,session)
                answers={e['id']:e['answers'][0] for e in exercises}
                assert client.post(f'/api/demo-module/{course}/{module}',json={'content_version':result.json()['content_version'],'responses':answers}).json()['score']==100
            assert len(client.get(f'/api/demo-module/{course}/4').json()['exercises'])>3
        assert client.get('/api/demo-module/uz-ru/11').status_code==404
        assert len(client.get('/api/demo-checkpoint/uz-ru/history').json())==1
        overview=client.get('/api/progress/overview').json()
        for course in overview['courses']:
            assert all(module['practice']['score']==100 for module in course['modules'])
        assert guest.get('/api/progress/overview').status_code==401
    Base.metadata.drop_all(engine)


def test_course_practice_checks_ten_topics_listening_and_dialogue_and_is_private(monkeypatch):
    from app import main
    for lesson_id,content in main.load_local_preview_lessons().items(): monkeypatch.setitem(main.LESSONS,lesson_id,content)
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    with TestClient(app) as client, TestClient(app) as other:
        assert other.get('/api/demo-course/uz-ru').status_code==401
        client.post('/api/auth/register',json={'email':'course-practice@example.com','password':'longpassword'})
        other.post('/api/auth/register',json={'email':'course-other@example.com','password':'longpassword'})
        for course in ('uz-ru','ru-uz'):
            loaded=client.get('/api/demo-course/'+course).json();public=loaded['exercises'];version=loaded['content_version']
            assert len(public)==12 and all('answers' not in e for e in public)
            assert any(e['type']=='listen_choice' and e.get('audio_src') for e in public)
            assert any(e['id']=='sample-dialogue' and e['type']=='text' for e in public)
            with main.Session(engine) as session: exercises=main.course_demo_exercises(course,session)
            assert any(e['type']=='text' for e in exercises)
            answers={e['id']:e['answers'][0] for e in exercises}
            assert client.post('/api/demo-course/'+course,json={'content_version':version,'responses':{'wrong':'x'}}).status_code==422
            assert client.post('/api/demo-course/'+course,json={'content_version':'0'*64,'responses':answers}).status_code==409
            assert client.post('/api/demo-course/'+course,json={'content_version':version,'responses':answers}).json()['score']==100
        for course in client.get('/api/progress/overview').json()['courses']: assert course['course_practice']['score']==100
        assert all(course['course_practice'] is None for course in other.get('/api/progress/overview').json()['courses'])
    Base.metadata.drop_all(engine)


def test_new_vocabulary_samples_include_written_recall():
    from app.main import load_local_preview_lessons,answer_matches
    lessons=load_local_preview_lessons()
    for course in ('uz-ru','ru-uz'):
        for module,number in ((4,4),(6,3),(7,2),(8,2),(10,2)):
            lesson=lessons[f'preview-{course}-{module:02}-{number:02}']
            exercise=next(e for e in lesson['exercises'] if e['id']=='q3')
            assert exercise['type']=='text' and answer_matches(exercise,exercise['answers'][0])
            if module==8: assert answer_matches(exercise,exercise['answers'][0].rstrip('?'))


def test_backup_refuses_existing_file_and_non_postgres(tmp_path):
    import os,subprocess,sys
    output=tmp_path/'archive.dump';output.write_bytes(b'existing')
    env={**os.environ,'DATABASE_URL':'postgresql+psycopg://tester:secret@localhost/test','PYTHONPATH':'.'}
    result=subprocess.run([sys.executable,'-m','scripts.backup_database',str(output)],env=env,text=True,capture_output=True)
    assert result.returncode!=0 and output.read_bytes()==b'existing'
    assert 'secret' not in result.stdout+result.stderr
    env['DATABASE_URL']='sqlite:///ignored.db'
    result=subprocess.run([sys.executable,'-m','scripts.backup_database',str(tmp_path/'other.dump')],env=env,text=True,capture_output=True)
    assert result.returncode!=0 and not (tmp_path/'other.dump').exists()


def test_built_frontend_mount_preserves_api_and_serves_only_bundle(tmp_path):
    import os,subprocess,sys
    bundle=tmp_path/'bundle';bundle.mkdir();(bundle/'index.html').write_text('<h1>Bundle fixture</h1>')
    assets=bundle/'assets';assets.mkdir();(assets/'app.js').write_text('/* bundle */')
    env={**os.environ,'PYTHONPATH':'.','DATABASE_URL':'sqlite:///'+str(tmp_path/'unused.db'),
         'SERVE_BUILT_FRONTEND':'true','FRONTEND_DIST':str(bundle),'ENABLE_DEMO_CONTENT':'false'}
    check='''from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as client:
    assert 'Bundle fixture' in client.get('/').text
    assert client.get('/assets/app.js').status_code==200
    assert client.get('/api/health').json()['status']=='ok'
    assert client.get('/app/main.py').status_code==404
    assert client.get('/api/not-a-route').status_code==404
'''
    result=subprocess.run([sys.executable,'-c',check],env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    env['FRONTEND_DIST']=str(tmp_path/'missing')
    result=subprocess.run([sys.executable,'-c','import app.main'],env=env,capture_output=True,text=True)
    assert result.returncode!=0 and 'Built frontend not found' in result.stderr


def test_practice_progress_distinguishes_changed_and_legacy_content(monkeypatch):
    import copy
    from datetime import datetime
    from app import main
    for lesson_id,content in main.load_local_preview_lessons().items(): monkeypatch.setitem(main.LESSONS,lesson_id,content)
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    with TestClient(app) as client:
        uid=client.post('/api/auth/register',json={'email':'versions@example.com','password':'longpassword'}).json()['id']
        module=client.get('/api/demo-module/uz-ru/5').json()
        with main.Session(engine) as s: answers={e['id']:e['answers'][0] for e in main.module_demo_exercises('uz-ru',5,s)[1]}
        assert client.post('/api/demo-module/uz-ru/5',json={'content_version':module['content_version'],'responses':answers}).status_code==200
        course=client.get('/api/demo-course/uz-ru').json()
        with main.Session(engine) as s: answers={e['id']:e['answers'][0] for e in main.course_demo_exercises('uz-ru',s)}
        assert client.post('/api/demo-course/uz-ru',json={'content_version':course['content_version'],'responses':answers}).status_code==200
        def state(): return client.get('/api/progress/overview').json()['courses'][0]
        assert state()['modules'][4]['practice']['version_status']=='current'
        assert state()['course_practice']['version_status']=='current'
        changed=copy.deepcopy(main.LESSONS['preview-uz-ru-05-01']);changed['exercises'][2]['explanation']='Updated explanation'
        monkeypatch.setitem(main.LESSONS,'preview-uz-ru-05-01',changed)
        assert state()['modules'][4]['practice']['version_status']=='changed'
        assert state()['course_practice']['version_status']=='changed'
        with main.Session(engine) as s:
            s.add(main.DemoCheckpointResult(user_id=uid,course='uz-ru',module_number=5,score=67,created_at=datetime(2100,1,1)));s.commit()
        assert state()['modules'][4]['practice']['version_status']=='unknown'
    Base.metadata.drop_all(engine)


def test_feedback_rating_is_optional_bounded_and_visible_to_editor():
    from sqlalchemy.orm import Session
    from app.main import EditorAccess
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    with TestClient(app) as learner,TestClient(app) as editor,TestClient(app) as guest:
        learner.post('/api/auth/register',json={'email':'rating-learner@example.com','password':'longpassword'})
        editor_id=editor.post('/api/auth/register',json={'email':'rating-editor@example.com','password':'longpassword'}).json()['id']
        with Session(engine) as s:s.add(EditorAccess(user_id=editor_id));s.commit()
        payload={'lesson_id':'uz-ru-greetings','category':'content'}
        assert learner.post('/api/feedback',json=payload).status_code==422
        for invalid in (0,6,True): assert learner.post('/api/feedback',json={**payload,'clarity_rating':invalid}).status_code==422
        rated=learner.post('/api/feedback',json={**payload,'clarity_rating':4})
        assert rated.status_code==200
        anonymous=guest.post('/api/preview/uz-ru/feedback',json={**payload,'clarity_rating':5})
        assert anonymous.status_code==200
        reports=editor.get('/api/admin/feedback').json()
        assert {r['clarity_rating'] for r in reports}=={4,5} and all(r['message']=='' for r in reports)
        assert all('user_id' not in r for r in reports)
    Base.metadata.drop_all(engine)


def test_editor_feedback_pagination_reaches_older_open_reports():
    from datetime import datetime
    from sqlalchemy.orm import Session
    from app.main import EditorAccess,Feedback
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    with TestClient(app) as editor,TestClient(app) as guest:
        uid=editor.post('/api/auth/register',json={'email':'feedback-pages@example.com','password':'longpassword'}).json()['id']
        with Session(engine) as s:
            s.add(EditorAccess(user_id=uid))
            s.add(Feedback(user_id=None,lesson_id='uz-ru-greetings',category='content',message='old open',status='open',created_at=datetime(2025,1,1)))
            s.add_all([Feedback(user_id=None,lesson_id='uz-ru-greetings',category='content',message=f'new {i}',status='resolved',created_at=datetime(2026,1,1)) for i in range(205)])
            s.commit()
        assert guest.get('/api/admin/feedback?status=open').status_code==401
        assert editor.get('/api/admin/feedback?status=open').json()[0]['message']=='old open'
        first=editor.get('/api/admin/feedback?status=resolved&limit=50&offset=0').json()
        second=editor.get('/api/admin/feedback?status=resolved&limit=50&offset=50').json()
        assert len(first)==len(second)==50 and not ({r['id'] for r in first}&{r['id'] for r in second})
        assert editor.get('/api/admin/feedback?limit=201').status_code==422
        assert editor.get('/api/admin/feedback?offset=-1').status_code==422
        assert editor.get('/api/admin/feedback?status=unknown').status_code==422
    Base.metadata.drop_all(engine)


def test_feedback_summary_is_private_and_counts_ratings_not_people():
    from datetime import datetime
    from sqlalchemy.orm import Session
    from app.main import EditorAccess,Feedback
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    with TestClient(app) as editor,TestClient(app) as learner,TestClient(app) as guest:
        uid=editor.post('/api/auth/register',json={'email':'summary-editor@example.com','password':'longpassword'}).json()['id']
        learner.post('/api/auth/register',json={'email':'summary-learner@example.com','password':'longpassword'})
        assert guest.get('/api/admin/feedback-summary').status_code==401
        assert learner.get('/api/admin/feedback-summary').status_code==403
        with Session(engine) as s:s.add(EditorAccess(user_id=uid));s.commit()
        assert editor.get('/api/admin/feedback-summary').json()=={'reports':0,'ratings':0,'average_clarity':None,'open_reports':0}
        with Session(engine) as s:
            for status,rating in [('open',5),('resolved',3),('open',None)]:
                s.add(Feedback(user_id=None,lesson_id='uz-ru-greetings',category='content',message='x',status=status,clarity_rating=rating,created_at=datetime(2026,1,1)))
            s.commit()
        assert editor.get('/api/admin/feedback-summary').json()=={'reports':3,'ratings':2,'average_clarity':4.0,'open_reports':2}
    Base.metadata.drop_all(engine)


def test_draft_examples_require_translation_and_remain_in_learner_view():
    from sqlalchemy.orm import Session
    from app.main import EditorAccess,public_lesson
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    with TestClient(app) as editor:
        uid=editor.post('/api/auth/register',json={'email':'examples-editor@example.com','password':'longpassword'}).json()['id']
        with Session(engine) as s:s.add(EditorAccess(user_id=uid));s.commit()
        content={'course':'uz-ru','title':'Example','objective':'Practice','minutes':5,
                 'words':[{'target':'читать','meaning':'o‘qimoq','example':'Я читаю.','example_translation':'Men o‘qiyman.'}],
                 'exercises':[{'id':'q1','type':'text','prompt':'Write','answers':['читать'],'explanation':'Practice.'}]}
        bad={**content,'words':[{'target':'читать','meaning':'o‘qimoq','example':'Я читаю.'}]}
        assert editor.post('/api/admin/drafts',json=bad).status_code==422
        saved=editor.post('/api/admin/drafts',json=content)
        assert saved.status_code==200
        word=public_lesson('example',saved.json()['content'])['words'][0]
        assert word['example']=='Я читаю.' and word['example_translation']=='Men o‘qiyman.'
        assert editor.get('/api/lessons/uz-ru-greetings').json()['words'][0]['example']
    Base.metadata.drop_all(engine)


def test_feedback_captures_owned_attempt_question_context():
    from sqlalchemy.orm import Session
    from app.main import EditorAccess,Feedback,AttemptContent
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    with TestClient(app) as learner,TestClient(app) as other,TestClient(app) as editor,TestClient(app) as guest:
        learner.post('/api/auth/register',json={'email':'context-learner@example.com','password':'longpassword'})
        other.post('/api/auth/register',json={'email':'context-other@example.com','password':'longpassword'})
        editor_id=editor.post('/api/auth/register',json={'email':'context-editor@example.com','password':'longpassword'}).json()['id']
        with Session(engine) as session:session.add(EditorAccess(user_id=editor_id));session.commit()
        attempt=learner.post('/api/lessons/uz-ru-greetings/attempts').json()['id']
        payload={'lesson_id':'uz-ru-greetings','attempt_id':attempt,'exercise_id':'g1','category':'content','message':'Please clarify'}
        assert other.post('/api/feedback',json=payload).status_code==404
        assert learner.post('/api/feedback',json={**payload,'exercise_id':'not-an-exercise'}).status_code==422
        response=learner.post('/api/feedback',json=payload)
        assert response.status_code==200
        with Session(engine) as session:
            report=session.get(Feedback,response.json()['id']);snapshot=session.get(AttemptContent,attempt)
            assert report.lesson_title=='Salomlashuv' and report.exercise_prompt=='Do‘stingizga qanday salom berasiz?'
            assert snapshot is not None
        listed=next(r for r in editor.get('/api/admin/feedback').json() if r['id']==response.json()['id'])
        assert listed['exercise_id']=='g1' and listed['exercise_prompt']=='Do‘stingizga qanday salom berasiz?'
        assert 'user_id' not in listed
        guest_payload={'lesson_id':'uz-ru-greetings','exercise_id':'g1','category':'content','clarity_rating':5}
        assert guest.post('/api/preview/uz-ru/feedback',json={**guest_payload,'exercise_id':'g2'}).status_code==404
        assert guest.post('/api/preview/uz-ru/feedback',json={**guest_payload,'attempt_id':attempt}).status_code==404
        assert guest.post('/api/preview/uz-ru/feedback',json=guest_payload).status_code==200
    Base.metadata.drop_all(engine)


def test_owner_dashboard_requires_explicit_owner_access():
    from sqlalchemy.orm import Session
    from app.main import OwnerAccess, EditorAccess
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as guest, TestClient(app) as owner, TestClient(app) as editor:
        assert guest.get('/api/owner/overview').status_code == 401
        owner_id=owner.post('/api/auth/register',json={'email':'owner-test@example.com','password':'longpassword'}).json()['id']
        editor_id=editor.post('/api/auth/register',json={'email':'editor-test@example.com','password':'longpassword'}).json()['id']
        with Session(engine) as session:
            session.add_all([OwnerAccess(user_id=owner_id),EditorAccess(user_id=editor_id)])
            session.commit()
        assert editor.get('/api/owner/overview').status_code == 403
        result=owner.get('/api/owner/overview')
        assert result.status_code == 200
        assert result.json()['accounts'] == 2
        assert result.json()['feedback_total'] == 0
        assert result.json()['average_clarity'] is None
    Base.metadata.drop_all(engine)


def test_owner_password_change_checks_current_password_and_revokes_other_sessions():
    from sqlalchemy.orm import Session
    from app.main import OwnerAccess
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as first, TestClient(app) as second, TestClient(app) as learner:
        owner_id=first.post('/api/auth/register',json={'email':'owner-password@example.com','password':'old-password'}).json()['id']
        with Session(engine) as session:
            session.add(OwnerAccess(user_id=owner_id)); session.commit()
        assert second.post('/api/auth/login',json={'email':'owner-password@example.com','password':'old-password'}).status_code==200
        learner.post('/api/auth/register',json={'email':'password-learner@example.com','password':'longpassword'})
        payload={'current_password':'old-password','new_password':'new-password'}
        assert learner.post('/api/owner/password',json=payload).status_code==403
        assert first.post('/api/owner/password',json=payload,headers={'Origin':'https://evil.example'}).status_code==403
        assert first.post('/api/owner/password',json={**payload,'current_password':'wrong'}).status_code==400
        assert first.post('/api/owner/password',json=payload).status_code==200
        assert first.get('/api/owner/overview').status_code==200
        assert second.get('/api/owner/overview').status_code==401
        assert second.post('/api/auth/login',json={'email':'owner-password@example.com','password':'old-password'}).status_code==401
        assert second.post('/api/auth/login',json={'email':'owner-password@example.com','password':'new-password'}).status_code==200
    Base.metadata.drop_all(engine)


def test_owner_account_management_and_requested_deletion():
    from sqlalchemy.orm import Session
    from app.main import OwnerAccess,EditorAccess,User
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as owner, TestClient(app) as learner, TestClient(app) as editor:
        owner_id=owner.post('/api/auth/register',json={'email':'management-owner@example.com','password':'longpassword'}).json()['id']
        learner_id=learner.post('/api/auth/register',json={'email':'management-learner@example.com','password':'longpassword'}).json()['id']
        editor_id=editor.post('/api/auth/register',json={'email':'management-editor@example.com','password':'longpassword'}).json()['id']
        with Session(engine) as s:
            s.add_all([OwnerAccess(user_id=owner_id),EditorAccess(user_id=owner_id),EditorAccess(user_id=editor_id)]);s.commit()
        assert learner.get('/api/owner/accounts').status_code==403
        assert editor.get('/api/owner/deletion-requests').status_code==403
        result=owner.get('/api/owner/accounts',params={'query':'management-learner'}).json()
        assert [a['id'] for a in result['accounts']]==[learner_id]
        assert owner.patch(f'/api/owner/accounts/{learner_id}/editor',json={'enabled':True},headers={'Origin':'https://evil.example'}).status_code==403
        assert owner.patch(f'/api/owner/accounts/{learner_id}/editor',json={'enabled':True}).json()=={'editor':True}
        assert editor.patch(f'/api/owner/accounts/{learner_id}/publisher',json={'enabled':True}).status_code==403
        assert owner.patch(f'/api/owner/accounts/{learner_id}/publisher',json={'enabled':True}).json()=={'publisher':True}
        assert owner.patch(f'/api/owner/accounts/{learner_id}/editor',json={'enabled':False}).status_code==409
        assert owner.patch(f'/api/owner/accounts/{learner_id}/publisher',json={'enabled':False}).json()=={'publisher':False}
        assert owner.patch(f'/api/owner/accounts/{owner_id}/editor',json={'enabled':False}).status_code==409
        learner.post('/api/profile/deletion-request')
        assert owner.get(f'/api/owner/deletion-requests/{learner_id}').status_code==409
        assert owner.patch(f'/api/owner/accounts/{learner_id}/editor',json={'enabled':False}).status_code==200
        assert [r['user_id'] for r in owner.get('/api/owner/deletion-requests').json()['requests']]==[learner_id]
        assert owner.get('/api/owner/deletion-requests?limit=1&offset=1').json()=={'requests':[],'more':False}
        assert owner.get(f'/api/owner/deletion-requests/{learner_id}').json()['counts']['deletion_request']==1
        assert owner.post(f'/api/owner/deletion-requests/{learner_id}/fulfill',json={'confirm':'NO'}).status_code==422
        assert owner.post(f'/api/owner/deletion-requests/{learner_id}/fulfill',json={'confirm':'DELETE'},headers={'Origin':'https://evil.example'}).status_code==403
        assert owner.post(f'/api/owner/deletion-requests/{learner_id}/fulfill',json={'confirm':'DELETE'}).json()['status']=='deleted'
        with Session(engine) as s: assert s.get(User,learner_id) is None and s.get(User,editor_id) is not None
        events=owner.get('/api/owner/role-events').json()['events']
        assert len(events)==4 and all(event['target_id'] is None for event in events)
        assert [event['role'] for event in events]==['editor','publisher','publisher','editor']
        assert owner.get('/api/owner/deletion-requests').json()=={'requests':[],'more':False}
    Base.metadata.drop_all(engine)


def test_owner_deletion_request_pagination():
    from datetime import datetime
    from sqlalchemy.orm import Session
    from app.main import OwnerAccess,User,DeletionRequest
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as owner:
        owner_id=owner.post('/api/auth/register',json={'email':'page-owner@example.com','password':'longpassword'}).json()['id']
        with Session(engine) as s:
            s.add(OwnerAccess(user_id=owner_id))
            for i in range(3):
                a=User(email=f'page-{i}@example.com',password_hash='unused',name=f'Page {i}',course='uz-ru');s.add(a);s.flush()
                s.add(DeletionRequest(user_id=a.id,created_at=datetime(2026,1,i+1),status='pending'))
            s.commit()
        first=owner.get('/api/owner/deletion-requests?limit=2').json()
        second=owner.get('/api/owner/deletion-requests?limit=2&offset=2').json()
        assert [r['name'] for r in first['requests']]==['Page 0','Page 1'] and first['more']
        assert [r['name'] for r in second['requests']]==['Page 2'] and not second['more']
    Base.metadata.drop_all(engine)


def test_teaching_note_is_preserved_in_attempt_snapshot(monkeypatch):
    import copy
    from app import main
    lesson_id='preview-uz-ru-04-01'
    original=main.load_local_preview_lessons()[lesson_id]
    monkeypatch.setitem(main.LESSONS,lesson_id,original)
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    with TestClient(app) as client:
        client.post('/api/auth/register',json={'email':'note-snapshot@example.com','password':'longpassword'})
        started=client.post('/api/lessons/'+lesson_id+'/attempts').json()
        note=started['lesson']['teaching_note'];assert note and 'Что это?' in note
        changed=copy.deepcopy(original);changed['teaching_note']='Changed after attempt started.'
        monkeypatch.setitem(main.LESSONS,lesson_id,changed)
        assert client.get('/api/lessons/'+lesson_id).json()['teaching_note']=='Changed after attempt started.'
        resumed=client.post('/api/lessons/'+lesson_id+'/attempts').json()
        assert resumed['id']==started['id'] and resumed['lesson']['teaching_note']==note
    Base.metadata.drop_all(engine)


def test_demo_typed_answers_accept_optional_final_punctuation():
    from app.main import load_local_preview_lessons,answer_matches,LESSONS,sample_dialogue_exercise
    previews=load_local_preview_lessons()
    for lesson_id in ('preview-uz-ru-04-05','preview-ru-uz-04-03'):
        exercise=next(e for e in previews[lesson_id]['exercises'] if e['type']=='text')
        expected=exercise['answers'][0]
        assert answer_matches(exercise,expected.rstrip('.!?'))
        assert answer_matches(exercise,expected.rstrip('.!?')+'!')
        assert not answer_matches(exercise,expected.rstrip('.!?')+' other')
    for course in ('uz-ru','ru-uz'):
        assert answer_matches(LESSONS[course+'-greetings']['exercises'][1],LESSONS[course+'-greetings']['exercises'][1]['answers'][0]+'.')
        dialogue=sample_dialogue_exercise(course)
        assert answer_matches(dialogue,dialogue['answers'][0]+'.')
    sensitive=next(e for e in previews['preview-uz-ru-01-01']['exercises'] if e['id']=='q3')
    assert not answer_matches(sensitive,sensitive['answers'][0].swapcase())


def test_readiness_reports_database_outage_without_details(monkeypatch):
    from sqlalchemy.exc import OperationalError
    from app import main
    with TestClient(app) as client:
        assert client.get('/api/ready').json()=={'status':'ready'}
        def unavailable():
            raise OperationalError('SELECT 1',{},Exception('private database details'))
        monkeypatch.setattr(main.engine,'connect',unavailable)
        response=client.get('/api/ready')
        assert response.status_code==503
        assert response.json()=={'detail':'Database unavailable'}
