"""Create the VyaparSetu foundation schema."""

import sqlalchemy as sa
from alembic import op

revision = "0001_foundations"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "merchants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("language", sa.String(160), nullable=False),
        sa.Column("available_cash", sa.Numeric(14, 2), nullable=False),
        sa.Column("existing_edi_daily", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "suppliers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("gstin", sa.String(160), unique=True, nullable=False),
        sa.Column("account_token", sa.String(160), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "invoices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "merchant_id", sa.String(36), sa.ForeignKey("merchants.id"), nullable=False
        ),
        sa.Column(
            "supplier_id", sa.String(36), sa.ForeignKey("suppliers.id"), nullable=False
        ),
        sa.Column("invoice_number", sa.String(160), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("discount_percent", sa.Numeric(14, 2), nullable=False),
        sa.Column("discount_requires_full_payment", sa.Boolean(), nullable=False),
        sa.Column("discount_deadline", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "merchant_id",
            "supplier_id",
            "invoice_number",
            name="uq_invoice_merchant_supplier_number",
        ),
    )
    op.create_table(
        "settlements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "merchant_id", sa.String(36), sa.ForeignKey("merchants.id"), nullable=False
        ),
        sa.Column("settlement_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "merchant_id", "settlement_date", name="uq_settlement_merchant_date"
        ),
    )
    op.create_table(
        "decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "invoice_id", sa.String(36), sa.ForeignKey("invoices.id"), nullable=False
        ),
        sa.Column("status", sa.String(160), nullable=False),
        sa.Column("approved_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("policy_version", sa.String(160), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "consents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "decision_id", sa.String(36), sa.ForeignKey("decisions.id"), nullable=False
        ),
        sa.Column("status", sa.String(160), nullable=False),
        sa.Column("language", sa.String(160), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "payments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "decision_id", sa.String(36), sa.ForeignKey("decisions.id"), nullable=False
        ),
        sa.Column(
            "supplier_id", sa.String(36), sa.ForeignKey("suppliers.id"), nullable=False
        ),
        sa.Column("idempotency_key", sa.String(160), unique=True, nullable=False),
        sa.Column("status", sa.String(160), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "edi_schedules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "payment_id", sa.String(36), sa.ForeignKey("payments.id"), nullable=False
        ),
        sa.Column("daily_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("tenor_days", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(160), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "merchant_id", sa.String(36), sa.ForeignKey("merchants.id"), nullable=False
        ),
        sa.Column(
            "invoice_id", sa.String(36), sa.ForeignKey("invoices.id"), nullable=True
        ),
        sa.Column("session_id", sa.String(160), nullable=False),
        sa.Column("event_type", sa.String(160), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("edi_schedules")
    op.drop_table("payments")
    op.drop_table("consents")
    op.drop_table("decisions")
    op.drop_table("settlements")
    op.drop_table("invoices")
    op.drop_table("suppliers")
    op.drop_table("merchants")
