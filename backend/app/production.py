import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import (
    Actor, CastMemberInstance, CastingAssignment, ControllerAssignmentEvent,
    EditExport, EditSequence, EditSequenceItem, PerformanceTake, PerformanceTakeEvent,
    PossessionLease, Project, ProjectCharacter, ProjectLocation, ProjectMembership,
    ProjectPhaseTransition, SceneCharacterAssignment, ScenePassageReference, SceneRun, SceneScriptVersion,
    Storyboard, StoryboardScene, User,
)
from .projects import CurrentUser, DbSession, _membership, _project_or_404
from .schemas import (
    CastMemberControllerUpdate, CastMemberInstanceRead, ControllerAssignmentEventRead,
    EditExportRead, EditSequenceCreate, EditSequenceItemCreate, EditSequenceItemRead,
    EditSequenceItemUpdate, EditSequenceRead, EditSequenceReorder,
    PerformanceEventBatchCreate, PerformanceTakeCreate, PerformanceTakeEventRead,
    PerformanceTakeRead, PerformanceTakeStatusUpdate, PossessionLeaseCreate, ProductionPhaseActivate,
    PossessionLeaseRead, PossessionLeaseRelease, SceneRunCreate, SceneRunRead,
    SceneRunStatusUpdate,
)

router = APIRouter(prefix="/api/projects/{project_id}/production", tags=["production"])


@router.post("/activate", response_model=dict)
def activate_production_phase(project_id: uuid.UUID, payload: ProductionPhaseActivate, db: DbSession, user: CurrentUser):
    project = _project_or_404(db, project_id)
    membership = _membership(db, project_id, user.id)
    if membership.role != "owner":
        raise HTTPException(status_code=403, detail="Only the project owner can move the project into production.")
    project = db.scalar(select(Project).where(Project.id == project_id).with_for_update())
    if project.current_phase != "storyboard":
        raise HTTPException(status_code=409, detail="Only a storyboard-phase project can enter production.")
    storyboard = db.scalar(select(Storyboard).where(
        Storyboard.project_id == project_id,
    ).order_by(Storyboard.created_at.desc(), Storyboard.id.desc()).limit(1))
    if storyboard is None:
        raise HTTPException(status_code=409, detail="Initialize the storyboard before entering production.")
    scenes = db.scalars(select(StoryboardScene).where(
        StoryboardScene.storyboard_id == storyboard.id,
    )).all()
    if not scenes:
        raise HTTPException(status_code=409, detail="Add at least one scene before entering production.")
    scene_ids = [scene.id for scene in scenes]
    participant_rows = db.execute(select(
        SceneCharacterAssignment.scene_id, ProjectCharacter.id, ProjectCharacter.name,
    ).join(ProjectCharacter, ProjectCharacter.id == SceneCharacterAssignment.character_id).where(
        SceneCharacterAssignment.scene_id.in_(scene_ids),
        ProjectCharacter.status == "active",
    )).all()
    active_cast = db.scalars(select(CastingAssignment.character_id).where(
        CastingAssignment.project_id == project_id, CastingAssignment.status == "active",
    )).all()
    active_cast_ids = set(active_cast)
    missing = sorted({name for _, character_id, name in participant_rows if character_id not in active_cast_ids})
    if missing:
        raise HTTPException(status_code=409, detail="Cast every active character used by the storyboard before entering production: " + ", ".join(missing))
    previous_phase = project.current_phase
    project.current_phase = "production"
    db.add(ProjectPhaseTransition(
        project_id=project.id, from_phase=previous_phase, to_phase="production",
        actor_user_id=user.id, narrative_version_id=storyboard.narrative_version_id,
        reason=payload.reason,
    ))
    db.commit()
    db.refresh(project)
    return {"project_id": str(project.id), "current_phase": project.current_phase}


def _project_access(db: Session, project_id: uuid.UUID, user_id: uuid.UUID, *, write: bool = False) -> Project:
    project = _project_or_404(db, project_id)
    member = _membership(db, project_id, user_id)
    if write and member.role not in ("owner", "editor"):
        raise HTTPException(status_code=403, detail="Only project owners and editors can manage production runtime.")
    if write and project.current_phase != "production":
        raise HTTPException(status_code=409, detail="Production runtime is available only after the project enters production.")
    return project


def _run_or_404(db: Session, project_id: uuid.UUID, run_id: uuid.UUID) -> SceneRun:
    run = db.scalar(select(SceneRun).where(SceneRun.id == run_id, SceneRun.project_id == project_id))
    if run is None:
        raise HTTPException(status_code=404, detail="Scene run not found in this project.")
    return run


