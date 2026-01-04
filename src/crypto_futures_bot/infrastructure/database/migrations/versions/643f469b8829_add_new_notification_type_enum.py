"""Convert notification_type enum to VARCHAR

Revision ID: 643f469b8829
Revises: cbe21a14a3b0
Create Date: 2026-01-04 12:52:21.821936
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "643f469b8829"
down_revision: str | Sequence[str] | None = "cbe21a14a3b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: convert notification_type from Enum to VARCHAR."""
    with op.batch_alter_table("push_notification") as batch_op:
        batch_op.alter_column(
            "notification_type",
            existing_type=sa.Enum("SIGNALS", "FATAL_ERRORS", name="pushnotificationtypeenum"),
            type_=sa.String(length=50),
            nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema: convert notification_type back to Enum."""
    # Optional: remove any rows that contain values outside the original enum
    op.execute(
        """
        DELETE FROM push_notification
        WHERE notification_type NOT IN ('SIGNALS', 'FATAL_ERRORS')
        """
    )
    with op.batch_alter_table("push_notification") as batch_op:
        batch_op.alter_column(
            "notification_type",
            existing_type=sa.String(length=50),
            type_=sa.Enum("SIGNALS", "FATAL_ERRORS", name="pushnotificationtypeenum"),
            nullable=False,
        )
