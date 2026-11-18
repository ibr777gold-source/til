"""Draft learning platform API. Not configured for public deployment."""
import hashlib, hmac, json, os, re, secrets, smtplib, time, unicodedata
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from typing import Literal
from fastapi import FastAPI, HTTPException, Request, Response, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel, EmailStr, Field, model_validator
from pwdlib import PasswordHash
from sqlalchemy import create_engine, String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from sqlalchemy.exc import IntegrityError

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg://til:til_dev_password@localhost:5432/til')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL='postgresql+psycopg://'+DATABASE_URL[len('postgres://'):]
elif DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL='postgresql+psycopg://'+DATABASE_URL[len('postgresql://'):]
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {})
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    name: Mapped[str] = mapped_column(String(80))
    course: Mapped[str] = mapped_column(String(10), default='uz-ru')
class LoginSession(Base):
    __tablename__ = 'sessions'
    token: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    expires: Mapped[datetime] = mapped_column(DateTime)
class Progress(Base):
    __tablename__ = 'progress'
    __table_args__ = (UniqueConstraint('user_id', 'lesson_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    lesson_id: Mapped[str] = mapped_column(String(80))
    best_score: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
class Attempt(Base):
    __tablename__ = 'attempts'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    lesson_id: Mapped[str] = mapped_column(String(80))
    answers: Mapped[str] = mapped_column(String(10000), default='{}')
    finished: Mapped[bool] = mapped_column(Boolean, default=False)

class DemoCheckpointResult(Base):
    __tablename__ = 'demo_checkpoint_results'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    course: Mapped[str] = mapped_column(String(5))
    module_number: Mapped[int] = mapped_column(Integer, default=3, server_default='3')
    content_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    score: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime)

class LessonRemediation(Base):
    __tablename__ = 'lesson_remediation'
    attempt_id: Mapped[int] = mapped_column(ForeignKey('attempts.id'), primary_key=True)
    exercise_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

class AnswerReceipt(Base):
    __tablename__ = 'answer_receipts'
    __table_args__ = (UniqueConstraint('attempt_id','exercise_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey('attempts.id'))
    exercise_id: Mapped[str] = mapped_column(String(80))
    response_hash: Mapped[str] = mapped_column(String(64))
    result: Mapped[str] = mapped_column(String(5000))

class ReviewItem(Base):
    __tablename__ = 'review_items'
    __table_args__ = (UniqueConstraint('user_id', 'lesson_id', 'exercise_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    lesson_id: Mapped[str] = mapped_column(String(80))
    exercise_id: Mapped[str] = mapped_column(String(80))
    stage: Mapped[int] = mapped_column(Integer, default=0)
    due_at: Mapped[datetime] = mapped_column(DateTime)

class EditorAccess(Base):
    __tablename__ = 'editor_access'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)

class OwnerAccess(Base):
    __tablename__ = 'owner_access'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)

class OwnerRoleEvent(Base):
    __tablename__ = 'owner_role_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    target_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'),nullable=True)
    role: Mapped[str] = mapped_column(String(20))
    enabled: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime)

class PublisherAccess(Base):
    __tablename__ = 'publisher_access'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)

class DraftLesson(Base):
    __tablename__ = 'draft_lessons'
    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    data: Mapped[str] = mapped_column(String(100000))
    updated_at: Mapped[datetime] = mapped_column(DateTime)

class DraftRevision(Base):
    __tablename__ = 'draft_revisions'
    __table_args__ = (UniqueConstraint('draft_id','version'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey('draft_lessons.id'))
    version: Mapped[int] = mapped_column(Integer)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    data: Mapped[str] = mapped_column(String(100000))
    created_at: Mapped[datetime] = mapped_column(DateTime)

class Feedback(Base):
    __tablename__ = 'feedback'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'),nullable=True)
    lesson_id: Mapped[str] = mapped_column(String(80))
    lesson_title: Mapped[str | None] = mapped_column(String(200),nullable=True)
    exercise_id: Mapped[str | None] = mapped_column(String(80),nullable=True)
    exercise_prompt: Mapped[str | None] = mapped_column(String(1000),nullable=True)
    category: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(String(2000))
    clarity_rating: Mapped[int | None] = mapped_column(Integer,nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='open')
    created_at: Mapped[datetime] = mapped_column(DateTime)

class PasswordReset(Base):
    __tablename__ = 'password_resets'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    expires: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)

class UserSettings(Base):
    __tablename__ = 'user_settings'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    daily_goal: Mapped[int | None] = mapped_column(Integer, nullable=True)

class Onboarding(Base):
    __tablename__ = 'onboarding'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    motivation: Mapped[str] = mapped_column(String(20))
    completed_at: Mapped[datetime] = mapped_column(DateTime)

class DeletionRequest(Base):
    __tablename__ = 'deletion_requests'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default='pending')

class DraftReview(Base):
    __tablename__ = 'draft_reviews'
    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey('draft_lessons.id'))
    version: Mapped[int] = mapped_column(Integer)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    decision: Mapped[str] = mapped_column(String(20))
    notes: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime)

class RateLimitBucket(Base):
    __tablename__ = 'rate_limit_buckets'
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[int] = mapped_column(Integer, index=True)

class AnalyticsEvent(Base):
    __tablename__ = 'analytics_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    event_name: Mapped[str] = mapped_column(String(60), index=True)
    properties: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)

class ReviewSession(Base):
    __tablename__ = 'review_sessions'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    course: Mapped[str] = mapped_column(String(10))
    answer_count: Mapped[int] = mapped_column(Integer, default=0)
    finished: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime)

class MediaAsset(Base):
    __tablename__ = 'media_assets'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    mime: Mapped[str] = mapped_column(String(40))
    attribution: Mapped[str] = mapped_column(String(500))
    rights_status: Mapped[str] = mapped_column(String(20), default='unverified')
    size: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime)

class MediaReview(Base):
    __tablename__ = 'media_reviews'
    id: Mapped[int] = mapped_column(primary_key=True)
    media_id: Mapped[str] = mapped_column(ForeignKey('media_assets.id'))
    reviewer_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    decision: Mapped[str] = mapped_column(String(20))
    notes: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime)

class PublishedRevision(Base):
    __tablename__ = 'published_revisions'
    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey('draft_lessons.id'))
    draft_version: Mapped[int] = mapped_column(Integer)
    lesson_id: Mapped[str] = mapped_column(String(80), index=True)
    course: Mapped[str] = mapped_column(String(10))
    module_number: Mapped[int] = mapped_column(Integer)
    data: Mapped[str] = mapped_column(String(100000))
    publisher_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime)

class PublishedLesson(Base):
    __tablename__ = 'published_lessons'
    lesson_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    revision_id: Mapped[int] = mapped_column(ForeignKey('published_revisions.id'))

class AttemptContent(Base):
    __tablename__ = 'attempt_content'
    attempt_id: Mapped[int] = mapped_column(ForeignKey('attempts.id'), primary_key=True)
    data: Mapped[str] = mapped_column(String(100000))
    published_revision_id: Mapped[int | None] = mapped_column(ForeignKey('published_revisions.id'), nullable=True)

class ReviewContent(Base):
    __tablename__ = 'review_content'
    review_item_id: Mapped[int] = mapped_column(ForeignKey('review_items.id'), primary_key=True)
    data: Mapped[str] = mapped_column(String(100000))

class PublicationAction(Base):
    __tablename__ = 'publication_actions'
    id: Mapped[int] = mapped_column(primary_key=True)
    revision_id: Mapped[int] = mapped_column(ForeignKey('published_revisions.id'))
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    action: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime)

class VocabularyAssessment(Base):
    __tablename__ = 'vocabulary_assessments'
    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(Integer, index=True)
    source_sha256: Mapped[str] = mapped_column(String(64))
    reviewer_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    disposition: Mapped[str] = mapped_column(String(20))
    level: Mapped[str] = mapped_column(String(20))
    topic: Mapped[str] = mapped_column(String(100))
    part_of_speech: Mapped[str] = mapped_column(String(100))
    notes: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime)

class LessonSafetyBlock(Base):
    __tablename__ = 'lesson_safety_blocks'
    lesson_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    revision_id: Mapped[int] = mapped_column(ForeignKey('published_revisions.id'))
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    reason: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime)

class DeletionAudit(Base):
    __tablename__ = 'deletion_audit'
    receipt: Mapped[str] = mapped_column(String(64), primary_key=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime)
    counts: Mapped[str] = mapped_column(String(2000))

# Original prototype content, deliberately unpublished until educator and audio review.
COURSES = [
 {'id':'uz-ru','source':'O‘zbekcha','target':'Русский','title':'Rus tili','subtitle':'O‘zbek tilida o‘rganing','level':'A0 → A1','description':'Kundalik muloqot uchun rus tilini boshidan o‘rganing.'},
 {'id':'ru-uz','source':'Русский','target':'O‘zbekcha','title':'Узбекский язык','subtitle':'Объяснения на русском','level':'A0 → A1','description':'Изучайте узбекский с нуля для повседневного общения.'},
]
LESSONS = {
 'uz-ru-greetings': {'course':'uz-ru','title':'Salomlashuv','eyebrow':'1-DARS · ILK QADAMLAR','objective':'Rus tilida salomlashish va xayrlashishni o‘rganasiz.','minutes':8,'words':[{'target':'Привет','meaning':'Salom (norasmiy)'},{'target':'Здравствуйте','meaning':'Assalomu alaykum (hurmat bilan)'},{'target':'Спасибо','meaning':'Rahmat'},{'target':'До свидания','meaning':'Xayr (hurmat bilan)'}], 'exercises':[
 {'id':'g1','type':'choice','prompt':'Do‘stingizga qanday salom berasiz?','options':['Привет','Спасибо','До свидания'],'answers':['Привет'],'explanation':'Привет — do‘stlar orasida norasmiy salomlashuv.'},
 {'id':'g2','type':'text','prompt':'«Rahmat» so‘zini ruscha yozing.','answers':['спасибо'],'normalization':{'punctuation_tolerant':True,'apostrophe_variants':True},'explanation':'Спасибо — rahmat degani.'},
 {'id':'g3','type':'choice','prompt':'Qaysi ibora hurmat bilan xayrlashish uchun ishlatiladi?','options':['Привет','До свидания','Спасибо'],'answers':['До свидания'],'explanation':'До свидания — hurmat bilan xayrlashish iborasi.'}]},
 'ru-uz-greetings': {'course':'ru-uz','title':'Приветствия','eyebrow':'УРОК 1 · ПЕРВЫЕ ШАГИ','objective':'Научитесь приветствовать людей и прощаться по-узбекски.','minutes':8,'words':[{'target':'Salom','meaning':'Привет (неформально)'},{'target':'Assalomu alaykum','meaning':'Здравствуйте (уважительно)'},{'target':'Rahmat','meaning':'Спасибо'},{'target':'Xayr','meaning':'До свидания / пока'}], 'exercises':[
 {'id':'g1','type':'choice','prompt':'Как неформально поприветствовать друга?','options':['Salom','Rahmat','Xayr'],'answers':['Salom'],'explanation':'Salom — неформальное приветствие.'},
 {'id':'g2','type':'text','prompt':'Напишите «спасибо» по-узбекски.','answers':['rahmat'],'normalization':{'punctuation_tolerant':True,'apostrophe_variants':True},'explanation':'Rahmat означает «спасибо».'},
 {'id':'g3','type':'choice','prompt':'Какое приветствие выражает уважение?','options':['Xayr','Assalomu alaykum','Rahmat'],'answers':['Assalomu alaykum'],'explanation':'Assalomu alaykum — уважительное приветствие.'}]}
}
# Original demo examples; educator review remains required.
LESSONS['uz-ru-greetings']['teaching_note']='«Привет» odatda yaqin kishilar bilan norasmiy salomlashish uchun ishlatiladi. «Здравствуйте» hurmat bilan salomlashish shaklidir.'
LESSONS['ru-uz-greetings']['teaching_note']='Salom обычно используют в неформальном общении. Assalomu alaykum — уважительное приветствие.'
for _word,_example,_translation in zip(LESSONS['uz-ru-greetings']['words'],
        ['Привет, Анна!','Здравствуйте, Анна!','Спасибо, Анна!','До свидания, Анна!'],
        ['Salom, Anna!','Assalomu alaykum, Anna!','Rahmat, Anna!','Xayr, Anna!']):
    _word.update(example=_example,example_translation=_translation)
for _word,_example,_translation in zip(LESSONS['ru-uz-greetings']['words'],
        ['Salom, Anya!','Assalomu alaykum, Anya!','Rahmat, Anya!','Xayr, Anya!'],
        ['Привет, Аня!','Здравствуйте, Аня!','Спасибо, Аня!','До свидания, Аня!']):
    _word.update(example=_example,example_translation=_translation)
DEFAULT_WEB_ORIGIN='http://127.0.0.1:5173'
app = FastAPI(title='Til API', version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv('WEB_ORIGIN',DEFAULT_WEB_ORIGIN)], allow_credentials=True, allow_methods=['GET','POST','PATCH'], allow_headers=['Content-Type','X-Requested-With'])
hasher = PasswordHash.recommended()
class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8,max_length=128)
    name: str = Field(default='',max_length=80)
class Selection(BaseModel): course: Literal['uz-ru','ru-uz']
class Answer(BaseModel): exercise_id: str; response: str = Field(max_length=4000)
def db():
    with Session(engine) as s: yield s
def user(request: Request, s: Session = Depends(db)):
    token = request.cookies.get('til_session')
    session = s.get(LoginSession, hashlib.sha256(token.encode()).hexdigest()) if token else None
    if not session or session.expires < datetime.now(timezone.utc).replace(tzinfo=None): raise HTTPException(401,'Please sign in')
    return s.get(User, session.user_id)
def check_origin(request: Request):
    origin = request.headers.get('origin')
    if origin and origin != os.getenv('WEB_ORIGIN',DEFAULT_WEB_ORIGIN): raise HTTPException(403,'Invalid origin')