def _instance_or_404(db: Session, run_id: uuid.UUID, instance_id: uuid.UUID) -> CastMemberInstance:
    item = db.scalar(select(CastMemberInstance).where(
        CastMemberInstance.id == instance_id, CastMemberInstance.scene_run_id == run_id,
    ))
    if item is None:
        raise HTTPException(status_code=404, detail="Cast member instance not found in this scene run.")
    return item


def _restore_possession_lease(
    db: Session, lease: PossessionLease, instance: CastMemberInstance,
    changed_by_user_id: uuid.UUID, reason: str,
) -> None:
    """Release a lease and restore its controller snapshot only if its epoch still owns authority."""
    if lease.released_at is not None:
        return
    lease.released_at = datetime.now(timezone.utc)
    if lease.authority_epoch != instance.authority_epoch:
        return
    restore_type = lease.previous_controller_type
    restore_user = lease.previous_controller_user_id
    if restore_type == "user" and restore_user is not None:
        member = db.scalar(select(ProjectMembership.id).where(
            ProjectMembership.user_id == restore_user,
            ProjectMembership.status == "active",
            ProjectMembership.project_id == db.scalar(select(SceneRun.project_id).where(SceneRun.id == instance.scene_run_id)),
        ))
        if member is None:
            restore_type, restore_user = "system", None
    previous_type, previous_user = instance.controller_type, instance.controller_user_id
    instance.authority_epoch += 1
    instance.controller_type = restore_type
    instance.controller_user_id = restore_user
    instance.control_mode = lease.previous_control_mode
    db.add(ControllerAssignmentEvent(
        cast_member_instance_id=instance.id, authority_epoch=instance.authority_epoch,
        previous_controller_type=previous_type, previous_controller_user_id=previous_user,
        new_controller_type=restore_type, new_controller_user_id=restore_user,
        control_mode=instance.control_mode, reason=reason,
        changed_by_user_id=changed_by_user_id,
    ))


def _run_read(db: Session, run: SceneRun) -> SceneRunRead:
    members = db.scalars(select(CastMemberInstance).where(
        CastMemberInstance.scene_run_id == run.id,
    ).order_by(CastMemberInstance.created_at, CastMemberInstance.id)).all()
    return SceneRunRead(
        id=run.id, project_id=run.project_id, storyboard_id=run.storyboard_id,
        scene_id=run.scene_id, run_number=run.run_number, status=run.status,
        scene_snapshot=run.scene_snapshot, created_by_user_id=run.created_by_user_id,
        started_at=run.started_at, ended_at=run.ended_at, created_at=run.created_at,
        cast_members=[CastMemberInstanceRead.model_validate(item, from_attributes=True) for item in members],
    )


def _take_read(db: Session, take: PerformanceTake) -> PerformanceTakeRead:
    events = db.scalars(select(PerformanceTakeEvent).where(
        PerformanceTakeEvent.take_id == take.id,
    ).order_by(PerformanceTakeEvent.event_order)).all()
    return PerformanceTakeRead(
        id=take.id, project_id=take.project_id, scene_run_id=take.scene_run_id,
        take_number=take.take_number, status=take.status, duration_ms=take.duration_ms,
        event_count=take.event_count, state_snapshot=take.state_snapshot,
        created_by_user_id=take.created_by_user_id, created_at=take.created_at,
        events=[PerformanceTakeEventRead.model_validate(item, from_attributes=True) for item in events],
    )


def _sequence_read(db: Session, sequence: EditSequence) -> EditSequenceRead:
    items = db.scalars(select(EditSequenceItem).where(
        EditSequenceItem.sequence_id == sequence.id,
    ).order_by(EditSequenceItem.item_order)).all()
    return EditSequenceRead(
        id=sequence.id, project_id=sequence.project_id, name=sequence.name,
        status=sequence.status, revision_number=sequence.revision_number,
        created_by_user_id=sequence.created_by_user_id, created_at=sequence.created_at,
        updated_at=sequence.updated_at,
        items=[EditSequenceItemRead.model_validate(item, from_attributes=True) for item in items],
    )


