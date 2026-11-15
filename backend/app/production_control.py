import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    CastMemberInstance, CastingAssignment, ControllerAssignmentEvent, PossessionLease,
    Project, ProjectCharacter, ProjectMembership, ProjectPhaseTransition,
    SceneCharacterAssignment, SceneRun, Storyboard, StoryboardScene,
)
from .projects import CurrentUser, DbSession, _membership, _project_or_404
from .schemas import (
    CastMemberControllerUpdate, PossessionLeaseAction, PossessionLeaseCreate,
    PossessionLeaseRead, ProductionPhaseActivate, SceneRunStatusUpdate,
)

router = APIRouter(tags=["production control"])


def _runtime_editor(db: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> tuple[Project, object]:
    project = _project_or_404(db, project_id)
    member = _membership(db, project_id, user_id)
    if member.role not in ("owner", "editor"):
        raise HTTPException(status_code=403, detail="Only project owners and editors can direct production.")
    if project.current_phase not in ("storyboard", "production"):
        raise HTTPException(status_code=409, detail="Production controls require the storyboard or production phase.")
    return project, member


def _run_or_404(db: Session, project_id: uuid.UUID, run_id: uuid.UUID) -> SceneRun:
    run = db.scalar(select(SceneRun).where(SceneRun.id == run_id, SceneRun.project_id == project_id))
    if run is None:
        raise HTTPException(status_code=404, detail="Scene run not found.")
    return run


def _instance_or_404(db: Session, run_id: uuid.UUID, instance_id: uuid.UUID) -> CastMemberInstance:
    instance = db.scalar(select(CastMemberInstance).where(
        CastMemberInstance.id == instance_id, CastMemberInstance.scene_run_id == run_id,
    ))
    if instance is None:
        raise HTTPException(status_code=404, detail="Cast member instance not found in this scene run.")
    return instance


def _restore_lease(db: Session, lease: PossessionLease, instance: CastMemberInstance,
                   changed_by_user_id: uuid.UUID, reason: str) -> None:
    if lease.revoked_at is not None:
        return
    lease.revoked_at = datetime.now(timezone.utc)
    if lease.authority_epoch != instance.authority_epoch:
        return
    restore_type = lease.previous_controller_type or "system"
    restore_user = lease.previous_controller_user_id
    run = db.get(SceneRun, instance.scene_run_id)
    if restore_type == "user" and restore_user is not None:
        active = db.scalar(select(ProjectMembership.id).where(
            ProjectMembership.project_id == run.project_id,
            ProjectMembership.user_id == restore_user,
            ProjectMembership.status == "active",
        ))
        if active is None:
            restore_type, restore_user = "system", None
    old_type, old_user = instance.controller_type, instance.controller_user_id
    instance.authority_epoch += 1
    run.authority_epoch += 1
    instance.controller_type = restore_type
    instance.controller_user_id = restore_user
    instance.control_mode = lease.previous_control_mode or "autonomous"
    db.add(ControllerAssignmentEvent(
        scene_run_id=run.id, cast_member_instance_id=instance.id,
        authority_epoch=instance.authority_epoch,
        previous_controller_type=old_type, previous_controller_user_id=old_user,
        new_controller_type=restore_type, new_controller_user_id=restore_user,
        reason=reason, changed_by_user_id=changed_by_user_id,
    ))


@router.post("/api/projects/{project_id}/production/activate", response_model=dict)
def activate_production(project_id: uuid.UUID, payload: ProductionPhaseActivate, db: DbSession, user: CurrentUser):
    project = _project_or_404(db, project_id)
    member = _membership(db, project_id, user.id)
    if member.role != "owner":
        raise HTTPException(status_code=403, detail="Only the project owner can move the project into production.")
    project = db.scalar(select(Project).where(Project.id == project_id).with_for_update())
    if project.current_phase != "storyboard":
        raise HTTPException(status_code=409, detail="Only a storyboard-phase project can enter production.")
    storyboard = db.scalar(select(Storyboard).where(
        Storyboard.project_id == project_id,
    ).order_by(Storyboard.created_at.desc(), Storyboard.id.desc()).limit(1))
    if storyboard is None:
        raise HTTPException(status_code=409, detail="Initialize the storyboard before entering production.")
    scenes = db.scalars(select(StoryboardScene).where(StoryboardScene.storyboard_id == storyboard.id)).all()
    if not scenes:
        raise HTTPException(status_code=409, detail="Add at least one scene before entering production.")
    participants = db.execute(select(ProjectCharacter.id, ProjectCharacter.name).join(
        SceneCharacterAssignment, SceneCharacterAssignment.character_id == ProjectCharacter.id,
    ).where(
        SceneCharacterAssignment.scene_id.in_([scene.id for scene in scenes]),
        ProjectCharacter.status == "active",
    )).all()
    cast_ids = set(db.scalars(select(CastingAssignment.character_id).where(
        CastingAssignment.project_id == project_id, CastingAssignment.status == "active",
    )).all())
    missing = sorted({name for character_id, name in participants if character_id not in cast_ids})
    if missing:
        raise HTTPException(status_code=409, detail="Cast all active characters used by the storyboard before entering production: " + ", ".join(missing))
    previous = project.current_phase
    project.current_phase = "production"
    db.add(ProjectPhaseTransition(
        project_id=project.id, from_phase=previous, to_phase="production",
        actor_user_id=user.id, narrative_version_id=storyboard.narrative_version_id,
        reason=payload.reason,
    ))
    db.commit()
    return {"project_id": str(project_id), "current_phase": "production"}


@router.patch("/api/projects/{project_id}/scene-runs/{run_id}", response_model=dict)
def update_scene_run_status(project_id: uuid.UUID, run_id: uuid.UUID, payload: SceneRunStatusUpdate,
                            db: DbSession, user: CurrentUser):
    _runtime_editor(db, project_id, user.id)
    run = _run_or_404(db, project_id, run_id)
    transitions = {
        "prepared": {"running", "aborted"},
        "running": {"paused", "completed", "aborted"},
        "paused": {"running", "completed", "aborted"},
        "completed": set(), "aborted": set(),
    }
    if payload.status not in transitions[run.status]:
        raise HTTPException(status_code=409, detail=f"Cannot transition a {run.status} scene run to {payload.status}.")
    now = datetime.now(timezone.utc)
    run.status = payload.status
    if payload.status == "running" and run.started_at is None:
        run.started_at = now
    if payload.status in ("completed", "aborted"):
        run.ended_at = now
        leases = db.scalars(select(PossessionLease).where(
            PossessionLease.scene_run_id == run.id, PossessionLease.revoked_at.is_(None),
        ).with_for_update()).all()
        for lease in leases:
            instance = db.get(CastMemberInstance, lease.cast_member_instance_id)
            if instance:
                _restore_lease(db, lease, instance, user.id, "scene_run_ended")
    db.commit()
    db.refresh(run)
    return {"id": str(run.id), "status": run.status, "started_at": run.started_at, "ended_at": run.ended_at}


@router.post("/api/projects/{project_id}/scene-runs/{run_id}/cast-members/{instance_id}/controller", response_model=dict)
def change_controller(project_id: uuid.UUID, run_id: uuid.UUID, instance_id: uuid.UUID,
                      payload: CastMemberControllerUpdate, db: DbSession, user: CurrentUser):
    _runtime_editor(db, project_id, user.id)
    run = _run_or_404(db, project_id, run_id)
    if run.status in ("completed", "aborted"):
        raise HTTPException(status_code=409, detail="Controller assignment is frozen after a scene run ends.")
    instance = _instance_or_404(db, run.id, instance_id)
    if payload.controller_type == "user":
        if payload.controller_user_id is None:
            raise HTTPException(status_code=422, detail="A human controller must be selected.")
        active = db.scalar(select(ProjectMembership.id).where(
            ProjectMembership.project_id == project_id, ProjectMembership.user_id == payload.controller_user_id,
            ProjectMembership.status == "active",
        ))
        if active is None:
            raise HTTPException(status_code=422, detail="The human controller must be an active project member.")
    elif payload.controller_user_id is not None:
        raise HTTPException(status_code=422, detail="Only user controllers may have a controller_user_id.")
    previous_type, previous_user = instance.controller_type, instance.controller_user_id
    instance.authority_epoch += 1
    run.authority_epoch += 1
    instance.controller_type = payload.controller_type
    instance.controller_user_id = payload.controller_user_id
    instance.control_mode = payload.control_mode
    leases = db.scalars(select(PossessionLease).where(
        PossessionLease.cast_member_instance_id == instance.id, PossessionLease.revoked_at.is_(None),
    )).all()
    for lease in leases:
        lease.revoked_at = datetime.now(timezone.utc)
    db.add(ControllerAssignmentEvent(
        scene_run_id=run.id, cast_member_instance_id=instance.id,
        authority_epoch=instance.authority_epoch,
        previous_controller_type=previous_type, previous_controller_user_id=previous_user,
        new_controller_type=instance.controller_type, new_controller_user_id=instance.controller_user_id,
        reason=payload.reason.strip() or "controller_changed", changed_by_user_id=user.id,
    ))
    db.commit()
    return {"id": str(instance.id), "controller_type": instance.controller_type,
            "controller_user_id": str(instance.controller_user_id) if instance.controller_user_id else None,
            "control_mode": instance.control_mode, "authority_epoch": instance.authority_epoch}


@router.post("/api/projects/{project_id}/scene-runs/{run_id}/cast-members/{instance_id}/leases", response_model=PossessionLeaseRead, status_code=201)
def acquire_possession(project_id: uuid.UUID, run_id: uuid.UUID, instance_id: uuid.UUID,
                       payload: PossessionLeaseCreate, db: DbSession, user: CurrentUser):
    project = _project_or_404(db, project_id)
    member = _membership(db, project_id, user.id)
    run = _run_or_404(db, project_id, run_id)
    if run.status != "running":
        raise HTTPException(status_code=409, detail="Possession requires a running scene.")
    instance = _instance_or_404(db, run.id, instance_id)
    assigned = instance.controller_type == "user" and instance.controller_user_id == user.id
    director = member.role in ("owner", "editor")
    if not assigned and not director:
        raise HTTPException(status_code=403, detail="Only the assigned performer or a director/editor may possess this character.")
    now = datetime.now(timezone.utc)
    active = db.scalar(select(PossessionLease).where(
        PossessionLease.cast_member_instance_id == instance.id,
        PossessionLease.revoked_at.is_(None),
    ).with_for_update())
    if active and active.expires_at > now:
        raise HTTPException(status_code=409, detail="This character already has an active possession lease.")
    if active:
        _restore_lease(db, active, instance, user.id, "possession_lease_expired")
        db.flush()
    previous_type, previous_user, previous_mode = instance.controller_type, instance.controller_user_id, instance.control_mode
    instance.authority_epoch += 1
    run.authority_epoch += 1
    instance.controller_type = "user"
    instance.controller_user_id = user.id
    instance.control_mode = "direct"
    db.add(ControllerAssignmentEvent(
        scene_run_id=run.id, cast_member_instance_id=instance.id,
        authority_epoch=instance.authority_epoch,
        previous_controller_type=previous_type, previous_controller_user_id=previous_user,
        new_controller_type="user", new_controller_user_id=user.id,
        reason="possession_acquired", changed_by_user_id=user.id,
    ))
    lease = PossessionLease(
        scene_run_id=run.id, cast_member_instance_id=instance.id,
        authority_epoch=instance.authority_epoch, controller_type="user",
        controller_user_id=user.id, created_by_user_id=user.id,
        expires_at=now + timedelta(seconds=payload.duration_seconds),
        lease_token=uuid.uuid4(), previous_controller_type=previous_type,
        previous_controller_user_id=previous_user, previous_control_mode=previous_mode,
    )
    db.add(lease)
    db.commit()
    db.refresh(lease)
    return PossessionLeaseRead.model_validate(lease, from_attributes=True)


def _lease_or_404(db: Session, instance: CastMemberInstance, user_id: uuid.UUID, token: uuid.UUID) -> PossessionLease:
    lease = db.scalar(select(PossessionLease).where(
        PossessionLease.cast_member_instance_id == instance.id,
        PossessionLease.controller_user_id == user_id,
        PossessionLease.lease_token == token,
        PossessionLease.revoked_at.is_(None),
    ).with_for_update())
    if lease is None:
        raise HTTPException(status_code=404, detail="Active possession lease not found.")
    if lease.expires_at <= datetime.now(timezone.utc) or lease.authority_epoch != instance.authority_epoch:
        _restore_lease(db, lease, instance, user_id, "possession_lease_expired")
        db.commit()
        raise HTTPException(status_code=409, detail="Possession lease expired or its authority epoch is stale.")
    return lease


@router.post("/api/projects/{project_id}/scene-runs/{run_id}/cast-members/{instance_id}/leases/renew", response_model=PossessionLeaseRead)
def renew_possession(project_id: uuid.UUID, run_id: uuid.UUID, instance_id: uuid.UUID,
                     payload: PossessionLeaseAction, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id); _membership(db, project_id, user.id)
    instance = _instance_or_404(db, _run_or_404(db, project_id, run_id).id, instance_id)
    lease = _lease_or_404(db, instance, user.id, payload.lease_token)
    lease.expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)
    db.commit(); db.refresh(lease)
    return PossessionLeaseRead.model_validate(lease, from_attributes=True)


