"""Add structured performance takes and ordered event streams."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013_performance_takes"
down_revision = "0012_scene_runtime"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "performance_takes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scene_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scene_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cast_member_instance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cast_member_instances.id", ondelete="RESTRICT")),
        sa.Column("take_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(160), nullable=False, server_default="Take"),
        sa.Column("status", sa.String(20), nullable=False, server_default="recording"),
        sa.Column("camera_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('recording', 'finalized', 'discarded')", name="ck_performance_takes_status"),
        sa.CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="ck_performance_takes_duration"),
        sa.UniqueConstraint("scene_run_id", "take_number", name="uq_performance_takes_run_number"),
    )
    op.create_index("ix_performance_takes_scene_run_id", "performance_takes", ["scene_run_id"])
    op.create_index("ix_performance_takes_scene_run_created", "performance_takes", ["scene_run_id", "created_at"])

    op.create_table(
        "performance_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("take_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("performance_takes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("timestamp_ms", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("take_id", "sequence_number", name="uq_performance_events_take_sequence"),
        sa.CheckConstraint("sequence_number >= 0", name="ck_performance_events_sequence"),
        sa.CheckConstraint("timestamp_ms >= 0", name="ck_performance_events_timestamp"),
        sa.CheckConstraint("event_type IN ('transform', 'gesture', 'expression', 'voice_marker', 'camera', 'cue')", name="ck_performance_events_type"),
    )
    op.create_index("ix_performance_events_take_id", "performance_events", ["take_id"])


def downgrade() -> None:
    op.drop_table("performance_events")
    op.drop_index("ix_performance_takes_scene_run_created", table_name="performance_takes")
    op.drop_index("ix_performance_takes_scene_run_id", table_name="performance_takes")
    op.drop_table("performance_takes")
