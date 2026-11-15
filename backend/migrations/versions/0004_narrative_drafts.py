"""Add narrative draft proposal versions and immutable source references."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_narrative_drafts"
down_revision = "0003_discussion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "narrative_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("current_version_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project_id", name="uq_narrative_drafts_project"),
        sa.CheckConstraint("current_version_number >= 0", name="ck_narrative_drafts_version_number"),
    )
    op.create_index("ix_narrative_drafts_project_id", "narrative_drafts", ["project_id"])

    op.create_table(
        "narrative_draft_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("narrative_drafts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="proposal"),
        sa.Column("origin", sa.String(length=20), nullable=False),
        sa.Column("provider_name", sa.String(length=80), nullable=True),
        sa.Column("model_name", sa.String(length=120), nullable=True),
        sa.Column("prompt_version", sa.String(length=80), nullable=True),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("parent_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("narrative_draft_versions.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("draft_id", "version_number", name="uq_narrative_draft_versions_number"),
        sa.CheckConstraint("version_number >= 1", name="ck_narrative_draft_versions_positive_number"),
        sa.CheckConstraint("status = 'proposal'", name="ck_narrative_draft_versions_proposal_only"),
        sa.CheckConstraint("origin IN ('compiled', 'manual')", name="ck_narrative_draft_versions_origin"),
    )
    op.create_index("ix_narrative_draft_versions_draft_id", "narrative_draft_versions", ["draft_id"])

    op.create_table(
        "draft_source_references",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("narrative_draft_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_order", sa.Integer(), nullable=False),
        sa.Column("source_kind", sa.String(length=30), nullable=False),
        sa.Column("contribution_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("story_contributions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("contribution_revision_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contribution_revisions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("suggestion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("story_suggestions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_title", sa.String(length=160), nullable=False),
        sa.Column("source_text_snapshot", sa.Text(), nullable=False),
        sa.UniqueConstraint("version_id", "source_order", name="uq_draft_source_references_order"),
        sa.CheckConstraint("source_order >= 1", name="ck_draft_source_references_positive_order"),
        sa.CheckConstraint("source_kind IN ('contribution', 'accepted_suggestion')", name="ck_draft_source_references_kind"),
    )
    op.create_index("ix_draft_source_references_version_id", "draft_source_references", ["version_id"])


def downgrade() -> None:
    op.drop_index("ix_draft_source_references_version_id", table_name="draft_source_references")
    op.drop_table("draft_source_references")
    op.drop_index("ix_narrative_draft_versions_draft_id", table_name="narrative_draft_versions")
    op.drop_table("narrative_draft_versions")
    op.drop_index("ix_narrative_drafts_project_id", table_name="narrative_drafts")
    op.drop_table("narrative_drafts")
