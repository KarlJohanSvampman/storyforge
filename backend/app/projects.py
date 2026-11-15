import os
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from .database import get_db
from .models import Project, ProjectMembership, Storyboard, User
from .schemas import InvitationCreate, MemberRead, ProjectCreate, ProjectDetail, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["projects"])
DbSession = Annotated[Session, Depends(get_db)]

def get_current_user(db: DbSession) -> User:
    """Development identity only. Replace with verified authentication before deployment."""
    if os.getenv("STORYFORGE_AUTH_MODE", "development") != "development":
        raise HTTPException(status_code=503, detail="A production authentication provider is not configured.")
    email = os.getenv("STORYFORGE_DEV_USER_EMAIL", "storyteller@storyforge.local").strip().lower()
    display_name = os.getenv("STORYFORGE_DEV_USER_NAME", "Storyteller").strip()
    user = db.scalar(select(User).where(User.email == email))
    if user:
        return user
    user = User(email=email, display_name=display_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

CurrentUser = Annotated[User, Depends(get_current_user)]

def _membership(db: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> ProjectMembership:
    membership = db.scalar(select(ProjectMembership).where(
        ProjectMembership.project_id == project_id,
        ProjectMembership.user_id == user_id,
        ProjectMembership.status == "active",
    ))
    if not membership:
        raise HTTPException(status_code=404, detail="Project not found.")
    return membership

def _project_or_404(db: Session, project_id: uuid.UUID) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project

def _project_read(db: Session, project: Project) -> ProjectRead:
    count = db.scalar(select(func.count(ProjectMembership.id)).where(
        ProjectMembership.project_id == project.id,
        ProjectMembership.status == "active",
    )) or 0
    return ProjectRead(
        id=project.id, title=project.title, description=project.description,
        logline=project.logline, genre=project.genre, format=project.format, category=project.category, visibility=project.visibility,
        current_phase=project.current_phase, owner_user_id=project.owner_user_id,
        created_at=project.created_at, updated_at=project.updated_at, member_count=count,
    )

@router.get("", response_model=list[ProjectRead])
def list_projects(db: DbSession, user: CurrentUser):
    projects = db.scalars(
        select(Project).join(ProjectMembership, ProjectMembership.project_id == Project.id)
        .where(ProjectMembership.user_id == user.id, ProjectMembership.status == "active")
        .order_by(Project.updated_at.desc())
    ).unique().all()
    return [_project_read(db, project) for project in projects]

@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: DbSession, user: CurrentUser):
    if not payload.title:
        raise HTTPException(status_code=422, detail="Project title cannot be blank.")
    project = Project(
        title=payload.title, description=payload.description, logline=payload.logline,
        genre=payload.genre, format=payload.format, category=payload.category, visibility=payload.visibility, owner_user_id=user.id,
    )
    db.add(project)
    db.flush()
    db.add(ProjectMembership(project_id=project.id, user_id=user.id, role="owner", status="active"))
    db.commit()
    db.refresh(project)
    return _project_read(db, project)

@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    project = _project_or_404(db, project_id)
    _membership(db, project.id, user.id)
    memberships = db.scalars(
        select(ProjectMembership).options(joinedload(ProjectMembership.user))
        .where(ProjectMembership.project_id == project.id)
        .order_by(ProjectMembership.created_at)
    ).all()
    base = _project_read(db, project)
    members = [MemberRead(
        id=m.id, display_name=m.user.display_name if m.user else None,
        email=m.user.email if m.user else None, invited_email=m.invited_email,
        role=m.role, status=m.status, created_at=m.created_at,
    ) for m in memberships]
    return ProjectDetail(**base.model_dump(), members=members)

@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(project_id: uuid.UUID, payload: ProjectUpdate, db: DbSession, user: CurrentUser):
    project = _project_or_404(db, project_id)
    membership = _membership(db, project.id, user.id)
    if membership.role not in ("owner", "editor"):
        raise HTTPException(status_code=403, detail="You do not have permission to edit this project.")
    values = payload.model_dump(exclude_unset=True)
    if "format" in values and values["format"] != project.format:
        existing_storyboard = db.scalar(select(Storyboard.id).where(Storyboard.project_id == project.id).limit(1))
        if existing_storyboard is not None:
            raise HTTPException(
                status_code=409,
                detail="Project format cannot be changed after a storyboard has been initialized. Create a new project for a different production format.",
            )
    for key, value in values.items():
        if value is not None:
            setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return _project_read(db, project)

@router.post("/{project_id}/invitations", response_model=MemberRead, status_code=status.HTTP_201_CREATED)
def invite_member(project_id: uuid.UUID, payload: InvitationCreate, db: DbSession, user: CurrentUser):
    project = _project_or_404(db, project_id)
    membership = _membership(db, project.id, user.id)
    if membership.role != "owner":
        raise HTTPException(status_code=403, detail="Only the project owner can invite members.")

    email = str(payload.email).lower()
    existing_user = db.scalar(select(User).where(User.email == email))
    duplicate_query = select(ProjectMembership).where(ProjectMembership.project_id == project.id)
    if existing_user:
        duplicate_query = duplicate_query.where(
            (ProjectMembership.user_id == existing_user.id)
            | (ProjectMembership.invited_email == email)
        )
    else:
        duplicate_query = duplicate_query.where(ProjectMembership.invited_email == email)
    if db.scalar(duplicate_query):
        raise HTTPException(status_code=409, detail="This person is already a project member or has been invited.")

    # Invitations remain pending until the recipient authenticates and accepts them.
    invitation = ProjectMembership(
        project_id=project.id, invited_email=email, role=payload.role, status="invited",
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return MemberRead(
        id=invitation.id, display_name=None,
        email=existing_user.email if existing_user else None,
        invited_email=invitation.invited_email, role=invitation.role,
        status=invitation.status, created_at=invitation.created_at,
    )
