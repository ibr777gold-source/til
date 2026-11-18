"""Grant publication permission to an existing editor, by an operator."""
import sys
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.main import EditorAccess, PublisherAccess, User, engine

if len(sys.argv) != 2:
    raise SystemExit('Usage: python -m scripts.grant_publisher EMAIL')
with Session(engine) as session:
    account=session.scalar(select(User).where(User.email==sys.argv[1].lower()))
    if not account or not session.get(EditorAccess,account.id):
        raise SystemExit('Account must exist and already have editor access.')
    if not session.get(PublisherAccess,account.id):
        session.add(PublisherAccess(user_id=account.id)); session.commit()
    print('Publisher access granted.')