def enforce_rate_limit(request: Request, action: str, limit: int, window_seconds: int = 60):
    # Do not trust client-provided forwarding headers. Configure an edge limiter
    # when deployed behind a proxy that hides individual client addresses.
    from sqlalchemy import delete
    if engine.dialect.name == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    elif engine.dialect.name == 'sqlite':
        from sqlalchemy.dialects.sqlite import insert
    else:
        raise RuntimeError('Rate limiter requires PostgreSQL or SQLite')
    now=int(time.time()); window=now//window_seconds
    host=request.client.host if request.client else 'unknown'
    key=hashlib.sha256(f'{action}:{host}:{window}'.encode()).hexdigest()
    statement=insert(RateLimitBucket).values(key=key,count=1,expires_at=(window+1)*window_seconds)
    statement=statement.on_conflict_do_update(index_elements=['key'],set_={'count':RateLimitBucket.count+1}).returning(RateLimitBucket.count)
    with engine.begin() as connection:
        count=connection.execute(statement).scalar_one()
        connection.execute(delete(RateLimitBucket).where(RateLimitBucket.expires_at<now-3600))
    if count>limit:
        raise HTTPException(429,'Too many requests; try again later',headers={'Retry-After':str((window+1)*window_seconds-now)})

def track(s: Session, user_id: int, name: str, properties: dict):
    # Only controlled identifiers and aggregate learning results; never answers or credentials.
    s.add(AnalyticsEvent(user_id=user_id,event_name=name,properties=json.dumps(properties),created_at=datetime.now(timezone.utc).replace(tzinfo=None)))

def login_cookie(response, s, u):
    token=secrets.token_urlsafe(48)
    s.add(LoginSession(token=hashlib.sha256(token.encode()).hexdigest(),user_id=u.id,expires=datetime.now(timezone.utc).replace(tzinfo=None)+timedelta(days=7))); s.commit()
    response.set_cookie('til_session',token,httponly=True,secure=os.getenv('COOKIE_SECURE','false')=='true',samesite='strict',max_age=604800)
def public_user(u): return {'id':u.id,'name':u.name,'email':u.email,'course':u.course}
def ensure_not_blocked(lesson_id: str,s: Session,lock: bool = False):
    if lock and lesson_id.startswith('draft-'):
        try: draft_id=int(lesson_id[6:])
        except ValueError: draft_id=None
        if draft_id is not None: s.scalar(select(DraftLesson).where(DraftLesson.id==draft_id).with_for_update())
    if s.get(LessonSafetyBlock,lesson_id): raise HTTPException(410,'This lesson is temporarily unavailable')

def blocked_lesson_ids(s: Session):
    return set(s.scalars(select(LessonSafetyBlock.lesson_id)))

def lesson_or_404(id, s: Session | None = None):
    if s: ensure_not_blocked(id,s)
    if id in LESSONS: return LESSONS[id]
    if s:
        current=s.get(PublishedLesson,id)
        revision=s.get(PublishedRevision,current.revision_id) if current else None
        if revision: return json.loads(revision.data)
    raise HTTPException(404,'Lesson not found')

def public_exercise(exercise: dict):
    public={k:v for k,v in exercise.items() if k not in ('answers','explanation','match_pairs')}
    if exercise['type']=='match':
        pairs=exercise.get('match_pairs',[])
        left=[pair['left'] for pair in pairs]; right=[pair['right'] for pair in pairs]
        secrets.SystemRandom().shuffle(left); secrets.SystemRandom().shuffle(right)
        public.update(match_left=left,match_right=right)
    return public

def public_lesson(lesson_id: str, content: dict):
    return {**{k:v for k,v in content.items() if k not in ('outline_ref','template_ref')},'id':lesson_id,'exercises':[public_exercise(e) for e in content['exercises']]}

def attempt_lesson(attempt: Attempt, s: Session):
    snapshot=s.get(AttemptContent,attempt.id)
    return json.loads(snapshot.data) if snapshot else lesson_or_404(attempt.lesson_id,s)

def review_lesson(item: ReviewItem,s: Session):
    snapshot=s.get(ReviewContent,item.id)
    return json.loads(snapshot.data) if snapshot else lesson_or_404(item.lesson_id,s)
def normalized(value, policy=None):
    policy=policy or {}
    value=unicodedata.normalize('NFKC',value)
    if not policy.get('case_sensitive',False): value=value.casefold()
    if policy.get('apostrophe_variants',True): value=value.translate(str.maketrans({c:'‘' for c in "'ʻʼ’`"}))
    value=' '.join(value.split())
    if policy.get('punctuation_tolerant',False): value=value.rstrip('.,!?;:…،؟。！？').rstrip()
    return value
def correct_answer(exercise: dict):
    if exercise['type']=='match': return '; '.join(pair['left']+' → '+pair['right'] for pair in exercise.get('match_pairs',[]))
    return exercise['answers'][0]

def answer_matches(exercise: dict, response: str):
    if exercise['type']=='match':
        try: supplied=json.loads(response)
        except (json.JSONDecodeError,TypeError): return False
        if not isinstance(supplied,dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in supplied.items()): return False
        return supplied=={pair['left']:pair['right'] for pair in exercise.get('match_pairs',[])}
    policy=exercise.get('normalization') or {}
    return normalized(response,policy) in [normalized(value,policy) for value in exercise['answers']]

def receipt_key(exercise: dict, response: str):
    if exercise['type']=='match':
        try:
            parsed=json.loads(response)
            if isinstance(parsed,dict): return json.dumps(parsed,sort_keys=True,ensure_ascii=False,separators=(',',':'))
        except (json.JSONDecodeError,TypeError): pass
        return response
    return normalized(response,exercise.get('normalization') or {})

@app.get('/api/health')
def health(): return {'status':'ok','content':'draft'}

@app.get('/api/ready')
def readiness():
    from sqlalchemy import text
    from sqlalchemy.exc import SQLAlchemyError
    try:
        with engine.connect() as connection:
            connection.execute(text('SELECT 1'))
    except SQLAlchemyError:
        raise HTTPException(503,'Database unavailable')
    return {'status':'ready'}
@app.get('/api/capabilities')
def capabilities():
    return {'password_reset_email':bool(os.getenv('SMTP_HOST') and os.getenv('SMTP_FROM'))}

@app.get('/api/courses')
def courses(): return COURSES
@app.get('/api/courses/{course}/lessons')
def course_lessons(course: str,s: Session=Depends(db)):
    if course not in [c['id'] for c in COURSES]: raise HTTPException(404,'Course not found')
    blocked=blocked_lesson_ids(s)
    entries=[{'id':k,'title':v['title'],'objective':v['objective'],'minutes':v['minutes'],'module_number':v.get('module_number',3),'lesson_number':v.get('lesson_number',1),'demo':True} for k,v in LESSONS.items() if v['course']==course]
    revisions=s.scalars(select(PublishedRevision).join(PublishedLesson,PublishedLesson.revision_id==PublishedRevision.id).where(PublishedRevision.course==course))
    for revision in revisions:
        if revision.lesson_id in blocked: continue
        data=json.loads(revision.data); position=data.get('lesson_number') or (data.get('outline_ref') or {}).get('lesson_number',1)
        entries.append({'id':revision.lesson_id,'title':data['title'],'objective':data['objective'],'minutes':data['minutes'],'module_number':revision.module_number,'lesson_number':position,'demo':False})
    return sorted(entries,key=lambda entry:(entry['module_number'],entry['lesson_number'],entry['demo'],entry['id']))
# The planned modules are a roadmap; only the explicitly listed demo lesson exists.
MODULES = {
 'uz-ru': [
  ('Tovushlar va kirill I','Tanish harflar va sodda bo‘g‘inlar'),
  ('Tovushlar va kirill II','Alifbo va urg‘u asoslari'),
  ('Salomlashuv va tanishuv','Salomlashish va o‘zini tanishtirish'),
  ('Odamlar va buyumlar','Olmoshlar va sodda nomlash'),
  ('Sonlar va vaqt','Sonlar, yosh va vaqt'),
  ('Oila va tavsif','Oila va sodda sifatlar'),
  ('Kundalik hayot','Ko‘p ishlatiladigan fe’llar'),
  ('Ovqat va xarid','So‘rovlar, narx va miqdor'),
  ('Joy va harakat','Qayerda, qayerga va qayerdan'),
  ('Amaliy muloqot','Kundalik suhbat va qisqa xabarlar')],
 'ru-uz': [
  ('Узбекская латиница I','Знакомые буквы и звуки'),
  ('Узбекская латиница II','O‘, G‘, Sh, Ch и Ng'),
  ('Приветствие и знакомство','Вежливые приветствия и представление'),
  ('Люди и предметы','Местоимения и называние предметов'),
  ('Числа и время','Числа, возраст и время'),
  ('Семья и описания','Семья, цвета и прилагательные'),
  ('Повседневная жизнь','Частые глаголы и отрицание'),
  ('Еда и покупки','Заказы, цены и просьбы'),
  ('Места и направления','Основные значения -da, -ga и -dan'),
  ('Практическое общение','Повседневные диалоги и сообщения')]
}

@app.get('/api/courses/{course}/modules')
def course_modules(course: str,s: Session=Depends(db)):
    if course not in MODULES: raise HTTPException(404,'Course not found')
    blocked=blocked_lesson_ids(s)
    result=[{'number':i+1,'title':title,'objective':objective,'status':'planned','lessons':[]}
            for i,(title,objective) in enumerate(MODULES[course])]
    for lesson_id, lesson in LESSONS.items():
        if lesson['course']!=course: continue
        module=result[lesson.get('module_number',3)-1]
        module['lessons'].append({'id':lesson_id,'title':lesson['title'],'minutes':lesson['minutes'],'lesson_number':lesson.get('lesson_number',1),'demo':True})
        module['status']='demo'
    revisions=s.scalars(select(PublishedRevision).join(PublishedLesson,PublishedLesson.revision_id==PublishedRevision.id).where(PublishedRevision.course==course).order_by(PublishedRevision.id))
    for revision in revisions:
        if revision.lesson_id in blocked: continue
        content=json.loads(revision.data); module=result[revision.module_number-1]
        position=content.get('lesson_number') or (content.get('outline_ref') or {}).get('lesson_number',1)
        module['lessons'].append({'id':revision.lesson_id,'title':content['title'],'minutes':content['minutes'],'lesson_number':position,'demo':False})
        module['status']='available'
    for module in result:
        module['lessons'].sort(key=lambda item:(item['lesson_number'],item['demo'],item['id']))
    return result

@app.post('/api/auth/register')
def register(data: Credentials, request: Request, response: Response, s: Session=Depends(db)):
    check_origin(request); enforce_rate_limit(request,'register',10); email=data.email.lower()
    if s.scalar(select(User).where(User.email==email)): raise HTTPException(409,'This email is already registered')
    u=User(email=email,password_hash=hasher.hash(data.password),name=data.name.strip() or email.split('@')[0]); s.add(u); s.flush(); track(s,u.id,'signup_completed',{}); s.commit(); s.refresh(u); login_cookie(response,s,u); return public_user(u)
@app.post('/api/auth/login')
def login(data: Credentials, request: Request, response: Response, s: Session=Depends(db)):
    check_origin(request); enforce_rate_limit(request,'login',10); u=s.scalar(select(User).where(User.email==data.email.lower()))
    if not u or not hasher.verify(data.password,u.password_hash): raise HTTPException(401,'Incorrect email or password')
    login_cookie(response,s,u); return public_user(u)
@app.post('/api/auth/logout')
def logout(request: Request, response: Response, s: Session=Depends(db)):
    check_origin(request); token=request.cookies.get('til_session'); session=s.get(LoginSession,hashlib.sha256(token.encode()).hexdigest()) if token else None
    if session: s.delete(session); s.commit()
    response.delete_cookie('til_session'); return {'ok':True}
@app.get('/api/me')
def me(u: User=Depends(user)): return public_user(u)
@app.patch('/api/me')
def update_me(data: Selection, request: Request, u: User=Depends(user), s: Session=Depends(db)):
    check_origin(request); u=s.merge(u); u.course=data.course; track(s,u.id,'course_selected',{'course':data.course}); s.commit(); return public_user(u)
@app.get('/api/progress')
def progress(u: User=Depends(user),s: Session=Depends(db)):
    result=[]
    for p in s.scalars(select(Progress).where(Progress.user_id==u.id)):
        current=s.get(PublishedLesson,p.lesson_id)
        published=s.get(PublishedRevision,current.revision_id) if current else None
        if not published:
            result.append({'lesson_id':p.lesson_id,'best_score':p.best_score,'completed':p.completed,'revision_changed':False}); continue
        attempts=s.scalars(select(Attempt).join(AttemptContent,AttemptContent.attempt_id==Attempt.id).join(PublishedRevision,PublishedRevision.id==AttemptContent.published_revision_id).where(
            Attempt.user_id==u.id,Attempt.lesson_id==p.lesson_id,Attempt.finished==True,
            PublishedRevision.draft_id==published.draft_id,PublishedRevision.draft_version==published.draft_version))
        scores=[]
        for attempt in attempts:
            content=attempt_lesson(attempt,s); answers=json.loads(attempt.answers); exercises=content['exercises']
            if exercises and all(e['id'] in answers for e in exercises):
                scores.append(round(100*sum(bool(answers[e['id']]) for e in exercises)/len(exercises)))
        result.append({'lesson_id':p.lesson_id,'best_score':max(scores,default=0),'completed':any(score>=80 for score in scores),'revision_changed':not scores})
    return result

