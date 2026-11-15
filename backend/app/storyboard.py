import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import (
    NarrativeApprovalDecision, NarrativeDraftVersion, Project, ProjectCharacter,
    ProjectLocation, ProjectPhaseTransition, SceneCharacterAssignment,
    ScenePassageReference, SceneScriptElement, SceneScriptVersion, Storyboard, StoryboardScene, User,
)
from .projects import CurrentUser, DbSession, _membership, _project_or_404
from .schemas import (
    CharacterCreate, CharacterRead, CharacterUpdate, LocationCreate, LocationRead,
    LocationUpdate, SceneCharacterRead, ScenePassageCreate, ScenePassageRead,
    SceneReorder, SceneScriptElementRead, SceneScriptVersionCreate, SceneScriptVersionRead,
    StoryboardDetail, StoryboardSceneCreate, StoryboardSceneRead, StoryboardSceneUpdate,
)

router = APIRouter(prefix="/api/projects/{project_id}/storyboard", tags=["storyboard"])


def _require_project(db: Session, project_id: uuid.UUID, user_id: uuid.UUID, *, write: bool = False) -> Project:
    project = _project_or_404(db, project_id)
    member = _membership(db, project_id, user_id)
    if write:
        if member.role == "viewer":
            raise HTTPException(status_code=403, detail="Viewers cannot edit the storyboard or creative assets.")
        if project.current_phase != "storyboard":
            raise HTTPException(status_code=409, detail="Storyboard changes are only available while the project is in the storyboard phase.")
    return project


def _storyboard_or_404(db: Session, project_id: uuid.UUID) -> Storyboard:
    # Return the latest storyboard interpretation for the project. Older versions
    # remain available in storage and retain their own scenes and source links.
    storyboard = db.scalar(
        select(Storyboard).where(Storyboard.project_id == project_id)
        .order_by(Storyboard.created_at.desc(), Storyboard.id.desc())
        .limit(1)
    )
    if storyboard is None:
        raise HTTPException(status_code=404, detail="Storyboard has not been initialized for this project.")
    return storyboard


def _scene_or_404(db: Session, storyboard_id: uuid.UUID, scene_id: uuid.UUID) -> StoryboardScene:
    scene = db.scalar(select(StoryboardScene).where(
        StoryboardScene.id == scene_id,
        StoryboardScene.storyboard_id == storyboard_id,
    ))
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found in this storyboard.")
    return scene


def _validate_location(db: Session, project_id: uuid.UUID, location_id: uuid.UUID | None) -> None:
    if location_id is None:
        return
    location = db.scalar(select(ProjectLocation).where(
        ProjectLocation.id == location_id,
        ProjectLocation.project_id == project_id,
        ProjectLocation.status == "active",
    ))
    if location is None:
        raise HTTPException(status_code=422, detail="The selected location is missing, archived, or belongs to another project.")


def _validate_characters(db: Session, project_id: uuid.UUID, character_ids: list[uuid.UUID]) -> list[ProjectCharacter]:
    if len(set(character_ids)) != len(character_ids):
        raise HTTPException(status_code=422, detail="A character can only be assigned to a scene once.")
    if not character_ids:
        return []
    characters = db.scalars(select(ProjectCharacter).where(
        ProjectCharacter.id.in_(character_ids),
        ProjectCharacter.project_id == project_id,
        ProjectCharacter.status == "active",
    )).all()
    by_id = {item.id: item for item in characters}
    if len(by_id) != len(character_ids):
        raise HTTPException(status_code=422, detail="One or more selected characters are missing, archived, or belong to another project.")
    return [by_id[item_id] for item_id in character_ids]


