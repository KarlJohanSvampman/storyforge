"""Add interview records, releases, private media storage metadata and rights."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_doc_interview_rights"
down_revision = "0009_documentary_research"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documentary_interview_subjects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name_or_pseudonym", sa.String(200), nullable=False),
        sa.Column("identity_mode", sa.String(20), nullable=False, server_default="named"),
        sa.Column("role_or_relationship", sa.String(240), nullable=False, server_default=""),
        sa.Column("background_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("identity_mode IN ('named', 'pseudonym', 'anonymous')", name="ck_documentary_interview_subjects_identity_mode"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_documentary_interview_subjects_status"),
    )
    op.create_index("ix_documentary_interview_subjects_project_id", "documentary_interview_subjects", ["project_id"])

    op.create_table(
        "documentary_interview_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documentary_interview_subjects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("session_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interviewer_name", sa.String(200), nullable=False, server_default=""),
        sa.Column("session_format", sa.String(20), nullable=False, server_default="in_person"),
        sa.Column("location_or_platform", sa.String(240), nullable=False, server_default=""),
        sa.Column("transcript_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("session_format IN ('in_person', 'remote', 'phone', 'written', 'other')", name="ck_documentary_interview_sessions_format"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_documentary_interview_sessions_status"),
    )
    op.create_index("ix_documentary_interview_sessions_project_id", "documentary_interview_sessions", ["project_id"])
    op.create_index("ix_documentary_interview_sessions_subject_id", "documentary_interview_sessions", ["subject_id"])

    op.create_table(
        "documentary_media_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documentary_research_sources.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("interview_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documentary_interview_sessions.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("asset_type", sa.String(30), nullable=False, server_default="document"),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(160), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("asset_type IN ('transcript', 'audio', 'video', 'image', 'document', 'release_document', 'other')", name="ck_documentary_media_assets_type"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_documentary_media_assets_status"),
        sa.CheckConstraint("size_bytes > 0", name="ck_documentary_media_assets_size"),
        sa.CheckConstraint("duration_seconds IS NULL OR duration_seconds > 0", name="ck_documentary_media_assets_duration"),
        sa.UniqueConstraint("storage_key", name="uq_documentary_media_assets_storage_key"),
    )
    op.create_index("ix_documentary_media_assets_project_id", "documentary_media_assets", ["project_id"])
    op.create_index("ix_documentary_media_assets_source_id", "documentary_media_assets", ["source_id"])
    op.create_index("ix_documentary_media_assets_interview_session_id", "documentary_media_assets", ["interview_session_id"])
    op.create_index("ix_documentary_media_assets_sha256", "documentary_media_assets", ["sha256"])

    op.create_table(
        "documentary_releases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documentary_interview_subjects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("interview_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documentary_interview_sessions.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("scope_type", sa.String(20), nullable=False, server_default="project"),
        sa.Column("scope_label", sa.String(240), nullable=False, server_default=""),
        sa.Column("consent_scope", sa.Text(), nullable=False),
        sa.Column("withdrawal_terms", sa.Text(), nullable=False, server_default=""),
        sa.Column("permitted_uses", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("release_document_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documentary_media_assets.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("scope_type IN ('project', 'production', 'release')", name="ck_documentary_releases_scope"),
        sa.CheckConstraint("status IN ('draft', 'signed', 'withdrawn', 'expired')", name="ck_documentary_releases_status"),
    )
    op.create_index("ix_documentary_releases_project_id", "documentary_releases", ["project_id"])
    op.create_index("ix_documentary_releases_subject_id", "documentary_releases", ["subject_id"])

    op.create_table(
        "documentary_release_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("release_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documentary_releases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("previous_status", sa.String(20), nullable=True),
        sa.Column("new_status", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_documentary_release_events_release_id", "documentary_release_events", ["release_id"])

    op.create_table(
        "documentary_media_rights",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("media_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documentary_media_assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("supersedes_rights_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documentary_media_rights.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("rights_holder", sa.String(240), nullable=False, server_default=""),
        sa.Column("rights_basis", sa.String(30), nullable=False, server_default="unknown"),
        sa.Column("license_name", sa.String(240), nullable=False, server_default=""),
        sa.Column("license_url", sa.String(2048), nullable=False, server_default=""),
        sa.Column("territory", sa.String(240), nullable=False, server_default="Worldwide"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("permitted_uses", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("attribution_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("attribution_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("restrictions", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("media_asset_id", "version_number", name="uq_documentary_media_rights_version"),
        sa.CheckConstraint("version_number >= 1", name="ck_documentary_media_rights_positive_version"),
        sa.CheckConstraint("rights_basis IN ('owned', 'licensed', 'public_domain', 'permission', 'fair_use', 'research_only', 'unknown')", name="ck_documentary_media_rights_basis"),
        sa.CheckConstraint("status IN ('active', 'needs_review', 'withdrawn', 'superseded')", name="ck_documentary_media_rights_status"),
        sa.CheckConstraint("valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from", name="ck_documentary_media_rights_validity"),
    )
    op.create_index("ix_documentary_media_rights_media_asset_id", "documentary_media_rights", ["media_asset_id"])

    op.create_table(
        "documentary_claim_usages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documentary_claims.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("storyboard_scenes.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("script_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scene_script_versions.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("usage_type", sa.String(30), nullable=False),
        sa.Column("reference_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("usage_type IN ('outline', 'scene', 'script', 'narration', 'lower_third', 'caption')", name="ck_documentary_claim_usages_type"),
    )
    op.create_index("ix_documentary_claim_usages_project_id", "documentary_claim_usages", ["project_id"])
    op.create_index("ix_documentary_claim_usages_claim_id", "documentary_claim_usages", ["claim_id"])
    op.create_index("ix_documentary_claim_usages_scene_id", "documentary_claim_usages", ["scene_id"])
    op.create_index("ix_documentary_claim_usages_script_version_id", "documentary_claim_usages", ["script_version_id"])


def downgrade() -> None:
    op.drop_index("ix_documentary_claim_usages_script_version_id", table_name="documentary_claim_usages")
    op.drop_index("ix_documentary_claim_usages_scene_id", table_name="documentary_claim_usages")
    op.drop_index("ix_documentary_claim_usages_claim_id", table_name="documentary_claim_usages")
    op.drop_index("ix_documentary_claim_usages_project_id", table_name="documentary_claim_usages")
    op.drop_table("documentary_claim_usages")

    op.drop_index("ix_documentary_media_rights_media_asset_id", table_name="documentary_media_rights")
    op.drop_table("documentary_media_rights")

    op.drop_index("ix_documentary_release_events_release_id", table_name="documentary_release_events")
    op.drop_table("documentary_release_events")

    op.drop_index("ix_documentary_releases_subject_id", table_name="documentary_releases")
    op.drop_index("ix_documentary_releases_project_id", table_name="documentary_releases")
    op.drop_table("documentary_releases")

    op.drop_index("ix_documentary_media_assets_sha256", table_name="documentary_media_assets")
    op.drop_index("ix_documentary_media_assets_interview_session_id", table_name="documentary_media_assets")
    op.drop_index("ix_documentary_media_assets_source_id", table_name="documentary_media_assets")
    op.drop_index("ix_documentary_media_assets_project_id", table_name="documentary_media_assets")
    op.drop_table("documentary_media_assets")

    op.drop_index("ix_documentary_interview_sessions_subject_id", table_name="documentary_interview_sessions")
    op.drop_index("ix_documentary_interview_sessions_project_id", table_name="documentary_interview_sessions")
    op.drop_table("documentary_interview_sessions")

    op.drop_index("ix_documentary_interview_subjects_project_id", table_name="documentary_interview_subjects")
    op.drop_table("documentary_interview_subjects")
