import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import AudioClip, AudioTrack, EditExport, EditSequence, EditSequenceItem, PerformanceTake, ProductionMediaAsset, Project, SceneRun, StoryboardScene
from .projects import CurrentUser, DbSession, _membership, _project_or_404
from .schemas import (
    EditExportRead, EditSequenceCreate, EditSequenceItemCreate, EditSequenceItemRead,
    EditSequenceItemUpdate, EditSequenceRead, EditSequenceReorder,
)

router = APIRouter(tags=["editorial assembly"])


def _editor(db: Session, project_id: uuid.UUID, user_id: uuid.UUID, write: bool = False) -> Project:
    project = _project_or_404(db, project_id)
    member = _membership(db, project_id, user_id)
    if write and member.role not in ("owner", "editor"):
        raise HTTPException(status_code=403, detail="Only project owners and editors can change edit sequences.")
    if write and project.current_phase not in ("production", "published"):
        raise HTTPException(status_code=409, detail="Editorial assembly requires a project in production.")
    return project


def _sequence(db: Session, project_id: uuid.UUID, sequence_id: uuid.UUID) -> EditSequence:
    sequence = db.scalar(select(EditSequence).where(
        EditSequence.id == sequence_id, EditSequence.project_id == project_id,
    ).with_for_update())
    if sequence is None:
        raise HTTPException(status_code=404, detail="Edit sequence not found.")
    return sequence


def _read_sequence(db: Session, sequence: EditSequence) -> EditSequenceRead:
    items = db.scalars(select(EditSequenceItem).where(
        EditSequenceItem.sequence_id == sequence.id,
    ).order_by(EditSequenceItem.item_order)).all()
    return EditSequenceRead(
        id=sequence.id, project_id=sequence.project_id, name=sequence.name,
        status=sequence.status, revision_number=sequence.revision_number,
        created_by_user_id=sequence.created_by_user_id, created_at=sequence.created_at,
        updated_at=sequence.updated_at,
        items=[EditSequenceItemRead.model_validate(item, from_attributes=True) for item in items],
    )


@router.post("/api/projects/{project_id}/edit-sequences", response_model=EditSequenceRead, status_code=status.HTTP_201_CREATED)
def create_sequence(project_id: uuid.UUID, payload: EditSequenceCreate, db: DbSession, user: CurrentUser):
    _editor(db, project_id, user.id, write=True)
    sequence = EditSequence(project_id=project_id, name=payload.name, created_by_user_id=user.id)
    db.add(sequence)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="An edit sequence with that name already exists.")
    db.refresh(sequence)
    return _read_sequence(db, sequence)


