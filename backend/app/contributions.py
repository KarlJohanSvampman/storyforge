import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .database import get_db
from .models import ContributionRevision, Project, ProjectMembership, StoryContribution, User
from .projects import CurrentUser, DbSession, _membership, _project_or_404
from .schemas import (
    ContributionCreate, ContributionDetail, ContributionRead,
    ContributionRevisionCreate, ContributionRevisionRead,
)

router = APIRouter(prefix="/api/projects/{project_id}/contributions", tags=["contributions"])


def _require_project_member(db: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> tuple[Project, ProjectMembership]:
    project = _project_or_404(db, project_id)
    membership = _membership(db, project.id, user_id)
    return project, membership


def _latest_revision(db: Session, contribution_id: uuid.UUID) -> ContributionRevision:
    revision = db.scalar(
        select(ContributionRevision)
        .where(ContributionRevision.contribution_id == contribution_id)
        .order_by(ContributionRevision.revision_number.desc())
        .limit(1)
    )
    if revision is None:
        raise HTTPException(status_code=500, detail="Contribution has no revision.")
    return revision


def _contribution_read(db: Session, contribution: StoryContribution) -> ContributionRead:
    revision = _latest_revision(db, contribution.id)
    author = db.get(User, contribution.author_user_id)
    return ContributionRead(
        id=contribution.id, project_id=contribution.project_id,
        author_user_id=contribution.author_user_id,
        author_display_name=author.display_name if author else "Unknown participant",
        title=contribution.title, status=contribution.status,
        current_revision_number=revision.revision_number, current_body=revision.body,
        created_at=contribution.created_at, updated_at=contribution.updated_at,
    )


def _revision_read(revision: ContributionRevision) -> ContributionRevisionRead:
    return ContributionRevisionRead(
        id=revision.id, revision_number=revision.revision_number, body=revision.body,
        author_user_id=revision.author_user_id,
        author_display_name=revision.author.display_name if revision.author else "Unknown participant",
        created_at=revision.created_at,
    )


@router.get("", response_model=list[ContributionRead])
def list_contributions(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _require_project_member(db, project_id, user.id)
    contributions = db.scalars(
        select(StoryContribution)
        .where(StoryContribution.project_id == project_id)
        .options(joinedload(StoryContribution.author))
        .order_by(StoryContribution.created_at.desc())
    ).all()
    return [_contribution_read(db, item) for item in contributions]


@router.post("", response_model=ContributionRead, status_code=status.HTTP_201_CREATED)
def create_contribution(project_id: uuid.UUID, payload: ContributionCreate, db: DbSession, user: CurrentUser):
    _, membership = _require_project_member(db, project_id, user.id)
    if membership.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot submit story contributions.")
    if not payload.title or not payload.body:
        raise HTTPException(status_code=422, detail="Contribution title and body cannot be blank.")

    contribution = StoryContribution(
        project_id=project_id, author_user_id=user.id, title=payload.title, status="active",
    )
    db.add(contribution)
    db.flush()
    revision = ContributionRevision(
        contribution_id=contribution.id, revision_number=1,
        body=payload.body, author_user_id=user.id,
    )
    db.add(revision)
    db.commit()
    db.refresh(contribution)
    return _contribution_read(db, contribution)


@router.get("/{contribution_id}", response_model=ContributionDetail)
def get_contribution(project_id: uuid.UUID, contribution_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _require_project_member(db, project_id, user.id)
    contribution = db.scalar(
        select(StoryContribution)
        .where(StoryContribution.id == contribution_id, StoryContribution.project_id == project_id)
        .options(joinedload(StoryContribution.revisions).joinedload(ContributionRevision.author),
                 joinedload(StoryContribution.author))
    )
    if contribution is None:
        raise HTTPException(status_code=404, detail="Contribution not found.")
    base = _contribution_read(db, contribution)
    revisions = [_revision_read(revision) for revision in contribution.revisions]
    return ContributionDetail(**base.model_dump(), revisions=revisions)


@router.patch("/{contribution_id}", response_model=ContributionRead)
def revise_contribution(
    project_id: uuid.UUID, contribution_id: uuid.UUID,
    payload: ContributionRevisionCreate, db: DbSession, user: CurrentUser,
):
    _, membership = _require_project_member(db, project_id, user.id)
    contribution = db.scalar(select(StoryContribution).where(
        StoryContribution.id == contribution_id, StoryContribution.project_id == project_id,
    ))
    if contribution is None:
        raise HTTPException(status_code=404, detail="Contribution not found.")
    if contribution.status != "active":
        raise HTTPException(status_code=409, detail="Withdrawn contributions cannot be revised.")
    can_edit = contribution.author_user_id == user.id or membership.role in ("owner", "editor")
    if not can_edit:
        raise HTTPException(status_code=403, detail="You can only revise your own contribution.")
    if not payload.body:
        raise HTTPException(status_code=422, detail="Contribution body cannot be blank.")

    latest = _latest_revision(db, contribution.id)
    revision = ContributionRevision(
        contribution_id=contribution.id, revision_number=latest.revision_number + 1,
        body=payload.body, author_user_id=user.id,
    )
    if payload.title is not None:
        if not payload.title:
            raise HTTPException(status_code=422, detail="Contribution title cannot be blank.")
        contribution.title = payload.title
    db.add(revision)
    db.commit()
    db.refresh(contribution)
    return _contribution_read(db, contribution)


@router.post("/{contribution_id}/withdraw", response_model=ContributionRead)
def withdraw_contribution(
    project_id: uuid.UUID, contribution_id: uuid.UUID, db: DbSession, user: CurrentUser,
):
    _, membership = _require_project_member(db, project_id, user.id)
    contribution = db.scalar(select(StoryContribution).where(
        StoryContribution.id == contribution_id, StoryContribution.project_id == project_id,
    ))
    if contribution is None:
        raise HTTPException(status_code=404, detail="Contribution not found.")
    can_withdraw = contribution.author_user_id == user.id or membership.role in ("owner", "editor")
    if not can_withdraw:
        raise HTTPException(status_code=403, detail="You cannot withdraw this contribution.")
    contribution.status = "withdrawn"
    db.commit()
    db.refresh(contribution)
    return _contribution_read(db, contribution)
