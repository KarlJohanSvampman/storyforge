"""Public-facing release pages and media delivery."""

import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .audio import _safe_path
from .models import ProductionVideoAsset, PublishedRelease
from .projects import DbSession

router = APIRouter(prefix="/api/public/releases", tags=["public releases"])


def _visible_release(db: Session, slug: str) -> PublishedRelease:
    release = db.scalar(select(PublishedRelease).where(PublishedRelease.slug == slug))
    # Private releases are deliberately indistinguishable from missing slugs.
    if release is None or release.visibility == "private":
        raise HTTPException(status_code=404, detail="Release not found.")
    return release


def _public_payload(release: PublishedRelease) -> dict:
    manifest = release.manifest_json or {}
    project = manifest.get("project") or {}
    master = manifest.get("master_video") or {}
    return {
        "slug": release.slug,
        "title": release.title,
        "synopsis": release.synopsis,
        "visibility": release.visibility,
        "published_at": release.published_at,
        "project_title": project.get("title") or release.title,
        "format": project.get("format"),
        "category": project.get("category"),
        "genre": project.get("genre"),
        "duration_ms": master.get("duration_ms"),
        "width": master.get("width"),
        "height": master.get("height"),
        "video_url": f"/api/public/releases/{release.slug}/video",
    }


@router.get("")
def list_public_releases(db: DbSession):
    releases = db.scalars(
        select(PublishedRelease)
        .where(PublishedRelease.visibility == "public")
        .order_by(PublishedRelease.published_at.desc())
        .limit(100)
    ).all()
    return [_public_payload(release) for release in releases]


@router.get("/{slug}/video")
def public_release_video(slug: str, db: DbSession):
    release = _visible_release(db, slug)
    asset = db.get(ProductionVideoAsset, release.video_asset_id)
    if asset is None or asset.status != "active":
        raise HTTPException(status_code=404, detail="Release media not found.")
    path = _safe_path(asset.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Release media not found.")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=f"{release.slug}.mp4",
        headers={"Cache-Control": "public, max-age=3600", "Accept-Ranges": "bytes"},
    )


@router.get("/{slug}")
def get_public_release(slug: str, db: DbSession):
    return _public_payload(_visible_release(db, slug))
