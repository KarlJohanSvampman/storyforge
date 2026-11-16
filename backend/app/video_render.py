import hashlib
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .audio import _project_access, _safe_path, _sequence_or_404
from .models import CastMemberInstance, EditSequence, EditSequenceItem, PerformanceEvent, PerformanceTake, ProductionVideoAsset, SceneRun, StoryboardScene, VideoRenderJob
from .projects import CurrentUser, DbSession, _membership, _project_or_404
from .schemas import ProductionVideoAssetRead, VideoRenderJobRead

router = APIRouter(tags=["production video"])

MAX_VIDEO_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024
MAX_VIDEO_DURATION_MS = 8 * 60 * 60 * 1000
MAX_HEADLESS_DURATION_MS = 10 * 60 * 1000


def _job_or_404(db: Session, project_id: uuid.UUID, job_id: uuid.UUID) -> VideoRenderJob:
    job = db.scalar(select(VideoRenderJob).where(
        VideoRenderJob.id == job_id,
        VideoRenderJob.project_id == project_id,
    ))
    if job is None:
        raise HTTPException(status_code=404, detail="Video render job not found.")
    return job


def _asset_or_404(db: Session, project_id: uuid.UUID, asset_id: uuid.UUID) -> ProductionVideoAsset:
    asset = db.scalar(select(ProductionVideoAsset).where(
        ProductionVideoAsset.id == asset_id,
        ProductionVideoAsset.project_id == project_id,
    ))
    if asset is None:
        raise HTTPException(status_code=404, detail="Video asset not found in this project.")
    return asset


def _job_read(job: VideoRenderJob) -> VideoRenderJobRead:
    return VideoRenderJobRead(
        id=job.id, project_id=job.project_id, sequence_id=job.sequence_id,
        sequence_revision=job.sequence_revision, status=job.status,
        render_source=job.render_source, input_size_bytes=job.input_size_bytes, output_size_bytes=job.output_size_bytes,
        output_sha256=job.output_sha256, duration_ms=job.duration_ms,
        width=job.width, height=job.height, error_message=job.error_message,
        download_url=(
            f"/api/projects/{job.project_id}/video-renders/{job.id}/download"
            if job.status == "completed" and job.output_storage_key else None
        ),
        created_by_user_id=job.created_by_user_id, created_at=job.created_at,
        started_at=job.started_at, completed_at=job.completed_at,
    )


def _asset_read(asset: ProductionVideoAsset) -> ProductionVideoAssetRead:
    return ProductionVideoAssetRead(
        id=asset.id, project_id=asset.project_id, sequence_id=asset.sequence_id,
        render_job_id=asset.render_job_id, sequence_revision=asset.sequence_revision,
        title=asset.title, original_filename=asset.original_filename,
        content_type=asset.content_type, size_bytes=asset.size_bytes, sha256=asset.sha256,
        duration_ms=asset.duration_ms, width=asset.width, height=asset.height,
        status=asset.status,
        download_url=f"/api/projects/{asset.project_id}/production/videos/{asset.id}/download",
        created_by_user_id=asset.created_by_user_id, created_at=asset.created_at,
    )


