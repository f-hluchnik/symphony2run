"""add verified and excluded columns

Revision ID: d432ee45a620
Revises: 
Create Date: 2026-04-29 22:00:45.162170

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd432ee45a620'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('works', sa.Column('verified', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('works', sa.Column('excluded', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    pass
