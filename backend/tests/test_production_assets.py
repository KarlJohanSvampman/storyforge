import json
import struct
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Project, ProjectCharacter
from test_audio_pipeline import _production_sequence

client = TestClient(app)


def _glb():
    document = json.dumps({"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": []}], "nodes": []}).encode()
    document += b" " * ((4 - len(document) % 4) % 4)
    total = 12 + 8 + len(document)
    return b"glTF" + struct.pack("<II", 2, total) + struct.pack("<II", len(document), 0x4E4F534A) + document


def _character(project_id):
    db = SessionLocal()
    try:
        project = db.get(Project, uuid.UUID(project_id))
        character = ProjectCharacter(
            project_id=project.id, name="Lead",
            created_by_user_id=project.owner_user_id,
        )
        db.add(character)
        db.commit()
        db.refresh(character)
        return str(character.id)
    finally:
        db.close()


def test_upload_list_download_and_version_character_asset(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_ASSET_DIR", str(tmp_path))
    project_id, _ = _production_sequence("Asset library")
    character_id = _character(project_id)
    url = f"/api/projects/{project_id}/production-assets"
    first = client.post(url, data={
        "name": "Lead character", "asset_kind": "character", "target_id": character_id,
    }, files={"file": ("lead.glb", _glb(), "model/gltf-binary")})
    assert first.status_code == 201, first.text
    asset = first.json()
    assert asset["version"] == 1
    assert asset["metadata_json"]["node_count"] == 0
    assert (tmp_path / f"{project_id}" / f"{asset['id']}.glb").is_file()

    bindings = client.get(url + "/bindings")
    assert bindings.status_code == 200
    assert bindings.json()[0]["asset"]["id"] == asset["id"]

    downloaded = client.get(url + f"/{asset['id']}/download")
    assert downloaded.status_code == 200
    assert downloaded.content == _glb()

    second = client.post(url, data={
        "name": "Lead character", "asset_kind": "character", "target_id": character_id,
    }, files={"file": ("lead-v2.glb", _glb(), "model/gltf-binary")})
    assert second.status_code == 201, second.text
    assert second.json()["version"] == 2
    assert client.get(url + "/bindings").json()[0]["asset"]["id"] == second.json()["id"]
    assert client.get(url + f"/{asset['id']}").status_code == 200


def test_asset_upload_rejects_external_gltf_and_wrong_target(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_ASSET_DIR", str(tmp_path))
    project_id, _ = _production_sequence("Asset validation")
    url = f"/api/projects/{project_id}/production-assets"
    external = json.dumps({
        "asset": {"version": "2.0"},
        "buffers": [{"uri": "https://example.invalid/model.bin", "byteLength": 4}],
    }).encode()
    rejected = client.post(url, data={
        "name": "Remote model", "asset_kind": "prop",
    }, files={"file": ("remote.gltf", external, "model/gltf+json")})
    assert rejected.status_code == 422
    wrong_target = client.post(url, data={
        "name": "Wrong character", "asset_kind": "character", "target_id": str(uuid.uuid4()),
    }, files={"file": ("lead.glb", _glb(), "model/gltf-binary")})
    assert wrong_target.status_code == 404


def test_asset_upload_rejects_invalid_glb(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_ASSET_DIR", str(tmp_path))
    project_id, _ = _production_sequence("Invalid GLB")
    response = client.post(
        f"/api/projects/{project_id}/production-assets",
        data={"name": "Bad", "asset_kind": "prop"},
        files={"file": ("bad.glb", b"not a glb", "model/gltf-binary")},
    )
    assert response.status_code == 415


def test_asset_binding_transform_is_validated_and_persisted(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_ASSET_DIR", str(tmp_path))
    project_id, _ = _production_sequence("Asset placement transform")
    character_id = _character(project_id)
    url = f"/api/projects/{project_id}/production-assets"
    uploaded = client.post(url, data={
        "name": "Placed lead", "asset_kind": "character", "target_id": character_id,
    }, files={"file": ("lead.glb", _glb(), "model/gltf-binary")})
    assert uploaded.status_code == 201, uploaded.text

    bindings = client.get(url + "/bindings")
    assert bindings.status_code == 200
    binding = bindings.json()[0]
    assert binding["transform_json"] == {
        "position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1],
    }

    changed = client.patch(url + f"/bindings/{binding['id']}/transform", json={
        "position": [1.25, 0.5, -2], "rotation": [0, 1.570796, 0], "scale": [1.5, 1.5, 1.5],
    })
    assert changed.status_code == 200, changed.text
    assert changed.json()["transform_json"] == {
        "position": [1.25, 0.5, -2],
        "rotation": [0, 1.570796, 0],
        "scale": [1.5, 1.5, 1.5],
    }

    invalid = client.patch(url + f"/bindings/{binding['id']}/transform", json={"scale": [1, 0, 1]})
    assert invalid.status_code == 422
