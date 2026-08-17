"""create interview tables

Revision ID: 003_interview_tables
Revises: 002_resume_table
Create Date: 2026-08-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '003_interview_tables'
down_revision = '002_resume_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'interview_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('resume_id', sa.String(length=36), nullable=True),
        sa.Column('target_role', sa.String(length=100), nullable=False),
        sa.Column('seniority_level', sa.String(length=50), nullable=False),
        sa.Column('interview_focus', sa.String(length=50), nullable=False),
        sa.Column('custom_job_desc', sa.Text(), nullable=True),
        sa.Column('parsed_jd_data', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
        sa.Column('focus_skills', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
        sa.Column('practice_mode', sa.String(length=50), nullable=False, server_default='full'),
        sa.Column('planned_core_questions', sa.Integer(), nullable=False, server_default='6'),
        sa.Column('max_total_turns', sa.Integer(), nullable=False, server_default='9'),
        sa.Column('current_turn_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='in_progress'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_interview_sessions_id'), 'interview_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_interview_sessions_user_id'), 'interview_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_interview_sessions_resume_id'), 'interview_sessions', ['resume_id'], unique=False)
    op.create_index(op.f('ix_interview_sessions_status'), 'interview_sessions', ['status'], unique=False)

    op.create_table(
        'interview_question_turns',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('turn_index', sa.Integer(), nullable=False),
        sa.Column('question_type', sa.String(length=50), nullable=False, server_default='core'),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('candidate_answer', sa.Text(), nullable=True),
        sa.Column('is_follow_up', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('parent_turn_id', sa.String(length=36), nullable=True),
        sa.Column('ideal_answer', sa.Text(), nullable=True),
        sa.Column('turn_duration_sec', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['parent_turn_id'], ['interview_question_turns.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_interview_question_turns_id'), 'interview_question_turns', ['id'], unique=False)
    op.create_index(op.f('ix_interview_question_turns_session_id'), 'interview_question_turns', ['session_id'], unique=False)
    op.create_index(op.f('ix_interview_question_turns_turn_index'), 'interview_question_turns', ['turn_index'], unique=False)


def downgrade() -> None:
    op.drop_table('interview_question_turns')
    op.drop_table('interview_sessions')
