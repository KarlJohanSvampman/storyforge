import hashlib
import json
import os
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from .database import SessionLocal
from .models import ProductionVideoAsset, VideoRenderJob


def _media_root() -> Path:
    return Path(os.getenv("STORYFORGE_PRODUCTION_MEDIA_DIR", "/app/storage/production-audio")).resolve()


def _safe_path(storage_key: str) -> Path:
    root = _media_root()
    candidate = (root / storage_key).resolve()
    if root != candidate and root not in candidate.parents:
        raise ValueError("Video render job contains an unsafe storage key.")
    return candidate


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_ffmpeg(input_path: Path, output_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is not installed in the video renderer container.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(output_path.stem + ".part.mp4")
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-i", str(input_path),
        "-map", "0:v:0", "-map", "0:a?",
        "-c:v", "libx264", "-preset", os.getenv("STORYFORGE_VIDEO_PRESET", "medium"),
        "-crf", os.getenv("STORYFORGE_VIDEO_CRF", "20"),
        "-pix_fmt", "yuv420p",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart",
        "-metadata", "title=StoryForge production export",
        str(temporary),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=6 * 60 * 60)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    if result.returncode != 0:
        temporary.unlink(missing_ok=True)
        detail = (result.stderr or result.stdout or "FFmpeg failed without diagnostic output.")[-3500:]
        raise RuntimeError(detail)
    if not temporary.is_file() or temporary.stat().st_size == 0:
        temporary.unlink(missing_ok=True)
        raise RuntimeError("FFmpeg completed without producing an MP4 file.")
    os.replace(temporary, output_path)


def _probe_video(path: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("FFprobe is not installed in the video renderer container.")
    result = subprocess.run(
        [
            ffprobe, "-v", "error", "-show_entries",
            "format=duration:stream=codec_type,width,height",
            "-of", "json", str(path),
        ],
        capture_output=True, text=True, check=False, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "FFprobe could not inspect the rendered MP4.")[-2500:])
    data = json.loads(result.stdout or "{}")
    video_stream = next((stream for stream in data.get("streams", []) if stream.get("codec_type") == "video"), None)
    if not video_stream:
        raise RuntimeError("The rendered file contains no video stream.")
    duration = float(data.get("format", {}).get("duration") or 0)
    width, height = int(video_stream.get("width") or 0), int(video_stream.get("height") or 0)
    if duration <= 0 or width <= 0 or height <= 0:
        raise RuntimeError("The rendered MP4 has invalid duration or dimensions.")
    return {"duration_ms": round(duration * 1000), "width": width, "height": height}


def claim_next_job() -> tuple[uuid.UUID, dict] | None:
    with SessionLocal() as db:
        job = db.scalar(
            select(VideoRenderJob)
            .where(VideoRenderJob.status == "queued")
            .order_by(VideoRenderJob.created_at, VideoRenderJob.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            return None
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        job.error_message = ""
        job_id = job.id
        snapshot = {
            "project_id": str(job.project_id), "sequence_id": str(job.sequence_id),
            "sequence_revision": job.sequence_revision, "title": job.title,
            "source_filename": job.source_filename, "input_storage_key": job.input_storage_key,
            "input_sha256": job.input_sha256, "created_by_user_id": str(job.created_by_user_id),
        }
        db.commit()
        return job_id, snapshot


def process_job(job_id: uuid.UUID, snapshot: dict) -> None:
    input_path = _safe_path(snapshot["input_storage_key"])
    output_key = f"video-exports/final/{snapshot['project_id']}/{job_id}.mp4"
    output_path = _safe_path(output_key)
    try:
        if not input_path.is_file():
            raise RuntimeError("Uploaded WebM source is missing from shared storage.")
        if _sha256(input_path) != snapshot["input_sha256"]:
            raise RuntimeError("Uploaded WebM source failed its SHA-256 integrity check.")
        _run_ffmpeg(input_path, output_path)
        metadata = _probe_video(output_path)
        size = output_path.stat().st_size
        digest = _sha256(output_path)
        with SessionLocal() as db:
            job = db.get(VideoRenderJob, job_id)
            if job is None:
                output_path.unlink(missing_ok=True)
                return
            asset = ProductionVideoAsset(
                project_id=job.project_id, sequence_id=job.sequence_id,
                render_job_id=job.id, sequence_revision=job.sequence_revision,
                title=job.title, original_filename=f"storyforge-{job.id}.mp4",
                content_type="video/mp4", size_bytes=size, sha256=digest,
                storage_key=output_key, duration_ms=metadata["duration_ms"],
                width=metadata["width"], height=metadata["height"],
                created_by_user_id=job.created_by_user_id,
            )
            db.add(asset)
            job.status = "completed"
            job.output_size_bytes = size
            job.output_sha256 = digest
            job.output_storage_key = output_key
            job.output_content_type = "video/mp4"
            job.duration_ms = metadata["duration_ms"]
            job.width = metadata["width"]
            job.height = metadata["height"]
            job.error_message = ""
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
        input_path.unlink(missing_ok=True)
    except Exception as error:
        output_path.unlink(missing_ok=True)
        with SessionLocal() as db:
            job = db.get(VideoRenderJob, job_id)
            if job is not None:
                job.status = "failed"
                job.error_message = str(error)[-4000:]
                job.completed_at = datetime.now(timezone.utc)
                db.commit()


def recover_stale_jobs(stale_after_hours: int = 12) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=stale_after_hours)
    recovered = 0
    with SessionLocal() as db:
        stale = db.scalars(
            select(VideoRenderJob)
            .where(VideoRenderJob.status == "running", VideoRenderJob.started_at < cutoff)
            .with_for_update(skip_locked=True)
        ).all()
        for job in stale:
            if _safe_path(job.input_storage_key).is_file():
                job.status = "queued"
                job.started_at = None
                job.error_message = "Render was re-queued after an interrupted worker process."
            else:
                job.status = "failed"
                job.error_message = "Render worker stopped and the uploaded source is missing."
                job.completed_at = datetime.now(timezone.utc)
            recovered += 1
        db.commit()
    return recovered


def run_worker(poll_seconds: float = 2.0) -> None:
    recovered = recover_stale_jobs()
    print(f"StoryForge video renderer started. Re-queued or failed {recovered} interrupted jobs.", flush=True)
    while True:
        claimed = claim_next_job()
        if claimed is None:
            time.sleep(poll_seconds)
            continue
        job_id, snapshot = claimed
        print(f"Encoding video job {job_id}.", flush=True)
        process_job(job_id, snapshot)
        print(f"Finished video job {job_id}.", flush=True)


if __name__ == "__main__":
    run_worker()
