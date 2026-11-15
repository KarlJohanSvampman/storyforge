import uuid

from fastapi.testclient import TestClient

from app.main import app
from tests.test_scene_runtime import _scene_with_casting


def test_performance_take_records_ordered_replayable_events() -> None:
    client, project_id, scene_id, _, _ = _scene_with_casting("Performance take integration")
    run_response = client.post(f"/api/projects/{project_id}/scene-runs", json={"scene_id": scene_id})
    assert run_response.status_code == 201
    run = run_response.json()
    cast_member_id = run["cast_members"][0]["id"]

    take_response = client.post(
        f"/api/projects/{project_id}/scene-runs/{run['id']}/takes",
        json={
            "title": "Opening performance",
            "cast_member_instance_id": cast_member_id,
            "camera_snapshot": {"position": [0, 1.6, 4], "fov": 50},
        },
    )
    assert take_response.status_code == 201, take_response.text
    take = take_response.json()
    assert take["status"] == "recording"
    assert take["take_number"] == 1

    events = client.post(
        f"/api/projects/{project_id}/takes/{take['id']}/events",
        json=[
            {"sequence_number": 0, "timestamp_ms": 0, "event_type": "transform", "payload": {"position": [0, 0, 0]}},
            {"sequence_number": 1, "timestamp_ms": 120, "event_type": "gesture", "payload": {"name": "wave", "weight": 0.8}},
            {"sequence_number": 2, "timestamp_ms": 240, "event_type": "camera", "payload": {"position": [1, 1.6, 4]}},
        ],
    )
    assert events.status_code == 200, events.text
    assert [item["sequence_number"] for item in events.json()["events"]] == [0, 1, 2]

    finalized = client.post(
        f"/api/projects/{project_id}/takes/{take['id']}/finalize",
        json={"duration_ms": 300},
    )
    assert finalized.status_code == 200
    assert finalized.json()["status"] == "finalized"
    assert finalized.json()["duration_ms"] == 300

    replay = client.get(f"/api/projects/{project_id}/takes/{take['id']}")
    assert replay.status_code == 200
    assert len(replay.json()["events"]) == 3


def test_performance_event_sequence_and_finalized_immutability() -> None:
    client, project_id, scene_id, _, _ = _scene_with_casting("Performance event validation")
    run = client.post(f"/api/projects/{project_id}/scene-runs", json={"scene_id": scene_id}).json()
    take = client.post(f"/api/projects/{project_id}/scene-runs/{run['id']}/takes", json={}).json()

    bad_sequence = client.post(
        f"/api/projects/{project_id}/takes/{take['id']}/events",
        json=[{"sequence_number": 1, "timestamp_ms": 0, "event_type": "cue", "payload": {}}],
    )
    assert bad_sequence.status_code == 409

    finalized = client.post(f"/api/projects/{project_id}/takes/{take['id']}/finalize", json={"duration_ms": 0})
    assert finalized.status_code == 200
    after = client.post(
        f"/api/projects/{project_id}/takes/{take['id']}/events",
        json=[{"sequence_number": 0, "timestamp_ms": 0, "event_type": "cue", "payload": {}}],
    )
    assert after.status_code == 409
