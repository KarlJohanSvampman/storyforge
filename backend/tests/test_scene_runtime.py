import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import (
    Actor, CastingAssignment, Project, ProjectCharacter, SceneCharacterAssignment,
    Storyboard, StoryboardScene,
)


def _scene_with_casting(title: str):
    client = TestClient(app)
    project_response = client.post("/api/projects", json={"title": title, "format": "movie", "category": "fiction"})
    assert project_response.status_code == 201
    project_id = uuid.UUID(project_response.json()["id"])
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        project.current_phase = "storyboard"
        character = ProjectCharacter(
            project_id=project_id, name="Mara", description="", visual_description="",
            personality_notes="", status="active", created_by_user_id=project.owner_user_id,
        )
        db.add(character)
        db.flush()
        from app.models import NarrativeDraft, NarrativeDraftVersion
        draft = NarrativeDraft(
            project_id=project_id, title="Approved narrative",
            current_version_number=1, created_by_user_id=project.owner_user_id,
        )
        db.add(draft)
        db.flush()
        narrative = NarrativeDraftVersion(
            draft_id=draft.id, version_number=1, title="Approved", content="Story",
            author_user_id=project.owner_user_id, parent_version_id=None, origin="manual",
        )
        db.add(narrative)
        storyboard = Storyboard(
            project_id=project_id, narrative_version_id=narrative.id,
            title="Storyboard", created_by_user_id=project.owner_user_id,
        )
        db.add(storyboard)
        db.flush()
        scene = StoryboardScene(
            storyboard_id=storyboard.id, scene_order=1, title="Opening",
            summary="", requirements="", created_by_user_id=project.owner_user_id,
        )
        db.add(scene)
        db.flush()
        db.add(SceneCharacterAssignment(
            scene_id=scene.id, character_id=character.id, role_label="Lead",
            notes="", assigned_by_user_id=project.owner_user_id,
        ))
        actor = Actor(owner_user_id=project.owner_user_id, display_name="Stage Actor")
        db.add(actor)
        db.flush()
        casting = CastingAssignment(
            project_id=project_id, actor_id=actor.id, character_id=character.id,
            role_label="Lead", controller_type="ai_agent", controller_user_id=None,
            control_mode="autonomous", control_settings={"voice": "warm"},
            assigned_by_user_id=project.owner_user_id,
        )
        db.add(casting)
        db.commit()
        scene_id = scene.id
        character_id = character.id
        actor_id = actor.id
    return client, str(project_id), str(scene_id), str(character_id), str(actor_id)


def test_scene_run_snapshots_only_scene_cast_and_source() -> None:
    client, project_id, scene_id, character_id, actor_id = _scene_with_casting("Scene runtime test")
    response = client.post(f"/api/projects/{project_id}/scene-runs", json={"scene_id": scene_id})
    assert response.status_code == 201, response.text
    run = response.json()
    assert run["status"] == "prepared"
    assert run["authority_epoch"] == 1
    assert run["scene_title"] == "Opening"
    assert len(run["cast_members"]) == 1
    member = run["cast_members"][0]
    assert member["actor_id"] == actor_id
    assert member["character_id"] == character_id
    assert member["actor_name_snapshot"] == "Stage Actor"
    assert member["controller_type"] == "ai_agent"
    assert member["control_settings"] == {"voice": "warm"}
    assert run["uncast_character_ids"] == []


def test_scene_run_rejects_scene_from_another_project() -> None:
    client, project_id, _, _, _ = _scene_with_casting("Scene runtime boundary A")
    _, _, foreign_scene_id, _, _ = _scene_with_casting("Scene runtime boundary B")
    response = client.post(f"/api/projects/{project_id}/scene-runs", json={"scene_id": foreign_scene_id})
    assert response.status_code == 404


def test_scene_run_reports_unmatched_casting_without_failing() -> None:
    client, project_id, scene_id, _, _ = _scene_with_casting("Scene runtime uncast")
    with SessionLocal() as db:
        scene = db.get(StoryboardScene, uuid.UUID(scene_id))
        character = db.scalar(select(ProjectCharacter).where(ProjectCharacter.name == "Mara", ProjectCharacter.project_id == uuid.UUID(project_id)))
        db.execute(
            __import__("sqlalchemy").delete(CastingAssignment).where(CastingAssignment.character_id == character.id)
        )
        db.commit()
    response = client.post(f"/api/projects/{project_id}/scene-runs", json={"scene_id": scene_id})
    assert response.status_code == 201
    assert len(response.json()["uncast_character_ids"]) == 1
