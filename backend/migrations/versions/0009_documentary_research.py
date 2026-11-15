"""Add documentary source registry and human fact-check ledger."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_documentary_research"
down_revision = "0008_project_formats_series"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documentary_research_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False, server_default="article"),
        sa.Column("creator", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("publisher", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("publication_date", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("citation_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("research_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("accessed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "source_type IN ('article', 'book', 'academic_paper', 'official_record', 'government_data', 'interview', 'archival_record', 'website', 'other')",
            name="ck_documentary_sources_type",
        ),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_documentary_sources_status"),
    )
    op.create_index(
        "ix_documentary_research_sources_project_id",
        "documentary_research_sources",
        ["project_id"],
    )

    op.create_table(
        "documentary_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=False, server_default=""),
        sa.Column("origin", sa.String(length=20), nullable=False, server_default="human"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("current_review_status", sa.String(length=30), nullable=False, server_default="unreviewed"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("origin IN ('human', 'ai_assisted')", name="ck_documentary_claims_origin"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_documentary_claims_status"),
        sa.CheckConstraint(
            "current_review_status IN ('unreviewed', 'needs_review', 'supported', 'contested', 'not_supported', 'insufficient_evidence')",
            name="ck_documentary_claims_review_status",
        ),
    )
    op.create_index("ix_documentary_claims_project_id", "documentary_claims", ["project_id"])

    op.create_table(
        "documentary_claim_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documentary_claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documentary_research_sources.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("evidence_relation", sa.String(length=20), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False, server_default=""),
        sa.Column("locator", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("claim_id", "source_id", name="uq_documentary_claim_evidence_pair"),
        sa.CheckConstraint("evidence_relation IN ('supports', 'challenges', 'context')", name="ck_documentary_evidence_relation"),
    )
    op.create_index("ix_documentary_claim_evidence_claim_id", "documentary_claim_evidence", ["claim_id"])
    op.create_index("ix_documentary_claim_evidence_source_id", "documentary_claim_evidence", ["source_id"])

    op.create_table(
        "documentary_claim_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documentary_claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_status", sa.String(length=30), nullable=False),
        sa.Column("result", sa.String(length=30), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "reviewed_evidence_snapshot",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column("reviewer_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "result IN ('supported', 'contested', 'not_supported', 'insufficient_evidence')",
            name="ck_documentary_claim_reviews_result",
        ),
    )
    op.create_index("ix_documentary_claim_reviews_claim_id", "documentary_claim_reviews", ["claim_id"])


def downgrade() -> None:
    op.drop_index("ix_documentary_claim_reviews_claim_id", table_name="documentary_claim_reviews")
    op.drop_table("documentary_claim_reviews")

    op.drop_index("ix_documentary_claim_evidence_source_id", table_name="documentary_claim_evidence")
    op.drop_index("ix_documentary_claim_evidence_claim_id", table_name="documentary_claim_evidence")
    op.drop_table("documentary_claim_evidence")

    op.drop_index("ix_documentary_claims_project_id", table_name="documentary_claims")
    op.drop_table("documentary_claims")

    op.drop_index("ix_documentary_research_sources_project_id", table_name="documentary_research_sources")
    op.drop_table("documentary_research_sources")
