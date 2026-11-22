"""Store compressed, chunked high-frequency motion capture samples."""

from alembic import op
import sqlalchemy as sa

revision = "0028_performance_capture_chunks"
down_revision = "0027_creator_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "performance_capture_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("take_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("start_timestamp_ms", sa.Integer(), nullable=False),
        sa.Column("end_timestamp_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("chunk_index >= 0", name="ck_performance_capture_chunks_index"),
        sa.CheckConstraint("sample_count > 0", name="ck_performance_capture_chunks_sample_count"),
        sa.CheckConstraint("size_bytes > 0", name="ck_performance_capture_chunks_size"),
        sa.ForeignKeyConstraint(["take_id"], ["performance_takes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key", name="uq_performance_capture_chunks_storage_key"),
        sa.UniqueConstraint("take_id", "chunk_index", name="uq_performance_capture_chunks_take_index"),
    )
    op.create_index("ix_performance_capture_chunks_take_id", "performance_capture_chunks", ["take_id"])
    op.create_index("ix_performance_capture_chunks_take_index", "performance_capture_chunks", ["take_id", "chunk_index"])


def downgrade() -> None:
    op.drop_index("ix_performance_capture_chunks_take_index", table_name="performance_capture_chunks")
    op.drop_index("ix_performance_capture_chunks_take_id", table_name="performance_capture_chunks")
    op.drop_table("performance_capture_chunks")
