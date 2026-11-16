"""Add replay annotations and indexes."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0015_performance_playback"
down_revision = "0014_editorial_sequences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "performance_annotations",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("take_id", uuid, sa.ForeignKey("performance_takes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", uuid, sa.ForeignKey("performance_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("cast_member_instance_id", uuid, sa.ForeignKey("cast_member_instances.id", ondelete="SET NULL"), nullable=True),
        sa.Column("author_user_id", uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("timestamp_ms", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(20), server_default="note", nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("timestamp_ms >= 0", name="ck_performance_annotations_timestamp"),
        sa.CheckConstraint("category IN ('note', 'continuity', 'performance', 'camera', 'audio')", name="ck_performance_annotations_category"),
        sa.CheckConstraint("status IN ('open', 'resolved')", name="ck_performance_annotations_status"),
    )
    op.create_index("ix_performance_annotations_take_id", "performance_annotations", ["take_id"])
    op.create_index("ix_performance_annotations_author_user_id", "performance_annotations", ["author_user_id"])
    op.create_index("ix_performance_annotations_take_time", "performance_annotations", ["take_id", "timestamp_ms"])


def downgrade() -> None:
    op.drop_index("ix_performance_annotations_take_time", table_name="performance_annotations")
    op.drop_index("ix_performance_annotations_author_user_id", table_name="performance_annotations")
    op.drop_index("ix_performance_annotations_take_id", table_name="performance_annotations")
    op.drop_table("performance_annotations")
