"""Add immutable published release snapshots."""

from alembic import op
import sqlalchemy as sa

revision = "0023_published_releases"
down_revision = "0022_production_asset_transforms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "published_releases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("release_number", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("synopsis", sa.Text(), server_default="", nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("storyboard_id", sa.Uuid(), nullable=False),
        sa.Column("narrative_version_id", sa.Uuid(), nullable=False),
        sa.Column("video_asset_id", sa.Uuid(), nullable=False),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column("published_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("release_number >= 1", name="ck_published_releases_positive_number"),
        sa.CheckConstraint("visibility IN ('private', 'unlisted', 'public')", name="ck_published_releases_visibility"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["storyboard_id"], ["storyboards.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["narrative_version_id"], ["narrative_draft_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["video_asset_id"], ["production_video_assets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["published_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "release_number", name="uq_published_releases_project_number"),
        sa.UniqueConstraint("slug", name="uq_published_releases_slug"),
    )
    op.create_index("ix_published_releases_project_id", "published_releases", ["project_id"])
    op.create_index("ix_published_releases_project_published", "published_releases", ["project_id", "published_at"])


def downgrade() -> None:
    op.drop_index("ix_published_releases_project_published", table_name="published_releases")
    op.drop_index("ix_published_releases_project_id", table_name="published_releases")
    op.drop_table("published_releases")
