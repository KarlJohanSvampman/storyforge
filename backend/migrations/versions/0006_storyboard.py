"""Add approved-narrative storyboard, scenes, script revisions and creative assets."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_storyboard"
down_revision = "0005_approval_phase"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_characters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("visual_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("personality_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_project_characters_status"),
    )
    op.create_index("ix_project_characters_project_id", "project_characters", ["project_id"])

    op.create_table(
        "project_locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("environment_type", sa.String(length=40), nullable=False, server_default="unspecified"),
        sa.Column("time_period", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("visual_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_project_locations_status"),
    )
    op.create_index("ix_project_locations_project_id", "project_locations", ["project_id"])

    op.create_table(
        "storyboards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("narrative_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("narrative_draft_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project_id", "narrative_version_id", name="uq_storyboards_project_narrative"),
    )
    op.create_index("ix_storyboards_project_id", "storyboards", ["project_id"])

    op.create_table(
        "storyboard_scenes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("storyboard_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("storyboards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scene_order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("requirements", sa.Text(), nullable=False, server_default=""),
        sa.Column("estimated_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project_locations.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("storyboard_id", "scene_order", name="uq_storyboard_scenes_order"),
        sa.CheckConstraint("scene_order >= 1", name="ck_storyboard_scenes_positive_order"),
        sa.CheckConstraint("estimated_duration_seconds IS NULL OR estimated_duration_seconds > 0", name="ck_storyboard_scenes_duration"),
    )
    op.create_index("ix_storyboard_scenes_storyboard_id", "storyboard_scenes", ["storyboard_id"])

    op.create_table(
        "scene_character_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("storyboard_scenes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project_characters.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("role_label", sa.String(length=80), nullable=False, server_default="Participant"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("assigned_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("scene_id", "character_id", name="uq_scene_character_assignments_pair"),
    )
    op.create_index("ix_scene_character_assignments_scene_id", "scene_character_assignments", ["scene_id"])
    op.create_index("ix_scene_character_assignments_character_id", "scene_character_assignments", ["character_id"])

    op.create_table(
        "scene_passage_references",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("storyboard_scenes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reference_order", sa.Integer(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("passage_snapshot", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("scene_id", "reference_order", name="uq_scene_passage_references_order"),
        sa.CheckConstraint("reference_order >= 1", name="ck_scene_passage_references_positive_order"),
        sa.CheckConstraint("start_offset >= 0 AND end_offset > start_offset", name="ck_scene_passage_references_offsets"),
    )
    op.create_index("ix_scene_passage_references_scene_id", "scene_passage_references", ["scene_id"])

    op.create_table(
        "scene_script_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("storyboard_scenes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("parent_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scene_script_versions.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("scene_id", "revision_number", name="uq_scene_script_versions_number"),
        sa.CheckConstraint("revision_number >= 1", name="ck_scene_script_versions_positive_number"),
    )
    op.create_index("ix_scene_script_versions_scene_id", "scene_script_versions", ["scene_id"])


def downgrade() -> None:
    op.drop_index("ix_scene_script_versions_scene_id", table_name="scene_script_versions")
    op.drop_table("scene_script_versions")
    op.drop_index("ix_scene_passage_references_scene_id", table_name="scene_passage_references")
    op.drop_table("scene_passage_references")
    op.drop_index("ix_scene_character_assignments_character_id", table_name="scene_character_assignments")
    op.drop_index("ix_scene_character_assignments_scene_id", table_name="scene_character_assignments")
    op.drop_table("scene_character_assignments")
    op.drop_index("ix_storyboard_scenes_storyboard_id", table_name="storyboard_scenes")
    op.drop_table("storyboard_scenes")
    op.drop_index("ix_storyboards_project_id", table_name="storyboards")
    op.drop_table("storyboards")
    op.drop_index("ix_project_locations_project_id", table_name="project_locations")
    op.drop_table("project_locations")
    op.drop_index("ix_project_characters_project_id", table_name="project_characters")
    op.drop_table("project_characters")
