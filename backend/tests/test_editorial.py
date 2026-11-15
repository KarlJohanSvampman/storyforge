from fastapi.testclient import TestClient

from app.main import app
from test_scene_runtime import _scene_with_casting

client = TestClient(app)


def _finalized_take(project_id: str, scene_id: str, run_id: str, title: str, timestamp: int):
    take_response = client.post(
        f"/api/projects/{project_id}/scene-runs/{run_id}/takes",
        json={"title": title, "camera_snapshot": {"preset": "wide"}, "state_snapshot": {"blocking": "initial"}},
    )
    assert take_response.status_code == 201, take_response.text
    take = take_response.json()
    events = client.post(
        f"/api/projects/{project_id}/takes/{take['id']}/events",
        json=[{"sequence_number": 0, "timestamp_ms": 0, "event_type": "cue", "payload": {"beat": "start"}},
              {"sequence_number": 1, "timestamp_ms": timestamp, "event_type": "camera", "payload": {"preset": "close"}}],
    )
    assert events.status_code == 200, events.text
    finalized = client.post(
        f"/api/projects/{project_id}/takes/{take['id']}/finalize",
        json={"duration_ms": timestamp + 200},
    )
    assert finalized.status_code == 200, finalized.text
    return take["id"]


def test_non_destructive_edit_sequence_and_immutable_edl_export():
    client, project_id, scene_id, _, _ = _scene_with_casting("Editorial assembly integration")
    run = client.post(f"/api/projects/{project_id}/scene-runs", json={"scene_id": scene_id}).json()
    first_take = _finalized_take(project_id, scene_id, run["id"], "Wide take", 1200)
    selected = client.post(f"/api/projects/{project_id}/takes/{first_take}/select")
    assert selected.status_code == 200
    sequence_response = client.post(
        f"/api/projects/{project_id}/edit-sequences",
        json={"name": "Assembly v1"},
    )
    assert sequence_response.status_code == 201, sequence_response.text
    sequence_id = sequence_response.json()["id"]
    item_response = client.post(
        f"/api/projects/{project_id}/edit-sequences/{sequence_id}/items",
        json={"take_id": first_take, "in_ms": 100, "out_ms": 1000, "transition": "fade",
              "title_overlay": "Opening", "effects": {"grade": "warm"}, "audio_cue": "Station ambience"},
    )
    assert item_response.status_code == 201, item_response.text
    item = item_response.json()["items"][0]
    updated = client.patch(
        f"/api/projects/{project_id}/edit-sequences/{sequence_id}/items/{item['id']}",
        json={"out_ms": 900, "transition": "dissolve"},
    )
    assert updated.status_code == 200
    assert updated.json()["revision_number"] == 3
    assert updated.json()["items"][0]["out_ms"] == 900

    exported = client.post(f"/api/projects/{project_id}/edit-sequences/{sequence_id}/export")
    assert exported.status_code == 201, exported.text
    manifest = exported.json()["manifest"]
    assert manifest["format"] == "storyforge-edit-decision-list"
    assert manifest["duration_ms"] == 800
    assert manifest["clips"][0]["transition"] == "dissolve"
    assert manifest["clips"][0]["title_overlay"] == "Opening"
    assert manifest["rendering"]["status"] == "manifest_only"

    replay = client.get(f"/api/projects/{project_id}/takes/{first_take}")
    assert replay.status_code == 200
    assert replay.json()["status"] == "selected"
    assert replay.json()["duration_ms"] == 1400