@app.get('/api/progress/overview')
def progress_overview(u: User=Depends(user),s: Session=Depends(db)):
    progress_by_id={item['lesson_id']:item for item in progress(u=u,s=s)}
    unfinished=unfinished_lessons(u=u,s=s)
    practice={}
    for entry in s.scalars(select(DemoCheckpointResult).where(DemoCheckpointResult.user_id==u.id).order_by(DemoCheckpointResult.created_at.desc(),DemoCheckpointResult.id.desc())):
        key=(entry.course,entry.module_number)
        if key in practice: continue
        status='unknown'
        if entry.content_digest:
            try:
                exercises=course_demo_exercises(entry.course,s) if entry.module_number==0 else module_demo_exercises(entry.course,entry.module_number,s)[1]
                status='current' if secrets.compare_digest(entry.content_digest,practice_digest(exercises)) else 'changed'
            except HTTPException: status='unavailable'
        practice[key]={'score':entry.score,'created_at':entry.created_at.isoformat()+'Z','version_status':status}
    courses=[]
    for course in COURSES:
        lessons=course_lessons(course['id'],s=s)
        modules=[]
        for number in range(1,11):
            items=[item for item in lessons if item['module_number']==number]
            modules.append({'number':number,'available':len(items),'completed':sum(bool(progress_by_id.get(item['id'],{}).get('completed')) for item in items),
                            'demo':sum(bool(item.get('demo')) for item in items),'practice':practice.get((course['id'],number))})
        courses.append({'course':course['id'],'available':len(lessons),'completed':sum(module['completed'] for module in modules),
                        'demo':sum(module['demo'] for module in modules),
                        'in_progress':sum(1 for item in unfinished if item['course']==course['id']),
                        'due_reviews':len(review(course=course['id'],u=u,s=s)), 'course_practice':practice.get((course['id'],0)), 'modules':modules})
    return {'courses':courses,'scope':'currently_available_lessons'}
@app.get('/api/preview/{course}')
def preview_exercise(course: Literal['uz-ru','ru-uz'],s: Session=Depends(db)):
    lesson_id=course+'-greetings'
    content=lesson_or_404(lesson_id,s)
    return {'title':content['title'],'exercise':public_exercise(content['exercises'][0])}

@app.post('/api/preview/{course}/answer')
def preview_answer(course: Literal['uz-ru','ru-uz'],data: Answer,request: Request,s: Session=Depends(db)):
    check_origin(request); enforce_rate_limit(request,'preview-answer',60)
    content=lesson_or_404(course+'-greetings',s)
    exercise=content['exercises'][0]
    if data.exercise_id!=exercise['id']: raise HTTPException(404,'Preview exercise not found')
    correct=answer_matches(exercise,data.response)
    return {'correct':correct,'explanation':exercise['explanation'],'correct_answer':correct_answer(exercise) if not correct else None}

