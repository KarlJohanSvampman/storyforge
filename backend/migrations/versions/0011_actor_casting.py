"""Add persistent actors, project performance settings and casting assignments."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011_actor_casting"
down_revision = "0010_doc_interview_rights"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "actors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("biography", sa.Text(), nullable=False, server_default=""),
        sa.Column("performance_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_actors_status"),
    )
    op.create_index("ix_actors_owner_user_id", "actors", ["owner_user_id"])
    op.create_table(
        "project_performance_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("default_controller_type", sa.String(30), nullable=False, server_default="ai_agent"),
        sa.Column("default_control_mode", sa.String(20), nullable=False, server_default="autonomous"),
        sa.Column("allow_actor_reuse", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("allow_character_recasting", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project_id", name="uq_project_performance_settings_project"),
        sa.CheckConstraint("default_controller_type IN ('user', 'ai_agent', 'script_engine', 'system')", name="ck_performance_settings_controller"),
        sa.CheckConstraint("default_control_mode IN ('direct', 'command', 'assisted', 'autonomous', 'scripted')", name="ck_performance_settings_mode"),
    )
    op.create_index("ix_project_performance_settings_project_id", "project_performance_settings", ["project_id"])
    op.create_table(
        "casting_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project_characters.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("role_label", sa.String(100), nullable=False, server_default="Cast"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("controller_type", sa.String(30), nullable=False),
        sa.Column("controller_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("control_mode", sa.String(20), nullable=False),
        sa.Column("control_settings", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("assigned_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'ended', 'replaced')", name="ck_casting_assignments_status"),
        sa.CheckConstraint("controller_type IN ('user', 'ai_agent', 'script_engine', 'system')", name="ck_casting_assignments_controller"),
        sa.CheckConstraint("control_mode IN ('direct', 'command', 'assisted', 'autonomous', 'scripted')", name="ck_casting_assignments_mode"),
    )
    op.create_index("ix_casting_assignments_project_id", "casting_assignments", ["project_id"])
    op.create_index("ix_casting_assignments_actor_id", "casting_assignments", ["actor_id"])
    op.create_index("ix_casting_assignments_character_id", "casting_assignments", ["character_id"])
    op.create_index("uq_casting_assignments_active_character", "casting_assignments", ["project_id", "character_id"], unique=True, postgresql_where=sa.text("status = 'active'"), sqlite_where=sa.text("status = 'active'"))


def downgrade() -> None:
    op.drop_index("uq_casting_assignments_active_character", table_name="casting_assignments")
    op.drop_index("ix_casting_assignments_character_id", table_name="casting_assignments")
    op.drop_index("ix_casting_assignments_actor_id", table_name="casting_assignments")
    op.drop_index("ix_casting_assignments_project_id", table_name="casting_assignments")
    op.drop_table("casting_assignments")
    op.drop_index("ix_project_performance_settings_project_id", table_name="project_performance_settings")
    op.drop_table("project_performance_settings")
    op.drop_index("ix_actors_owner_user_id", table_name="actors")
    op.drop_table("actors")
