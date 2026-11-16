"""Project-scoped GLB/GLTF asset library and character/location bindings."""
import hashlib
import json
import os
import struct
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import ProductionAsset, ProductionAssetBinding, ProjectCharacter, ProjectLocation
from .projects import CurrentUser, DbSession, _membership, _project_or_404
from .schemas import ProductionAssetBindingRead, ProductionAssetRead, ProductionAssetUpload

router = APIRouter(prefix="/api/projects/{project_id}/production-assets", tags=["production assets"])

MAX_ASSET_BYTES = 250 * 1024 * 1024
MAX_GLTF_JSON_BYTES = 25 * 1024 * 1024
GLB_MAGIC = b"glTF"
GLB_JSON_CHUNK = 0x4E4F534A


def _asset_root() -> Path:
    return Path(os.getenv("STORYFORGE_ASSET_DIR", "/app/storage/assets")).resolve()


def _asset_path(storage_key: str) -> Path:
    root = _asset_root()
    candidate = (root / storage_key).resolve()
    if root not in candidate.parents:
        raise HTTPException(status_code=500, detail="Invalid asset storage key.")
    return candidate


def _project_access(db: Session, project_id: uuid.UUID, user_id: uuid.UUID, *, write: bool = False):
    project = _project_or_404(db, project_id)
    member = _membership(db, project_id, user_id)
    if write and member.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot modify production assets.")
    if write and project.current_phase == "published":
        raise HTTPException(status_code=409, detail="Production assets are read-only after publication.")
    return project


def _asset_or_404(db: Session, project_id: uuid.UUID, asset_id: uuid.UUID) -> ProductionAsset:
    asset = db.scalar(select(ProductionAsset).where(
        ProductionAsset.id == asset_id,
        ProductionAsset.project_id == project_id,
    ))
    if asset is None:
        raise HTTPException(status_code=404, detail="Production asset not found in this project.")
    return asset


def _read(asset: ProductionAsset) -> ProductionAssetRead:
    return ProductionAssetRead(
        id=asset.id, project_id=asset.project_id, asset_kind=asset.asset_kind,
        name=asset.name, description=asset.description,
        original_filename=asset.original_filename, file_format=asset.file_format,
        content_type=asset.content_type, size_bytes=asset.size_bytes,
        sha256=asset.sha256, version=asset.version, gltf_version=asset.gltf_version,
        metadata_json=asset.metadata_json or {}, status=asset.status,
        download_url=f"/api/projects/{asset.project_id}/production-assets/{asset.id}/download",
        created_by_user_id=asset.created_by_user_id, created_at=asset.created_at,
    )


def _inspect_glb(data: bytes) -> dict:
    if len(data) < 20 or data[:4] != GLB_MAGIC:
        raise HTTPException(status_code=415, detail="The uploaded GLB file has an invalid glTF binary header.")
    version, declared_length = struct.unpack_from("<II", data, 4)
    if version != 2 or declared_length != len(data):
        raise HTTPException(status_code=422, detail="Only valid glTF 2.0 GLB files are supported.")
    chunk_length, chunk_type = struct.unpack_from("<II", data, 12)
    if chunk_type != GLB_JSON_CHUNK or chunk_length > MAX_GLTF_JSON_BYTES or 20 + chunk_length > len(data):
        raise HTTPException(status_code=422, detail="The GLB must begin with a bounded JSON metadata chunk.")
    try:
        document = json.loads(data[20:20 + chunk_length].decode("utf-8").rstrip(" \x00 "))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=422, detail="The GLB JSON chunk is invalid.")
    return _validate_gltf_document(document)


def _inspect_gltf(data: bytes) -> dict:
    if len(data) > MAX_GLTF_JSON_BYTES:
        raise HTTPException(status_code=413, detail="The GLTF JSON document exceeds the 25 MiB limit.")
    try:
        document = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=422, detail="The GLTF file must contain valid UTF-8 JSON.")
    return _validate_gltf_document(document)


def _validate_gltf_document(document: object) -> dict:
    if not isinstance(document, dict) or not isinstance(document.get("asset"), dict):
        raise HTTPException(status_code=422, detail="The file is not a valid glTF document.")
    version = document["asset"].get("version")
    if version != "2.0":
        raise HTTPException(status_code=422, detail="Only glTF 2.0 assets are supported.")
    # A single-file library cannot safely resolve arbitrary external paths or URLs.
    for collection in ("buffers", "images"):
        for item in document.get(collection, []):
            uri = item.get("uri") if isinstance(item, dict) else None
            if uri and not uri.startswith("data:"):
                raise HTTPException(status_code=422, detail="External GLTF resources are not accepted. Embed buffers and images as data URIs or upload a self-contained GLB.")
    return {
        "scene_count": len(document.get("scenes", [])),
        "node_count": len(document.get("nodes", [])),
        "mesh_count": len(document.get("meshes", [])),
        "material_count": len(document.get("materials", [])),
        "animation_count": len(document.get("animations", [])),
        "has_skins": bool(document.get("skins")),
    }


def _validate_target(db: Session, project_id: uuid.UUID, kind: str, target_id: uuid.UUID | None):
    if kind == "prop":
        if target_id is not None:
            raise HTTPException(status_code=422, detail="Prop models are library entries and do not bind to a character or location.")
        return
    if target_id is None:
        raise HTTPException(status_code=422, detail=f"A {kind} asset must be assigned to a project {kind}.")
    model = ProjectCharacter if kind == "character" else ProjectLocation
    target = db.scalar(select(model).where(model.id == target_id, model.project_id == project_id, model.status == "active"))
    if target is None:
        raise HTTPException(status_code=404, detail=f"Active {kind} not found in this project.")


