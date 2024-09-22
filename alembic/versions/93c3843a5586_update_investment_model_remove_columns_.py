"""Update Investment model - remove columns, add withdrawable_profit

Revision ID: 93c3843a5586
Revises: 9a3be82d92cd
Create Date: 2024-09-18 13:52:21.434779

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '93c3843a5586'
down_revision: Union[str, None] = '9a3be82d92cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### Add the new column withdrawable_profit ###
    op.add_column('investment', sa.Column('withdrawable_profit', sa.Float(), nullable=False, server_default='0'))

    # ### Remove the old columns profit and is_confirmed ###
    op.drop_column('investment', 'profit')
    op.drop_column('investment', 'is_confirmed')

    # ### Additional auto-generated changes (if needed) ###
    op.alter_column('investment', 'cycle_length',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.add_column('user_transaction', sa.Column('type_tran', sa.String(), nullable=True))
    op.alter_column('user_transaction', 'request_date',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)


def downgrade() -> None:
    # ### Revert the changes made in upgrade ###
    
    # Restore profit and is_confirmed columns
    op.add_column('investment', sa.Column('profit', sa.Float(), nullable=True))
    op.add_column('investment', sa.Column('is_confirmed', sa.Boolean(), nullable=False, server_default='false'))

    # Remove withdrawable_profit column
    op.drop_column('investment', 'withdrawable_profit')

    # ### Additional auto-generated changes (if needed) ###
    op.alter_column('investment', 'cycle_length',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.drop_column('user_transaction', 'type_tran')
    op.alter_column('user_transaction', 'request_date',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