# Configure a shared key if multiple workers serve practice requests.
PRACTICE_REVISION_KEY=os.getenv('PRACTICE_REVISION_KEY','').encode() or secrets.token_bytes(32)
def practice_payload(exercises: list[dict]):
    return json.dumps(exercises,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()

def practice_digest(exercises: list[dict]):
    return hashlib.sha256(practice_payload(exercises)).hexdigest()

def practice_version(exercises: list[dict]):
    return hmac.new(PRACTICE_REVISION_KEY,practice_payload(exercises),hashlib.sha256).hexdigest()

def require_practice_version(exercises: list[dict],version: str):
    if not secrets.compare_digest(practice_version(exercises),version): raise HTTPException(409,'Practice content changed; reload before submitting')

class CheckpointSubmission(BaseModel):
    responses: dict[str,str] = Field(max_length=3)
    content_version: str = Field(pattern=r'^[a-f0-9]{64}$')

@app.get('/api/demo-checkpoint/{course}')
def demo_checkpoint(course: Literal['uz-ru','ru-uz'],u: User=Depends(user),s: Session=Depends(db)):
    lesson=lesson_or_404(course+'-greetings',s)
    return {'title':lesson['title'],'content_version':practice_version(lesson['exercises']),'exercises':[public_exercise(e) for e in lesson['exercises']]}

@app.post('/api/demo-checkpoint/{course}')
def grade_demo_checkpoint(course: Literal['uz-ru','ru-uz'],data: CheckpointSubmission,request: Request,u: User=Depends(user),s: Session=Depends(db)):
    check_origin(request); enforce_rate_limit(request,'demo-checkpoint',20)
    exercises=lesson_or_404(course+'-greetings',s)['exercises']
    require_practice_version(exercises,data.content_version)
    if set(data.responses)!=set(e['id'] for e in exercises) or any(not value.strip() or len(value)>4000 for value in data.responses.values()):
        raise HTTPException(422,'Answer every question')
    results=[{'id':e['id'],'prompt':e['prompt'],'correct':answer_matches(e,data.responses[e['id']]),'answer':correct_answer(e),'explanation':e['explanation']} for e in exercises]
    score=round(100*sum(item['correct'] for item in results)/len(results))
    s.add(DemoCheckpointResult(user_id=u.id,course=course,content_digest=practice_digest(exercises),score=score,created_at=datetime.now(timezone.utc).replace(tzinfo=None)))
    track(s,u.id,'demo_checkpoint_completed',{'course':course,'score':score});s.commit()
    return {'score':score,'results':results}

@app.get('/api/demo-checkpoint/{course}/history')
def demo_checkpoint_history(course: Literal['uz-ru','ru-uz'],u: User=Depends(user),s: Session=Depends(db)):
    entries=s.scalars(select(DemoCheckpointResult).where(DemoCheckpointResult.user_id==u.id,DemoCheckpointResult.course==course,DemoCheckpointResult.module_number==3).order_by(DemoCheckpointResult.created_at.desc(),DemoCheckpointResult.id.desc()).limit(10))
    return [{'score':entry.score,'created_at':entry.created_at.isoformat()+'Z'} for entry in entries]

def sample_listening_exercise(course: str):
    if course=='ru-uz':
        return {'id':'sample-listening','type':'listen_choice','prompt':'Прослушайте слово. Что оно означает?','audio_src':'/audio/synthetic/uz-thanks.mp3','options':['Спасибо','Привет','До свидания'],'answers':['Спасибо'],'explanation':'Rahmat означает «спасибо».'}
    return {'id':'sample-listening','type':'listen_choice','prompt':'So‘zni tinglang. U nimani anglatadi?','audio_src':'/audio/synthetic/ru-thanks.mp3','options':['Rahmat','Salom','Xayr'],'answers':['Rahmat'],'explanation':'Спасибо — rahmat.'}

def sample_dialogue_exercise(course: str):
    if course=='ru-uz':
        return {'id':'sample-dialogue','type':'text','prompt':'Вас спросили: «Ismingiz nima?» Представьтесь по-узбекски именем Anya. Начните: «Mening ismim…»','answers':['Mening ismim Anya'],'normalization':{'punctuation_tolerant':True,'apostrophe_variants':True},'explanation':'Mening ismim Anya — меня зовут Аня.'}
    return {'id':'sample-dialogue','type':'text','prompt':'Sizdan «Как вас зовут?» deb so‘rashdi. Anya deb ruscha tanishing. «Меня зовут…» deb boshlang.','answers':['Меня зовут Аня'],'normalization':{'punctuation_tolerant':True,'apostrophe_variants':True},'explanation':'Меня зовут Аня — mening ismim Anya.'}

def module_demo_exercises(course: str,module_number: int,s: Session):
    from app.demo_audio import listening_exercise
    if module_number<1 or module_number>10: raise HTTPException(404,'Module not found')
    entries=sorted(((key,item) for key,item in LESSONS.items() if item['course']==course and item.get('module_number',3)==module_number),key=lambda pair:(pair[1].get('lesson_number',1),pair[0]))
    blocked=blocked_lesson_ids(s); selected=[]; first=None; recall=None
    for lesson_id, content in entries:
        if lesson_id in blocked: continue
        exercises=[e for e in content['exercises'] if e['type'] in ('choice','text')]
        if recall is None:
            recall=next(({**e,'id':f'{lesson_id}:{e["id"]}','practice_lesson_title':content['title'],'practice_lesson_id':lesson_id} for e in exercises if e['type']=='text'),None)
        if first is None:
            if len(exercises)<3: continue
            first=content; selected.extend({**e,'practice_lesson_title':content['title'],'practice_lesson_id':lesson_id} for e in exercises[:3])
        elif exercises and len(selected)<8:
            exercise=exercises[0]
            selected.append({**exercise,'id':f'{lesson_id}:{exercise["id"]}','practice_lesson_title':content['title'],'practice_lesson_id':lesson_id})
    if first is not None:
        if not any(e['type']=='text' for e in selected) and recall is not None: selected.append(recall)
        selected.append(listening_exercise(course,module_number))
        return first,selected
    raise HTTPException(404,'Module practice unavailable')

@app.get('/api/demo-module/{course}/{module_number}')
def module_demo(course: Literal['uz-ru','ru-uz'],module_number: int,u: User=Depends(user),s: Session=Depends(db)):
    content,exercises=module_demo_exercises(course,module_number,s)
    return {'title':MODULES[course][module_number-1][0],'content_version':practice_version(exercises),'exercises':[public_exercise(e) for e in exercises]}

class ModulePracticeSubmission(BaseModel):
    responses: dict[str,str] = Field(max_length=10)
    content_version: str = Field(pattern=r'^[a-f0-9]{64}$')

@app.post('/api/demo-module/{course}/{module_number}')
def grade_module_demo(course: Literal['uz-ru','ru-uz'],module_number: int,data: ModulePracticeSubmission,request: Request,u: User=Depends(user),s: Session=Depends(db)):
    check_origin(request); enforce_rate_limit(request,'demo-module',20)
    _,exercises=module_demo_exercises(course,module_number,s)
    require_practice_version(exercises,data.content_version)
    if set(data.responses)!=set(e['id'] for e in exercises) or any(not value.strip() or len(value)>4000 for value in data.responses.values()): raise HTTPException(422,'Answer every question')
    results=[{'id':e['id'],'prompt':e['prompt'],'correct':answer_matches(e,data.responses[e['id']]),'answer':correct_answer(e),'explanation':e['explanation']} for e in exercises]
    score=round(100*sum(item['correct'] for item in results)/len(results))
    s.add(DemoCheckpointResult(user_id=u.id,course=course,module_number=module_number,content_digest=practice_digest(exercises),score=score,created_at=datetime.now(timezone.utc).replace(tzinfo=None)))
    track(s,u.id,'demo_module_practice_completed',{'course':course,'module_number':module_number,'score':score});s.commit()
    return {'score':score,'results':results}

class CoursePracticeSubmission(BaseModel):
    responses: dict[str,str] = Field(max_length=12)
    content_version: str = Field(pattern=r'^[a-f0-9]{64}$')

def course_demo_exercises(course: str,s: Session):
    selected=[]
    for module in range(1,11):
        _,exercises=module_demo_exercises(course,module,s)
        exercise=next((e for e in exercises if e['type']=='text'),exercises[0]) if module in (2,5,7) else exercises[0]
        selected.append({**exercise,'id':f'm{module}-{exercise["id"]}','practice_lesson_title':MODULES[course][module-1][0]})
    selected.extend([sample_listening_exercise(course),sample_dialogue_exercise(course)])
    return selected

@app.get('/api/demo-course/{course}')
def course_demo(course: Literal['uz-ru','ru-uz'],u: User=Depends(user),s: Session=Depends(db)):
    exercises=course_demo_exercises(course,s)
    return {'title':'Пробная проверка по курсу' if course=='ru-uz' else 'Kurs bo‘yicha namuna sinov','content_version':practice_version(exercises),'exercises':[public_exercise(e) for e in exercises]}

@app.post('/api/demo-course/{course}')
def grade_course_demo(course: Literal['uz-ru','ru-uz'],data: CoursePracticeSubmission,request: Request,u: User=Depends(user),s: Session=Depends(db)):
    check_origin(request);enforce_rate_limit(request,'demo-course',20)
    exercises=course_demo_exercises(course,s)
    require_practice_version(exercises,data.content_version)
    if set(data.responses)!=set(e['id'] for e in exercises) or any(not value.strip() or len(value)>4000 for value in data.responses.values()): raise HTTPException(422,'Answer every question')
    results=[{'id':e['id'],'prompt':e['prompt'],'correct':answer_matches(e,data.responses[e['id']]),'answer':correct_answer(e),'explanation':e['explanation']} for e in exercises]
    score=round(100*sum(item['correct'] for item in results)/len(results))
    s.add(DemoCheckpointResult(user_id=u.id,course=course,module_number=0,content_digest=practice_digest(exercises),score=score,created_at=datetime.now(timezone.utc).replace(tzinfo=None)))
    track(s,u.id,'demo_course_practice_completed',{'course':course,'score':score});s.commit()
    return {'score':score,'results':results}

@app.get('/api/lessons/{lesson_id}')
def lesson(lesson_id: str,s: Session=Depends(db)):
    return public_lesson(lesson_id,lesson_or_404(lesson_id,s))
@app.post('/api/lessons/{lesson_id}/attempts')
def start(lesson_id: str, request: Request,u: User=Depends(user),s: Session=Depends(db)):
    check_origin(request); ensure_not_blocked(lesson_id,s,lock=True)
    s.scalar(select(User).where(User.id==u.id).with_for_update())
    a=s.scalar(select(Attempt).where(Attempt.user_id==u.id, Attempt.lesson_id==lesson_id, Attempt.finished==False).order_by(Attempt.id.desc()))
    if not a:
        content=lesson_or_404(lesson_id,s)
        a=Attempt(user_id=u.id,lesson_id=lesson_id); s.add(a); s.flush()
        published=s.get(PublishedLesson,lesson_id)
        s.add(AttemptContent(attempt_id=a.id,data=json.dumps(content,ensure_ascii=False),published_revision_id=published.revision_id if published else None))
        track(s,u.id,'lesson_started',{'lesson_id':lesson_id,'course':content['course']}); s.commit(); s.refresh(a)
    return {'id':a.id, 'answered':list(json.loads(a.answers).keys()),'lesson':public_lesson(lesson_id,attempt_lesson(a,s))}
@app.post('/api/attempts/{attempt_id}/answers')
def answer(attempt_id: int,data: Answer,request: Request,u: User=Depends(user),s: Session=Depends(db)):
    import json
    check_origin(request); enforce_rate_limit(request,'answer',60)
    initial=s.get(Attempt,attempt_id)
    if not initial or initial.user_id!=u.id: raise HTTPException(404,'Attempt not found')
    ensure_not_blocked(initial.lesson_id,s,lock=True)
    s.scalar(select(User).where(User.id==u.id).with_for_update())
    a=s.scalar(select(Attempt).where(Attempt.id==attempt_id).with_for_update().execution_options(populate_existing=True))
    if not a or a.user_id!=u.id: raise HTTPException(404,'Attempt not found')
    content=attempt_lesson(a,s)
    e=next((e for e in content['exercises'] if e['id']==data.exercise_id),None)
    if not e: raise HTTPException(404,'Exercise not found')
    response_hash=hashlib.sha256(receipt_key(e,data.response).encode()).hexdigest()
    receipt=s.scalar(select(AnswerReceipt).where(AnswerReceipt.attempt_id==attempt_id,AnswerReceipt.exercise_id==data.exercise_id))
    if receipt:
        if not secrets.compare_digest(receipt.response_hash,response_hash): raise HTTPException(409,'Exercise already answered')
        return json.loads(receipt.result)
    if a.finished: raise HTTPException(409,'Attempt already completed')
    answers=json.loads(a.answers)
    if e['id'] in answers: raise HTTPException(409,'Exercise already answered')
    correct=answer_matches(e,data.response); answers[e['id']]=correct; a.answers=json.dumps(answers)
    if not correct:
        s.add(LessonRemediation(attempt_id=a.id,exercise_id=e['id'],resolved=False,retry_count=0))
        item=s.scalar(select(ReviewItem).where(ReviewItem.user_id==u.id, ReviewItem.lesson_id==a.lesson_id, ReviewItem.exercise_id==e['id']))
        if not item:
            item=ReviewItem(user_id=u.id, lesson_id=a.lesson_id, exercise_id=e['id'], stage=0, due_at=datetime.now(timezone.utc).replace(tzinfo=None)); s.add(item)
        else:
            item.stage=0; item.due_at=datetime.now(timezone.utc).replace(tzinfo=None)
        s.flush(); snapshot=s.get(ReviewContent,item.id)
        if snapshot: snapshot.data=json.dumps(content,ensure_ascii=False)
        else: s.add(ReviewContent(review_item_id=item.id,data=json.dumps(content,ensure_ascii=False)))
    result={'correct':correct,'explanation':e['explanation'],'correct_answer':correct_answer(e) if not correct else None}
    s.add(AnswerReceipt(attempt_id=attempt_id,exercise_id=e['id'],response_hash=response_hash,result=json.dumps(result,ensure_ascii=False)))
    track(s,u.id,'exercise_answered',{'lesson_id':a.lesson_id,'exercise_id':e['id'],'correct':correct})
    s.commit()
    return result
@app.post('/api/attempts/{attempt_id}/complete')
def complete(attempt_id: int,request: Request,u: User=Depends(user),s: Session=Depends(db)):
    import json
    check_origin(request)
    initial=s.get(Attempt,attempt_id)
    if not initial or initial.user_id!=u.id: raise HTTPException(404,'Attempt not found')
    ensure_not_blocked(initial.lesson_id,s,lock=True)
    s.scalar(select(User).where(User.id==u.id).with_for_update())
    a=s.scalar(select(Attempt).where(Attempt.id==attempt_id).with_for_update().execution_options(populate_existing=True))
    if not a or a.user_id!=u.id: raise HTTPException(404,'Attempt not found')
    content=attempt_lesson(a,s); answers=json.loads(a.answers); exercises=content['exercises']
    if len(answers)!=len(exercises): raise HTTPException(400,'Answer every exercise first')
    if not a.finished and s.scalar(select(LessonRemediation.attempt_id).where(LessonRemediation.attempt_id==a.id,LessonRemediation.resolved==False).limit(1)):
        raise HTTPException(409,'Practice missed exercises before completing the lesson')
    score=round(100*sum(answers.values())/len(exercises))
    if not a.finished: track(s,u.id,'lesson_completed',{'lesson_id':a.lesson_id,'course':content['course'],'score':score})
    a.finished=True
    p=s.scalar(select(Progress).where(Progress.user_id==u.id,Progress.lesson_id==a.lesson_id))
    if not p: p=Progress(user_id=u.id,lesson_id=a.lesson_id); s.add(p)
    p.best_score=max(p.best_score or 0,score); p.completed=p.completed or score>=80; s.commit(); return {'score':score,'passed':score>=80}

@app.get('/api/attempts/{attempt_id}/remediation')
def remediation_queue(attempt_id: int,u: User=Depends(user),s: Session=Depends(db)):
    attempt=s.get(Attempt,attempt_id)
    if not attempt or attempt.user_id!=u.id: raise HTTPException(404,'Attempt not found')
    ensure_not_blocked(attempt.lesson_id,s,lock=True)
    if attempt.finished: return []
    unresolved=set(s.scalars(select(LessonRemediation.exercise_id).where(LessonRemediation.attempt_id==attempt.id,LessonRemediation.resolved==False)))
    return [public_exercise(e) for e in attempt_lesson(attempt,s)['exercises'] if e['id'] in unresolved]

class RemediationAnswer(BaseModel):
    response: str = Field(min_length=1,max_length=4000)

@app.post('/api/attempts/{attempt_id}/remediation/{exercise_id}')
def retry_missed(attempt_id: int,exercise_id: str,data: RemediationAnswer,request: Request,u: User=Depends(user),s: Session=Depends(db)):
    check_origin(request); enforce_rate_limit(request,'remediation',60)
    initial=s.get(Attempt,attempt_id)
    if not initial or initial.user_id!=u.id: raise HTTPException(404,'Attempt not found')
    ensure_not_blocked(initial.lesson_id,s,lock=True)
    s.scalar(select(User).where(User.id==u.id).with_for_update())
    attempt=s.scalar(select(Attempt).where(Attempt.id==attempt_id).with_for_update().execution_options(populate_existing=True))
    if not attempt or attempt.user_id!=u.id: raise HTTPException(404,'Attempt not found')
    item=s.get(LessonRemediation,(attempt_id,exercise_id))
    if not item: raise HTTPException(404,'Missed exercise not found')
    content=attempt_lesson(attempt,s)
    exercise=next((e for e in content['exercises'] if e['id']==exercise_id),None)
    if not exercise: raise HTTPException(404,'Exercise not found')
    correct=answer_matches(exercise,data.response)
    if item.resolved:
        if correct: return {'correct':True,'explanation':exercise['explanation'],'correct_answer':None}
        raise HTTPException(409,'Exercise already resolved')
    if attempt.finished: raise HTTPException(409,'Attempt already completed')
    item.retry_count+=1
    if correct:
        item.resolved=True
        review=s.scalar(select(ReviewItem).where(ReviewItem.user_id==u.id,ReviewItem.lesson_id==attempt.lesson_id,ReviewItem.exercise_id==exercise_id).with_for_update())
        snapshot=s.get(ReviewContent,review.id) if review else None
        now=datetime.now(timezone.utc).replace(tzinfo=None)
        if review and snapshot and json.loads(snapshot.data)==content and review.stage==0:
            review.stage=1; review.due_at=now+timedelta(days=1)
    track(s,u.id,'exercise_retried',{'lesson_id':attempt.lesson_id,'exercise_id':exercise_id,'correct':correct})
    s.commit()
    return {'correct':correct,'explanation':exercise['explanation'],'correct_answer':correct_answer(exercise) if not correct else None}

def result_details(a: Attempt,s: Session):
    if not a.finished: raise HTTPException(409,'Complete the lesson before viewing results')
    content=attempt_lesson(a,s); answers=json.loads(a.answers); exercises=content['exercises']
    if not exercises or any(e['id'] not in answers for e in exercises): raise HTTPException(409,'Attempt results are incomplete')
    details=[]
    for exercise in exercises:
        receipt=s.scalar(select(AnswerReceipt).where(AnswerReceipt.attempt_id==a.id,AnswerReceipt.exercise_id==exercise['id']))
        feedback=json.loads(receipt.result) if receipt else None
        details.append({'id':exercise['id'],'prompt':exercise['prompt'],'correct':bool(answers[exercise['id']]),
                        'explanation':feedback['explanation'] if feedback else exercise['explanation'],
                        'correct_answer':(feedback.get('correct_answer') if feedback else None) or correct_answer(exercise)})
    score=round(100*sum(bool(answers[e['id']]) for e in exercises)/len(exercises))
    return {'attempt_id':a.id,'score':score,'passed':score>=80,'lesson':public_lesson(a.lesson_id,content),'exercises':details}

@app.get('/api/attempts/{attempt_id}/results')
def attempt_results(attempt_id: int,u: User=Depends(user),s: Session=Depends(db)):
    a=s.get(Attempt,attempt_id)
    if not a or a.user_id!=u.id: raise HTTPException(404,'Attempt not found')
    ensure_not_blocked(a.lesson_id,s,lock=True)
    return result_details(a,s)

@app.get('/api/lessons/{lesson_id}/results')
def latest_lesson_results(lesson_id: str,u: User=Depends(user),s: Session=Depends(db)):
    a=s.scalar(select(Attempt).where(Attempt.user_id==u.id,Attempt.lesson_id==lesson_id,Attempt.finished==True).order_by(Attempt.id.desc()))
    if not a: raise HTTPException(404,'No completed attempt found')
    ensure_not_blocked(a.lesson_id,s,lock=True)
    return result_details(a,s)

@app.get('/api/review')
def review(course: Literal['uz-ru','ru-uz'] | None = None,include_upcoming: bool = False,u: User=Depends(user), s: Session=Depends(db)):
    now=datetime.now(timezone.utc).replace(tzinfo=None)
    statement=select(ReviewItem).where(ReviewItem.user_id==u.id)
    if not include_upcoming: statement=statement.where(ReviewItem.due_at<=now)
    items=s.scalars(statement.order_by(ReviewItem.due_at,ReviewItem.id))
    result=[]; blocked=blocked_lesson_ids(s)
    for item in items:
        if item.lesson_id in blocked: continue
        try: lesson=review_lesson(item,s)
        except HTTPException: continue
        exercise=next((e for e in lesson['exercises'] if e['id']==item.exercise_id),None)
        if exercise and (course is None or lesson['course']==course):
            result.append({'id':item.id,'course':lesson['course'],'lesson_title':lesson['title'],'due':item.due_at<=now,'due_at':item.due_at.isoformat()+'Z','exercise':public_exercise(exercise)})
    return result

class ReviewAnswer(BaseModel):
    response: str = Field(min_length=1,max_length=4000)
    session_id: int | None = None

@app.post('/api/review/{item_id}/answer')
def review_answer(item_id: int,data: ReviewAnswer,request: Request,u: User=Depends(user),s: Session=Depends(db)):
    check_origin(request); enforce_rate_limit(request,'review-answer',60)
    initial=s.get(ReviewItem,item_id)
    if not initial or initial.user_id!=u.id: raise HTTPException(404,'Review item not found')
    ensure_not_blocked(initial.lesson_id,s,lock=True)
    s.scalar(select(User).where(User.id==u.id).with_for_update())
    item=s.scalar(select(ReviewItem).where(ReviewItem.id==item_id).with_for_update().execution_options(populate_existing=True))
    if not item or item.user_id!=u.id: raise HTTPException(404,'Review item not found')
    now=datetime.now(timezone.utc).replace(tzinfo=None)
    was_due=item.due_at<=now
    lesson=review_lesson(item,s)
    review_session=None
    if data.session_id is not None:
        review_session=s.scalar(select(ReviewSession).where(ReviewSession.id==data.session_id).with_for_update())
        if not review_session or review_session.user_id!=u.id: raise HTTPException(404,'Review session not found')
        if review_session.finished or review_session.course!=lesson['course']: raise HTTPException(409,'Review session is unavailable')
    e=next((e for e in lesson['exercises'] if e['id']==item.exercise_id),None)
    if not e: raise HTTPException(404,'Exercise not found')
    correct=answer_matches(e,data.response)
    if correct and was_due:
        item.stage+=1
        if item.stage>3:
            snapshot=s.get(ReviewContent,item.id)
            if snapshot: s.delete(snapshot); s.flush()
            s.delete(item)
        else:
            item.due_at=now+timedelta(days=[1,3,7][item.stage-1])
    elif not correct:
        item.stage=0; item.due_at=now
    if review_session: review_session.answer_count+=1
    s.commit()
    return {'correct':correct,'explanation':e['explanation'],'correct_answer':correct_answer(e) if not correct else None,'practiced_early':not was_due}

# Draft authoring remains separate from learner-visible material until the
# editorial, audio, immutable-version and publication gates are implemented.
class DraftWord(BaseModel):
    target: str = Field(min_length=1,max_length=200)
    meaning: str = Field(min_length=1,max_length=300)
    example: str = Field(default='',max_length=400)
    example_translation: str = Field(default='',max_length=400)
    media_id: str | None = Field(default=None, max_length=64)

class DialogueLine(BaseModel):
    speaker: str = Field(min_length=1,max_length=80)
    text: str = Field(min_length=1,max_length=500)

class MatchPair(BaseModel):
    left: str = Field(min_length=1,max_length=80)
    right: str = Field(min_length=1,max_length=80)

class NormalizationPolicy(BaseModel):
    case_sensitive: bool = False
    punctuation_tolerant: bool = False
    apostrophe_variants: bool = True

class DraftExercise(BaseModel):
    id: str = Field(min_length=1,max_length=80,pattern=r'^[a-zA-Z0-9_-]+$')
    type: Literal['choice','text','order','listen_choice','listen_text','dialogue','match']
    prompt: str = Field(min_length=1,max_length=1000)
    options: list[str] = Field(default_factory=list,max_length=12)
    answers: list[str] = Field(default_factory=list,max_length=20)
    explanation: str = Field(min_length=1,max_length=2000)
    media_id: str | None = Field(default=None, max_length=64)
    dialogue: list[DialogueLine] = Field(default_factory=list,max_length=12)
    normalization: NormalizationPolicy = Field(default_factory=NormalizationPolicy)
    match_pairs: list[MatchPair] = Field(default_factory=list,max_length=8)

class OutlineReference(BaseModel):
    course: Literal['uz-ru','ru-uz']
    module_number: int = Field(ge=1,le=10)
    lesson_number: int = Field(ge=1,le=6)
    source_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')

class TemplateReference(BaseModel):
    template_id: str = Field(pattern=r'^(?:uz-ru|ru-uz)-[0-9]{2}-[0-9]{2}$')
    source_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')

class DraftContent(BaseModel):
    course: Literal['uz-ru','ru-uz']
    title: str = Field(min_length=1,max_length=200)
    objective: str = Field(min_length=1,max_length=1000)
    teaching_note: str = Field(default='',max_length=2000)
    minutes: int = Field(ge=1,le=60)
    module_number: int = Field(default=3,ge=1,le=10)
    lesson_number: int = Field(default=1,ge=1,le=100)
    outline_ref: OutlineReference | None = None
    template_ref: TemplateReference | None = None
    @model_validator(mode='before')
    @classmethod
    def infer_legacy_position(cls, value):
        if isinstance(value,dict) and 'lesson_number' not in value:
            value=dict(value); value['lesson_number']=(value.get('outline_ref') or {}).get('lesson_number',1)
        return value
    words: list[DraftWord] = Field(min_length=1,max_length=30)
    exercises: list[DraftExercise] = Field(min_length=1,max_length=50)

def validate_draft(content: DraftContent, s: Session):
    if content.outline_ref and (content.outline_ref.course!=content.course or content.outline_ref.module_number!=content.module_number or content.outline_ref.lesson_number!=content.lesson_number):
        raise HTTPException(422,'Outline direction, module, and lesson number must match the draft')
    for word in content.words:
        if bool(word.example.strip())!=bool(word.example_translation.strip()): raise HTTPException(422,'Provide both an example and its translation')
        if word.media_id and not s.get(MediaAsset,word.media_id): raise HTTPException(422,'Audio asset not found')
    ids=set()
    for e in content.exercises:
        if e.type=='dialogue' and (not e.dialogue or any(not line.speaker.strip() or not line.text.strip() for line in e.dialogue)): raise HTTPException(422,'Dialogue exercises need at least one non-empty turn')
        if e.type in ('listen_choice','listen_text') and not e.media_id: raise HTTPException(422,'Listening exercises require audio')
        if e.media_id and not s.get(MediaAsset,e.media_id): raise HTTPException(422,'Audio asset not found')
        if e.id in ids: raise HTTPException(422,'Exercise IDs must be unique')
        ids.add(e.id)
        if e.type=='match':
            left=[normalized(pair.left) for pair in e.match_pairs]; right=[normalized(pair.right) for pair in e.match_pairs]
            if len(left)<2 or any(not item for item in left+right) or len(set(left))!=len(left) or len(set(right))!=len(right):
                raise HTTPException(422,'Matching requires at least two distinct, non-empty pairs')
        elif not e.answers or any(not value.strip() for value in e.answers): raise HTTPException(422,'Answers cannot be blank')
        policy=e.normalization.model_dump()
        if e.type=='order':
            from collections import Counter
            token_policy={**policy,'punctuation_tolerant':False}
            tokens=[normalized(option,token_policy) for option in e.options]
            if len(tokens)<2 or any(not token or ' ' in token for token in tokens):
                raise HTTPException(422,'Word-order exercises require at least two single-word tokens')
            if any(Counter(normalized(answer,token_policy).split())!=Counter(tokens) for answer in e.answers):
                raise HTTPException(422,'Each accepted order must use every token exactly once')
        if e.type in ('choice','listen_choice','dialogue'):
            options=[normalized(option,policy) for option in e.options]
            if len(options)<2 or any(not option for option in options) or len(options)!=len(set(options)):
                raise HTTPException(422,'Choice exercises require distinct, non-empty options')
            if any(normalized(answer,policy) not in options for answer in e.answers):
                raise HTTPException(422,'Every choice answer must match an option')

def require_editor(u: User=Depends(user),s: Session=Depends(db)):
    if not s.get(EditorAccess,u.id): raise HTTPException(403,'Editor access required')
    return u

def require_owner(u: User=Depends(user),s: Session=Depends(db)):
    if not s.get(OwnerAccess,u.id): raise HTTPException(403,'Owner access required')
    return u

class OwnerPasswordChange(BaseModel):
    current_password: str = Field(min_length=1,max_length=128)
    new_password: str = Field(min_length=8,max_length=128)

@app.post('/api/owner/password')
def change_owner_password(data: OwnerPasswordChange,request: Request,u: User=Depends(require_owner),s: Session=Depends(db)):
    check_origin(request); enforce_rate_limit(request,'owner-password',5)
    account=s.scalar(select(User).where(User.id==u.id).with_for_update().execution_options(populate_existing=True))
    if not account or not hasher.verify(data.current_password,account.password_hash): raise HTTPException(400,'Current password is incorrect')
    if data.current_password==data.new_password: raise HTTPException(400,'Choose a different password')
    account.password_hash=hasher.hash(data.new_password)
    current_hash=hashlib.sha256(request.cookies['til_session'].encode()).hexdigest()
    for session in s.scalars(select(LoginSession).where(LoginSession.user_id==u.id,LoginSession.token!=current_hash)): s.delete(session)
    for link in s.scalars(select(PasswordReset).where(PasswordReset.user_id==u.id,PasswordReset.used==False)): link.used=True
    s.commit()
    return {'message':'Password changed. Other sessions have been signed out.'}

@app.get('/api/owner/overview')
def owner_overview(u: User=Depends(require_owner),s: Session=Depends(db)):
    from sqlalchemy import func
    def count(model,*conditions):
        return s.scalar(select(func.count()).select_from(model).where(*conditions)) or 0
    since=datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(days=7)
    active=s.scalar(select(func.count(func.distinct(AnalyticsEvent.user_id))).where(AnalyticsEvent.created_at>=since,AnalyticsEvent.event_name.in_(['lesson_completed','review_completed']))) or 0
    rating=s.scalar(select(func.avg(Feedback.clarity_rating)))
    return {'accounts':count(User),'lesson_attempts':count(Attempt),'lessons_completed':count(Attempt,Attempt.finished==True),'active_learners_7d':active,'feedback_total':count(Feedback),'feedback_open':count(Feedback,Feedback.status=='open'),'average_clarity':round(float(rating),2) if rating is not None else None,'sample_lessons':len(LESSONS),'published_lessons':count(PublishedLesson),'draft_lessons':count(DraftLesson),'audio_assets':count(MediaAsset),'pending_deletions':count(DeletionRequest,DeletionRequest.status=='pending')}

@app.get('/api/owner/accounts')
def owner_accounts(query: str=Query('',max_length=100),offset: int=Query(0,ge=0),limit: int=Query(25,ge=1,le=50),u: User=Depends(require_owner),s: Session=Depends(db)):
    term=query.strip().lower().replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
    statement=select(User).order_by(User.id).offset(offset).limit(limit+1)
    if term: statement=statement.where(User.email.ilike('%'+term+'%',escape='\\') | User.name.ilike('%'+term+'%',escape='\\'))
    accounts=list(s.scalars(statement)); more=len(accounts)>limit; accounts=accounts[:limit]
    return {'accounts':[{'id':a.id,'name':a.name,'email':a.email,'course':a.course,'editor':bool(s.get(EditorAccess,a.id)),'owner':bool(s.get(OwnerAccess,a.id)),'publisher':bool(s.get(PublisherAccess,a.id)),'deletion_requested':bool((d:=s.get(DeletionRequest,a.id)) and d.status=='pending')} for a in accounts],'more':more}

class EditorAccessChange(BaseModel):
    enabled: bool

@app.patch('/api/owner/accounts/{account_id}/editor')
def owner_change_editor(account_id: int,data: EditorAccessChange,request: Request,u: User=Depends(require_owner),s: Session=Depends(db)):
    check_origin(request)
    account=s.scalar(select(User).where(User.id==account_id).with_for_update())
    if not account: raise HTTPException(404,'Account not found')
    if not data.enabled and (s.get(OwnerAccess,account_id) or s.get(PublisherAccess,account_id)): raise HTTPException(409,'Owner and publisher accounts must retain editor access')
    access=s.get(EditorAccess,account_id)
    if data.enabled and not access: s.add(EditorAccess(user_id=account_id))
    if not data.enabled and access: s.delete(access)
    if bool(access)!=data.enabled: s.add(OwnerRoleEvent(actor_id=u.id,target_id=account_id,role='editor',enabled=data.enabled,created_at=datetime.now(timezone.utc).replace(tzinfo=None)))
    s.commit(); return {'editor':data.enabled}

@app.patch('/api/owner/accounts/{account_id}/publisher')
def owner_change_publisher(account_id: int,data: EditorAccessChange,request: Request,u: User=Depends(require_owner),s: Session=Depends(db)):
    check_origin(request)
    account=s.scalar(select(User).where(User.id==account_id).with_for_update())
    if not account: raise HTTPException(404,'Account not found')
    if data.enabled and not s.get(EditorAccess,account_id): raise HTTPException(409,'Publisher must already have editor access')
    if not data.enabled and s.get(OwnerAccess,account_id): raise HTTPException(409,'Owner publishing access cannot be removed here')
    access=s.get(PublisherAccess,account_id)
    if data.enabled and not access: s.add(PublisherAccess(user_id=account_id))
    if not data.enabled and access: s.delete(access)
    if bool(access)!=data.enabled: s.add(OwnerRoleEvent(actor_id=u.id,target_id=account_id,role='publisher',enabled=data.enabled,created_at=datetime.now(timezone.utc).replace(tzinfo=None)))
    s.commit(); return {'publisher':data.enabled}

@app.get('/api/owner/role-events')
def owner_role_events(offset: int=Query(0,ge=0),limit: int=Query(25,ge=1,le=50),u: User=Depends(require_owner),s: Session=Depends(db)):
    events=list(s.scalars(select(OwnerRoleEvent).order_by(OwnerRoleEvent.id.desc()).offset(offset).limit(limit+1)))
    return {'events':[{'id':e.id,'actor_id':e.actor_id,'target_id':e.target_id,'role':e.role,'enabled':e.enabled,'created_at':e.created_at.isoformat()+'Z'} for e in events[:limit]],'more':len(events)>limit}

@app.get('/api/owner/deletion-requests')
def owner_deletion_requests(offset: int=Query(0,ge=0),limit: int=Query(25,ge=1,le=50),u: User=Depends(require_owner),s: Session=Depends(db)):
    rows=list(s.execute(select(DeletionRequest,User).join(User,User.id==DeletionRequest.user_id).where(DeletionRequest.status=='pending').order_by(DeletionRequest.created_at,User.id).offset(offset).limit(limit+1)))
    return {'requests':[{'user_id':a.id,'email':a.email,'name':a.name,'created_at':r.created_at.isoformat()+'Z'} for r,a in rows[:limit]],'more':len(rows)>limit}

@app.get('/api/owner/deletion-requests/{account_id}')
def owner_deletion_preview(account_id: int,u: User=Depends(require_owner),s: Session=Depends(db)):
    from app.deletion import DeletionBlocked,deletion_plan
    try: _,counts=deletion_plan(s,account_id)
    except DeletionBlocked as e: raise HTTPException(409,str(e))
    return {'counts':counts}

class DeletionConfirmation(BaseModel):
    confirm: Literal['DELETE']

@app.post('/api/owner/deletion-requests/{account_id}/fulfill')
def owner_deletion_fulfill(account_id: int,data: DeletionConfirmation,request: Request,u: User=Depends(require_owner),s: Session=Depends(db)):
    from app.deletion import DeletionBlocked,fulfill_deletion
    check_origin(request)
    try: result=fulfill_deletion(s,account_id); s.commit()
    except DeletionBlocked as e: s.rollback(); raise HTTPException(409,str(e))
    return {'status':'deleted',**result}

def draft_view(d, s):
    publication=s.get(PublishedLesson,f'draft-{d.id}')
    blocked=s.get(LessonSafetyBlock,f'draft-{d.id}')
    latest=s.scalar(select(DraftRevision).where(DraftRevision.draft_id==d.id).order_by(DraftRevision.version.desc()))
    return {'id':d.id,'author_id':d.author_id,'updated_at':d.updated_at.isoformat()+'Z','status':'draft','version':latest.version if latest else 0,'published_revision_id':publication.revision_id if publication else None,'safety_blocked':bool(blocked),'content':json.loads(d.data)}

@app.get('/api/admin/drafts')
def list_drafts(u: User=Depends(require_editor),s: Session=Depends(db)):
    return [draft_view(d,s) for d in s.scalars(select(DraftLesson).order_by(DraftLesson.updated_at.desc()))]

@app.post('/api/admin/drafts')
def create_draft(content: DraftContent, request: Request,u: User=Depends(require_editor),s: Session=Depends(db)):
    check_origin(request); validate_draft(content,s); verify_outline_ref(content); verify_template_ref(content)
    d=DraftLesson(author_id=u.id,data=content.model_dump_json(),updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
    s.add(d); s.flush()
    s.add(DraftRevision(draft_id=d.id,version=1,author_id=u.id,data=d.data,created_at=d.updated_at))
    s.commit(); s.refresh(d); return draft_view(d,s)

@app.get('/api/admin/drafts/{draft_id}')
def get_draft(draft_id: int,u: User=Depends(require_editor),s: Session=Depends(db)):
    d=s.get(DraftLesson,draft_id)
    if not d: raise HTTPException(404,'Draft not found')
    return draft_view(d,s)

@app.patch('/api/admin/drafts/{draft_id}')
def update_draft(draft_id: int,content: DraftContent,request: Request,expected_version: int,u: User=Depends(require_editor),s: Session=Depends(db)):
    check_origin(request); validate_draft(content,s); verify_outline_ref(content); verify_template_ref(content); d=s.scalar(select(DraftLesson).where(DraftLesson.id==draft_id).with_for_update())
    if not d: raise HTTPException(404,'Draft not found')
    latest=s.scalar(select(DraftRevision).where(DraftRevision.draft_id==d.id).order_by(DraftRevision.version.desc()))
    version=latest.version if latest else 0
    if version != expected_version: raise HTTPException(409,'Draft changed; reload before saving')
    if not latest:
        s.add(DraftRevision(draft_id=d.id,version=1,author_id=d.author_id,data=d.data,created_at=d.updated_at)); version=1
    d.data=content.model_dump_json(); d.updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
    s.add(DraftRevision(draft_id=d.id,version=version+1,author_id=u.id,data=d.data,created_at=d.updated_at))
    try: s.commit()
    except IntegrityError:
        s.rollback(); raise HTTPException(409,'Draft changed; reload before saving')
    return draft_view(d,s)

@app.get('/api/admin/drafts/{draft_id}/revisions')
def draft_revisions(draft_id: int,u: User=Depends(require_editor),s: Session=Depends(db)):
    if not s.get(DraftLesson,draft_id): raise HTTPException(404,'Draft not found')
    revisions=s.scalars(select(DraftRevision).where(DraftRevision.draft_id==draft_id).order_by(DraftRevision.version.desc()))
    return [{'version':r.version,'author_id':r.author_id,'created_at':r.created_at.isoformat()+'Z','content':json.loads(r.data)} for r in revisions]

class FeedbackInput(BaseModel):
    lesson_id: str = Field(max_length=80)
    category: Literal['content','technical','accessibility','other']
    message: str = Field(default='',max_length=2000)
    clarity_rating: int | None = Field(default=None,strict=True,ge=1,le=5)
    attempt_id: int | None = Field(default=None,gt=0)
    exercise_id: str | None = Field(default=None,min_length=1,max_length=80)

def feedback_context(content: dict,exercise_id: str | None):
    if exercise_id is None: return content['title'],None
    exercise=next((e for e in content['exercises'] if e['id']==exercise_id),None)
    if not exercise: raise HTTPException(422,'Feedback exercise not found')
    return content['title'],exercise['prompt']

@app.post('/api/feedback')
def submit_feedback(data: FeedbackInput,request: Request,u: User=Depends(user),s: Session=Depends(db)):
    check_origin(request); enforce_rate_limit(request,'feedback',10)
    if data.attempt_id is not None:
        attempt=s.get(Attempt,data.attempt_id)
        if not attempt or attempt.user_id!=u.id or attempt.lesson_id!=data.lesson_id: raise HTTPException(404,'Attempt not found')
        content=attempt_lesson(attempt,s)
    else:
        try: content=lesson_or_404(data.lesson_id,s)
        except HTTPException as exc:
            if exc.status_code not in (404,410): raise
            attempt=s.scalar(select(Attempt).where(Attempt.user_id==u.id,Attempt.lesson_id==data.lesson_id).order_by(Attempt.id.desc()).limit(1))
            if not attempt: raise exc
            content=attempt_lesson(attempt,s)
    title,prompt=feedback_context(content,data.exercise_id)
    message=data.message.strip()
    if not message and data.clarity_rating is None: raise HTTPException(422,'Provide a rating or comment')
    f=Feedback(user_id=u.id,lesson_id=data.lesson_id,lesson_title=title,exercise_id=data.exercise_id,exercise_prompt=prompt,category=data.category,message=message,clarity_rating=data.clarity_rating,status='open',created_at=datetime.now(timezone.utc).replace(tzinfo=None))
    s.add(f); track(s,u.id,'feedback_submitted',{'lesson_id':data.lesson_id,'category':data.category}); s.commit(); return {'id':f.id,'status':f.status}

@app.post('/api/preview/{course}/feedback')
def submit_preview_feedback(course: Literal['uz-ru','ru-uz'],data: FeedbackInput,request: Request,s: Session=Depends(db)):
    check_origin(request); enforce_rate_limit(request,'preview-feedback',5)
    lesson_id=course+'-greetings'
    if data.lesson_id!=lesson_id or data.attempt_id is not None: raise HTTPException(404,'Preview not found')
    content=lesson_or_404(lesson_id,s)
    if data.exercise_id is not None and data.exercise_id!=content['exercises'][0]['id']: raise HTTPException(404,'Preview exercise not found')
    title,prompt=feedback_context(content,data.exercise_id)
    message=data.message.strip()
    if not message and data.clarity_rating is None: raise HTTPException(422,'Provide a rating or comment')
    report=Feedback(user_id=None,lesson_id=lesson_id,lesson_title=title,exercise_id=data.exercise_id,exercise_prompt=prompt,category=data.category,message=message,clarity_rating=data.clarity_rating,status='open',created_at=datetime.now(timezone.utc).replace(tzinfo=None))
    s.add(report); s.commit()
    return {'id':report.id,'status':report.status}

@app.get('/api/admin/feedback')
def list_feedback(status: Literal['open','resolved'] | None=None,offset: int=Query(default=0,ge=0,le=1000000),limit: int=Query(default=200,ge=1,le=200),u: User=Depends(require_editor),s: Session=Depends(db)):
    query=select(Feedback)
    if status: query=query.where(Feedback.status==status)
    rows=s.scalars(query.order_by(Feedback.created_at.desc(),Feedback.id.desc()).offset(offset).limit(limit))
    return [{'id':f.id,'lesson_id':f.lesson_id,'lesson_title':f.lesson_title,'exercise_id':f.exercise_id,'exercise_prompt':f.exercise_prompt,'category':f.category,'message':f.message,'clarity_rating':f.clarity_rating,'status':f.status,'created_at':f.created_at.isoformat()+'Z'} for f in rows]

@app.get('/api/admin/feedback-summary')
def feedback_summary(u: User=Depends(require_editor),s: Session=Depends(db)):
    from sqlalchemy import case,func
    total,rated,average,open_count=s.execute(select(func.count(Feedback.id),func.count(Feedback.clarity_rating),func.avg(Feedback.clarity_rating),func.sum(case((Feedback.status=='open',1),else_=0)))).one()
    return {'reports':total,'ratings':rated,'average_clarity':round(float(average),2) if average is not None else None,'open_reports':open_count or 0}

class FeedbackStatus(BaseModel):
    status: Literal['open','resolved']

@app.patch('/api/admin/feedback/{feedback_id}')
def update_feedback(feedback_id: int,data: FeedbackStatus,request: Request,u: User=Depends(require_editor),s: Session=Depends(db)):
    check_origin(request); item=s.get(Feedback,feedback_id)
    if not item: raise HTTPException(404,'Feedback not found')
    item.status=data.status; s.commit(); return {'id':item.id,'status':item.status}

class ResetRequest(BaseModel):
    email: EmailStr

class ResetConfirm(BaseModel):
    token: str = Field(min_length=30,max_length=200)
    password: str = Field(min_length=8,max_length=128)

def send_reset_email(address: str,token: str):
    host=os.getenv('SMTP_HOST')
    sender=os.getenv('SMTP_FROM')
    if not host or not sender:
        raise RuntimeError('SMTP_HOST and SMTP_FROM must be configured')
    origin=os.getenv('WEB_ORIGIN',DEFAULT_WEB_ORIGIN).rstrip('/')
    message=EmailMessage()
    message['Subject']='Til password reset'
    message['From']=sender
    message['To']=address
    message.set_content('Use this link to reset your Til password. It expires in 30 minutes.\n\n'+origin+'/?reset_token='+token+'\n\nIf you did not request this, you can ignore this message.')
    with smtplib.SMTP(host,int(os.getenv('SMTP_PORT','587')),timeout=10) as smtp:
        if os.getenv('SMTP_STARTTLS','true').lower()=='true': smtp.starttls()
        if os.getenv('SMTP_USERNAME'): smtp.login(os.environ['SMTP_USERNAME'],os.environ.get('SMTP_PASSWORD',''))
        smtp.send_message(message)

@app.post('/api/auth/password-reset/request')
def request_password_reset(data: ResetRequest,request: Request,s: Session=Depends(db)):
    check_origin(request); enforce_rate_limit(request,'reset-request',5)
    user_record=s.scalar(select(User).where(User.email==data.email.lower()))
    if user_record:
        token=secrets.token_urlsafe(48); now=datetime.now(timezone.utc).replace(tzinfo=None)
        record=PasswordReset(token_hash=hashlib.sha256(token.encode()).hexdigest(),user_id=user_record.id,expires=now+timedelta(minutes=30),used=False)
        s.add(record); s.commit()
        try: send_reset_email(user_record.email,token)
        except (OSError, smtplib.SMTPException, RuntimeError):
            # Keep the response identical for known and unknown accounts.
            s.delete(record); s.commit()
    return {'message':'If the account exists, reset instructions will be sent.'}

@app.post('/api/auth/password-reset/confirm')
def confirm_password_reset(data: ResetConfirm,request: Request,s: Session=Depends(db)):
    check_origin(request); enforce_rate_limit(request,'reset-confirm',10)
    token_hash=hashlib.sha256(data.token.encode()).hexdigest()
    initial=s.get(PasswordReset,token_hash)
    if not initial: raise HTTPException(400,'Invalid or expired reset link')
    account=s.scalar(select(User).where(User.id==initial.user_id).with_for_update())
    reset=s.scalar(select(PasswordReset).where(PasswordReset.token_hash==token_hash).with_for_update().execution_options(populate_existing=True))
    now=datetime.now(timezone.utc).replace(tzinfo=None)
    if not account or not reset or reset.used or reset.expires<now: raise HTTPException(400,'Invalid or expired reset link')
    account.password_hash=hasher.hash(data.password); reset.used=True
    # Revoke other reset links and all active sessions after a password change.
    for link in s.scalars(select(PasswordReset).where(PasswordReset.user_id==account.id,PasswordReset.used==False)): link.used=True
    for session in s.scalars(select(LoginSession).where(LoginSession.user_id==account.id)): s.delete(session)
    s.commit(); return {'message':'Password updated. Please sign in.'}

class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1,max_length=80)
    daily_goal: int | None = Field(default=None,ge=5,le=120)

@app.get('/api/profile')
def profile(u: User=Depends(user),s: Session=Depends(db)):
    settings=s.get(UserSettings,u.id); deletion=s.get(DeletionRequest,u.id)
    return {**public_user(u),'daily_goal':settings.daily_goal if settings else None,'deletion_requested':bool(deletion and deletion.status=='pending')}

@app.patch('/api/profile')
def update_profile(data: ProfileUpdate,request: Request,u: User=Depends(user),s: Session=Depends(db)):
    check_origin(request); name=data.name.strip()
    if not name: raise HTTPException(422,'Name cannot be blank')
    account=s.get(User,u.id); account.name=name
    settings=s.get(UserSettings,u.id)
    if not settings: settings=UserSettings(user_id=u.id,daily_goal=data.daily_goal); s.add(settings)
    else: settings.daily_goal=data.daily_goal
    s.commit(); return {'name':account.name,'daily_goal':settings.daily_goal}

@app.post('/api/profile/deletion-request')
def request_deletion(request: Request,u: User=Depends(user),s: Session=Depends(db)):
    check_origin(request); item=s.get(DeletionRequest,u.id)
    if not item:
        item=DeletionRequest(user_id=u.id,created_at=datetime.now(timezone.utc).replace(tzinfo=None),status='pending'); s.add(item)
    else: item.status='pending'
    s.commit(); return {'status':'pending'}

class ReviewDecision(BaseModel):
    version: int = Field(ge=1)
    decision: Literal['approved','changes_requested']
    notes: str = Field(min_length=1,max_length=2000)

@app.post('/api/admin/drafts/{draft_id}/reviews')
def review_draft(draft_id: int,data: ReviewDecision,request: Request,u: User=Depends(require_editor),s: Session=Depends(db)):
    check_origin(request)
    draft=s.scalar(select(DraftLesson).where(DraftLesson.id==draft_id).with_for_update())
    if not draft: raise HTTPException(404,'Draft not found')
    revision=s.scalar(select(DraftRevision).where(DraftRevision.draft_id==draft_id,DraftRevision.version==data.version))
    if not revision: raise HTTPException(404,'Revision not found')
    if revision.author_id==u.id: raise HTTPException(403,'A different editor must review this revision')
    notes=data.notes.strip()
    if not notes: raise HTTPException(422,'Review notes are required')
    review=DraftReview(draft_id=draft_id,version=data.version,reviewer_id=u.id,decision=data.decision,notes=notes,created_at=datetime.now(timezone.utc).replace(tzinfo=None))
    s.add(review); s.commit(); return {'id':review.id,'version':review.version,'decision':review.decision}

@app.get('/api/admin/drafts/{draft_id}/reviews')
def list_draft_reviews(draft_id: int,u: User=Depends(require_editor),s: Session=Depends(db)):
    if not s.get(DraftLesson,draft_id): raise HTTPException(404,'Draft not found')
    reviews=s.scalars(select(DraftReview).where(DraftReview.draft_id==draft_id).order_by(DraftReview.created_at.desc(),DraftReview.id.desc()))
    return [{'id':r.id,'version':r.version,'reviewer_id':r.reviewer_id,'decision':r.decision,'notes':r.notes,'created_at':r.created_at.isoformat()+'Z'} for r in reviews]

@app.get('/api/admin/analytics/overview')
def analytics_overview(u: User=Depends(require_editor),s: Session=Depends(db)):
    from sqlalchemy import func
    since=datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(days=7)
    counts=dict(s.execute(select(AnalyticsEvent.event_name,func.count()).where(AnalyticsEvent.created_at>=since).group_by(AnalyticsEvent.event_name)).all())
    active=s.scalar(select(func.count(func.distinct(AnalyticsEvent.user_id))).where(AnalyticsEvent.created_at>=since,AnalyticsEvent.event_name.in_(['lesson_completed','review_completed']))) or 0
    return {'period_days':7,'events':counts,'learners_completing_practice':active}

class ReviewSessionInput(BaseModel):
    course: Literal['uz-ru','ru-uz']

@app.post('/api/review/sessions')
def start_review_session(data: ReviewSessionInput,request: Request,u: User=Depends(user),s: Session=Depends(db)):
    check_origin(request)
    session=ReviewSession(user_id=u.id,course=data.course,answer_count=0,finished=False,started_at=datetime.now(timezone.utc).replace(tzinfo=None))
    s.add(session); track(s,u.id,'review_started',{'course':data.course}); s.commit(); s.refresh(session); return {'id':session.id}

@app.post('/api/review/sessions/{session_id}/complete')
def complete_review_session(session_id: int,request: Request,u: User=Depends(user),s: Session=Depends(db)):
    check_origin(request); session=s.scalar(select(ReviewSession).where(ReviewSession.id==session_id).with_for_update())
    if not session or session.user_id!=u.id: raise HTTPException(404,'Review session not found')
    if not session.answer_count: raise HTTPException(400,'Answer at least one review item')
    if not session.finished:
        session.finished=True; track(s,u.id,'review_completed',{'course':session.course,'answer_count':session.answer_count}); s.commit()
    return {'completed':True,'answer_count':session.answer_count}

MEDIA_ROOT=Path(os.getenv('MEDIA_ROOT','./.media')).resolve()
MAX_AUDIO_BYTES=5*1024*1024

def identify_audio(data: bytes):
    if data.startswith(b'RIFF') and data[8:12]==b'WAVE': return 'audio/wav'
    if data.startswith(b'OggS'): return 'audio/ogg'
    if data.startswith(b'ID3') or (len(data)>1 and data[0]==0xff and data[1]&0xe0==0xe0): return 'audio/mpeg'
    return None

@app.post('/api/admin/media')
async def upload_media(request: Request,attribution: str='',u: User=Depends(require_editor),s: Session=Depends(db)):
    check_origin(request)
    if len(attribution)>500: raise HTTPException(422,'Attribution is too long')
    chunks=[]; size=0
    async for chunk in request.stream():
        size+=len(chunk)
        if size>MAX_AUDIO_BYTES: raise HTTPException(413,'Audio exceeds 5 MB')
        chunks.append(chunk)
    data=b''.join(chunks); mime=identify_audio(data)
    if not mime: raise HTTPException(415,'Only WAV, Ogg, and MP3 audio are supported')
    asset_id=secrets.token_hex(24); MEDIA_ROOT.mkdir(mode=0o700,parents=True,exist_ok=True)
    path=MEDIA_ROOT / asset_id
    try:
        with path.open('xb') as out: out.write(data)
        asset=MediaAsset(id=asset_id,owner_id=u.id,mime=mime,attribution=attribution.strip(),rights_status='unverified',size=size,created_at=datetime.now(timezone.utc).replace(tzinfo=None))
        s.add(asset); s.commit()
    except Exception:
        path.unlink(missing_ok=True); raise
    return {'id':asset_id,'mime':mime,'size':size,'attribution':asset.attribution,'rights_status':asset.rights_status}

@app.get('/api/admin/media/{asset_id}')
def get_media(asset_id: str,u: User=Depends(require_editor),s: Session=Depends(db)):
    asset=s.get(MediaAsset,asset_id)
    if not asset or len(asset_id)!=48 or any(c not in '0123456789abcdef' for c in asset_id): raise HTTPException(404,'Media not found')
    path=MEDIA_ROOT / asset_id
    if not path.is_file(): raise HTTPException(404,'Media not found')
    return FileResponse(path,media_type=asset.mime,headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})

