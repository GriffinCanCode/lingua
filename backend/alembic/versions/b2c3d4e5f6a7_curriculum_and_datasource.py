"""Add curriculum and datasource tables

Revision ID: b2c3d4e5f6a7
Revises: aa54dbb881bd
Create Date: 2025-12-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'aa54dbb881bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === Curriculum Tables ===
    
    op.create_table(
        'curriculum_sections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('language', sa.String(10), nullable=False, default='ru'),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('order_index', sa.Integer, nullable=False, default=0),
        sa.Column('icon', sa.String(50)),
        sa.Column('color', sa.String(20)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_curriculum_sections_language_order', 'curriculum_sections', ['language', 'order_index'])

    op.create_table(
        'curriculum_units',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('section_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('curriculum_sections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('order_index', sa.Integer, nullable=False, default=0),
        sa.Column('icon', sa.String(50)),
        sa.Column('prerequisite_units', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), default=[]),
        sa.Column('target_patterns', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), default=[]),
        sa.Column('estimated_duration_min', sa.Integer, default=30),
        sa.Column('is_checkpoint', sa.Boolean, default=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('extra_data', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_curriculum_units_section_order', 'curriculum_units', ['section_id', 'order_index'])

    op.create_table(
        'curriculum_nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('unit_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('curriculum_units.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('order_index', sa.Integer, nullable=False, default=0),
        sa.Column('node_type', sa.String(50), nullable=False, default='practice'),
        sa.Column('target_patterns', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), default=[]),
        sa.Column('complexity_min', sa.Integer, default=1),
        sa.Column('complexity_max', sa.Integer, default=10),
        sa.Column('min_reviews_to_complete', sa.Integer, default=5),
        sa.Column('sentence_pool_size', sa.Integer, default=0),
        sa.Column('estimated_duration_min', sa.Integer, default=5),
        sa.Column('extra_data', postgresql.JSONB, default={}),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_curriculum_nodes_unit_order', 'curriculum_nodes', ['unit_id', 'order_index'])

    op.create_table(
        'user_node_progress',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('node_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('curriculum_nodes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='locked'),
        sa.Column('level', sa.Integer, default=0),
        sa.Column('total_reviews', sa.Integer, default=0),
        sa.Column('correct_reviews', sa.Integer, default=0),
        sa.Column('started_at', sa.DateTime),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('last_practiced_at', sa.DateTime),
        sa.Column('extra_data', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_user_node_progress_user_node', 'user_node_progress', ['user_id', 'node_id'], unique=True)

    op.create_table(
        'user_unit_progress',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('unit_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('curriculum_units.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='locked'),
        sa.Column('is_crowned', sa.Boolean, default=False),
        sa.Column('completed_nodes', sa.Integer, default=0),
        sa.Column('total_nodes', sa.Integer, default=0),
        sa.Column('started_at', sa.DateTime),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('crowned_at', sa.DateTime),
        sa.Column('extra_data', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_user_unit_progress_user_unit', 'user_unit_progress', ['user_id', 'unit_id'], unique=True)

    # === Data Source Tables ===

    op.create_table(
        'data_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('language', sa.String(10), nullable=False, default='ru'),
        sa.Column('version', sa.String(50)),
        sa.Column('url', sa.String(500)),
        sa.Column('license', sa.String(100)),
        sa.Column('description', sa.Text),
        sa.Column('last_sync', sa.DateTime),
        sa.Column('next_sync', sa.DateTime),
        sa.Column('sync_frequency_days', sa.Integer, default=90),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('config', postgresql.JSONB, default={}),
        sa.Column('stats', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_data_sources_name_lang', 'data_sources', ['name', 'language'])

    op.create_table(
        'ingestion_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_name', sa.String(100), nullable=False),
        sa.Column('language', sa.String(10), nullable=False, default='ru'),
        sa.Column('file_path', sa.String(500)),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('started_at', sa.DateTime),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('records_processed', sa.Integer, default=0),
        sa.Column('records_created', sa.Integer, default=0),
        sa.Column('records_updated', sa.Integer, default=0),
        sa.Column('records_skipped', sa.Integer, default=0),
        sa.Column('records_failed', sa.Integer, default=0),
        sa.Column('error_log', postgresql.JSONB, default=[]),
        sa.Column('config', postgresql.JSONB, default={}),
        sa.Column('stats', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    op.create_index('ix_ingestion_records_source_status', 'ingestion_records', ['source_name', 'status'])

    op.create_table(
        'external_id_mappings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_name', sa.String(100), nullable=False),
        sa.Column('external_id', sa.String(255), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('internal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.String(50)),
        sa.Column('checksum', sa.String(64)),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_external_id_unique', 'external_id_mappings', ['source_name', 'external_id', 'entity_type'], unique=True)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('external_id_mappings')
    op.drop_table('ingestion_records')
    op.drop_table('data_sources')
    op.drop_table('user_unit_progress')
    op.drop_table('user_node_progress')
    op.drop_table('curriculum_nodes')
    op.drop_table('curriculum_units')
    op.drop_table('curriculum_sections')