@router.post("/scene-runs", response_model=SceneRunRead, status_code=status.HTTP_201_CREATED)
def create_scene_run(project_id: uuid.UUID, payload: SceneRunCreate, db: DbSession, user: CurrentUser):
    project = _project_access(db, project_id, user.id, write=True)
    storyboard = db.scalar(select(Storyboard).where(
        Storyboard.project_id == project_id,
    ).order_by(Storyboard.created_at.desc(), Storyboard.id.desc()).limit(1))
    if storyboard is None:
        raise HTTPException(status_code=409, detail="Initialize a storyboard before creating a scene run.")
    scene = db.scalar(select(StoryboardScene).where(
        StoryboardScene.id == payload.scene_id, StoryboardScene.storyboard_id == storyboard.id,
    ))
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found in the current storyboard.")
    participants = db.scalars(select(ProjectCharacter).join(
        SceneCharacterAssignment, SceneCharacterAssignment.character_id == ProjectCharacter.id,
    ).where(SceneCharacterAssignment.scene_id == scene.id).order_by(ProjectCharacter.name)).all()
    assignments = db.scalars(select(CastingAssignment).where(
        CastingAssignment.project_id == project_id,
        CastingAssignment.status == "active",
    )).all()
    casts_by_character = {item.character_id: item for item in assignments}
    missing = [character.name for character in participants if character.id not in casts_by_character]
    if missing:
        raise HTTPException(status_code=409, detail="Every scene participant needs an active casting assignment before a run can be created: " + ", ".join(missing))
    if any(character.status != "active" for character in participants):
        raise HTTPException(status_code=409, detail="Archived characters cannot be instantiated in a new scene run.")

    location = db.get(ProjectLocation, scene.location_id) if scene.location_id else None
    script = db.scalar(select(SceneScriptVersion).where(
        SceneScriptVersion.scene_id == scene.id,
    ).order_by(SceneScriptVersion.revision_number.desc()).limit(1))
    passage_rows = db.scalars(select(ScenePassageReference).where(
        ScenePassageReference.scene_id == scene.id,
    ).order_by(ScenePassageReference.reference_order)).all()
    run_number = (db.scalar(select(func.max(SceneRun.run_number)).where(SceneRun.scene_id == scene.id)) or 0) + 1
    snapshot = {
        "scene": {
            "id": str(scene.id), "title": scene.title, "summary": scene.summary,
            "requirements": scene.requirements, "estimated_duration_seconds": scene.estimated_duration_seconds,
            "location": {"id": str(location.id), "name": location.name, "description": location.description,
                         "environment_type": location.environment_type, "time_period": location.time_period,
                         "visual_notes": location.visual_notes} if location else None,
        },
        "storyboard_id": str(storyboard.id),
        "approved_narrative_version_id": str(storyboard.narrative_version_id),
        "script": {"version_id": str(script.id), "revision_number": script.revision_number, "content": script.content} if script else None,
        "passages": [{"start_offset": item.start_offset, "end_offset": item.end_offset, "text": item.passage_snapshot} for item in passage_rows],
        "participants": [],
        "snapshot_created_at": datetime.now(timezone.utc).isoformat(),
    }
    run = SceneRun(
        project_id=project_id, storyboard_id=storyboard.id, scene_id=scene.id,
        run_number=run_number, scene_snapshot=snapshot, created_by_user_id=user.id,
    )
    db.add(run)
    db.flush()
    for character in participants:
        cast = casts_by_character[character.id]
        actor = db.get(Actor, cast.actor_id)
        if actor is None:
            raise HTTPException(status_code=409, detail="A casting assignment references a missing actor profile.")
        actor_snapshot = {"id": str(actor.id), "display_name": actor.display_name,
                          "biography": actor.biography, "performance_notes": actor.performance_notes}
        character_snapshot = {"id": str(character.id), "name": character.name,
                              "description": character.description, "visual_description": character.visual_description,
                              "personality_notes": character.personality_notes}
        instance = CastMemberInstance(
            scene_run_id=run.id, casting_assignment_id=cast.id, actor_id=actor.id,
            character_id=character.id, actor_snapshot=actor_snapshot,
            character_snapshot=character_snapshot, controller_type=cast.controller_type,
            controller_user_id=cast.controller_user_id, control_mode=cast.control_mode,
            initial_controller_type=cast.controller_type, initial_controller_user_id=cast.controller_user_id,
            initial_control_mode=cast.control_mode, state_snapshot={},
        )
        db.add(instance)
        db.flush()
        snapshot["participants"].append({"instance_id": str(instance.id), "actor": actor_snapshot,
                                          "character": character_snapshot, "controller_type": cast.controller_type,
                                          "controller_user_id": str(cast.controller_user_id) if cast.controller_user_id else None,
                                          "control_mode": cast.control_mode})
        db.add(ControllerAssignmentEvent(
            cast_member_instance_id=instance.id, authority_epoch=instance.authority_epoch,
            previous_controller_type="system", previous_controller_user_id=None,
            new_controller_type=instance.controller_type, new_controller_user_id=instance.controller_user_id,
            control_mode=instance.control_mode, reason="scene_run_initialized", changed_by_user_id=user.id,
        ))
    run.scene_snapshot = snapshot
    db.commit()
    db.refresh(run)
    return _run_read(db)


@router.get("/scene-runs", response_model=list[SceneRunRead])
def list_scene_runs(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id)
    runs = db.scalars(select(SceneRun).where(SceneRun.project_id == project_id).order_by(
        SceneRun.created_at.desc(), SceneRun.run_number.desc(),
    )).all()
    return [_run_read(db, item) for item in runs]


