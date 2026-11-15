import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import CastMemberInstance, ControllerAssignmentEvent, PerformanceEvent, PerformanceTake, Project, SceneRun
from .projects import CurrentUser, DbSession, _membership, _project_or_404
from .schemas import (
    PerformanceEventCreate, PerformanceTakeCreate, PerformanceTakeFinalize,
    PerformanceTakeRead, PerformanceEventRead,
)

router = APIRouter(tags=["performance capture"])


def _require_editor(db: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> Project:
    project = _project_or_404(db, project_id)
    member = _membership(db, project_id, user_id)
    if member.role not in ("owner", "editor"):
        raise HTTPException(status_code=403, detail="Only project owners and editors can record production takes.")
    return project


def _take_read(db: Session, take: PerformanceTake) -> PerformanceTakeRead:
    events = db.scalars(
        select(PerformanceEvent).where(PerformanceEvent.take_id == take.id)
        .order_by(PerformanceEvent.sequence_number)
    ).all()
    return PerformanceTakeRead(
        id=take.id, scene_run_id=take.scene_run_id,
        cast_member_instance_id=take.cast_member_instance_id,
        take_number=take.take_number, title=take.title, status=take.status,
        camera_snapshot=take.camera_snapshot or {}, state_snapshot=take.state_snapshot or {}, duration_ms=take.duration_ms,
        created_by_user_id=take.created_by_user_id, created_at=take.created_at,
        finalized_at=take.finalized_at,
        events=[PerformanceEventRead.model_validate(event, from_attributes=True) for event in events],
    )


@router.post("/api/projects/{project_id}/scene-runs/{run_id}/takes", response_model=PerformanceTakeRead, status_code=status.HTTP_201_CREATED)
def create_take(project_id: uuid.UUID, run_id: uuid.UUID, payload: PerformanceTakeCreate, db: DbSession, user: CurrentUser):
    _require_editor(db, project_id, user.id)
    run = db.scalar(select(SceneRun).where(SceneRun.id == run_id, SceneRun.project_id == project_id))
    if run is None:
        raise HTTPException(status_code=404, detail="Scene run not found.")
    if run.status not in ("prepared", "running"):
        raise HTTPException(status_code=409, detail="A take can only be recorded for a prepared or running scene.")
    if payload.cast_member_instance_id is not None:
        member = db.scalar(select(CastMemberInstance).where(
            CastMemberInstance.id == payload.cast_member_instance_id,
            CastMemberInstance.scene_run_id == run.id,
            CastMemberInstance.instance_status == "ready",
        ))
        if member is None:
            raise HTTPException(status_code=422, detail="The selected cast member does not belong to this scene run.")
    active = db.scalar(select(PerformanceTake.id).where(
        PerformanceTake.scene_run_id == run.id, PerformanceTake.status == "recording"
    ).limit(1))
    if active:
        raise HTTPException(status_code=409, detail="Finish or discard the current recording before starting another take.")
    take_number = (db.scalar(select(func.max(PerformanceTake.take_number)).where(PerformanceTake.scene_run_id == run.id)) or 0) + 1
    take = PerformanceTake(
        scene_run_id=run.id, cast_member_instance_id=payload.cast_member_instance_id,
        take_number=take_number, title=payload.title,
        camera_snapshot=payload.camera_snapshot, state_snapshot=payload.state_snapshot,
        status="recording", created_by_user_id=user.id,
    )
    if run.status == "prepared":
        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
    db.add(take)
    db.commit()
    db.refresh(take)
    return _take_read(db, take)


@router.post("/api/projects/{project_id}/takes/{take_id}/events", response_model=PerformanceTakeRead)
def append_take_events(project_id: uuid.UUID, take_id: uuid.UUID, payload: list[PerformanceEventCreate], db: DbSession, user: CurrentUser):
    _require_editor(db, project_id, user.id)
    take = db.scalar(
        select(PerformanceTake).join(SceneRun, SceneRun.id == PerformanceTake.scene_run_id)
        .where(PerformanceTake.id == take_id, SceneRun.project_id == project_id)
    )
    if take is None:
        raise HTTPException(status_code=404, detail="Performance take not found.")
    if take.status != "recording":
        raise HTTPException(status_code=409, detail="Events cannot be appended to a take that is not recording.")
    if not payload:
        return _take_read(db, take)
    if len(payload) > 250:
        raise HTTPException(status_code=422, detail="A single event batch cannot exceed 250 events.")
    existing = db.scalar(select(func.max(PerformanceEvent.sequence_number)).where(PerformanceEvent.take_id == take.id))
    expected_sequence = (existing + 1) if existing is not None else 0
    previous_timestamp = db.scalar(select(func.max(PerformanceEvent.timestamp_ms)).where(PerformanceEvent.take_id == take.id))
    run = db.get(SceneRun, take.scene_run_id)
    for offset, event in enumerate(payload):
        if event.sequence_number != expected_sequence + offset:
            raise HTTPException(status_code=409, detail=f"Expected event sequence {expected_sequence + offset}.")
        if previous_timestamp is not None and event.timestamp_ms < previous_timestamp:
            raise HTTPException(status_code=422, detail="Performance event timestamps must be monotonic.")
        if offset and event.timestamp_ms < payload[offset - 1].timestamp_ms:
            raise HTTPException(status_code=422, detail="Performance event timestamps must be monotonic.")
        if take.duration_ms is not None and event.timestamp_ms > take.duration_ms:
            raise HTTPException(status_code=422, detail="Event timestamp exceeds the take duration.")
        if event.cast_member_instance_id is not None:
            instance = db.scalar(select(CastMemberInstance).where(
                CastMemberInstance.id == event.cast_member_instance_id,
                CastMemberInstance.scene_run_id == run.id,
            ))
            if instance is None:
                raise HTTPException(status_code=422, detail="Performance event cast member does not belong to this scene run.")
            if event.authority_epoch is None or db.scalar(select(ControllerAssignmentEvent.id).where(
                ControllerAssignmentEvent.cast_member_instance_id == instance.id,
                ControllerAssignmentEvent.authority_epoch == event.authority_epoch,
            )) is None:
                raise HTTPException(status_code=409, detail="Performance event uses an unknown controller authority epoch.")
        elif event.authority_epoch is not None:
            raise HTTPException(status_code=422, detail="An authority epoch requires a cast member instance.")
    db.add_all([
        PerformanceEvent(
            take_id=take.id, sequence_number=event.sequence_number,
            timestamp_ms=event.timestamp_ms, event_type=event.event_type,
            cast_member_instance_id=event.cast_member_instance_id, authority_epoch=event.authority_epoch,
            payload=event.payload,
        ) for event in payload
    ])
    db.commit()
    db.refresh(take)
    return _take_read(db, take)


@router.post("/api/projects/{project_id}/takes/{take_id}/finalize", response_model=PerformanceTakeRead)
def finalize_take(project_id: uuid.UUID, take_id: uuid.UUID, payload: PerformanceTakeFinalize, db: DbSession, user: CurrentUser):
    _require_editor(db, project_id, user.id)
    take = db.scalar(
        select(PerformanceTake).join(SceneRun, SceneRun.id == PerformanceTake.scene_run_id)
        .where(PerformanceTake.id == take_id, SceneRun.project_id == project_id)
    )
    if take is None:
        raise HTTPException(status_code=404, detail="Performance take not found.")
    if take.status != "recording":
        raise HTTPException(status_code=409, detail="Only a recording take can be finalized.")
    latest_event = db.scalar(select(func.max(PerformanceEvent.timestamp_ms)).where(PerformanceEvent.take_id == take.id))
    if latest_event is not None and latest_event > payload.duration_ms:
        raise HTTPException(status_code=422, detail="Take duration cannot precede its final event.")
    take.status = "finalized"
    take.duration_ms = payload.duration_ms
    take.finalized_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(take)
    return _take_read(db, take)



@router.get("/api/projects/{project_id}/takes", response_model=list[PerformanceTakeRead])
def list_takes(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id)
    _membership(db, project_id, user.id)
    takes = db.scalars(select(PerformanceTake).join(
        SceneRun, SceneRun.id == PerformanceTake.scene_run_id,
    ).where(SceneRun.project_id == project_id).order_by(
        PerformanceTake.created_at.desc(), PerformanceTake.take_number.desc(),
    )).all()
    return [_take_read(db, take) for take in takes]


@router.post("/api/projects/{project_id}/takes/{take_id}/select", response_model=PerformanceTakeRead)
def select_take(project_id: uuid.UUID, take_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _require_editor(db, project_id, user.id)
    take = db.scalar(select(PerformanceTake).join(
        SceneRun, SceneRun.id == PerformanceTake.scene_run_id,
    ).where(PerformanceTake.id == take_id, SceneRun.project_id == project_id).with_for_update())
    if take is None:
        raise HTTPException(status_code=404, detail="Performance take not found.")
    if take.status not in ("finalized", "selected"):
        raise HTTPException(status_code=409, detail="Only finalized takes can be selected for editing.")
    run = db.get(SceneRun, take.scene_run_id)
    previous = db.scalars(select(PerformanceTake).join(
        SceneRun, SceneRun.id == PerformanceTake.scene_run_id,
    ).where(
        SceneRun.scene_id == run.scene_id, PerformanceTake.status == "selected",
        PerformanceTake.id != take.id,
    ).with_for_update()).all()
    for item in previous:
        item.status = "finalized"
    take.status = "selected"
    db.commit(); db.refresh(take)
    return _take_read(db, take)


@router.post("/api/projects/{project_id}/takes/{take_id}/discard", response_model=PerformanceTakeRead)
def discard_take(project_id: uuid.UUID, take_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _require_editor(db, project_id, user.id)
    take = db.scalar(select(PerformanceTake).join(
        SceneRun, SceneRun.id == PerformanceTake.scene_run_id,
    ).where(PerformanceTake.id == take_id, SceneRun.project_id == project_id))
    if take is None:
        raise HTTPException(status_code=404, detail="Performance take not found.")
    if take.status == "selected":
        raise HTTPException(status_code=409, detail="A selected take must be deselected before it can be discarded.")
    if take.status == "recording":
        raise HTTPException(status_code=409, detail="Finalize a recording before discarding it.")
    take.status = "discarded"
    db.commit(); db.refresh(take)
    return _take_read(db, take)


@router.get("/api/projects/{project_id}/takes/{take_id}", response_model=PerformanceTakeRead)
def get_take(project_id: uuid.UUID, take_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id)
    _membership(db, project_id, user.id)
    take = db.scalar(
        select(PerformanceTake).join(SceneRun, SceneRun.id == PerformanceTake.scene_run_id)
        .where(PerformanceTake.id == take_id, SceneRun.project_id == project_id)
    )
    if take is None:
        raise HTTPException(status_code=404, detail="Performance take not found.")
    return _take_read(db, take)
