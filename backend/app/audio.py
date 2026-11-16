import hashlib
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import AudioClip, AudioTrack, EditSequence, ProductionMediaAsset, Project
from .projects import CurrentUser, DbSession, _membership, _project_or_404
from .schemas import (
    AudioClipCreate, AudioClipRead, AudioClipUpdate,
    AudioTrackCreate, AudioTrackRead, AudioTrackUpdate,
    ProductionMediaAssetRead,
)

router = APIRouter(tags=["production audio"])

MAX_AUDIO_UPLOAD_BYTES = 250 * 1024 * 1024
AUDIO_FORMATS = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".aac": "audio/aac",
    ".flac": "audio/flac",
}


def _project_access(db: Session, project_id: uuid.UUID, user_id: uuid.UUID, *, write: bool = False) -> Project:
    project = _project_or_404(db, project_id)
    membership = _membership(db, project_id, user_id)
    if write:
        if membership.role not in ("owner", "editor"):
            raise HTTPException(status_code=403, detail="Only project owners and editors can manage production audio.")
        if project.current_phase != "production":
            raise HTTPException(status_code=409, detail="Audio editing is available only during the production phase.")
    return project


def _sequence_or_404(db: Session, project_id: uuid.UUID, sequence_id: uuid.UUID) -> EditSequence:
    sequence = db.scalar(select(EditSequence).where(
        EditSequence.id == sequence_id,
        EditSequence.project_id == project_id,
    ))
    if sequence is None:
        raise HTTPException(status_code=404, detail="Edit sequence not found.")
    return sequence


def _track_or_404(db: Session, sequence_id: uuid.UUID, track_id: uuid.UUID) -> AudioTrack:
    track = db.scalar(select(AudioTrack).where(
        AudioTrack.id == track_id,
        AudioTrack.sequence_id == sequence_id,
    ))
    if track is None:
        raise HTTPException(status_code=404, detail="Audio track not found.")
    return track


def _asset_or_404(db: Session, project_id: uuid.UUID, asset_id: uuid.UUID) -> ProductionMediaAsset:
    asset = db.scalar(select(ProductionMediaAsset).where(
        ProductionMediaAsset.id == asset_id,
        ProductionMediaAsset.project_id == project_id,
    ))
    if asset is None:
        raise HTTPException(status_code=404, detail="Audio asset not found in this project.")
    return asset


def _media_root() -> Path:
    return Path(os.getenv("STORYFORGE_PRODUCTION_MEDIA_DIR", "/app/storage/production-audio")).resolve()


def _safe_path(storage_key: str) -> Path:
    root = _media_root()
    candidate = (root / storage_key).resolve()
    if root != candidate and root not in candidate.parents:
        raise HTTPException(status_code=404, detail="Audio file not found.")
    return candidate


