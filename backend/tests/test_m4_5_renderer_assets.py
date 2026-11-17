import json
import struct
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import CastMemberInstance, SceneRun, VideoRenderJob
from test_audio_pipeline import _production_sequence

client = TestClient(app)


def _glb():
    document = json.dumps({
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": []}],
        "nodes": [],
    }).encode()
    document += b" " * ((4 - len(document) % 4) % 4)
    total = 12 + 8 + len(document)
    return b"glTF" + struct.pack("<II", 2, total) + struct.pack("<II", len(document), 0x4E4F534A) + document


def test_headless_3d_manifest_snapshots_assigned_asset_version_and_transform(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_ASSET_DIR", str(tmp_path))
    project_id, sequence = _production_sequence("M4.5 renderer asset snapshot")
    sequence_detail = client.get(f"/api/projects/{project_id}/edit-sequences/{sequence['id']}")
    assert sequence_detail.status_code == 200, sequence_detail.text
    scene_id = sequence_detail.json()["items"][0]["scene_id"]

    with SessionLocal() as db:
        run = db.scalar(select(SceneRun).where(SceneRun.scene_id == uuid.UUID(scene_id)))
        assert run is not None
        member = db.scalar(select(CastMemberInstance).where(CastMemberInstance.scene_run_id == run.id))
        assert member is not None
        character_id = str(member.character_id)

    asset_response = client.post(
        f"/api/projects/{project_id}/production-assets",
        data={"name": "Lead mesh", "asset_kind": "character", "target_id": character_id},
        files={"file": ("lead.glb", _glb(), "model/gltf-binary")},
    )
    assert asset_response.status_code == 201, asset_response.text
    asset = asset_response.json()

    bindings = client.get(f"/api/projects/{project_id}/production-assets/bindings")
    binding = next(row for row in bindings.json() if row["asset_id"] == asset["id"])
    placement = {"position": [2, 0.25, -1], "rotation": [0, 1.2, 0], "scale": [1.5, 1.5, 1.5]}
    updated = client.patch(
        f"/api/projects/{project_id}/production-assets/bindings/{binding['id']}/transform",
        json=placement,
    )
    assert updated.status_code == 200, updated.text

    queued = client.post(
        f"/api/projects/{project_id}/edit-sequences/{sequence['id']}/scene-renders?renderer=3d",
    )
    assert queued.status_code == 202, queued.text
    with SessionLocal() as db:
        job = db.get(VideoRenderJob, uuid.UUID(queued.json()["id"]))
        assert job is not None
        manifest = job.render_manifest

    assert manifest["format_version"] == 2
    assert manifest["asset_snapshot_version"] == 1
    clip_assets = manifest["clips"][0]["production_assets"]
    assert len(clip_assets) == 1
    snapshot = clip_assets[0]
    assert snapshot["asset_id"] == asset["id"]
    assert snapshot["version"] == asset["version"]
    assert snapshot["sha256"] == asset["sha256"]
    assert snapshot["storage_key"] == f"{project_id}/{asset['id']}.glb"
    assert snapshot["transform"] == placement
    assert snapshot["render_url"].endswith(f"/{asset['id']}.glb")
