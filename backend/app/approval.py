import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    NarrativeApprovalDecision, NarrativeApprovalRound, NarrativeApprovalVoter,
    NarrativeApprovalVote, NarrativeDraft, NarrativeDraftVersion,
    Project, ProjectApprovalRule, ProjectMembership, ProjectPhaseTransition, User,
)
from .projects import CurrentUser, DbSession, _membership, _project_or_404
from .schemas import (
    ApprovalOverview, ApprovalRuleRead, ApprovalRuleUpdate,
    ApprovalVoteCreate, ApprovalVoteRead, ApprovalDecisionRead, ApprovalDecisionCreate,
    ApprovalVersionStatusRead, PhaseTransitionRead,
)

router = APIRouter(prefix="/api/projects/{project_id}", tags=["approval and phase progression"])
VOTING_ROLES = ("owner", "editor", "contributor")
PHASES_OPEN_FOR_APPROVAL = ("contributions", "development")


def _eligible_members(db: Session, project: Project, mode: str) -> dict[uuid.UUID, str]:
    memberships = db.scalars(
        select(ProjectMembership).where(
            ProjectMembership.project_id == project.id,
            ProjectMembership.status == "active",
            ProjectMembership.user_id.is_not(None),
            ProjectMembership.role.in_(VOTING_ROLES),
        )
    ).all()
    eligible = {
        membership.user_id: membership.role
        for membership in memberships
        if membership.user_id is not None
    }
    if mode == "owner_only":
        return {
            project.owner_user_id: eligible[project.owner_user_id]
        } if project.owner_user_id in eligible else {}
    return eligible


def _rule_read(db: Session, project_id: uuid.UUID) -> ApprovalRuleRead:
    rule = db.scalar(select(ProjectApprovalRule).where(ProjectApprovalRule.project_id == project_id))
    if rule is None:
        return ApprovalRuleRead(mode="owner_only", configured=False)
    return ApprovalRuleRead(
        mode=rule.mode,
        configured=True,
        updated_by_user_id=rule.updated_by_user_id,
        updated_at=rule.updated_at,
    )


def _decision_read(db: Session, decision: NarrativeApprovalDecision | None) -> ApprovalDecisionRead | None:
    if decision is None:
        return None
    actor = db.get(User, decision.actor_user_id)
    return ApprovalDecisionRead(
        id=decision.id,
        version_id=decision.version_id,
        actor_user_id=decision.actor_user_id,
        actor_display_name=actor.display_name if actor else "Unknown participant",
        outcome=decision.outcome,
        rule_mode=decision.rule_mode,
        eligible_voter_count=decision.eligible_voter_count,
        approve_count=decision.approve_count,
        reject_count=decision.reject_count,
        required_votes=decision.required_votes,
        note=decision.note,
        created_at=decision.created_at,
    )