def _asset_read(asset: ProductionMediaAsset) -> ProductionMediaAssetRead:
    return ProductionMediaAssetRead(
        id=asset.id, project_id=asset.project_id, title=asset.title,
        original_filename=asset.original_filename, content_type=asset.content_type,
        size_bytes=asset.size_bytes, sha256=asset.sha256, duration_ms=asset.duration_ms,
        status=asset.status,
        download_url=f"/api/projects/{asset.project_id}/production/media/{asset.id}/download",
        created_by_user_id=asset.created_by_user_id, created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


def _track_read(db: Session, project_id: uuid.UUID, track: AudioTrack) -> AudioTrackRead:
    rows = db.execute(
        select(AudioClip, ProductionMediaAsset)
        .join(ProductionMediaAsset, ProductionMediaAsset.id == AudioClip.media_asset_id)
        .where(AudioClip.track_id == track.id)
        .order_by(AudioClip.clip_order, AudioClip.timeline_start_ms)
    ).all()
    clips = [
        AudioClipRead(
            id=clip.id, track_id=clip.track_id, media_asset_id=asset.id,
            asset_title=asset.title, original_filename=asset.original_filename,
            content_type=asset.content_type,
            download_url=f"/api/projects/{project_id}/production/media/{asset.id}/download",
            asset_duration_ms=asset.duration_ms, clip_order=clip.clip_order,
            source_in_ms=clip.source_in_ms, source_out_ms=clip.source_out_ms,
            timeline_start_ms=clip.timeline_start_ms, gain=clip.gain,
            fade_in_ms=clip.fade_in_ms, fade_out_ms=clip.fade_out_ms,
            created_at=clip.created_at,
        )
        for clip, asset in rows
    ]
    return AudioTrackRead(
        id=track.id, sequence_id=track.sequence_id, name=track.name, role=track.role,
        track_order=track.track_order, gain=track.gain, pan=track.pan,
        muted=track.muted, solo=track.solo, created_by_user_id=track.created_by_user_id,
        created_at=track.created_at, updated_at=track.updated_at, clips=clips,
    )


@router.get("/api/projects/{project_id}/production/media", response_model=list[ProductionMediaAssetRead])
def list_audio_assets(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id)
    assets = db.scalars(select(ProductionMediaAsset).where(
        ProductionMediaAsset.project_id == project_id,
        ProductionMediaAsset.status == "active",
    ).order_by(ProductionMediaAsset.created_at.desc())).all()
    return [_asset_read(asset) for asset in assets]


@router.post("/api/projects/{project_id}/production/media", response_model=ProductionMediaAssetRead, status_code=status.HTTP_201_CREATED)
async def upload_audio_asset(
    project_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=240),
    duration_ms: int | None = Form(None),
):
    _project_access(db, project_id, user.id, write=True)
    if duration_ms is not None and duration_ms <= 0:
        raise HTTPException(status_code=422, detail="Audio duration must be greater than zero.")
    original = (file.filename or "").replace("\\", "/").split("/")[-1].strip()
    if not original or original in {".", ".."}:
        raise HTTPException(status_code=422, detail="A valid original filename is required.")
    suffix = Path(original).suffix.lower()
    content_type = AUDIO_FORMATS.get(suffix)
    if content_type is None:
        raise HTTPException(status_code=415, detail="Unsupported audio format. Upload MP3, WAV, M4A, OGG, AAC or FLAC.")
    clean_title = title.strip()
    if not clean_title:
        raise HTTPException(status_code=422, detail="Audio asset title cannot be blank.")
    original = original[-255:]

    asset_id = uuid.uuid4()
    storage_key = f"{project_id}/{asset_id}{suffix}"
    target = _safe_path(storage_key)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    digest = hashlib.sha256()
    size = 0
    try:
        with temporary.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_AUDIO_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Audio uploads are limited to 250 MiB per file.")
                digest.update(chunk)
                output.write(chunk)
        if size == 0:
            raise HTTPException(status_code=422, detail="Empty audio files cannot be uploaded.")
        os.replace(temporary, target)
        asset = ProductionMediaAsset(
            id=asset_id, project_id=project_id, title=clean_title,
            original_filename=original, content_type=content_type,
            size_bytes=size, sha256=digest.hexdigest(), storage_key=storage_key,
            duration_ms=duration_ms, created_by_user_id=user.id,
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return _asset_read(asset)
    except Exception:
        db.rollback()
        temporary.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


@router.get("/api/projects/{project_id}/production/media/{asset_id}/download")
def download_audio_asset(project_id: uuid.UUID, asset_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id)
    asset = _asset_or_404(db, project_id, asset_id)
    path = _safe_path(asset.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Audio file is missing from storage.")
    return FileResponse(
        path, media_type=asset.content_type, filename=asset.original_filename,
        content_disposition_type="inline",
    )


@router.post("/api/projects/{project_id}/edit-sequences/{sequence_id}/audio-tracks", response_model=AudioTrackRead, status_code=status.HTTP_201_CREATED)
def create_audio_track(project_id: uuid.UUID, sequence_id: uuid.UUID, payload: AudioTrackCreate, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id, write=True)
    sequence = _sequence_or_404(db, project_id, sequence_id)
    if sequence.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft edit sequences can be changed.")
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Audio track name cannot be blank.")
    order = (db.scalar(select(func.max(AudioTrack.track_order)).where(AudioTrack.sequence_id == sequence.id)) or 0) + 1
    track = AudioTrack(
        sequence_id=sequence.id, name=name, role=payload.role, track_order=order,
        gain=payload.gain, pan=payload.pan, created_by_user_id=user.id,
    )
    db.add(track)
    sequence.revision_number += 1
    db.commit()
    db.refresh(track)
    return _track_read(db, project_id, track)


@router.get("/api/projects/{project_id}/edit-sequences/{sequence_id}/audio-tracks", response_model=list[AudioTrackRead])
def list_audio_tracks(project_id: uuid.UUID, sequence_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id)
    _sequence_or_404(db, project_id, sequence_id)
    tracks = db.scalars(select(AudioTrack).where(
        AudioTrack.sequence_id == sequence_id,
    ).order_by(AudioTrack.track_order, AudioTrack.created_at)).all()
    return [_track_read(db, project_id, track) for track in tracks]


@router.patch("/api/projects/{project_id}/edit-sequences/{sequence_id}/audio-tracks/{track_id}", response_model=AudioTrackRead)
def update_audio_track(project_id: uuid.UUID, sequence_id: uuid.UUID, track_id: uuid.UUID, payload: AudioTrackUpdate, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id, write=True)
    sequence = _sequence_or_404(db, project_id, sequence_id)
    if sequence.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft edit sequences can be changed.")
    track = _track_or_404(db, sequence.id, track_id)
    values = payload.model_dump(exclude_unset=True)
    if values.get("name") is not None:
        values["name"] = values["name"].strip()
        if not values["name"]:
            raise HTTPException(status_code=422, detail="Audio track name cannot be blank.")
    for key, value in values.items():
        if value is not None:
            setattr(track, key, value)
    sequence.revision_number += 1
    db.commit()
    db.refresh(track)
    return _track_read(db, project_id, track)


@router.delete("/api/projects/{project_id}/edit-sequences/{sequence_id}/audio-tracks/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_audio_track(project_id: uuid.UUID, sequence_id: uuid.UUID, track_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id, write=True)
    sequence = _sequence_or_404(db, project_id, sequence_id)
    if sequence.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft edit sequences can be changed.")
    track = _track_or_404(db, sequence.id, track_id)
    db.delete(track)
    sequence.revision_number += 1
    db.commit()


@router.post("/api/projects/{project_id}/edit-sequences/{sequence_id}/audio-tracks/{track_id}/clips", response_model=AudioTrackRead, status_code=status.HTTP_201_CREATED)
def add_audio_clip(project_id: uuid.UUID, sequence_id: uuid.UUID, track_id: uuid.UUID, payload: AudioClipCreate, db: DbSession, user: CurrentUser):
    project = _project_access(db, project_id, user.id, write=True)
    sequence = _sequence_or_404(db, project_id, sequence_id)
    if sequence.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft edit sequences can be changed.")
    track = _track_or_404(db, sequence.id, track_id)
    asset = _asset_or_404(db, project.id, payload.media_asset_id)
    if asset.status != "active":
        raise HTTPException(status_code=409, detail="Archived audio assets cannot be placed in new clips.")
    _validate_clip_range(payload.source_in_ms, payload.source_out_ms, payload.fade_in_ms, payload.fade_out_ms, asset.duration_ms)
    order = (db.scalar(select(func.max(AudioClip.clip_order)).where(AudioClip.track_id == track.id)) or 0) + 1
    db.add(AudioClip(
        track_id=track.id, media_asset_id=asset.id, clip_order=order,
        source_in_ms=payload.source_in_ms, source_out_ms=payload.source_out_ms,
        timeline_start_ms=payload.timeline_start_ms, gain=payload.gain,
        fade_in_ms=payload.fade_in_ms, fade_out_ms=payload.fade_out_ms,
    ))
    sequence.revision_number += 1
    db.commit()
    return _track_read(db, project.id, db.get(AudioTrack, track.id))


def _validate_clip_range(source_in: int, source_out: int, fade_in: int, fade_out: int, asset_duration: int | None) -> None:
    if source_in >= source_out:
        raise HTTPException(status_code=422, detail="Audio source in/out points are invalid.")
    if asset_duration is not None and source_out > asset_duration:
        raise HTTPException(status_code=422, detail="Audio clip source range exceeds the source asset duration.")
    clip_duration = source_out - source_in
    if fade_in > clip_duration or fade_out > clip_duration or fade_in + fade_out > clip_duration:
        raise HTTPException(status_code=422, detail="Audio fades cannot exceed the clip duration.")


@router.patch("/api/projects/{project_id}/edit-sequences/{sequence_id}/audio-tracks/{track_id}/clips/{clip_id}", response_model=AudioTrackRead)
def update_audio_clip(project_id: uuid.UUID, sequence_id: uuid.UUID, track_id: uuid.UUID, clip_id: uuid.UUID, payload: AudioClipUpdate, db: DbSession, user: CurrentUser):
    project = _project_access(db, project_id, user.id, write=True)
    sequence = _sequence_or_404(db, project_id, sequence_id)
    if sequence.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft edit sequences can be changed.")
    track = _track_or_404(db, sequence.id, track_id)
    clip = db.scalar(select(AudioClip).where(AudioClip.id == clip_id, AudioClip.track_id == track.id))
    if clip is None:
        raise HTTPException(status_code=404, detail="Audio clip not found.")
    values = {key: value for key, value in payload.model_dump(exclude_unset=True).items() if value is not None}
    source_in = values.get("source_in_ms", clip.source_in_ms)
    source_out = values.get("source_out_ms", clip.source_out_ms)
    fade_in = values.get("fade_in_ms", clip.fade_in_ms)
    fade_out = values.get("fade_out_ms", clip.fade_out_ms)
    asset = _asset_or_404(db, project.id, clip.media_asset_id)
    _validate_clip_range(source_in, source_out, fade_in, fade_out, asset.duration_ms)
    for key, value in values.items():
        setattr(clip, key, value)
    sequence.revision_number += 1
    db.commit()
    return _track_read(db, project.id, db.get(AudioTrack, track.id))


@router.delete("/api/projects/{project_id}/edit-sequences/{sequence_id}/audio-tracks/{track_id}/clips/{clip_id}", response_model=AudioTrackRead)
def delete_audio_clip(project_id: uuid.UUID, sequence_id: uuid.UUID, track_id: uuid.UUID, clip_id: uuid.UUID, db: DbSession, user: CurrentUser):
    project = _project_access(db, project_id, user.id, write=True)
    sequence = _sequence_or_404(db, project_id, sequence_id)
    if sequence.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft edit sequences can be changed.")
    track = _track_or_404(db, sequence.id, track_id)
    clip = db.scalar(select(AudioClip).where(AudioClip.id == clip_id, AudioClip.track_id == track.id))
    if clip is None:
        raise HTTPException(status_code=404, detail="Audio clip not found.")
    db.delete(clip)
    sequence.revision_number += 1
    db.commit()
    return _track_read(db, project.id, db.get(AudioTrack, track.id))
