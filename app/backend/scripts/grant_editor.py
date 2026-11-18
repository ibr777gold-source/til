"""Grant editor access locally: python -m scripts.grant_editor EMAIL."""
import sys
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.main import EditorAccess, User, engine

if len(sys.argv) != 2:
    raise SystemExit('Usage: python -m scripts.grant_editor EMAIL')
with Session(engine) as session:
    user = session.scalar(select(User).where(User.email == sys.argv[1].lower()))
    if not user:
        raise SystemExit('Account not found; register it first.')
    if not session.get(EditorAccess, user.id):
        session.add(EditorAccess(user_id=user.id))
        session.commit()
    print('Editor access granted.')
