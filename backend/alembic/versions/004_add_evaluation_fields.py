"""add multi-dimensional evaluation fields

Revision ID: 004_evaluation_fields
Revises: 003_interview_tables
Create Date: 2026-08-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '004_evaluation_fields'
down_revision = '003_interview_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add evaluation columns to interview_sessions
    op.add_column('interview_sessions', sa.Column('overall_score', sa.Integer(), nullable=True))
    op.add_column(
        'interview_sessions',
        sa.Column('dimension_scores', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True)
    )
    op.add_column(
        'interview_sessions',
        sa.Column('evaluation_report', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True)
    )

    # 2. Add evaluation columns to interview_question_turns
    op.add_column('interview_question_turns', sa.Column('relevance_score', sa.Integer(), nullable=True))
    op.add_column('interview_question_turns', sa.Column('correctness_score', sa.Integer(), nullable=True))
    op.add_column('interview_question_turns', sa.Column('keywords_score', sa.Integer(), nullable=True))
    op.add_column('interview_question_turns', sa.Column('clarity_score', sa.Integer(), nullable=True))
    op.add_column('interview_question_turns', sa.Column('confidence_score', sa.Integer(), nullable=True))
    op.add_column('interview_question_turns', sa.Column('turn_score', sa.Integer(), nullable=True))
    op.add_column(
        'interview_question_turns',
        sa.Column('evaluation_data', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True)
    )


def downgrade() -> None:
    # Drop columns from interview_question_turns
    op.drop_column('interview_question_turns', 'evaluation_data')
    op.drop_column('interview_question_turns', 'turn_score')
    op.drop_column('interview_question_turns', 'confidence_score')
    op.drop_column('interview_question_turns', 'clarity_score')
    op.drop_column('interview_question_turns', 'keywords_score')
    op.drop_column('interview_question_turns', 'correctness_score')
    op.drop_column('interview_question_turns', 'relevance_score')

    # Drop columns from interview_sessions
    op.drop_column('interview_sessions', 'evaluation_report')
    op.drop_column('interview_sessions', 'dimension_scores')
    op.drop_column('interview_sessions', 'overall_score')
