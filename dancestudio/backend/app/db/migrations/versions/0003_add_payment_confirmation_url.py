"""Add confirmation_url column to payments

Revision ID: 0003_add_payment_confirmation_url
Revises: 0002_admin_login
Create Date: 2024-05-26
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_add_payment_confirmation_url"
down_revision = "0002_admin_login"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column("confirmation_url", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payments", "confirmation_url")
