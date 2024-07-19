"""add user accepted terms at column

Revision ID: 2a88c56aa888
Revises: 7e5b5dc7342b
Create Date: 2024-07-19 14:00:57.042123

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import apps.webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '2a88c56aa888'
down_revision: Union[str, None] = '7e5b5dc7342b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('user', sa.Column('accepted_terms_at', sa.DateTime, nullable=True))

def downgrade():
    op.drop_column('user', 'accepted_terms_at')