@router.get("/scene-runs/{run_id}", response_model=SceneRunRead)
def get_scene_run(project_id: uuid.UUID, run_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id)
    return _run_read(db, _run_or_404(db, project_id, run_id))


@router.patch("/scene-runs/{run_id}", response_model=SceneRunRead)
def update_scene_run(project_id: uuid.UUID, run_id: uuid.UUID, payload: SceneRunStatusUpdate, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id, write=True)
    run = _run_or_404(db, project_id, run_id)
    allowed = {"ready": {"running", "abandoned"}, "running": {"paused", "completed", "abandoned"},
               "paused": {"running", "completed", "abandoned"}, "completed": set(), "abandoned": set()}
    if payload.status not in allowed[run.status]:
        raise HTTPException(status_code=409, detail=f"Cannot transition a scene run from {run.status} to {payload.status}.")
    run.status = payload.status
    if payload.status == "running" and run.started_at is None:
        run.started_at = datetime.now(timezone.utc)
    if payload.status in ("completed", "abandoned"):
        run.ended_at = datetime.now(timezone.utc)
        leases = db.scalars(select(PossessionLease).join(
            CastMemberInstance, CastMemberInstance.id == PossessionLease.cast_member_instance_id,
        ).where(CastMemberInstance.scene_run_id == run.id, PossessionLease.released_at.is_(None))).all()
        for lease in leases:
            instance = db.get(CastMemberInstance, lease.cast_member_instance_id)
            if instance is not None:
                _restore_possession_lease(db, lease, instance, user.id, "scene_run_ended")
            else:
                lease.released_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return _run_read(db, run)


@router.post("/scene-runs/{run_id}/instances/{instance_id}/controller", response_model=CastMemberInstanceRead)
def update_instance_controller(project_id: uuid.UUID, run_id: uuid.UUID, instance_id: uuid.UUID,
                               payload: CastMemberControllerUpdate, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id, write=True)
    run = _run_or_404(db, project_id, run_id)
    if run.status in ("completed", "abandoned"):
        raise HTTPException(status_code=409, detail="Controller assignments are frozen after a scene run ends.")
    instance = _instance_or_404(db, run.id, instance_id)
    if payload.controller_type == "user":
        if payload.controller_user_id is None:
            raise HTTPException(status_code=422, detail="A human controller must be selected.")
        member = db.scalar(select(ProjectMembership.id).where(
            ProjectMembership.project_id == project_id, ProjectMembership.user_id == payload.controller_user_id,
            ProjectMembership.status == "active",
        ))
        if member is None:
            raise HTTPException(status_code=422, detail="The human controller must be an active project member.")
    elif payload.controller_user_id is not None:
        raise HTTPException(status_code=422, detail="Only user controllers may have a controller_user_id.")
    previous_type, previous_user = instance.controller_type, instance.controller_user_id
    instance.authority_epoch += 1
    instance.controller_type = payload.controller_type
    instance.controller_user_id = payload.controller_user_id
    instance.control_mode = payload.control_mode
    active_leases = db.scalars(select(PossessionLease).where(
        PossessionLease.cast_member_instance_id == instance.id, PossessionLease.released_at.is_(None),
    )).all()
    now = datetime.now(timezone.utc)
    for lease in active_leases:
        lease.released_at = now
    db.add(ControllerAssignmentEvent(
        cast_member_instance_id=instance.id, authority_epoch=instance.authority_epoch,
        previous_controller_type=previous_type, previous_controller_user_id=previous_user,
        new_controller_type=instance.controller_type, new_controller_user_id=instance.controller_user_id,
        control_mode=instance.control_mode, reason=payload.reason.strip() or "controller_changed",
        changed_by_user_id=user.id,
    ))
    db.commit()
    db.refresh(instance)
    return CastMemberInstanceRead.model_validate(instance, from_attributes=True)


@router.get("/scene-runs/{run_id}/controller-events", response_model=list[ControllerAssignmentEventRead])
def list_controller_events(project_id: uuid.UUID, run_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id)
    run = _run_or_404(db, project_id, run_id)
    events = db.scalars(select(ControllerAssignmentEvent).join(
        CastMemberInstance, CastMemberInstance.id == ControllerAssignmentEvent.cast_member_instance_id,
    ).where(CastMemberInstance.scene_run_id == run.id).order_by(
        ControllerAssignmentEvent.created_at, ControllerAssignmentEvent.authority_epoch,
    )).all()
    return [ControllerAssignmentEventRead.model_validate(item, from_attributes=True) for item in events]


