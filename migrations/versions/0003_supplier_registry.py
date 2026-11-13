"""Add verified payout details to the supplier registry."""

import sqlalchemy as sa
from alembic import op

revision = "0003_supplier_registry"
down_revision = "0002_invoice_intake"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "suppliers",
        sa.Column(
            "registry_status",
            sa.String(16),
            nullable=False,
            server_default="UNVERIFIED",
        ),
    )
    op.add_column("suppliers", sa.Column("payout_account_name", sa.String(160)))
    op.add_column("suppliers", sa.Column("payout_last4", sa.String(4)))
    op.add_column(
        "suppliers",
        sa.Column(
            "payout_verified", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.create_check_constraint(
        "ck_supplier_registry_status",
        "suppliers",
        "registry_status IN ('ACTIVE', 'UNVERIFIED', 'BLOCKED')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_supplier_registry_status", "suppliers", type_="check")
    for column in (
        "payout_verified",
        "payout_last4",
        "payout_account_name",
        "registry_status",
    ):
        op.drop_column("suppliers", column)
