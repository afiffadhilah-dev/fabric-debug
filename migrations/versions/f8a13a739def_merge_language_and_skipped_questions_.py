"""merge language and skipped_questions branches

Revision ID: f8a13a739def
Revises: 143fb069d2ff, fe742c42a681
Create Date: 2026-02-05 15:50:07.520224

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'f8a13a739def'
down_revision: Union[str, Sequence[str], None] = ('143fb069d2ff', 'fe742c42a681')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
