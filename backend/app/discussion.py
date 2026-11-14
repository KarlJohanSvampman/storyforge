import uuid
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .models import (
    ContributionComment, ContributionRevision, Project, ProjectMembership,
    StoryContribution, StorySuggestion, SuggestionDecision, User,
)
from .projects import CurrentUser, DbSession, _membership, _project_or_404
from .schemas import (
    CommentCreate, CommentRead, SuggestionCreate, SuggestionDecisionCreate,
    SuggestionDecisionRead, SuggestionRead,
)

router = APIRouter(prefix="/api/projects/{project_id}/contributions/{contribution_id}", tags=["discussion"])


def _context(db: Session, project_id: uuid.UUID, contribution_id: uuid.UUID, user_id: uuid.UUID):
    project = _project_or_404(db, project_id)
    membership = _membership(db, project.id, user_id)
    contribution = db.scalar(select(StoryContribution).where(
        StoryContribution.id == contribution_id, StoryContribution.project_id == project_id,
    ))
    if contribution is None:
        raise HTTPException(status_code=404, detail="Contribution not found.")
    return project, membership, contribution


def _comment_read(comment: ContributionComment) -> CommentRead:
    return CommentRead(
        id=comment.id, contribution_id=comment.contribution_id,
        revision_id=comment.revision_id, parent_comment_id=comment.parent_comment_id,
        author_user_id=comment.author_user_id,
        author_display_name=comment.author.display_name if comment.author else "Unknown participant",
        body=comment.body, created_at=comment.created_at,
    )


def _suggestion_read(suggestion: StorySuggestion) -> SuggestionRead:
    decisions = [
        SuggestionDecisionRead(
            id=d.id, actor_user_id=d.actor_user_id,
            actor_display_name=d.actor.display_name if d.actor else "Unknown participant",
            previous_status=d.previous_status, new_status=d.new_status,
            note=d.note, created_at=d.created_at,
        )
        for d in sorted(suggestion.decisions, key=lambda item: item.created_at)
    ]
    return SuggestionRead(
        id=suggestion.id, contribution_id=suggestion.contribution_id,
        target_revision_id=suggestion.target_revision_id, author_user_id=suggestion.author_user_id,
        author_display_name=suggestion.author.display_name if suggestion.author else "Unknown participant",
        title=suggestion.title, rationale=suggestion.rationale,
        proposed_text=suggestion.proposed_text, status=suggestion.status,
        created_at=suggestion.created_at, updated_at=suggestion.updated_at,
        decisions=decisions,
    )


