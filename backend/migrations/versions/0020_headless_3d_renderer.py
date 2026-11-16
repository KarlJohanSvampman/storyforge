"""Allow durable headless Three.js render jobs."""
from alembic import op

revision = "0020_headless_3d_renderer"
down_revision = "0019_headless_animatic_render"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_video_render_jobs_source", "video_render_jobs", type_="check")
    op.create_check_constraint(
        "ck_video_render_jobs_source",
        "video_render_jobs",
        "render_source IN ('webm_upload', 'headless_animatic', 'headless_3d')",
    )


def downgrade() -> None:
    op.execute(
        "UPDATE video_render_jobs SET status = 'failed', "
        "error_message = 'Headless 3D jobs are not supported after downgrade.', "
        "completed_at = CURRENT_TIMESTAMP "
        "WHERE render_source = 'headless_3d' AND status IN ('queued', 'running')"
    )
    op.execute(
        "UPDATE video_render_jobs SET render_source = 'headless_animatic' "
        "WHERE render_source = 'headless_3d'"
    )
    op.drop_constraint("ck_video_render_jobs_source", "video_render_jobs", type_="check")
    op.create_check_constraint(
        "ck_video_render_jobs_source",
        "video_render_jobs",
        "render_source IN ('webm_upload', 'headless_animatic')",
    )
