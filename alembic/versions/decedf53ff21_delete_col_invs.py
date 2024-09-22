"""delete_col_invs

Revision ID: decedf53ff21
Revises: 9a3be82d92cd
Create Date: 2024-09-17 13:00:11.646598

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'decedf53ff21'
down_revision: Union[str, None] = '9a3be82d92cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Commands to upgrade the database (i.e., removing a column)
    op.drop_column('investment', 'is_confirmed')


def downgrade():
    # Commands to downgrade the database (i.e., restoring the column)
    op.add_column('investment', sa.Column('is_confirmed', sa.Boolean(), default=False))
    
    
    
