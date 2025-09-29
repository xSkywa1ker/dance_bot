from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tg_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=255)),
        sa.Column("age", sa.Integer()),
        sa.Column("phone", sa.String(length=32)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "directions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
    )

    slot_status = postgresql.ENUM("scheduled", "canceled", "completed", name="slotstatus")
    slot_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "class_slots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("direction_id", sa.Integer(), sa.ForeignKey("directions.id", ondelete="CASCADE")),
        sa.Column("starts_at", sa.DateTime(timezone=True), index=True),
        sa.Column("duration_min", sa.Integer()),
        sa.Column("capacity", sa.Integer()),
        sa.Column("price_single_visit", sa.Numeric(10, 2)),
        sa.Column("allow_subscription", sa.Boolean(), server_default=sa.true()),
        sa.Column("status", slot_status, server_default="scheduled"),
        sa.UniqueConstraint("direction_id", "starts_at", name="uq_class_slot_direction_time"),
        sa.CheckConstraint("capacity > 0", name="ck_class_slot_capacity_positive"),
    )

    booking_status = postgresql.ENUM(
        "reserved",
        "confirmed",
        "canceled",
        "late_cancel",
        "attended",
        "no_show",
        name="bookingstatus",
    )
    booking_status.create(op.get_bind(), checkfirst=True)
    booking_source = postgresql.ENUM("bot", "admin", name="bookingsource")
    booking_source.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("class_slot_id", sa.Integer(), sa.ForeignKey("class_slots.id", ondelete="CASCADE")),
        sa.Column("status", booking_status, server_default="reserved"),
        sa.Column("source", booking_source, server_default="bot"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("canceled_at", sa.DateTime(timezone=True)),
        sa.Column("canceled_by", sa.String(length=64)),
        sa.Column("cancellation_reason", sa.String(length=255)),
        sa.UniqueConstraint("user_id", "class_slot_id", name="uq_booking_user_slot"),
    )
    op.create_index("ix_booking_class_slot", "bookings", ["class_slot_id"])

    product_type = postgresql.ENUM("subscription", "single", name="producttype")
    product_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type", product_type, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("price", sa.Numeric(10, 2)),
        sa.Column("classes_count", sa.Integer()),
        sa.Column("validity_days", sa.Integer()),
        sa.Column("direction_limit_id", sa.Integer(), sa.ForeignKey("directions.id")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
    )

    subscription_status = postgresql.ENUM("active", "expired", "frozen", name="subscriptionstatus")
    subscription_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id")),
        sa.Column("remaining_classes", sa.Integer()),
        sa.Column("valid_from", sa.DateTime(timezone=True)),
        sa.Column("valid_to", sa.DateTime(timezone=True)),
        sa.Column("status", subscription_status, server_default="active"),
    )
    op.create_index("ix_subscription_user", "subscriptions", ["user_id"])

    payment_status = postgresql.ENUM("pending", "paid", "failed", "canceled", "refunded", name="paymentstatus")
    payment_status.create(op.get_bind(), checkfirst=True)
    payment_purpose = postgresql.ENUM("single_visit", "subscription", name="paymentpurpose")
    payment_purpose.create(op.get_bind(), checkfirst=True)
    payment_provider = postgresql.ENUM("yookassa", "stripe", "tinkoff", "cloudpayments", name="paymentprovider")
    payment_provider.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id")),
        sa.Column("class_slot_id", sa.Integer(), sa.ForeignKey("class_slots.id")),
        sa.Column("amount", sa.Numeric(10, 2)),
        sa.Column("currency", sa.CHAR(length=3), server_default="RUB"),
        sa.Column("provider", payment_provider),
        sa.Column("order_id", sa.String(length=64), unique=True),
        sa.Column("provider_payment_id", sa.String(length=128)),
        sa.Column("status", payment_status, server_default="pending"),
        sa.Column("purpose", payment_purpose),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_payments_order_id", "payments", ["order_id"], unique=True)

    waitlist_status = postgresql.ENUM("active", "notified", "joined", "expired", name="waitliststatus")
    waitlist_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "waitlist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("class_slot_id", sa.Integer(), sa.ForeignKey("class_slots.id", ondelete="CASCADE")),
        sa.Column("status", waitlist_status, server_default="active"),
        sa.UniqueConstraint("user_id", "class_slot_id", name="uq_waitlist_user_slot"),
    )

    admin_role = postgresql.ENUM("admin", "manager", "viewer", name="adminrole")
    admin_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), unique=True),
        sa.Column("password_hash", sa.String(length=255)),
        sa.Column("role", admin_role, server_default="viewer"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
    )

    actor_type = postgresql.ENUM("user", "admin", "system", name="actortype")
    actor_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_type", actor_type),
        sa.Column("actor_id", sa.Integer()),
        sa.Column("action", sa.String(length=255)),
        sa.Column("payload", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("admin_users")
    op.drop_table("waitlist")
    op.drop_index("ix_payments_order_id", table_name="payments")
    op.drop_table("payments")
    op.drop_table("subscriptions")
    op.drop_table("products")
    op.drop_index("ix_booking_class_slot", table_name="bookings")
    op.drop_table("bookings")
    op.drop_table("class_slots")
    op.drop_table("directions")
    op.drop_table("users")
