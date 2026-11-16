"""Add reusable production audio assets, tracks and clips."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0016_audio_pipeline"
down_revision = "0015_performance_playback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "production_media_assets",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("project_id", uuid, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("created_by_user_id", uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("size_bytes > 0", name="ck_production_media_assets_size"),
        sa.CheckConstraint("duration_ms IS NULL OR duration_ms > 0", name="ck_production_media_assets_duration"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_production_media_assets_status"),
        sa.UniqueConstraint("storage_key", name="uq_production_media_assets_storage_key"),
    )
    op.create_index("ix_production_media_assets_project_id", "production_media_assets", ["project_id"])
    op.create_index("ix_production_media_assets_sha256", "production_media_assets", ["sha256"])
    op.create_index("ix_production_media_assets_project_created", "production_media_assets", ["project_id", "created_at"])

    op.create_table(
        "audio_tracks",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("sequence_id", uuid, sa.ForeignKey("edit_sequences.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("role", sa.String(20), server_default="effects", nullable=False),
        sa.Column("track_order", sa.Integer(), nullable=False),
        sa.Column("gain", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("pan", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("muted", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("solo", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_by_user_id", uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("sequence_id", "track_order", name="uq_audio_tracks_sequence_order"),
        sa.CheckConstraint("track_order >= 1", name="ck_audio_tracks_order"),
        sa.CheckConstraint("role IN ('dialogue', 'music', 'effects', 'ambience', 'voiceover')", name="ck_audio_tracks_role"),
        sa.CheckConstraint("gain >= 0 AND gain <= 2", name="ck_audio_tracks_gain"),
        sa.CheckConstraint("pan >= -1 AND pan <= 1", name="ck_audio_tracks_pan"),
    )
    op.create_index("ix_audio_tracks_sequence_id", "audio_tracks", ["sequence_id"])

    op.create_table(
        "audio_clips",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("track_id", uuid, sa.ForeignKey("audio_tracks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_asset_id", uuid, sa.ForeignKey("production_media_assets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("clip_order", sa.Integer(), nullable=False),
        sa.Column("source_in_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("source_out_ms", sa.Integer(), nullable=False),
        sa.Column("timeline_start_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("gain", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("fade_in_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("fade_out_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("track_id", "clip_order", name="uq_audio_clips_track_order"),
        sa.CheckConstraint("clip_order >= 1", name="ck_audio_clips_order"),
        sa.CheckConstraint("source_in_ms >= 0 AND source_out_ms > source_in_ms", name="ck_audio_clips_source_range"),
        sa.CheckConstraint("timeline_start_ms >= 0", name="ck_audio_clips_timeline_start"),
        sa.CheckConstraint("gain >= 0 AND gain <= 2", name="ck_audio_clips_gain"),
        sa.CheckConstraint("fade_in_ms >= 0 AND fade_out_ms >= 0", name="ck_audio_clips_fades"),
    )
    op.create_index("ix_audio_clips_track_id", "audio_clips", ["track_id"])
    op.create_index("ix_audio_clips_media_asset_id", "audio_clips", ["media_asset_id"])
    op.create_index("ix_audio_clips_track_timeline", "audio_clips", ["track_id", "timeline_start_ms"])


def downgrade() -> None:
    op.drop_index("ix_audio_clips_track_timeline", table_name="audio_clips")
    op.drop_index("ix_audio_clips_media_asset_id", table_name="audio_clips")
    op.drop_index("ix_audio_clips_track_id", table_name="audio_clips")
    op.drop_table("audio_clips")
    op.drop_index("ix_audio_tracks_sequence_id", table_name="audio_tracks")
    op.drop_table("audio_tracks")
    op.drop_index("ix_production_media_assets_project_created", table_name="production_media_assets")
    op.drop_index("ix_production_media_assets_sha256", table_name="production_media_assets")
    op.drop_index("ix_production_media_assets_project_id", table_name="production_media_assets")
    op.drop_table("production_media_assets")
