"""Persist consent-bound simulated payments by invoice intake."""

import sqlalchemy as sa
from alembic import op

revision = "0007_payment_proposals"
down_revision = "0006_merchant_funding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_proposals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "intake_id",
            sa.String(36),
            sa.ForeignKey("invoice_intakes.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "merchant_id", sa.String(36), sa.ForeignKey("merchants.id"), nullable=False
        ),
        sa.Column(
            "supplier_id", sa.String(36), sa.ForeignKey("suppliers.id"), nullable=False
        ),
        sa.Column("invoice_key", sa.String(200), nullable=False),
        sa.Column("account_token", sa.String(160), nullable=False),
        sa.Column("terms", sa.JSON(), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("consent_at", sa.DateTime(timezone=True)),
        sa.Column("receipt", sa.JSON(none_as_null=True)),
        sa.UniqueConstraint(
            "merchant_id",
            "supplier_id",
            "invoice_key",
            name="uq_payment_proposal_invoice",
        ),
    )


def downgrade() -> None:
    op.drop_table("payment_proposals")
