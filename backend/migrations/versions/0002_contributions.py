"""Add version-preserved story contributions."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_contributions"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "story_contributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'withdrawn')", name="ck_story_contributions_status"),
    )
    op.create_index("ix_story_contributions_project_id", "story_contributions", ["project_id"])
    op.create_index("ix_story_contributions_author_user_id", "story_contributions", ["author_user_id"])
    op.create_table(
        "contribution_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("contribution_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("story_contributions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("contribution_id", "revision_number", name="uq_contribution_revisions_number"),
        sa.CheckConstraint("revision_number >= 1", name="ck_contribution_revisions_positive_number"),
    )
    op.create_index("ix_contribution_revisions_contribution_id", "contribution_revisions", ["contribution_id"])


def downgrade() -> None:
    op.drop_index("ix_contribution_revisions_contribution_id", table_name="contribution_revisions")
    op.drop_table("contribution_revisions")
    op.drop_index("ix_story_contributions_author_user_id", table_name="story_contributions")
    op.drop_index("ix_story_contributions_project_id", table_name="story_contributions")
    op.drop_table("story_contributions")
