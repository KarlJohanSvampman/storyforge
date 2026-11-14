"""Add contribution discussion and suggestion workflow."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_discussion"
down_revision = "0002_contributions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contribution_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("contribution_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("story_contributions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contribution_revisions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("parent_comment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contribution_comments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="visible"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('visible', 'hidden')", name="ck_contribution_comments_status"),
    )
    op.create_index("ix_contribution_comments_contribution_id", "contribution_comments", ["contribution_id"])

    op.create_table(
        "story_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("contribution_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("story_contributions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_revision_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contribution_revisions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("proposed_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'accepted', 'rejected', 'deferred')", name="ck_story_suggestions_status"),
    )
    op.create_index("ix_story_suggestions_contribution_id", "story_suggestions", ["contribution_id"])

    op.create_table(
        "suggestion_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("suggestion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("story_suggestions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("previous_status", sa.String(length=20), nullable=True),
        sa.Column("new_status", sa.String(length=20), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_suggestion_decisions_suggestion_id", "suggestion_decisions", ["suggestion_id"])


def downgrade() -> None:
    op.drop_index("ix_suggestion_decisions_suggestion_id", table_name="suggestion_decisions")
    op.drop_table("suggestion_decisions")
    op.drop_index("ix_story_suggestions_contribution_id", table_name="story_suggestions")
    op.drop_table("story_suggestions")
    op.drop_index("ix_contribution_comments_contribution_id", table_name="contribution_comments")
    op.drop_table("contribution_comments")
