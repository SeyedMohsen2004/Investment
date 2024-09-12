"""new_col_inves

Revision ID: 75a785eac6c1
Revises: 04c9c9c0017e
Create Date: 2024-09-08 22:20:54.646584

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '75a785eac6c1'
down_revision = '04c9c9c0017e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add a new column to the "investment" table
    op.add_column('user', sa.Column('register_date', sa.Date()))


def downgrade() -> None:
    # Remove the new column from the "investment" table
    op.drop_column('user', 'register_date')