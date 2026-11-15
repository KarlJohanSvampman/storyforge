import uuid
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Actor, CastingAssignment, Project, ProjectCharacter, ProjectMembership, ProjectPerformanceSettings
from .projects import CurrentUser, DbSession, _membership, _project_or_404
from .schemas import (
    ActorCreate, ActorRead, ActorUpdate, CastingAssignmentCreate,
    CastingAssignmentRead, CastingAssignmentUpdate, PerformanceSettingsRead,
    PerformanceSettingsUpdate,
)

router = APIRouter(tags=["actors and casting"])


def _require_project_editor(db: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> Project:
    project = _project_or_404(db, project_id)
    member = _membership(db, project_id, user_id)
    if member.role not in ("owner", "editor"):
        raise HTTPException(status_code=403, detail="Only project owners and editors can manage casting.")
    if project.current_phase not in ("storyboard", "production"):
        raise HTTPException(status_code=409, detail="Casting can be managed after the project enters the storyboard phase.")
    return project


def _assignment_read(db: Session, assignment: CastingAssignment) -> CastingAssignmentRead:
    actor = db.get(Actor, assignment.actor_id)
    character = db.get(ProjectCharacter, assignment.character_id)
    return CastingAssignmentRead(
        id=assignment.id, project_id=assignment.project_id, actor_id=assignment.actor_id,
        actor_name=actor.display_name, character_id=assignment.character_id,
        character_name=character.name, role_label=assignment.role_label,
        status=assignment.status, controller_type=assignment.controller_type,
        controller_user_id=assignment.controller_user_id, control_mode=assignment.control_mode,
        control_settings=assignment.control_settings or {}, assigned_by_user_id=assignment.assigned_by_user_id,
        created_at=assignment.created_at, updated_at=assignment.updated_at,
    )


@router.get("/api/actors", response_model=list[ActorRead])
def list_actors(db: DbSession, user: CurrentUser):
    return db.scalars(select(Actor).where(Actor.owner_user_id == user.id).order_by(Actor.updated_at.desc())).all()


@router.post("/api/actors", response_model=ActorRead, status_code=status.HTTP_201_CREATED)
def create_actor(payload: ActorCreate, db: DbSession, user: CurrentUser):
    if not payload.display_name:
        raise HTTPException(status_code=422, detail="Actor display name cannot be blank.")
    actor = Actor(owner_user_id=user.id, **payload.model_dump())
    db.add(actor)
    db.commit()
    db.refresh(actor)
    return actor


@router.patch("/api/actors/{actor_id}", response_model=ActorRead)
def update_actor(actor_id: uuid.UUID, payload: ActorUpdate, db: DbSession, user: CurrentUser):
    actor = db.get(Actor, actor_id)
    if not actor or actor.owner_user_id != user.id:
        raise HTTPException(status_code=404, detail="Actor not found.")
    values = payload.model_dump(exclude_unset=True)
    if values.get("display_name") == "":
        raise HTTPException(status_code=422, detail="Actor display name cannot be blank.")
    if values.get("status") == "archived":
        active = db.scalar(select(CastingAssignment.id).where(CastingAssignment.actor_id == actor.id, CastingAssignment.status == "active").limit(1))
        if active:
            raise HTTPException(status_code=409, detail="An actor with active casting assignments cannot be archived.")
    for key, value in values.items():
        setattr(actor, key, value)
    db.commit()
    db.refresh(actor)
    return actor


@router.get("/api/projects/{project_id}/performance-settings", response_model=PerformanceSettingsRead)
def get_performance_settings(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id)
    _membership(db, project_id, user.id)
    settings = db.scalar(select(ProjectPerformanceSettings).where(ProjectPerformanceSettings.project_id == project_id))
    if not settings:
        settings = ProjectPerformanceSettings(project_id=project_id, updated_by_user_id=user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.patch("/api/projects/{project_id}/performance-settings", response_model=PerformanceSettingsRead)
def update_performance_settings(project_id: uuid.UUID, payload: PerformanceSettingsUpdate, db: DbSession, user: CurrentUser):
    _require_project_editor(db, project_id, user.id)
    settings = db.scalar(select(ProjectPerformanceSettings).where(ProjectPerformanceSettings.project_id == project_id))
    if not settings:
        settings = ProjectPerformanceSettings(project_id=project_id, updated_by_user_id=user.id)
        db.add(settings)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(settings, key, value)
    settings.updated_by_user_id = user.id
    db.commit()
    db.refresh(settings)
    return settings


@router.get("/api/projects/{project_id}/casting", response_model=list[CastingAssignmentRead])
def list_casting(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id)
    _membership(db, project_id, user.id)
    assignments = db.scalars(select(CastingAssignment).where(CastingAssignment.project_id == project_id).order_by(CastingAssignment.created_at)).all()
    return [_assignment_read(db, item) for item in assignments]


@router.post("/api/projects/{project_id}/casting", response_model=CastingAssignmentRead, status_code=status.HTTP_201_CREATED)
def create_casting(project_id: uuid.UUID, payload: CastingAssignmentCreate, db: DbSession, user: CurrentUser):
    _require_project_editor(db, project_id, user.id)
    actor = db.get(Actor, payload.actor_id)
    if not actor or actor.owner_user_id != user.id or actor.status != "active":
        raise HTTPException(status_code=404, detail="Active actor profile not found or not owned by the current user.")
    character = db.get(ProjectCharacter, payload.character_id)
    if not character or character.project_id != project_id or character.status != "active":
        raise HTTPException(status_code=404, detail="Active character not found in this project.")
    settings = db.scalar(select(ProjectPerformanceSettings).where(ProjectPerformanceSettings.project_id == project_id))
    if not settings:
        settings = ProjectPerformanceSettings(project_id=project_id, updated_by_user_id=user.id)
        db.add(settings)
        db.flush()
    existing_character_cast = db.scalar(select(CastingAssignment).where(CastingAssignment.project_id == project_id, CastingAssignment.character_id == character.id, CastingAssignment.status == "active"))
    if existing_character_cast:
        if not settings.allow_character_recasting:
            raise HTTPException(status_code=409, detail="Project settings do not allow replacing an active casting assignment.")
        existing_character_cast.status = "replaced"
    if not settings.allow_actor_reuse:
        actor_query = select(CastingAssignment.id).where(CastingAssignment.project_id == project_id, CastingAssignment.actor_id == actor.id, CastingAssignment.status == "active")
        if existing_character_cast:
            actor_query = actor_query.where(CastingAssignment.id != existing_character_cast.id)
        actor_in_project = db.scalar(actor_query.limit(1))
        if actor_in_project:
            raise HTTPException(status_code=409, detail="Project settings do not allow this actor to portray multiple characters.")
    if not payload.role_label.strip():
        raise HTTPException(status_code=422, detail="Casting role label cannot be blank.")

    controller_type = payload.controller_type or settings.default_controller_type
    control_mode = payload.control_mode or settings.default_control_mode
    controller_user_id = payload.controller_user_id
    if controller_type == "user":
        controller_user_id = controller_user_id or user.id
        member = db.scalar(select(ProjectMembership.id).where(ProjectMembership.project_id == project_id, ProjectMembership.user_id == controller_user_id, ProjectMembership.status == "active"))
        if not member:
            raise HTTPException(status_code=422, detail="The selected human controller must be an active project member.")
    elif controller_user_id is not None:
        raise HTTPException(status_code=422, detail="controller_user_id is only valid for user-controlled actors.")
    assignment = CastingAssignment(
        project_id=project_id, actor_id=actor.id, character_id=character.id,
        role_label=payload.role_label.strip(), controller_type=controller_type,
        controller_user_id=controller_user_id, control_mode=control_mode,
        control_settings=payload.control_settings, assigned_by_user_id=user.id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return _assignment_read(db, assignment)


@router.patch("/api/projects/{project_id}/casting/{assignment_id}", response_model=CastingAssignmentRead)
def update_casting(project_id: uuid.UUID, assignment_id: uuid.UUID, payload: CastingAssignmentUpdate, db: DbSession, user: CurrentUser):
    _require_project_editor(db, project_id, user.id)
    assignment = db.scalar(select(CastingAssignment).where(CastingAssignment.id == assignment_id, CastingAssignment.project_id == project_id))
    if not assignment:
        raise HTTPException(status_code=404, detail="Casting assignment not found.")
    values = payload.model_dump(exclude_unset=True)
    controller_type = values.get("controller_type", assignment.controller_type)
    controller_user_id = values.get("controller_user_id", assignment.controller_user_id)
    if controller_type == "user":
        controller_user_id = controller_user_id or user.id
        member = db.scalar(select(ProjectMembership.id).where(ProjectMembership.project_id == project_id, ProjectMembership.user_id == controller_user_id, ProjectMembership.status == "active"))
        if not member:
            raise HTTPException(status_code=422, detail="The selected human controller must be an active project member.")
    else:
        if values.get("controller_user_id") is not None:
            raise HTTPException(status_code=422, detail="controller_user_id is only valid for user-controlled actors.")
        controller_user_id = None
    for key, value in values.items():
        if key == "controller_user_id":
            continue
        if value is not None:
            setattr(assignment, key, value)
    assignment.controller_user_id = controller_user_id
    db.commit()
    db.refresh(assignment)
    return _assignment_read(db, assignment)
