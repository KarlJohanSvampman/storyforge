"""Project-scoped immutable GLB/GLTF production assets and bindings."""
from alembic import op
import sqlalchemy as sa

revision = "0021_production_asset_library"
down_revision = "0020_headless_3d_renderer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "production_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("asset_kind", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("file_format", sa.String(length=8), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("gltf_version", sa.String(length=20), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.CheckConstraint("asset_kind IN ('character', 'location', 'prop')", name="ck_production_assets_kind"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_production_assets_status"),
        sa.CheckConstraint("version >= 1", name="ck_production_assets_version"),
        sa.CheckConstraint("size_bytes > 0", name="ck_production_assets_size"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "asset_kind", "name", "version", name="uq_production_assets_version"),
        sa.UniqueConstraint("storage_key", name="uq_production_assets_storage_key"),
    )
    op.create_index("ix_production_assets_project_id", "production_assets", ["project_id"])
    op.create_index("ix_production_assets_project_created", "production_assets", ["project_id", "created_at"])

    op.create_table(
        "production_asset_bindings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.CheckConstraint("target_type IN ('character', 'location')", name="ck_production_asset_bindings_target"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["production_assets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "target_type", "target_id", name="uq_production_asset_bindings_target"),
    )
    op.create_index("ix_production_asset_bindings_project_id", "production_asset_bindings", ["project_id"])
    op.create_index("ix_production_asset_bindings_asset_id", "production_asset_bindings", ["asset_id"])


def downgrade() -> None:
    op.drop_index("ix_production_asset_bindings_asset_id", table_name="production_asset_bindings")
    op.drop_index("ix_production_asset_bindings_project_id", table_name="production_asset_bindings")
    op.drop_table("production_asset_bindings")
    op.drop_index("ix_production_assets_project_created", table_name="production_assets")
    op.drop_index("ix_production_assets_project_id", table_name="production_assets")
    op.drop_table("production_assets")
