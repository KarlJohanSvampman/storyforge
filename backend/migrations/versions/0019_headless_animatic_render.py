"""Add immutable headless animatic manifests to video render jobs."""
from alembic import op
import sqlalchemy as sa

revision = "0019_headless_animatic_render"
down_revision = "0018_video_render_pipeline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "video_render_jobs",
        sa.Column("render_source", sa.String(30), server_default="webm_upload", nullable=False),
    )
    op.add_column("video_render_jobs", sa.Column("render_manifest", sa.JSON(), nullable=True))
    op.drop_constraint("ck_video_render_jobs_input_size", "video_render_jobs", type_="check")
    op.alter_column("video_render_jobs", "input_storage_key", existing_type=sa.String(500), nullable=True)
    op.alter_column("video_render_jobs", "input_size_bytes", existing_type=sa.Integer(), nullable=True)
    op.alter_column("video_render_jobs", "input_sha256", existing_type=sa.String(64), nullable=True)
    op.alter_column("video_render_jobs", "input_content_type", existing_type=sa.String(100), nullable=True)
    op.create_check_constraint(
        "ck_video_render_jobs_input_size",
        "video_render_jobs",
        "input_size_bytes IS NULL OR input_size_bytes > 0",
    )
    op.create_check_constraint(
        "ck_video_render_jobs_source",
        "video_render_jobs",
        "render_source IN ('webm_upload', 'headless_animatic')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_video_render_jobs_source", "video_render_jobs", type_="check")
    op.drop_constraint("ck_video_render_jobs_input_size", "video_render_jobs", type_="check")
    op.alter_column("video_render_jobs", "input_storage_key", existing_type=sa.String(500), nullable=False)
    op.alter_column("video_render_jobs", "input_size_bytes", existing_type=sa.Integer(), nullable=False)
    op.alter_column("video_render_jobs", "input_sha256", existing_type=sa.String(64), nullable=False)
    op.alter_column("video_render_jobs", "input_content_type", existing_type=sa.String(100), nullable=False)
    op.create_check_constraint(
        "ck_video_render_jobs_input_size", "video_render_jobs", "input_size_bytes > 0"
    )
    op.drop_column("video_render_jobs", "render_manifest")
    op.drop_column("video_render_jobs", "render_source")
