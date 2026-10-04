"""initial schema

Creates the 10 core tables (see docs/architecture.md, "Database schema").
The embedding size (1024 = BGE-M3) is fixed here on purpose: switching to an
embedding model with a different size needs a new migration + re-embedding.

Revision ID: 0001
Revises: 
Create Date: 2026-10-03 20:50:06.645140
"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # pgvector adds the `vector` column type and similarity operators
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table('api_cache',
    sa.Column('key', sa.String(length=128), nullable=False),
    sa.Column('namespace', sa.String(length=32), nullable=False),
    sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('key', name=op.f('pk_api_cache'))
    )
    op.create_index(op.f('ix_api_cache_expires_at'), 'api_cache', ['expires_at'], unique=False)
    op.create_index(op.f('ix_api_cache_namespace'), 'api_cache', ['namespace'], unique=False)
    op.create_table('documents',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('title', sa.Text(), nullable=True),
    sa.Column('source', sa.String(length=32), server_default='upload', nullable=False),
    sa.Column('mime_type', sa.String(length=100), nullable=False),
    sa.Column('size_bytes', sa.BigInteger(), nullable=False),
    sa.Column('content_sha256', sa.String(length=64), nullable=False),
    sa.Column('storage_path', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=16), server_default='pending', nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('page_count', sa.Integer(), nullable=True),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('pending', 'processing', 'ready', 'failed')", name=op.f('ck_documents_valid_status')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_documents')),
    sa.UniqueConstraint('content_sha256', name=op.f('uq_documents_content_sha256'))
    )
    op.create_table('patents',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('source', sa.String(length=32), nullable=False),
    sa.Column('publication_number', sa.String(length=64), nullable=False),
    sa.Column('country', sa.String(length=4), nullable=True),
    sa.Column('kind_code', sa.String(length=4), nullable=True),
    sa.Column('family_id', sa.String(length=64), nullable=True),
    sa.Column('title', sa.Text(), nullable=True),
    sa.Column('abstract', sa.Text(), nullable=True),
    sa.Column('claims_text', sa.Text(), nullable=True),
    sa.Column('description_text', sa.Text(), nullable=True),
    sa.Column('applicants', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
    sa.Column('inventors', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
    sa.Column('cpc_codes', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
    sa.Column('filing_date', sa.Date(), nullable=True),
    sa.Column('publication_date', sa.Date(), nullable=True),
    sa.Column('priority_date', sa.Date(), nullable=True),
    sa.Column('legal_status', sa.Text(), nullable=True),
    sa.Column('url', sa.Text(), nullable=True),
    sa.Column('raw', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.Column('fetched_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_patents')),
    sa.UniqueConstraint('source', 'publication_number', name=op.f('uq_patents_source_publication_number'))
    )
    op.create_index(op.f('ix_patents_family_id'), 'patents', ['family_id'], unique=False)
    op.create_index(op.f('ix_patents_publication_number'), 'patents', ['publication_number'], unique=False)
    op.create_table('queries',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('conversation_id', sa.Uuid(), nullable=True),
    sa.Column('query_text', sa.Text(), nullable=False),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_queries'))
    )
    op.create_index(op.f('ix_queries_conversation_id'), 'queries', ['conversation_id'], unique=False)
    op.create_table('agent_runs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('query_id', sa.Uuid(), nullable=False),
    sa.Column('pipeline', sa.String(length=32), nullable=False),
    sa.Column('status', sa.String(length=24), server_default='running', nullable=False),
    sa.Column('plan', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('answer_text', sa.Text(), nullable=True),
    sa.Column('answer', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('grounding_score', sa.Float(), nullable=True),
    sa.Column('prompt_tokens', sa.Integer(), nullable=True),
    sa.Column('completion_tokens', sa.Integer(), nullable=True),
    sa.Column('cost_usd', sa.Numeric(precision=10, scale=6), nullable=True),
    sa.Column('latency_ms', sa.Integer(), nullable=True),
    sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("status IN ('running', 'succeeded', 'insufficient_evidence', 'failed')", name=op.f('ck_agent_runs_valid_status')),
    sa.ForeignKeyConstraint(['query_id'], ['queries.id'], name=op.f('fk_agent_runs_query_id_queries'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_agent_runs'))
    )
    op.create_index(op.f('ix_agent_runs_query_id'), 'agent_runs', ['query_id'], unique=False)
    op.create_table('chunks',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('document_id', sa.Uuid(), nullable=True),
    sa.Column('patent_id', sa.Uuid(), nullable=True),
    sa.Column('chunk_index', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('section', sa.String(length=32), nullable=True),
    sa.Column('page_number', sa.Integer(), nullable=True),
    sa.Column('char_start', sa.Integer(), nullable=True),
    sa.Column('char_end', sa.Integer(), nullable=True),
    sa.Column('token_count', sa.Integer(), nullable=True),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=1024), nullable=True),
    sa.Column('embedding_model', sa.String(length=128), nullable=True),
    sa.Column('tsv', postgresql.TSVECTOR(), sa.Computed("to_tsvector('english', text)", persisted=True), nullable=False),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('num_nonnulls(document_id, patent_id) = 1', name=op.f('ck_chunks_exactly_one_owner')),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], name=op.f('fk_chunks_document_id_documents'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['patent_id'], ['patents.id'], name=op.f('fk_chunks_patent_id_patents'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_chunks')),
    sa.UniqueConstraint('document_id', 'chunk_index', name=op.f('uq_chunks_document_id_chunk_index')),
    sa.UniqueConstraint('patent_id', 'chunk_index', name=op.f('uq_chunks_patent_id_chunk_index'))
    )
    op.create_index(op.f('ix_chunks_document_id'), 'chunks', ['document_id'], unique=False)
    op.create_index('ix_chunks_embedding_hnsw', 'chunks', ['embedding'], unique=False, postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64}, postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.create_index(op.f('ix_chunks_patent_id'), 'chunks', ['patent_id'], unique=False)
    op.create_index('ix_chunks_tsv', 'chunks', ['tsv'], unique=False, postgresql_using='gin')
    op.create_table('claim_verifications',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('agent_run_id', sa.Uuid(), nullable=False),
    sa.Column('claim_index', sa.Integer(), nullable=False),
    sa.Column('claim_text', sa.Text(), nullable=False),
    sa.Column('verdict', sa.String(length=24), nullable=False),
    sa.Column('support_score', sa.Float(), nullable=True),
    sa.Column('evidence_ids', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
    sa.Column('method', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("verdict IN ('supported', 'partially_supported', 'unsupported')", name=op.f('ck_claim_verifications_valid_verdict')),
    sa.ForeignKeyConstraint(['agent_run_id'], ['agent_runs.id'], name=op.f('fk_claim_verifications_agent_run_id_agent_runs'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_claim_verifications'))
    )
    op.create_index(op.f('ix_claim_verifications_agent_run_id'), 'claim_verifications', ['agent_run_id'], unique=False)
    op.create_table('evaluations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('agent_run_id', sa.Uuid(), nullable=True),
    sa.Column('experiment', sa.String(length=64), nullable=True),
    sa.Column('metric_name', sa.String(length=64), nullable=False),
    sa.Column('metric_value', sa.Float(), nullable=False),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['agent_run_id'], ['agent_runs.id'], name=op.f('fk_evaluations_agent_run_id_agent_runs'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_evaluations'))
    )
    op.create_index(op.f('ix_evaluations_agent_run_id'), 'evaluations', ['agent_run_id'], unique=False)
    op.create_index(op.f('ix_evaluations_experiment'), 'evaluations', ['experiment'], unique=False)
    op.create_index(op.f('ix_evaluations_metric_name'), 'evaluations', ['metric_name'], unique=False)
    op.create_table('retrieval_results',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('agent_run_id', sa.Uuid(), nullable=False),
    sa.Column('rank', sa.Integer(), nullable=False),
    sa.Column('source_type', sa.String(length=32), nullable=False),
    sa.Column('chunk_id', sa.Uuid(), nullable=True),
    sa.Column('patent_id', sa.Uuid(), nullable=True),
    sa.Column('method', sa.String(length=16), nullable=False),
    sa.Column('score', sa.Float(), nullable=True),
    sa.Column('rerank_score', sa.Float(), nullable=True),
    sa.Column('retrieved_text', sa.Text(), nullable=False),
    sa.Column('cited_in_answer', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['agent_run_id'], ['agent_runs.id'], name=op.f('fk_retrieval_results_agent_run_id_agent_runs'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['chunk_id'], ['chunks.id'], name=op.f('fk_retrieval_results_chunk_id_chunks'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['patent_id'], ['patents.id'], name=op.f('fk_retrieval_results_patent_id_patents'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_retrieval_results'))
    )
    op.create_index(op.f('ix_retrieval_results_agent_run_id'), 'retrieval_results', ['agent_run_id'], unique=False)
    op.create_index(op.f('ix_retrieval_results_chunk_id'), 'retrieval_results', ['chunk_id'], unique=False)
    op.create_index(op.f('ix_retrieval_results_patent_id'), 'retrieval_results', ['patent_id'], unique=False)
    op.create_table('tool_calls',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('agent_run_id', sa.Uuid(), nullable=False),
    sa.Column('step_index', sa.Integer(), nullable=False),
    sa.Column('tool_name', sa.String(length=64), nullable=False),
    sa.Column('input', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.Column('output_summary', sa.Text(), nullable=True),
    sa.Column('success', sa.Boolean(), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('latency_ms', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['agent_run_id'], ['agent_runs.id'], name=op.f('fk_tool_calls_agent_run_id_agent_runs'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tool_calls'))
    )
    op.create_index(op.f('ix_tool_calls_agent_run_id'), 'tool_calls', ['agent_run_id'], unique=False)
    op.create_index(op.f('ix_tool_calls_tool_name'), 'tool_calls', ['tool_name'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_tool_calls_tool_name'), table_name='tool_calls')
    op.drop_index(op.f('ix_tool_calls_agent_run_id'), table_name='tool_calls')
    op.drop_table('tool_calls')
    op.drop_index(op.f('ix_retrieval_results_patent_id'), table_name='retrieval_results')
    op.drop_index(op.f('ix_retrieval_results_chunk_id'), table_name='retrieval_results')
    op.drop_index(op.f('ix_retrieval_results_agent_run_id'), table_name='retrieval_results')
    op.drop_table('retrieval_results')
    op.drop_index(op.f('ix_evaluations_metric_name'), table_name='evaluations')
    op.drop_index(op.f('ix_evaluations_experiment'), table_name='evaluations')
    op.drop_index(op.f('ix_evaluations_agent_run_id'), table_name='evaluations')
    op.drop_table('evaluations')
    op.drop_index(op.f('ix_claim_verifications_agent_run_id'), table_name='claim_verifications')
    op.drop_table('claim_verifications')
    op.drop_index('ix_chunks_tsv', table_name='chunks', postgresql_using='gin')
    op.drop_index(op.f('ix_chunks_patent_id'), table_name='chunks')
    op.drop_index('ix_chunks_embedding_hnsw', table_name='chunks', postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64}, postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.drop_index(op.f('ix_chunks_document_id'), table_name='chunks')
    op.drop_table('chunks')
    op.drop_index(op.f('ix_agent_runs_query_id'), table_name='agent_runs')
    op.drop_table('agent_runs')
    op.drop_index(op.f('ix_queries_conversation_id'), table_name='queries')
    op.drop_table('queries')
    op.drop_index(op.f('ix_patents_publication_number'), table_name='patents')
    op.drop_index(op.f('ix_patents_family_id'), table_name='patents')
    op.drop_table('patents')
    op.drop_table('documents')
    op.drop_index(op.f('ix_api_cache_namespace'), table_name='api_cache')
    op.drop_index(op.f('ix_api_cache_expires_at'), table_name='api_cache')
    op.drop_table('api_cache')