class MediaReviewInput(BaseModel):
    decision: Literal['approved','rejected']
    notes: str = Field(min_length=1,max_length=2000)

@app.get('/api/admin/media')
def list_media(u: User=Depends(require_editor),s: Session=Depends(db)):
    assets=s.scalars(select(MediaAsset).order_by(MediaAsset.created_at.desc()).limit(200))
    return [{'id':a.id,'owner_id':a.owner_id,'mime':a.mime,'size':a.size,'attribution':a.attribution,'rights_status':a.rights_status,'created_at':a.created_at.isoformat()+'Z'} for a in assets]

@app.get('/api/admin/media/{asset_id}/reviews')
def media_reviews(asset_id: str,u: User=Depends(require_editor),s: Session=Depends(db)):
    if not s.get(MediaAsset,asset_id): raise HTTPException(404,'Media not found')
    reviews=s.scalars(select(MediaReview).where(MediaReview.media_id==asset_id).order_by(MediaReview.created_at.desc(),MediaReview.id.desc()))
    return [{'id':r.id,'reviewer_id':r.reviewer_id,'decision':r.decision,'notes':r.notes,'created_at':r.created_at.isoformat()+'Z'} for r in reviews]

@app.post('/api/admin/media/{asset_id}/reviews')
def review_media(asset_id: str,data: MediaReviewInput,request: Request,u: User=Depends(require_editor),s: Session=Depends(db)):
    check_origin(request)
    asset=s.scalar(select(MediaAsset).where(MediaAsset.id==asset_id).with_for_update())
    if not asset: raise HTTPException(404,'Media not found')
    if asset.owner_id==u.id: raise HTTPException(403,'A different editor must review this audio')
    notes=data.notes.strip()
    if not notes: raise HTTPException(422,'Review notes are required')
    if data.decision=='approved' and not asset.attribution: raise HTTPException(422,'Source or attribution is required for approval')
    review=MediaReview(media_id=asset_id,reviewer_id=u.id,decision=data.decision,notes=notes,created_at=datetime.now(timezone.utc).replace(tzinfo=None))
    asset.rights_status=data.decision; s.add(review); s.commit()
    return {'id':review.id,'decision':review.decision,'rights_status':asset.rights_status}

