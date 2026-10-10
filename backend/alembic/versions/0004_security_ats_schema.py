"""0004_security_ats_schema

Revision ID: 0004_security_ats_schema
Revises: 0003_matching_schema
Create Date: 2026-10-06 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_security_ats_schema"
down_revision: Union[str, None] = "0003_matching_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. fsp_achievements
    op.create_table(
        "fsp_achievements",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("candidate_profile_id", sa.Integer(), nullable=False),
        sa.Column("fsp_id", sa.String(length=64), nullable=False),
        sa.Column("championship_name", sa.String(length=255), nullable=False),
        sa.Column("discipline", sa.String(length=100), nullable=False),
        sa.Column("stage", sa.String(length=50), server_default=sa.text("'всероссийский'"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("place", sa.Integer(), nullable=True),
        sa.Column("medal", sa.String(length=20), nullable=True),
        sa.Column("sport_rank", sa.String(length=50), nullable=True),
        sa.Column("rating_points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("certificate_url", sa.String(length=500), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"], name="fk_fsp_achievements_candidate", ondelete="CASCADE"),
        sa.CheckConstraint("discipline IN ('algorithmic', 'product', 'infosec', 'robotics')", name="chk_fsp_achievements_discipline"),
        sa.CheckConstraint("year BETWEEN 2018 AND 2030", name="chk_fsp_achievements_year"),
        sa.CheckConstraint("place IS NULL OR place > 0", name="chk_fsp_achievements_place"),
        sa.CheckConstraint("medal IS NULL OR medal IN ('gold', 'silver', 'bronze', 'participant')", name="chk_fsp_achievements_medal"),
        sa.CheckConstraint("sport_rank IS NULL OR sport_rank IN ('kms', 'ms', 'none', 'first_class')", name="chk_fsp_achievements_sport_rank"),
        sa.CheckConstraint("rating_points >= 0", name="chk_fsp_achievements_rating"),
    )
    op.create_index("ix_fsp_achievements_candidate", "fsp_achievements", ["candidate_profile_id"])
    op.create_index("ix_fsp_achievements_discipline", "fsp_achievements", ["discipline"])
    op.create_index("ix_fsp_achievements_fsp_id", "fsp_achievements", ["fsp_id"])

    # 2. vacancies
    op.create_table(
        "vacancies",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("employer_profile_id", sa.Integer(), nullable=False),
        sa.Column("specialization_id", sa.Integer(), nullable=False),
        sa.Column("grade_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("required_skills_json", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("salary_min", sa.Integer(), nullable=False),
        sa.Column("salary_max", sa.Integer(), nullable=False),
        sa.Column("work_format", sa.String(length=64), server_default=sa.text("'remote'"), nullable=False),
        sa.Column("city", sa.String(length=100), server_default=sa.text("'Москва'"), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'published'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["employer_profile_id"], ["employer_profiles.id"], name="fk_vacancies_employer", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["specialization_id"], ["specializations.id"], name="fk_vacancies_spec", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["grade_id"], ["grades.id"], name="fk_vacancies_grade", ondelete="RESTRICT"),
        sa.CheckConstraint("salary_min > 0 AND salary_max >= salary_min", name="chk_vacancies_salary"),
        sa.CheckConstraint("status IN ('published', 'closed', 'draft', 'archived')", name="chk_vacancies_status"),
        sa.CheckConstraint("work_format IN ('remote', 'office', 'hybrid', 'any')", name="chk_vacancies_work_format"),
    )
    op.create_index("ix_vacancies_employer", "vacancies", ["employer_profile_id"])
    op.create_index("ix_vacancies_spec_grade", "vacancies", ["specialization_id", "grade_id"])
    op.create_index("ix_vacancies_status", "vacancies", ["status"])

    # 3. invitations
    op.create_table(
        "invitations",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("employer_profile_id", sa.Integer(), nullable=False),
        sa.Column("candidate_profile_id", sa.Integer(), nullable=False),
        sa.Column("need_id", sa.Integer(), nullable=True),
        sa.Column("vacancy_id", sa.Integer(), nullable=True),
        sa.Column("proposal_text", sa.Text(), nullable=False),
        sa.Column("salary_min", sa.Integer(), nullable=False),
        sa.Column("salary_max", sa.Integer(), nullable=False),
        sa.Column("contact_method", sa.String(length=50), server_default=sa.text("'platform'"), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'sent'"), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decline_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["employer_profile_id"], ["employer_profiles.id"], name="fk_invitations_employer", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"], name="fk_invitations_candidate", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["need_id"], ["employer_needs.id"], name="fk_invitations_need", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vacancy_id"], ["vacancies.id"], name="fk_invitations_vacancy", ondelete="SET NULL"),
        sa.CheckConstraint("salary_min > 0 AND salary_max >= salary_min", name="chk_invitations_salary"),
        sa.CheckConstraint("status IN ('sent', 'viewed', 'accepted', 'declined', 'expired')", name="chk_invitations_status"),
    )
    op.create_index("ix_invitations_candidate_status", "invitations", ["candidate_profile_id", "status"])
    op.create_index("ix_invitations_employer_status", "invitations", ["employer_profile_id", "status"])
    op.create_index("ix_invitations_created", "invitations", ["created_at"])
    op.create_index("ix_invitations_emp_cand_status", "invitations", ["employer_profile_id", "candidate_profile_id", "status"])

    # 4. applications
    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("vacancy_id", sa.Integer(), nullable=False),
        sa.Column("candidate_profile_id", sa.Integer(), nullable=False),
        sa.Column("cover_letter", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'applied'"), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vacancy_id", "candidate_profile_id", name="uq_applications_cand_vac"),
        sa.ForeignKeyConstraint(["vacancy_id"], ["vacancies.id"], name="fk_applications_vacancy", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"], name="fk_applications_candidate", ondelete="CASCADE"),
        sa.CheckConstraint("status IN ('applied', 'viewed', 'accepted', 'rejected', 'withdrawn')", name="chk_applications_status"),
    )
    op.create_index("ix_applications_vacancy_status", "applications", ["vacancy_id", "status"])
    op.create_index("ix_applications_candidate", "applications", ["candidate_profile_id"])

    # 5. ats_integrations
    op.create_table(
        "ats_integrations",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("employer_profile_id", sa.Integer(), nullable=False),
        sa.Column("ats_type", sa.String(length=32), nullable=False),
        sa.Column("api_key_hash", sa.String(length=255), nullable=True),
        sa.Column("webhook_url", sa.String(length=500), nullable=True),
        sa.Column("webhook_signing_secret", sa.String(length=128), nullable=True),
        sa.Column("webhook_secret", sa.String(length=255), nullable=True),
        sa.Column("webhook_delivery_logs_json", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("events_subscribed_json", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employer_profile_id", "ats_type", name="uq_employer_ats_type"),
        sa.ForeignKeyConstraint(["employer_profile_id"], ["employer_profiles.id"], name="fk_ats_integrations_employer", ondelete="CASCADE"),
        sa.CheckConstraint("ats_type IN ('huntflow', 'hh', 'headhunter', 'e_staff', 'potok', 'custom', 'custom_webhook')", name="chk_ats_type"),
    )
    op.create_index("ix_ats_integrations_employer", "ats_integrations", ["employer_profile_id"])


def downgrade() -> None:
    op.drop_table("ats_integrations")
    op.drop_table("applications")
    op.drop_table("invitations")
    op.drop_table("vacancies")
    op.drop_table("fsp_achievements")
