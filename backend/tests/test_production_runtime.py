import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import (
    NarrativeDraft, NarrativeDraftVersion, Project, ProjectCharacter,
    SceneCharacterAssignment, Storyboard, StoryboardScene,
)

client = TestClient(app)


def _production_scene(title: str = "Runtime test", phase: str = "production") -> tuple[str, str]:
    response = client.post("/api/projects", json={"title": title, "format": "movie", "category": "fiction"})
    assert response.status_code == 201
    project_id = response.json()["id"]
    character_id = str(uuid.uuid4())
    with SessionLocal() as db:
        project = db.scalar(select(Project).where(Project.id == uuid.UUID(project_id)))
        project.current_phase = phase
        draft = NarrativeDraft(
            project_id=project.id, title="Approved source", current_version_number=1,
            created_by_user_id=project.owner_user_id,
        )
        db.add(draft)
        db.flush()
        version = NarrativeDraftVersion(
            draft_id=draft.id, version_number=1, title="Approved source",
            content="The scene begins.", status="proposal", origin="manual",
            author_user_id=project.owner_user_id,
        )
        db.add(version)
        db.flush()
        storyboard = Storyboard(
            project_id=project.id, narrative_version_id=version.id,
            title="Approved source", created_by_user_id=project.owner_user_id,
        )
        db.add(storyboard)
        db.flush()
        character = ProjectCharacter(
            id=uuid.UUID(character_id), project_id=project.id, name="Mara",
            description="Lead", visual_description="A traveller", personality_notes="Curious",
            status="active", created_by_user_id=project.owner_user_id,
        )
        db.add(character)
        db.flush()
        scene = StoryboardScene(
            storyboard_id=storyboard.id, scene_order=1, title="The arrival",
            summary="Mara enters the station.", requirements="Night exterior",
            estimated_duration_seconds=30, created_by_user_id=project.owner_user_id,
        )
        db.add(scene)
        db.flush()
        db.add(SceneCharacterAssignment(
            scene_id=scene.id, character_id=character.id,
            assigned_by_user_id=project.owner_user_id,
        ))
        db.commit()
        return project_id, str(scene.id)


