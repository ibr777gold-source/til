"""Create and delete one isolated test account against a dedicated PostgreSQL DB."""
import os
from uuid import uuid4
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.main import app, engine, User, DeletionAudit
from app.deletion import deletion_plan, fulfill_deletion

url=make_url(os.environ['DATABASE_URL'])
if url.get_backend_name()!='postgresql' or url.database!='til_test':
    raise SystemExit('Use a dedicated PostgreSQL database named til_test.')
with TestClient(app) as learner, TestClient(app) as other:
    def signup(client):
        result=client.post('/api/auth/register',json={'email':f'{uuid4().hex}@example.com','password':'longpassword'})
        assert result.status_code==200,result.text
        return result.json()['id']
    uid=signup(learner); other_id=signup(other)
    assert learner.post('/api/onboarding',json={'course':'uz-ru','motivation':'daily','daily_goal':None}).status_code==200
    attempt=learner.post('/api/lessons/uz-ru-greetings/attempts').json()['id']
    assert not learner.post(f'/api/attempts/{attempt}/answers',json={'exercise_id':'g1','response':'wrong'}).json()['correct']
    assert learner.post('/api/profile/deletion-request').status_code==200
    with Session(engine) as session:
        _,counts=deletion_plan(session,uid); assert counts['attempts']==1 and counts['review_items']==1
        result=fulfill_deletion(session,uid);session.commit()
    assert learner.get('/api/me').status_code==401 and other.get('/api/me').status_code==200
    with Session(engine) as session:
        assert session.get(User,uid) is None and session.get(User,other_id) is not None
        assert session.get(DeletionAudit,result['receipt']) is not None
    print('PostgreSQL pending-account deletion, foreign keys and isolation: passed')
