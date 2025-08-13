"""Add notifications table

Revision ID: 2652b286f6cb
Revises: 118d4ef0454d
Create Date: 2025-07-16 09:17:54.047565

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2652b286f6cb"
down_revision: Union[str, None] = "ed37e461f285"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME: str = "notifications"


def upgrade() -> None:
    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("user_id", sa.Text, nullable=False, index=True),
        sa.Column("message_type", sa.Text, nullable=False),
        sa.Column("notification_type", sa.Text, nullable=False),
        sa.Column("notifier_used", sa.Text, nullable=False),
        sa.Column("is_sent", sa.Boolean, nullable=False),
        sa.Column("is_received", sa.Boolean, nullable=True),
        sa.Column("status", sa.Text, nullable=True),
        sa.Column("created_at", sa.BigInteger, nullable=False),
        sa.Column("updated_at", sa.BigInteger, nullable=False),
    )

    # TODO: Populate table so that only new users get the welcome message.


def downgrade() -> None:
    op.drop_table(table_name=TABLE_NAME)
