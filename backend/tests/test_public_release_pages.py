from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import PublishedRelease
from test_audio_pipeline import _production_sequence
from test_publications import _completed_video, _approve_storyboard_narrative

client = TestClient(app)





def test_public_release_visibility_and_media_delivery(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_PRODUCTION_MEDIA_DIR", str(tmp_path))
    project_id, sequence = _production_sequence("Public release delivery")
    sequence = client.get(f"/api/projects/{project_id}/edit-sequences/{sequence['id']}").json()
    asset_id, owner_id = _completed_video(project_id, sequence["id"], tmp_path)
    storyboard_id = _approve_storyboard_narrative(project_id, owner_id)
    response = client.post(f"/api/projects/{project_id}/releases", json={
        "video_asset_id": asset_id, "storyboard_id": storyboard_id,
        "title": "Public premiere", "synopsis": "A public synopsis.",
    })
    assert response.status_code == 201, response.text
    slug = response.json()["slug"]

    # Private is not discoverable or addressable through public routes.
    assert client.get(f"/api/public/releases/{slug}").status_code == 404
    assert client.get(f"/api/public/releases/{slug}/video").status_code == 404
    assert client.get("/api/public/releases").json() == []

    with SessionLocal() as db:
        release = db.scalar(select(PublishedRelease).where(PublishedRelease.slug == slug))
        release.visibility = "public"
        db.commit()

    page = client.get(f"/api/public/releases/{slug}")
    assert page.status_code == 200
    assert page.json()["title"] == "Public premiere"
    assert page.json()["synopsis"] == "A public synopsis."
    assert page.json()["video_url"] == f"/api/public/releases/{slug}/video"
    assert set(page.json()).isdisjoint({"manifest_json", "project_id", "video_asset_id"})
    assert [item["slug"] for item in client.get("/api/public/releases").json()] == [slug]

    video = client.get(f"/api/public/releases/{slug}/video")
    assert video.status_code == 200
    assert video.headers["content-type"].startswith("video/mp4")
    assert video.content == b"\x00\x00\x00\x18ftypmp42storyforge-test-video"

    with SessionLocal() as db:
        release = db.scalar(select(PublishedRelease).where(PublishedRelease.slug == slug))
        release.visibility = "unlisted"
        db.commit()
    assert client.get(f"/api/public/releases/{slug}").status_code == 200
    assert client.get("/api/public/releases").json() == []

    with SessionLocal() as db:
        release = db.scalar(select(PublishedRelease).where(PublishedRelease.slug == slug))
        release.visibility = "private"
        db.commit()
    assert client.get(f"/api/public/releases/{slug}").status_code == 404
