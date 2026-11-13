"""Persist merchant funding inputs for payment decisions."""

import sqlalchemy as sa
from alembic import op

revision = "0006_merchant_funding"
down_revision = "0005_purchase_order_prices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "merchant_funding",
        sa.Column(
            "merchant_id",
            sa.String(36),
            sa.ForeignKey("merchants.id"),
            primary_key=True,
        ),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=False),
        sa.Column("instant_net", sa.BigInteger(), nullable=False),
        sa.Column("instant_fee", sa.BigInteger(), nullable=False),
        sa.Column("offer_version", sa.String(80)),
        sa.Column("daily_rate_bps", sa.Integer()),
        sa.Column("fee_paise", sa.BigInteger()),
        sa.Column("tenor_days", sa.Integer()),
    )


def downgrade() -> None:
    op.drop_table("merchant_funding")
