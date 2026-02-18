"""merge dev and main migration branches

Revision ID: 1119b51e758d
Revises: 1c749d65c84e, f8a13a739def
Create Date: 2026-02-10 08:08:00.444126

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '1119b51e758d'
down_revision: Union[str, Sequence[str], None] = ('1c749d65c84e', 'f8a13a739def')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
