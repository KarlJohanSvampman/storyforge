import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import Project, ProjectCharacter


def _project_with_character(title: str) -> tuple[str, str]:
    client = TestClient(app)
    response = client.post("/api/projects", json={"title": title, "format": "movie", "category": "fiction"})
    assert response.status_code == 201
    project_id = response.json()["id"]
    character_id = str(uuid.uuid4())
    with SessionLocal() as db:
        project = db.scalar(select(Project).where(Project.id == uuid.UUID(project_id)))
        project.current_phase = "storyboard"
        db.add(ProjectCharacter(
            id=uuid.UUID(character_id), project_id=project.id, name="Mara",
            description="", visual_description="", personality_notes="",
            status="active", created_by_user_id=project.owner_user_id,
        ))
        db.commit()
    return project_id, character_id


def test_actor_profile_and_casting_controller_configuration() -> None:
    client = TestClient(app)
    project_id, character_id = _project_with_character("Actor casting integration")
    actor_response = client.post("/api/actors", json={"display_name": "  Stage Performer  ", "biography": "Performer"})
    assert actor_response.status_code == 201
    actor = actor_response.json()
    assert actor["display_name"] == "Stage Performer"
    cast_response = client.post(
        f"/api/projects/{project_id}/casting",
        json={"actor_id": actor["id"], "character_id": character_id, "controller_type": "user", "control_mode": "direct"},
    )
    assert cast_response.status_code == 201
    cast = cast_response.json()
    assert cast["actor_name"] == "Stage Performer"
    assert cast["character_name"] == "Mara"
    assert cast["controller_type"] == "user"
    assert cast["control_mode"] == "direct"
    assert cast["controller_user_id"] is not None
    listed = client.get(f"/api/projects/{project_id}/casting")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    switched = client.patch(
        f"/api/projects/{project_id}/casting/{cast['id']}",
        json={"controller_type": "ai_agent", "control_mode": "autonomous"},
    )
    assert switched.status_code == 200
    assert switched.json()["controller_type"] == "ai_agent"
    assert switched.json()["controller_user_id"] is None


def test_casting_rejects_character_from_another_project() -> None:
    client = TestClient(app)
    project_id, _ = _project_with_character("Casting boundary integration")
    actor = client.post("/api/actors", json={"display_name": "Private Actor"}).json()
    _, foreign_character_id = _project_with_character("Other casting project")
    response = client.post(
        f"/api/projects/{project_id}/casting",
        json={"actor_id": actor["id"], "character_id": foreign_character_id},
    )
    assert response.status_code == 404


def test_actor_cannot_be_archived_while_casting_is_active() -> None:
    client = TestClient(app)
    project_id, character_id = _project_with_character("Actor archive integration")
    actor = client.post("/api/actors", json={"display_name": "Active Cast"}).json()
    cast = client.post(f"/api/projects/{project_id}/casting", json={"actor_id": actor["id"], "character_id": character_id})
    assert cast.status_code == 201
    archived = client.patch(f"/api/actors/{actor['id']}", json={"status": "archived"})
    assert archived.status_code == 409


def test_project_casting_policies_enforce_reuse_and_recasting() -> None:
    client = TestClient(app)
    project_id, first_character_id = _project_with_character("Casting policy integration")
    second_character_id = str(uuid.uuid4())
    with SessionLocal() as db:
        project = db.scalar(select(Project).where(Project.id == uuid.UUID(project_id)))
        db.add(ProjectCharacter(
            id=uuid.UUID(second_character_id), project_id=project.id, name="Jon",
            description="", visual_description="", personality_notes="",
            status="active", created_by_user_id=project.owner_user_id,
        ))
        db.commit()

    actor = client.post("/api/actors", json={"display_name": "One Role Actor"}).json()
    settings = client.patch(
        f"/api/projects/{project_id}/performance-settings",
        json={"allow_actor_reuse": False, "allow_character_recasting": False},
    )
    assert settings.status_code == 200

    first = client.post(
        f"/api/projects/{project_id}/casting",
        json={"actor_id": actor["id"], "character_id": first_character_id},
    )
    assert first.status_code == 201

    # A different character cannot reuse the same actor when the policy is disabled.
    reuse = client.post(
        f"/api/projects/{project_id}/casting",
        json={"actor_id": actor["id"], "character_id": second_character_id},
    )
    assert reuse.status_code == 409

    # Replacing the same character is independently governed by the recasting policy.
    replacement_actor = client.post("/api/actors", json={"display_name": "Replacement"}).json()
    recast = client.post(
        f"/api/projects/{project_id}/casting",
        json={"actor_id": replacement_actor["id"], "character_id": first_character_id},
    )
    assert recast.status_code == 409


def test_casting_rejects_blank_role_label_and_non_member_controller() -> None:
    client = TestClient(app)
    project_id, character_id = _project_with_character("Controller validation integration")
    actor = client.post("/api/actors", json={"display_name": "Controller Test"}).json()

    blank_role = client.post(
        f"/api/projects/{project_id}/casting",
        json={"actor_id": actor["id"], "character_id": character_id, "role_label": "   "},
    )
    assert blank_role.status_code == 422

    foreign_user_id = uuid.uuid4()
    invalid_controller = client.post(
        f"/api/projects/{project_id}/casting",
        json={"actor_id": actor["id"], "character_id": character_id, "controller_type": "user", "controller_user_id": str(foreign_user_id)},
    )
    assert invalid_controller.status_code == 422


def test_actor_library_is_private_to_owner() -> None:
    client = TestClient(app)
    actor = client.post("/api/actors", json={"display_name": "Private Library Entry"}).json()
    listed = client.get("/api/actors")
    assert listed.status_code == 200
    assert any(item["id"] == actor["id"] for item in listed.json())
