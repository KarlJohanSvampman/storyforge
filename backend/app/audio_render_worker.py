import hashlib
import os
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from .database import SessionLocal
from .models import AudioRenderJob


def _media_root() -> Path:
    return Path(os.getenv("STORYFORGE_PRODUCTION_MEDIA_DIR", "/app/storage/production-audio")).resolve()


def _safe_storage_path(storage_key: str) -> Path:
    root = _media_root()
    candidate = (root / storage_key).resolve()
    if root != candidate and root not in candidate.parents:
        raise ValueError("Audio render manifest contains an unsafe storage key.")
    return candidate


def _seconds(milliseconds: int | float) -> str:
    return f"{float(milliseconds) / 1000:.6f}"


def _render_command(manifest: dict[str, Any], output_path: Path) -> list[str]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is not installed in the audio renderer container.")
    clips: list[dict[str, Any]] = []
    for track in manifest.get("tracks", []):
        track_gain = float(track.get("gain", 1.0))
        track_pan = max(-1.0, min(1.0, float(track.get("pan", 0.0))))
        for clip in track.get("clips", []):
            clips.append({
                **clip,
                "track_gain": track_gain,
                "track_pan": track_pan,
            })
    if not clips:
        raise RuntimeError("The render snapshot contains no audible clips.")

    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y"]
    filters = []
    labels = []
    for index, clip in enumerate(clips):
        source_path = _safe_storage_path(str(clip["storage_key"]))
        if not source_path.is_file():
            raise RuntimeError(f'Audio source "{clip.get("filename", clip["media_asset_id"])}" is missing.')
        expected_hash = clip.get("sha256")
        if expected_hash:
            digest = hashlib.sha256()
            with source_path.open("rb") as source_file:
                for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != expected_hash:
                raise RuntimeError(f'Audio source "{clip.get("filename", clip["media_asset_id"])}" failed its SHA-256 integrity check.')
        command.extend(["-i", str(source_path)])
        source_in = int(clip["source_in_ms"])
        source_out = int(clip["source_out_ms"])
        duration_ms = source_out - source_in
        if source_in < 0 or duration_ms <= 0:
            raise RuntimeError("The render snapshot contains an invalid audio source range.")
        fade_in = int(clip.get("fade_in_ms", 0))
        fade_out = int(clip.get("fade_out_ms", 0))
        if fade_in < 0 or fade_out < 0 or fade_in + fade_out > duration_ms:
            raise RuntimeError("The render snapshot contains invalid fade durations.")
        timeline_start = int(clip.get("timeline_start_ms", 0))
        if timeline_start < 0:
            raise RuntimeError("The render snapshot contains a negative timeline offset.")

        gain = float(clip.get("gain", 1.0)) * float(clip["track_gain"])
        pan = float(clip["track_pan"])
        left_gain = 1.0 - max(0.0, pan)
        right_gain = 1.0 + min(0.0, pan)
        chain = [
            f"atrim=start={_seconds(source_in)}:duration={_seconds(duration_ms)}",
            "asetpts=PTS-STARTPTS",
            "aformat=sample_fmts=fltp:channel_layouts=stereo",
            f"volume={gain:.6f}",
            f"pan=stereo|c0=c0*{left_gain:.6f}|c1=c1*{right_gain:.6f}",
        ]
        if fade_in:
            chain.append(f"afade=t=in:st=0:d={_seconds(fade_in)}")
        if fade_out:
            chain.append(
                f"afade=t=out:st={_seconds(duration_ms - fade_out)}:d={_seconds(fade_out)}"
            )
        if timeline_start:
            chain.append(f"adelay={timeline_start}|{timeline_start}")
        label = f"clip{index}"
        filters.append(f"[{index}:a]{','.join(chain)}[{label}]")
        labels.append(f"[{label}]")

    total_duration = int(manifest["duration_ms"])
    if total_duration <= 0:
        raise RuntimeError("The render snapshot has no positive timeline duration.")
    mix = (
        "".join(labels)
        + f"amix=inputs={len(labels)}:duration=longest:dropout_transition=0:normalize=0,"
        + f"apad=whole_dur={_seconds(total_duration)},"
        + f"atrim=duration={_seconds(total_duration)},"
        + "alimiter=limit=0.98:level=false,asetpts=PTS-STARTPTS[out]"
    )
    filters.append(mix)
    command.extend([
        "-filter_complex", ";".join(filters),
        "-map", "[out]",
        "-ar", str(int(manifest.get("sample_rate", 48000))),
        "-ac", str(int(manifest.get("channels", 2))),
        "-c:a", "pcm_s24le",
        "-metadata", "title=StoryForge audio mix",
        str(output_path),
    ])
    return command


