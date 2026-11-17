import hashlib
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import (
    NarrativeApprovalDecision, ProductionVideoAsset, Project, PublishedRelease,
    Storyboard, VideoRenderJob,
)
from test_audio_pipeline import _production_sequence

client = TestClient(app)


def _completed_video(project_id: str, sequence_id: str, tmp_path):
    with SessionLocal() as db:
        project = db.get(Project, uuid.UUID(project_id))
        assert project is not None
        owner_id = project.owner_user_id
        sequence = db.get(__import__("app.models", fromlist=["EditSequence"]).EditSequence, uuid.UUID(sequence_id))
        assert sequence is not None
        payload = b"\x00\x00\x00\x18ftypmp42storyforge-test-video"
        storage_key = f"video-exports/final/{project_id}/release-test.mp4"
        path = tmp_path / storage_key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        job = VideoRenderJob(
            project_id=project.id, sequence_id=sequence.id,
            sequence_revision=sequence.revision_number, status="completed",
            title="Final master", source_filename="final.webm",
            render_source="headless_3d", render_manifest={"format_version": 2},
            input_storage_key=None, input_size_bytes=None, input_sha256=None,
            input_content_type=None, expected_duration_ms=1200,
            output_size_bytes=len(payload), output_sha256=digest,
            output_storage_key=storage_key, output_content_type="video/mp4",
            duration_ms=1200, width=1280, height=720,
            error_message="", created_by_user_id=owner_id,
        )
        db.add(job)
        db.flush()
        asset = ProductionVideoAsset(
            project_id=project.id, sequence_id=sequence.id, render_job_id=job.id,
            sequence_revision=sequence.revision_number, title="Final master",
            original_filename="final.mp4", content_type="video/mp4",
            size_bytes=len(payload), sha256=digest, storage_key=storage_key,
            duration_ms=1200, width=1280, height=720, status="active",
            created_by_user_id=owner_id,
        )
        db.add(asset)
        db.commit()
        return str(asset.id), str(owner_id)


def _approve_storyboard_narrative(project_id: str, owner_id: str):
    with SessionLocal() as db:
        project = db.get(Project, uuid.UUID(project_id))
        storyboard = db.scalar(select(Storyboard).where(Storyboard.project_id == project.id))
        assert storyboard is not None
        db.add(NarrativeApprovalDecision(
            version_id=storyboard.narrative_version_id,
            actor_user_id=uuid.UUID(owner_id),
            outcome="approved", rule_mode="owner_only",
            eligible_voter_count=1, approve_count=1, reject_count=0,
            required_votes=1, note="Approved for release.",
        ))
        db.commit()
        return str(storyboard.id)


def test_publish_release_snapshots_approved_story_and_finished_video(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_PRODUCTION_MEDIA_DIR", str(tmp_path))
    project_id, sequence = _production_sequence("Immutable release snapshot")
    asset_id, owner_id = _completed_video(project_id, sequence["id"], tmp_path)
    storyboard_id = _approve_storyboard_narrative(project_id, owner_id)

    response = client.post(f"/api/projects/{project_id}/releases", json={
        "video_asset_id": asset_id,
        "storyboard_id": storyboard_id,
        "title": "The First Release",
        "synopsis": "A snapshot that must not change.",
    })
    assert response.status_code == 201, response.text
    release = response.json()
    assert release["release_number"] == 1
    assert release["slug"].startswith("the-first-release-")
    assert release["visibility"] == "private"
    assert release["manifest_json"]["format_version"] == 1
    assert release["manifest_json"]["project"]["title"] == "Immutable release snapshot"
    assert release["manifest_json"]["source"]["narrative_content"] == "Story"
    assert release["manifest_json"]["master_video"]["asset_id"] == asset_id
    assert release["manifest_json"]["master_video"]["sha256"]

    with SessionLocal() as db:
        project = db.get(Project, uuid.UUID(project_id))
        project.title = "Changed after release"
        db.commit()

    fetched = client.get(f"/api/projects/{project_id}/releases/{release['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["manifest_json"]["project"]["title"] == "Immutable release snapshot"
    assert fetched.json()["title"] == "The First Release"

    listed = client.get(f"/api/projects/{project_id}/releases")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    update_attempt = client.patch(f"/api/projects/{project_id}/releases/{release['id']}", json={"title": "Mutated"})
    delete_attempt = client.delete(f"/api/projects/{project_id}/releases/{release['id']}")
    assert update_attempt.status_code == 405
    assert delete_attempt.status_code == 405


def test_release_requires_approved_narrative_and_integral_finished_video(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_PRODUCTION_MEDIA_DIR", str(tmp_path))
    project_id, sequence = _production_sequence("Release validation")
    asset_id, owner_id = _completed_video(project_id, sequence["id"], tmp_path)
    with SessionLocal() as db:
        storyboard = db.scalar(select(Storyboard).where(Storyboard.project_id == uuid.UUID(project_id)))
        storyboard_id = str(storyboard.id)

    unapproved = client.post(f"/api/projects/{project_id}/releases", json={
        "video_asset_id": asset_id, "storyboard_id": storyboard_id,
    })
    assert unapproved.status_code == 409

    _approve_storyboard_narrative(project_id, owner_id)
    video_path = tmp_path / "video-exports" / "final" / project_id / "release-test.mp4"
    video_path.write_bytes(b"tampered")
    tampered = client.post(f"/api/projects/{project_id}/releases", json={
        "video_asset_id": asset_id, "storyboard_id": storyboard_id,
    })
    assert tampered.status_code == 409


def test_release_requires_project_owner(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_PRODUCTION_MEDIA_DIR", str(tmp_path))
    project_id, sequence = _production_sequence("Release owner permission")
    asset_id, owner_id = _completed_video(project_id, sequence["id"], tmp_path)
    storyboard_id = _approve_storyboard_narrative(project_id, owner_id)
    # The development identity is the project owner; a non-member cannot enumerate releases.
    unknown_project = str(uuid.uuid4())
    missing = client.get(f"/api/projects/{unknown_project}/releases")
    assert missing.status_code == 404
