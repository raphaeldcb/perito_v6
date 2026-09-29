"""Add email communication tables for monitoring and auto-response.

Revision ID: 20260916_comunicacoes_001
Revises: phase2_001
Create Date: 2026-09-16 18:00:00.000000

Tables:
- email_messages: Microsoft Graph email monitoring with judicial classification
- email_config: Configuration for each monitored mailbox
- email_template: Response templates with variable substitution
- email_feedback: User corrections for learning and accuracy improvement

Features:
- Automatic classification of judicial vs non-judicial emails
- Data extraction: tribunal, vara, comarca, processo, pedido, prazo
- Suggested responses with user editing capability
- Template system for auto-responses
- Feedback tracking for model improvement
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260916_comunicacoes_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create email communication tables."""

    # ============ EMAIL_MESSAGES TABLE ============
    # Stores monitored emails from Microsoft Graph
    op.create_table(
        'email_messages',
        sa.Column('id', sa.Integer(), nullable=False),

        # Microsoft identifiers
        sa.Column('message_id', sa.String(255), nullable=False, unique=True),
        sa.Column('internet_message_id', sa.String(255), nullable=True, unique=True),
        sa.Column('conversation_id', sa.String(255), nullable=True),

        # Sender/Recipients
        sa.Column('from_address', sa.String(255), nullable=False),
        sa.Column('from_name', sa.String(255), nullable=True),
        sa.Column('to_addresses', sa.Text(), nullable=False),  # JSON array
        sa.Column('cc_addresses', sa.Text(), nullable=True),   # JSON array

        # Content
        sa.Column('subject', sa.String(500), nullable=False),
        sa.Column('body_text', sa.Text(), nullable=True),
        sa.Column('body_html', sa.Text(), nullable=True),
        sa.Column('received_datetime', sa.DateTime(), nullable=False),

        # Judicial classification
        sa.Column('is_judicial', sa.Boolean(), default=False, nullable=False),
        sa.Column('judicial_confidence', sa.Float(), nullable=True),  # 0.0-1.0
        sa.Column('judicial_reason', sa.Text(), nullable=True),

        # Extracted procedural data
        sa.Column('tribunal', sa.String(255), nullable=True),
        sa.Column('vara', sa.String(255), nullable=True),
        sa.Column('comarca', sa.String(255), nullable=True),
        sa.Column('numero_processo', sa.String(50), nullable=True),
        sa.Column('pedido', sa.Text(), nullable=True),
        sa.Column('prazo', sa.String(100), nullable=True),

        # Status
        sa.Column('status', sa.String(50), nullable=False, server_default='novo'),

        # Response tracking
        sa.Column('resposta_sugerida', sa.Text(), nullable=True),
        sa.Column('resposta_editada', sa.Text(), nullable=True),
        sa.Column('resposta_enviada', sa.DateTime(), nullable=True),

        # Attachments
        sa.Column('has_attachments', sa.Boolean(), default=False, nullable=False),
        sa.Column('attachments_data', sa.Text(), nullable=True),  # JSON

        # Audit
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),

        sa.PrimaryKeyConstraint('id'),
    )

    # Indexes for performance
    op.create_index('idx_email_messages_message_id', 'email_messages', ['message_id'])
    op.create_index('idx_email_messages_judicial', 'email_messages', ['is_judicial'])
    op.create_index('idx_email_messages_status', 'email_messages', ['status'])
    op.create_index('idx_email_messages_numero_processo', 'email_messages', ['numero_processo'])
    op.create_index('idx_email_messages_received', 'email_messages', ['received_datetime'])


    # ============ EMAIL_CONFIG TABLE ============
    # Configuration for monitored mailboxes
    op.create_table(
        'email_config',
        sa.Column('id', sa.Integer(), nullable=False),

        # Monitored account
        sa.Column('mailbox_email', sa.String(255), nullable=False, unique=True),

        # Execution interval (minutes)
        sa.Column('intervalo_minutos', sa.Integer(), nullable=False, server_default='5'),

        # Status
        sa.Column('ativo', sa.Boolean(), default=True, nullable=False),
        sa.Column('ultima_execucao', sa.DateTime(), nullable=True),
        sa.Column('proxima_execucao', sa.DateTime(), nullable=True),

        # Required fields for judicial emails (JSON)
        sa.Column('campos_obrigatorios', sa.Text(),
                  nullable=False,
                  server_default='{"tribunal": true, "vara": true, "numero_processo": true, "pedido": true}'),

        # Response mode: "rascunho" (draft) or "automatico" (auto-send)
        sa.Column('modo_resposta', sa.String(50), nullable=False, server_default='rascunho'),

        # Default template for responses
        sa.Column('template_id', sa.Integer(), nullable=True),

        # Audit
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),

        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index('idx_email_config_mailbox', 'email_config', ['mailbox_email'])
    op.create_index('idx_email_config_ativo', 'email_config', ['ativo'])


    # ============ EMAIL_TEMPLATE TABLE ============
    # Response templates with variable substitution
    op.create_table(
        'email_template',
        sa.Column('id', sa.Integer(), nullable=False),

        # Template metadata
        sa.Column('nome', sa.String(255), nullable=False),
        sa.Column('assunto', sa.String(500), nullable=False),
        sa.Column('corpo', sa.Text(), nullable=False),

        # Variables: {{tribunal}}, {{vara}}, {{numero_processo}}, {{pedido}}, {{campos_faltantes}}, {{assinatura}}

        # Status
        sa.Column('ativo', sa.Boolean(), default=True, nullable=False),
        sa.Column('padrao', sa.Boolean(), default=False, nullable=False),  # One default at a time

        # Audit
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),

        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index('idx_email_template_ativo', 'email_template', ['ativo'])
    op.create_index('idx_email_template_padrao', 'email_template', ['padrao'])


    # ============ EMAIL_FEEDBACK TABLE ============
    # User corrections for model feedback and learning
    op.create_table(
        'email_feedback',
        sa.Column('id', sa.Integer(), nullable=False),

        # Reference to email
        sa.Column('email_message_id', sa.Integer(), nullable=False),

        # Response corrections
        sa.Column('resposta_original', sa.Text(), nullable=True),
        sa.Column('resposta_corrigida', sa.Text(), nullable=True),

        # Field corrections: original vs corrected values
        sa.Column('tribunal_original', sa.String(255), nullable=True),
        sa.Column('tribunal_corrigido', sa.String(255), nullable=True),

        sa.Column('vara_original', sa.String(255), nullable=True),
        sa.Column('vara_corrigida', sa.String(255), nullable=True),

        sa.Column('comarca_original', sa.String(255), nullable=True),
        sa.Column('comarca_corrigida', sa.String(255), nullable=True),

        sa.Column('numero_processo_original', sa.String(50), nullable=True),
        sa.Column('numero_processo_corrigido', sa.String(50), nullable=True),

        sa.Column('pedido_original', sa.Text(), nullable=True),
        sa.Column('pedido_corrigido', sa.Text(), nullable=True),

        # User context (for multi-user scenarios)
        sa.Column('usuario_id', sa.Integer(), nullable=True),

        # Audit
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['email_message_id'], ['email_messages.id'], ondelete='CASCADE'),
    )

    # Indexes for feedback tracking
    op.create_index('idx_email_feedback_email_id', 'email_feedback', ['email_message_id'])
    op.create_index('idx_email_feedback_usuario_id', 'email_feedback', ['usuario_id'])
    op.create_index('idx_email_feedback_created', 'email_feedback', ['created_at'])


    # ============ FOREIGN KEY for EMAIL_CONFIG.TEMPLATE_ID ============
    op.create_foreign_key(
        'fk_email_config_template_id',
        'email_config', 'email_template',
        ['template_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Drop email communication tables."""

    # Drop foreign key
    op.drop_constraint('fk_email_config_template_id', 'email_config', type_='foreignkey')

    # Drop feedback table and indexes
    op.drop_index('idx_email_feedback_created')
    op.drop_index('idx_email_feedback_usuario_id')
    op.drop_index('idx_email_feedback_email_id')
    op.drop_table('email_feedback')

    # Drop template table and indexes
    op.drop_index('idx_email_template_padrao')
    op.drop_index('idx_email_template_ativo')
    op.drop_table('email_template')

    # Drop config table and indexes
    op.drop_index('idx_email_config_ativo')
    op.drop_index('idx_email_config_mailbox')
    op.drop_table('email_config')

    # Drop messages table and indexes
    op.drop_index('idx_email_messages_received')
    op.drop_index('idx_email_messages_numero_processo')
    op.drop_index('idx_email_messages_status')
    op.drop_index('idx_email_messages_judicial')
    op.drop_index('idx_email_messages_message_id')
    op.drop_table('email_messages')
