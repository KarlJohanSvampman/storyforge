from fastapi.testclient import TestClient

from app.main import app
from test_audio_pipeline import _production_sequence
from test_publications import _completed_video, _approve_storyboard_narrative

client = TestClient(app)


def test_opt_in_credits_are_snapshotted_and_revocation_only_affects_future_releases(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_PRODUCTION_MEDIA_DIR", str(tmp_path))
    project_id, sequence = _production_sequence("Credit consent snapshot")
    sequence = client.get(f"/api/projects/{project_id}/edit-sequences/{sequence['id']}").json()
    asset_id, owner_id = _completed_video(project_id, sequence["id"], tmp_path)
    storyboard_id = _approve_storyboard_narrative(project_id, owner_id)

    contribution = client.post(f"/api/projects/{project_id}/contributions", json={
        "title": "Opening idea", "body": "The first story contribution.",
    })
    assert contribution.status_code == 201, contribution.text

    consent = client.post(f"/api/projects/{project_id}/credit-consents", json={
        "category": "contributor", "role_label": "Story contributor",
        "public_name": "A. Writer",
    })
    assert consent.status_code == 201, consent.text
    consent_id = consent.json()["id"]

    first = client.post(f"/api/projects/{project_id}/releases", json={
        "video_asset_id": asset_id, "storyboard_id": storyboard_id,
        "title": "Credited edition",
    })
    assert first.status_code == 201, first.text
    credits = first.json()["manifest_json"]["credits"]
    assert credits == [{
        "category": "contributor", "role_label": "Story contributor",
        "public_name": "A. Writer",
    }]

    revoked = client.delete(f"/api/projects/{project_id}/credit-consents/{consent_id}")
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["revoked_at"] is not None

    historical = client.get(f"/api/projects/{project_id}/releases/{first.json()['id']}")
    assert historical.status_code == 200
    assert historical.json()["manifest_json"]["credits"] == credits

    second = client.post(f"/api/projects/{project_id}/releases", json={
        "video_asset_id": asset_id, "storyboard_id": storyboard_id,
        "title": "Uncredited edition",
    })
    assert second.status_code == 201, second.text
    assert second.json()["manifest_json"]["credits"] == []
