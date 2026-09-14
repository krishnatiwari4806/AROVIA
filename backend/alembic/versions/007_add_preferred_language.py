"""add preferred_language column to interview_sessions

Revision ID: 007_add_preferred_language
Revises: 006_coach_conversation_unique
Create Date: 2026-09-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007_add_preferred_language'
down_revision = '006_coach_conversation_unique'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('interview_sessions', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'preferred_language',
                sa.String(length=20),
                nullable=False,
                server_default='en',
            )
        )


def downgrade() -> None:
    with op.batch_alter_table('interview_sessions', schema=None) as batch_op:
        batch_op.drop_column('preferred_language')
