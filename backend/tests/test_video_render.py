import uuid
import json
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import VideoRenderJob
from app.video_render_worker import _probe_video, _run_ffmpeg, process_job
from test_audio_pipeline import _production_sequence

client = TestClient(app)


def test_video_export_upload_queues_private_project_job(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_PRODUCTION_MEDIA_DIR", str(tmp_path))
    project_id, sequence = _production_sequence("Persistent video export")
    response = client.post(
        f"/api/projects/{project_id}/edit-sequences/{sequence['id']}/video-renders",
        data={
            "title": "Final cut",
            "sequence_revision": str(sequence["revision_number"]),
            "expected_duration_ms": "1400",
        },
        files={"file": ("final.webm", b"webm-test-data", "video/webm")},
    )
    assert response.status_code == 202, response.text
    job = response.json()
    assert job["status"] == "queued"
    assert job["input_size_bytes"] == len(b"webm-test-data")
    assert job["download_url"] is None
    incoming = tmp_path / "video-exports" / "incoming" / str(project_id) / f"{job['id']}.webm"
    assert incoming.read_bytes() == b"webm-test-data"

    listed = client.get(f"/api/projects/{project_id}/edit-sequences/{sequence['id']}/video-renders")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == job["id"]

    unavailable = client.get(f"/api/projects/{project_id}/video-renders/{job['id']}/download")
    assert unavailable.status_code == 409


def test_video_export_rejects_stale_revision_and_non_webm(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_PRODUCTION_MEDIA_DIR", str(tmp_path))
    project_id, sequence = _production_sequence("Stale video export")
    url = f"/api/projects/{project_id}/edit-sequences/{sequence['id']}/video-renders"
    stale = client.post(
        url,
        data={"title": "Stale", "sequence_revision": "999", "expected_duration_ms": "1000"},
        files={"file": ("clip.webm", b"webm", "video/webm")},
    )
    assert stale.status_code == 409
    unsupported = client.post(
        url,
        data={
            "title": "Unsupported", "sequence_revision": str(sequence["revision_number"]),
            "expected_duration_ms": "1000",
        },
        files={"file": ("clip.mov", b"mov", "video/quicktime")},
    )
    assert unsupported.status_code == 415


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="FFmpeg tools unavailable")
def test_video_worker_transcodes_webm_to_h264_mp4(tmp_path):
    source = tmp_path / "source.webm"
    generated = subprocess.run(
        [
            shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=320x240:r=24:d=1",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-c:v", "libvpx-vp9", "-c:a", "libopus", "-shortest", str(source),
        ],
        capture_output=True, text=True, check=False,
    )
    assert generated.returncode == 0, generated.stderr
    output = tmp_path / "final.mp4"
    _run_ffmpeg(source, output)
    metadata = _probe_video(output)
    assert metadata["width"] == 320
    assert metadata["height"] == 240
    assert 900 <= metadata["duration_ms"] <= 1100
    probe = subprocess.run(
        [shutil.which("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,pix_fmt", "-of", "json", str(output)],
        capture_output=True, text=True, check=True,
    )
    stream = json.loads(probe.stdout)["streams"][0]
    assert stream["codec_name"] == "h264"
    assert stream["pix_fmt"] == "yuv420p"



@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="FFmpeg tools unavailable")
def test_video_render_worker_persists_mp4_asset_and_authenticated_download(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_PRODUCTION_MEDIA_DIR", str(tmp_path))
    source = tmp_path / "browser-capture.webm"
    generated = subprocess.run(
        [
            shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "color=c=blue:s=320x240:r=24:d=1",
            "-f", "lavfi", "-i", "sine=frequency=660:duration=1",
            "-c:v", "libvpx-vp9", "-c:a", "libopus", "-shortest", str(source),
        ],
        capture_output=True, text=True, check=False,
    )
    assert generated.returncode == 0, generated.stderr

    project_id, sequence = _production_sequence("Server MP4 delivery")
    with source.open("rb") as video_file:
        queued = client.post(
            f"/api/projects/{project_id}/edit-sequences/{sequence['id']}/video-renders",
            data={
                "title": "Server rendered final",
                "sequence_revision": str(sequence["revision_number"]),
                "expected_duration_ms": "1000",
            },
            files={"file": ("browser-capture.webm", video_file, "video/webm")},
        )
    assert queued.status_code == 202, queued.text
    job_data = queued.json()
    with SessionLocal() as db:
        job = db.get(VideoRenderJob, job_data["id"])
        snapshot = {
            "project_id": str(job.project_id), "sequence_id": str(job.sequence_id),
            "sequence_revision": job.sequence_revision, "title": job.title,
            "source_filename": job.source_filename, "input_storage_key": job.input_storage_key,
            "input_sha256": job.input_sha256, "created_by_user_id": str(job.created_by_user_id),
        }

    process_job(uuid.UUID(job_data["id"]), snapshot)

    jobs = client.get(f"/api/projects/{project_id}/edit-sequences/{sequence['id']}/video-renders")
    assert jobs.status_code == 200
    completed = jobs.json()[0]
    assert completed["status"] == "completed", completed
    assert completed["output_sha256"]
    assert completed["output_size_bytes"] > 0
    assert completed["width"] == 320 and completed["height"] == 240
    assert completed["download_url"]

    downloaded = client.get(completed["download_url"])
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"].startswith("video/mp4")
    assert downloaded.content[4:8] == b"ftyp"

    assets = client.get(f"/api/projects/{project_id}/production/videos")
    assert assets.status_code == 200
    assert len(assets.json()) == 1
    assert assets.json()[0]["title"] == "Server rendered final"
    assert assets.json()[0]["sha256"] == completed["output_sha256"]
