"""Add stub and telegram providers to payment enum

Revision ID: 0005_extend_payment_provider
Revises: 0004_add_settings_table
Create Date: 2025-10-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0005_extend_payment_provider"
down_revision = "0004_add_settings_table"
branch_labels = None
depends_on = None


OLD_PAYMENT_PROVIDERS = (
    "yookassa",
    "stripe",
    "tinkoff",
    "cloudpayments",
)

NEW_PAYMENT_PROVIDERS = OLD_PAYMENT_PROVIDERS + (
    "stub",
    "telegram",
)


def upgrade() -> None:
    for provider in NEW_PAYMENT_PROVIDERS[len(OLD_PAYMENT_PROVIDERS) :]:
        op.execute(
            sa.text(
                "ALTER TYPE paymentprovider ADD VALUE IF NOT EXISTS :provider"
            ).bindparams(provider=provider)
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE payments SET provider = 'yookassa' "
            "WHERE provider IN ('stub', 'telegram')"
        )
    )

    payment_provider_old = postgresql.ENUM(
        *OLD_PAYMENT_PROVIDERS,
        name="paymentprovider_old",
    )
    payment_provider_old.create(op.get_bind(), checkfirst=False)

    op.execute(
        "ALTER TABLE payments ALTER COLUMN provider TYPE paymentprovider_old "
        "USING provider::text::paymentprovider_old"
    )

    op.execute("DROP TYPE paymentprovider")
    op.execute("ALTER TYPE paymentprovider_old RENAME TO paymentprovider")
