"""Add setting media table and subscription initial classes

Revision ID: 0006_add_setting_media_and_manual_subscription
Revises: 0005_extend_payment_provider
Create Date: 2025-10-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0006_add_setting_media_and_manual_subscription"
down_revision = "0005_extend_payment_provider"
branch_labels = None
depends_on = None


media_type_enum = postgresql.ENUM(
    "image",
    "video",
    name="settingmediatype",
    create_type=False,
)


def upgrade() -> None:
    postgresql.ENUM("image", "video", name="settingmediatype").create(
        op.get_bind(), checkfirst=True
    )

    op.create_table(
        "setting_media",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("setting_key", sa.String(length=64), nullable=False),
        sa.Column("file_path", sa.String(length=255), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column(
            "media_type",
            media_type_enum,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["setting_key"], ["settings.key"], ondelete="CASCADE"),
    )

    op.add_column(
        "subscriptions",
        sa.Column("initial_classes", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "initial_classes")
    op.drop_table("setting_media")

    postgresql.ENUM("image", "video", name="settingmediatype").drop(
        op.get_bind(), checkfirst=True
    )
