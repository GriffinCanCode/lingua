"""Add vocabulary tracking tables

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6a7
Create Date: 2025-12-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'vocabulary',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('word', sa.String(255), nullable=False),
        sa.Column('translation', sa.String(255), nullable=False),
        sa.Column('language', sa.String(10), default='ru'),
        sa.Column('pos', sa.String(50)),
        sa.Column('gender', sa.String(1)),
        sa.Column('semantic', postgresql.JSONB, default=[]),
        sa.Column('frequency', sa.Integer, default=1),
        sa.Column('difficulty', sa.Integer, default=1),
        sa.Column('audio', sa.String(500)),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    op.create_index('ix_vocabulary_language', 'vocabulary', ['language'])
    op.create_index('ix_vocabulary_pos', 'vocabulary', ['pos'])

    op.create_table(
        'user_vocab_mastery',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('vocab_id', sa.String(100), sa.ForeignKey('vocabulary.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('state', sa.String(20), default='unseen'),
        sa.Column('exposure_count', sa.Integer, default=0),
        sa.Column('correct_count', sa.Integer, default=0),
        sa.Column('ease_factor', sa.Float, default=2.5),
        sa.Column('interval', sa.Integer, default=1),
        sa.Column('next_review', sa.DateTime),
        sa.Column('last_review', sa.DateTime),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_user_vocab_mastery_state', 'user_vocab_mastery', ['user_id', 'state'])


def downgrade() -> None:
    op.drop_table('user_vocab_mastery')
    op.drop_table('vocabulary')
