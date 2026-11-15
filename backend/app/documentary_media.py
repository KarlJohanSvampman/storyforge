import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    DocumentaryClaim,
    DocumentaryClaimEvidence,
    DocumentaryClaimUsage,
    DocumentaryInterviewSession,
    DocumentaryInterviewSubject,
    DocumentaryMediaAsset,
    DocumentaryMediaRights,
    DocumentaryRelease,
    DocumentaryReleaseEvent,
    DocumentaryResearchSource,
    Project,
    SceneScriptVersion,
    Storyboard,
    StoryboardScene,
)
from .projects import CurrentUser, DbSession, _membership, _project_or_404
from .schemas import (
    DocumentaryClaimUsageCreate,
    DocumentaryClaimUsageRead,
    DocumentaryInterviewSessionCreate,
    DocumentaryInterviewSessionRead,
    DocumentaryInterviewSessionUpdate,
    DocumentaryInterviewSubjectCreate,
    DocumentaryInterviewSubjectRead,
    DocumentaryInterviewSubjectUpdate,
    DocumentaryMediaAssetRead,
    DocumentaryMediaRightsCreate,
    DocumentaryMediaRightsRead,
    DocumentaryProductionOverview,
    DocumentaryReleaseCreate,
    DocumentaryReleaseEventRead,
    DocumentaryReleaseRead,
    DocumentaryReleaseWithdraw,
)

router = APIRouter(prefix="/api/projects/{project_id}/documentary", tags=["documentary production research"])

ASSET_TYPES = {"transcript", "audio", "video", "image", "document", "release_document", "other"}
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".json": "application/json",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


def _documentary_project(
    db: Session, project_id: uuid.UUID, user_id: uuid.UUID, *, write: bool = False
) -> tuple[Project, object]:
    project = _project_or_404(db, project_id)
    membership = _membership(db, project_id, user_id)
    if project.category != "documentary":
        raise HTTPException(status_code=409, detail="Interview and media workflows are available for documentary projects only.")
    if write:
        if membership.role == "viewer":
            raise HTTPException(status_code=403, detail="Viewers cannot edit documentary production research.")
        if project.current_phase == "published":
            raise HTTPException(status_code=409, detail="Documentary production research is read-only after publication.")
    return project, membership


def _subject_or_404(db: Session, project_id: uuid.UUID, subject_id: uuid.UUID) -> DocumentaryInterviewSubject:
    item = db.scalar(select(DocumentaryInterviewSubject).where(
        DocumentaryInterviewSubject.id == subject_id,
        DocumentaryInterviewSubject.project_id == project_id,
    ))
    if item is None:
        raise HTTPException(status_code=404, detail="Interview subject not found in this project.")
    return item


def _session_or_404(db: Session, project_id: uuid.UUID, session_id: uuid.UUID) -> DocumentaryInterviewSession:
    item = db.scalar(select(DocumentaryInterviewSession).where(
        DocumentaryInterviewSession.id == session_id,
        DocumentaryInterviewSession.project_id == project_id,
    ))
    if item is None:
        raise HTTPException(status_code=404, detail="Interview session not found in this project.")
    return item


def _asset_or_404(db: Session, project_id: uuid.UUID, asset_id: uuid.UUID) -> DocumentaryMediaAsset:
    item = db.scalar(select(DocumentaryMediaAsset).where(
        DocumentaryMediaAsset.id == asset_id,
        DocumentaryMediaAsset.project_id == project_id,
    ))
    if item is None:
        raise HTTPException(status_code=404, detail="Media asset not found in this project.")
    return item


def _media_root() -> Path:
    return Path(os.getenv("STORYFORGE_MEDIA_DIR", "/app/storage/documentary")).resolve()


def _safe_storage_path(storage_key: str) -> Path:
    root = _media_root()
    candidate = (root / storage_key).resolve()
    if root != candidate and root not in candidate.parents:
        raise HTTPException(status_code=404, detail="Media file not found.")
    return candidate


