"""Immutable publication releases and provenance snapshots."""

import hashlib
import re
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .audio import _safe_path
from .models import (
    AudioClip, AudioTrack, EditSequence, EditSequenceItem, NarrativeApprovalDecision,
    NarrativeDraftVersion, ProductionMediaAsset, ProductionVideoAsset, Project,
    ProjectCharacter, ProjectLocation, PublishedRelease, SceneCharacterAssignment,
    SceneScriptElement, SceneScriptVersion, Storyboard, StoryboardEpisode, StoryboardScene,
    StoryboardSeason, VideoRenderJob,
)
from .projects import CurrentUser, DbSession, _membership
from .schemas import PublishedReleaseCreate, PublishedReleaseRead

router = APIRouter(prefix="/api/projects/{project_id}/releases", tags=["publication releases"])


def _release_or_404(db: Session, project_id: uuid.UUID, release_id: uuid.UUID) -> PublishedRelease:
    release = db.scalar(select(PublishedRelease).where(
        PublishedRelease.id == release_id,
        PublishedRelease.project_id == project_id,
    ))
    if release is None:
        raise HTTPException(status_code=404, detail="Published release not found.")
    return release


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:160].strip("-") or "release"


def _sha256_file(path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _scene_snapshot(db: Session, scene: StoryboardScene) -> dict:
    location = db.get(ProjectLocation, scene.location_id) if scene.location_id else None
    assignments = db.scalars(select(SceneCharacterAssignment).where(
        SceneCharacterAssignment.scene_id == scene.id,
    ).order_by(SceneCharacterAssignment.created_at)).all()
    characters = []
    for assignment in assignments:
        character = db.get(ProjectCharacter, assignment.character_id)
        if character is not None:
            characters.append({
                "character_id": str(character.id),
                "name": character.name,
                "role_label": assignment.role_label,
                "notes": assignment.notes,
            })

    script = db.scalar(select(SceneScriptVersion).where(
        SceneScriptVersion.scene_id == scene.id,
    ).order_by(SceneScriptVersion.revision_number.desc()).limit(1))
    script_snapshot = None
    if script is not None:
        elements = db.scalars(select(SceneScriptElement).where(
            SceneScriptElement.script_version_id == script.id,
        ).order_by(SceneScriptElement.element_order)).all()
        script_snapshot = {
            "id": str(script.id),
            "revision_number": script.revision_number,
            "content": script.content,
            "elements": [{
                "order": element.element_order,
                "type": element.element_type,
                "content": element.content,
                "character_id": str(element.character_id) if element.character_id else None,
                "character_name_snapshot": element.character_name_snapshot,
            } for element in elements],
        }
    return {
        "id": str(scene.id),
        "scene_order": scene.scene_order,
        "episode_id": str(scene.episode_id) if scene.episode_id else None,
        "title": scene.title,
        "summary": scene.summary,
        "requirements": scene.requirements,
        "estimated_duration_seconds": scene.estimated_duration_seconds,
        "location": ({
            "id": str(location.id), "name": location.name,
            "description": location.description, "environment_type": location.environment_type,
            "time_period": location.time_period, "visual_notes": location.visual_notes,
        } if location else None),
        "characters": characters,
        "script": script_snapshot,
    }


def _build_manifest(db: Session, project: Project, storyboard: Storyboard, narrative: NarrativeDraftVersion,
                    sequence: EditSequence, asset: ProductionVideoAsset, job: VideoRenderJob,
                    release_number: int) -> dict:
    scenes = db.scalars(select(StoryboardScene).where(
        StoryboardScene.storyboard_id == storyboard.id,
    ).order_by(StoryboardScene.scene_order, StoryboardScene.created_at)).all()
    scene_snapshots = [_scene_snapshot(db, scene) for scene in scenes]

    seasons = db.scalars(select(StoryboardSeason).where(
        StoryboardSeason.storyboard_id == storyboard.id,
    ).order_by(StoryboardSeason.season_number)).all()
    season_snapshots = []
    for season in seasons:
        episodes = db.scalars(select(StoryboardEpisode).where(
            StoryboardEpisode.season_id == season.id,
        ).order_by(StoryboardEpisode.episode_number)).all()
        season_snapshots.append({
            "id": str(season.id), "season_number": season.season_number,
            "title": season.title, "description": season.description,
            "story_arc": season.story_arc,
            "episodes": [{
                "id": str(episode.id), "episode_number": episode.episode_number,
                "title": episode.title, "logline": episode.logline,
                "synopsis": episode.synopsis,
                "estimated_duration_seconds": episode.estimated_duration_seconds,
                "status": episode.status,
            } for episode in episodes],
        })

    sequence_items = db.scalars(select(EditSequenceItem).where(
        EditSequenceItem.sequence_id == sequence.id,
    ).order_by(EditSequenceItem.item_order)).all()
    storyboard_scene_ids = {scene.id for scene in scenes}
    if not sequence_items:
        raise HTTPException(status_code=409, detail="The selected edit sequence has no clips.")
    if any(item.scene_id not in storyboard_scene_ids for item in sequence_items):
        raise HTTPException(status_code=409, detail="The selected edit sequence contains scenes outside the chosen storyboard.")

    tracks = db.scalars(select(AudioTrack).where(
        AudioTrack.sequence_id == sequence.id,
    ).order_by(AudioTrack.track_order)).all()
    track_snapshots = []
    for track in tracks:
        clips = db.scalars(select(AudioClip).where(
            AudioClip.track_id == track.id,
        ).order_by(AudioClip.clip_order)).all()
        clip_snapshots = []
        for clip in clips:
            media = db.get(ProductionMediaAsset, clip.media_asset_id)
            clip_snapshots.append({
                "id": str(clip.id), "clip_order": clip.clip_order,
                "source_in_ms": clip.source_in_ms, "source_out_ms": clip.source_out_ms,
                "timeline_start_ms": clip.timeline_start_ms, "gain": clip.gain,
                "fade_in_ms": clip.fade_in_ms, "fade_out_ms": clip.fade_out_ms,
                "media_asset": ({
                    "id": str(media.id), "title": media.title,
                    "content_type": media.content_type, "size_bytes": media.size_bytes,
                    "sha256": media.sha256, "duration_ms": media.duration_ms,
                } if media else None),
            })
        track_snapshots.append({
            "id": str(track.id), "name": track.name, "role": track.role,
            "track_order": track.track_order, "gain": track.gain, "pan": track.pan,
            "muted": track.muted, "solo": track.solo, "clips": clip_snapshots,
        })
    sequence_snapshot = {
        "id": str(sequence.id), "name": sequence.name,
        "revision_number": sequence.revision_number,
        "items": [{
            "id": str(item.id), "take_id": str(item.take_id),
            "scene_id": str(item.scene_id), "item_order": item.item_order,
            "in_ms": item.in_ms, "out_ms": item.out_ms,
            "transition": item.transition, "title_overlay": item.title_overlay,
            "effects": item.effects or {}, "audio_cue": item.audio_cue,
        } for item in sequence_items],
        "audio_tracks": track_snapshots,
    }

    return {
        "format_version": 1,
        "release_number": release_number,
        "project": {
            "id": str(project.id), "title": project.title,
            "description": project.description, "logline": project.logline,
            "genre": project.genre, "format": project.format,
            "category": project.category, "visibility": project.visibility,
        },
        "source": {
            "storyboard_id": str(storyboard.id),
            "storyboard_title": storyboard.title,
            "narrative_version_id": str(narrative.id),
            "narrative_version_number": narrative.version_number,
            "narrative_title": narrative.title,
            "narrative_content": narrative.content,
            "narrative_origin": narrative.origin,
            "narrative_provider": narrative.provider_name,
            "narrative_model": narrative.model_name,
            "approval_decision_id": str(db.scalar(select(NarrativeApprovalDecision).where(
                NarrativeApprovalDecision.version_id == narrative.id,
            )).id),
        },
        "storyboard": {"seasons": season_snapshots, "scenes": scene_snapshots},
        "edit_sequence": sequence_snapshot,
        "master_video": {
            "asset_id": str(asset.id), "title": asset.title,
            "sequence_id": str(asset.sequence_id),
            "sequence_revision": asset.sequence_revision,
            "render_job_id": str(job.id), "render_source": job.render_source,
            "original_filename": asset.original_filename,
            "content_type": asset.content_type, "size_bytes": asset.size_bytes,
            "sha256": asset.sha256, "duration_ms": asset.duration_ms,
            "width": asset.width, "height": asset.height,
            "storage_key": asset.storage_key,
        },
    }


@router.post("", response_model=PublishedReleaseRead, status_code=status.HTTP_201_CREATED)
def create_published_release(project_id: uuid.UUID, payload: PublishedReleaseCreate, db: DbSession, user: CurrentUser):
    project = db.scalar(select(Project).where(Project.id == project_id).with_for_update())
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    membership = _membership(db, project_id, user.id)
    if membership.role != "owner":
        raise HTTPException(status_code=403, detail="Only the project owner can publish a release.")
    if project.current_phase != "production":
        raise HTTPException(status_code=409, detail="A release can only be published from an active production project.")

    storyboard = db.scalar(select(Storyboard).where(
        Storyboard.id == payload.storyboard_id,
        Storyboard.project_id == project_id,
    ))
    if storyboard is None:
        raise HTTPException(status_code=404, detail="Storyboard not found in this project.")
    narrative = db.get(NarrativeDraftVersion, storyboard.narrative_version_id)
    decision = db.scalar(select(NarrativeApprovalDecision).where(
        NarrativeApprovalDecision.version_id == storyboard.narrative_version_id,
    ))
    if narrative is None or decision is None or decision.outcome != "approved":
        raise HTTPException(status_code=409, detail="The storyboard's exact narrative version must have an approved decision before publication.")

    asset = db.scalar(select(ProductionVideoAsset).where(
        ProductionVideoAsset.id == payload.video_asset_id,
        ProductionVideoAsset.project_id == project_id,
        ProductionVideoAsset.status == "active",
    ))
    if asset is None:
        raise HTTPException(status_code=404, detail="An active finished video asset from this project is required.")
    job = db.scalar(select(VideoRenderJob).where(
        VideoRenderJob.id == asset.render_job_id,
        VideoRenderJob.project_id == project_id,
        VideoRenderJob.status == "completed",
    ))
    if (
        job is None
        or job.output_sha256 != asset.sha256
        or job.output_storage_key != asset.storage_key
        or job.output_size_bytes != asset.size_bytes
        or job.output_content_type != asset.content_type
        or job.duration_ms != asset.duration_ms
        or job.width != asset.width
        or job.height != asset.height
        or asset.content_type != "video/mp4"
    ):
        raise HTTPException(status_code=409, detail="The selected video asset does not match a completed MP4 render job.")
    sequence = db.scalar(select(EditSequence).where(
        EditSequence.id == asset.sequence_id,
        EditSequence.project_id == project_id,
    ))
    if sequence is None or asset.sequence_revision != sequence.revision_number:
        raise HTTPException(status_code=409, detail="The edit sequence has changed since this video was rendered. Render the current sequence before publishing.")

    video_path = _safe_path(asset.storage_key)
    if not video_path.is_file() or _sha256_file(video_path) != asset.sha256:
        raise HTTPException(status_code=409, detail="The finished video file is missing or failed integrity verification.")

    title = (payload.title or project.title).strip()
    synopsis = (payload.synopsis if payload.synopsis is not None else project.logline or project.description).strip()
    if not title:
        raise HTTPException(status_code=422, detail="Release title cannot be blank.")

    latest_number = db.scalar(select(func.max(PublishedRelease.release_number)).where(
        PublishedRelease.project_id == project_id,
    )) or 0
    release_number = latest_number + 1
    slug = f"{_slugify(title)}-{str(project_id)[:8]}-r{release_number}"
    manifest = _build_manifest(db, project, storyboard, narrative, sequence, asset, job, release_number)
    release = PublishedRelease(
        project_id=project_id, release_number=release_number, slug=slug,
        title=title, synopsis=synopsis, visibility=project.visibility,
        storyboard_id=storyboard.id, narrative_version_id=narrative.id,
        video_asset_id=asset.id, manifest_json=manifest,
        published_by_user_id=user.id,
    )
    db.add(release)
    db.commit()
    db.refresh(release)
    return release


@router.get("", response_model=list[PublishedReleaseRead])
def list_published_releases(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _membership(db, project_id, user.id)
    return db.scalars(select(PublishedRelease).where(
        PublishedRelease.project_id == project_id,
    ).order_by(PublishedRelease.release_number.desc())).all()


@router.get("/{release_id}", response_model=PublishedReleaseRead)
def get_published_release(project_id: uuid.UUID, release_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _membership(db, project_id, user.id)
    return _release_or_404(db, project_id, release_id)
