"""Add immutable EDL snapshots and headless video render mode."""
from alembic import op
import sqlalchemy as sa

revision = "0019_headless_video_rendering"
down_revision = "0018_video_render_pipeline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("video_render_jobs", sa.Column("render_mode", sa.String(20), server_default="upload", nullable=False))
    op.add_column("video_render_jobs", sa.Column("render_manifest", sa.JSON(), nullable=True))
    op.alter_column("video_render_jobs", "input_storage_key", existing_type=sa.String(length=500), nullable=True)
    op.alter_column("video_render_jobs", "input_size_bytes", existing_type=sa.Integer(), nullable=True)
    op.alter_column("video_render_jobs", "input_sha256", existing_type=sa.String(length=64), nullable=True)
    op.alter_column("video_render_jobs", "input_content_type", existing_type=sa.String(length=100), nullable=True)
    op.drop_constraint("ck_video_render_jobs_input_size", "video_render_jobs", type_="check")
    op.create_check_constraint(
        "ck_video_render_jobs_render_mode",
        "video_render_jobs",
        "render_mode IN ('upload', 'headless')",
    )
    op.create_check_constraint(
        "ck_video_render_jobs_input_size",
        "video_render_jobs",
        "input_size_bytes IS NULL OR input_size_bytes > 0",
    )
    op.create_check_constraint(
        "ck_video_render_jobs_render_source",
        "video_render_jobs",
        "(render_mode = 'upload' AND input_storage_key IS NOT NULL AND input_size_bytes IS NOT NULL AND input_sha256 IS NOT NULL AND render_manifest IS NULL) OR (render_mode = 'headless' AND input_storage_key IS NULL AND input_size_bytes IS NULL AND input_sha256 IS NULL AND render_manifest IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_video_render_jobs_render_source", "video_render_jobs", type_="check")
    op.drop_constraint("ck_video_render_jobs_input_size", "video_render_jobs", type_="check")
    op.drop_constraint("ck_video_render_jobs_render_mode", "video_render_jobs", type_="check")
    op.create_check_constraint("ck_video_render_jobs_input_size", "video_render_jobs", "input_size_bytes > 0")
    op.alter_column("video_render_jobs", "input_content_type", existing_type=sa.String(length=100), nullable=False)
    op.alter_column("video_render_jobs", "input_sha256", existing_type=sa.String(length=64), nullable=False)
    op.alter_column("video_render_jobs", "input_size_bytes", existing_type=sa.Integer(), nullable=False)
    op.alter_column("video_render_jobs", "input_storage_key", existing_type=sa.String(length=500), nullable=False)
    op.drop_column("video_render_jobs", "render_manifest")
    op.drop_column("video_render_jobs", "render_mode")
