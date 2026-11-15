"""Add typed screenplay elements to immutable scene script versions."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_structured_screenplay"
down_revision = "0006_storyboard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scene_script_elements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("script_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scene_script_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("element_order", sa.Integer(), nullable=False),
        sa.Column("element_type", sa.String(length=30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project_characters.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("character_name_snapshot", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("script_version_id", "element_order", name="uq_scene_script_elements_order"),
        sa.CheckConstraint("element_order >= 1", name="ck_scene_script_elements_positive_order"),
        sa.CheckConstraint(
            "element_type IN ('action', 'dialogue', 'parenthetical', 'transition', 'production_note')",
            name="ck_scene_script_elements_type",
        ),
        sa.CheckConstraint(
            "element_type != 'dialogue' OR character_id IS NOT NULL",
            name="ck_scene_script_elements_dialogue_character",
        ),
    )
    op.create_index("ix_scene_script_elements_script_version_id", "scene_script_elements", ["script_version_id"])


def downgrade() -> None:
    op.drop_index("ix_scene_script_elements_script_version_id", table_name="scene_script_elements")
    op.drop_table("scene_script_elements")