@app.get('/api/admin/capabilities')
def editor_capabilities(u: User=Depends(require_editor),s: Session=Depends(db)):
    return {'publisher':bool(s.get(PublisherAccess,u.id))}

class PublishRequest(BaseModel):
    expected_version: int = Field(ge=1)

@app.post('/api/admin/drafts/{draft_id}/publish')
def publish_draft(draft_id: int,data: PublishRequest,request: Request,u: User=Depends(require_editor),s: Session=Depends(db)):
    check_origin(request)
    if not s.get(PublisherAccess,u.id): raise HTTPException(403,'Publisher access required')
    draft=s.scalar(select(DraftLesson).where(DraftLesson.id==draft_id).with_for_update())
    if not draft: raise HTTPException(404,'Draft not found')
    ensure_not_blocked(f'draft-{draft_id}',s)
    revision=s.scalar(select(DraftRevision).where(DraftRevision.draft_id==draft_id).order_by(DraftRevision.version.desc()))
    if not revision or revision.version!=data.expected_version: raise HTTPException(409,'Draft changed; reload before publishing')
    review=s.scalar(select(DraftReview).where(DraftReview.draft_id==draft_id,DraftReview.version==revision.version).order_by(DraftReview.created_at.desc(),DraftReview.id.desc()))
    if not review or review.decision!='approved' or review.reviewer_id==revision.author_id: raise HTTPException(409,'Latest revision needs an independent approval')
    content=DraftContent.model_validate_json(revision.data); validate_draft(content,s)
    for word in content.words:
        if not word.media_id: raise HTTPException(409,'Every vocabulary item needs reviewed audio')
    media_ids={w.media_id for w in content.words if w.media_id} | {e.media_id for e in content.exercises if e.media_id}
    # Stable lock order prevents two publishers from deadlocking on shared assets.
    for asset_id in sorted(media_ids):
        asset=s.scalar(select(MediaAsset).where(MediaAsset.id==asset_id).with_for_update())
        if not asset or asset.rights_status!='approved' or not (MEDIA_ROOT / asset.id).is_file(): raise HTTPException(409,'Every audio asset must be present and rights-approved')
    lesson_id=f'draft-{draft_id}'
    current=s.get(PublishedLesson,lesson_id)
    current_revision=s.get(PublishedRevision,current.revision_id) if current else None
    if current_revision and current_revision.draft_version==revision.version:
        return {'lesson_id':lesson_id,'revision_id':current_revision.id,'version':revision.version}
    payload=content.model_dump(); payload['eyebrow']=f'MODULE {content.module_number:02d} · LESSON'
    published=PublishedRevision(draft_id=draft_id,draft_version=revision.version,lesson_id=lesson_id,course=content.course,module_number=content.module_number,data=json.dumps(payload,ensure_ascii=False),publisher_id=u.id,created_at=datetime.now(timezone.utc).replace(tzinfo=None))
    s.add(published); s.flush()
    if current: current.revision_id=published.id
    else: s.add(PublishedLesson(lesson_id=lesson_id,revision_id=published.id))
    s.add(PublicationAction(revision_id=published.id,actor_id=u.id,action='published',reason='',created_at=datetime.now(timezone.utc).replace(tzinfo=None)))
    s.commit(); return {'lesson_id':lesson_id,'revision_id':published.id,'version':revision.version}

