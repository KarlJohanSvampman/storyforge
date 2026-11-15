import uuid
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import (
    ContributionRevision, DraftSourceReference, NarrativeDraft,
    NarrativeDraftVersion, Project, StoryContribution, StorySuggestion, User,
)
from .projects import CurrentUser, DbSession, _membership, _project_or_404
from .schemas import (
    NarrativeDraftCompile, NarrativeDraftDetail,
    NarrativeDraftVersionCreate, NarrativeDraftVersionRead, NarrativeDraftSourceRead,
)
from .services.narrative_compiler import CompilerSource, get_narrative_compiler

router = APIRouter(prefix="/api/projects/{project_id}/draft", tags=["narrative drafts"])


def _require_access(db: Session, project_id: uuid.UUID, user_id: uuid.UUID, *, write: bool = False) -> Project:
    project = _project_or_404(db, project_id)
    membership = _membership(db, project_id, user_id)
    if write and membership.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot create or edit narrative drafts.")
    return project


def _version_read(db: Session, version: NarrativeDraftVersion) -> NarrativeDraftVersionRead:
    author = db.get(User, version.author_user_id)
    sources = db.scalars(
        select(DraftSourceReference)
        .where(DraftSourceReference.version_id == version.id)
        .order_by(DraftSourceReference.source_order)
    ).all()
    source_reads = [
        NarrativeDraftSourceRead(
            id=source.id,
            source_order=source.source_order,
            source_kind=source.source_kind,
            contribution_id=source.contribution_id,
            contribution_revision_id=source.contribution_revision_id,
            suggestion_id=source.suggestion_id,
            source_title=source.source_title,
            source_text_snapshot=source.source_text_snapshot,
        )
        for source in sources
    ]
    return NarrativeDraftVersionRead(
        id=version.id,
        version_number=version.version_number,
        title=version.title,
        content=version.content,
        status=version.status,
        origin=version.origin,
        provider_name=version.provider_name,
        model_name=version.model_name,
        prompt_version=version.prompt_version,
        author_user_id=version.author_user_id,
        author_display_name=author.display_name if author else "Unknown participant",
        parent_version_id=version.parent_version_id,
        created_at=version.created_at,
        sources=source_reads,
    )


def _draft_detail(db: Session, draft: NarrativeDraft) -> NarrativeDraftDetail:
    versions = db.scalars(
        select(NarrativeDraftVersion)
        .where(NarrativeDraftVersion.draft_id == draft.id)
        .order_by(NarrativeDraftVersion.version_number)
    ).all()
    return NarrativeDraftDetail(
        id=draft.id,
        project_id=draft.project_id,
        title=draft.title,
        current_version_number=draft.current_version_number,
        created_by_user_id=draft.created_by_user_id,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        versions=[_version_read(db, version) for version in versions],
    )


