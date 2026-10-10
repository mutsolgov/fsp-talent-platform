"""0003_matching_schema

Revision ID: 0003_matching_schema
Revises: 0002_assessment_schema
Create Date: 2026-10-06 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_matching_schema"
down_revision: Union[str, None] = "0002_assessment_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. employer_profiles
    op.create_table(
        "employer_profiles",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("inn", sa.String(length=12), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("is_inn_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("trust_score", sa.Integer(), server_default=sa.text("50"), nullable=False),
        sa.Column("invite_daily_limit", sa.Integer(), server_default=sa.text("20"), nullable=False),
        sa.Column("invites_sent_today", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_invite_reset_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=100), server_default=sa.text("'Москва'"), nullable=False),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_employer_profiles_user"),
        sa.UniqueConstraint("inn", name="uq_employer_profiles_inn"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_employer_profiles_user", ondelete="CASCADE"),
        sa.CheckConstraint("length(inn) IN (10, 12)", name="chk_employer_inn_length"),
        sa.CheckConstraint("trust_score >= 0 AND trust_score <= 100", name="chk_employer_trust_score"),
        sa.CheckConstraint("invite_daily_limit >= 0", name="chk_employer_daily_limit"),
        sa.CheckConstraint("invites_sent_today >= 0", name="chk_employer_sent_today"),
    )
    op.create_index("ix_employer_profiles_user_id", "employer_profiles", ["user_id"])
    op.create_index("ix_employer_profiles_inn", "employer_profiles", ["inn"])
    op.create_index("ix_employer_profiles_trust", "employer_profiles", ["trust_score"])

    # 2. employer_needs
    op.create_table(
        "employer_needs",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("employer_profile_id", sa.Integer(), nullable=False),
        sa.Column("specialization_id", sa.Integer(), nullable=False),
        sa.Column("target_grade_id", sa.Integer(), nullable=False),
        sa.Column("core_stack_json", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("nice_to_have_stack_json", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("salary_min", sa.Integer(), nullable=False),
        sa.Column("salary_max", sa.Integer(), nullable=False),
        sa.Column("work_format", sa.String(length=64), server_default=sa.text("'remote'"), nullable=False),
        sa.Column("team_tasks_text", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["employer_profile_id"], ["employer_profiles.id"], name="fk_employer_needs_employer", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["specialization_id"], ["specializations.id"], name="fk_employer_needs_spec", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_grade_id"], ["grades.id"], name="fk_employer_needs_grade", ondelete="RESTRICT"),
        sa.CheckConstraint("salary_min > 0 AND salary_max >= salary_min", name="chk_employer_needs_salary"),
        sa.CheckConstraint("work_format IN ('remote', 'office', 'hybrid', 'any')", name="chk_employer_needs_work_format"),
    )
    op.create_index("ix_employer_needs_employer", "employer_needs", ["employer_profile_id"])
    op.create_index("ix_employer_needs_spec_grade", "employer_needs", ["specialization_id", "target_grade_id"])

    # 3. candidate_categorizations
    op.create_table(
        "candidate_categorizations",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("candidate_profile_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("confirmed_grade_id", sa.Integer(), nullable=False),
        sa.Column("test_score", sa.Float(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("source_session_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"], name="fk_candidate_cat_profile", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], name="fk_candidate_cat_category", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["confirmed_grade_id"], ["grades.id"], name="fk_candidate_cat_grade", ondelete="RESTRICT"),
        sa.CheckConstraint("test_score >= 0.0 AND test_score <= 100.0", name="chk_candidate_cat_score"),
    )
    op.create_index("ix_candidate_cat_cand_curr", "candidate_categorizations", ["candidate_profile_id", "is_current"])
    op.create_index("ix_candidate_cat_cooldown", "candidate_categorizations", ["cooldown_until"])

    # 4. saved_shortlists
    op.create_table(
        "saved_shortlists",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("employer_profile_id", sa.Integer(), nullable=False),
        sa.Column("need_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("filter_criteria_json", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["employer_profile_id"], ["employer_profiles.id"], name="fk_saved_shortlists_employer", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["need_id"], ["employer_needs.id"], name="fk_saved_shortlists_need", ondelete="SET NULL"),
    )
    op.create_index("ix_saved_shortlists_employer", "saved_shortlists", ["employer_profile_id"])
    op.create_index("ix_saved_shortlists_need", "saved_shortlists", ["need_id"])

    # 5. shortlist_items
    op.create_table(
        "shortlist_items",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("shortlist_id", sa.Integer(), nullable=False),
        sa.Column("candidate_profile_id", sa.Integer(), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("match_score", sa.Float(), nullable=False),
        sa.Column("delta_score", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("rank_position", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("explainability_json", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shortlist_id", "candidate_profile_id", name="uq_shortlist_cand"),
        sa.ForeignKeyConstraint(["shortlist_id"], ["saved_shortlists.id"], name="fk_shortlist_items_shortlist", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"], name="fk_shortlist_items_candidate", ondelete="CASCADE"),
        sa.CheckConstraint("match_score >= 0.0 AND match_score <= 100.0", name="chk_shortlist_items_score"),
        sa.CheckConstraint("rank_position > 0", name="chk_shortlist_items_rank"),
    )
    op.create_index("ix_shortlist_items_shortlist", "shortlist_items", ["shortlist_id"])
    op.create_index("ix_shortlist_items_pinned", "shortlist_items", ["shortlist_id", "is_pinned"])
    op.create_index("ix_shortlist_items_score", "shortlist_items", ["shortlist_id", "match_score"])


def downgrade() -> None:
    op.drop_table("shortlist_items")
    op.drop_table("saved_shortlists")
    op.drop_table("candidate_categorizations")
    op.drop_table("employer_needs")
    op.drop_table("employer_profiles")
