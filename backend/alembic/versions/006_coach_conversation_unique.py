"""add unique constraint to coach_conversations on (user_id, session_id)

Revision ID: 006_coach_conversation_unique
Revises: 005_create_coach_tables
Create Date: 2026-09-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006_coach_conversation_unique'
down_revision = '005_create_coach_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('coach_conversations', schema=None) as batch_op:
        batch_op.create_unique_constraint(
            'uq_coach_conversation_user_session',
            ['user_id', 'session_id']
        )


def downgrade() -> None:
    with op.batch_alter_table('coach_conversations', schema=None) as batch_op:
        batch_op.drop_constraint(
            'uq_coach_conversation_user_session',
            type_='unique'
        )
