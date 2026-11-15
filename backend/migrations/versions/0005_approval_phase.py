"""Add project approval rules, vote history, decisions, and phase history."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_approval_phase"
down_revision = "0004_narrative_drafts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_approval_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False, server_default="owner_only"),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project_id", name="uq_project_approval_rules_project"),
        sa.CheckConstraint("mode IN ('owner_only', 'majority')", name="ck_project_approval_rules_mode"),
    )
    op.create_index("ix_project_approval_rules_project_id", "project_approval_rules", ["project_id"])

    op.create_table(
        "narrative_approval_votes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("narrative_draft_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("voter_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("choice", sa.String(length=20), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("choice IN ('approve', 'reject')", name="ck_narrative_approval_votes_choice"),
    )
    op.create_index("ix_narrative_approval_votes_version_id", "narrative_approval_votes", ["version_id"])
    op.create_index("ix_narrative_approval_votes_voter_user_id", "narrative_approval_votes", ["voter_user_id"])

    op.create_table(
        "narrative_approval_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("narrative_draft_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("rule_mode", sa.String(length=20), nullable=False),
        sa.Column("eligible_voter_count", sa.Integer(), nullable=False),
        sa.Column("approve_count", sa.Integer(), nullable=False),
        sa.Column("reject_count", sa.Integer(), nullable=False),
        sa.Column("required_votes", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("version_id", name="uq_narrative_approval_decisions_version"),
        sa.CheckConstraint("outcome IN ('approved', 'rejected')", name="ck_narrative_approval_decisions_outcome"),
        sa.CheckConstraint("rule_mode IN ('owner_only', 'majority')", name="ck_narrative_approval_decisions_rule_mode"),
    )
    op.create_index("ix_narrative_approval_decisions_version_id", "narrative_approval_decisions", ["version_id"])

    op.create_table(
        "project_phase_transitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_phase", sa.String(length=30), nullable=False),
        sa.Column("to_phase", sa.String(length=30), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("narrative_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("narrative_draft_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_project_phase_transitions_project_id", "project_phase_transitions", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_project_phase_transitions_project_id", table_name="project_phase_transitions")
    op.drop_table("project_phase_transitions")
    op.drop_index("ix_narrative_approval_decisions_version_id", table_name="narrative_approval_decisions")
    op.drop_table("narrative_approval_decisions")
    op.drop_index("ix_narrative_approval_votes_voter_user_id", table_name="narrative_approval_votes")
    op.drop_index("ix_narrative_approval_votes_version_id", table_name="narrative_approval_votes")
    op.drop_table("narrative_approval_votes")
    op.drop_index("ix_project_approval_rules_project_id", table_name="project_approval_rules")
    op.drop_table("project_approval_rules")
