import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import CastMemberInstance, PerformanceAnnotation, PerformanceEvent, PerformanceTake, Project, SceneRun, User
from .projects import CurrentUser, DbSession, _membership, _project_or_404

router = APIRouter(tags=["performance playback"])


class AnnotationCreate(BaseModel):
    timestamp_ms: int = Field(ge=0)
    category: Literal["note", "continuity", "performance", "camera", "audio"] = "note"
    content: str = Field(min_length=1, max_length=5000)
    event_id: uuid.UUID | None = None
    cast_member_instance_id: uuid.UUID | None = None


class AnnotationUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=5000)
    category: Literal["note", "continuity", "performance", "camera", "audio"] | None = None
    status: Literal["open", "resolved"] | None = None


def _take_or_404(db: Session, project_id: uuid.UUID, take_id: uuid.UUID) -> tuple[PerformanceTake, SceneRun]:
    row = db.execute(
        select(PerformanceTake, SceneRun)
        .join(SceneRun, SceneRun.id == PerformanceTake.scene_run_id)
        .where(PerformanceTake.id == take_id, SceneRun.project_id == project_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Performance take not found.")
    return row[0], row[1]


def _annotation_read(db: Session, annotation: PerformanceAnnotation) -> dict:
    author = db.get(User, annotation.author_user_id)
    return {
        "id": annotation.id, "take_id": annotation.take_id, "event_id": annotation.event_id,
        "cast_member_instance_id": annotation.cast_member_instance_id,
        "author_user_id": annotation.author_user_id,
        "author_display_name": author.display_name if author else "Former member",
        "timestamp_ms": annotation.timestamp_ms, "category": annotation.category,
        "content": annotation.content, "status": annotation.status,
        "created_at": annotation.created_at, "updated_at": annotation.updated_at,
    }


@router.get("/api/projects/{project_id}/takes/{take_id}/replay")
def get_take_replay(project_id: uuid.UUID, take_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id)
    _membership(db, project_id, user.id)
    take, run = _take_or_404(db, project_id, take_id)
    if take.status not in ("finalized", "selected"):
        raise HTTPException(status_code=409, detail="Only finalized or selected takes can be replayed.")
    cast_members = db.scalars(
        select(CastMemberInstance).where(CastMemberInstance.scene_run_id == run.id)
        .order_by(CastMemberInstance.created_at, CastMemberInstance.id)
    ).all()
    events = db.scalars(
        select(PerformanceEvent).where(PerformanceEvent.take_id == take.id)
        .order_by(PerformanceEvent.timestamp_ms, PerformanceEvent.sequence_number)
    ).all()
    annotations = db.scalars(
        select(PerformanceAnnotation).where(PerformanceAnnotation.take_id == take.id)
        .order_by(PerformanceAnnotation.timestamp_ms, PerformanceAnnotation.created_at)
    ).all()
    return {
        "take_id": take.id, "scene_run_id": run.id, "scene_id": run.scene_id,
        "status": take.status, "duration_ms": take.duration_ms or 0,
        "camera_snapshot": take.camera_snapshot or {}, "state_snapshot": take.state_snapshot or {},
        "cast_members": [{
            "id": item.id, "actor_name_snapshot": item.actor_name_snapshot,
            "character_name_snapshot": item.character_name_snapshot,
            "role_label_snapshot": item.role_label_snapshot,
        } for item in cast_members],
        "events": [{
            "id": event.id, "sequence_number": event.sequence_number,
            "timestamp_ms": event.timestamp_ms, "event_type": event.event_type,
            "cast_member_instance_id": event.cast_member_instance_id,
            "authority_epoch": event.authority_epoch, "payload": event.payload or {},
        } for event in events],
        "annotations": [_annotation_read(db, item) for item in annotations],
        "playback_capabilities": {
            "event_seek": True, "transform_reconstruction": "position_rotation_scale_payloads",
            "camera_reconstruction": "preset_or_position_target_payloads",
            "physics_determinism": False, "skeletal_animation": False,
        },
    }


@router.post("/api/projects/{project_id}/takes/{take_id}/annotations", status_code=status.HTTP_201_CREATED)
def create_annotation(project_id: uuid.UUID, take_id: uuid.UUID, payload: AnnotationCreate, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id)
    _membership(db, project_id, user.id)
    take, run = _take_or_404(db, project_id, take_id)
    if take.status not in ("finalized", "selected"):
        raise HTTPException(status_code=409, detail="Annotations can only be added to finalized or selected takes.")
    if take.duration_ms is not None and payload.timestamp_ms > take.duration_ms:
        raise HTTPException(status_code=422, detail="Annotation timestamp exceeds the take duration.")
    if payload.event_id is not None:
        event = db.scalar(select(PerformanceEvent).where(
            PerformanceEvent.id == payload.event_id, PerformanceEvent.take_id == take.id
        ))
        if event is None:
            raise HTTPException(status_code=422, detail="The event does not belong to this take.")
    if payload.cast_member_instance_id is not None and db.scalar(select(CastMemberInstance.id).where(
        CastMemberInstance.id == payload.cast_member_instance_id,
        CastMemberInstance.scene_run_id == run.id,
    )) is None:
        raise HTTPException(status_code=422, detail="The cast member does not belong to this scene run.")
    annotation = PerformanceAnnotation(
        take_id=take.id, event_id=payload.event_id,
        cast_member_instance_id=payload.cast_member_instance_id,
        author_user_id=user.id, timestamp_ms=payload.timestamp_ms,
        category=payload.category, content=payload.content.strip(),
    )
    db.add(annotation); db.commit(); db.refresh(annotation)
    return _annotation_read(db, annotation)


@router.patch("/api/projects/{project_id}/takes/{take_id}/annotations/{annotation_id}")
def update_annotation(project_id: uuid.UUID, take_id: uuid.UUID, annotation_id: uuid.UUID, payload: AnnotationUpdate, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id)
    member = _membership(db, project_id, user.id)
    take, _ = _take_or_404(db, project_id, take_id)
    annotation = db.scalar(select(PerformanceAnnotation).where(
        PerformanceAnnotation.id == annotation_id, PerformanceAnnotation.take_id == take.id
    ))
    if annotation is None:
        raise HTTPException(status_code=404, detail="Performance annotation not found.")
    if payload.status is not None and member.role not in ("owner", "editor"):
        raise HTTPException(status_code=403, detail="Only project owners and editors can resolve director notes.")
    if annotation.author_user_id != user.id and member.role not in ("owner", "editor"):
        raise HTTPException(status_code=403, detail="You can only edit your own annotations.")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(annotation, key, value.strip() if key == "content" and value is not None else value)
    db.commit(); db.refresh(annotation)
    return _annotation_read(db, annotation)
