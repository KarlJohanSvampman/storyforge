"""Collaborative, append-only humanoid rig profiles for character asset versions."""
import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from .models import ProductionAssetRigProfile
from .production_assets import _asset_or_404, _project_access
from .projects import CurrentUser, DbSession
from .schemas import HumanoidRigProfileRead, HumanoidRigProfileSave

router = APIRouter(
    prefix="/api/projects/{project_id}/production-assets",
    tags=["production asset rig profiles"],
)


def _read_profile(asset, row: ProductionAssetRigProfile) -> HumanoidRigProfileRead:
    return HumanoidRigProfileRead(
        asset_id=asset.id,
        asset_version=asset.version,
        revision=row.revision,
        rig_signature=row.rig_signature,
        profile=row.profile_json,
        updated_by_user_id=row.updated_by_user_id,
        updated_at=row.created_at,
    )


def _latest(db, asset_id: uuid.UUID) -> ProductionAssetRigProfile | None:
    return db.scalar(
        select(ProductionAssetRigProfile)
        .where(ProductionAssetRigProfile.asset_id == asset_id)
        .order_by(ProductionAssetRigProfile.revision.desc())
        .limit(1)
    )


def _character_asset(db, project_id: uuid.UUID, asset_id: uuid.UUID):
    asset = _asset_or_404(db, project_id, asset_id)
    if asset.asset_kind != "character":
        raise HTTPException(status_code=422, detail="Rig profiles can only be attached to character assets.")
    return asset


@router.get("/{asset_id}/rig-profile", response_model=HumanoidRigProfileRead | None)
def get_rig_profile(project_id: uuid.UUID, asset_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id)
    asset = _character_asset(db, project_id, asset_id)
    row = _latest(db, asset.id)
    return _read_profile(asset, row) if row else None


@router.get("/{asset_id}/rig-profile/versions", response_model=list[HumanoidRigProfileRead])
def list_rig_profile_versions(project_id: uuid.UUID, asset_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id)
    asset = _character_asset(db, project_id, asset_id)
    rows = db.scalars(
        select(ProductionAssetRigProfile)
        .where(ProductionAssetRigProfile.asset_id == asset.id)
        .order_by(ProductionAssetRigProfile.revision.desc())
        .limit(100)
    ).all()
    return [_read_profile(asset, row) for row in rows]


@router.put("/{asset_id}/rig-profile", response_model=HumanoidRigProfileRead)
def save_rig_profile(
    project_id: uuid.UUID,
    asset_id: uuid.UUID,
    payload: HumanoidRigProfileSave,
    db: DbSession,
    user: CurrentUser,
):
    _project_access(db, project_id, user.id, write=True)
    asset = _character_asset(db, project_id, asset_id)
    if asset.status != "active":
        raise HTTPException(status_code=409, detail="Archived character assets cannot receive rig profile changes.")

    latest = _latest(db, asset.id)
    current_revision = latest.revision if latest else 0
    if payload.expected_revision != current_revision:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Rig profile changed since it was loaded. Reload the latest revision before saving.",
                "current_revision": current_revision,
            },
        )

    row = ProductionAssetRigProfile(
        asset_id=asset.id,
        revision=current_revision + 1,
        rig_signature=payload.rig_signature,
        profile_json=payload.profile.model_dump(by_alias=True, exclude_none=True),
        updated_by_user_id=user.id,
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        latest = _latest(db, asset.id)
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Another collaborator saved a rig profile at the same time. Reload the latest revision before saving.",
                "current_revision": latest.revision if latest else 0,
            },
        )
    return _read_profile(asset, row)
