"""add ml_risk_score columns to scan_results

Revision ID: 69fdaf6f09a6
Revises: 0e4b06a15cc9
Create Date: 2026-06-25 13:15:56.239274

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69fdaf6f09a6'
down_revision: Union[str, Sequence[str], None] = '0e4b06a15cc9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "scan_results",
        sa.Column("ml_risk_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("ml_risk_tier", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("scan_results", "ml_risk_tier")
    op.drop_column("scan_results", "ml_risk_score")
