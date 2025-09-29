"""add login field to admin users

Revision ID: 0002_admin_login
Revises: 0001_initial
Create Date: 2024-05-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_admin_login"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("admin_users") as batch_op:
        batch_op.add_column(sa.Column("login", sa.String(length=255), nullable=True))

    op.execute("UPDATE admin_users SET login = email")

    with op.batch_alter_table("admin_users") as batch_op:
        batch_op.alter_column("login", nullable=False)
        batch_op.create_unique_constraint("uq_admin_users_login", ["login"])
        batch_op.drop_column("email")


def downgrade() -> None:
    with op.batch_alter_table("admin_users") as batch_op:
        batch_op.add_column(sa.Column("email", sa.String(length=255), nullable=True))

    op.execute("UPDATE admin_users SET email = login")

    with op.batch_alter_table("admin_users") as batch_op:
        batch_op.alter_column("email", nullable=False)
        batch_op.create_unique_constraint("admin_users_email_key", ["email"])
        batch_op.drop_constraint("uq_admin_users_login", type_="unique")
        batch_op.drop_column("login")
