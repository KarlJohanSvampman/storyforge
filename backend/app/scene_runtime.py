import uuid
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    Actor, CastMemberInstance, CastingAssignment, ControllerAssignmentEvent, Project, ProjectCharacter, SceneCharacterAssignment,
    SceneRun, Storyboard, StoryboardScene,
)
from .projects import CurrentUser, DbSession, _membership, _project_or_404
from .schemas import CastMemberInstanceRead, SceneRunCreate, SceneRunRead

router = APIRouter(tags=["scene runtime"])


def _scene_run_read(db: Session, run: SceneRun) -> SceneRunRead:
    scene = db.get(StoryboardScene, run.scene_id)
    members = db.scalars(
        select(CastMemberInstance).where(CastMemberInstance.scene_run_id == run.id)
        .order_by(CastMemberInstance.character_name_snapshot)
    ).all()
    participant_ids = set(db.scalars(
        select(SceneCharacterAssignment.character_id)
        .where(SceneCharacterAssignment.scene_id == run.scene_id)
    ).all())
    cast_ids = {item.character_id for item in members}
    return SceneRunRead(
        id=run.id, project_id=run.project_id, storyboard_id=run.storyboard_id,
        scene_id=run.scene_id, scene_title=scene.title, location_id=scene.location_id,
        narrative_version_id=run.narrative_version_id, status=run.status,
        authority_epoch=run.authority_epoch, created_by_user_id=run.created_by_user_id,
        created_at=run.created_at, started_at=run.started_at, ended_at=run.ended_at,
        cast_members=[CastMemberInstanceRead.model_validate(item, from_attributes=True) for item in members],
        uncast_character_ids=sorted(participant_ids - cast_ids, key=str),
    )


def _require_runtime_editor(db: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> Project:
    project = _project_or_404(db, project_id)
    member = _membership(db, project_id, user_id)
    if member.role not in ("owner", "editor"):
        raise HTTPException(status_code=403, detail="Only project owners and editors can prepare scene runs.")
    if project.current_phase not in ("storyboard", "production"):
        raise HTTPException(status_code=409, detail="Scene runs require a storyboard or production phase.")
    return project


@router.post("/api/projects/{project_id}/scene-runs", response_model=SceneRunRead, status_code=status.HTTP_201_CREATED)
def create_scene_run(project_id: uuid.UUID, payload: SceneRunCreate, db: DbSession, user: CurrentUser):
    _require_runtime_editor(db, project_id, user.id)
    storyboard = db.scalar(
        select(Storyboard).where(Storyboard.project_id == project_id)
        .order_by(Storyboard.created_at.desc(), Storyboard.id.desc()).limit(1)
    )
    if storyboard is None:
        raise HTTPException(status_code=409, detail="Initialize a storyboard before preparing a scene run.")
    scene = db.scalar(select(StoryboardScene).where(
        StoryboardScene.id == payload.scene_id,
        StoryboardScene.storyboard_id == storyboard.id,
    ))
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found in the current storyboard.")

    participant_ids = db.scalars(
        select(SceneCharacterAssignment.character_id)
        .where(SceneCharacterAssignment.scene_id == scene.id)
    ).all()
    assignments = db.scalars(
        select(CastingAssignment).where(
            CastingAssignment.project_id == project_id,
            CastingAssignment.character_id.in_(participant_ids) if participant_ids else False,
            CastingAssignment.status == "active",
        )
    ).all() if participant_ids else []
    assignment_by_character = {item.character_id: item for item in assignments}

    run = SceneRun(
        project_id=project_id, storyboard_id=storyboard.id, scene_id=scene.id,
        narrative_version_id=storyboard.narrative_version_id,
        status="prepared", authority_epoch=1, created_by_user_id=user.id,
    )
    db.add(run)
    db.flush()

    for character_id in participant_ids:
        assignment = assignment_by_character.get(character_id)
        if assignment is None:
            continue
        actor = db.get(Actor, assignment.actor_id)
        character = db.get(ProjectCharacter, character_id)
        if actor is None or character is None:
            continue
        instance = CastMemberInstance(
            scene_run_id=run.id, casting_assignment_id=assignment.id,
            actor_id=actor.id, character_id=character.id,
            actor_name_snapshot=actor.display_name, character_name_snapshot=character.name,
            role_label_snapshot=assignment.role_label,
            controller_type=assignment.controller_type,
            controller_user_id=assignment.controller_user_id,
            control_mode=assignment.control_mode,
            control_settings=assignment.control_settings or {},
            authority_epoch=1,
        )
        db.add(instance)
        db.flush()
        db.add(ControllerAssignmentEvent(
            scene_run_id=run.id, cast_member_instance_id=instance.id,
            authority_epoch=1, previous_controller_type=None,
            previous_controller_user_id=None, new_controller_type=assignment.controller_type,
            new_controller_user_id=assignment.controller_user_id,
            reason="scene_run_initialized", changed_by_user_id=user.id,
        ))
    db.commit()
    db.refresh(run)
    return _scene_run_read(db, run)


@router.get("/api/projects/{project_id}/scene-runs", response_model=list[SceneRunRead])
def list_scene_runs(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id)
    _membership(db, project_id, user.id)
    runs = db.scalars(
        select(SceneRun).where(SceneRun.project_id == project_id)
        .order_by(SceneRun.created_at.desc(), SceneRun.id.desc())
    ).all()
    return [_scene_run_read(db, run) for run in runs]


@router.get("/api/projects/{project_id}/scene-runs/{run_id}", response_model=SceneRunRead)
def get_scene_run(project_id: uuid.UUID, run_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id)
    _membership(db, project_id, user.id)
    run = db.scalar(select(SceneRun).where(SceneRun.id == run_id, SceneRun.project_id == project_id))
    if run is None:
        raise HTTPException(status_code=404, detail="Scene run not found.")
    return _scene_run_read(db, run)
