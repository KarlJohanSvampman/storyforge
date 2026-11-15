import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    DocumentaryClaim,
    DocumentaryClaimEvidence,
    DocumentaryClaimReview,
    DocumentaryResearchSource,
    Project,
    User,
)
from .projects import CurrentUser, DbSession, _membership, _project_or_404
from .schemas import (
    DocumentaryClaimCreate,
    DocumentaryClaimEvidenceCreate,
    DocumentaryClaimEvidenceRead,
    DocumentaryClaimRead,
    DocumentaryClaimReviewCreate,
    DocumentaryClaimReviewRead,
    DocumentaryClaimUpdate,
    DocumentaryResearchOverview,
    DocumentarySourceCreate,
    DocumentarySourceRead,
    DocumentarySourceUpdate,
)

router = APIRouter(prefix="/api/projects/{project_id}/documentary", tags=["documentary research"])


def _require_documentary_project(
    db: Session,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    write: bool = False,
) -> Project:
    project = _project_or_404(db, project_id)
    membership = _membership(db, project_id, user_id)
    if project.category != "documentary":
        raise HTTPException(status_code=409, detail="Research registers and fact-checking are available for documentary projects only.")
    if write:
        if membership.role == "viewer":
            raise HTTPException(status_code=403, detail="Viewers cannot edit documentary research.")
        if project.current_phase == "published":
            raise HTTPException(status_code=409, detail="Documentary research is read-only after publication.")
    return project


def _source_or_404(db: Session, project_id: uuid.UUID, source_id: uuid.UUID) -> DocumentaryResearchSource:
    source = db.scalar(select(DocumentaryResearchSource).where(
        DocumentaryResearchSource.id == source_id,
        DocumentaryResearchSource.project_id == project_id,
    ))
    if source is None:
        raise HTTPException(status_code=404, detail="Research source not found in this project.")
    return source


def _claim_or_404(db: Session, project_id: uuid.UUID, claim_id: uuid.UUID) -> DocumentaryClaim:
    claim = db.scalar(select(DocumentaryClaim).where(
        DocumentaryClaim.id == claim_id,
        DocumentaryClaim.project_id == project_id,
    ))
    if claim is None:
        raise HTTPException(status_code=404, detail="Documentary claim not found in this project.")
    return claim


def _documentary_detail(db: Session, project_id: uuid.UUID) -> DocumentaryResearchOverview:
    sources = db.scalars(
        select(DocumentaryResearchSource)
        .where(DocumentaryResearchSource.project_id == project_id)
        .order_by(DocumentaryResearchSource.created_at, DocumentaryResearchSource.id)
    ).all()
    claims = db.scalars(
        select(DocumentaryClaim)
        .where(DocumentaryClaim.project_id == project_id)
        .order_by(DocumentaryClaim.created_at, DocumentaryClaim.id)
    ).all()

    claim_reads: list[DocumentaryClaimRead] = []
    for claim in claims:
        author = db.get(User, claim.created_by_user_id)
        evidence_rows = db.scalars(
            select(DocumentaryClaimEvidence)
            .where(DocumentaryClaimEvidence.claim_id == claim.id)
            .order_by(DocumentaryClaimEvidence.created_at, DocumentaryClaimEvidence.id)
        ).all()
        evidence_reads = []
        for item in evidence_rows:
            source = db.get(DocumentaryResearchSource, item.source_id)
            if source is None:
                continue
            evidence_reads.append(DocumentaryClaimEvidenceRead(
                id=item.id,
                source_id=source.id,
                source_title=source.title,
                source_type=source.source_type,
                source_url=source.url,
                source_status=source.status,
                evidence_relation=item.evidence_relation,
                excerpt=item.excerpt,
                locator=item.locator,
                notes=item.notes,
                created_by_user_id=item.created_by_user_id,
                created_at=item.created_at,
            ))

        review_rows = db.scalars(
            select(DocumentaryClaimReview)
            .where(DocumentaryClaimReview.claim_id == claim.id)
            .order_by(DocumentaryClaimReview.created_at, DocumentaryClaimReview.id)
        ).all()
        review_reads = []
        for item in review_rows:
            reviewer = db.get(User, item.reviewer_user_id)
            review_reads.append(DocumentaryClaimReviewRead(
                id=item.id,
                previous_status=item.previous_status,
                result=item.result,
                rationale=item.rationale,
                reviewed_evidence_snapshot=item.reviewed_evidence_snapshot or [],
                reviewer_user_id=item.reviewer_user_id,
                reviewer_display_name=reviewer.display_name if reviewer else "Unknown reviewer",
                created_at=item.created_at,
            ))

        claim_reads.append(DocumentaryClaimRead(
            id=claim.id,
            project_id=claim.project_id,
            statement=claim.statement,
            context=claim.context,
            origin=claim.origin,
            status=claim.status,
            current_review_status=claim.current_review_status,
            created_by_user_id=claim.created_by_user_id,
            created_by_display_name=author.display_name if author else "Unknown participant",
            created_at=claim.created_at,
            updated_at=claim.updated_at,
            evidence=evidence_reads,
            reviews=review_reads,
        ))

    return DocumentaryResearchOverview(
        project_id=project_id,
        sources=[DocumentarySourceRead.model_validate(item, from_attributes=True) for item in sources],
        claims=claim_reads,
    )