@router.post("/scene-runs/{run_id}/instances/{instance_id}/lease", response_model=PossessionLeaseRead, status_code=status.HTTP_201_CREATED)
def acquire_possession_lease(project_id: uuid.UUID, run_id: uuid.UUID, instance_id: uuid.UUID,
                             payload: PossessionLeaseCreate, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id)
    run = _run_or_404(db, project_id, run_id)
    if run.status != "running":
        raise HTTPException(status_code=409, detail="Direct possession is available only while the scene run is running.")
    instance = _instance_or_404(db, run.id, instance_id)
    membership = _membership(db, project_id, user.id)
    assigned_human = instance.controller_type == "user" and instance.controller_user_id == user.id
    director_override = membership.role in ("owner", "editor")
    if instance.status != "active" or not (assigned_human or director_override):
        raise HTTPException(status_code=403, detail="Direct possession requires the assigned performer or a project director/editor.")
    now = datetime.now(timezone.utc)
    current = db.scalar(select(PossessionLease).where(
        PossessionLease.cast_member_instance_id == instance.id, PossessionLease.released_at.is_(None),
    ).with_for_update())
    if current and current.expires_at > now:
        raise HTTPException(status_code=409, detail="This character already has an active possession lease.")
    if current:
        _restore_possession_lease(db, current, instance, user.id, "possession_lease_expired")
        db.flush()
    previous_type, previous_user, previous_mode = instance.controller_type, instance.controller_user_id, instance.control_mode
    instance.authority_epoch += 1
    instance.controller_type = "user"
    instance.controller_user_id = user.id
    instance.control_mode = "direct"
    db.add(ControllerAssignmentEvent(
        cast_member_instance_id=instance.id, authority_epoch=instance.authority_epoch,
        previous_controller_type=previous_type, previous_controller_user_id=previous_user,
        new_controller_type="user", new_controller_user_id=user.id,
        control_mode="direct", reason="possession_acquired", changed_by_user_id=user.id,
    ))
    lease = PossessionLease(
        cast_member_instance_id=instance.id, controller_user_id=user.id,
        previous_controller_type=previous_type, previous_controller_user_id=previous_user,
        previous_control_mode=previous_mode, authority_epoch=instance.authority_epoch,
        expires_at=now + timedelta(seconds=payload.duration_seconds),
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
        PossessionLease.released_at.is_(None),
    ))
    if lease is None:
        raise HTTPException(status_code=404, detail="Active possession lease not found.")
    if lease.expires_at <= datetime.now(timezone.utc) or lease.authority_epoch != instance.authority_epoch:
        _restore_possession_lease(db, lease, instance, user_id, "possession_lease_expired")
        db.commit()
        raise HTTPException(status_code=409, detail="Possession lease expired or its authority epoch is stale.")
    return lease


@router.post("/scene-runs/{run_id}/instances/{instance_id}/lease/renew", response_model=PossessionLeaseRead)
def renew_possession_lease(project_id: uuid.UUID, run_id: uuid.UUID, instance_id: uuid.UUID,
                           payload: PossessionLeaseRelease, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id)
    run = _run_or_404(db, project_id, run_id)
    instance = _instance_or_404(db, run.id, instance_id)
    lease = _lease_or_404(db, instance, user.id, payload.lease_token)
    lease.expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)
    db.commit()
    db.refresh(lease)
    return PossessionLeaseRead.model_validate(lease, from_attributes=True)


@router.post("/scene-runs/{run_id}/instances/{instance_id}/lease/release", response_model=PossessionLeaseRead)
def release_possession_lease(project_id: uuid.UUID, run_id: uuid.UUID, instance_id: uuid.UUID,
                             payload: PossessionLeaseRelease, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id)
    run = _run_or_404(db, project_id, run_id)
    instance = _instance_or_404(db, run.id, instance_id)
    lease = _lease_or_404(db, instance, user.id, payload.lease_token)
    _restore_possession_lease(db, lease, instance, user.id, "possession_released")
    db.commit()
    db.refresh(lease)
    return PossessionLeaseRead.model_validate(lease, from_attributes=True)


@router.post("/scene-runs/{run_id}/takes", response_model=PerformanceTakeRead, status_code=status.HTTP_201_CREATED)
def create_take(project_id: uuid.UUID, run_id: uuid.UUID, payload: PerformanceTakeCreate, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id, write=True)
    run = _run_or_404(db, project_id, run_id)
    if run.status not in ("paused", "completed"):
        raise HTTPException(status_code=409, detail="Pause or complete a scene run before sealing a take.")
    number = (db.scalar(select(func.max(PerformanceTake.take_number)).where(PerformanceTake.scene_run_id == run.id)) or 0) + 1
    take = PerformanceTake(
        project_id=project_id, scene_run_id=run.id, take_number=number,
        state_snapshot=payload.state_snapshot, created_by_user_id=user.id,
    )
    db.add(take)
    db.commit()
    db.refresh(take)
    return _take_read(db, take)


