"""Add denormalized release discovery fields."""

from alembic import op
import sqlalchemy as sa

revision = "0026_release_discovery_fields"
down_revision = "0025_release_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("published_releases", sa.Column("genre", sa.String(length=80), server_default="", nullable=False))
    op.add_column("published_releases", sa.Column("category", sa.String(length=20), server_default="fiction", nullable=False))
    op.add_column("published_releases", sa.Column("format", sa.String(length=20), server_default="movie", nullable=False))
    op.add_column("published_releases", sa.Column("creator_name", sa.String(length=160), server_default="", nullable=False))
    op.create_index("ix_published_releases_visibility_published", "published_releases", ["visibility", "published_at"])
    op.create_index("ix_published_releases_genre", "published_releases", ["genre"])
    op.create_index("ix_published_releases_category", "published_releases", ["category"])
    op.create_index("ix_published_releases_format", "published_releases", ["format"])
    op.create_index("ix_published_releases_creator", "published_releases", ["creator_name"])


def downgrade() -> None:
    op.drop_index("ix_published_releases_creator", table_name="published_releases")
    op.drop_index("ix_published_releases_format", table_name="published_releases")
    op.drop_index("ix_published_releases_category", table_name="published_releases")
    op.drop_index("ix_published_releases_genre", table_name="published_releases")
    op.drop_index("ix_published_releases_visibility_published", table_name="published_releases")
    op.drop_column("published_releases", "creator_name")
    op.drop_column("published_releases", "format")
    op.drop_column("published_releases", "category")
    op.drop_column("published_releases", "genre")
