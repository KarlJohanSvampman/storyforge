import uuid

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Project, User
from test_audio_pipeline import _production_sequence
from test_publications import _completed_video, _approve_storyboard_narrative

client = TestClient(app)


def test_public_discovery_filters_by_genre_creator_and_sorts_by_ratings(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_PRODUCTION_MEDIA_DIR", str(tmp_path))
    monkeypatch.setenv("STORYFORGE_DEV_USER_EMAIL", "discovery-owner@example.test")
    project_id, sequence = _production_sequence("Discovery listing")
    sequence = client.get(f"/api/projects/{project_id}/edit-sequences/{sequence['id']}").json()
    asset_id, owner_id = _completed_video(project_id, sequence["id"], tmp_path)
    storyboard_id = _approve_storyboard_narrative(project_id, owner_id)
    with SessionLocal() as db:
        project = db.get(Project, uuid.UUID(project_id))
        project.visibility = "public"
        project.genre = "Science Fiction"
        project.category = "fiction"
        project.format = "tv_series"
        creator = db.get(User, project.owner_user_id).display_name
        db.commit()

    published = client.post(f"/api/projects/{project_id}/releases", json={
        "video_asset_id": asset_id, "storyboard_id": storyboard_id,
        "title": "The Discovery Test",
    })
    assert published.status_code == 201, published.text
    slug = published.json()["slug"]

    monkeypatch.setenv("STORYFORGE_DEV_USER_EMAIL", "discovery-rater@example.test")
    rated = client.put(f"/api/public/releases/{slug}/rating", json={"score": 10})
    assert rated.status_code == 200

    response = client.get("/api/public/releases", params={
        "genre": "science", "creator": creator, "category": "fiction",
        "format": "tv_series", "sort": "popular", "limit": 10,
    })
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["slug"] == slug
    assert rows[0]["creator_name"] == creator
    assert rows[0]["genre"] == "Science Fiction"
    assert rows[0]["format"] == "tv_series"
    assert rows[0]["average_score"] == 10
    assert rows[0]["rating_count"] == 1

    assert client.get("/api/public/releases", params={"genre": "western"}).json() == []
    assert client.get("/api/public/releases", params={"creator": "no such creator"}).json() == []
    top_rated = client.get("/api/public/releases", params={"sort": "top_rated"})
    assert top_rated.status_code == 200
    assert top_rated.json()[0]["slug"] == slug
