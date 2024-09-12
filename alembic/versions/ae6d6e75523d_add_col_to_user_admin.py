"""add_col_to_user_admin

Revision ID: ae6d6e75523d
Revises: a43dd452f0d2
Create Date: 2024-09-12 09:20:00.060971

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ae6d6e75523d'
down_revision = 'a43dd452f0d2'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Add the admin column as nullable
    op.add_column('user', sa.Column('admin', sa.Boolean(), nullable=True))

    # Step 2: Set default value (False) for existing records
    op.execute('UPDATE "user" SET admin = False')

    # Step 3: Alter the column to be non-nullable
    op.alter_column('user', 'admin', nullable=False)


def downgrade():
    # Remove the admin column in the downgrade function
    op.drop_column('user', 'admin')