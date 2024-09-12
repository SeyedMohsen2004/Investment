"""delete_col_invs

Revision ID: 9a2a43e9d144
Revises: 75a785eac6c1
Create Date: 2024-09-08 22:34:03.220613

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9a2a43e9d144'
down_revision = '75a785eac6c1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the column 'confirm_check_date' from the 'investment' table
    op.drop_column('investment', 'starter_date')

def downgrade() -> None:
    # Add the column 'confirm_check_date' back to the 'investment' table in case of downgrade
    op.add_column('investment', sa.Column('starter_date', sa.Date(), nullable=True))