import uuid

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Project
from test_audio_pipeline import _production_sequence
from test_publications import _completed_video, _approve_storyboard_narrative

client = TestClient(app)


def test_ratings_reviews_spoilers_reactions_and_report_threshold(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_PRODUCTION_MEDIA_DIR", str(tmp_path))
    monkeypatch.setenv("STORYFORGE_DEV_USER_EMAIL", "review-author@example.test")
    project_id, sequence = _production_sequence("Release audience feedback")
    sequence = client.get(f"/api/projects/{project_id}/edit-sequences/{sequence['id']}").json()
    asset_id, owner_id = _completed_video(project_id, sequence["id"], tmp_path)
    storyboard_id = _approve_storyboard_narrative(project_id, owner_id)
    with SessionLocal() as db:
        project = db.get(Project, uuid.UUID(project_id))
        project.visibility = "public"
        db.commit()

    release = client.post(f"/api/projects/{project_id}/releases", json={
        "video_asset_id": asset_id, "storyboard_id": storyboard_id, "title": "Audience edition",
    })
    assert release.status_code == 201, release.text
    slug = release.json()["slug"]

    first_rating = client.put(f"/api/public/releases/{slug}/rating", json={"score": 7})
    second_rating = client.put(f"/api/public/releases/{slug}/rating", json={"score": 9})
    assert first_rating.status_code == 200
    assert second_rating.status_code == 200
    assert second_rating.json()["score"] == 9

    first_review = client.put(f"/api/public/releases/{slug}/review", json={
        "body": "A thoughtful film with a surprising ending.",
        "contains_spoilers": True,
    })
    assert first_review.status_code == 200, first_review.text
    review_id = first_review.json()["id"]
    edited_review = client.put(f"/api/public/releases/{slug}/review", json={
        "body": "Updated thoughts — the ending really works.",
        "contains_spoilers": False,
    })
    assert edited_review.json()["id"] == review_id
    assert edited_review.json()["contains_spoilers"] is False

    monkeypatch.setenv("STORYFORGE_DEV_USER_EMAIL", "reader-one@example.test")
    assert client.put(f"/api/public/releases/{slug}/reviews/{review_id}/helpful").status_code == 200
    first_report = client.post(f"/api/public/releases/{slug}/reviews/{review_id}/reports", json={"reason": "Spam or abuse"})
    assert first_report.status_code == 201
    assert first_report.json()["review_hidden"] is False

    monkeypatch.setenv("STORYFORGE_DEV_USER_EMAIL", "reader-two@example.test")
    second_report = client.post(f"/api/public/releases/{slug}/reviews/{review_id}/reports", json={"reason": "Spam or abuse"})
    assert second_report.status_code == 201
    assert second_report.json()["review_hidden"] is False

    monkeypatch.setenv("STORYFORGE_DEV_USER_EMAIL", "reader-three@example.test")
    third_report = client.post(f"/api/public/releases/{slug}/reviews/{review_id}/reports", json={"reason": "Spam or abuse"})
    assert third_report.status_code == 201
    assert third_report.json()["review_hidden"] is True

    feedback = client.get(f"/api/public/releases/{slug}/feedback")
    assert feedback.status_code == 200
    assert feedback.json()["rating_count"] == 1
    assert feedback.json()["average_score"] == 9
    assert feedback.json()["rating_distribution"]["9"] == 1
    assert feedback.json()["reviews"] == []