@router.get("/takes/{take_id}", response_model=PerformanceTakeRead)
def get_take(project_id: uuid.UUID, take_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id)
    take = db.scalar(select(PerformanceTake).where(
        PerformanceTake.id == take_id, PerformanceTake.project_id == project_id,
    ))
    if take is None:
        raise HTTPException(status_code=404, detail="Performance take not found.")
    return _take_read(db, take)


@router.post("/takes/{take_id}/events", response_model=PerformanceTakeRead)
def append_take_events(project_id: uuid.UUID, take_id: uuid.UUID, payload: PerformanceEventBatchCreate,
                       db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id, write=True)
    take = db.scalar(select(PerformanceTake).where(
        PerformanceTake.id == take_id, PerformanceTake.project_id == project_id,
    ).with_for_update())
    if take is None:
        raise HTTPException(status_code=404, detail="Performance take not found.")
    if take.status != "recorded":
        raise HTTPException(status_code=409, detail="Selected or rejected takes are immutable.")
    run = _run_or_404(db, project_id, take.scene_run_id)
    if run.status not in ("paused", "completed"):
        raise HTTPException(status_code=409, detail="The scene run must be paused or completed before events are committed.")
    last = db.scalar(select(PerformanceTakeEvent).where(
        PerformanceTakeEvent.take_id == take.id,
    ).order_by(PerformanceTakeEvent.event_order.desc()).limit(1))
    previous_timestamp = last.timestamp_ms if last else -1
    next_order = take.event_count + 1
    for item in payload.events:
        if item.timestamp_ms < previous_timestamp:
            raise HTTPException(status_code=422, detail="Performance event timestamps must be monotonic.")
        instance = None
        if item.cast_member_instance_id:
            instance = _instance_or_404(db, run.id, item.cast_member_instance_id)
            if item.authority_epoch is None or db.scalar(select(ControllerAssignmentEvent.id).where(
                ControllerAssignmentEvent.cast_member_instance_id == instance.id,
                ControllerAssignmentEvent.authority_epoch == item.authority_epoch,
            )) is None:
                raise HTTPException(status_code=409, detail="Event rejected because its controller authority epoch is unknown or stale.")
        elif item.authority_epoch is not None:
            raise HTTPException(status_code=422, detail="An authority epoch requires a cast member instance.")
        db.add(PerformanceTakeEvent(
            take_id=take.id, event_order=next_order, timestamp_ms=item.timestamp_ms,
            event_type=item.event_type, cast_member_instance_id=instance.id if instance else None,
            authority_epoch=item.authority_epoch, payload=item.payload,
        ))
        previous_timestamp = item.timestamp_ms
        take.duration_ms = max(take.duration_ms, item.timestamp_ms)
        next_order += 1
    take.event_count += len(payload.events)
    db.commit()
    db.refresh(take)
    return _take_read(db, take)


@router.patch("/takes/{take_id}", response_model=PerformanceTakeRead)
def update_take_status(project_id: uuid.UUID, take_id: uuid.UUID, payload: PerformanceTakeStatusUpdate,
                       db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id, write=True)
    take = db.scalar(select(PerformanceTake).where(
        PerformanceTake.id == take_id, PerformanceTake.project_id == project_id,
    ).with_for_update())
    if take is None:
        raise HTTPException(status_code=404, detail="Performance take not found.")
    if take.status == "rejected":
        raise HTTPException(status_code=409, detail="Rejected takes are immutable.")
    run = _run_or_404(db, project_id, take.scene_run_id)
    if payload.status == "selected":
        if take.event_count == 0:
            raise HTTPException(status_code=409, detail="A take needs recorded events before it can be selected.")
        previous = db.scalars(select(PerformanceTake).join(
            SceneRun, SceneRun.id == PerformanceTake.scene_run_id,
        ).where(SceneRun.scene_id == run.scene_id, PerformanceTake.status == "selected",
                PerformanceTake.id != take.id).with_for_update()).all()
        for item in previous:
            item.status = "recorded"
    take.status = payload.status
    db.commit()
    db.refresh(take)
    return _take_read(db, take)


@router.get("/takes", response_model=list[PerformanceTakeRead])
def list_takes(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id)
    takes = db.scalars(select(PerformanceTake).where(
        PerformanceTake.project_id == project_id,
    ).order_by(PerformanceTake.created_at.desc())).all()
    return [_take_read(db, item) for item in takes]


