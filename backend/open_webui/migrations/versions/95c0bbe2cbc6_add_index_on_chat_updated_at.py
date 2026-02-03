"""add index on chat updated_at

Revision ID: 95c0bbe2cbc6
Revises: f47e8b9c1d23
Create Date: 2026-02-03 11:46:16.062725

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '95c0bbe2cbc6'
down_revision: Union[str, None] = 'f47e8b9c1d23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_index(
        "idx_chat_updated_at",
        "chat",
        ["updated_at"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "idx_chat_updated_at",
        table_name="chat",
    )