@router.post(
    "/api/projects/{project_id}/edit-sequences/{sequence_id}/video-renders",
    response_model=VideoRenderJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_video_render(
    project_id: uuid.UUID,
    sequence_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=240),
    sequence_revision: int = Form(..., ge=1),
    expected_duration_ms: int = Form(..., gt=0, le=MAX_VIDEO_DURATION_MS),
):
    project = _project_access(db, project_id, user.id, write=True)
    sequence = db.scalar(select(EditSequence).where(
        EditSequence.id == sequence_id,
        EditSequence.project_id == project_id,
    ).with_for_update())
    if sequence is None:
        raise HTTPException(status_code=404, detail="Edit sequence not found.")
    if sequence.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft edit sequences can be exported.")
    if sequence.revision_number != sequence_revision:
        raise HTTPException(status_code=409, detail="The edit sequence changed during export. Reload the sequence and render again.")
    original = (file.filename or "").replace("\\", "/").split("/")[-1].strip()
    if not original or Path(original).suffix.lower() != ".webm":
        raise HTTPException(status_code=415, detail="Upload a browser-captured WebM video.")
    if not (file.content_type or "").lower().startswith("video/webm"):
        raise HTTPException(status_code=415, detail="The uploaded video must use the video/webm media type.")
    clean_title = title.strip()
    if not clean_title:
        raise HTTPException(status_code=422, detail="Video title cannot be blank.")

    job_id = uuid.uuid4()
    storage_key = f"video-exports/incoming/{project_id}/{job_id}.webm"
    target = _safe_path(storage_key)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".webm.part")
    digest = hashlib.sha256()
    size = 0
    try:
        with temporary.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_VIDEO_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Video uploads are limited to 2 GiB per export.")
                digest.update(chunk)
                output.write(chunk)
        if size == 0:
            raise HTTPException(status_code=422, detail="An empty video cannot be exported.")
        os.replace(temporary, target)
        job = VideoRenderJob(
            id=job_id, project_id=project.id, sequence_id=sequence.id,
            sequence_revision=sequence.revision_number, status="queued", render_source="webm_upload",
            title=clean_title, source_filename=original,
            input_storage_key=storage_key, input_size_bytes=size,
            input_sha256=digest.hexdigest(), input_content_type=file.content_type or "video/webm",
            expected_duration_ms=expected_duration_ms, created_by_user_id=user.id,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return _job_read(job)
    except Exception:
        db.rollback()
        temporary.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


@router.post(
    "/api/projects/{project_id}/edit-sequences/{sequence_id}/scene-renders",
    response_model=VideoRenderJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_headless_scene_render(
    project_id: uuid.UUID,
    sequence_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
):
    project = _project_access(db, project_id, user.id, write=True)
    sequence = db.scalar(select(EditSequence).where(
        EditSequence.id == sequence_id,
        EditSequence.project_id == project_id,
    ).with_for_update())
    if sequence is None:
        raise HTTPException(status_code=404, detail="Edit sequence not found.")
    if sequence.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft edit sequences can be rendered.")
    items = db.scalars(select(EditSequenceItem).where(
        EditSequenceItem.sequence_id == sequence.id,
    ).order_by(EditSequenceItem.item_order)).all()
    if not items:
        raise HTTPException(status_code=422, detail="Add at least one selected take before rendering.")

    clips = []
    for item in items:
        row = db.execute(
            select(PerformanceTake, SceneRun, StoryboardScene)
            .join(SceneRun, SceneRun.id == PerformanceTake.scene_run_id)
            .join(StoryboardScene, StoryboardScene.id == item.scene_id)
            .where(
                PerformanceTake.id == item.take_id,
                SceneRun.project_id == project.id,
                SceneRun.scene_id == item.scene_id,
                PerformanceTake.status == "selected",
            )
        ).first()
        if row is None:
            raise HTTPException(status_code=409, detail="Every edit clip must reference a selected take from this project.")
        take, run, scene = row
        if take.duration_ms is None or item.in_ms < 0 or item.out_ms > take.duration_ms or item.in_ms >= item.out_ms:
            raise HTTPException(status_code=422, detail="An edit clip has invalid source trim points.")
        cast = db.scalars(select(CastMemberInstance).where(
            CastMemberInstance.scene_run_id == run.id,
            CastMemberInstance.instance_status == "ready",
        ).order_by(CastMemberInstance.created_at, CastMemberInstance.id)).all()
        events = db.scalars(select(PerformanceEvent).where(
            PerformanceEvent.take_id == take.id,
        ).order_by(PerformanceEvent.timestamp_ms, PerformanceEvent.sequence_number)).all()
        clips.append({
            "item_id": str(item.id), "take_id": str(take.id), "scene_id": str(scene.id),
            "scene_title": scene.title, "item_order": item.item_order,
            "in_ms": item.in_ms, "out_ms": item.out_ms,
            "duration_ms": item.out_ms - item.in_ms,
            "transition": item.transition, "title_overlay": item.title_overlay,
            "effects": item.effects or {}, "camera_snapshot": take.camera_snapshot or {},
            "state_snapshot": take.state_snapshot or {},
            "cast_members": [{
                "id": str(member.id), "actor_name": member.actor_name_snapshot,
                "character_name": member.character_name_snapshot,
                "role_label": member.role_label_snapshot,
            } for member in cast],
            "events": [{
                "timestamp_ms": event.timestamp_ms, "sequence_number": event.sequence_number,
                "event_type": event.event_type,
                "cast_member_instance_id": str(event.cast_member_instance_id) if event.cast_member_instance_id else None,
                "payload": event.payload or {},
            } for event in events],
        })

    transition_ms = 450
    total_duration = sum(clip["duration_ms"] for clip in clips)
    for index in range(1, len(clips)):
        if clips[index]["transition"] in ("fade", "dissolve"):
            overlap = min(transition_ms, clips[index - 1]["duration_ms"] // 3, clips[index]["duration_ms"] // 3)
            clips[index]["transition_duration_ms"] = max(0, overlap)
            total_duration -= max(0, overlap)
        else:
            clips[index]["transition_duration_ms"] = 0
    if total_duration <= 0 or total_duration > MAX_HEADLESS_DURATION_MS:
        raise HTTPException(status_code=422, detail="Headless animatic renders are limited to 10 minutes per export.")

    manifest = {
        "format_version": 1, "renderer": "storyforge-headless-animatic-v1",
        "project_id": str(project.id), "sequence_id": str(sequence.id),
        "sequence_revision": sequence.revision_number, "width": 1280, "height": 720,
        "fps": 24, "duration_ms": total_duration, "clips": clips,
        "capabilities": {
            "transform_reconstruction": True, "camera_preset_framing": True,
            "title_overlays": True, "cut": True, "fade_through_black": True,
            "cross_dissolve": True, "skeletal_animation": False, "full_3d_assets": False,
        },
    }
    job = VideoRenderJob(
        project_id=project.id, sequence_id=sequence.id,
        sequence_revision=sequence.revision_number, status="queued",
        render_source="headless_animatic", render_manifest=manifest,
        title=sequence.name, source_filename="storyforge-headless-animatic",
        input_storage_key=None, input_size_bytes=None, input_sha256=None,
        input_content_type=None, expected_duration_ms=total_duration,
        created_by_user_id=user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _job_read(job)


@router.get(
    "/api/projects/{project_id}/edit-sequences/{sequence_id}/video-renders",
    response_model=list[VideoRenderJobRead],
)
def list_video_renders(project_id: uuid.UUID, sequence_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id)
    _membership(db, project_id, user.id)
    _sequence_or_404(db, project_id, sequence_id)
    jobs = db.scalars(select(VideoRenderJob).where(
        VideoRenderJob.project_id == project_id,
        VideoRenderJob.sequence_id == sequence_id,
    ).order_by(VideoRenderJob.created_at.desc())).all()
    return [_job_read(job) for job in jobs]


@router.get("/api/projects/{project_id}/production/videos", response_model=list[ProductionVideoAssetRead])
def list_production_videos(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id)
    _membership(db, project_id, user.id)
    assets = db.scalars(select(ProductionVideoAsset).where(
        ProductionVideoAsset.project_id == project_id,
        ProductionVideoAsset.status == "active",
    ).order_by(ProductionVideoAsset.created_at.desc())).all()
    return [_asset_read(asset) for asset in assets]


@router.get("/api/projects/{project_id}/production/videos/{asset_id}/download")
def download_production_video(project_id: uuid.UUID, asset_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id)
    _membership(db, project_id, user.id)
    asset = _asset_or_404(db, project_id, asset_id)
    if asset.status != "active":
        raise HTTPException(status_code=404, detail="Video asset is archived.")
    path = _safe_path(asset.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Video file is missing from storage.")
    return FileResponse(
        path, media_type=asset.content_type,
        filename=asset.original_filename, content_disposition_type="attachment",
    )


@router.get("/api/projects/{project_id}/video-renders/{job_id}/download")
def download_video_render(project_id: uuid.UUID, job_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_or_404(db, project_id)
    _membership(db, project_id, user.id)
    job = _job_or_404(db, project_id, job_id)
    if job.status != "completed" or not job.output_storage_key:
        raise HTTPException(status_code=409, detail="The MP4 export is not ready for download.")
    path = _safe_path(job.output_storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Rendered MP4 file is missing from storage.")
    return FileResponse(
        path, media_type="video/mp4",
        filename=f"storyforge-{job.id}.mp4", content_disposition_type="attachment",
    )