@router.get("", response_model=NarrativeDraftDetail | None)
def get_draft(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _require_access(db, project_id, user.id)
    draft = db.scalar(select(NarrativeDraft).where(NarrativeDraft.project_id == project_id))
    return _draft_detail(db, draft) if draft else None


@router.post("/compile", response_model=NarrativeDraftDetail, status_code=status.HTTP_201_CREATED)
def compile_draft(
    project_id: uuid.UUID,
    payload: NarrativeDraftCompile,
    db: DbSession,
    user: CurrentUser,
):
    project = _require_access(db, project_id, user.id, write=True)
    if not payload.sources:
        raise HTTPException(status_code=422, detail="Select at least one contribution revision.")

    revision_ids = [item.revision_id for item in payload.sources]
    if len(set(revision_ids)) != len(revision_ids):
        raise HTTPException(status_code=422, detail="A contribution revision can only be selected once.")

    revisions = db.scalars(
        select(ContributionRevision)
        .join(StoryContribution, StoryContribution.id == ContributionRevision.contribution_id)
        .where(
            ContributionRevision.id.in_(revision_ids),
            StoryContribution.project_id == project_id,
            StoryContribution.status == "active",
        )
    ).all()
    revisions_by_id = {revision.id: revision for revision in revisions}
    if len(revisions_by_id) != len(revision_ids):
        raise HTTPException(status_code=422, detail="One or more selected revisions are missing, withdrawn, or outside this project.")

    selected_sources: list[tuple[str, str, str, uuid.UUID, uuid.UUID, uuid.UUID | None]] = []
    suggestion_ids = [suggestion_id for item in payload.sources for suggestion_id in item.accepted_suggestion_ids]
    if len(set(suggestion_ids)) != len(suggestion_ids):
        raise HTTPException(status_code=422, detail="An accepted suggestion can only be selected once.")

    for item in payload.sources:
        revision = revisions_by_id[item.revision_id]
        contribution = db.get(StoryContribution, revision.contribution_id)
        selected_sources.append((
            revision.title, revision.body, "contribution",
            contribution.id, revision.id, None,
        ))

        if item.accepted_suggestion_ids:
            suggestions = db.scalars(
                select(StorySuggestion).where(
                    StorySuggestion.id.in_(item.accepted_suggestion_ids),
                    StorySuggestion.contribution_id == contribution.id,
                    StorySuggestion.target_revision_id == revision.id,
                    StorySuggestion.status == "accepted",
                )
            ).all()
            suggestions_by_id = {suggestion.id: suggestion for suggestion in suggestions}
            if len(suggestions_by_id) != len(item.accepted_suggestion_ids):
                raise HTTPException(
                    status_code=422,
                    detail="Suggestions must be accepted and anchored to the selected contribution revision.",
                )
            for suggestion_id in item.accepted_suggestion_ids:
                suggestion = suggestions_by_id[suggestion_id]
                selected_sources.append((
                    suggestion.title, suggestion.proposed_text, "accepted_suggestion",
                    contribution.id, revision.id, suggestion.id,
                ))

    title = (payload.title or project.title).strip()
    compiler_sources = [
        CompilerSource(title=source[0], text=source[1], source_kind=source[2])
        for source in selected_sources
    ]
    output = get_narrative_compiler().compile(title=title, sources=compiler_sources)

    # Locking the project also serializes the first compilation, when no draft
    # row exists yet and there is therefore no draft row available to lock.
    db.scalar(select(Project).where(Project.id == project_id).with_for_update())
    draft = db.scalar(
        select(NarrativeDraft).where(NarrativeDraft.project_id == project_id).with_for_update()
    )
    if draft is None:
        draft = NarrativeDraft(
            project_id=project_id, title=title,
            created_by_user_id=user.id, current_version_number=0,
        )
        db.add(draft)
        db.flush()

    next_number = draft.current_version_number + 1
    previous = db.scalar(
        select(NarrativeDraftVersion)
        .where(NarrativeDraftVersion.draft_id == draft.id)
        .order_by(NarrativeDraftVersion.version_number.desc())
        .limit(1)
    )
    version = NarrativeDraftVersion(
        draft_id=draft.id,
        version_number=next_number,
        title=title,
        content=output.content,
        status="proposal",
        origin="compiled",
        provider_name=output.provider_name,
        model_name=output.model_name,
        prompt_version=output.prompt_version,
        author_user_id=user.id,
        parent_version_id=previous.id if previous else None,
    )
    db.add(version)
    db.flush()
    for index, source in enumerate(selected_sources, start=1):
        source_title, source_text, source_kind, contribution_id, revision_id, suggestion_id = source
        db.add(DraftSourceReference(
            version_id=version.id,
            source_order=index,
            source_kind=source_kind,
            contribution_id=contribution_id,
            contribution_revision_id=revision_id,
            suggestion_id=suggestion_id,
            source_title=source_title,
            source_text_snapshot=source_text,
        ))
    draft.title = title
    draft.current_version_number = next_number
    db.commit()
    db.refresh(draft)
    return _draft_detail(db, draft)


@router.post("/{draft_id}/versions", response_model=NarrativeDraftDetail, status_code=status.HTTP_201_CREATED)
def create_manual_version(
    project_id: uuid.UUID,
    draft_id: uuid.UUID,
    payload: NarrativeDraftVersionCreate,
    db: DbSession,
    user: CurrentUser,
):
    _require_access(db, project_id, user.id, write=True)
    draft = db.scalar(
        select(NarrativeDraft)
        .where(NarrativeDraft.id == draft_id, NarrativeDraft.project_id == project_id)
        .with_for_update()
    )
    if draft is None:
        raise HTTPException(status_code=404, detail="Narrative draft not found.")

    base = db.get(NarrativeDraftVersion, payload.base_version_id)
    if base is None or base.draft_id != draft.id:
        raise HTTPException(status_code=404, detail="Base draft version not found.")
    if base.version_number != draft.current_version_number:
        raise HTTPException(
            status_code=409,
            detail="This draft has a newer version. Reload it before saving your changes.",
        )

    version = NarrativeDraftVersion(
        draft_id=draft.id,
        version_number=draft.current_version_number + 1,
        title=(payload.title or base.title).strip(),
        content=payload.content.strip(),
        status="proposal",
        origin="manual",
        provider_name=None,
        model_name=None,
        prompt_version=None,
        author_user_id=user.id,
        parent_version_id=base.id,
    )
    db.add(version)
    db.flush()

    previous_sources = db.scalars(
        select(DraftSourceReference)
        .where(DraftSourceReference.version_id == base.id)
        .order_by(DraftSourceReference.source_order)
    ).all()
    for source in previous_sources:
        db.add(DraftSourceReference(
            version_id=version.id,
            source_order=source.source_order,
            source_kind=source.source_kind,
            contribution_id=source.contribution_id,
            contribution_revision_id=source.contribution_revision_id,
            suggestion_id=source.suggestion_id,
            source_title=source.source_title,
            source_text_snapshot=source.source_text_snapshot,
        ))

    draft.title = version.title
    draft.current_version_number = version.version_number
    db.commit()
    db.refresh(draft)
    return _draft_detail(db, draft)
