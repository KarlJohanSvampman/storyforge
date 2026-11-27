"""Versioned humanoid rig profiles for immutable character asset versions."""
from alembic import op
import sqlalchemy as sa

revision = "0029_production_asset_rig_profiles"
down_revision = "0028_performance_capture_chunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "production_asset_rig_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("rig_signature", sa.String(length=128), nullable=True),
        sa.Column("profile_json", sa.JSON(), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("revision >= 1", name="ck_production_asset_rig_profiles_revision"),
        sa.ForeignKeyConstraint(["asset_id"], ["production_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "revision", name="uq_production_asset_rig_profiles_revision"),
    )
    op.create_index(
        "ix_production_asset_rig_profiles_asset_id",
        "production_asset_rig_profiles", ["asset_id"],
    )
    op.create_index(
        "ix_production_asset_rig_profiles_asset_created",
        "production_asset_rig_profiles", ["asset_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_production_asset_rig_profiles_asset_created", table_name="production_asset_rig_profiles")
    op.drop_index("ix_production_asset_rig_profiles_asset_id", table_name="production_asset_rig_profiles")
    op.drop_table("production_asset_rig_profiles")
