"""add language to interview_session

Revision ID: fe742c42a681
Revises: df0746987e94
Create Date: 2026-02-03 17:42:24.605664

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'fe742c42a681'
down_revision: Union[str, Sequence[str], None] = 'df0746987e94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("interview_sessions")}
    
    if "language" not in columns:
        op.add_column(
            "interview_sessions",
            sa.Column("language", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('interview_sessions', 'language')
