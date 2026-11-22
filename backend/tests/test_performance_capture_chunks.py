import json
import uuid

from fastapi.testclient import TestClient

from app.main import app
from test_scene_runtime import _scene_with_casting


client = TestClient(app)


def test_chunked_body_capture_upload_list_and_replay(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_CAPTURE_DIR", str(tmp_path))
    client, project_id, scene_id, _, _ = _scene_with_casting("Chunked body capture")
    run_response = client.post(f"/api/projects/{project_id}/scene-runs", json={"scene_id": scene_id})
    assert run_response.status_code == 201, run_response.text
    run = run_response.json()
    cast_member_id = run["cast_members"][0]["id"]

    take_response = client.post(
        f"/api/projects/{project_id}/scene-runs/{run['id']}/takes",
        json={"title": "Quest body pass", "cast_member_instance_id": cast_member_id},
    )
    assert take_response.status_code == 201, take_response.text
    take_id = take_response.json()["id"]

    samples = [
        {
            "timestamp_ms": index * 33,
            "head": {"x": index / 100, "y": 1.7, "z": 0.0},
            "head_orientation": {"x": 0, "y": 0, "z": 0, "w": 1},
            "left_wrist": None,
            "right_wrist": {"x": 0.3, "y": 1.2, "z": -0.2},
        }
        for index in range(60)
    ]
    first = client.post(
        f"/api/projects/{project_id}/takes/{take_id}/capture-chunks",
        json={"chunk_index": 0, "samples": samples},
    )
    assert first.status_code == 201, first.text
    chunk = first.json()
    assert chunk["sample_count"] == 60
    assert chunk["start_timestamp_ms"] == 0
    assert chunk["end_timestamp_ms"] == 1947
    assert chunk["size_bytes"] < len(json.dumps(samples).encode())

    wrong_index = client.post(
        f"/api/projects/{project_id}/takes/{take_id}/capture-chunks",
        json={"chunk_index": 2, "samples": [{"timestamp_ms": 2000}]},
    )
    assert wrong_index.status_code == 409

    backwards = client.post(
        f"/api/projects/{project_id}/takes/{take_id}/capture-chunks",
        json={"chunk_index": 1, "samples": [{"timestamp_ms": 1949}]},
    )
    assert backwards.status_code == 422

    second = client.post(
        f"/api/projects/{project_id}/takes/{take_id}/capture-chunks",
        json={"chunk_index": 1, "samples": [{"timestamp_ms": 1983, "head": None}]},
    )
    assert second.status_code == 201, second.text

    chunks = client.get(f"/api/projects/{project_id}/takes/{take_id}/capture-chunks")
    assert chunks.status_code == 200
    assert [item["chunk_index"] for item in chunks.json()] == [0, 1]

    replay = client.get(chunk["download_url"])
    assert replay.status_code == 200
    assert len(replay.json()["samples"]) == 60
    assert replay.json()["samples"][10]["head"]["x"] == 0.1

    take_list = client.get(f"/api/projects/{project_id}/capture-takes")
    assert take_list.status_code == 200
    assert take_list.json()[0]["sample_count"] == 61
    assert take_list.json()[0]["id"] == take_id

    finalized = client.post(
        f"/api/projects/{project_id}/takes/{take_id}/finalize",
        json={"duration_ms": 2000},
    )
    assert finalized.status_code == 200
    blocked = client.post(
        f"/api/projects/{project_id}/takes/{take_id}/capture-chunks",
        json={"chunk_index": 2, "samples": [{"timestamp_ms": 2001}]},
    )
    assert blocked.status_code == 409


def test_chunked_capture_rejects_invalid_samples_and_cross_project_access(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_CAPTURE_DIR", str(tmp_path))
    client, project_id, scene_id, _, _ = _scene_with_casting("Capture sample validation")
    run = client.post(f"/api/projects/{project_id}/scene-runs", json={"scene_id": scene_id}).json()
    take = client.post(f"/api/projects/{project_id}/scene-runs/{run['id']}/takes", json={}).json()

    invalid = client.post(
        f"/api/projects/{project_id}/takes/{take['id']}/capture-chunks",
        data='{"chunk_index":0,"samples":[{"timestamp_ms":0,"head":{"x":NaN,"y":1,"z":0}}]}',
        headers={"Content-Type": "application/json"},
    )
    assert invalid.status_code == 422

    other_project = str(uuid.uuid4())
    denied = client.get(f"/api/projects/{other_project}/takes/{take['id']}/capture-chunks")
    assert denied.status_code == 404
