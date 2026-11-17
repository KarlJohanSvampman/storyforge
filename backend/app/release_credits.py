"""Revocable, user-controlled opt-in for public project credits."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from .models import Actor, CastingAssignment, Project, ProjectCreditConsent, StoryContribution
from .projects import CurrentUser, DbSession, _membership, _project_or_404
from .schemas import ProjectCreditConsentCreate, ProjectCreditConsentRead

router = APIRouter(prefix="/api/projects/{project_id}/credit-consents", tags=["release credits"])


@router.get("", response_model=list[ProjectCreditConsentRead])
def list_credit_consents(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id)
    _membership(db, project_id, user.id)
    return db.scalars(select(ProjectCreditConsent).where(
        ProjectCreditConsent.project_id == project_id,
    ).order_by(ProjectCreditConsent.consented_at.desc())).all()


@router.post("", response_model=ProjectCreditConsentRead, status_code=status.HTTP_201_CREATED)
def opt_in_to_credit(project_id: uuid.UUID, payload: ProjectCreditConsentCreate, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id)
    membership = _membership(db, project_id, user.id)
    if payload.category == "cast":
        if payload.actor_id is None:
            raise HTTPException(status_code=422, detail="Choose the actor profile you want credited.")
        actor = db.scalar(select(Actor).where(
            Actor.id == payload.actor_id, Actor.owner_user_id == user.id, Actor.status == "active",
        ))
        if actor is None:
            raise HTTPException(status_code=404, detail="Active actor profile not found for this user.")
        assignment = db.scalar(select(CastingAssignment).where(
            CastingAssignment.project_id == project_id,
            CastingAssignment.actor_id == actor.id,
            CastingAssignment.status == "active",
        ))
        if assignment is None:
            raise HTTPException(status_code=409, detail="That actor is not currently cast in this project.")
    elif payload.category == "contributor":
        contribution = db.scalar(select(StoryContribution).where(
            StoryContribution.project_id == project_id,
            StoryContribution.author_user_id == user.id,
        ))
        if contribution is None:
            raise HTTPException(status_code=409, detail="A contributor credit requires at least one project contribution.")
    elif membership.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot opt in to production credits.")

    existing = db.scalar(select(ProjectCreditConsent).where(
        ProjectCreditConsent.project_id == project_id,
        ProjectCreditConsent.user_id == user.id,
        ProjectCreditConsent.category == payload.category,
        ProjectCreditConsent.role_label == payload.role_label,
        ProjectCreditConsent.actor_id == payload.actor_id,
        ProjectCreditConsent.revoked_at.is_(None),
    ))
    if existing is not None:
        raise HTTPException(status_code=409, detail="An active consent for this credit already exists.")
    consent = ProjectCreditConsent(
        project_id=project_id, user_id=user.id, category=payload.category,
        role_label=payload.role_label, public_name=payload.public_name,
        actor_id=payload.actor_id,
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)
    return consent


@router.delete("/{consent_id}", response_model=ProjectCreditConsentRead)
def revoke_credit_consent(project_id: uuid.UUID, consent_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id)
    # Consent is personal: allow revocation even if the participant has left the project.
    consent = db.scalar(select(ProjectCreditConsent).where(
        ProjectCreditConsent.id == consent_id,
        ProjectCreditConsent.project_id == project_id,
        ProjectCreditConsent.user_id == user.id,
    ).with_for_update())
    if consent is None:
        raise HTTPException(status_code=404, detail="Your credit consent was not found.")
    if consent.revoked_at is None:
        consent.revoked_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(consent)
    return consent
