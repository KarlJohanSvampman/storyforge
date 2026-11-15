"""Add project format/category and TV-series season/episode structure."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_project_formats_series"
down_revision = "0007_structured_screenplay"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("format", sa.String(length=20), nullable=False, server_default="movie"),
    )
    op.add_column(
        "projects",
        sa.Column("category", sa.String(length=20), nullable=False, server_default="fiction"),
    )
    op.create_check_constraint(
        "ck_projects_format", "projects", "format IN ('movie', 'tv_series')",
    )
    op.create_check_constraint(
        "ck_projects_category", "projects", "category IN ('fiction', 'documentary')",
    )

    op.create_table(
        "storyboard_seasons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("storyboard_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("storyboards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("season_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("story_arc", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("storyboard_id", "season_number", name="uq_storyboard_seasons_number"),
        sa.CheckConstraint("season_number >= 1", name="ck_storyboard_seasons_positive_number"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_storyboard_seasons_status"),
    )
    op.create_index("ix_storyboard_seasons_storyboard_id", "storyboard_seasons", ["storyboard_id"])

    op.create_table(
        "storyboard_episodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("season_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("storyboard_seasons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("episode_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("logline", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("synopsis", sa.Text(), nullable=False, server_default=""),
        sa.Column("estimated_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("season_id", "episode_number", name="uq_storyboard_episodes_number"),
        sa.CheckConstraint("episode_number >= 1", name="ck_storyboard_episodes_positive_number"),
        sa.CheckConstraint("estimated_duration_seconds IS NULL OR estimated_duration_seconds > 0", name="ck_storyboard_episodes_duration"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_storyboard_episodes_status"),
    )
    op.create_index("ix_storyboard_episodes_season_id", "storyboard_episodes", ["season_id"])

    op.add_column(
        "storyboard_scenes",
        sa.Column("episode_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_storyboard_scenes_episode_id_storyboard_episodes",
        "storyboard_scenes", "storyboard_episodes", ["episode_id"], ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_storyboard_scenes_episode_id", "storyboard_scenes", ["episode_id"])

    op.drop_constraint("uq_storyboard_scenes_order", "storyboard_scenes", type_="unique")
    op.create_unique_constraint(
        "uq_storyboard_scenes_episode_order",
        "storyboard_scenes",
        ["storyboard_id", "episode_id", "scene_order"],
    )
    op.create_index(
        "uq_storyboard_scenes_movie_order",
        "storyboard_scenes",
        ["storyboard_id", "scene_order"],
        unique=True,
        postgresql_where=sa.text("episode_id IS NULL"),
    )


def downgrade() -> None:
    # Collapse episode-owned scenes back to one movie-style sequence per
    # storyboard before removing the series hierarchy. First move all scene
    # numbers above the current range so the positive-number and unique
    # constraints remain valid while the new sequence is assigned.
    op.execute("""
        UPDATE storyboard_scenes
        SET scene_order = scene_order + (
            SELECT COALESCE(MAX(scene_order), 0) + COUNT(*) + 1
            FROM storyboard_scenes
        )
    """)
    op.execute("""
        WITH ranked_scenes AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY storyboard_id
                       ORDER BY episode_id NULLS FIRST, scene_order, id
                   ) AS new_order
            FROM storyboard_scenes
        )
        UPDATE storyboard_scenes AS scenes
        SET scene_order = ranked_scenes.new_order,
            episode_id = NULL
        FROM ranked_scenes
        WHERE scenes.id = ranked_scenes.id
    """)

    op.drop_index("uq_storyboard_scenes_movie_order", table_name="storyboard_scenes")
    op.drop_constraint("uq_storyboard_scenes_episode_order", "storyboard_scenes", type_="unique")
    op.drop_index("ix_storyboard_scenes_episode_id", table_name="storyboard_scenes")
    op.drop_constraint(
        "fk_storyboard_scenes_episode_id_storyboard_episodes",
        "storyboard_scenes",
        type_="foreignkey",
    )
    op.drop_column("storyboard_scenes", "episode_id")
    op.create_unique_constraint(
        "uq_storyboard_scenes_order",
        "storyboard_scenes",
        ["storyboard_id", "scene_order"],
    )

    op.drop_index("ix_storyboard_episodes_season_id", table_name="storyboard_episodes")
    op.drop_table("storyboard_episodes")
    op.drop_index("ix_storyboard_seasons_storyboard_id", table_name="storyboard_seasons")
    op.drop_table("storyboard_seasons")

    op.drop_constraint("ck_projects_category", "projects", type_="check")
    op.drop_constraint("ck_projects_format", "projects", type_="check")
    op.drop_column("projects", "category")
    op.drop_column("projects", "format")
