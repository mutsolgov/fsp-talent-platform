"""0001_initial_schema

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-10-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("email_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint("role IN ('candidate', 'employer', 'admin')", name="chk_users_role"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role", "users", ["role"])

    # 2. user_consents
    op.create_table(
        "user_consents",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("consent_pdn_processing", sa.Boolean(), nullable=False),
        sa.Column("consent_profile_publication", sa.Boolean(), nullable=False),
        sa.Column("policy_version", sa.String(length=32), server_default=sa.text("'v1.0-2026'"), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=False),
        sa.Column("consent_timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_user_consents_user", ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_user_consents_user_id"),
        sa.CheckConstraint("consent_pdn_processing IS TRUE OR revoked_at IS NOT NULL", name="chk_user_consents_active"),
    )
    op.create_index("ix_user_consents_user_id", "user_consents", ["user_id"])
    op.create_index("ix_user_consents_timestamp", "user_consents", ["consent_timestamp"])

    # 3. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("payload_json", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_audit_logs_user", ondelete="SET NULL"),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # 4. specializations
    op.create_table(
        "specializations",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_specializations_code"),
        sa.CheckConstraint("code IN ('backend', 'frontend', 'ml_data', 'devops', 'qa', 'infosec')", name="chk_specializations_code"),
    )
    op.create_index("ix_specializations_code", "specializations", ["code"])

    # 5. grades
    op.create_table(
        "grades",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("rank_order", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_grades_code"),
        sa.UniqueConstraint("rank_order", name="uq_grades_rank_order"),
        sa.CheckConstraint("code IN ('junior', 'middle', 'senior', 'lead')", name="chk_grades_code"),
        sa.CheckConstraint("rank_order BETWEEN 1 AND 4", name="chk_grades_rank_order"),
    )
    op.create_index("ix_grades_rank_order", "grades", ["rank_order"])

    # 6. categories
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("specialization_id", sa.Integer(), nullable=False),
        sa.Column("grade_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["specialization_id"], ["specializations.id"], name="fk_categories_spec", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["grade_id"], ["grades.id"], name="fk_categories_grade", ondelete="RESTRICT"),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
        sa.UniqueConstraint("specialization_id", "grade_id", name="uq_categories_spec_grade"),
    )
    op.create_index("ix_categories_slug", "categories", ["slug"])
    op.create_index("ix_categories_spec_grade", "categories", ["specialization_id", "grade_id"])

    # 7. skills
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("specialization_id", sa.Integer(), nullable=True),
        sa.Column("category_tag", sa.String(length=50), server_default=sa.text("'general'"), nullable=False),
        sa.Column("is_core", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["specialization_id"], ["specializations.id"], name="fk_skills_spec", ondelete="SET NULL"),
        sa.UniqueConstraint("name", name="uq_skills_name"),
        sa.UniqueConstraint("slug", name="uq_skills_slug"),
    )
    op.create_index("ix_skills_name", "skills", ["name"])
    op.create_index("ix_skills_slug", "skills", ["slug"])
    op.create_index("ix_skills_specialization", "skills", ["specialization_id"])


def downgrade() -> None:
    op.drop_table("skills")
    op.drop_table("categories")
    op.drop_table("grades")
    op.drop_table("specializations")
    op.drop_table("audit_logs")
    op.drop_table("user_consents")
    op.drop_table("users")
