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


def _sample_rig_profile():
    return {
        "id": "custom-humanoid-v1",
        "label": "Custom humanoid",
        "bindings": [
            {"bone": "Spine", "start": "pelvis", "end": "spine"},
            {"bone": "Chest", "start": "spine", "end": "chest"},
            {"bone": "Neck", "start": "chest", "end": "neck"},
            {"bone": "Head", "start": "neck", "end": "head"},
        ],
        "fitCanonicalHeight": True,
    }


def test_character_rig_profile_is_shared_versioned_and_asset_scoped(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_ASSET_DIR", str(tmp_path))
    project_id, _ = _production_sequence("Persistent rig profiles")
    character_id = _character(project_id)
    url = f"/api/projects/{project_id}/production-assets"
    uploaded = client.post(url, data={
        "name": "Lead character", "asset_kind": "character", "target_id": character_id,
    }, files={"file": ("lead.glb", _glb(), "model/gltf-binary")})
    assert uploaded.status_code == 201, uploaded.text
    asset = uploaded.json()
    profile_url = url + f"/{asset['id']}/rig-profile"

    assert client.get(profile_url).json() is None
    saved = client.put(profile_url, json={
        "profile": _sample_rig_profile(), "expected_revision": 0,
        "rig_signature": "sha256:fixture",
    })
    assert saved.status_code == 200, saved.text
    first = saved.json()
    assert first["revision"] == 1
    assert first["asset_version"] == 1
    assert first["profile"]["bindings"][0]["bone"] == "Spine"

    changed_profile = _sample_rig_profile()
    changed_profile["label"] = "Adjusted humanoid"
    updated = client.put(profile_url, json={
        "profile": changed_profile, "expected_revision": 1,
        "rig_signature": "sha256:fixture",
    })
    assert updated.status_code == 200, updated.text
    assert updated.json()["revision"] == 2
    assert updated.json()["profile"]["label"] == "Adjusted humanoid"

    stale = client.put(profile_url, json={
        "profile": _sample_rig_profile(), "expected_revision": 1,
    })
    assert stale.status_code == 409

    history = client.get(profile_url + "/versions")
    assert history.status_code == 200
    assert [row["revision"] for row in history.json()] == [2, 1]

    # A new immutable character asset version gets its own independent profile history.
    next_asset = client.post(url, data={
        "name": "Lead character", "asset_kind": "character", "target_id": character_id,
    }, files={"file": ("lead-v2.glb", _glb(), "model/gltf-binary")})
    assert next_asset.status_code == 201
    assert next_asset.json()["version"] == 2
    assert client.get(url + f"/{next_asset.json()['id']}/rig-profile").json() is None


def test_character_rig_profile_rejects_invalid_or_non_character_profiles(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_ASSET_DIR", str(tmp_path))
    project_id, _ = _production_sequence("Rig profile validation")
    character_id = _character(project_id)
    url = f"/api/projects/{project_id}/production-assets"
    uploaded = client.post(url, data={
        "name": "Lead character", "asset_kind": "character", "target_id": character_id,
    }, files={"file": ("lead.glb", _glb(), "model/gltf-binary")})
    asset_id = uploaded.json()["id"]
    profile_url = url + f"/{asset_id}/rig-profile"

    duplicate_bone = _sample_rig_profile()
    duplicate_bone["bindings"][1]["bone"] = "Spine"
    rejected = client.put(profile_url, json={"profile": duplicate_bone, "expected_revision": 0})
    assert rejected.status_code == 422

    prop = client.post(url, data={"name": "Prop", "asset_kind": "prop"},
        files={"file": ("prop.glb", _glb(), "model/gltf-binary")})
    assert prop.status_code == 201
    rejected_prop = client.get(url + f"/{prop.json()['id']}/rig-profile")
    assert rejected_prop.status_code == 422
