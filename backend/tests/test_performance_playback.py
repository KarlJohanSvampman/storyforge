from fastapi.testclient import TestClient

from app.main import app
from test_scene_runtime import _scene_with_casting
from test_editorial import _finalized_take

client = TestClient(app)


def test_finalized_take_replay_is_ordered_and_includes_snapshots_and_annotations():
    _, project_id, scene_id, _, _ = _scene_with_casting("Replay and notes")
    run = client.post(f"/api/projects/{project_id}/scene-runs", json={"scene_id": scene_id}).json()
    take_id = _finalized_take(project_id, scene_id, run["id"], "Replay take", 900)

    replay = client.get(f"/api/projects/{project_id}/takes/{take_id}/replay")
    assert replay.status_code == 200, replay.text
    data = replay.json()
    assert data["duration_ms"] == 1100
    assert data["state_snapshot"] == {"blocking": "initial"}
    assert [event["sequence_number"] for event in data["events"]] == [0, 1]
    assert data["events"][0]["timestamp_ms"] <= data["events"][1]["timestamp_ms"]
    assert data["cast_members"]
    assert data["playback_capabilities"]["physics_determinism"] is False

    note = client.post(
        f"/api/projects/{project_id}/takes/{take_id}/annotations",
        json={"timestamp_ms": 400, "category": "continuity", "content": "Check eyeline before the cut."},
    )
    assert note.status_code == 201, note.text
    assert note.json()["status"] == "open"
    assert note.json()["author_display_name"]

    updated = client.patch(
        f"/api/projects/{project_id}/takes/{take_id}/annotations/{note.json()['id']}",
        json={"status": "resolved"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["status"] == "resolved"

    refreshed = client.get(f"/api/projects/{project_id}/takes/{take_id}/replay")
    assert refreshed.json()["annotations"][0]["content"] == "Check eyeline before the cut."
    assert refreshed.json()["annotations"][0]["status"] == "resolved"


def test_replay_and_annotations_enforce_project_and_take_boundaries():
    _, project_id, scene_id, _, _ = _scene_with_casting("Replay boundaries")
    run = client.post(f"/api/projects/{project_id}/scene-runs", json={"scene_id": scene_id}).json()
    take_id = _finalized_take(project_id, scene_id, run["id"], "Bounded take", 500)

    invalid_event = client.post(
        f"/api/projects/{project_id}/takes/{take_id}/annotations",
        json={"timestamp_ms": 100, "event_id": "00000000-0000-0000-0000-000000000001", "content": "Wrong event"},
    )
    assert invalid_event.status_code == 422
    beyond_duration = client.post(
        f"/api/projects/{project_id}/takes/{take_id}/annotations",
        json={"timestamp_ms": 9999, "content": "Outside take"},
    )
    assert beyond_duration.status_code == 422
    missing = client.get(f"/api/projects/{project_id}/takes/00000000-0000-0000-0000-000000000001/replay")
    assert missing.status_code == 404
