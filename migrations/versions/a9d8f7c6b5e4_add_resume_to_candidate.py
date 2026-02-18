"""add_resume_to_candidate_table

Revision ID: a9d8f7c6b5e4
Revises: 1119b51e758d
Create Date: 2026-02-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a9d8f7c6b5e4'
down_revision: Union[str, Sequence[str], None] = '1119b51e758d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("candidate")}

    if "resume" not in columns:
        op.add_column(
            'candidate',
            sa.Column('resume', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('candidate', 'resume')
