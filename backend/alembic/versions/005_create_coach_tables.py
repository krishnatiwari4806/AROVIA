"""create coach conversations and messages tables

Revision ID: 005_create_coach_tables
Revises: 004_evaluation_fields
Create Date: 2026-08-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_create_coach_tables'
down_revision = '004_evaluation_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create coach_conversations table
    op.create_table(
        'coach_conversations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_coach_conversations_id'), 'coach_conversations', ['id'], unique=False)
    op.create_index(op.f('ix_coach_conversations_session_id'), 'coach_conversations', ['session_id'], unique=False)
    op.create_index(op.f('ix_coach_conversations_user_id'), 'coach_conversations', ['user_id'], unique=False)

    # 2. Create coach_messages table
    op.create_table(
        'coach_messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('conversation_id', sa.String(length=36), nullable=False),
        sa.Column('sender', sa.String(length=20), nullable=False),
        sa.Column('message_text', sa.Text(), nullable=False),
        sa.Column('context_turn_index', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['coach_conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_coach_messages_conversation_id'), 'coach_messages', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_coach_messages_id'), 'coach_messages', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_coach_messages_id'), table_name='coach_messages')
    op.drop_index(op.f('ix_coach_messages_conversation_id'), table_name='coach_messages')
    op.drop_table('coach_messages')

    op.drop_index(op.f('ix_coach_conversations_user_id'), table_name='coach_conversations')
    op.drop_index(op.f('ix_coach_conversations_session_id'), table_name='coach_conversations')
    op.drop_index(op.f('ix_coach_conversations_id'), table_name='coach_conversations')
    op.drop_table('coach_conversations')
