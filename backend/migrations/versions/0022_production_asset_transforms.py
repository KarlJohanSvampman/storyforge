"""Persist per-binding 3D placement transforms for renderer integration."""
from alembic import op
import sqlalchemy as sa

revision = "0022_production_asset_transforms"
down_revision = "0021_production_asset_library"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "production_asset_bindings",
        sa.Column(
            "transform_json", sa.JSON(), nullable=False,
            server_default=sa.text("""'{"position":[0,0,0],"rotation":[0,0,0],"scale":[1,1,1]}'"""),
        ),
    )


def downgrade() -> None:
    op.drop_column("production_asset_bindings", "transform_json")
