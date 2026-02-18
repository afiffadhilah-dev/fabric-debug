"""merge heads

Revision ID: 839991411da5
Revises: 50b9546ecded, a9d8f7c6b5e4
Create Date: 2026-02-12 13:37:05.492123

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '839991411da5'
down_revision: Union[str, Sequence[str], None] = ('50b9546ecded', 'a9d8f7c6b5e4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
