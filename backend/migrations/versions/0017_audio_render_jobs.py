"""Add durable offline audio render jobs."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0017_audio_render_jobs"
down_revision = "0016_audio_pipeline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "audio_render_jobs",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("project_id", uuid, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_id", uuid, sa.ForeignKey("edit_sequences.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="queued", nullable=False),
        sa.Column("render_manifest", sa.JSON(), nullable=False),
        sa.Column("output_storage_key", sa.String(500), nullable=True),
        sa.Column("output_content_type", sa.String(100), nullable=True),
        sa.Column("output_size_bytes", sa.Integer(), nullable=True),
        sa.Column("output_sha256", sa.String(64), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), server_default="", nullable=False),
        sa.Column("created_by_user_id", uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('queued', 'running', 'completed', 'failed')", name="ck_audio_render_jobs_status"),
        sa.CheckConstraint("output_size_bytes IS NULL OR output_size_bytes > 0", name="ck_audio_render_jobs_output_size"),
        sa.CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="ck_audio_render_jobs_duration"),
    )
    op.create_index("ix_audio_render_jobs_project_id", "audio_render_jobs", ["project_id"])
    op.create_index("ix_audio_render_jobs_sequence_id", "audio_render_jobs", ["sequence_id"])
    op.create_index("ix_audio_render_jobs_project_created", "audio_render_jobs", ["project_id", "created_at"])
    op.create_index("ix_audio_render_jobs_status_created", "audio_render_jobs", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audio_render_jobs_status_created", table_name="audio_render_jobs")
    op.drop_index("ix_audio_render_jobs_project_created", table_name="audio_render_jobs")
    op.drop_index("ix_audio_render_jobs_sequence_id", table_name="audio_render_jobs")
    op.drop_index("ix_audio_render_jobs_project_id", table_name="audio_render_jobs")
    op.drop_table("audio_render_jobs")