def _storyboard_detail(db: Session, storyboard: Storyboard) -> StoryboardDetail:
    narrative = db.get(NarrativeDraftVersion, storyboard.narrative_version_id)
    if narrative is None:
        raise HTTPException(status_code=409, detail="The storyboard's approved narrative version is unavailable.")

    character_rows = db.scalars(
        select(ProjectCharacter).where(ProjectCharacter.project_id == storyboard.project_id)
        .order_by(ProjectCharacter.name)
    ).all()
    location_rows = db.scalars(
        select(ProjectLocation).where(ProjectLocation.project_id == storyboard.project_id)
        .order_by(ProjectLocation.name)
    ).all()
    scene_rows = db.scalars(
        select(StoryboardScene).where(StoryboardScene.storyboard_id == storyboard.id)
        .order_by(StoryboardScene.scene_order)
    ).all()

    scenes: list[StoryboardSceneRead] = []
    for scene in scene_rows:
        assignments = db.scalars(
            select(SceneCharacterAssignment).where(SceneCharacterAssignment.scene_id == scene.id)
        ).all()
        scene_characters = []
        for assignment in assignments:
            character = db.get(ProjectCharacter, assignment.character_id)
            if character:
                scene_characters.append(SceneCharacterRead(
                    id=character.id, name=character.name,
                    role_label=assignment.role_label, notes=assignment.notes,
                ))

        passages = db.scalars(
            select(ScenePassageReference).where(ScenePassageReference.scene_id == scene.id)
            .order_by(ScenePassageReference.reference_order)
        ).all()
        scripts = db.scalars(
            select(SceneScriptVersion).where(SceneScriptVersion.scene_id == scene.id)
            .order_by(SceneScriptVersion.revision_number)
        ).all()
        script_reads = []
        for script in scripts:
            author = db.get(User, script.author_user_id)
            element_rows = db.scalars(
                select(SceneScriptElement)
                .where(SceneScriptElement.script_version_id == script.id)
                .order_by(SceneScriptElement.element_order)
            ).all()
            element_reads = [
                SceneScriptElementRead(
                    id=element.id,
                    element_order=element.element_order,
                    element_type=element.element_type,
                    content=element.content,
                    character_id=element.character_id,
                    character_name=element.character_name_snapshot,
                    created_at=element.created_at,
                )
                for element in element_rows
            ]
            script_reads.append(SceneScriptVersionRead(
                id=script.id, revision_number=script.revision_number,
                content=script.content, parent_version_id=script.parent_version_id,
                author_user_id=script.author_user_id,
                author_display_name=author.display_name if author else "Unknown participant",
                created_at=script.created_at, elements=element_reads,
            ))
        location = db.get(ProjectLocation, scene.location_id) if scene.location_id else None
        scenes.append(StoryboardSceneRead(
            id=scene.id, scene_order=scene.scene_order, title=scene.title,
            summary=scene.summary, requirements=scene.requirements,
            estimated_duration_seconds=scene.estimated_duration_seconds,
            location_id=scene.location_id, location_name=location.name if location else None,
            characters=scene_characters,
            passages=[ScenePassageRead.model_validate(item, from_attributes=True) for item in passages],
            script_versions=script_reads, created_by_user_id=scene.created_by_user_id,
            created_at=scene.created_at, updated_at=scene.updated_at,
        ))

    return StoryboardDetail(
        id=storyboard.id, project_id=storyboard.project_id, title=storyboard.title,
        narrative_version_id=narrative.id, narrative_version_number=narrative.version_number,
        narrative_title=narrative.title, narrative_content=narrative.content,
        created_by_user_id=storyboard.created_by_user_id, created_at=storyboard.created_at,
        scenes=scenes,
        characters=[CharacterRead.model_validate(item, from_attributes=True) for item in character_rows],
        locations=[LocationRead.model_validate(item, from_attributes=True) for item in location_rows],
    )


