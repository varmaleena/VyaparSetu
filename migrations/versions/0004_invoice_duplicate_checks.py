"""Store duplicate screening results and index prior invoice observations."""

import sqlalchemy as sa
from alembic import op

revision = "0004_invoice_duplicate_checks"
down_revision = "0003_supplier_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invoice_duplicate_checks",
        sa.Column(
            "intake_id",
            sa.String(36),
            sa.ForeignKey("invoice_intakes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "merchant_id", sa.String(36), sa.ForeignKey("merchants.id"), nullable=False
        ),
        sa.Column("supplier_gstin", sa.String(15), nullable=False),
        sa.Column("invoice_number", sa.String(160), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("total_paise", sa.BigInteger(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("image_sha256", sa.String(64), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    for suffix, columns in {
        "fingerprint": ["fingerprint"],
        "image": ["image_sha256"],
        "date_amount": ["invoice_date", "total_paise"],
        "invoice_number": ["invoice_number", "invoice_date"],
    }.items():
        op.create_index(
            f"ix_duplicate_{suffix}",
            "invoice_duplicate_checks",
            ["merchant_id", "supplier_gstin", *columns],
        )


def downgrade() -> None:
    op.drop_table("invoice_duplicate_checks")