@router.post("/edit-sequences", response_model=EditSequenceRead, status_code=status.HTTP_201_CREATED)
def create_edit_sequence(project_id: uuid.UUID, payload: EditSequenceCreate, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id, write=True)
    sequence = EditSequence(project_id=project_id, name=payload.name, created_by_user_id=user.id)
    db.add(sequence)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="An edit sequence with that name already exists in this project.")
    db.refresh(sequence)
    return _sequence_read(db, sequence)


@router.get("/edit-sequences", response_model=list[EditSequenceRead])
def list_edit_sequences(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id)
    sequences = db.scalars(select(EditSequence).where(
        EditSequence.project_id == project_id,
    ).order_by(EditSequence.updated_at.desc())).all()
    return [_sequence_read(db, item) for item in sequences]


def _sequence_or_404(db: Session, project_id: uuid.UUID, sequence_id: uuid.UUID) -> EditSequence:
    sequence = db.scalar(select(EditSequence).where(
        EditSequence.id == sequence_id, EditSequence.project_id == project_id,
    ))
    if sequence is None:
        raise HTTPException(status_code=404, detail="Edit sequence not found in this project.")
    return sequence


@router.get("/edit-sequences/{sequence_id}", response_model=EditSequenceRead)
def get_edit_sequence(project_id: uuid.UUID, sequence_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id)
    return _sequence_read(db, _sequence_or_404(db, project_id, sequence_id))


@router.post("/edit-sequences/{sequence_id}/items", response_model=EditSequenceRead, status_code=status.HTTP_201_CREATED)
def add_edit_item(project_id: uuid.UUID, sequence_id: uuid.UUID, payload: EditSequenceItemCreate,
                  db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id, write=True)
    sequence = _sequence_or_404(db, project_id, sequence_id)
    if sequence.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft edit sequences can be changed.")
    take = db.scalar(select(PerformanceTake).where(
        PerformanceTake.id == payload.take_id, PerformanceTake.project_id == project_id,
    ))
    if take is None or take.status != "selected":
        raise HTTPException(status_code=422, detail="Edit clips must reference a selected take from this project.")
    run = db.get(SceneRun, take.scene_run_id)
    if run is None or run.project_id != project_id:
        raise HTTPException(status_code=422, detail="The selected take has no valid scene run.")
    if payload.in_ms >= payload.out_ms or payload.out_ms > take.duration_ms:
        raise HTTPException(status_code=422, detail="Clip trim points must be within the selected take duration.")
    order = (db.scalar(select(func.max(EditSequenceItem.item_order)).where(EditSequenceItem.sequence_id == sequence.id)) or 0) + 1
    db.add(EditSequenceItem(
        sequence_id=sequence.id, take_id=take.id, scene_id=run.scene_id, item_order=order,
        in_ms=payload.in_ms, out_ms=payload.out_ms, transition=payload.transition,
        title_overlay=payload.title_overlay, effects=payload.effects, audio_cue=payload.audio_cue,
    ))
    sequence.revision_number += 1
    db.commit()
    db.refresh(sequence)
    return _sequence_read(db, sequence)


@router.patch("/edit-sequences/{sequence_id}/items/{item_id}", response_model=EditSequenceRead)
def update_edit_item(project_id: uuid.UUID, sequence_id: uuid.UUID, item_id: uuid.UUID,
                     payload: EditSequenceItemUpdate, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id, write=True)
    sequence = _sequence_or_404(db, project_id, sequence_id)
    if sequence.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft edit sequences can be changed.")
    item = db.scalar(select(EditSequenceItem).where(
        EditSequenceItem.id == item_id, EditSequenceItem.sequence_id == sequence.id,
    ))
    if item is None:
        raise HTTPException(status_code=404, detail="Edit sequence item not found.")
    values = payload.model_dump(exclude_unset=True)
    in_ms = values.get("in_ms", item.in_ms)
    out_ms = values.get("out_ms", item.out_ms)
    take = db.get(PerformanceTake, item.take_id)
    if in_ms >= out_ms or take is None or out_ms > take.duration_ms:
        raise HTTPException(status_code=422, detail="Clip trim points must be within the selected take duration.")
    for key, value in values.items():
        if value is not None:
            setattr(item, key, value)
    sequence.revision_number += 1
    db.commit()
    db.refresh(sequence)
    return _sequence_read(db, sequence)


@router.delete("/edit-sequences/{sequence_id}/items/{item_id}", response_model=EditSequenceRead)
def delete_edit_item(project_id: uuid.UUID, sequence_id: uuid.UUID, item_id: uuid.UUID,
                     db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id, write=True)
    sequence = _sequence_or_404(db, project_id, sequence_id)
    if sequence.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft edit sequences can be changed.")
    item = db.scalar(select(EditSequenceItem).where(
        EditSequenceItem.id == item_id, EditSequenceItem.sequence_id == sequence.id,
    ))
    if item is None:
        raise HTTPException(status_code=404, detail="Edit sequence item not found.")
    db.delete(item)
    db.flush()
    remaining = db.scalars(select(EditSequenceItem).where(
        EditSequenceItem.sequence_id == sequence.id,
    ).order_by(EditSequenceItem.item_order)).all()
    for index, row in enumerate(remaining, start=1):
        row.item_order = index
    sequence.revision_number += 1
    db.commit()
    db.refresh(sequence)
    return _sequence_read(db, sequence)