@router.get("", response_model=list[ProductionAssetRead])
def list_assets(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id)
    assets = db.scalars(select(ProductionAsset).where(
        ProductionAsset.project_id == project_id,
        ProductionAsset.status == "active",
    ).order_by(ProductionAsset.asset_kind, ProductionAsset.name, ProductionAsset.version.desc())).all()
    return [_read(asset) for asset in assets]


@router.post("", response_model=ProductionAssetRead, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    project_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    name: str = Form(..., min_length=1, max_length=160),
    description: str = Form(default="", max_length=10000),
    asset_kind: str = Form(...),
    target_id: str | None = Form(default=None),
    file: UploadFile = File(...),
):
    _project_access(db, project_id, user.id, write=True)
    name = name.strip()
    description = description.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Asset name cannot be blank.")
    if asset_kind not in ("character", "location", "prop"):
        raise HTTPException(status_code=422, detail="asset_kind must be character, location, or prop.")
    try:
        parsed_target_id = uuid.UUID(target_id) if target_id else None
    except ValueError:
        raise HTTPException(status_code=422, detail="target_id must be a UUID.")
    _validate_target(db, project_id, asset_kind, parsed_target_id)
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()
    if extension not in (".glb", ".gltf"):
        raise HTTPException(status_code=415, detail="Only .glb and .gltf files are supported.")
    chunks = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_ASSET_BYTES:
            raise HTTPException(status_code=413, detail="3D assets are limited to 250 MiB.")
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise HTTPException(status_code=422, detail="The uploaded asset is empty.")
    metadata = _inspect_glb(data) if extension == ".glb" else _inspect_gltf(data)
    digest = hashlib.sha256(data).hexdigest()
    existing_version = db.scalar(select(func.max(ProductionAsset.version)).where(
        ProductionAsset.project_id == project_id,
        ProductionAsset.asset_kind == asset_kind,
        ProductionAsset.name == name,
    )) or 0
    asset_id = uuid.uuid4()
    storage_key = f"{project_id}/{asset_id}.{extension[1:]}"
    destination = _asset_path(storage_key)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    asset = ProductionAsset(
        id=asset_id, project_id=project_id, asset_kind=asset_kind, name=name,
        description=description, original_filename=filename,
        file_format=extension[1:], content_type="model/gltf-binary" if extension == ".glb" else "model/gltf+json",
        size_bytes=len(data), sha256=digest, storage_key=storage_key,
        version=existing_version + 1, metadata_json=metadata, created_by_user_id=user.id,
    )
    try:
        db.add(asset)
        db.flush()
        if asset_kind in ("character", "location"):
            binding = db.scalar(select(ProductionAssetBinding).where(
                ProductionAssetBinding.project_id == project_id,
                ProductionAssetBinding.target_type == asset_kind,
                ProductionAssetBinding.target_id == parsed_target_id,
            ))
            if binding:
                binding.asset_id = asset.id
                binding.updated_by_user_id = user.id
            else:
                db.add(ProductionAssetBinding(
                    project_id=project_id, asset_id=asset.id, target_type=asset_kind,
                    target_id=parsed_target_id, updated_by_user_id=user.id,
                ))
        db.commit()
        db.refresh(asset)
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise
    return _read(asset)


@router.get("/bindings", response_model=list[ProductionAssetBindingRead])
def list_bindings(project_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id)
    bindings = db.scalars(select(ProductionAssetBinding).where(
        ProductionAssetBinding.project_id == project_id,
    ).order_by(ProductionAssetBinding.target_type, ProductionAssetBinding.target_id)).all()
    result = []
    for binding in bindings:
        asset = _asset_or_404(db, project_id, binding.asset_id)
        result.append(ProductionAssetBindingRead(
            id=binding.id, project_id=binding.project_id, asset_id=binding.asset_id,
            target_type=binding.target_type, target_id=binding.target_id,
            updated_by_user_id=binding.updated_by_user_id, updated_at=binding.updated_at,
            asset=_read(asset),
        ))
    return result


@router.delete("/{asset_id}/binding", status_code=status.HTTP_204_NO_CONTENT)
def remove_binding(project_id: uuid.UUID, asset_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id, write=True)
    asset = _asset_or_404(db, project_id, asset_id)
    binding = db.scalar(select(ProductionAssetBinding).where(
        ProductionAssetBinding.project_id == project_id,
        ProductionAssetBinding.asset_id == asset.id,
    ))
    if binding:
        db.delete(binding)
        db.commit()
    return None


@router.get("/{asset_id}", response_model=ProductionAssetRead)
def get_asset(project_id: uuid.UUID, asset_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id)
    return _read(_asset_or_404(db, project_id, asset_id))


@router.get("/{asset_id}/download")
def download_asset(project_id: uuid.UUID, asset_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id)
    asset = _asset_or_404(db, project_id, asset_id)
    if asset.status != "active":
        raise HTTPException(status_code=404, detail="Production asset not found.")
    path = _asset_path(asset.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Asset file is missing from storage.")
    return FileResponse(path, media_type=asset.content_type, filename=asset.original_filename)


@router.patch("/{asset_id}/archive", response_model=ProductionAssetRead)
def archive_asset(project_id: uuid.UUID, asset_id: uuid.UUID, db: DbSession, user: CurrentUser):
    _project_access(db, project_id, user.id, write=True)
    asset = _asset_or_404(db, project_id, asset_id)
    binding = db.scalar(select(ProductionAssetBinding.id).where(ProductionAssetBinding.asset_id == asset.id))
    if binding:
        raise HTTPException(status_code=409, detail="Unassign the asset before archiving it.")
    asset.status = "archived"
    db.commit()
    db.refresh(asset)
    return _read(asset)