def render_audio_manifest(manifest: dict[str, Any], output_path: Path) -> tuple[int, str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".part.wav")
    command = _render_command(manifest, temporary)
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=False, timeout=4 * 60 * 60,
        )
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    if result.returncode != 0:
        temporary.unlink(missing_ok=True)
        detail = (result.stderr or result.stdout or "FFmpeg failed without diagnostic output.")[-3500:]
        raise RuntimeError(detail)
    if not temporary.is_file() or temporary.stat().st_size == 0:
        temporary.unlink(missing_ok=True)
        raise RuntimeError("FFmpeg completed without producing an audio file.")
    os.replace(temporary, output_path)
    digest = hashlib.sha256()
    with output_path.open("rb") as rendered:
        for chunk in iter(lambda: rendered.read(1024 * 1024), b""):
            digest.update(chunk)
    return output_path.stat().st_size, digest.hexdigest()


def claim_next_job() -> tuple[uuid.UUID, dict[str, Any]] | None:
    with SessionLocal() as db:
        job = db.scalar(
            select(AudioRenderJob)
            .where(AudioRenderJob.status == "queued")
            .order_by(AudioRenderJob.created_at, AudioRenderJob.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            return None
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        job.error_message = ""
        job_id = job.id
        manifest = dict(job.render_manifest)
        db.commit()
        return job_id, manifest


def process_job(job_id: uuid.UUID, manifest: dict[str, Any]) -> None:
    storage_key = f"renders/{manifest['project_id']}/{job_id}.wav"
    output_path = _safe_storage_path(storage_key)
    try:
        size, digest = render_audio_manifest(manifest, output_path)
        with SessionLocal() as db:
            job = db.get(AudioRenderJob, job_id)
            if job is None:
                output_path.unlink(missing_ok=True)
                return
            job.status = "completed"
            job.output_storage_key = storage_key
            job.output_content_type = "audio/wav"
            job.output_size_bytes = size
            job.output_sha256 = digest
            job.duration_ms = int(manifest["duration_ms"])
            job.error_message = ""
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    except Exception as error:
        output_path.unlink(missing_ok=True)
        with SessionLocal() as db:
            job = db.get(AudioRenderJob, job_id)
            if job is not None:
                job.status = "failed"
                job.error_message = str(error)[-4000:]
                job.completed_at = datetime.now(timezone.utc)
                db.commit()


def recover_stale_jobs(stale_after_hours: int = 12) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=stale_after_hours)
    with SessionLocal() as db:
        stale = db.scalars(
            select(AudioRenderJob)
            .where(AudioRenderJob.status == "running", AudioRenderJob.started_at < cutoff)
            .with_for_update(skip_locked=True)
        ).all()
        for job in stale:
            job.status = "queued"
            job.started_at = None
            job.error_message = "Render was re-queued after an interrupted worker process."
        db.commit()
        return len(stale)


def run_worker(poll_seconds: float = 2.0) -> None:
    recovered = recover_stale_jobs()
    print(f"StoryForge audio renderer started. Re-queued {recovered} interrupted jobs.", flush=True)
    while True:
        claimed = claim_next_job()
        if claimed is None:
            time.sleep(poll_seconds)
            continue
        job_id, manifest = claimed
        print(f"Rendering audio job {job_id}.", flush=True)
        process_job(job_id, manifest)
        print(f"Finished audio job {job_id}.", flush=True)


if __name__ == "__main__":
    run_worker()
