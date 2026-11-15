from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_reports_current_api_version() -> None:
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "storyforge-api",
        "version": app.version,
    }


def test_project_create_list_detail_and_invitation_flow() -> None:
    client = TestClient(app)

    created = client.post(
        "/api/projects",
        json={
            "title": "CI integration project",
            "description": "Created by the automated backend test.",
            "logline": "A small project used to verify the basic project lifecycle.",
            "genre": "Test",
            "format": "movie",
            "category": "fiction",
            "visibility": "private",
        },
    )
    assert created.status_code == 201
    project = created.json()
    assert project["title"] == "CI integration project"
    assert project["member_count"] == 1

    project_id = project["id"]
    listed = client.get("/api/projects")
    assert listed.status_code == 200
    assert any(item["id"] == project_id for item in listed.json())

    detail = client.get(f"/api/projects/{project_id}")
    assert detail.status_code == 200
    assert detail.json()["members"][0]["role"] == "owner"

    invitation = client.post(
        f"/api/projects/{project_id}/invitations",
        json={"email": "collaborator@example.test", "role": "contributor"},
    )
    assert invitation.status_code == 201
    assert invitation.json()["status"] == "invited"
    assert invitation.json()["invited_email"] == "collaborator@example.test"