@router.post("/api/projects/{project_id}/scene-runs/{run_id}/cast-members/{instance_id}/leases/release", response_model=PossessionLeaseRead)
def release_possession(project_id: uuid.UUID, run_id: uuid.UUID, instance_id: uuid.UUID,
                       payload: PossessionLeaseAction, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id); _membership(db, project_id, user.id)
    instance = _instance_or_404(db, _run_or_404(db, project_id, run_id).id, instance_id)
    lease = _lease_or_404(db, instance, user.id, payload.lease_token)
    _restore_lease(db, lease, instance, user.id, "possession_released")
    db.commit(); db.refresh(lease)
    return PossessionLeaseRead.model_validate(lease, from_attributes=True)


@router.get("/api/projects/{project_id}/scene-runs/{run_id}/controller-events", response_model=list[dict])
def controller_history(project_id: uuid.UUID, run_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id); _membership(db, project_id, user.id)
    run = _run_or_404(db, project_id, run_id)
    events = db.scalars(select(ControllerAssignmentEvent).where(
        ControllerAssignmentEvent.scene_run_id == run.id,
    ).order_by(ControllerAssignmentEvent.created_at, ControllerAssignmentEvent.id)).all()
    return [{
        "id": str(item.id), "cast_member_instance_id": str(item.cast_member_instance_id),
        "authority_epoch": item.authority_epoch, "previous_controller_type": item.previous_controller_type,
        "previous_controller_user_id": str(item.previous_controller_user_id) if item.previous_controller_user_id else None,
        "new_controller_type": item.new_controller_type,
        "new_controller_user_id": str(item.new_controller_user_id) if item.new_controller_user_id else None,
        "reason": item.reason, "changed_by_user_id": str(item.changed_by_user_id),
        "created_at": item.created_at,
    } for item in events]
