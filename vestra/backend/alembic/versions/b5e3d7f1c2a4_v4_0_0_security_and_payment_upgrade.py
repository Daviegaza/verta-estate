"""v4.0.0 — Security, Payments, and Model Upgrades

Revision ID: b5e3d7f1c2a4
Revises: a4f8c2e1b3d9
Create Date: 2026-06-21

Changes:
- Add two_factor_enabled, totp_secret to users
- Add consent fields to users (GDPR)
- Add deposit_reference to escrow_transactions
- Add device_info to refresh token sessions
- Add UniqueConstraint to saved_properties
- Add new payment provider columns
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b5e3d7f1c2a4'
down_revision: Union[str, None] = 'a4f8c2e1b3d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Users table: 2FA + GDPR consent ──
    op.add_column('users', sa.Column('two_factor_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('totp_secret', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('consent_marketing', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('consent_data_processing', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('consent_date', sa.DateTime(timezone=True), nullable=True))

    # ── Escrow transactions: separate deposit reference ──
    op.add_column('escrow_transactions', sa.Column('deposit_reference', sa.String(255), nullable=True))

    # ── Saved properties: add unique constraint ──
    # First drop any existing duplicate saved_properties (keep the oldest)
    op.execute("""
        DELETE FROM saved_properties sp1
        USING saved_properties sp2
        WHERE sp1.id > sp2.id
        AND sp1.user_id = sp2.user_id
        AND sp1.property_id = sp2.property_id
    """)
    op.create_unique_constraint('uq_saved_property_user_property', 'saved_properties', ['user_id', 'property_id'])

    # ── Payments: add provider type for new payment methods ──
    op.add_column('payments', sa.Column('provider_type', sa.String(50), nullable=True))
    op.add_column('payments', sa.Column('provider_transaction_id', sa.String(255), nullable=True))
    op.add_column('payments', sa.Column('provider_receipt_url', sa.Text, nullable=True))

    # ── Create index for provider lookups ──
    op.create_index('ix_payments_provider_type', 'payments', ['provider_type'])
    op.create_index('ix_payments_provider_transaction', 'payments', ['provider_transaction_id'])

    # ── Notification: add expires_at for auto-cleanup ──
    op.add_column('notifications', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_notifications_expires_at', 'notifications', ['expires_at'])

    # ── Webhooks: add last_failure_at and failure_count ──
    op.add_column('webhooks', sa.Column('last_failure_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('webhooks', sa.Column('failure_count', sa.Integer(), nullable=False, server_default='0'))

    # ── User events: add correlation_id for tracing ──
    op.add_column('user_events', sa.Column('correlation_id', sa.String(50), nullable=True))
    op.create_index('ix_user_events_correlation', 'user_events', ['correlation_id'])


def downgrade() -> None:
    # ── Users table ──
    op.drop_column('users', 'consent_date')
    op.drop_column('users', 'consent_data_processing')
    op.drop_column('users', 'consent_marketing')
    op.drop_column('users', 'totp_secret')
    op.drop_column('users', 'two_factor_enabled')

    # ── Escrow transactions ──
    op.drop_column('escrow_transactions', 'deposit_reference')

    # ── Saved properties ──
    op.drop_constraint('uq_saved_property_user_property', 'saved_properties', type_='unique')

    # ── Payments ──
    op.drop_index('ix_payments_provider_transaction', table_name='payments')
    op.drop_index('ix_payments_provider_type', table_name='payments')
    op.drop_column('payments', 'provider_receipt_url')
    op.drop_column('payments', 'provider_transaction_id')
    op.drop_column('payments', 'provider_type')

    # ── Notifications ──
    op.drop_index('ix_notifications_expires_at', table_name='notifications')
    op.drop_column('notifications', 'expires_at')

    # ── Webhooks ──
    op.drop_column('webhooks', 'failure_count')
    op.drop_column('webhooks', 'last_failure_at')

    # ── User events ──
    op.drop_index('ix_user_events_correlation', table_name='user_events')
    op.drop_column('user_events', 'correlation_id')
