"""Extend runtime authority and add non-destructive editorial sequences."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0014_editorial_sequences"
down_revision = "0013_performance_takes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.add_column("cast_member_instances", sa.Column("authority_epoch", sa.Integer(), server_default="1", nullable=False))
    op.create_check_constraint("ck_cast_member_instances_authority_epoch", "cast_member_instances", "authority_epoch >= 1")

    op.add_column("possession_leases", sa.Column("lease_token", uuid, nullable=True))
    op.add_column("possession_leases", sa.Column("previous_controller_type", sa.String(30), nullable=True))
    op.add_column("possession_leases", sa.Column("previous_controller_user_id", uuid, nullable=True))
    op.add_column("possession_leases", sa.Column("previous_control_mode", sa.String(20), nullable=True))
    op.execute("UPDATE possession_leases SET lease_token = gen_random_uuid() WHERE lease_token IS NULL")
    op.alter_column("possession_leases", "lease_token", nullable=False)
    op.create_unique_constraint("uq_possession_leases_lease_token", "possession_leases", ["lease_token"])

    op.add_column("performance_takes", sa.Column("state_snapshot", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False))
    op.drop_constraint("ck_performance_takes_status", "performance_takes", type_="check")
    op.create_check_constraint(
        "ck_performance_takes_status", "performance_takes",
        "status IN ('recording', 'finalized', 'selected', 'discarded')",
    )

    op.add_column("performance_events", sa.Column("cast_member_instance_id", uuid, nullable=True))
    op.add_column("performance_events", sa.Column("authority_epoch", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_performance_events_cast_member_instance_id", "performance_events",
        "cast_member_instances", ["cast_member_instance_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_performance_events_cast_member_instance_id", "performance_events", ["cast_member_instance_id"])

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
        sa.CheckConstraint("status IN ('draft', 'locked')", name="ck_edit_sequences_status"),
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
    op.drop_index("ix_performance_events_cast_member_instance_id", table_name="performance_events")
    op.drop_constraint("fk_performance_events_cast_member_instance_id", "performance_events", type_="foreignkey")
    op.drop_column("performance_events", "authority_epoch")
    op.drop_column("performance_events", "cast_member_instance_id")
    op.drop_column("performance_takes", "state_snapshot")
    op.drop_constraint("ck_performance_takes_status", "performance_takes", type_="check")
    op.create_check_constraint("ck_performance_takes_status", "performance_takes", "status IN ('recording', 'finalized', 'discarded')")
    op.drop_constraint("uq_possession_leases_lease_token", "possession_leases", type_="unique")
    op.drop_column("possession_leases", "previous_control_mode")
    op.drop_column("possession_leases", "previous_controller_user_id")
    op.drop_column("possession_leases", "previous_controller_type")
    op.drop_column("possession_leases", "lease_token")
    op.drop_constraint("ck_cast_member_instances_authority_epoch", "cast_member_instances", type_="check")
    op.drop_column("cast_member_instances", "authority_epoch")
