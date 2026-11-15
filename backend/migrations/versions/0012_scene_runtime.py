"""Add isolated scene runs, cast snapshots, controller audit and possession leases."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012_scene_runtime"
down_revision = "0011_actor_casting"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scene_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("storyboard_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("storyboards.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("storyboard_scenes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("narrative_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("narrative_draft_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="prepared"),
        sa.Column("authority_epoch", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('prepared', 'running', 'paused', 'completed', 'aborted')", name="ck_scene_runs_status"),
        sa.CheckConstraint("authority_epoch >= 1", name="ck_scene_runs_authority_epoch"),
    )
    op.create_index("ix_scene_runs_project_id", "scene_runs", ["project_id"])
    op.create_index("ix_scene_runs_scene_id", "scene_runs", ["scene_id"])
    op.create_index("ix_scene_runs_project_created", "scene_runs", ["project_id", "created_at"])

    op.create_table(
        "cast_member_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scene_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scene_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("casting_assignment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("casting_assignments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project_characters.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("actor_name_snapshot", sa.String(160), nullable=False),
        sa.Column("character_name_snapshot", sa.String(160), nullable=False),
        sa.Column("role_label_snapshot", sa.String(100), nullable=False),
        sa.Column("controller_type", sa.String(30), nullable=False),
        sa.Column("controller_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("control_mode", sa.String(20), nullable=False),
        sa.Column("control_settings", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("instance_status", sa.String(20), nullable=False, server_default="ready"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("scene_run_id", "character_id", name="uq_cast_member_instances_run_character"),
        sa.CheckConstraint("instance_status IN ('ready', 'removed')", name="ck_cast_member_instances_status"),
        sa.CheckConstraint("controller_type IN ('user', 'ai_agent', 'script_engine', 'system')", name="ck_cast_member_instances_controller"),
        sa.CheckConstraint("control_mode IN ('direct', 'command', 'assisted', 'autonomous', 'scripted')", name="ck_cast_member_instances_mode"),
    )
    op.create_index("ix_cast_member_instances_scene_run_id", "cast_member_instances", ["scene_run_id"])

    op.create_table(
        "controller_assignment_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scene_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scene_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cast_member_instance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cast_member_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("authority_epoch", sa.Integer(), nullable=False),
        sa.Column("previous_controller_type", sa.String(30)),
        sa.Column("previous_controller_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("new_controller_type", sa.String(30), nullable=False),
        sa.Column("new_controller_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_controller_assignment_events_scene_run_id", "controller_assignment_events", ["scene_run_id"])
    op.create_index("ix_controller_assignment_events_cast_member_instance_id", "controller_assignment_events", ["cast_member_instance_id"])

    op.create_table(
        "possession_leases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scene_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scene_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cast_member_instance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cast_member_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("authority_epoch", sa.Integer(), nullable=False),
        sa.Column("controller_type", sa.String(30), nullable=False),
        sa.Column("controller_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("authority_epoch >= 1", name="ck_possession_leases_epoch"),
        sa.CheckConstraint("expires_at > created_at", name="ck_possession_leases_expiry"),
    )
    op.create_index("ix_possession_leases_scene_run_id", "possession_leases", ["scene_run_id"])
    op.create_index("ix_possession_leases_cast_member_instance_id", "possession_leases", ["cast_member_instance_id"])
    op.create_index("ix_possession_leases_instance_active", "possession_leases", ["cast_member_instance_id", "revoked_at", "expires_at"])


def downgrade() -> None:
    op.drop_table("possession_leases")
    op.drop_table("controller_assignment_events")
    op.drop_table("cast_member_instances")
    op.drop_index("ix_scene_runs_project_created", table_name="scene_runs")
    op.drop_index("ix_scene_runs_scene_id", table_name="scene_runs")
    op.drop_index("ix_scene_runs_project_id", table_name="scene_runs")
    op.drop_table("scene_runs")
