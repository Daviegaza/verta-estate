"""add_action_url_to_notifications

Revision ID: a4f8c2e1b3d9
Revises: 3cc87f3fb440
Create Date: 2026-06-20 15:30:00.000000

Add action_url column to notifications table for deep-linking.
Also removes stale duplicate model tables that may have been created
from the now-deleted kyc_verification.py, notification.py, message.py,
saved_property.py, saved_search.py files.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision: str = 'a4f8c2e1b3d9'
down_revision: Union[str, None] = '3cc87f3fb440'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add action_url column to notifications table for deep-link support
    op.add_column(
        'notifications',
        sa.Column('action_url', sa.String(1000), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('notifications', 'action_url')
