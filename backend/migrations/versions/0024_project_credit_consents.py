"""Add revocable opt-in project credit consents."""

from alembic import op
import sqlalchemy as sa

revision = "0024_project_credit_consents"
down_revision = "0023_published_releases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_credit_consents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("role_label", sa.String(length=100), nullable=False),
        sa.Column("public_name", sa.String(length=160), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("consented_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("category IN ('contributor', 'cast', 'production')", name="ck_project_credit_consents_category"),
        sa.CheckConstraint("(category = 'cast' AND actor_id IS NOT NULL) OR (category != 'cast' AND actor_id IS NULL)", name="ck_project_credit_consents_actor"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["actors.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_credit_consents_project_id", "project_credit_consents", ["project_id"])
    op.create_index("ix_project_credit_consents_user_id", "project_credit_consents", ["user_id"])
    op.create_index("ix_project_credit_consents_project_active", "project_credit_consents", ["project_id", "revoked_at"])


def downgrade() -> None:
    op.drop_index("ix_project_credit_consents_project_active", table_name="project_credit_consents")
    op.drop_index("ix_project_credit_consents_user_id", table_name="project_credit_consents")
    op.drop_index("ix_project_credit_consents_project_id", table_name="project_credit_consents")
    op.drop_table("project_credit_consents")
