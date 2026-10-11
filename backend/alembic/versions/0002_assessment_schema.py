"""0002_assessment_schema

Revision ID: 0002_assessment_schema
Revises: 0001_initial_schema
Create Date: 2026-10-06 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_assessment_schema"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. candidate_profiles
    op.create_table(
        "candidate_profiles",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("middle_name", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("telegram", sa.String(length=64), nullable=True),
        sa.Column("github_url", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("relocation_ready", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("work_format", sa.String(length=64), nullable=True),
        sa.Column("expected_salary", sa.Integer(), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("raw_resume_pdf_path", sa.String(length=500), nullable=True),
        sa.Column("survey_data_json", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("fsp_id", sa.String(length=64), nullable=True),
        sa.Column("fsp_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("freshness_score", sa.Float(), server_default=sa.text("50.0"), nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_candidate_profiles_user"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_candidate_profiles_user", ondelete="CASCADE"),
        sa.CheckConstraint("work_format IS NULL OR work_format IN ('remote', 'office', 'hybrid', 'any')", name="chk_candidate_work_format"),
        sa.CheckConstraint("expected_salary IS NULL OR expected_salary > 0", name="chk_candidate_salary"),
        sa.CheckConstraint("freshness_score >= 0.0 AND freshness_score <= 100.0", name="chk_candidate_freshness"),
    )
    op.create_index("ix_candidate_profiles_user_id", "candidate_profiles", ["user_id"])
    op.create_index("ix_candidate_profiles_fsp_id", "candidate_profiles", ["fsp_id"])
    op.create_index("ix_candidate_profiles_freshness", "candidate_profiles", ["freshness_score"])

    # 2. candidate_skills
    op.create_table(
        "candidate_skills",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("candidate_profile_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("years_experience", sa.Float(), server_default=sa.text("1.0"), nullable=False),
        sa.Column("proficiency_level", sa.String(length=20), server_default=sa.text("'intermediate'"), nullable=False),
        sa.Column("is_core", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"], name="fk_candidate_skills_profile", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], name="fk_candidate_skills_skill", ondelete="CASCADE"),
        sa.UniqueConstraint("candidate_profile_id", "skill_id", name="uq_candidate_skills"),
        sa.CheckConstraint("years_experience >= 0.0", name="chk_candidate_skills_years"),
        sa.CheckConstraint("proficiency_level IN ('beginner', 'intermediate', 'advanced', 'expert')", name="chk_candidate_skills_level"),
    )
    op.create_index("ix_candidate_skills_profile_skill", "candidate_skills", ["candidate_profile_id", "skill_id"])

    # 3. canonical_item_families
    op.create_table(
        "canonical_item_families",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("specialization_id", sa.Integer(), nullable=False),
        sa.Column("grade_id", sa.Integer(), nullable=False),
        sa.Column("family_code", sa.String(length=64), nullable=False),
        sa.Column("task_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("template_text", sa.Text(), nullable=False),
        sa.Column("param_matrix_json", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("test_generator_code", sa.Text(), nullable=False),
        sa.Column("param_a", sa.Float(), server_default=sa.text("1.0"), nullable=False),
        sa.Column("param_b", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("param_c", sa.Float(), server_default=sa.text("0.2"), nullable=False),
        sa.Column("time_limit_sec", sa.Integer(), server_default=sa.text("1200"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["specialization_id"], ["specializations.id"], name="fk_canonical_items_spec", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["grade_id"], ["grades.id"], name="fk_canonical_items_grade", ondelete="RESTRICT"),
        sa.UniqueConstraint("family_code", name="uq_canonical_items_family_code"),
        sa.CheckConstraint("task_type IN ('algorithmic', 'system_design', 'code_triage', 'code_sandbox', 'mcq')", name="chk_canonical_items_task_type"),
        sa.CheckConstraint("param_a > 0.0", name="chk_canonical_items_param_a"),
        sa.CheckConstraint("param_c >= 0.0 AND param_c <= 1.0", name="chk_canonical_items_param_c"),
        sa.CheckConstraint("time_limit_sec > 0", name="chk_canonical_items_time"),
    )
    op.create_index("ix_canonical_items_spec_grade", "canonical_item_families", ["specialization_id", "grade_id"])
    op.create_index("ix_canonical_items_family_code", "canonical_item_families", ["family_code"])

    # 4. assessment_sessions
    op.create_table(
        "assessment_sessions",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("candidate_profile_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("session_type", sa.String(length=32), server_default=sa.text("'initial'"), nullable=False),
        sa.Column("seed_hash", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'in_progress'"), nullable=False),
        sa.Column("raw_score", sa.Float(), nullable=True),
        sa.Column("theta_score", sa.Float(), nullable=True),
        sa.Column("verdict", sa.String(length=32), nullable=True),
        sa.Column("time_spent_sec", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"], name="fk_assessment_sessions_profile", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], name="fk_assessment_sessions_category", ondelete="RESTRICT"),
        sa.CheckConstraint("session_type IN ('initial', 'boost', 'retest_lower')", name="chk_assessment_session_type"),
        sa.CheckConstraint("status IN ('in_progress', 'completed', 'submitted', 'expired', 'cancelled', 'abandoned')", name="chk_assessment_session_status"),
        sa.CheckConstraint("theta_score IS NULL OR (theta_score >= 0.0 AND theta_score <= 100.0)", name="chk_assessment_session_theta"),
        sa.CheckConstraint("verdict IS NULL OR verdict IN ('confirmed', 'boost_offered', 'retest_lower_offered', 'lower_grade_offered', 'failed')", name="chk_assessment_session_verdict"),
    )
    op.create_index("ix_assessment_sessions_cand_status", "assessment_sessions", ["candidate_profile_id", "status"])
    op.create_index("ix_assessment_sessions_seed_hash", "assessment_sessions", ["seed_hash"])

    # 5. assessment_answers
    op.create_table(
        "assessment_answers",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("item_family_id", sa.Integer(), nullable=False),
        sa.Column("variant_params_json", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("variant_seed", sa.String(length=64), server_default=sa.text("''"), nullable=False),
        sa.Column("candidate_answer_text", sa.Text(), nullable=True),
        sa.Column("submitted_code", sa.Text(), nullable=True),
        sa.Column("test_results_json", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("is_correct", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("points_awarded", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("time_taken_sec", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["assessment_sessions.id"], name="fk_assessment_answers_session", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_family_id"], ["canonical_item_families.id"], name="fk_assessment_answers_item", ondelete="RESTRICT"),
        sa.UniqueConstraint("session_id", "item_family_id", name="uq_session_item"),
        sa.CheckConstraint("points_awarded >= 0.0", name="chk_assessment_answers_points"),
        sa.CheckConstraint("time_taken_sec >= 0", name="chk_assessment_answers_time"),
    )
    op.create_index("ix_assessment_answers_session", "assessment_answers", ["session_id"])

    # 6. cooldown_resets
    op.create_table(
        "cooldown_resets",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("candidate_profile_id", sa.Integer(), nullable=False),
        sa.Column("reset_by_user_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=255), server_default=sa.text("'Jury Demo Bypass'"), nullable=False),
        sa.Column("previous_cooldown_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"], name="fk_cooldown_resets_profile", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reset_by_user_id"], ["users.id"], name="fk_cooldown_resets_user", ondelete="RESTRICT"),
    )
    op.create_index("ix_cooldown_resets_candidate", "cooldown_resets", ["candidate_profile_id"])
    op.create_index("ix_cooldown_resets_created_at", "cooldown_resets", ["created_at"])

    # 7. micro_challenges
    op.create_table(
        "micro_challenges",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("employer_profile_id", sa.Integer(), nullable=True),
        sa.Column("specialization_id", sa.Integer(), nullable=False),
        sa.Column("grade_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("code_stub", sa.Text(), nullable=False),
        sa.Column("test_cases_json", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("points", sa.Integer(), server_default=sa.text("20"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["specialization_id"], ["specializations.id"], name="fk_micro_challenges_spec", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["grade_id"], ["grades.id"], name="fk_micro_challenges_grade", ondelete="RESTRICT"),
        sa.CheckConstraint("points > 0 AND points <= 100", name="chk_micro_challenges_points"),
    )
    op.create_index("ix_micro_challenges_spec_grade", "micro_challenges", ["specialization_id", "grade_id"])
    op.create_index("ix_micro_challenges_employer", "micro_challenges", ["employer_profile_id"])

    # 8. challenge_submissions
    op.create_table(
        "challenge_submissions",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("challenge_id", sa.Integer(), nullable=False),
        sa.Column("candidate_profile_id", sa.Integer(), nullable=False),
        sa.Column("solution_code", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("execution_time_ms", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("memory_kb", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("test_results_json", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("freshness_points_awarded", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["challenge_id"], ["micro_challenges.id"], name="fk_challenge_submissions_chall", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"], name="fk_challenge_submissions_cand", ondelete="CASCADE"),
        sa.CheckConstraint("status IN ('passed', 'failed', 'timeout', 'error')", name="chk_challenge_submission_status"),
        sa.CheckConstraint("execution_time_ms >= 0", name="chk_challenge_submission_time"),
        sa.CheckConstraint("memory_kb >= 0", name="chk_challenge_submission_memory"),
        sa.CheckConstraint("freshness_points_awarded >= 0.0", name="chk_challenge_submission_freshness"),
    )
    op.create_index("ix_challenge_submissions_cand_chall", "challenge_submissions", ["candidate_profile_id", "challenge_id"])
    op.create_index("ix_challenge_submissions_status", "challenge_submissions", ["status"])


def downgrade() -> None:
    op.drop_table("challenge_submissions")
    op.drop_table("micro_challenges")
    op.drop_table("cooldown_resets")
    op.drop_table("assessment_answers")
    op.drop_table("assessment_sessions")
    op.drop_table("canonical_item_families")
    op.drop_table("candidate_skills")
    op.drop_table("candidate_profiles")
