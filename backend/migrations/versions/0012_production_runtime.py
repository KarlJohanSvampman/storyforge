"""Add isolated scene runs, replayable takes and non-destructive edit sequences."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012_production_runtime"
down_revision = "0011_actor_casting"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "scene_runs",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("project_id", uuid, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("storyboard_id", uuid, sa.ForeignKey("storyboards.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scene_id", uuid, sa.ForeignKey("storyboard_scenes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("run_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="ready", nullable=False),
        sa.Column("scene_snapshot", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("created_by_user_id", uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('ready', 'running', 'paused', 'completed', 'abandoned')", name="ck_scene_runs_status"),
        sa.CheckConstraint("run_number >= 1", name="ck_scene_runs_number"),
        sa.UniqueConstraint("scene_id", "run_number", name="uq_scene_runs_scene_number"),
    )
    op.create_index("ix_scene_runs_project_id", "scene_runs", ["project_id"])
    op.create_index("ix_scene_runs_scene_id", "scene_runs", ["scene_id"])

    op.create_table(
        "cast_member_instances",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("scene_run_id", uuid, sa.ForeignKey("scene_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("casting_assignment_id", uuid, sa.ForeignKey("casting_assignments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("actor_id", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("character_id", uuid, sa.ForeignKey("project_characters.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("actor_snapshot", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("character_snapshot", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("controller_type", sa.String(30), nullable=False),
        sa.Column("controller_user_id", uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("control_mode", sa.String(20), nullable=False),
        sa.Column("initial_controller_type", sa.String(30), nullable=False),
        sa.Column("initial_controller_user_id", uuid, nullable=True),
        sa.Column("initial_control_mode", sa.String(20), nullable=False),
        sa.Column("authority_epoch", sa.Integer(), server_default="1", nullable=False),
        sa.Column("state_snapshot", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'removed')", name="ck_cast_member_instances_status"),
        sa.CheckConstraint("controller_type IN ('user', 'ai_agent', 'script_engine', 'system')", name="ck_cast_member_instances_controller"),
        sa.CheckConstraint("control_mode IN ('direct', 'command', 'assisted', 'autonomous', 'scripted')", name="ck_cast_member_instances_mode"),
        sa.UniqueConstraint("scene_run_id", "casting_assignment_id", name="uq_cast_member_instances_casting"),
    )
    op.create_index("ix_cast_member_instances_scene_run_id", "cast_member_instances", ["scene_run_id"])

    op.create_table(
        "controller_assignment_events",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("cast_member_instance_id", uuid, sa.ForeignKey("cast_member_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("authority_epoch", sa.Integer(), nullable=False),
        sa.Column("previous_controller_type", sa.String(30), nullable=False),
        sa.Column("previous_controller_user_id", uuid, nullable=True),
        sa.Column("new_controller_type", sa.String(30), nullable=False),
        sa.Column("new_controller_user_id", uuid, nullable=True),
        sa.Column("control_mode", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(240), server_default="controller_changed", nullable=False),
        sa.Column("changed_by_user_id", uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("cast_member_instance_id", "authority_epoch", name="uq_controller_events_epoch"),
    )
    op.create_index("ix_controller_assignment_events_cast_member_instance_id", "controller_assignment_events", ["cast_member_instance_id"])

    op.create_table(
        "possession_leases",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("cast_member_instance_id", uuid, sa.ForeignKey("cast_member_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("controller_user_id", uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("lease_token", uuid, nullable=False, unique=True),
        sa.Column("authority_epoch", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_possession_leases_cast_member_instance_id", "possession_leases", ["cast_member_instance_id"])
    op.create_index("uq_possession_leases_active_instance", "possession_leases", ["cast_member_instance_id"], unique=True, postgresql_where=sa.text("released_at IS NULL"), sqlite_where=sa.text("released_at IS NULL"))

    op.create_table(
        "performance_takes",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("project_id", uuid, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scene_run_id", uuid, sa.ForeignKey("scene_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("take_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="recorded", nullable=False),
        sa.Column("duration_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("event_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("state_snapshot", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("created_by_user_id", uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("take_number >= 1", name="ck_performance_takes_number"),
        sa.CheckConstraint("status IN ('recorded', 'selected', 'rejected')", name="ck_performance_takes_status"),
        sa.CheckConstraint("duration_ms >= 0", name="ck_performance_takes_duration"),
        sa.UniqueConstraint("scene_run_id", "take_number", name="uq_performance_takes_number"),
    )
    op.create_index("ix_performance_takes_project_id", "performance_takes", ["project_id"])
    op.create_index("ix_performance_takes_scene_run_id", "performance_takes", ["scene_run_id"])

    op.create_table(
        "performance_take_events",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("take_id", uuid, sa.ForeignKey("performance_takes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_order", sa.Integer(), nullable=False),
        sa.Column("timestamp_ms", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("cast_member_instance_id", uuid, sa.ForeignKey("cast_member_instances.id", ondelete="SET NULL"), nullable=True),
        sa.Column("authority_epoch", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("event_order >= 1", name="ck_performance_take_events_order"),
        sa.CheckConstraint("timestamp_ms >= 0", name="ck_performance_take_events_timestamp"),
        sa.UniqueConstraint("take_id", "event_order", name="uq_performance_take_events_order"),
    )
    op.create_index("ix_performance_take_events_take_id", "performance_take_events", ["take_id"])

    op.create_table(
        "edit_sequences",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("project_id", uuid, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("revision_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by_user_id", uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('draft', 'locked', 'exported')", name="ck_edit_sequences_status"),
        sa.UniqueConstraint("project_id", "name", name="uq_edit_sequences_project_name"),
    )
    op.create_index("ix_edit_sequences_project_id", "edit_sequences", ["project_id"])

    op.create_table(
        "edit_sequence_items",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("sequence_id", uuid, sa.ForeignKey("edit_sequences.id", ondelete="CASCADE"), nullable=False),
        sa.Column("take_id", uuid, sa.ForeignKey("performance_takes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scene_id", uuid, sa.ForeignKey("storyboard_scenes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("item_order", sa.Integer(), nullable=False),
        sa.Column("in_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("out_ms", sa.Integer(), nullable=False),
        sa.Column("transition", sa.String(20), server_default="cut", nullable=False),
        sa.Column("title_overlay", sa.String(500), server_default="", nullable=False),
        sa.Column("effects", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("audio_cue", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("item_order >= 1", name="ck_edit_sequence_items_order"),
        sa.CheckConstraint("in_ms >= 0 AND out_ms > in_ms", name="ck_edit_sequence_items_trim"),
        sa.CheckConstraint("transition IN ('cut', 'fade', 'dissolve')", name="ck_edit_sequence_items_transition"),
        sa.UniqueConstraint("sequence_id", "item_order", name="uq_edit_sequence_items_order"),
    )
    op.create_index("ix_edit_sequence_items_sequence_id", "edit_sequence_items", ["sequence_id"])

    op.create_table(
        "edit_exports",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("sequence_id", uuid, sa.ForeignKey("edit_sequences.id", ondelete="CASCADE"), nullable=False),
        sa.Column("export_number", sa.Integer(), nullable=False),
        sa.Column("sequence_revision", sa.Integer(), nullable=False),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("sequence_id", "export_number", name="uq_edit_exports_number"),
    )
    op.create_index("ix_edit_exports_sequence_id", "edit_exports", ["sequence_id"])


def downgrade() -> None:
    op.drop_index("ix_edit_exports_sequence_id", table_name="edit_exports")
    op.drop_table("edit_exports")
    op.drop_index("ix_edit_sequence_items_sequence_id", table_name="edit_sequence_items")
    op.drop_table("edit_sequence_items")
    op.drop_index("ix_edit_sequences_project_id", table_name="edit_sequences")
    op.drop_table("edit_sequences")
    op.drop_index("ix_performance_take_events_take_id", table_name="performance_take_events")
    op.drop_table("performance_take_events")
    op.drop_index("ix_performance_takes_scene_run_id", table_name="performance_takes")
    op.drop_index("ix_performance_takes_project_id", table_name="performance_takes")
    op.drop_table("performance_takes")
    op.drop_index("ix_possession_leases_active_instance", table_name="possession_leases")
    op.drop_index("ix_possession_leases_cast_member_instance_id", table_name="possession_leases")
    op.drop_table("possession_leases")
    op.drop_index("ix_controller_assignment_events_cast_member_instance_id", table_name="controller_assignment_events")
    op.drop_table("controller_assignment_events")
    op.drop_index("ix_cast_member_instances_scene_run_id", table_name="cast_member_instances")
    op.drop_table("cast_member_instances")
    op.drop_index("ix_scene_runs_scene_id", table_name="scene_runs")
    op.drop_index("ix_scene_runs_project_id", table_name="scene_runs")
    op.drop_table("scene_runs")
