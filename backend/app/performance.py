import gzip
import hashlib
import json
import os
import uuid
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import CastMemberInstance, ControllerAssignmentEvent, PerformanceCaptureChunk, PerformanceEvent, PerformanceTake, Project, SceneRun
from .projects import CurrentUser, DbSession, _membership, _project_or_404
from .schemas import (
    PerformanceEventCreate, PerformanceTakeCreate, PerformanceTakeFinalize,
    PerformanceTakeRead, PerformanceEventRead, PerformanceCaptureChunkCreate,
    PerformanceCaptureChunkRead, PerformanceCaptureTakeRead,
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



def _capture_root() -> Path:
    return Path(os.getenv("STORYFORGE_CAPTURE_DIR", "/app/storage/captures")).resolve()


def _capture_path(storage_key: str) -> Path:
    root = _capture_root()
    candidate = (root / storage_key).resolve()
    if root not in candidate.parents:
        raise HTTPException(status_code=500, detail="Invalid capture storage key.")
    return candidate


def _capture_chunk_read(chunk: PerformanceCaptureChunk, take: PerformanceTake) -> PerformanceCaptureChunkRead:
    return PerformanceCaptureChunkRead(
        id=chunk.id, chunk_index=chunk.chunk_index, sample_count=chunk.sample_count,
        start_timestamp_ms=chunk.start_timestamp_ms, end_timestamp_ms=chunk.end_timestamp_ms,
        size_bytes=chunk.size_bytes, sha256=chunk.sha256, created_at=chunk.created_at,
        download_url=f"/api/projects/{take.scene_run.project_id}/takes/{take.id}/capture-chunks/{chunk.id}",
    )


@router.get("/api/projects/{project_id}/capture-takes", response_model=list[PerformanceCaptureTakeRead])
def list_capture_takes(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id)
    _membership(db, project_id, user.id)
    rows = db.execute(
        select(PerformanceTake, func.coalesce(func.sum(PerformanceCaptureChunk.sample_count), 0))
        .join(SceneRun, SceneRun.id == PerformanceTake.scene_run_id)
        .outerjoin(PerformanceCaptureChunk, PerformanceCaptureChunk.take_id == PerformanceTake.id)
        .where(SceneRun.project_id == project_id)
        .group_by(PerformanceTake.id)
        .having(func.coalesce(func.sum(PerformanceCaptureChunk.sample_count), 0) > 0)
        .order_by(PerformanceTake.created_at.desc())
    ).all()
    return [
        PerformanceCaptureTakeRead(
            id=take.id, scene_run_id=take.scene_run_id,
            cast_member_instance_id=take.cast_member_instance_id,
            take_number=take.take_number, title=take.title, status=take.status,
            duration_ms=take.duration_ms, created_at=take.created_at, sample_count=count,
        ) for take, count in rows
    ]


@router.post(
    "/api/projects/{project_id}/takes/{take_id}/capture-chunks",
    response_model=PerformanceCaptureChunkRead,
    status_code=status.HTTP_201_CREATED,
)
def append_capture_chunk(
    project_id: uuid.UUID, take_id: uuid.UUID, payload: PerformanceCaptureChunkCreate,
    db: DbSession, user: CurrentUser,
):
    _require_editor(db, project_id, user.id)
    take = db.scalar(
        select(PerformanceTake).join(SceneRun, SceneRun.id == PerformanceTake.scene_run_id)
        .where(PerformanceTake.id == take_id, SceneRun.project_id == project_id)
    )
    if take is None:
        raise HTTPException(status_code=404, detail="Performance take not found.")
    if take.status != "recording":
        raise HTTPException(status_code=409, detail="Capture samples cannot be appended after a take is finalized.")
    previous = db.scalar(
        select(PerformanceCaptureChunk).where(PerformanceCaptureChunk.take_id == take.id)
        .order_by(PerformanceCaptureChunk.chunk_index.desc()).limit(1)
    )
    expected_index = previous.chunk_index + 1 if previous else 0
    if payload.chunk_index != expected_index:
        raise HTTPException(status_code=409, detail=f"Expected capture chunk index {expected_index}.")
    timestamps = [sample["timestamp_ms"] for sample in payload.samples]
    if previous and timestamps[0] < previous.end_timestamp_ms:
        raise HTTPException(status_code=422, detail="Capture timestamps must be monotonic across chunks.")
    if take.duration_ms is not None and timestamps[-1] > take.duration_ms:
        raise HTTPException(status_code=422, detail="Capture sample exceeds the take duration.")

    raw = json.dumps(payload.samples, separators=(",", ":"), allow_nan=False).encode("utf-8")
    compressed = gzip.compress(raw, compresslevel=6)
    chunk_id = uuid.uuid4()
    storage_key = f"{project_id}/{take.id}/{chunk_id}.json.gz"
    destination = _capture_path(storage_key)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(compressed)
    chunk = PerformanceCaptureChunk(
        id=chunk_id, take_id=take.id, chunk_index=payload.chunk_index,
        storage_key=storage_key, sha256=hashlib.sha256(compressed).hexdigest(),
        size_bytes=len(compressed), sample_count=len(payload.samples),
        start_timestamp_ms=timestamps[0], end_timestamp_ms=timestamps[-1],
    )
    try:
        db.add(chunk)
        db.commit()
        db.refresh(chunk)
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise
    return _capture_chunk_read(chunk, take)


@router.get("/api/projects/{project_id}/takes/{take_id}/capture-chunks", response_model=list[PerformanceCaptureChunkRead])
def list_capture_chunks(project_id: uuid.UUID, take_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id)
    _membership(db, project_id, user.id)
    take = db.scalar(
        select(PerformanceTake).join(SceneRun, SceneRun.id == PerformanceTake.scene_run_id)
        .where(PerformanceTake.id == take_id, SceneRun.project_id == project_id)
    )
    if take is None:
        raise HTTPException(status_code=404, detail="Performance take not found.")
    chunks = db.scalars(
        select(PerformanceCaptureChunk).where(PerformanceCaptureChunk.take_id == take.id)
        .order_by(PerformanceCaptureChunk.chunk_index)
    ).all()
    return [_capture_chunk_read(chunk, take) for chunk in chunks]


@router.get("/api/projects/{project_id}/takes/{take_id}/capture-chunks/{chunk_id}")
def read_capture_chunk(
    project_id: uuid.UUID, take_id: uuid.UUID, chunk_id: uuid.UUID,
    db: DbSession, user: CurrentUser,
):
    _project_or_404(db, project_id)
    _membership(db, project_id, user.id)
    chunk = db.scalar(
        select(PerformanceCaptureChunk)
        .join(PerformanceTake, PerformanceTake.id == PerformanceCaptureChunk.take_id)
        .join(SceneRun, SceneRun.id == PerformanceTake.scene_run_id)
        .where(
            PerformanceCaptureChunk.id == chunk_id,
            PerformanceCaptureChunk.take_id == take_id,
            SceneRun.project_id == project_id,
        )
    )
    if chunk is None:
        raise HTTPException(status_code=404, detail="Capture chunk not found.")
    path = _capture_path(chunk.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Capture chunk file is missing from storage.")
    try:
        compressed = path.read_bytes()
        if hashlib.sha256(compressed).hexdigest() != chunk.sha256:
            raise HTTPException(status_code=500, detail="Capture chunk integrity check failed.")
        samples = json.loads(gzip.decompress(compressed).decode("utf-8"))
    except (OSError, gzip.BadGzipFile, EOFError, UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="Capture chunk could not be decoded.")
    return {"chunk_index": chunk.chunk_index, "samples": samples}


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