def _approval_overview(db: Session, project: Project, user_id: uuid.UUID) -> ApprovalOverview:
    rule_read = _rule_read(db, project.id)
    mode = rule_read.mode
    draft = db.scalar(select(NarrativeDraft).where(NarrativeDraft.project_id == project.id))
    versions = []
    if draft:
        draft_versions = db.scalars(
            select(NarrativeDraftVersion)
            .where(NarrativeDraftVersion.draft_id == draft.id)
            .order_by(NarrativeDraftVersion.version_number)
        ).all()
        for version in draft_versions:
            ballot = db.scalar(
                select(NarrativeApprovalRound)
                .where(NarrativeApprovalRound.version_id == version.id)
            )
            if ballot:
                mode = ballot.rule_mode
                eligible_ids = set(db.scalars(
                    select(NarrativeApprovalVoter.voter_user_id)
                    .where(NarrativeApprovalVoter.round_id == ballot.id)
                ).all())
                eligible_voter_count = ballot.eligible_voter_count
                required_votes = ballot.required_votes
            else:
                mode = rule_read.mode
                eligible_members = _eligible_members(db, project, mode)
                eligible_ids = set(eligible_members)
                eligible_voter_count = len(eligible_ids)
                required_votes = 1 if mode == "owner_only" else (eligible_voter_count // 2 + 1)

            vote_events = db.scalars(
                select(NarrativeApprovalVote)
                .where(NarrativeApprovalVote.version_id == version.id)
                .order_by(NarrativeApprovalVote.created_at, NarrativeApprovalVote.id)
            ).all()
            latest_by_user: dict[uuid.UUID, NarrativeApprovalVote] = {}
            for vote in vote_events:
                latest_by_user[vote.voter_user_id] = vote
            counted_votes = [
                vote for voter_id, vote in latest_by_user.items()
                if voter_id in eligible_ids
            ]
            approve_count = sum(vote.choice == "approve" for vote in counted_votes)
            reject_count = sum(vote.choice == "reject" for vote in counted_votes)
            decision = db.scalar(
                select(NarrativeApprovalDecision)
                .where(NarrativeApprovalDecision.version_id == version.id)
            )
            # The final decision is authoritative; retain its exact decision-time tally snapshot.
            if decision:
                mode = decision.rule_mode
                eligible_voter_count = decision.eligible_voter_count
                required_votes = decision.required_votes
                approve_count = decision.approve_count
                reject_count = decision.reject_count
            vote_reads = []
            user_cache: dict[uuid.UUID, User | None] = {}
            for vote in vote_events:
                latest = latest_by_user.get(vote.voter_user_id) == vote
                if vote.voter_user_id not in user_cache:
                    user_cache[vote.voter_user_id] = db.get(User, vote.voter_user_id)
                voter = user_cache[vote.voter_user_id]
                vote_reads.append(ApprovalVoteRead(
                    id=vote.id,
                    version_id=vote.version_id,
                    voter_user_id=vote.voter_user_id,
                    voter_display_name=voter.display_name if voter else "Unknown participant",
                    choice=vote.choice,
                    note=vote.note,
                    created_at=vote.created_at,
                    is_latest=latest,
                    counts_toward_result=latest and vote.voter_user_id in eligible_ids,
                ))
            latest_user_vote = latest_by_user.get(user_id)
            can_vote = (
                version.version_number == draft.current_version_number
                and decision is None
                and project.current_phase in PHASES_OPEN_FOR_APPROVAL
                and user_id in eligible_ids
            )
            can_finalize = (
                user_id == project.owner_user_id
                and version.version_number == draft.current_version_number
                and decision is None
                and project.current_phase in PHASES_OPEN_FOR_APPROVAL
                and (approve_count >= required_votes or reject_count >= required_votes)
            )
            versions.append(ApprovalVersionStatusRead(
                version_id=version.id,
                version_number=version.version_number,
                is_current_version=version.version_number == draft.current_version_number,
                rule_mode=mode,
                ballot_opened_at=ballot.created_at if ballot else None,
                eligible_voter_count=eligible_voter_count,
                required_votes=required_votes,
                approve_count=approve_count,
                reject_count=reject_count,
                current_user_vote=latest_user_vote.choice if latest_user_vote else None,
                can_vote=can_vote,
                can_finalize=can_finalize,
                decision_outcome=decision.outcome if decision else None,
                votes=vote_reads,
                decision=_decision_read(db, decision),
            ))

    transitions = db.scalars(
        select(ProjectPhaseTransition)
        .where(ProjectPhaseTransition.project_id == project.id)
        .order_by(ProjectPhaseTransition.created_at, ProjectPhaseTransition.id)
    ).all()
    phase_reads = []
    for transition in transitions:
        actor = db.get(User, transition.actor_user_id)
        phase_reads.append(PhaseTransitionRead(
            id=transition.id,
            from_phase=transition.from_phase,
            to_phase=transition.to_phase,
            actor_user_id=transition.actor_user_id,
            actor_display_name=actor.display_name if actor else "Unknown participant",
            narrative_version_id=transition.narrative_version_id,
            reason=transition.reason,
            created_at=transition.created_at,
        ))
    return ApprovalOverview(
        project_id=project.id,
        current_phase=project.current_phase,
        rule=rule_read,
        versions=versions,
        phase_history=phase_reads,
    )


def _locked_project(db: Session, project_id: uuid.UUID) -> Project:
    project = db.scalar(select(Project).where(Project.id == project_id).with_for_update())
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


def _current_version(
    db: Session, project: Project, draft_id: uuid.UUID, version_id: uuid.UUID,
) -> tuple[NarrativeDraft, NarrativeDraftVersion]:
    draft = db.scalar(
        select(NarrativeDraft)
        .where(NarrativeDraft.id == draft_id, NarrativeDraft.project_id == project.id)
        .with_for_update()
    )
    if draft is None:
        raise HTTPException(status_code=404, detail="Narrative draft not found.")
    version = db.scalar(
        select(NarrativeDraftVersion).where(
            NarrativeDraftVersion.id == version_id,
            NarrativeDraftVersion.draft_id == draft.id,
        )
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Narrative draft version not found.")
    if version.version_number != draft.current_version_number:
        raise HTTPException(status_code=409, detail="Only the current draft version can be put to a vote.")
    if project.current_phase not in PHASES_OPEN_FOR_APPROVAL:
        raise HTTPException(status_code=409, detail="This project is no longer in a phase that accepts narrative approval.")
    existing = db.scalar(
        select(NarrativeApprovalDecision).where(NarrativeApprovalDecision.version_id == version.id)
    )
    if existing:
        raise HTTPException(status_code=409, detail="A final approval decision already exists for this version.")
    return draft, version


@router.get("/approval", response_model=ApprovalOverview)
def get_approval_overview(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    project = _project_or_404(db, project_id)
    _membership(db, project.id, user.id)
    return _approval_overview(db, project, user.id)


@router.put("/approval-rule", response_model=ApprovalOverview)
def update_approval_rule(
    project_id: uuid.UUID,
    payload: ApprovalRuleUpdate,
    db: DbSession,
    user: CurrentUser,
):
    project = _locked_project(db, project_id)
    membership = _membership(db, project.id, user.id)
    if membership.role != "owner":
        raise HTTPException(status_code=403, detail="Only the project owner can configure the approval rule.")
    if project.current_phase not in PHASES_OPEN_FOR_APPROVAL:
        raise HTTPException(status_code=409, detail="The approval rule is locked after the project enters storyboarding.")
    round_exists = db.scalar(
        select(NarrativeApprovalRound.id)
        .join(NarrativeDraftVersion, NarrativeDraftVersion.id == NarrativeApprovalRound.version_id)
        .join(NarrativeDraft, NarrativeDraft.id == NarrativeDraftVersion.draft_id)
        .where(NarrativeDraft.project_id == project.id)
        .limit(1)
    )
    vote_exists = db.scalar(
        select(NarrativeApprovalVote.id)
        .join(NarrativeDraftVersion, NarrativeDraftVersion.id == NarrativeApprovalVote.version_id)
        .join(NarrativeDraft, NarrativeDraft.id == NarrativeDraftVersion.draft_id)
        .where(NarrativeDraft.project_id == project.id)
        .limit(1)
    )
    decision_exists = db.scalar(
        select(NarrativeApprovalDecision.id)
        .join(NarrativeDraftVersion, NarrativeDraftVersion.id == NarrativeApprovalDecision.version_id)
        .join(NarrativeDraft, NarrativeDraft.id == NarrativeDraftVersion.draft_id)
        .where(NarrativeDraft.project_id == project.id)
        .limit(1)
    )
    if round_exists or vote_exists or decision_exists:
        raise HTTPException(status_code=409, detail="The approval rule cannot change after voting has started.")
    rule = db.scalar(
        select(ProjectApprovalRule).where(ProjectApprovalRule.project_id == project.id).with_for_update()
    )
    if rule is None:
        rule = ProjectApprovalRule(
            project_id=project.id, mode=payload.mode, updated_by_user_id=user.id,
        )
        db.add(rule)
    else:
        rule.mode = payload.mode
        rule.updated_by_user_id = user.id
    db.commit()
    return _approval_overview(db, project, user.id)


@router.post(
    "/draft/{draft_id}/versions/{version_id}/votes",
    response_model=ApprovalOverview,
    status_code=status.HTTP_201_CREATED,
)
def cast_approval_vote(
    project_id: uuid.UUID,
    draft_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: ApprovalVoteCreate,
    db: DbSession,
    user: CurrentUser,
):
    project = _locked_project(db, project_id)
    _membership(db, project.id, user.id)
    _, version = _current_version(db, project, draft_id, version_id)
    ballot = db.scalar(
        select(NarrativeApprovalRound)
        .where(NarrativeApprovalRound.version_id == version.id)
        .with_for_update()
    )
    if ballot:
        mode = ballot.rule_mode
        eligible_members = {
            voter.voter_user_id: voter.role_snapshot
            for voter in db.scalars(
                select(NarrativeApprovalVoter).where(NarrativeApprovalVoter.round_id == ballot.id)
            ).all()
        }
    else:
        rule = db.scalar(select(ProjectApprovalRule).where(ProjectApprovalRule.project_id == project.id))
        mode = rule.mode if rule else "owner_only"
        eligible_members = _eligible_members(db, project, mode)
        if not eligible_members:
            raise HTTPException(status_code=409, detail="There are no active eligible members for this approval rule.")
    eligible_ids = set(eligible_members)
    if user.id not in eligible_ids:
        if mode == "owner_only":
            raise HTTPException(status_code=403, detail="Only the project owner may vote under this approval rule.")
        raise HTTPException(status_code=403, detail="Only members eligible when this ballot opened may vote.")

    if ballot is None:
        eligible_count = len(eligible_members)
        required_count = 1 if mode == "owner_only" else (eligible_count // 2 + 1)
        ballot = NarrativeApprovalRound(
            version_id=version.id,
            rule_mode=mode,
            eligible_voter_count=eligible_count,
            required_votes=required_count,
        )
        db.add(ballot)
        db.flush()
        for voter_id, role_snapshot in eligible_members.items():
            db.add(NarrativeApprovalVoter(
                round_id=ballot.id,
                voter_user_id=voter_id,
                role_snapshot=role_snapshot,
            ))
        db.flush()
    latest = db.scalars(
        select(NarrativeApprovalVote)
        .where(
            NarrativeApprovalVote.version_id == version.id,
            NarrativeApprovalVote.voter_user_id == user.id,
        )
        .order_by(NarrativeApprovalVote.created_at.desc(), NarrativeApprovalVote.id.desc())
        .limit(1)
    ).first()
    if latest and latest.choice == payload.choice:
        raise HTTPException(status_code=409, detail="Your latest vote already has that choice.")
    db.add(NarrativeApprovalVote(
        version_id=version.id,
        voter_user_id=user.id,
        choice=payload.choice,
        note=payload.note,
    ))
    db.commit()
    return _approval_overview(db, project, user.id)


@router.post(
    "/draft/{draft_id}/versions/{version_id}/decision",
    response_model=ApprovalOverview,
)
def finalize_approval_decision(
    project_id: uuid.UUID,
    draft_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: ApprovalDecisionCreate,
    db: DbSession,
    user: CurrentUser,
):
    project = _locked_project(db, project_id)
    membership = _membership(db, project.id, user.id)
    if membership.role != "owner":
        raise HTTPException(status_code=403, detail="Only the project owner can finalize the approval decision.")
    draft, version = _current_version(db, project, draft_id, version_id)
    ballot = db.scalar(
        select(NarrativeApprovalRound)
        .where(NarrativeApprovalRound.version_id == version.id)
        .with_for_update()
    )
    if ballot is None:
        raise HTTPException(status_code=409, detail="Voting has not started for this narrative version.")
    mode = ballot.rule_mode
    eligible_ids = set(db.scalars(
        select(NarrativeApprovalVoter.voter_user_id)
        .where(NarrativeApprovalVoter.round_id == ballot.id)
    ).all())
    vote_events = db.scalars(
        select(NarrativeApprovalVote)
        .where(NarrativeApprovalVote.version_id == version.id)
        .order_by(NarrativeApprovalVote.created_at, NarrativeApprovalVote.id)
    ).all()
    latest_by_user: dict[uuid.UUID, NarrativeApprovalVote] = {}
    for vote in vote_events:
        latest_by_user[vote.voter_user_id] = vote
    counted_votes = [
        vote for voter_id, vote in latest_by_user.items()
        if voter_id in eligible_ids
    ]
    required_votes = ballot.required_votes
    approve_count = sum(vote.choice == "approve" for vote in counted_votes)
    reject_count = sum(vote.choice == "reject" for vote in counted_votes)
    if approve_count >= required_votes:
        outcome = "approved"
    elif reject_count >= required_votes:
        outcome = "rejected"
    else:
        raise HTTPException(
            status_code=409,
            detail=f"No final outcome yet: {approve_count} approve, {reject_count} reject; {required_votes} matching votes required.",
        )

    db.add(NarrativeApprovalDecision(
        version_id=version.id,
        actor_user_id=user.id,
        outcome=outcome,
        rule_mode=mode,
        eligible_voter_count=ballot.eligible_voter_count,
        approve_count=approve_count,
        reject_count=reject_count,
        required_votes=required_votes,
        note=payload.note,
    ))
    if outcome == "approved":
        previous_phase = project.current_phase
        project.current_phase = "storyboard"
        db.add(ProjectPhaseTransition(
            project_id=project.id,
            from_phase=previous_phase,
            to_phase="storyboard",
            actor_user_id=user.id,
            narrative_version_id=version.id,
            reason=f"Approved narrative draft version {version.version_number}.",
        ))
    db.commit()
    db.refresh(project)
    return _approval_overview(db, project, user.id)
