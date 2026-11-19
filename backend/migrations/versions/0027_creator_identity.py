"""Introduce persistent creator identities and link immutable releases to owners."""

import re
import uuid

from alembic import op
import sqlalchemy as sa

revision = "0027_creator_identity"
down_revision = "0026_release_discovery_fields"
branch_labels = None
depends_on = None


def _slug(value: str, user_id: uuid.UUID) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:140].strip("-") or "creator"
    return f"{base}-{str(user_id)[:8]}"


def upgrade() -> None:
    op.create_table(
        "creator_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("public_slug", sa.String(length=180), nullable=False),
        sa.Column("bio", sa.Text(), server_default="", nullable=False),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("website_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(public_slug)) > 0", name="ck_creator_profiles_slug_nonempty"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_creator_profiles_user"),
        sa.UniqueConstraint("public_slug", name="uq_creator_profiles_public_slug"),
    )
    op.create_index("ix_creator_profiles_user_id", "creator_profiles", ["user_id"])
    op.add_column("published_releases", sa.Column("creator_user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_published_releases_creator_user_id_users",
        "published_releases", "users", ["creator_user_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_published_releases_creator_user_id", "published_releases", ["creator_user_id"])

    bind = op.get_bind()
    users = sa.table("users",
        sa.column("id", sa.Uuid()), sa.column("display_name", sa.String()))
    profiles = sa.table("creator_profiles",
        sa.column("id", sa.Uuid()), sa.column("user_id", sa.Uuid()),
        sa.column("public_slug", sa.String()), sa.column("bio", sa.Text()),
    )
    for user_id, display_name in bind.execute(sa.select(users.c.id, users.c.display_name)):
        bind.execute(profiles.insert().values(
            id=uuid.uuid4(), user_id=user_id,
            public_slug=_slug(display_name or "creator", user_id), bio="",
        ))

    releases = sa.table("published_releases",
        sa.column("project_id", sa.Uuid()), sa.column("creator_user_id", sa.Uuid()))
    projects = sa.table("projects",
        sa.column("id", sa.Uuid()), sa.column("owner_user_id", sa.Uuid()))
    bind.execute(
        releases.update().values(creator_user_id=sa.select(projects.c.owner_user_id)
            .where(projects.c.id == releases.c.project_id).scalar_subquery())
    )


def downgrade() -> None:
    op.drop_index("ix_published_releases_creator_user_id", table_name="published_releases")
    op.drop_constraint("fk_published_releases_creator_user_id_users", "published_releases", type_="foreignkey")
    op.drop_column("published_releases", "creator_user_id")
    op.drop_index("ix_creator_profiles_user_id", table_name="creator_profiles")
    op.drop_table("creator_profiles")