@router.get("", response_model=DocumentaryResearchOverview)
def get_documentary_research(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _require_documentary_project(db, project_id, user.id)
    return _documentary_detail(db, project_id)


@router.post("/sources", response_model=DocumentaryResearchOverview, status_code=status.HTTP_201_CREATED)
def create_research_source(project_id: uuid.UUID, payload: DocumentarySourceCreate, db: DbSession, user: CurrentUser):
    _require_documentary_project(db, project_id, user.id, write=True)
    source = DocumentaryResearchSource(
        project_id=project_id,
        title=payload.title,
        source_type=payload.source_type,
        creator=payload.creator,
        publisher=payload.publisher,
        publication_date=payload.publication_date,
        url=payload.url,
        citation_text=payload.citation_text,
        research_notes=payload.research_notes,
        created_by_user_id=user.id,
    )
    db.add(source)
    db.commit()
    return _documentary_detail(db, project_id)


@router.patch("/sources/{source_id}", response_model=DocumentaryResearchOverview)
def update_research_source(
    project_id: uuid.UUID,
    source_id: uuid.UUID,
    payload: DocumentarySourceUpdate,
    db: DbSession,
    user: CurrentUser,
):
    _require_documentary_project(db, project_id, user.id, write=True)
    source = db.scalar(select(DocumentaryResearchSource).where(
        DocumentaryResearchSource.id == source_id,
        DocumentaryResearchSource.project_id == project_id,
    ).with_for_update())
    if source is None:
        raise HTTPException(status_code=404, detail="Research source not found in this project.")
    values = payload.model_dump(exclude_unset=True)
    for key, value in values.items():
        if value is not None or key == "url":
            setattr(source, key, value)

    # Changing metadata or archiving a source invalidates any current claim
    # review that relied on it. Previous review events and evidence snapshots
    # remain intact for audit.
    claim_ids = db.scalars(
        select(DocumentaryClaimEvidence.claim_id)
        .where(DocumentaryClaimEvidence.source_id == source.id)
    ).all()
    distinct_claim_ids = set(claim_ids)
    if distinct_claim_ids:
        linked_claims = db.scalars(
            select(DocumentaryClaim)
            .where(DocumentaryClaim.id.in_(distinct_claim_ids))
            .with_for_update()
        ).all()
        for claim in linked_claims:
            if claim.current_review_status != "unreviewed":
                claim.current_review_status = "needs_review"
    db.commit()
    return _documentary_detail(db, project_id)


@router.post("/claims", response_model=DocumentaryResearchOverview, status_code=status.HTTP_201_CREATED)
def create_documentary_claim(project_id: uuid.UUID, payload: DocumentaryClaimCreate, db: DbSession, user: CurrentUser):
    _require_documentary_project(db, project_id, user.id, write=True)
    claim = DocumentaryClaim(
        project_id=project_id,
        statement=payload.statement,
        context=payload.context,
        origin=payload.origin,
        created_by_user_id=user.id,
    )
    db.add(claim)
    db.commit()
    return _documentary_detail(db, project_id)


@router.patch("/claims/{claim_id}", response_model=DocumentaryResearchOverview)
def update_documentary_claim(
    project_id: uuid.UUID,
    claim_id: uuid.UUID,
    payload: DocumentaryClaimUpdate,
    db: DbSession,
    user: CurrentUser,
):
    _require_documentary_project(db, project_id, user.id, write=True)
    claim = _claim_or_404(db, project_id, claim_id)
    claim.status = payload.status
    db.commit()
    return _documentary_detail(db, project_id)


@router.post("/claims/{claim_id}/evidence", response_model=DocumentaryResearchOverview, status_code=status.HTTP_201_CREATED)
def add_claim_evidence(
    project_id: uuid.UUID,
    claim_id: uuid.UUID,
    payload: DocumentaryClaimEvidenceCreate,
    db: DbSession,
    user: CurrentUser,
):
    _require_documentary_project(db, project_id, user.id, write=True)
    claim = db.scalar(select(DocumentaryClaim).where(
        DocumentaryClaim.id == claim_id,
        DocumentaryClaim.project_id == project_id,
    ).with_for_update())
    if claim is None:
        raise HTTPException(status_code=404, detail="Documentary claim not found in this project.")
    if claim.status != "active":
        raise HTTPException(status_code=409, detail="Archived claims cannot receive new evidence.")
    source = _source_or_404(db, project_id, payload.source_id)
    if source.status != "active":
        raise HTTPException(status_code=409, detail="Archived sources cannot be linked as new evidence.")
    existing = db.scalar(select(DocumentaryClaimEvidence.id).where(
        DocumentaryClaimEvidence.claim_id == claim.id,
        DocumentaryClaimEvidence.source_id == source.id,
    ))
    if existing:
        raise HTTPException(status_code=409, detail="This source is already linked to the claim. Each source may be linked once per claim.")

    db.add(DocumentaryClaimEvidence(
        claim_id=claim.id,
        source_id=source.id,
        evidence_relation=payload.evidence_relation,
        excerpt=payload.excerpt,
        locator=payload.locator,
        notes=payload.notes,
        created_by_user_id=user.id,
    ))
    # Any evidence change means the prior review may no longer be current.
    if claim.current_review_status != "unreviewed":
        claim.current_review_status = "needs_review"
    db.commit()
    return _documentary_detail(db, project_id)


@router.post("/claims/{claim_id}/reviews", response_model=DocumentaryResearchOverview, status_code=status.HTTP_201_CREATED)
def review_documentary_claim(
    project_id: uuid.UUID,
    claim_id: uuid.UUID,
    payload: DocumentaryClaimReviewCreate,
    db: DbSession,
    user: CurrentUser,
):
    _require_documentary_project(db, project_id, user.id, write=True)
    claim = db.scalar(select(DocumentaryClaim).where(
        DocumentaryClaim.id == claim_id,
        DocumentaryClaim.project_id == project_id,
    ).with_for_update())
    if claim is None:
        raise HTTPException(status_code=404, detail="Documentary claim not found in this project.")
    if claim.status != "active":
        raise HTTPException(status_code=409, detail="Archived claims cannot be reviewed.")

    evidence_rows = db.execute(
        select(DocumentaryClaimEvidence, DocumentaryResearchSource)
        .join(DocumentaryResearchSource, DocumentaryResearchSource.id == DocumentaryClaimEvidence.source_id)
        .where(
            DocumentaryClaimEvidence.claim_id == claim.id,
            DocumentaryResearchSource.status == "active",
        )
        .order_by(DocumentaryClaimEvidence.created_at, DocumentaryClaimEvidence.id)
    ).all()
    relations = {evidence.evidence_relation for evidence, _source in evidence_rows}
    if payload.result == "supported" and "supports" not in relations:
        raise HTTPException(status_code=422, detail="A supported decision requires at least one active source marked as supporting the claim.")
    if payload.result == "contested" and not {"supports", "challenges"}.issubset(relations):
        raise HTTPException(status_code=422, detail="A contested decision requires active evidence that both supports and challenges the claim.")
    if payload.result == "not_supported" and "challenges" not in relations:
        raise HTTPException(status_code=422, detail="A not-supported decision requires at least one active source marked as challenging the claim.")

    snapshot = []
    for evidence, source in evidence_rows:
        snapshot.append({
            "source_id": str(source.id),
            "source_title": source.title,
            "source_type": source.source_type,
            "source_status": source.status,
            "creator": source.creator,
            "publisher": source.publisher,
            "publication_date": source.publication_date,
            "url": source.url,
            "citation_text": source.citation_text,
            "evidence_relation": evidence.evidence_relation,
            "excerpt": evidence.excerpt,
            "locator": evidence.locator,
            "notes": evidence.notes,
        })

    previous = claim.current_review_status
    review = DocumentaryClaimReview(
        claim_id=claim.id,
        previous_status=previous,
        result=payload.result,
        rationale=payload.rationale,
        reviewed_evidence_snapshot=snapshot,
        reviewer_user_id=user.id,
    )
    db.add(review)
    claim.current_review_status = payload.result
    db.commit()
    return _documentary_detail(db, project_id)