@router.get("/api/projects/{project_id}/edit-sequences", response_model=list[EditSequenceRead])
def list_sequences(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _editor(db, project_id, user.id)
    rows = db.scalars(select(EditSequence).where(
        EditSequence.project_id == project_id,
    ).order_by(EditSequence.updated_at.desc())).all()
    return [_read_sequence(db, row) for row in rows]


@router.get("/api/projects/{project_id}/edit-sequences/{sequence_id}", response_model=EditSequenceRead)
def get_sequence(project_id: uuid.UUID, sequence_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _editor(db, project_id, user.id)
    return _read_sequence(db, _sequence(db, project_id, sequence_id))


@router.post("/api/projects/{project_id}/edit-sequences/{sequence_id}/items", response_model=EditSequenceRead, status_code=status.HTTP_201_CREATED)
def add_item(project_id: uuid.UUID, sequence_id: uuid.UUID, payload: EditSequenceItemCreate,
             db: DbSession, user: CurrentUser):
    _editor(db, project_id, user.id, write=True)
    sequence = _sequence(db, project_id, sequence_id)
    if sequence.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft sequences can be edited.")
    take = db.scalar(select(PerformanceTake).join(
        SceneRun, SceneRun.id == PerformanceTake.scene_run_id,
    ).where(PerformanceTake.id == payload.take_id, SceneRun.project_id == project_id))
    if take is None or take.status != "selected":
        raise HTTPException(status_code=422, detail="A clip must reference a selected take from this project.")
    if take.duration_ms is None or payload.in_ms >= payload.out_ms or payload.out_ms > take.duration_ms:
        raise HTTPException(status_code=422, detail="Clip source in/out points must be within the selected take duration.")
    run = db.get(SceneRun, take.scene_run_id)
    order = (db.scalar(select(func.max(EditSequenceItem.item_order)).where(EditSequenceItem.sequence_id == sequence.id)) or 0) + 1
    db.add(EditSequenceItem(
        sequence_id=sequence.id, take_id=take.id, scene_id=run.scene_id,
        item_order=order, in_ms=payload.in_ms, out_ms=payload.out_ms,
        transition=payload.transition, title_overlay=payload.title_overlay,
        effects=payload.effects, audio_cue=payload.audio_cue,
    ))
    sequence.revision_number += 1
    db.commit(); db.refresh(sequence)
    return _read_sequence(db, sequence)


@router.patch("/api/projects/{project_id}/edit-sequences/{sequence_id}/items/{item_id}", response_model=EditSequenceRead)
def update_item(project_id: uuid.UUID, sequence_id: uuid.UUID, item_id: uuid.UUID,
                payload: EditSequenceItemUpdate, db: DbSession, user: CurrentUser):
    _editor(db, project_id, user.id, write=True)
    sequence = _sequence(db, project_id, sequence_id)
    if sequence.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft sequences can be edited.")
    item = db.scalar(select(EditSequenceItem).where(
        EditSequenceItem.id == item_id, EditSequenceItem.sequence_id == sequence.id,
    ))
    if item is None:
        raise HTTPException(status_code=404, detail="Edit clip not found.")
    values = payload.model_dump(exclude_unset=True)
    in_ms, out_ms = values.get("in_ms", item.in_ms), values.get("out_ms", item.out_ms)
    take = db.get(PerformanceTake, item.take_id)
    if take is None or take.duration_ms is None or in_ms >= out_ms or out_ms > take.duration_ms:
        raise HTTPException(status_code=422, detail="Clip source in/out points must be within the selected take duration.")
    for key, value in values.items():
        if value is not None:
            setattr(item, key, value)
    sequence.revision_number += 1
    db.commit(); db.refresh(sequence)
    return _read_sequence(db, sequence)


@router.delete("/api/projects/{project_id}/edit-sequences/{sequence_id}/items/{item_id}", response_model=EditSequenceRead)
def delete_item(project_id: uuid.UUID, sequence_id: uuid.UUID, item_id: uuid.UUID,
                db: DbSession, user: CurrentUser):
    _editor(db, project_id, user.id, write=True)
    sequence = _sequence(db, project_id, sequence_id)
    if sequence.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft sequences can be edited.")
    item = db.scalar(select(EditSequenceItem).where(
        EditSequenceItem.id == item_id, EditSequenceItem.sequence_id == sequence.id,
    ))
    if item is None:
        raise HTTPException(status_code=404, detail="Edit clip not found.")
    db.delete(item); db.flush()
    remaining = db.scalars(select(EditSequenceItem).where(
        EditSequenceItem.sequence_id == sequence.id,
    ).order_by(EditSequenceItem.item_order)).all()
    for index, row in enumerate(remaining, start=1):
        row.item_order = index
    sequence.revision_number += 1
    db.commit(); db.refresh(sequence)
    return _read_sequence(db, sequence)


@router.put("/api/projects/{project_id}/edit-sequences/{sequence_id}/reorder", response_model=EditSequenceRead)
def reorder_items(project_id: uuid.UUID, sequence_id: uuid.UUID, payload: EditSequenceReorder,
                  db: DbSession, user: CurrentUser):
    _editor(db, project_id, user.id, write=True)
    sequence = _sequence(db, project_id, sequence_id)
    if sequence.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft sequences can be edited.")
    rows = db.scalars(select(EditSequenceItem).where(
        EditSequenceItem.sequence_id == sequence.id,
    ).with_for_update()).all()
    by_id = {row.id: row for row in rows}
    if len(payload.item_ids) != len(rows) or set(payload.item_ids) != set(by_id):
        raise HTTPException(status_code=422, detail="Reorder must include every clip exactly once.")
    offset = len(rows) + max((row.item_order for row in rows), default=0) + 1
    for row in rows:
        row.item_order += offset
    db.flush()
    for index, item_id in enumerate(payload.item_ids, start=1):
        by_id[item_id].item_order = index
    sequence.revision_number += 1
    db.commit(); db.refresh(sequence)
    return _read_sequence(db, sequence)


@router.post("/api/projects/{project_id}/edit-sequences/{sequence_id}/export", response_model=EditExportRead, status_code=status.HTTP_201_CREATED)
def export_sequence(project_id: uuid.UUID, sequence_id: uuid.UUID, db: DbSession, user: CurrentUser):
    project = _editor(db, project_id, user.id, write=True)
    sequence = _sequence(db, project_id, sequence_id)
    items = db.scalars(select(EditSequenceItem).where(
        EditSequenceItem.sequence_id == sequence.id,
    ).order_by(EditSequenceItem.item_order)).all()
    if not items:
        raise HTTPException(status_code=409, detail="Add at least one selected take before exporting.")
    cursor = 0
    clips = []
    for item in items:
        take = db.get(PerformanceTake, item.take_id)
        run = db.get(SceneRun, take.scene_run_id) if take else None
        scene = db.get(StoryboardScene, item.scene_id)
        if take is None or take.status != "selected" or run is None or scene is None:
            raise HTTPException(status_code=409, detail="Every clip must reference a valid selected take.")
        duration = item.out_ms - item.in_ms
        clips.append({
            "order": item.item_order, "scene_id": str(scene.id), "scene_title": scene.title,
            "scene_run_id": str(run.id), "take_id": str(take.id), "take_number": take.take_number,
            "take_title": take.title, "source_in_ms": item.in_ms, "source_out_ms": item.out_ms,
            "timeline_start_ms": cursor, "timeline_end_ms": cursor + duration,
            "duration_ms": duration, "transition": item.transition,
            "title_overlay": item.title_overlay, "effects": item.effects, "audio_cue": item.audio_cue,
        })
        cursor += duration
    audio_tracks = []
    audio_duration_ms = 0
    track_rows = db.scalars(
        select(AudioTrack).where(AudioTrack.sequence_id == sequence.id)
        .order_by(AudioTrack.track_order, AudioTrack.created_at)
    ).all()
    for track in track_rows:
        audio_clips = []
        clip_rows = db.execute(
            select(AudioClip, ProductionMediaAsset)
            .join(ProductionMediaAsset, ProductionMediaAsset.id == AudioClip.media_asset_id)
            .where(AudioClip.track_id == track.id)
            .order_by(AudioClip.clip_order, AudioClip.timeline_start_ms)
        ).all()
        for audio_clip, asset in clip_rows:
            if asset.project_id != project_id:
                raise HTTPException(status_code=409, detail="An audio clip references media outside this project.")
            clip_duration = audio_clip.source_out_ms - audio_clip.source_in_ms
            timeline_end = audio_clip.timeline_start_ms + clip_duration
            audio_duration_ms = max(audio_duration_ms, timeline_end)
            audio_clips.append({
                "id": str(audio_clip.id), "media_asset_id": str(asset.id),
                "title": asset.title, "filename": asset.original_filename,
                "content_type": asset.content_type, "sha256": asset.sha256,
                "download_url": f"/api/projects/{project_id}/production/media/{asset.id}/download",
                "asset_duration_ms": asset.duration_ms,
                "source_in_ms": audio_clip.source_in_ms, "source_out_ms": audio_clip.source_out_ms,
                "timeline_start_ms": audio_clip.timeline_start_ms, "timeline_end_ms": timeline_end,
                "duration_ms": clip_duration, "gain": audio_clip.gain,
                "fade_in_ms": audio_clip.fade_in_ms, "fade_out_ms": audio_clip.fade_out_ms,
                "clip_order": audio_clip.clip_order,
            })
        audio_tracks.append({
            "id": str(track.id), "name": track.name, "role": track.role,
            "track_order": track.track_order, "gain": track.gain, "pan": track.pan,
            "muted": track.muted, "solo": track.solo, "clips": audio_clips,
        })
    number = (db.scalar(select(func.max(EditExport.export_number)).where(EditExport.sequence_id == sequence.id)) or 0) + 1
    manifest = {
        "format": "storyforge-edit-decision-list", "format_version": 2,
        "project": {"id": str(project.id), "title": project.title, "format": project.format, "category": project.category},
        "sequence": {"id": str(sequence.id), "name": sequence.name, "revision": sequence.revision_number},
        "timebase": {"unit": "milliseconds", "frame_rate": None},
        "duration_ms": max(cursor, audio_duration_ms), "video_duration_ms": cursor,
        "audio_duration_ms": audio_duration_ms, "clips": clips, "audio_tracks": audio_tracks,
        "audio_mix": {"sample_peak_normalization": False, "rendered": False, "note": "Audio sources and mix automation are referenced by this EDL; a final mixed audio file is not rendered."},
        "rendering": {"status": "manifest_only", "note": "This is an immutable edit decision list, not a rendered video file."},
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    export = EditExport(
        sequence_id=sequence.id, export_number=number, sequence_revision=sequence.revision_number,
        manifest=manifest, created_by_user_id=user.id,
    )
    db.add(export)
    db.commit(); db.refresh(export)
    return EditExportRead.model_validate(export, from_attributes=True)


@router.get("/api/projects/{project_id}/edit-exports/{export_id}", response_model=EditExportRead)
def get_export(project_id: uuid.UUID, export_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _editor(db, project_id, user.id)
    export = db.scalar(select(EditExport).join(
        EditSequence, EditSequence.id == EditExport.sequence_id,
    ).where(EditExport.id == export_id, EditSequence.project_id == project_id))
    if export is None:
        raise HTTPException(status_code=404, detail="Edit export not found.")
    return EditExportRead.model_validate(export, from_attributes=True)
