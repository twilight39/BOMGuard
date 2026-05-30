"""add users and user_preferences tables

Revision ID: 9f1d5a38fef5
Revises: 0001_initial_schema
Create Date: 2026-05-30 01:06:57.138668

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9f1d5a38fef5"
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.String(50), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column(
            "subscribed_regulation_ids",
            postgresql.ARRAY(sa.String()),
            server_default="{}",
        ),
        sa.Column(
            "default_regulation_ids",
            postgresql.ARRAY(sa.String()),
            server_default="{}",
        ),
        sa.Column("email_notifications", sa.Boolean(), server_default=sa.text("true")),
    )

    op.add_column(
        "boms",
        sa.Column("user_id", sa.String(50), sa.ForeignKey("users.id"), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("boms", "user_id")
    op.drop_table("user_preferences")
    op.drop_table("users")
