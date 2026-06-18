"""initial tables

Revision ID: 0001_initial
Revises: None
Create Date: 2026-06-16
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("bio", sa.Text(), nullable=True, server_default=""),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)
    op.create_index(op.f("ix_user_username"), "user", ["username"], unique=True)

    op.create_table(
        "interview_goal",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("company_name", sa.String(length=140), nullable=False),
        sa.Column("role", sa.String(length=140), nullable=False),
        sa.Column("interview_date", sa.Date(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Planned"),
        sa.Column("notes", sa.Text(), nullable=True, server_default=""),
        sa.Column("job_description", sa.Text(), nullable=True, server_default=""),
        sa.Column("responsibilities", sa.Text(), nullable=True, server_default=""),
        sa.Column("preferred_qualifications", sa.Text(), nullable=True, server_default=""),
        sa.Column("company_notes", sa.Text(), nullable=True, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "goal_task",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("goal_id", sa.Integer(), sa.ForeignKey("interview_goal.id"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "skill",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("goal_id", sa.Integer(), sa.ForeignKey("interview_goal.id"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("confidence_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Not Started"),
        sa.Column("notes", sa.Text(), nullable=True, server_default=""),
        sa.Column("resource_url", sa.String(length=500), nullable=True, server_default=""),
    )

    op.create_table(
        "course",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("goal_id", sa.Integer(), sa.ForeignKey("interview_goal.id"), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("platform", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("url", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("instructor", sa.String(length=120), nullable=True, server_default=""),
        sa.Column("total_lessons", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_lessons", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "course_skill",
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("course.id"), primary_key=True),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skill.id"), primary_key=True),
    )

    op.create_table(
        "daily_task",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "activity",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("goal_id", sa.Integer(), sa.ForeignKey("interview_goal.id"), nullable=True),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("activity")
    op.drop_table("daily_task")
    op.drop_table("course_skill")
    op.drop_table("course")
    op.drop_table("skill")
    op.drop_table("goal_task")
    op.drop_table("interview_goal")
    op.drop_index(op.f("ix_user_username"), table_name="user")
    op.drop_index(op.f("ix_user_email"), table_name="user")
    op.drop_table("user")