class WithdrawRequest(BaseModel):
    expected_revision_id: int = Field(ge=1)
    reason: str = Field(min_length=1,max_length=2000)

@app.post('/api/admin/drafts/{draft_id}/withdraw')
def withdraw_draft(draft_id: int,data: WithdrawRequest,request: Request,u: User=Depends(require_editor),s: Session=Depends(db)):
    check_origin(request)
    if not s.get(PublisherAccess,u.id): raise HTTPException(403,'Publisher access required')
    draft=s.scalar(select(DraftLesson).where(DraftLesson.id==draft_id).with_for_update())
    if not draft: raise HTTPException(404,'Draft not found')
    current=s.get(PublishedLesson,f'draft-{draft_id}')
    if not current: raise HTTPException(404,'Lesson is not published')
    if current.revision_id!=data.expected_revision_id: raise HTTPException(409,'Publication changed; reload before withdrawing')
    reason=data.reason.strip()
    if not reason: raise HTTPException(422,'Withdrawal reason is required')
    s.add(PublicationAction(revision_id=current.revision_id,actor_id=u.id,action='withdrawn',reason=reason,created_at=datetime.now(timezone.utc).replace(tzinfo=None)))
    s.delete(current); s.commit(); return {'withdrawn':True}

@app.get('/api/admin/drafts/{draft_id}/publications')
def publication_history(draft_id: int,u: User=Depends(require_editor),s: Session=Depends(db)):
    if not s.get(DraftLesson,draft_id): raise HTTPException(404,'Draft not found')
    rows=s.execute(select(PublicationAction,PublishedRevision).join(PublishedRevision,PublishedRevision.id==PublicationAction.revision_id).where(PublishedRevision.draft_id==draft_id).order_by(PublicationAction.id.desc()))
    return [{'action':action.action,'reason':action.reason,'actor_id':action.actor_id,'revision_id':revision.id,'draft_version':revision.draft_version,'created_at':action.created_at.isoformat()+'Z'} for action,revision in rows]

@app.get('/api/media/{asset_id}')
def published_media(asset_id: str,request: Request,s: Session=Depends(db)):
    asset=s.get(MediaAsset,asset_id)
    if not asset or asset.rights_status!='approved' or len(asset_id)!=48 or any(c not in '0123456789abcdef' for c in asset_id): raise HTTPException(404,'Media not found')
    def contains(payload):
        content=json.loads(payload)
        return any(item.get('media_id')==asset_id for item in content['words']+content['exercises'])
    blocked=blocked_lesson_ids(s)
    current=s.scalars(select(PublishedRevision).join(PublishedLesson,PublishedLesson.revision_id==PublishedRevision.id))
    allowed=any(revision.lesson_id not in blocked and contains(revision.data) for revision in current)
    if not allowed:
        try: viewer=user(request,s)
        except HTTPException: viewer=None
        if viewer:
            attempts=s.execute(select(AttemptContent,Attempt.lesson_id).join(Attempt,Attempt.id==AttemptContent.attempt_id).where(Attempt.user_id==viewer.id))
            allowed=any(lesson_id not in blocked and contains(snapshot.data) for snapshot,lesson_id in attempts)
            if not allowed:
                reviews=s.execute(select(ReviewContent,ReviewItem.lesson_id).join(ReviewItem,ReviewItem.id==ReviewContent.review_item_id).where(ReviewItem.user_id==viewer.id))
                allowed=any(lesson_id not in blocked and contains(snapshot.data) for snapshot,lesson_id in reviews)
    if not allowed: raise HTTPException(404,'Media not found')
    path=MEDIA_ROOT / asset_id
    if not path.is_file(): raise HTTPException(404,'Media not found')
    return FileResponse(path,media_type=asset.mime,headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})

@app.get('/api/continue')
def unfinished_lessons(u: User=Depends(user),s: Session=Depends(db)):
    attempts=s.scalars(select(Attempt).where(Attempt.user_id==u.id,Attempt.finished==False).order_by(Attempt.id.desc()))
    result=[]; blocked=blocked_lesson_ids(s)
    for attempt in attempts:
        if attempt.lesson_id in blocked: continue
        try: content=attempt_lesson(attempt,s)
        except HTTPException: continue
        result.append({'lesson_id':attempt.lesson_id,'title':content['title'],'course':content['course'],'answered':len(json.loads(attempt.answers)),'total':len(content['exercises'])})
    return result

# Internal staging is read-only and deliberately disconnected from publication.
STAGED_VOCABULARY = Path(os.getenv('STAGED_VOCABULARY', str(Path(__file__).resolve().parents[3] / 'project/staging/vocabulary-headings.jsonl')))

@app.get('/api/admin/vocabulary')
def staged_vocabulary(query: str = '', flagged: bool = False, offset: int = 0, limit: int = 25,
                      u: User=Depends(require_editor),s: Session=Depends(db)):
    if len(query)>100 or offset<0 or limit<1 or limit>100:
        raise HTTPException(422,'Invalid search or pagination')
    if not STAGED_VOCABULARY.is_file():
        raise HTTPException(503,'Vocabulary staging file is unavailable')
    needle=unicodedata.normalize('NFC',query.strip()).casefold()
    matches=[]
    try:
        with STAGED_VOCABULARY.open(encoding='utf-8') as source:
            for line in source:
                record=json.loads(line)
                if flagged and not record.get('flags'): continue
                searchable=' '.join(str(record.get(key) or '') for key in ('entry_id','candidate_headword','raw_heading'))
                if needle and needle not in unicodedata.normalize('NFC',searchable).casefold(): continue
                matches.append(record)
    except (OSError,UnicodeError,json.JSONDecodeError):
        raise HTTPException(503,'Vocabulary staging file cannot be read')
    page=matches[offset:offset+limit]
    if page:
        assessments=s.scalars(select(VocabularyAssessment).where(VocabularyAssessment.entry_id.in_([item['entry_id'] for item in page])).order_by(VocabularyAssessment.id.desc()))
        latest={}
        for a in assessments: latest.setdefault((a.entry_id,a.source_sha256),assessment_view(a))
        for item in page: item['assessment']=latest.get((item['entry_id'],item['source_sha256']))
    return {'total':len(matches),'offset':offset,'limit':limit,'items':page}