@router.get("/comments", response_model=list[CommentRead])
def list_comments(project_id: uuid.UUID, contribution_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _context(db, project_id, contribution_id, user.id)
    comments = db.scalars(
        select(ContributionComment)
        .where(ContributionComment.contribution_id == contribution_id, ContributionComment.status == "visible")
        .options(joinedload(ContributionComment.author))
        .order_by(ContributionComment.created_at.asc())
    ).all()
    return [_comment_read(comment) for comment in comments]


@router.post("/comments", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
def create_comment(
    project_id: uuid.UUID, contribution_id: uuid.UUID,
    payload: CommentCreate, db: DbSession, user: CurrentUser,
):
    _, _, contribution = _context(db, project_id, contribution_id, user.id)
    if contribution.status != "active":
        raise HTTPException(status_code=409, detail="Withdrawn contributions are read-only.")
    if not payload.body:
        raise HTTPException(status_code=422, detail="Comment cannot be blank.")
    if payload.revision_id:
        revision = db.get(ContributionRevision, payload.revision_id)
        if revision is None or revision.contribution_id != contribution.id:
            raise HTTPException(status_code=422, detail="The selected revision does not belong to this contribution.")
    if payload.parent_comment_id:
        parent = db.get(ContributionComment, payload.parent_comment_id)
        if parent is None or parent.contribution_id != contribution.id or parent.status != "visible":
            raise HTTPException(status_code=422, detail="Parent comment is not available in this contribution.")
    comment = ContributionComment(
        contribution_id=contribution.id, revision_id=payload.revision_id,
        parent_comment_id=payload.parent_comment_id, author_user_id=user.id,
        body=payload.body, status="visible",
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return _comment_read(comment)


@router.get("/suggestions", response_model=list[SuggestionRead])
def list_suggestions(project_id: uuid.UUID, contribution_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _context(db, project_id, contribution_id, user.id)
    suggestions = db.scalars(
        select(StorySuggestion)
        .where(StorySuggestion.contribution_id == contribution_id)
        .options(joinedload(StorySuggestion.author), joinedload(StorySuggestion.decisions).joinedload(SuggestionDecision.actor))
        .order_by(StorySuggestion.created_at.asc())
    ).unique().all()
    return [_suggestion_read(suggestion) for suggestion in suggestions]


@router.post("/suggestions", response_model=SuggestionRead, status_code=status.HTTP_201_CREATED)
def create_suggestion(
    project_id: uuid.UUID, contribution_id: uuid.UUID,
    payload: SuggestionCreate, db: DbSession, user: CurrentUser,
):
    _, _, contribution = _context(db, project_id, contribution_id, user.id)
    if contribution.status != "active":
        raise HTTPException(status_code=409, detail="Withdrawn contributions are read-only.")
    if not payload.title or not payload.proposed_text:
        raise HTTPException(status_code=422, detail="Suggestion title and proposed text cannot be blank.")
    revision = db.get(ContributionRevision, payload.target_revision_id)
    if revision is None or revision.contribution_id != contribution.id:
        raise HTTPException(status_code=422, detail="Suggestions must target a revision of this contribution.")
    suggestion = StorySuggestion(
        contribution_id=contribution.id, target_revision_id=revision.id,
        author_user_id=user.id, title=payload.title,
        rationale=payload.rationale, proposed_text=payload.proposed_text, status="pending",
    )
    db.add(suggestion)
    db.flush()
    db.add(SuggestionDecision(
        suggestion_id=suggestion.id, actor_user_id=user.id,
        previous_status=None, new_status="pending", note="Suggestion submitted.",
    ))
    db.commit()
    db.refresh(suggestion)
    return _suggestion_read(suggestion)


@router.post("/suggestions/{suggestion_id}/decision", response_model=SuggestionRead)
def decide_suggestion(
    project_id: uuid.UUID, contribution_id: uuid.UUID, suggestion_id: uuid.UUID,
    payload: SuggestionDecisionCreate, db: DbSession, user: CurrentUser,
):
    _, membership, _ = _context(db, project_id, contribution_id, user.id)
    if membership.role not in ("owner", "editor"):
        raise HTTPException(status_code=403, detail="Only project owners and editors can resolve suggestions.")
    suggestion = db.scalar(
        select(StorySuggestion)
        .where(StorySuggestion.id == suggestion_id, StorySuggestion.contribution_id == contribution_id)
        .options(joinedload(StorySuggestion.decisions).joinedload(SuggestionDecision.actor))
        .with_for_update()
    )
    if suggestion is None:
        raise HTTPException(status_code=404, detail="Suggestion not found.")
    if suggestion.status in ("accepted", "rejected"):
        raise HTTPException(status_code=409, detail="Accepted or rejected suggestions are closed.")
    if payload.status not in ("accepted", "rejected", "deferred"):
        raise HTTPException(status_code=422, detail="Unsupported suggestion decision.")
    previous = suggestion.status
    suggestion.status = payload.status
    decision = SuggestionDecision(
        suggestion_id=suggestion.id, actor_user_id=user.id,
        previous_status=previous, new_status=payload.status, note=payload.note,
    )
    db.add(decision)
    db.commit()
    db.refresh(suggestion)
    return _suggestion_read(suggestion)
