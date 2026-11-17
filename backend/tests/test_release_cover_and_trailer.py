import uuid

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Project
from test_audio_pipeline import _production_sequence
from test_publications import _completed_video, _approve_storyboard_narrative

client = TestClient(app)


def test_release_cover_and_optional_trailer_are_snapshotted_and_served(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_PRODUCTION_MEDIA_DIR", str(tmp_path))
    project_id, sequence = _production_sequence("Release poster and trailer")
    sequence = client.get(f"/api/projects/{project_id}/edit-sequences/{sequence['id']}").json()
    asset_id, owner_id = _completed_video(project_id, sequence["id"], tmp_path)
    storyboard_id = _approve_storyboard_narrative(project_id, owner_id)
    with SessionLocal() as db:
        project = db.get(Project, uuid.UUID(project_id))
        project.visibility = "public"
        db.commit()

    published = client.post(f"/api/projects/{project_id}/releases", json={
        "video_asset_id": asset_id, "trailer_video_asset_id": asset_id,
        "storyboard_id": storyboard_id, "title": "Poster premiere",
        "synopsis": "A test release with its own cover and trailer.",
    })
    assert published.status_code == 201, published.text
    release = published.json()
    assert release["manifest_json"]["poster"]["content_type"] == "image/jpeg"
    assert release["manifest_json"]["poster"]["sha256"]
    assert release["manifest_json"]["trailer_video"]["asset_id"] == asset_id

    page = client.get(f"/api/public/releases/{release['slug']}")
    assert page.status_code == 200
    assert page.json()["poster_url"].endswith("/poster")
    assert page.json()["trailer_url"].endswith("/trailer")
    poster = client.get(page.json()["poster_url"])
    assert poster.status_code == 200
    assert poster.headers["content-type"].startswith("image/jpeg")
    assert poster.content[:3] == b"\\xff\\xd8\\xff"
    trailer = client.get(page.json()["trailer_url"])
    assert trailer.status_code == 200
    assert trailer.headers["content-type"].startswith("video/mp4")