class VocabularyAssessmentInput(BaseModel):
    source_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    disposition: Literal['candidate','exclude','needs_review']
    level: Literal['unknown','a0','a1','later'] = 'unknown'
    topic: str = Field(default='',max_length=100)
    part_of_speech: str = Field(default='',max_length=100)
    notes: str = Field(min_length=1,max_length=2000)

def assessment_view(a: VocabularyAssessment):
    return {'id':a.id,'entry_id':a.entry_id,'source_sha256':a.source_sha256,'reviewer_id':a.reviewer_id,'disposition':a.disposition,'level':a.level,'topic':a.topic,'part_of_speech':a.part_of_speech,'notes':a.notes,'created_at':a.created_at.isoformat()+'Z'}

def staged_entry(entry_id: int):
    if not STAGED_VOCABULARY.is_file(): raise HTTPException(503,'Vocabulary staging file is unavailable')
    try:
        with STAGED_VOCABULARY.open(encoding='utf-8') as source:
            for line in source:
                item=json.loads(line)
                if item.get('entry_id')==entry_id: return item
    except (OSError,UnicodeError,json.JSONDecodeError): raise HTTPException(503,'Vocabulary staging file cannot be read')
    raise HTTPException(404,'Vocabulary entry not found')

@app.post('/api/admin/vocabulary/{entry_id}/assessments')
def assess_vocabulary(entry_id: int,data: VocabularyAssessmentInput,request: Request,u: User=Depends(require_editor),s: Session=Depends(db)):
    check_origin(request); item=staged_entry(entry_id)
    if item.get('source_sha256')!=data.source_sha256: raise HTTPException(409,'Source changed; reload before recording a review')
    notes=data.notes.strip()
    if not notes: raise HTTPException(422,'Review notes are required')
    assessment=VocabularyAssessment(entry_id=entry_id,source_sha256=data.source_sha256,reviewer_id=u.id,disposition=data.disposition,level=data.level,topic=data.topic.strip(),part_of_speech=data.part_of_speech.strip(),notes=notes,created_at=datetime.now(timezone.utc).replace(tzinfo=None))
    s.add(assessment); s.commit(); s.refresh(assessment); return assessment_view(assessment)

@app.get('/api/admin/vocabulary/{entry_id}/assessments')
def vocabulary_assessment_history(entry_id: int,u: User=Depends(require_editor),s: Session=Depends(db)):
    item=staged_entry(entry_id)
    assessments=s.scalars(select(VocabularyAssessment).where(VocabularyAssessment.entry_id==entry_id,VocabularyAssessment.source_sha256==item['source_sha256']).order_by(VocabularyAssessment.id.desc()))
    return [assessment_view(a) for a in assessments]

CURRICULUM_ROOT = Path(os.getenv('CURRICULUM_ROOT', str(Path(__file__).resolve().parents[3] / 'project/curriculum')))

@app.get('/api/admin/curriculum/{course}')
def curriculum_outline(course: Literal['uz-ru','ru-uz'],u: User=Depends(require_editor),s: Session=Depends(db)):
    path=CURRICULUM_ROOT / f'{course}.json'
    try:
        raw=path.read_bytes(); content=json.loads(raw.decode('utf-8'))
    except (OSError,UnicodeError,json.JSONDecodeError):
        raise HTTPException(503,'Curriculum outline is unavailable')
    if content.get('course')!=course or content.get('status')!='draft_unreviewed':
        raise HTTPException(503,'Curriculum outline is invalid')
    digest=hashlib.sha256(raw).hexdigest()
    by_position={(m['number'],lesson['number']):lesson for m in content['modules'] for lesson in m['lessons']}
    relevant=[]
    for draft in s.scalars(select(DraftLesson)):
        payload=json.loads(draft.data); ref=payload.get('outline_ref') or {}
        if ref.get('course')==course and (ref.get('module_number'),ref.get('lesson_number')) in by_position:
            relevant.append((draft,ref))
    ids=[draft.id for draft,_ in relevant]
    latest={}; decisions={}; pointers={}; published={}
    if ids:
        for revision in s.scalars(select(DraftRevision).where(DraftRevision.draft_id.in_(ids)).order_by(DraftRevision.version.desc())):
            latest.setdefault(revision.draft_id,revision)
        for review in s.scalars(select(DraftReview).where(DraftReview.draft_id.in_(ids)).order_by(DraftReview.id.desc())):
            decisions.setdefault((review.draft_id,review.version),review.decision)
        pointers={p.lesson_id:p.revision_id for p in s.scalars(select(PublishedLesson).where(PublishedLesson.lesson_id.in_([f'draft-{i}' for i in ids])))}
        if pointers:
            published={r.id:r for r in s.scalars(select(PublishedRevision).where(PublishedRevision.id.in_(list(pointers.values()))))}
    for draft,ref in relevant:
        revision=latest.get(draft.id); version=revision.version if revision else 0
        publication=published.get(pointers.get(f'draft-{draft.id}'))
        by_position[(ref['module_number'],ref['lesson_number'])].setdefault('drafts',[]).append({
            'id':draft.id,'title':json.loads(draft.data)['title'],'version':version,
            'review':decisions.get((draft.id,version)),'source_changed':ref.get('source_sha256')!=digest,
            'published_version':publication.draft_version if publication else None})
    return {**content,'source_sha256':digest}

def verify_outline_ref(content: DraftContent):
    ref=content.outline_ref
    if not ref: return
    path=CURRICULUM_ROOT / f'{ref.course}.json'
    try:
        raw=path.read_bytes(); outline=json.loads(raw.decode('utf-8'))
    except (OSError,UnicodeError,json.JSONDecodeError):
        raise HTTPException(503,'Curriculum outline is unavailable')
    if hashlib.sha256(raw).hexdigest()!=ref.source_sha256: raise HTTPException(409,'Outline changed; reselect it before saving')
    module=next((m for m in outline.get('modules',[]) if m.get('number')==ref.module_number),None)
    if outline.get('course')!=ref.course or not module or not any(l.get('number')==ref.lesson_number for l in module.get('lessons',[])):
        raise HTTPException(422,'Outline reference is invalid')

class OnboardingInput(BaseModel):
    course: Literal['uz-ru','ru-uz']
    motivation: Literal['daily','work','study','travel','other']
    daily_goal: int | None = Field(default=None,ge=5,le=120)

@app.get('/api/onboarding')
def onboarding_status(u: User=Depends(user),s: Session=Depends(db)):
    item=s.get(Onboarding,u.id); settings=s.get(UserSettings,u.id)
    return {'completed':bool(item),'course':u.course,'motivation':item.motivation if item else None,'daily_goal':settings.daily_goal if settings else None}

@app.post('/api/onboarding')
def complete_onboarding(data: OnboardingInput,request: Request,u: User=Depends(user),s: Session=Depends(db)):
    check_origin(request)
    account=s.scalar(select(User).where(User.id==u.id).with_for_update())
    item=s.get(Onboarding,u.id)
    is_new=item is None
    if is_new:
        item=Onboarding(user_id=u.id,motivation=data.motivation,completed_at=datetime.now(timezone.utc).replace(tzinfo=None)); s.add(item)
    else: item.motivation=data.motivation
    settings=s.get(UserSettings,u.id)
    if not settings: settings=UserSettings(user_id=u.id,daily_goal=data.daily_goal); s.add(settings)
    else: settings.daily_goal=data.daily_goal
    changed=account.course!=data.course
    account.course=data.course
    if is_new: track(s,u.id,'onboarding_completed',{'course':data.course,'motivation':data.motivation})
    if is_new or changed: track(s,u.id,'course_selected',{'course':data.course})
    s.commit()
    return {'completed':True,'course':account.course,'motivation':item.motivation,'daily_goal':settings.daily_goal}

class SafetyActionInput(BaseModel):
    reason: str = Field(min_length=1,max_length=2000)

@app.post('/api/admin/drafts/{draft_id}/safety-block')
def block_lesson(draft_id: int,data: SafetyActionInput,request: Request,u: User=Depends(require_editor),s: Session=Depends(db)):
    check_origin(request)
    if not s.get(PublisherAccess,u.id): raise HTTPException(403,'Publisher access required')
    draft=s.scalar(select(DraftLesson).where(DraftLesson.id==draft_id).with_for_update())
    if not draft: raise HTTPException(404,'Draft not found')
    lesson_id=f'draft-{draft_id}'
    if s.get(LessonSafetyBlock,lesson_id): raise HTTPException(409,'Lesson is already blocked')
    current=s.get(PublishedLesson,lesson_id)
    revision=s.get(PublishedRevision,current.revision_id) if current else s.scalar(select(PublishedRevision).where(PublishedRevision.draft_id==draft_id).order_by(PublishedRevision.id.desc()))
    if not revision: raise HTTPException(404,'No published revision found')
    reason=data.reason.strip()
    if not reason: raise HTTPException(422,'A reason is required')
    now=datetime.now(timezone.utc).replace(tzinfo=None)
    s.add(LessonSafetyBlock(lesson_id=lesson_id,revision_id=revision.id,actor_id=u.id,reason=reason,created_at=now))
    s.add(PublicationAction(revision_id=revision.id,actor_id=u.id,action='blocked',reason=reason,created_at=now))
    if current: s.delete(current)
    s.commit(); return {'blocked':True}

@app.post('/api/admin/drafts/{draft_id}/safety-unblock')
def unblock_lesson(draft_id: int,data: SafetyActionInput,request: Request,u: User=Depends(require_editor),s: Session=Depends(db)):
    check_origin(request)
    if not s.get(PublisherAccess,u.id): raise HTTPException(403,'Publisher access required')
    draft=s.scalar(select(DraftLesson).where(DraftLesson.id==draft_id).with_for_update())
    if not draft: raise HTTPException(404,'Draft not found')
    block=s.get(LessonSafetyBlock,f'draft-{draft_id}')
    if not block: raise HTTPException(404,'Lesson is not blocked')
    reason=data.reason.strip()
    if not reason: raise HTTPException(422,'A reason is required')
    s.add(PublicationAction(revision_id=block.revision_id,actor_id=u.id,action='unblocked',reason=reason,created_at=datetime.now(timezone.utc).replace(tzinfo=None)))
    s.delete(block); s.commit(); return {'blocked':False,'published':False}

LESSON_TEMPLATE_ROOT=Path(os.getenv('LESSON_TEMPLATE_ROOT',str(Path(__file__).resolve().parents[3] / 'project/curriculum/drafts')))

def read_lesson_template(template_id: str):
    if not re.fullmatch(r'(?:uz-ru|ru-uz)-[0-9]{2}-[0-9]{2}',template_id): raise HTTPException(404,'Template not found')
    path=LESSON_TEMPLATE_ROOT / f'{template_id}.json'
    try:
        raw=path.read_bytes(); item=json.loads(raw.decode('utf-8'))
    except FileNotFoundError: raise HTTPException(404,'Template not found')
    except (OSError,UnicodeError,json.JSONDecodeError): raise HTTPException(503,'Template unavailable')
    if item.get('status')!='draft_unreviewed' or not isinstance(item.get('content'),dict): raise HTTPException(503,'Template is invalid')
    digest=hashlib.sha256(raw).hexdigest()
    return item,digest

@app.get('/api/admin/lesson-templates')
def list_lesson_templates(u: User=Depends(require_editor)):
    if not LESSON_TEMPLATE_ROOT.is_dir(): raise HTTPException(503,'Template directory unavailable')
    entries=[]
    for path in sorted(LESSON_TEMPLATE_ROOT.glob('*.json')):
        if not re.fullmatch(r'(?:uz-ru|ru-uz)-[0-9]{2}-[0-9]{2}',path.stem): continue
        item,digest=read_lesson_template(path.stem); data=item['content']
        entries.append({'id':path.stem,'course':data.get('course'),'title':data.get('title'),'module_number':data.get('module_number'),'lesson_number':data.get('lesson_number'),'status':item['status'],'source_sha256':digest})
    return entries

@app.get('/api/admin/lesson-templates/{template_id}')
def lesson_template(template_id: str,u: User=Depends(require_editor)):
    item,digest=read_lesson_template(template_id)
    return {'id':template_id,'status':item['status'],'source_sha256':digest,'editorial_notes':item.get('editorial_notes',[]),'content':item['content']}

def verify_template_ref(content: DraftContent):
    ref=content.template_ref
    if not ref: return
    item,digest=read_lesson_template(ref.template_id)
    if digest!=ref.source_sha256: raise HTTPException(409,'Lesson template changed; reselect it before saving')
    source=item['content']
    if source.get('course')!=content.course or source.get('module_number')!=content.module_number or source.get('lesson_number')!=content.lesson_number:
        raise HTTPException(422,'Template direction and position must match the draft')


def load_local_preview_lessons():
    """Load clearly labelled, unreviewed content only for the local MVP demo."""
    previews={}
    for path in sorted(LESSON_TEMPLATE_ROOT.glob('*.json')):
        if not re.fullmatch(r'(?:uz-ru|ru-uz)-[0-9]{2}-[0-9]{2}',path.stem): continue
        item,_=read_lesson_template(path.stem)
        content=DraftContent.model_validate(item['content'])
        with Session(engine) as session: validate_draft(content,session)
        if not path.stem.startswith(content.course+'-'): raise ValueError('Preview course mismatch')
        lesson=content.model_dump(exclude_none=True)
        lesson['eyebrow']='ДЕМО-УРОК · НЕ ПРОВЕРЕН' if content.course=='ru-uz' else 'NAMUNA DARS · TEKSHIRILMAGAN'
        previews['preview-'+path.stem]=lesson
    return previews

if os.getenv('ENABLE_DEMO_CONTENT','false').lower()=='true':
    LESSONS.update(load_local_preview_lessons())

# Optional local single-origin demo. API routes above retain precedence.
if os.getenv('SERVE_BUILT_FRONTEND','false').lower()=='true':
    from fastapi.staticfiles import StaticFiles
    frontend_dist=Path(os.getenv('FRONTEND_DIST',str(Path(__file__).resolve().parents[2] / 'frontend' / 'dist')))
    if not (frontend_dist/'index.html').is_file():
        raise RuntimeError('Built frontend not found; run npm run build in app/frontend.')
    app.mount('/',StaticFiles(directory=frontend_dist,html=True),name='frontend')