def _cast(project_id: str, character_id: str) -> str:
    actor = client.post("/api/actors", json={"display_name": "Test performer"})
    assert actor.status_code == 201
    response = client.post(
        f"/api/projects/{project_id}/casting",
        json={"actor_id": actor.json()["id"], "character_id": character_id,
              "controller_type": "user", "control_mode": "direct"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_scene_run_instances_controller_epochs_and_possession_lease():
    project_id, scene_id = _production_scene()
    with SessionLocal() as db:
        project = db.get(Project, uuid.UUID(project_id))
        character_id = db.scalar(select(ProjectCharacter.id).where(ProjectCharacter.project_id == project.id))
    _cast(project_id, str(character_id))

    created = client.post(f"/api/projects/{project_id}/production/scene-runs", json={"scene_id": scene_id})
    assert created.status_code == 201, created.text
    run = created.json()
    assert run["run_number"] == 1
    assert run["status"] == "ready"
    assert len(run["cast_members"]) == 1
    instance = run["cast_members"][0]
    assert instance["character_snapshot"]["name"] == "Mara"
    assert instance["authority_epoch"] == 1

    started = client.patch(
        f"/api/projects/{project_id}/production/scene-runs/{run['id']}",
        json={"status": "running"},
    )
    assert started.status_code == 200
    lease = client.post(
        f"/api/projects/{project_id}/production/scene-runs/{run['id']}/instances/{instance['id']}/lease",
        json={"duration_seconds": 20},
    )
    assert lease.status_code == 201, lease.text
    assert lease.json()["authority_epoch"] == 2

    switched = client.post(
        f"/api/projects/{project_id}/production/scene-runs/{run['id']}/instances/{instance['id']}/controller",
        json={"controller_type": "ai_agent", "control_mode": "autonomous", "reason": "director_handoff"},
    )
    assert switched.status_code == 200
    assert switched.json()["authority_epoch"] == 3
    assert switched.json()["controller_user_id"] is None
    history = client.get(f"/api/projects/{project_id}/production/scene-runs/{run['id']}/controller-events")
    assert history.status_code == 200
    assert [event["authority_epoch"] for event in history.json()] == [1, 2, 3]

    paused = client.patch(
        f"/api/projects/{project_id}/production/scene-runs/{run['id']}",
        json={"status": "paused"},
    )
    assert paused.status_code == 200


def test_record_select_and_export_edit_sequence_manifest():
    project_id, scene_id = _production_scene("Recording and edit integration")
    with SessionLocal() as db:
        project = db.get(Project, uuid.UUID(project_id))
        character_id = db.scalar(select(ProjectCharacter.id).where(ProjectCharacter.project_id == project.id))
        user_id = project.owner_user_id
    _cast(project_id, str(character_id))
    run = client.post(f"/api/projects/{project_id}/production/scene-runs", json={"scene_id": scene_id}).json()
    instance = run["cast_members"][0]
    client.patch(f"/api/projects/{project_id}/production/scene-runs/{run['id']}", json={"status": "running"})
    client.patch(
        f"/api/projects/{project_id}/production/scene-runs/{run['id']}/instances/{instance['id']}/controller",
        json={"controller_type": "ai_agent", "control_mode": "autonomous"},
    )
    client.patch(f"/api/projects/{project_id}/production/scene-runs/{run['id']}", json={"status": "paused"})

    take = client.post(
        f"/api/projects/{project_id}/production/scene-runs/{run['id']}/takes",
        json={"state_snapshot": {"camera": "wide"}},
    )
    assert take.status_code == 201, take.text
    take_id = take.json()["id"]
    events = client.post(
        f"/api/projects/{project_id}/production/takes/{take_id}/events",
        json={"events": [
            {"timestamp_ms": 0, "event_type": "scene_started", "payload": {"beat": "arrival"}},
            {"timestamp_ms": 1500, "event_type": "character_transform", "cast_member_instance_id": instance["id"],
             "authority_epoch": 2, "payload": {"position": [1, 0, 2], "rotation": [0, 1.57, 0]}},
        ]},
    )
    assert events.status_code == 200, events.text
    assert events.json()["event_count"] == 2
    assert events.json()["duration_ms"] == 1500

    selected = client.patch(
        f"/api/projects/{project_id}/production/takes/{take_id}",
        json={"status": "selected"},
    )
    assert selected.status_code == 200
    sequence = client.post(
        f"/api/projects/{project_id}/production/edit-sequences",
        json={"name": "Assembly v1"},
    )
    assert sequence.status_code == 201, sequence.text
    sequence_id = sequence.json()["id"]
    item = client.post(
        f"/api/projects/{project_id}/production/edit-sequences/{sequence_id}/items",
        json={"take_id": take_id, "in_ms": 100, "out_ms": 1400,
              "transition": "fade", "title_overlay": "The arrival",
              "effects": {"grade": "warm"}, "audio_cue": "Low station ambience"},
    )
    assert item.status_code == 201, item.text
    exported = client.post(
        f"/api/projects/{project_id}/production/edit-sequences/{sequence_id}/export",
    )
    assert exported.status_code == 201, exported.text
    manifest = exported.json()["manifest"]
    assert manifest["format"] == "storyforge-edit-decision-list"
    assert manifest["duration_ms"] == 1300
    assert manifest["clips"][0]["transition"] == "fade"
    assert manifest["clips"][0]["take_id"] == take_id
    assert manifest["rendering"]["status"] == "manifest_only"


def test_scene_run_requires_active_cast_for_every_scene_character():
    project_id, scene_id = _production_scene("Missing cast integration")
    response = client.post(
        f"/api/projects/{project_id}/production/scene-runs",
        json={"scene_id": scene_id},
    )
    assert response.status_code == 409
    assert "active casting assignment" in response.json()["detail"]



def test_owner_activates_production_only_after_storyboard_characters_are_cast():
    project_id, scene_id = _production_scene("Production handoff", phase="storyboard")
    blocked = client.post(
        f"/api/projects/{project_id}/production/activate",
        json={"reason": "Ready"},
    )
    assert blocked.status_code == 409
    with SessionLocal() as db:
        project = db.get(Project, uuid.UUID(project_id))
        character_id = db.scalar(select(ProjectCharacter.id).where(ProjectCharacter.project_id == project.id))
    _cast(project_id, str(character_id))
    activated = client.post(
        f"/api/projects/{project_id}/production/activate",
        json={"reason": "Storyboard and cast approved."},
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["current_phase"] == "production"
    created = client.post(
        f"/api/projects/{project_id}/production/scene-runs",
        json={"scene_id": scene_id},
    )
    assert created.status_code == 201



def test_direct_possession_temporarily_overrides_ai_and_restores_it():
    project_id, scene_id = _production_scene("AI possession integration")
    with SessionLocal() as db:
        project = db.get(Project, uuid.UUID(project_id))
        character_id = db.scalar(select(ProjectCharacter.id).where(ProjectCharacter.project_id == project.id))
    assignment_id = _cast(project_id, str(character_id))
    switched = client.patch(
        f"/api/projects/{project_id}/casting/{assignment_id}",
        json={"controller_type": "ai_agent", "control_mode": "autonomous"},
    )
    assert switched.status_code == 200
    run = client.post(f"/api/projects/{project_id}/production/scene-runs", json={"scene_id": scene_id}).json()
    instance = run["cast_members"][0]
    client.patch(f"/api/projects/{project_id}/production/scene-runs/{run['id']}", json={"status": "running"})
    lease = client.post(
        f"/api/projects/{project_id}/production/scene-runs/{run['id']}/instances/{instance['id']}/lease",
        json={"duration_seconds": 30},
    )
    assert lease.status_code == 201, lease.text
    possessed = client.get(f"/api/projects/{project_id}/production/scene-runs/{run['id']}").json()["cast_members"][0]
    assert possessed["controller_type"] == "user"
    assert possessed["controller_user_id"] is not None
    assert possessed["control_mode"] == "direct"
    assert possessed["authority_epoch"] == 2

    released = client.post(
        f"/api/projects/{project_id}/production/scene-runs/{run['id']}/instances/{instance['id']}/lease/release",
        json={"lease_token": lease.json()["lease_token"]},
    )
    assert released.status_code == 200
    restored = client.get(f"/api/projects/{project_id}/production/scene-runs/{run['id']}").json()["cast_members"][0]
    assert restored["controller_type"] == "ai_agent"
    assert restored["controller_user_id"] is None
    assert restored["control_mode"] == "autonomous"
    assert restored["authority_epoch"] == 3
