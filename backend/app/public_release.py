"""Public-facing release pages and media delivery."""

import hashlib
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
        "poster_url": f"/api/public/releases/{release.slug}/poster" if manifest.get("poster") else None,
        "trailer_url": f"/api/public/releases/{release.slug}/trailer" if manifest.get("trailer_video") else None,
        "credits": [{
            "category": item.get("category"),
            "role_label": item.get("role_label"),
            "public_name": item.get("public_name"),
            "character_name": item.get("character_name"),
        } for item in manifest.get("credits", [])
            if item.get("category") in {"contributor", "cast", "production"}
            and item.get("public_name") and item.get("role_label")],
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



def _verified_snapshot_file(release: PublishedRelease, section: str):
    snapshot = (release.manifest_json or {}).get(section)
    if not isinstance(snapshot, dict) or not snapshot.get("storage_key") or not snapshot.get("sha256"):
        raise HTTPException(status_code=404, detail="Release media not found.")
    path = _safe_path(snapshot["storage_key"])
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Release media not found.")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != snapshot["sha256"]:
        raise HTTPException(status_code=409, detail="Release media failed integrity verification.")
    return path, snapshot


@router.get("/{slug}/poster")
def public_release_poster(slug: str, db: DbSession):
    release = _visible_release(db, slug)
    path, snapshot = _verified_snapshot_file(release, "poster")
    return FileResponse(path, media_type="image/jpeg", filename=f"{release.slug}-poster.jpg",
                        headers={"Cache-Control": "public, max-age=86400"})


@router.get("/{slug}/trailer")
def public_release_trailer(slug: str, db: DbSession):
    release = _visible_release(db, slug)
    path, snapshot = _verified_snapshot_file(release, "trailer_video")
    return FileResponse(path, media_type="video/mp4", filename=f"{release.slug}-trailer.mp4",
                        headers={"Cache-Control": "public, max-age=3600", "Accept-Ranges": "bytes"})


@router.get("/{slug}/video")
def public_release_video(slug: str, db: DbSession):
    release = _visible_release(db, slug)
    asset = db.get(ProductionVideoAsset, release.video_asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Release media not found.")
    path = _safe_path(asset.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Release media not found.")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != asset.sha256:
        raise HTTPException(status_code=409, detail="Release media failed integrity verification.")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=f"{release.slug}.mp4",
        headers={"Cache-Control": "public, max-age=3600", "Accept-Ranges": "bytes"},
    )


@router.get("/{slug}")
def get_public_release(slug: str, db: DbSession):
    return _public_payload(_visible_release(db, slug))