@router.get("", response_model=StoryboardDetail | None)
def get_storyboard(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _require_project(db, project_id, user.id)
    storyboard = db.scalar(
        select(Storyboard).where(Storyboard.project_id == project_id)
        .order_by(Storyboard.created_at.desc(), Storyboard.id.desc())
        .limit(1)
    )
    return _storyboard_detail(db, storyboard) if storyboard else None


@router.post("", response_model=StoryboardDetail, status_code=status.HTTP_201_CREATED)
def initialize_storyboard(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    project = _require_project(db, project_id, user.id, write=True)
    # The project row lock serializes first-time initialization.
    project = db.scalar(select(Project).where(Project.id == project_id).with_for_update())
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    if project.current_phase != "storyboard":
        raise HTTPException(status_code=409, detail="Storyboard initialization requires the project to be in the storyboard phase.")
    transition = db.scalar(
        select(ProjectPhaseTransition)
        .where(
            ProjectPhaseTransition.project_id == project_id,
            ProjectPhaseTransition.to_phase == "storyboard",
        )
        .order_by(ProjectPhaseTransition.created_at.desc(), ProjectPhaseTransition.id.desc())
        .limit(1)
    )
    if transition is None or transition.narrative_version_id is None:
        raise HTTPException(status_code=409, detail="No approved narrative transition is recorded for this project.")
    decision = db.scalar(select(NarrativeApprovalDecision).where(
        NarrativeApprovalDecision.version_id == transition.narrative_version_id,
        NarrativeApprovalDecision.outcome == "approved",
    ))
    narrative = db.get(NarrativeDraftVersion, transition.narrative_version_id)
    if decision is None or narrative is None:
        raise HTTPException(status_code=409, detail="The storyboard can only be initialized from the approved narrative version.")

    existing = db.scalar(select(Storyboard).where(
        Storyboard.project_id == project_id,
        Storyboard.narrative_version_id == narrative.id,
    ))
    if existing:
        return _storyboard_detail(db, existing)
    storyboard = Storyboard(
        project_id=project_id, narrative_version_id=narrative.id,
        title=narrative.title, created_by_user_id=user.id,
    )
    db.add(storyboard)
    db.commit()
    db.refresh(storyboard)
    return _storyboard_detail(db, storyboard)


@router.post("/characters", response_model=CharacterRead, status_code=status.HTTP_201_CREATED)
def create_character(project_id: uuid.UUID, payload: CharacterCreate, db: DbSession, user: CurrentUser):
    _require_project(db, project_id, user.id, write=True)
    _storyboard_or_404(db, project_id)
    character = ProjectCharacter(
        project_id=project_id, name=payload.name, description=payload.description,
        visual_description=payload.visual_description, personality_notes=payload.personality_notes,
        created_by_user_id=user.id,
    )
    db.add(character)
    db.commit()
    db.refresh(character)
    return CharacterRead.model_validate(character, from_attributes=True)


@router.patch("/characters/{character_id}", response_model=CharacterRead)
def update_character(project_id: uuid.UUID, character_id: uuid.UUID, payload: CharacterUpdate, db: DbSession, user: CurrentUser):
    _require_project(db, project_id, user.id, write=True)
    _storyboard_or_404(db, project_id)
    character = db.scalar(select(ProjectCharacter).where(
        ProjectCharacter.id == character_id, ProjectCharacter.project_id == project_id,
    ))
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(character, key, value)
    db.commit()
    db.refresh(character)
    return CharacterRead.model_validate(character, from_attributes=True)


@router.post("/locations", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
def create_location(project_id: uuid.UUID, payload: LocationCreate, db: DbSession, user: CurrentUser):
    _require_project(db, project_id, user.id, write=True)
    _storyboard_or_404(db, project_id)
    location = ProjectLocation(
        project_id=project_id, name=payload.name, description=payload.description,
        environment_type=payload.environment_type, time_period=payload.time_period,
        visual_notes=payload.visual_notes, created_by_user_id=user.id,
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return LocationRead.model_validate(location, from_attributes=True)


@router.patch("/locations/{location_id}", response_model=LocationRead)
def update_location(project_id: uuid.UUID, location_id: uuid.UUID, payload: LocationUpdate, db: DbSession, user: CurrentUser):
    _require_project(db, project_id, user.id, write=True)
    _storyboard_or_404(db, project_id)
    location = db.scalar(select(ProjectLocation).where(
        ProjectLocation.id == location_id, ProjectLocation.project_id == project_id,
    ))
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(location, key, value)
    db.commit()
    db.refresh(location)
    return LocationRead.model_validate(location, from_attributes=True)


@router.post("/scenes", response_model=StoryboardDetail, status_code=status.HTTP_201_CREATED)
def create_scene(project_id: uuid.UUID, payload: StoryboardSceneCreate, db: DbSession, user: CurrentUser):
    _require_project(db, project_id, user.id, write=True)
    storyboard = db.scalar(select(Storyboard).where(Storyboard.project_id == project_id).with_for_update())
    if storyboard is None:
        raise HTTPException(status_code=409, detail="Initialize the storyboard before adding scenes.")
    _validate_location(db, project_id, payload.location_id)
    characters = _validate_characters(db, project_id, payload.character_ids)
    next_order = (db.scalar(select(func.max(StoryboardScene.scene_order)).where(
        StoryboardScene.storyboard_id == storyboard.id,
    )) or 0) + 1
    scene = StoryboardScene(
        storyboard_id=storyboard.id, scene_order=next_order, title=payload.title,
        summary=payload.summary, requirements=payload.requirements,
        estimated_duration_seconds=payload.estimated_duration_seconds,
        location_id=payload.location_id, created_by_user_id=user.id,
    )
    db.add(scene)
    db.flush()
    for character in characters:
        db.add(SceneCharacterAssignment(
            scene_id=scene.id, character_id=character.id, assigned_by_user_id=user.id,
        ))
    db.commit()
    return _storyboard_detail(db, storyboard)


@router.patch("/scenes/{scene_id}", response_model=StoryboardDetail)
def update_scene(project_id: uuid.UUID, scene_id: uuid.UUID, payload: StoryboardSceneUpdate, db: DbSession, user: CurrentUser):
    _require_project(db, project_id, user.id, write=True)
    storyboard = _storyboard_or_404(db, project_id)
    scene = db.scalar(select(StoryboardScene).where(
        StoryboardScene.id == scene_id,
        StoryboardScene.storyboard_id == storyboard.id,
    ).with_for_update())
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found in this storyboard.")

    values = payload.model_dump(exclude_unset=True)
    character_ids = values.pop("character_ids", None)
    if "location_id" in values:
        _validate_location(db, project_id, values["location_id"])
    if character_ids is not None:
        characters = _validate_characters(db, project_id, character_ids)
        db.query(SceneCharacterAssignment).filter(
            SceneCharacterAssignment.scene_id == scene.id,
        ).delete(synchronize_session=False)
        for character in characters:
            db.add(SceneCharacterAssignment(
                scene_id=scene.id, character_id=character.id, assigned_by_user_id=user.id,
            ))
    for key, value in values.items():
        setattr(scene, key, value)
    db.commit()
    return _storyboard_detail(db, storyboard)


@router.put("/scenes/reorder", response_model=StoryboardDetail)
def reorder_scenes(project_id: uuid.UUID, payload: SceneReorder, db: DbSession, user: CurrentUser):
    _require_project(db, project_id, user.id, write=True)
    storyboard = db.scalar(select(Storyboard).where(Storyboard.project_id == project_id).with_for_update())
    if storyboard is None:
        raise HTTPException(status_code=404, detail="Storyboard not found.")
    scenes = db.scalars(select(StoryboardScene).where(
        StoryboardScene.storyboard_id == storyboard.id,
    ).with_for_update()).all()
    by_id = {scene.id: scene for scene in scenes}
    if len(payload.scene_ids) != len(scenes) or set(payload.scene_ids) != set(by_id):
        raise HTTPException(status_code=422, detail="Reorder must include every storyboard scene exactly once.")
    offset = max((scene.scene_order for scene in scenes), default=0) + len(scenes) + 1
    for scene in scenes:
        scene.scene_order += offset
    db.flush()
    for index, scene_id in enumerate(payload.scene_ids, start=1):
        by_id[scene_id].scene_order = index
    db.commit()
    return _storyboard_detail(db, storyboard)


@router.post("/scenes/{scene_id}/passages", response_model=StoryboardDetail, status_code=status.HTTP_201_CREATED)
def add_scene_passage(project_id: uuid.UUID, scene_id: uuid.UUID, payload: ScenePassageCreate, db: DbSession, user: CurrentUser):
    _require_project(db, project_id, user.id, write=True)
    storyboard = _storyboard_or_404(db, project_id)
    scene = db.scalar(select(StoryboardScene).where(
        StoryboardScene.id == scene_id,
        StoryboardScene.storyboard_id == storyboard.id,
    ).with_for_update())
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found in this storyboard.")
    narrative = db.get(NarrativeDraftVersion, storyboard.narrative_version_id)
    if narrative is None:
        raise HTTPException(status_code=409, detail="The approved narrative source is unavailable.")
    if not payload.passage_text.strip():
        raise HTTPException(status_code=422, detail="The selected narrative passage cannot be blank.")
    # Find the requested occurrence using Python code-point offsets. The browser
    # never supplies offsets, avoiding JavaScript UTF-16 / Python Unicode drift.
    start_offset = -1
    search_from = 0
    for _ in range(payload.occurrence):
        start_offset = narrative.content.find(payload.passage_text, search_from)
        if start_offset < 0:
            break
        search_from = start_offset + 1
    if start_offset < 0:
        raise HTTPException(status_code=422, detail="The exact passage text was not found in the approved narrative. Copy it from the source panel and try again.")
    end_offset = start_offset + len(payload.passage_text)
    snapshot = narrative.content[start_offset:end_offset]
    next_order = (db.scalar(select(func.max(ScenePassageReference.reference_order)).where(
        ScenePassageReference.scene_id == scene.id,
    )) or 0) + 1
    db.add(ScenePassageReference(
        scene_id=scene.id, reference_order=next_order,
        start_offset=start_offset, end_offset=end_offset,
        passage_snapshot=snapshot, created_by_user_id=user.id,
    ))
    db.commit()
    return _storyboard_detail(db, storyboard)


@router.post("/scenes/{scene_id}/script", response_model=StoryboardDetail, status_code=status.HTTP_201_CREATED)
def add_scene_script_version(project_id: uuid.UUID, scene_id: uuid.UUID, payload: SceneScriptVersionCreate, db: DbSession, user: CurrentUser):
    _require_project(db, project_id, user.id, write=True)
    storyboard = _storyboard_or_404(db, project_id)
    scene = db.scalar(select(StoryboardScene).where(
        StoryboardScene.id == scene_id, StoryboardScene.storyboard_id == storyboard.id,
    ).with_for_update())
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found in this storyboard.")
    latest = db.scalar(select(SceneScriptVersion).where(
        SceneScriptVersion.scene_id == scene.id,
    ).order_by(SceneScriptVersion.revision_number.desc()).limit(1).with_for_update())
    if latest is None and payload.base_version_id is not None:
        raise HTTPException(status_code=409, detail="This scene has no earlier script version.")
    if latest is not None and payload.base_version_id != latest.id:
        raise HTTPException(status_code=409, detail="The scene script has changed. Reload the latest version before saving.")

    element_characters: dict[uuid.UUID, ProjectCharacter] = {}
    if payload.elements:
        character_ids = [
            item.character_id for item in payload.elements
            if item.character_id is not None
        ]
        if len(set(character_ids)) != len(character_ids):
            # A character may speak multiple times in one script; repeated IDs
            # are expected, so only validate existence/ownership, not uniqueness.
            character_ids = list(set(character_ids))
        if character_ids:
            rows = db.scalars(select(ProjectCharacter).where(
                ProjectCharacter.id.in_(character_ids),
                ProjectCharacter.project_id == project_id,
                ProjectCharacter.status == "active",
            )).all()
            element_characters = {row.id: row for row in rows}
            if len(element_characters) != len(character_ids):
                raise HTTPException(
                    status_code=422,
                    detail="Every dialogue or parenthetical character must be active and belong to this project.",
                )

    def render_elements() -> str:
        rendered: list[str] = []
        for item in payload.elements or []:
            if item.element_type == "action":
                rendered.append(item.content)
            elif item.element_type == "dialogue":
                character = element_characters[item.character_id]
                rendered.append(f"{character.name.upper()}\\n{item.content}")
            elif item.element_type == "parenthetical":
                rendered.append(f"({item.content})")
            elif item.element_type == "transition":
                rendered.append(item.content.upper())
            else:
                rendered.append(f"[PRODUCTION NOTE: {item.content}]")
        return "\\n\\n".join(rendered)

    script_content = payload.content if payload.content is not None else render_elements()
    if not script_content.strip():
        raise HTTPException(status_code=422, detail="Script content cannot be blank.")

    version = SceneScriptVersion(
        scene_id=scene.id, revision_number=(latest.revision_number + 1 if latest else 1),
        content=script_content, parent_version_id=latest.id if latest else None,
        author_user_id=user.id,
    )
    db.add(version)
    db.flush()
    for element_order, item in enumerate(payload.elements or [], start=1):
        character = element_characters.get(item.character_id) if item.character_id else None
        db.add(SceneScriptElement(
            script_version_id=version.id,
            element_order=element_order,
            element_type=item.element_type,
            content=item.content,
            character_id=character.id if character else None,
            character_name_snapshot=character.name if character else None,
        ))
    db.commit()
    return _storyboard_detail(db, storyboard)
