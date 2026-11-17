"""Add release ratings, reviews, reactions and reports."""

from alembic import op
import sqlalchemy as sa

revision = "0025_release_feedback"
down_revision = "0024_project_credit_consents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "release_ratings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("release_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("score >= 1 AND score <= 10", name="ck_release_ratings_score"),
        sa.ForeignKeyConstraint(["release_id"], ["published_releases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("release_id", "user_id", name="uq_release_ratings_release_user"),
    )
    op.create_index("ix_release_ratings_release_id", "release_ratings", ["release_id"])
    op.create_index("ix_release_ratings_user_id", "release_ratings", ["user_id"])
    op.create_index("ix_release_ratings_release_score", "release_ratings", ["release_id", "score"])

    op.create_table(
        "release_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("release_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("contains_spoilers", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="visible", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('visible', 'hidden')", name="ck_release_reviews_status"),
        sa.ForeignKeyConstraint(["release_id"], ["published_releases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("release_id", "user_id", name="uq_release_reviews_release_user"),
    )
    op.create_index("ix_release_reviews_release_id", "release_reviews", ["release_id"])
    op.create_index("ix_release_reviews_user_id", "release_reviews", ["user_id"])
    op.create_index("ix_release_reviews_release_visible", "release_reviews", ["release_id", "status", "created_at"])

    op.create_table(
        "release_review_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("review_id", sa.Uuid(), nullable=False),
        sa.Column("reporter_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('open', 'resolved')", name="ck_release_review_reports_status"),
        sa.ForeignKeyConstraint(["review_id"], ["release_reviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("review_id", "reporter_user_id", name="uq_release_review_reports_review_reporter"),
    )
    op.create_index("ix_release_review_reports_review_id", "release_review_reports", ["review_id"])
    op.create_index("ix_release_review_reports_reporter_user_id", "release_review_reports", ["reporter_user_id"])

    op.create_table(
        "release_review_reactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("review_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("reaction", sa.String(length=20), server_default="helpful", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("reaction = 'helpful'", name="ck_release_review_reactions_kind"),
        sa.ForeignKeyConstraint(["review_id"], ["release_reviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("review_id", "user_id", name="uq_release_review_reactions_review_user"),
    )
    op.create_index("ix_release_review_reactions_review_id", "release_review_reactions", ["review_id"])
    op.create_index("ix_release_review_reactions_user_id", "release_review_reactions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_release_review_reactions_user_id", table_name="release_review_reactions")
    op.drop_index("ix_release_review_reactions_review_id", table_name="release_review_reactions")
    op.drop_table("release_review_reactions")
    op.drop_index("ix_release_review_reports_reporter_user_id", table_name="release_review_reports")
    op.drop_index("ix_release_review_reports_review_id", table_name="release_review_reports")
    op.drop_table("release_review_reports")
    op.drop_index("ix_release_reviews_release_visible", table_name="release_reviews")
    op.drop_index("ix_release_reviews_user_id", table_name="release_reviews")
    op.drop_index("ix_release_reviews_release_id", table_name="release_reviews")
    op.drop_table("release_reviews")
    op.drop_index("ix_release_ratings_release_score", table_name="release_ratings")
    op.drop_index("ix_release_ratings_user_id", table_name="release_ratings")
    op.drop_index("ix_release_ratings_release_id", table_name="release_ratings")
    op.drop_table("release_ratings")