def _latest_rights(db: Session, asset_id: uuid.UUID) -> DocumentaryMediaRights | None:
    return db.scalar(
        select(DocumentaryMediaRights)
        .where(DocumentaryMediaRights.media_asset_id == asset_id)
        .order_by(DocumentaryMediaRights.version_number.desc())
        .limit(1)
    )


def _production_overview(db: Session, project_id: uuid.UUID) -> DocumentaryProductionOverview:
    now = datetime.now(timezone.utc)
    subjects = db.scalars(
        select(DocumentaryInterviewSubject)
        .where(DocumentaryInterviewSubject.project_id == project_id)
        .order_by(DocumentaryInterviewSubject.created_at, DocumentaryInterviewSubject.id)
    ).all()
    subject_by_id = {item.id: item for item in subjects}

    sessions = db.scalars(
        select(DocumentaryInterviewSession)
        .where(DocumentaryInterviewSession.project_id == project_id)
        .order_by(DocumentaryInterviewSession.session_date, DocumentaryInterviewSession.id)
    ).all()
    assets = db.scalars(
        select(DocumentaryMediaAsset)
        .where(DocumentaryMediaAsset.project_id == project_id)
        .order_by(DocumentaryMediaAsset.created_at, DocumentaryMediaAsset.id)
    ).all()
    assets_by_session: dict[uuid.UUID, list[uuid.UUID]] = {}
    media_reads = []
    for asset in assets:
        if asset.interview_session_id:
            assets_by_session.setdefault(asset.interview_session_id, []).append(asset.id)
        rights = _latest_rights(db, asset.id)
        rights_read = DocumentaryMediaRightsRead.model_validate(rights, from_attributes=True) if rights else None
        if rights_read and rights_read.status == "active" and (
            (rights_read.valid_from is not None and rights_read.valid_from > now)
            or (rights_read.valid_until is not None and rights_read.valid_until < now)
        ):
            rights_read = rights_read.model_copy(update={"status": "needs_review"})
        media_reads.append(DocumentaryMediaAssetRead(
            id=asset.id,
            project_id=asset.project_id,
            source_id=asset.source_id,
            interview_session_id=asset.interview_session_id,
            title=asset.title,
            asset_type=asset.asset_type,
            original_filename=asset.original_filename,
            content_type=asset.content_type,
            size_bytes=asset.size_bytes,
            sha256=asset.sha256,
            duration_seconds=asset.duration_seconds,
            status=asset.status,
            download_url=f"/api/projects/{project_id}/documentary/media/{asset.id}/download",
            latest_rights=rights_read,
            created_by_user_id=asset.created_by_user_id,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
        ))

    session_reads = [
        DocumentaryInterviewSessionRead(
            id=item.id,
            project_id=item.project_id,
            subject_id=item.subject_id,
            subject_label=subject_by_id[item.subject_id].name_or_pseudonym if item.subject_id in subject_by_id else "Unknown subject",
            session_date=item.session_date,
            interviewer_name=item.interviewer_name,
            session_format=item.session_format,
            location_or_platform=item.location_or_platform,
            transcript_notes=item.transcript_notes,
            status=item.status,
            media_asset_ids=assets_by_session.get(item.id, []),
            created_by_user_id=item.created_by_user_id,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in sessions
    ]

    releases = db.scalars(
        select(DocumentaryRelease)
        .where(DocumentaryRelease.project_id == project_id)
        .order_by(DocumentaryRelease.created_at, DocumentaryRelease.id)
    ).all()
    release_reads = []
    for release in releases:
        events = db.scalars(
            select(DocumentaryReleaseEvent)
            .where(DocumentaryReleaseEvent.release_id == release.id)
            .order_by(DocumentaryReleaseEvent.created_at, DocumentaryReleaseEvent.id)
        ).all()
        subject = subject_by_id.get(release.subject_id)
        release_status = release.status
        if release_status == "signed" and release.expires_at is not None and release.expires_at < now:
            release_status = "expired"
        release_reads.append(DocumentaryReleaseRead(
            id=release.id,
            project_id=release.project_id,
            subject_id=release.subject_id,
            subject_label=subject.name_or_pseudonym if subject else "Unknown subject",
            interview_session_id=release.interview_session_id,
            scope_type=release.scope_type,
            scope_label=release.scope_label,
            consent_scope=release.consent_scope,
            withdrawal_terms=release.withdrawal_terms,
            permitted_uses=release.permitted_uses or [],
            status=release_status,
            signed_at=release.signed_at,
            expires_at=release.expires_at,
            release_document_asset_id=release.release_document_asset_id,
            created_by_user_id=release.created_by_user_id,
            created_at=release.created_at,
            updated_at=release.updated_at,
            events=[DocumentaryReleaseEventRead.model_validate(event, from_attributes=True) for event in events],
        ))

    usages = db.scalars(
        select(DocumentaryClaimUsage)
        .where(DocumentaryClaimUsage.project_id == project_id)
        .order_by(DocumentaryClaimUsage.created_at, DocumentaryClaimUsage.id)
    ).all()
    usage_reads = []
    for usage in usages:
        claim = db.get(DocumentaryClaim, usage.claim_id)
        scene = db.get(StoryboardScene, usage.scene_id) if usage.scene_id else None
        script = db.get(SceneScriptVersion, usage.script_version_id) if usage.script_version_id else None
        usage_reads.append(DocumentaryClaimUsageRead(
            id=usage.id,
            claim_id=usage.claim_id,
            claim_statement=claim.statement if claim else "Missing claim",
            claim_review_status=claim.current_review_status if claim else "unknown",
            usage_type=usage.usage_type,
            scene_id=usage.scene_id,
            scene_title=scene.title if scene else None,
            script_version_id=usage.script_version_id,
            script_revision_number=script.revision_number if script else None,
            reference_text=usage.reference_text,
            created_by_user_id=usage.created_by_user_id,
            created_at=usage.created_at,
        ))

    return DocumentaryProductionOverview(
        project_id=project_id,
        subjects=[DocumentaryInterviewSubjectRead.model_validate(item, from_attributes=True) for item in subjects],
        sessions=session_reads,
        releases=release_reads,
        media_assets=media_reads,
        claim_usages=usage_reads,
    )


def _claim_usage_permission(usage_type: str) -> str:
    return {
        "outline": "research",
        "scene": "storyboard",
        "script": "script",
        "narration": "narration",
        "lower_third": "lower_third",
        "caption": "caption",
    }[usage_type]


def _validate_source_media_clearance(
    db: Session, project_id: uuid.UUID, claim_id: uuid.UUID, usage_type: str
) -> None:
    """A media file used as claim evidence must have matching rights and interview consent."""
    evidence_source_ids = db.scalars(
        select(DocumentaryClaimEvidence.source_id).where(DocumentaryClaimEvidence.claim_id == claim_id)
    ).all()
    if not evidence_source_ids:
        return
    evidence_sources = db.scalars(
        select(DocumentaryResearchSource).where(
            DocumentaryResearchSource.project_id == project_id,
            DocumentaryResearchSource.id.in_(set(evidence_source_ids)),
        )
    ).all()
    assets = db.scalars(
        select(DocumentaryMediaAsset).where(
            DocumentaryMediaAsset.project_id == project_id,
            DocumentaryMediaAsset.source_id.in_(set(evidence_source_ids)),
        )
    ).all()
    assets_by_source: dict[uuid.UUID, list[DocumentaryMediaAsset]] = {}
    for asset in assets:
        if asset.source_id:
            assets_by_source.setdefault(asset.source_id, []).append(asset)
    for source in evidence_sources:
        if source.source_type == "interview":
            linked_assets = assets_by_source.get(source.id, [])
            linked_sessions = {asset.interview_session_id for asset in linked_assets}
            if not linked_assets or None in linked_sessions or len(linked_sessions) != 1:
                raise HTTPException(
                    status_code=409,
                    detail=f'Interview source "{source.title}" must be linked to exactly one interview session through an uploaded transcript or media asset before production use.',
                )
    permission = _claim_usage_permission(usage_type)
    now = datetime.now(timezone.utc)

    for asset in assets:
        if asset.status != "active":
            raise HTTPException(
                status_code=409,
                detail=f'Media evidence "{asset.title}" is archived and cannot be used in new production material.',
            )
        rights = _latest_rights(db, asset.id)
        if rights is None or rights.status != "active":
            raise HTTPException(
                status_code=409,
                detail=f'Media evidence "{asset.title}" needs a current rights record before it can be placed in {usage_type.replace("_", " ")}.',
            )
        if rights.valid_from and rights.valid_from > now:
            raise HTTPException(status_code=409, detail=f'Media rights for "{asset.title}" are not yet effective.')
        if rights.valid_until and rights.valid_until < now:
            raise HTTPException(status_code=409, detail=f'Media rights for "{asset.title}" have expired.')
        if rights.rights_basis == "unknown" and permission != "research":
            raise HTTPException(
                status_code=409,
                detail=f'Media rights for "{asset.title}" are unresolved; unknown rights cannot clear production use.',
            )
        if rights.rights_basis == "research_only" and permission != "research":
            raise HTTPException(
                status_code=409,
                detail=f'Media rights for "{asset.title}" are limited to research use.',
            )
        if permission not in (rights.permitted_uses or []) and "all" not in (rights.permitted_uses or []):
            raise HTTPException(
                status_code=409,
                detail=f'Media rights for "{asset.title}" do not permit {permission.replace("_", " ")} use.',
            )

        if asset.interview_session_id:
            session = _session_or_404(db, project_id, asset.interview_session_id)
            if session.status != "active":
                raise HTTPException(status_code=409, detail=f'Interview session "{session.id}" is archived and cannot be used in new production material.')
            signed_releases = db.scalars(
                select(DocumentaryRelease).where(
                    DocumentaryRelease.project_id == project_id,
                    DocumentaryRelease.subject_id == session.subject_id,
                    DocumentaryRelease.status == "signed",
                    DocumentaryRelease.scope_type.in_(("project", "production")),
                    DocumentaryRelease.signed_at.is_not(None),
                    DocumentaryRelease.signed_at <= now,
                    (
                        DocumentaryRelease.interview_session_id.is_(None)
                        | (DocumentaryRelease.interview_session_id == session.id)
                    ),
                )
            ).all()
            release_covers_use = any(
                (release.expires_at is None or release.expires_at >= now)
                and permission in (release.permitted_uses or [])
                for release in signed_releases
            )
            if not release_covers_use:
                raise HTTPException(
                    status_code=409,
                    detail=f'No active signed interview release for "{session.id}" permits {permission.replace("_", " ")} use.',
                )


@router.get("/production", response_model=DocumentaryProductionOverview)
def get_documentary_production(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _documentary_project(db, project_id, user.id)
    return _production_overview(db, project_id)


@router.post("/interview-subjects", response_model=DocumentaryProductionOverview, status_code=status.HTTP_201_CREATED)
def create_interview_subject(
    project_id: uuid.UUID,
    payload: DocumentaryInterviewSubjectCreate,
    db: DbSession,
    user: CurrentUser,
):
    _documentary_project(db, project_id, user.id, write=True)
    db.add(DocumentaryInterviewSubject(
        project_id=project_id,
        name_or_pseudonym=payload.name_or_pseudonym,
        identity_mode=payload.identity_mode,
        role_or_relationship=payload.role_or_relationship,
        background_notes=payload.background_notes,
        created_by_user_id=user.id,
    ))
    db.commit()
    return _production_overview(db, project_id)


@router.patch("/interview-subjects/{subject_id}", response_model=DocumentaryProductionOverview)
def update_interview_subject(
    project_id: uuid.UUID,
    subject_id: uuid.UUID,
    payload: DocumentaryInterviewSubjectUpdate,
    db: DbSession,
    user: CurrentUser,
):
    _documentary_project(db, project_id, user.id, write=True)
    subject = _subject_or_404(db, project_id, subject_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(subject, key, value)
    db.commit()
    return _production_overview(db, project_id)


@router.post("/interview-sessions", response_model=DocumentaryProductionOverview, status_code=status.HTTP_201_CREATED)
def create_interview_session(
    project_id: uuid.UUID,
    payload: DocumentaryInterviewSessionCreate,
    db: DbSession,
    user: CurrentUser,
):
    _documentary_project(db, project_id, user.id, write=True)
    subject = _subject_or_404(db, project_id, payload.subject_id)
    if subject.status != "active":
        raise HTTPException(status_code=409, detail="Archived interview subjects cannot receive new sessions.")
    db.add(DocumentaryInterviewSession(
        project_id=project_id,
        subject_id=subject.id,
        session_date=payload.session_date,
        interviewer_name=payload.interviewer_name,
        session_format=payload.session_format,
        location_or_platform=payload.location_or_platform,
        transcript_notes=payload.transcript_notes,
        created_by_user_id=user.id,
    ))
    db.commit()
    return _production_overview(db, project_id)


@router.patch("/interview-sessions/{session_id}", response_model=DocumentaryProductionOverview)
def update_interview_session(
    project_id: uuid.UUID,
    session_id: uuid.UUID,
    payload: DocumentaryInterviewSessionUpdate,
    db: DbSession,
    user: CurrentUser,
):
    _documentary_project(db, project_id, user.id, write=True)
    session = _session_or_404(db, project_id, session_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(session, key, value)
    db.commit()
    return _production_overview(db, project_id)


@router.post("/releases", response_model=DocumentaryProductionOverview, status_code=status.HTTP_201_CREATED)
def create_documentary_release(
    project_id: uuid.UUID,
    payload: DocumentaryReleaseCreate,
    db: DbSession,
    user: CurrentUser,
):
    _documentary_project(db, project_id, user.id, write=True)
    subject = _subject_or_404(db, project_id, payload.subject_id)
    if subject.status != "active":
        raise HTTPException(status_code=409, detail="Archived interview subjects cannot receive new releases.")
    if payload.interview_session_id:
        session = _session_or_404(db, project_id, payload.interview_session_id)
        if session.subject_id != subject.id:
            raise HTTPException(status_code=422, detail="The selected interview session belongs to a different subject.")
        if session.status != "active":
            raise HTTPException(status_code=409, detail="An archived interview session cannot receive a new release.")
    if payload.release_document_asset_id:
        release_file = _asset_or_404(db, project_id, payload.release_document_asset_id)
        if release_file.asset_type != "release_document" or release_file.status != "active":
            raise HTTPException(status_code=422, detail="The attached release document must be an active release_document media asset.")

    release = DocumentaryRelease(
        project_id=project_id,
        subject_id=subject.id,
        interview_session_id=payload.interview_session_id,
        scope_type=payload.scope_type,
        scope_label=payload.scope_label,
        consent_scope=payload.consent_scope,
        withdrawal_terms=payload.withdrawal_terms,
        permitted_uses=list(payload.permitted_uses),
        status=payload.status,
        signed_at=payload.signed_at,
        expires_at=payload.expires_at,
        release_document_asset_id=payload.release_document_asset_id,
        created_by_user_id=user.id,
    )
    db.add(release)
    db.flush()
    db.add(DocumentaryReleaseEvent(
        release_id=release.id,
        actor_user_id=user.id,
        previous_status=None,
        new_status=release.status,
        reason="Release record created.",
    ))
    db.commit()
    return _production_overview(db, project_id)


@router.post("/releases/{release_id}/withdraw", response_model=DocumentaryProductionOverview)
def withdraw_documentary_release(
    project_id: uuid.UUID,
    release_id: uuid.UUID,
    payload: DocumentaryReleaseWithdraw,
    db: DbSession,
    user: CurrentUser,
):
    _documentary_project(db, project_id, user.id, write=True)
    release = db.scalar(select(DocumentaryRelease).where(
        DocumentaryRelease.id == release_id,
        DocumentaryRelease.project_id == project_id,
    ).with_for_update())
    if release is None:
        raise HTTPException(status_code=404, detail="Release record not found in this project.")
    if release.status == "withdrawn":
        raise HTTPException(status_code=409, detail="This release has already been withdrawn.")
    previous_status = release.status
    release.status = "withdrawn"
    db.add(DocumentaryReleaseEvent(
        release_id=release.id,
        actor_user_id=user.id,
        previous_status=previous_status,
        new_status="withdrawn",
        reason=payload.reason,
    ))
    db.commit()
    return _production_overview(db, project_id)


@router.post("/media", response_model=DocumentaryProductionOverview, status_code=status.HTTP_201_CREATED)
async def upload_documentary_media(
    project_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=240),
    asset_type: str = Form("document"),
    source_id: uuid.UUID | None = Form(None),
    interview_session_id: uuid.UUID | None = Form(None),
    duration_seconds: int | None = Form(None),
):
    _documentary_project(db, project_id, user.id, write=True)
    if asset_type not in ASSET_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported documentary asset type.")
    if duration_seconds is not None and duration_seconds <= 0:
        raise HTTPException(status_code=422, detail="Media duration must be greater than zero.")
    if source_id:
        source = db.scalar(select(DocumentaryResearchSource).where(
            DocumentaryResearchSource.id == source_id,
            DocumentaryResearchSource.project_id == project_id,
        ))
        if source is None or source.status != "active":
            raise HTTPException(status_code=422, detail="Media must be linked to an active research source in this project.")
    if interview_session_id:
        session = _session_or_404(db, project_id, interview_session_id)
        if session.status != "active":
            raise HTTPException(status_code=409, detail="Cannot attach new files to an archived interview session.")

    original = (file.filename or "").replace("\\", "/").split("/")[-1].strip()
    if not original or original in {".", ".."}:
        raise HTTPException(status_code=422, detail="A valid original filename is required.")
    suffix = Path(original).suffix.lower()
    media_type = ALLOWED_EXTENSIONS.get(suffix)
    if media_type is None:
        raise HTTPException(status_code=415, detail="Unsupported file extension. Allowed types: PDF, text, CSV, JSON, DOCX, ODT, common audio/video and image formats.")
    if asset_type == "audio" and not media_type.startswith("audio/"):
        raise HTTPException(status_code=422, detail="Audio assets must use an audio file format.")
    if asset_type == "video" and not media_type.startswith("video/"):
        raise HTTPException(status_code=422, detail="Video assets must use a video file format.")
    if asset_type == "image" and not media_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="Image assets must use an image file format.")
    document_types = {
        "text/plain", "text/markdown", "text/csv", "application/json",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.oasis.opendocument.text",
    }
    if asset_type in {"document", "transcript", "release_document"} and media_type not in document_types:
        raise HTTPException(status_code=422, detail="Document, transcript and release-document assets must use a supported document format.")
    clean_title = title.strip()
    if not clean_title:
        raise HTTPException(status_code=422, detail="A non-empty asset title is required.")
    if len(original) > 255:
        original = original[-255:]

    asset_id = uuid.uuid4()
    storage_key = f"{project_id}/{asset_id}{suffix}"
    target = _safe_storage_path(storage_key)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    digest = hashlib.sha256()
    size = 0
    try:
        with temporary.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Documentary uploads are limited to 100 MiB per file.")
                digest.update(chunk)
                output.write(chunk)
        if size == 0:
            raise HTTPException(status_code=422, detail="Empty files cannot be uploaded.")
        os.replace(temporary, target)
        asset = DocumentaryMediaAsset(
            id=asset_id,
            project_id=project_id,
            source_id=source_id,
            interview_session_id=interview_session_id,
            title=clean_title,
            asset_type=asset_type,
            original_filename=original,
            content_type=media_type,
            size_bytes=size,
            sha256=digest.hexdigest(),
            storage_key=storage_key,
            duration_seconds=duration_seconds,
            created_by_user_id=user.id,
        )
        db.add(asset)
        db.commit()
    except Exception:
        db.rollback()
        temporary.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    return _production_overview(db, project_id)


@router.post("/media/{asset_id}/rights", response_model=DocumentaryProductionOverview, status_code=status.HTTP_201_CREATED)
def create_media_rights_version(
    project_id: uuid.UUID,
    asset_id: uuid.UUID,
    payload: DocumentaryMediaRightsCreate,
    db: DbSession,
    user: CurrentUser,
):
    _documentary_project(db, project_id, user.id, write=True)
    asset = _asset_or_404(db, project_id, asset_id)
    if asset.status != "active":
        raise HTTPException(status_code=409, detail="Archived media assets cannot receive new rights records.")
    previous = _latest_rights(db, asset.id)
    if previous is not None:
        previous.status = "superseded"
        version_number = previous.version_number + 1
    else:
        version_number = 1
    if payload.rights_basis == "research_only" and any(
        use not in {"research"} for use in payload.permitted_uses
    ):
        raise HTTPException(status_code=422, detail="Research-only rights may only permit research use.")
    db.add(DocumentaryMediaRights(
        media_asset_id=asset.id,
        version_number=version_number,
        supersedes_rights_id=previous.id if previous else None,
        rights_holder=payload.rights_holder,
        rights_basis=payload.rights_basis,
        license_name=payload.license_name,
        license_url=payload.license_url,
        territory=payload.territory,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        permitted_uses=list(payload.permitted_uses),
        attribution_required=payload.attribution_required,
        attribution_text=payload.attribution_text,
        restrictions=payload.restrictions,
        status="active",
        created_by_user_id=user.id,
    ))
    db.commit()
    return _production_overview(db, project_id)


@router.post("/claims/{claim_id}/usages", response_model=DocumentaryProductionOverview, status_code=status.HTTP_201_CREATED)
def create_documentary_claim_usage(
    project_id: uuid.UUID,
    claim_id: uuid.UUID,
    payload: DocumentaryClaimUsageCreate,
    db: DbSession,
    user: CurrentUser,
):
    project, _membership_record = _documentary_project(db, project_id, user.id, write=True)
    claim = db.scalar(select(DocumentaryClaim).where(
        DocumentaryClaim.id == claim_id,
        DocumentaryClaim.project_id == project_id,
    ).with_for_update())
    if claim is None:
        raise HTTPException(status_code=404, detail="Documentary claim not found in this project.")
    if claim.status != "active":
        raise HTTPException(status_code=409, detail="Archived claims cannot be linked to production material.")
    if claim.current_review_status != "supported":
        raise HTTPException(status_code=409, detail="Only claims with a current Supported human review can be placed in documentary production material.")

    if payload.scene_id or payload.script_version_id:
        if project.current_phase not in {"storyboard", "production"}:
            raise HTTPException(status_code=409, detail="Scene and screenplay references can only be added after the project enters storyboard or production.")
    scene = None
    if payload.scene_id:
        scene = db.get(StoryboardScene, payload.scene_id)
        if scene is None:
            raise HTTPException(status_code=404, detail="Storyboard scene not found.")
        storyboard = db.get(Storyboard, scene.storyboard_id)
        if storyboard is None or storyboard.project_id != project_id:
            raise HTTPException(status_code=422, detail="The selected scene does not belong to this documentary project.")
    if payload.script_version_id:
        script = db.get(SceneScriptVersion, payload.script_version_id)
        if script is None or scene is None or script.scene_id != scene.id:
            raise HTTPException(status_code=422, detail="The screenplay revision must belong to the selected scene.")
    _validate_source_media_clearance(db, project_id, claim.id, payload.usage_type)

    db.add(DocumentaryClaimUsage(
        project_id=project_id,
        claim_id=claim.id,
        scene_id=payload.scene_id,
        script_version_id=payload.script_version_id,
        usage_type=payload.usage_type,
        reference_text=payload.reference_text,
        created_by_user_id=user.id,
    ))
    db.commit()
    return _production_overview(db, project_id)


@router.get("/media/{asset_id}/download")
def download_documentary_media(
    project_id: uuid.UUID,
    asset_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
):
    _project, membership = _documentary_project(db, project_id, user.id)
    asset = _asset_or_404(db, project_id, asset_id)
    if asset.status != "active":
        raise HTTPException(status_code=404, detail="Media asset is archived.")
    if asset.asset_type == "release_document" and membership.role not in {"owner", "editor"}:
        raise HTTPException(status_code=403, detail="Only project owners and editors may download signed release documents.")
    path = _safe_storage_path(asset.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="The media file is missing from private storage.")
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=asset.original_filename,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
