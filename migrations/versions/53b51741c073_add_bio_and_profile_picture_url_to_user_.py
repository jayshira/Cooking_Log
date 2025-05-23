"""Add bio and profile_picture_url to User model

Revision ID: 53b51741c073
Revises: 0fdefdf0b6f9
Create Date: 2025-05-16 22:21:59.528656

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '53b51741c073'
down_revision = '0fdefdf0b6f9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('bio', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('profile_picture_url', sa.String(length=255), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('profile_picture_url')
        batch_op.drop_column('bio')

    # ### end Alembic commands ###
