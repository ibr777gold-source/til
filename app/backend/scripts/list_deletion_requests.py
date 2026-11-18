"""List pending account deletion requests for the local operator."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.main import DeletionRequest, User, engine

with Session(engine) as session:
    rows = session.execute(select(DeletionRequest, User.email).join(User, User.id == DeletionRequest.user_id).where(DeletionRequest.status == 'pending').order_by(DeletionRequest.created_at))
    for request, email in rows:
        print(f'{request.user_id}\t{email}\t{request.created_at.isoformat()}Z\t{request.status}')
