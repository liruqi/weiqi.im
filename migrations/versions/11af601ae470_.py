"""empty message

Revision ID: 11af601ae470
Revises: 889c4f6a8ef8
Create Date: 2016-05-01 20:12:07.912497

"""

# revision identifiers, used by Alembic.
revision = '11af601ae470'
down_revision = '889c4f6a8ef8'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('games', sa.Column('demo_control_display', sa.String(), nullable=False))
    op.add_column('games', sa.Column('demo_owner_display', sa.String(), nullable=False))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('games', 'demo_owner_display')
    op.drop_column('games', 'demo_control_display')
    ### end Alembic commands ###
