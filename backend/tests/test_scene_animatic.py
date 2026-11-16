import json
import shutil
import subprocess
import uuid

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageChops

from app.database import SessionLocal
from app.main import app
from app.models import VideoRenderJob
from app.scene_animatic import render_manifest_frames, render_clip_frame, render_timeline_frame
from app.video_render_worker import _probe_video, process_job
from test_audio_pipeline import _production_sequence

client = TestClient(app)


def _manifest():
    member = {"id": "cast-1", "character_name": "Mara", "actor_name": "Actor"}
    return {
        "format_version": 1, "renderer": "storyforge-headless-animatic-v1",
        "project_id": "project-1", "sequence_id": "sequence-1", "sequence_revision": 4,
        "width": 640, "height": 360, "fps": 12, "duration_ms": 1500,
        "clips": [
            {
                "item_id": "item-1", "scene_id": "scene-1", "scene_title": "The arrival",
                "in_ms": 0, "out_ms": 1000, "duration_ms": 1000, "transition": "cut",
                "transition_duration_ms": 0, "title_overlay": "A new beginning",
                "cast_members": [member],
                "events": [
                    {"timestamp_ms": 0, "event_type": "transform", "cast_member_instance_id": "cast-1",
                     "payload": {"position": [-2, 0, 0]}},
                    {"timestamp_ms": 900, "event_type": "transform", "cast_member_instance_id": "cast-1",
                     "payload": {"position": [2, 0, 0]}},
                ],
            },
            {
                "item_id": "item-2", "scene_id": "scene-2", "scene_title": "The departure",
                "in_ms": 0, "out_ms": 1000, "duration_ms": 1000, "transition": "dissolve",
                "transition_duration_ms": 500, "title_overlay": "",
                "cast_members": [{"id": "cast-2", "character_name": "Jon", "actor_name": "Actor"}],
                "events": [],
            },
        ],
    }


def test_headless_animatic_reconstructs_transforms_and_cross_dissolves(tmp_path):
    manifest = _manifest()
    first = render_clip_frame(manifest["clips"][0], 0, 640, 360)
    last = render_clip_frame(manifest["clips"][0], 900, 640, 360)
    assert ImageChops.difference(first, last).getbbox() is not None
    first.close()
    last.close()

    count = render_manifest_frames(manifest, tmp_path / "frames")
    assert count == 18
    assert len(list((tmp_path / "frames").glob("frame-*.jpg"))) == count


def test_headless_animatic_rejects_unsafe_frame_budget(tmp_path):
    manifest = _manifest()
    manifest["width"] = 4096
    with pytest.raises(ValueError, match="unsupported dimensions"):
        render_manifest_frames(manifest, tmp_path / "frames")


def test_scene_render_endpoint_snapshots_selected_take_and_revision(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_PRODUCTION_MEDIA_DIR", str(tmp_path))
    project_id, sequence = _production_sequence("Headless scene render")
    sequence = client.get(f"/api/projects/{project_id}/edit-sequences/{sequence['id']}").json()
    response = client.post(
        f"/api/projects/{project_id}/edit-sequences/{sequence['id']}/scene-renders"
    )
    assert response.status_code == 202, response.text
    job = response.json()
    assert job["status"] == "queued"
    assert job["render_source"] == "headless_animatic"
    assert job["input_size_bytes"] is None

    with SessionLocal() as db:
        stored = db.get(VideoRenderJob, job["id"])
        manifest = stored.render_manifest
        assert manifest["sequence_revision"] == sequence["revision_number"]
        assert manifest["clips"][0]["scene_title"]
        assert manifest["clips"][0]["cast_members"]
        assert [event["event_type"] for event in manifest["clips"][0]["events"]] == ["cue", "camera"]
        assert manifest["clips"][0]["events"][1]["payload"]["preset"] == "close"
        snapshot = {
            "project_id": str(stored.project_id), "sequence_id": str(stored.sequence_id),
            "sequence_revision": stored.sequence_revision, "title": stored.title,
            "source_filename": stored.source_filename, "render_source": stored.render_source,
            "render_manifest": stored.render_manifest, "input_storage_key": stored.input_storage_key,
            "input_sha256": stored.input_sha256, "created_by_user_id": str(stored.created_by_user_id),
        }

    assert snapshot["render_manifest"]["renderer"] == "storyforge-headless-animatic-v1"


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="FFmpeg tools unavailable")
def test_headless_scene_job_renders_mp4_and_persists_asset(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_PRODUCTION_MEDIA_DIR", str(tmp_path))
    project_id, sequence = _production_sequence("Headless scene MP4")
    sequence = client.get(f"/api/projects/{project_id}/edit-sequences/{sequence['id']}").json()
    queued = client.post(
        f"/api/projects/{project_id}/edit-sequences/{sequence['id']}/scene-renders"
    )
    assert queued.status_code == 202, queued.text
    job_id = uuid.UUID(queued.json()["id"])
    with SessionLocal() as db:
        stored = db.get(VideoRenderJob, job_id)
        manifest = stored.render_manifest
        manifest["width"] = 640
        manifest["height"] = 360
        manifest["fps"] = 12
        stored.render_manifest = manifest
        db.commit()
        snapshot = {
            "project_id": str(stored.project_id), "sequence_id": str(stored.sequence_id),
            "sequence_revision": stored.sequence_revision, "title": stored.title,
            "source_filename": stored.source_filename, "render_source": stored.render_source,
            "render_manifest": stored.render_manifest, "input_storage_key": stored.input_storage_key,
            "input_sha256": stored.input_sha256, "created_by_user_id": str(stored.created_by_user_id),
        }

    process_job(job_id, snapshot)
    jobs = client.get(f"/api/projects/{project_id}/edit-sequences/{sequence['id']}/video-renders")
    completed = next(item for item in jobs.json() if item["id"] == str(job_id))
    assert completed["status"] == "completed", completed
    assert completed["render_source"] == "headless_animatic"
    assert completed["output_size_bytes"] > 0
    assert completed["width"] == 640 and completed["height"] == 360
    downloaded = client.get(completed["download_url"])
    assert downloaded.status_code == 200
    assert downloaded.content[4:8] == b"ftyp"

def test_headless_timeline_composites_the_incoming_clip_transition():
    manifest = _manifest()
    clips = manifest["clips"]
    starts = [0, 500]

    outgoing = render_clip_frame(clips[0], 750, 640, 360)
    incoming = render_clip_frame(clips[1], 250, 640, 360)
    actual = render_timeline_frame(clips, starts, 750, 640, 360)
    expected = Image.blend(outgoing, incoming, 0.5)
    assert ImageChops.difference(actual, expected).getbbox() is None
    outgoing.close()
    incoming.close()
    actual.close()
    expected.close()

    clips[1]["transition"] = "fade"
    midpoint = render_timeline_frame(clips, starts, 750, 640, 360)
    assert midpoint.getpixel((320, 180)) == (0, 0, 0)
    midpoint.close()

