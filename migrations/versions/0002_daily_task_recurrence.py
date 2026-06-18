"""add recurrence fields to daily_task

Revision ID: 0002_daily_task_recurrence
Revises: 0001_initial
Create Date: 2026-06-16
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_daily_task_recurrence"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("daily_task", sa.Column("recurrence_type", sa.String(length=20), nullable=False, server_default="none"))
    op.add_column("daily_task", sa.Column("recurrence_interval_days", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("daily_task", sa.Column("recurrence_days_of_week", sa.String(length=50), nullable=False, server_default=""))
    op.add_column("daily_task", sa.Column("recurring", sa.Boolean(), nullable=False, server_default=sa.text("0")))


def downgrade():
    op.drop_column("daily_task", "recurring")
    op.drop_column("daily_task", "recurrence_days_of_week")
    op.drop_column("daily_task", "recurrence_interval_days")
    op.drop_column("daily_task", "recurrence_type")
