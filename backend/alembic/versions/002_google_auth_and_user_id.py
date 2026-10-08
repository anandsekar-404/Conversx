"""Add Google Auth & ConversX User ID fields

Revision ID: 002_google_auth_and_user_id
Revises: 001_initial_schema
Create Date: 2026-10-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '002_google_auth_and_user_id'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('google_subject', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('users', sa.Column('display_name', sa.String(length=128), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('conversx_user_id', sa.String(length=64), nullable=True))
    op.add_column('users', sa.Column('conversx_user_id_normalized', sa.String(length=64), nullable=True))
    op.add_column('users', sa.Column('onboarding_completed', sa.Boolean(), server_default='false', nullable=False))

    op.create_index(op.f('ix_users_google_subject'), 'users', ['google_subject'], unique=True)
    op.create_index(op.f('ix_users_conversx_user_id_normalized'), 'users', ['conversx_user_id_normalized'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_conversx_user_id_normalized'), table_name='users')
    op.drop_index(op.f('ix_users_google_subject'), table_name='users')
    op.drop_column('users', 'onboarding_completed')
    op.drop_column('users', 'conversx_user_id_normalized')
    op.drop_column('users', 'conversx_user_id')
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'display_name')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'google_subject')