@router.put("/edit-sequences/{sequence_id}/reorder", response_model=EditSequenceRead)
def reorder_edit_items(project_id: uuid.UUID, sequence_id: uuid.UUID, payload: EditSequenceReorder,
                       db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id, write=True)
    sequence = _sequence_or_404(db, project_id, sequence_id)
    if sequence.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft edit sequences can be changed.")
    rows = db.scalars(select(EditSequenceItem).where(
        EditSequenceItem.sequence_id == sequence.id,
    ).with_for_update()).all()
    by_id = {row.id: row for row in rows}
    if len(payload.item_ids) != len(rows) or set(payload.item_ids) != set(by_id):
        raise HTTPException(status_code=422, detail="Reorder must include every edit item exactly once.")
    offset = len(rows) + max((row.item_order for row in rows), default=0) + 1
    for row in rows:
        row.item_order += offset
    db.flush()
    for index, item_id in enumerate(payload.item_ids, start=1):
        by_id[item_id].item_order = index
    sequence.revision_number += 1
    db.commit()
    db.refresh(sequence)
    return _sequence_read(db, sequence)


@router.post("/edit-sequences/{sequence_id}/export", response_model=EditExportRead, status_code=status.HTTP_201_CREATED)
def export_edit_sequence(project_id: uuid.UUID, sequence_id: uuid.UUID, db: DbSession, user: CurrentUser):
    project = _project_access(db, project_id, user.id, write=True)
    sequence = _sequence_or_404(db, project_id, sequence_id)
    items = db.scalars(select(EditSequenceItem).where(
        EditSequenceItem.sequence_id == sequence.id,
    ).order_by(EditSequenceItem.item_order)).all()
    if not items:
        raise HTTPException(status_code=409, detail="Add at least one selected take to the edit sequence before exporting.")
    clips = []
    cursor = 0
    for item in items:
        take = db.get(PerformanceTake, item.take_id)
        run = db.get(SceneRun, take.scene_run_id) if take else None
        scene = db.get(StoryboardScene, item.scene_id)
        if take is None or run is None or scene is None or take.status != "selected":
            raise HTTPException(status_code=409, detail="Every edit item must reference a currently selected, valid take.")
        duration = item.out_ms - item.in_ms
        clips.append({
            "order": item.item_order, "scene_id": str(scene.id), "scene_title": scene.title,
            "scene_run_id": str(run.id), "take_id": str(take.id), "take_number": take.take_number,
            "source_in_ms": item.in_ms, "source_out_ms": item.out_ms,
            "timeline_start_ms": cursor, "timeline_end_ms": cursor + duration,
            "duration_ms": duration, "transition": item.transition,
            "title_overlay": item.title_overlay, "effects": item.effects, "audio_cue": item.audio_cue,
        })
        cursor += duration
    export_number = (db.scalar(select(func.max(EditExport.export_number)).where(EditExport.sequence_id == sequence.id)) or 0) + 1
    manifest = {
        "format": "storyforge-edit-decision-list",
        "format_version": 1,
        "project": {"id": str(project.id), "title": project.title, "format": project.format, "category": project.category},
        "sequence": {"id": str(sequence.id), "name": sequence.name, "revision": sequence.revision_number},
        "timebase": {"unit": "milliseconds", "frame_rate": None},
        "duration_ms": cursor,
        "clips": clips,
        "rendering": {"status": "manifest_only", "note": "This export is an immutable edit decision list. Video rendering and media conform are not yet implemented."},
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    export = EditExport(
        sequence_id=sequence.id, export_number=export_number,
        sequence_revision=sequence.revision_number, manifest=manifest,
        created_by_user_id=user.id,
    )
    db.add(export)
    db.commit()
    db.refresh(export)
    return EditExportRead.model_validate(export, from_attributes=True)


@router.get("/exports/{export_id}", response_model=EditExportRead)
def get_edit_export(project_id: uuid.UUID, export_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id)
    export = db.scalar(select(EditExport).join(
        EditSequence, EditSequence.id == EditExport.sequence_id,
    ).where(EditExport.id == export_id, EditSequence.project_id == project_id))
    if export is None:
        raise HTTPException(status_code=404, detail="Edit export not found.")
    return EditExportRead.model_validate(export, from_attributes=True)
