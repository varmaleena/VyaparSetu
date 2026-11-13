"""Store normalized pre-tax purchase-order reference prices."""

import sqlalchemy as sa
from alembic import op

revision = "0005_purchase_order_prices"
down_revision = "0004_invoice_duplicate_checks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "purchase_order_prices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "merchant_id", sa.String(36), sa.ForeignKey("merchants.id"), nullable=False
        ),
        sa.Column(
            "supplier_gstin",
            sa.String(160),
            sa.ForeignKey("suppliers.gstin", onupdate="CASCADE"),
            nullable=False,
        ),
        sa.Column("purchase_order_number", sa.String(80), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.Column("hsn", sa.String(8), nullable=False),
        sa.Column("unit", sa.String(40), nullable=False),
        sa.Column("unit_price_paise", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("unit_price_paise > 0", name="ck_po_positive_price"),
    )
    op.create_index(
        "ix_po_price_scope",
        "purchase_order_prices",
        ["merchant_id", "supplier_gstin", "purchase_order_number"],
    )


def downgrade() -> None:
    op.drop_table("purchase_order_prices")
