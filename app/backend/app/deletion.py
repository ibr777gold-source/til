"""Operator-run fulfillment of a pending learner account deletion request."""
import json
import secrets
from datetime import datetime, timezone
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session
from app.main import (
    AnalyticsEvent, AnswerReceipt, Attempt, AttemptContent, DeletionAudit,
    DeletionRequest, DemoCheckpointResult, DraftLesson, DraftReview, DraftRevision, EditorAccess,
    Feedback, LessonRemediation, LessonSafetyBlock, LoginSession, MediaAsset, MediaReview,
    Onboarding, OwnerAccess, OwnerRoleEvent, PasswordReset, Progress, PublicationAction, PublishedRevision,
    PublisherAccess, ReviewContent, ReviewItem, ReviewSession, User,
    UserSettings, VocabularyAssessment,
)

class DeletionBlocked(Exception):
    """Request cannot be fulfilled safely without an operator resolving dependencies."""

# Shared editorial content must never be removed as a side effect of deleting an account.
EDITORIAL_REFERENCES = (
    (OwnerAccess, OwnerAccess.user_id), (OwnerRoleEvent, OwnerRoleEvent.actor_id), (EditorAccess, EditorAccess.user_id), (PublisherAccess, PublisherAccess.user_id),
    (DraftLesson, DraftLesson.author_id), (DraftRevision, DraftRevision.author_id),
    (DraftReview, DraftReview.reviewer_id), (MediaAsset, MediaAsset.owner_id),
    (MediaReview, MediaReview.reviewer_id), (PublishedRevision, PublishedRevision.publisher_id),
    (PublicationAction, PublicationAction.actor_id), (LessonSafetyBlock, LessonSafetyBlock.actor_id),
    (VocabularyAssessment, VocabularyAssessment.reviewer_id),
)


def deletion_plan(session: Session, user_id: int, *, lock: bool = False):
    stmt=select(User).where(User.id==user_id)
    if lock: stmt=stmt.with_for_update()
    account=session.scalar(stmt)
    if not account: raise DeletionBlocked('Account not found.')
    request=session.get(DeletionRequest,user_id)
    if not request or request.status!='pending': raise DeletionBlocked('No pending deletion request.')
    if any(session.scalar(select(func.count()).select_from(model).where(column==user_id)) for model,column in EDITORIAL_REFERENCES):
        raise DeletionBlocked('Account has editorial access or shared content; an operator must resolve those dependencies first.')
    attempt_ids=select(Attempt.id).where(Attempt.user_id==user_id)
    review_ids=select(ReviewItem.id).where(ReviewItem.user_id==user_id)
    targets=(
        ('lesson_remediation',LessonRemediation,LessonRemediation.attempt_id.in_(attempt_ids)),
        ('answer_receipts',AnswerReceipt,AnswerReceipt.attempt_id.in_(attempt_ids)),
        ('attempt_content',AttemptContent,AttemptContent.attempt_id.in_(attempt_ids)),
        ('review_content',ReviewContent,ReviewContent.review_item_id.in_(review_ids)),
        ('attempts',Attempt,Attempt.user_id==user_id),
        ('review_items',ReviewItem,ReviewItem.user_id==user_id),
        ('review_sessions',ReviewSession,ReviewSession.user_id==user_id),
        ('progress',Progress,Progress.user_id==user_id),
        ('demo_checkpoint_results',DemoCheckpointResult,DemoCheckpointResult.user_id==user_id),
        ('feedback',Feedback,Feedback.user_id==user_id),
        ('analytics_events',AnalyticsEvent,AnalyticsEvent.user_id==user_id),
        ('password_resets',PasswordReset,PasswordReset.user_id==user_id),
        ('sessions',LoginSession,LoginSession.user_id==user_id),
        ('onboarding',Onboarding,Onboarding.user_id==user_id),
        ('settings',UserSettings,UserSettings.user_id==user_id),
        ('deletion_request',DeletionRequest,DeletionRequest.user_id==user_id),
    )
    counts={name:session.scalar(select(func.count()).select_from(model).where(condition)) for name,model,condition in targets}
    return targets,counts


def fulfill_deletion(session: Session,user_id: int):
    """Delete only requested, non-editorial account data in one transaction.

    Caller must commit or roll back the transaction. No email or user ID is retained
    in the receipt. A receipt does not by itself prove removal from external backups.
    """
    targets,counts=deletion_plan(session,user_id,lock=True)
    for _,model,condition in targets:
        session.execute(delete(model).where(condition))
    # Keep role history without retaining a reference to a deleted learner.
    session.execute(update(OwnerRoleEvent).where(OwnerRoleEvent.target_id==user_id).values(target_id=None))
    session.execute(delete(User).where(User.id==user_id))
    receipt=secrets.token_hex(24)
    session.add(DeletionAudit(receipt=receipt,completed_at=datetime.now(timezone.utc).replace(tzinfo=None),counts=json.dumps(counts,sort_keys=True)))
    session.flush()
    return {'receipt':receipt,'counts':counts}
