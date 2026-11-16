import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .audio import _media_root, _safe_path, _project_access, _sequence_or_404
from .models import AudioClip, AudioRenderJob, AudioTrack, ProductionMediaAsset, Project
from .projects import CurrentUser, DbSession, _membership, _project_or_404
from .schemas import AudioRenderJobRead

router = APIRouter(tags=["audio rendering"])


def _job_or_404(db: Session, project_id: uuid.UUID, job_id: uuid.UUID) -> AudioRenderJob:
    job = db.scalar(select(AudioRenderJob).where(
        AudioRenderJob.id == job_id,
        AudioRenderJob.project_id == project_id,
    ))
    if job is None:
        raise HTTPException(status_code=404, detail="Audio render job not found.")
    return job


def _job_read(job: AudioRenderJob) -> AudioRenderJobRead:
    return AudioRenderJobRead(
        id=job.id, project_id=job.project_id, sequence_id=job.sequence_id,
        sequence_revision=job.sequence_revision, status=job.status,
        output_content_type=job.output_content_type, output_size_bytes=job.output_size_bytes,
        output_sha256=job.output_sha256, duration_ms=job.duration_ms,
        error_message=job.error_message,
        download_url=(
            f"/api/projects/{job.project_id}/audio-renders/{job.id}/download"
            if job.status == "completed" and job.output_storage_key else None
        ),
        created_by_user_id=job.created_by_user_id, created_at=job.created_at,
        started_at=job.started_at, completed_at=job.completed_at,
    )


def _build_snapshot(db: Session, project: Project, sequence_id: uuid.UUID) -> dict:
    tracks = db.scalars(select(AudioTrack).where(
        AudioTrack.sequence_id == sequence_id,
    ).order_by(AudioTrack.track_order, AudioTrack.created_at)).all()
    has_solo = any(track.solo for track in tracks)
    snapshot_tracks = []
    duration_ms = 0
    clip_count = 0
    for track in tracks:
        if track.muted or (has_solo and not track.solo):
            continue
        rows = db.execute(
            select(AudioClip, ProductionMediaAsset)
            .join(ProductionMediaAsset, ProductionMediaAsset.id == AudioClip.media_asset_id)
            .where(AudioClip.track_id == track.id)
            .order_by(AudioClip.clip_order, AudioClip.timeline_start_ms)
        ).all()
        clips = []
        for clip, asset in rows:
            if asset.project_id != project.id:
                raise HTTPException(status_code=409, detail="An audio clip references media outside this project.")
            if asset.status != "active":
                raise HTTPException(status_code=409, detail=f'Audio source "{asset.title}" is archived.')
            source_path = _safe_path(asset.storage_key)
            if not source_path.is_file():
                raise HTTPException(status_code=409, detail=f'Audio source "{asset.title}" is missing from storage.')
            clip_duration = clip.source_out_ms - clip.source_in_ms
            timeline_end = clip.timeline_start_ms + clip_duration
            duration_ms = max(duration_ms, timeline_end)
            clips.append({
                "id": str(clip.id), "media_asset_id": str(asset.id),
                "storage_key": asset.storage_key, "sha256": asset.sha256,
                "title": asset.title, "filename": asset.original_filename,
                "source_in_ms": clip.source_in_ms, "source_out_ms": clip.source_out_ms,
                "timeline_start_ms": clip.timeline_start_ms, "duration_ms": clip_duration,
                "gain": clip.gain, "fade_in_ms": clip.fade_in_ms, "fade_out_ms": clip.fade_out_ms,
            })
            clip_count += 1
        if clips:
            snapshot_tracks.append({
                "id": str(track.id), "name": track.name, "role": track.role,
                "gain": track.gain, "pan": track.pan, "clips": clips,
            })
    if clip_count == 0:
        raise HTTPException(status_code=409, detail="Add at least one audible clip to an unmuted audio track before rendering.")
    return {
        "format": "storyforge-audio-mix", "format_version": 1,
        "project_id": str(project.id), "sequence_id": str(sequence_id),
        "duration_ms": duration_ms, "sample_rate": 48000, "channels": 2,
        "tracks": snapshot_tracks, "clip_count": clip_count,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/api/projects/{project_id}/edit-sequences/{sequence_id}/audio-renders", response_model=AudioRenderJobRead, status_code=status.HTTP_202_ACCEPTED)
def create_audio_render(project_id: uuid.UUID, sequence_id: uuid.UUID, db: DbSession, user: CurrentUser):
    project = _project_access(db, project_id, user.id, write=True)
    sequence = _sequence_or_404(db, project_id, sequence_id)
    if sequence.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft edit sequences can be rendered.")
    manifest = _build_snapshot(db, project, sequence.id)
    manifest["sequence_revision"] = sequence.revision_number
    job = AudioRenderJob(
        project_id=project.id, sequence_id=sequence.id,
        sequence_revision=sequence.revision_number, status="queued",
        render_manifest=manifest, duration_ms=manifest["duration_ms"], created_by_user_id=user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _job_read(job)


@router.get("/api/projects/{project_id}/edit-sequences/{sequence_id}/audio-renders", response_model=list[AudioRenderJobRead])
def list_audio_renders(project_id: uuid.UUID, sequence_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id)
    _membership(db, project_id, user.id)
    _sequence_or_404(db, project_id, sequence_id)
    jobs = db.scalars(select(AudioRenderJob).where(
        AudioRenderJob.project_id == project_id,
        AudioRenderJob.sequence_id == sequence_id,
    ).order_by(AudioRenderJob.created_at.desc())).all()
    return [_job_read(job) for job in jobs]


@router.get("/api/projects/{project_id}/audio-renders/{job_id}", response_model=AudioRenderJobRead)
def get_audio_render(project_id: uuid.UUID, job_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id)
    _membership(db, project_id, user.id)
    return _job_read(_job_or_404(db, project_id, job_id))


@router.get("/api/projects/{project_id}/audio-renders/{job_id}/download")
def download_audio_render(project_id: uuid.UUID, job_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id)
    _membership(db, project_id, user.id)
    job = _job_or_404(db, project_id, job_id)
    if job.status != "completed" or not job.output_storage_key:
        raise HTTPException(status_code=409, detail="The audio render is not ready for download.")
    path = _safe_path(job.output_storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Rendered audio file is missing from storage.")
    return FileResponse(
        path, media_type=job.output_content_type or "audio/wav",
        filename=f"storyforge-mix-{job.id}.wav", content_disposition_type="attachment",
    )
