from fastapi.testclient import TestClient

from app.main import app
from test_scene_runtime import _scene_with_casting

client = TestClient(app)


def test_director_possession_temporarily_overrides_and_restores_ai_controller():
    client, project_id, scene_id, _, _ = _scene_with_casting("Director possession")
    run_response = client.post(f"/api/projects/{project_id}/scene-runs", json={"scene_id": scene_id})
    assert run_response.status_code == 201, run_response.text
    run = run_response.json()
    instance = run["cast_members"][0]
    assert instance["controller_type"] == "ai_agent"
    started = client.patch(
        f"/api/projects/{project_id}/scene-runs/{run['id']}",
        json={"status": "running"},
    )
    assert started.status_code == 200
    current_user = client.get("/api/me").json()

    lease_response = client.post(
        f"/api/projects/{project_id}/scene-runs/{run['id']}/cast-members/{instance['id']}/leases",
        json={"duration_seconds": 20},
    )
    assert lease_response.status_code == 201, lease_response.text
    lease = lease_response.json()
    possessed = client.get(f"/api/projects/{project_id}/scene-runs/{run['id']}").json()["cast_members"][0]
    assert possessed["controller_type"] == "user"
    assert possessed["controller_user_id"] == current_user["id"]
    assert possessed["control_mode"] == "direct"
    assert possessed["authority_epoch"] == 2

    released = client.post(
        f"/api/projects/{project_id}/scene-runs/{run['id']}/cast-members/{instance['id']}/leases/release",
        json={"lease_token": lease["lease_token"]},
    )
    assert released.status_code == 200, released.text
    restored = client.get(f"/api/projects/{project_id}/scene-runs/{run['id']}").json()["cast_members"][0]
    assert restored["controller_type"] == "ai_agent"
    assert restored["controller_user_id"] is None
    assert restored["control_mode"] == "autonomous"
    assert restored["authority_epoch"] == 3


def test_scene_run_phase_handoff_requires_cast_and_records_transition():
    client, project_id, scene_id, _, _ = _scene_with_casting("Production activation")
    response = client.post(
        f"/api/projects/{project_id}/production/activate",
        json={"reason": "Storyboard and cast are ready."},
    )
    assert response.status_code == 200, response.text
    assert response.json()["current_phase"] == "production"
    run = client.post(f"/api/projects/{project_id}/scene-runs", json={"scene_id": scene_id})
    assert run.status_code == 201


def test_performance_events_validate_instance_and_authority_epoch():
    client, project_id, scene_id, _, _ = _scene_with_casting("Authority-aware recording")
    run = client.post(f"/api/projects/{project_id}/scene-runs", json={"scene_id": scene_id}).json()
    instance = run["cast_members"][0]
    take = client.post(
        f"/api/projects/{project_id}/scene-runs/{run['id']}/takes",
        json={"cast_member_instance_id": instance["id"], "state_snapshot": {"blocking": "A"}},
    ).json()
    bad = client.post(
        f"/api/projects/{project_id}/takes/{take['id']}/events",
        json=[{"sequence_number": 0, "timestamp_ms": 0, "event_type": "transform",
               "cast_member_instance_id": instance["id"], "authority_epoch": 99,
               "payload": {"position": [0, 0, 0]}}],
    )
    assert bad.status_code == 409
    good = client.post(
        f"/api/projects/{project_id}/takes/{take['id']}/events",
        json=[{"sequence_number": 0, "timestamp_ms": 0, "event_type": "transform",
               "cast_member_instance_id": instance["id"], "authority_epoch": 1,
               "payload": {"position": [0, 0, 0]}}],
    )
    assert good.status_code == 200, good.text
    assert good.json()["events"][0]["cast_member_instance_id"] == instance["id"]
