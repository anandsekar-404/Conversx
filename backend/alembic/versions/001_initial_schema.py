"""Initial schema creation

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-08 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=20), server_default='USER', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_banned', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. practice_sessions table
    op.create_table(
        'practice_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('scenario_id', sa.String(length=64), nullable=False),
        sa.Column('practice_type', sa.String(length=32), server_default='casual', nullable=False),
        sa.Column('attempt_number', sa.Integer(), server_default='1', nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('delivery_score', sa.Integer(), nullable=True),
        sa.Column('wpm', sa.Float(), nullable=True),
        sa.Column('filler_rate', sa.Float(), nullable=True),
        sa.Column('speaking_duration', sa.Float(), nullable=True),
        sa.Column('is_voice', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('dimension_scores', sa.JSON(), nullable=True),
        sa.Column('detected_issues_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_practice_sessions_user_id'), 'practice_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_practice_sessions_scenario_id'), 'practice_sessions', ['scenario_id'], unique=False)

    # 3. moderation_events table
    op.create_table(
        'moderation_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('severity', sa.Integer(), server_default='0', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='safe', nullable=False),
        sa.Column('matched_rules', sa.JSON(), nullable=True),
        sa.Column('action_taken', sa.String(length=32), server_default='none', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_moderation_events_content_hash'), 'moderation_events', ['content_hash'], unique=False)

    # 4. appeals table
    op.create_table(
        'appeals',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('violation_id', sa.String(length=64), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='pending', nullable=False),
        sa.Column('admin_decision', sa.String(length=32), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_appeals_user_id'), 'appeals', ['user_id'], unique=False)
    op.create_index(op.f('ix_appeals_violation_id'), 'appeals', ['violation_id'], unique=False)

    # 5. admin_audit_logs table
    op.create_table(
        'admin_audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('admin_id', sa.String(length=64), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('target_id', sa.String(length=64), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_admin_audit_logs_admin_id'), 'admin_audit_logs', ['admin_id'], unique=False)


def downgrade() -> None:
    op.drop_table('admin_audit_logs')
    op.drop_table('appeals')
    op.drop_table('moderation_events')
    op.drop_table('practice_sessions')
    op.drop_table('users')
