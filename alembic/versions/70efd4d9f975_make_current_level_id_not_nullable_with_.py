"""Make current_level_id not nullable with default 0

Revision ID: 70efd4d9f975
Revises: 26951bb70a8a
Create Date: 2024-12-29 00:29:22.979414

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '70efd4d9f975'
down_revision: Union[str, None] = '26951bb70a8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Ensure existing rows have a default value for `current_level_id`
    op.execute('UPDATE "user" SET current_level_id = 0 WHERE current_level_id IS NULL')

    # Alter `current_level_id` column to be non-nullable and set default to 0
    op.alter_column('user', 'current_level_id',
                    existing_type=sa.INTEGER(),
                    nullable=False,
                    server_default='0')

    # Add unique constraint to `wallet_address`
    op.create_unique_constraint('uq_user_wallet_address', 'user', ['wallet_address'])


def downgrade() -> None:
    # Remove the unique constraint on `wallet_address`
    op.drop_constraint('uq_user_wallet_address', 'user', type_='unique')

    # Revert `current_level_id` column to nullable and remove default
    op.alter_column('user', 'current_level_id',
                    existing_type=sa.INTEGER(),
                    nullable=True,
                    server_default=None)
