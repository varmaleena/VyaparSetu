"""Store invoice images before supplier and invoice fields are extracted."""

import sqlalchemy as sa
from alembic import op

revision = "0002_invoice_intake"
down_revision = "0001_foundations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invoice_intakes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "merchant_id", sa.String(36), sa.ForeignKey("merchants.id"), nullable=False
        ),
        sa.Column("session_id", sa.String(160), nullable=False),
        sa.Column("object_uri", sa.Text(), nullable=False, unique=True),
        sa.Column("object_generation", sa.BigInteger(), nullable=False),
        sa.Column("media_type", sa.String(32), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_invoice_intake_owner", "invoice_intakes", ["merchant_id", "session_id"]
    )


def downgrade() -> None:
    op.drop_table("invoice_intakes")
