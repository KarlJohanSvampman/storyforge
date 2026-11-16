"""Add persistent video assets and server-side MP4 render jobs."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0018_video_render_pipeline"
down_revision = "0017_audio_render_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "video_render_jobs",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("project_id", uuid, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_id", uuid, sa.ForeignKey("edit_sequences.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="queued", nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("source_filename", sa.String(255), nullable=False),
        sa.Column("input_storage_key", sa.String(500), nullable=False),
        sa.Column("input_size_bytes", sa.Integer(), nullable=False),
        sa.Column("input_sha256", sa.String(64), nullable=False),
        sa.Column("input_content_type", sa.String(100), nullable=False),
        sa.Column("expected_duration_ms", sa.Integer(), nullable=False),
        sa.Column("output_size_bytes", sa.Integer(), nullable=True),
        sa.Column("output_sha256", sa.String(64), nullable=True),
        sa.Column("output_storage_key", sa.String(500), nullable=True),
        sa.Column("output_content_type", sa.String(100), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), server_default="", nullable=False),
        sa.Column("created_by_user_id", uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('queued', 'running', 'completed', 'failed')", name="ck_video_render_jobs_status"),
        sa.CheckConstraint("input_size_bytes > 0", name="ck_video_render_jobs_input_size"),
        sa.CheckConstraint("output_size_bytes IS NULL OR output_size_bytes > 0", name="ck_video_render_jobs_output_size"),
        sa.CheckConstraint("expected_duration_ms > 0", name="ck_video_render_jobs_expected_duration"),
    )
    op.create_index("ix_video_render_jobs_project_id", "video_render_jobs", ["project_id"])
    op.create_index("ix_video_render_jobs_sequence_id", "video_render_jobs", ["sequence_id"])
    op.create_index("ix_video_render_jobs_project_created", "video_render_jobs", ["project_id", "created_at"])
    op.create_index("ix_video_render_jobs_status_created", "video_render_jobs", ["status", "created_at"])

    op.create_table(
        "production_video_assets",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("project_id", uuid, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_id", uuid, sa.ForeignKey("edit_sequences.id", ondelete="CASCADE"), nullable=False),
        sa.Column("render_job_id", uuid, sa.ForeignKey("video_render_jobs.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("sequence_revision", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), server_default="video/mp4", nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False, unique=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("created_by_user_id", uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("size_bytes > 0", name="ck_production_video_assets_size"),
        sa.CheckConstraint("duration_ms > 0", name="ck_production_video_assets_duration"),
        sa.CheckConstraint("width > 0 AND height > 0", name="ck_production_video_assets_dimensions"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_production_video_assets_status"),
    )
    op.create_index("ix_production_video_assets_project_id", "production_video_assets", ["project_id"])
    op.create_index("ix_production_video_assets_sequence_id", "production_video_assets", ["sequence_id"])
    op.create_index("ix_production_video_assets_sha256", "production_video_assets", ["sha256"])
    op.create_index("ix_production_video_assets_project_created", "production_video_assets", ["project_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_production_video_assets_project_created", table_name="production_video_assets")
    op.drop_index("ix_production_video_assets_sha256", table_name="production_video_assets")
    op.drop_index("ix_production_video_assets_sequence_id", table_name="production_video_assets")
    op.drop_index("ix_production_video_assets_project_id", table_name="production_video_assets")
    op.drop_table("production_video_assets")
    op.drop_index("ix_video_render_jobs_status_created", table_name="video_render_jobs")
    op.drop_index("ix_video_render_jobs_project_created", table_name="video_render_jobs")
    op.drop_index("ix_video_render_jobs_sequence_id", table_name="video_render_jobs")
    op.drop_index("ix_video_render_jobs_project_id", table_name="video_render_jobs")
    op.drop_table("video_render_jobs")
