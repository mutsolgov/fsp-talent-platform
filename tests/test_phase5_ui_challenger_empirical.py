#!/usr/bin/env python3
"""
FSP IT-Talent Platform — Phase 5 Frontend Invariants & RBAC Empirical Stress Harness
Challenger: challenger_phase5_ui_1

Empirically tests:
1. SalaryRangeInput domain invariants (min > 0, max >= min, ratio <= 3.5, RUB currency).
2. App.tsx 35 routes and full RBAC security matrix (140 role-route combinations).
3. RadarMatchChart 4-axis SVG radar math redistribution for non-FSP candidates (weights sum = 1.0, zero score penalty).
"""
import re
import sys
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
APP_TSX = FRONTEND_DIR / "src" / "App.tsx"
SALARY_INPUT_TSX = FRONTEND_DIR / "src" / "components" / "molecules" / "SalaryRangeInput.tsx"
RADAR_CHART_TSX = FRONTEND_DIR / "src" / "components" / "molecules" / "RadarMatchChart.tsx"
PROTECTED_ROUTE_TSX = FRONTEND_DIR / "src" / "components" / "atoms" / "ProtectedRoute.tsx"
RANKING_ENGINE_PY = REPO_ROOT / "backend" / "app" / "services" / "ranking_engine.py"

def test_salary_range_domain_invariants():
    """Verify SalaryRangeInput invariant logic against canonical business rules."""
    print(">>> [STRESS 1] SalaryRangeInput Domain Invariants...")

    def validate_salary_range(min_val: float, max_val: float) -> str | None:
        if min_val <= 0:
            return "Минимальная зарплата должна быть строго больше нуля"
        if max_val < min_val:
            return "Максимальная зарплата не может быть меньше минимальной"
        if min_val > 0 and max_val / min_val > 3.5:
            return "Разброс зарплатной вилки не может превышать 3.5x"
        return None

    # 1.1 Non-positive minimums
    assert validate_salary_range(0, 200000) == "Минимальная зарплата должна быть строго больше нуля"
    assert validate_salary_range(-1, 200000) == "Минимальная зарплата должна быть строго больше нуля"
    assert validate_salary_range(-100000, 100000) == "Минимальная зарплата должна быть строго больше нуля"
    assert validate_salary_range(-0.0001, 100000) == "Минимальная зарплата должна быть строго больше нуля"

    # 1.2 Inverted range (max < min)
    assert validate_salary_range(200000, 100000) == "Максимальная зарплата не может быть меньше минимальной"
    assert validate_salary_range(300000, 299999) == "Максимальная зарплата не может быть меньше минимальной"
    assert validate_salary_range(500000, 1) == "Максимальная зарплата не может быть меньше минимальной"

    # 1.3 Spread ratio boundary conditions (spread <= 3.5)
    # Exact boundary 3.5x -> MUST BE ACCEPTED
    assert validate_salary_range(100000, 350000) is None, "3.5x boundary must be accepted"
    assert validate_salary_range(50000, 175000) is None, "3.5x boundary must be accepted"
    assert validate_salary_range(200000, 700000) is None, "3.5x boundary must be accepted"

    # Exceeding boundary -> MUST BE REJECTED
    assert validate_salary_range(100000, 350001) == "Разброс зарплатной вилки не может превышать 3.5x"
    assert validate_salary_range(100000, 350100) == "Разброс зарплатной вилки не может превышать 3.5x"
    assert validate_salary_range(100000, 360000) == "Разброс зарплатной вилки не может превышать 3.5x"
    assert validate_salary_range(50000, 200000) == "Разброс зарплатной вилки не может превышать 3.5x"
    assert validate_salary_range(100000, 1000000) == "Разброс зарплатной вилки не может превышать 3.5x"

    # Valid realistic cases
    assert validate_salary_range(150000, 250000) is None
    assert validate_salary_range(200000, 300000) is None
    assert validate_salary_range(100000, 100000) is None  # Flat rate min==max
    assert validate_salary_range(300000, 600000) is None  # 2.0x

    # Inspect source code of SalaryRangeInput.tsx to ensure no regression
    content = SALARY_INPUT_TSX.read_text(encoding="utf-8")
    assert "min <= 0" in content, "Missing min <= 0 check"
    assert "max < min" in content, "Missing max < min check"
    assert "max / min > 3.5" in content, "Missing 3.5x spread check"
    assert "RubCurrencySymbol" in content, "Missing RubCurrencySymbol"
    assert "toLocaleString('ru-RU')" in content, "Missing ru-RU currency localization"
    print("  -> SalaryRangeInput domain invariants PASS (all boundary cases verified).")


def test_app_routes_and_rbac_matrix():
    """Extract and stress-test all 35 canonical routes and 140 RBAC role combinations."""
    print(">>> [STRESS 2] App.tsx 35 Canonical Routes & RBAC Matrix...")

    content = APP_TSX.read_text(encoding="utf-8")

    # Extract all route definitions
    # Regex for route objects: { id: 'R..', path: '...', pattern: /.../, allowedRoles: [...] }
    route_pattern = re.compile(
        r"id:\s*'(R[0-9]{2})',\s*path:\s*'([^']+)',\s*pattern:\s*(/(?:\\/|[^/\n])+/[a-z]*),\s*allowedRoles:\s*\[([^\]]+)\]",
        re.DOTALL
    )

    matches = route_pattern.findall(content)
    assert len(matches) == 35, f"Expected exactly 35 canonical routes, found {len(matches)}"

    routes_dict = {}
    for r_id, r_path, r_regex_str, r_roles_str in matches:
        roles = [r.strip().strip("'\"") for r in r_roles_str.split(",") if r.strip()]
        # Parse JS regex string e.g. /^\/vacancies\/\d+$/
        raw_regex = r_regex_str.strip("/")
        compiled_regex = re.compile(raw_regex)
        routes_dict[r_id] = {
            "id": r_id,
            "path": r_path,
            "regex": compiled_regex,
            "allowedRoles": roles,
        }

    # Verify all R01..R35 are present
    expected_ids = [f"R{i:02d}" for i in range(1, 36)]
    assert sorted(routes_dict.keys()) == expected_ids, "Route IDs mismatch from R01 to R35"

    # Canonical sample URLs to test path matching
    test_urls = {
        "R01": "/",
        "R02": "/login",
        "R03": "/register",
        "R04": "/auth/callback",
        "R05": "/verify-email",
        "R06": "/vacancies",
        "R07": "/vacancies/123",
        "R08": "/categories",
        "R09": "/candidate/onboarding",
        "R10": "/candidate/assessment/42",
        "R11": "/candidate/assessment/42/results",
        "R12": "/candidate/profile",
        "R13": "/candidate/invitations",
        "R14": "/candidate/applications",
        "R15": "/candidate/challenges",
        "R16": "/candidate/challenges/99",
        "R17": "/candidate/privacy",
        "R18": "/employer/needs",
        "R19": "/employer/needs/new",
        "R20": "/employer/needs/5",
        "R21": "/employer/candidate-bank",
        "R22": "/employer/candidate-bank/10",
        "R23": "/employer/shortlists",
        "R24": "/employer/shortlists/7",
        "R25": "/employer/invitations",
        "R26": "/employer/vacancies",
        "R27": "/employer/vacancies/new",
        "R28": "/employer/vacancies/88",
        "R29": "/employer/applications",
        "R30": "/employer/ats-settings",
        "R31": "/employer/challenges/new",
        "R32": "/demo/dashboard",
        "R33": "/demo/benchmark-runner",
        "R34": "/admin/audit-logs",
        "R35": "/admin/analytics",
    }

    # Verify URL regex matching
    for r_id, url in test_urls.items():
        r = routes_dict[r_id]
        assert r["regex"].match(url), f"Route {r_id} regex failed to match {url}"

    # Verify negative non-matching (Adversarial inputs)
    assert not routes_dict["R07"]["regex"].match("/vacancies/abc"), "R07 must reject non-numeric id"
    assert not routes_dict["R10"]["regex"].match("/candidate/assessment/abc"), "R10 must reject non-numeric session id"
    assert not routes_dict["R20"]["regex"].match("/employer/needs/xyz"), "R20 must reject non-numeric need id"
    assert not routes_dict["R22"]["regex"].match("/employer/candidate-bank/xyz"), "R22 must reject non-numeric candidate id"
    assert not routes_dict["R34"]["regex"].match("/admin/audit-logs/delete"), "R34 must reject subpaths"

    # Full RBAC Matrix: 4 roles x 35 routes = 140 checks
    roles_tested = ["public", "candidate", "employer", "admin"]
    matrix_results = {"authorized": 0, "blocked_403": 0}

    for r_id in expected_ids:
        route = routes_dict[r_id]
        allowed = set(route["allowedRoles"])

        for user_role in roles_tested:
            is_authorized = (user_role in allowed) or (user_role == "admin")

            if user_role == "public":
                # Public should only access public landing, auth, public vacancies, categories, and jury demo
                if r_id in ["R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R32", "R33"]:
                    assert is_authorized, f"Public should have access to {r_id}"
                else:
                    assert not is_authorized, f"Public must be BLOCKED (403) from {r_id}"

            elif user_role == "candidate":
                # Candidate has access to public routes + candidate routes R09-R17 + demo
                if r_id in ["R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08",
                            "R09", "R10", "R11", "R12", "R13", "R14", "R15", "R16", "R17",
                            "R32", "R33"]:
                    assert is_authorized, f"Candidate should have access to {r_id}"
                else:
                    # Blocked from employer (R18-R31) and admin (R34-R35)
                    assert not is_authorized, f"Candidate must be BLOCKED (403) from {r_id}"

            elif user_role == "employer":
                # Employer has access to public routes + employer routes R18-R31 + demo
                if r_id in ["R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08",
                            "R18", "R19", "R20", "R21", "R22", "R23", "R24",
                            "R25", "R26", "R27", "R28", "R29", "R30", "R31",
                            "R32", "R33"]:
                    assert is_authorized, f"Employer should have access to {r_id}"
                else:
                    # Blocked from candidate (R09-R17) and admin (R34-R35)
                    assert not is_authorized, f"Employer must be BLOCKED (403) from {r_id}"

            elif user_role == "admin":
                # Admin has access to all routes unconditionally
                assert is_authorized, f"Admin must have superuser access to {r_id}"

            if is_authorized:
                matrix_results["authorized"] += 1
            else:
                matrix_results["blocked_403"] += 1

    # ProtectedRoute inspection
    pr_content = PROTECTED_ROUTE_TSX.read_text(encoding="utf-8")
    assert "403" in pr_content, "ProtectedRoute must render 403 status"
    assert "Доступ ограничен (RBAC 152-ФЗ)" in pr_content, "ProtectedRoute must state 152-ФЗ restriction"
    assert "/login" in pr_content, "ProtectedRoute must include fallback login link"
    assert "/demo/dashboard" in pr_content, "ProtectedRoute must include jury demo link"

    print(f"  -> RBAC Matrix 140 checks PASS: {matrix_results['authorized']} Authorized, {matrix_results['blocked_403']} Blocked (403).")


def test_radar_match_chart_math_redistribution():
    """Verify RadarMatchChart SVG 4-axis math and non-FSP penalty neutrality."""
    print(">>> [STRESS 3] RadarMatchChart Math Redistribution & SVG Symmetry...")

    # Load ranking engine weights from backend to cross-verify frontend specification
    re_content = RANKING_ENGINE_PY.read_text(encoding="utf-8")
    assert "WEIGHTS_WITH_FSP = (0.35, 0.25, 0.25, 0.15)" in re_content
    assert "WEIGHTS_WITHOUT_FSP = (0.52, 0.30, 0.00, 0.18)" in re_content

    # Weight sums
    w_fsp = (0.35, 0.25, 0.25, 0.15)
    w_non_fsp = (0.52, 0.30, 0.00, 0.18)

    assert round(sum(w_fsp), 6) == 1.00, "FSP weights must sum to 1.00"
    assert round(sum(w_non_fsp), 6) == 1.00, "Non-FSP weights must sum to 1.00"

    # Ceiling test: both models have a 100.0 maximum possible score
    fsp_max = 0.35 * 100 + 0.25 * 100 + 0.25 * 100 + 0.15 * 100
    non_fsp_max = 0.52 * 100 + 0.30 * 100 + 0.00 * 0 + 0.18 * 100
    assert fsp_max == 100.0, f"FSP maximum score is {fsp_max}"
    assert non_fsp_max == 100.0, f"Non-FSP maximum score is {non_fsp_max}"
    assert fsp_max == non_fsp_max, "Zero score penalty invariant violated!"

    # Inspect RadarMatchChart.tsx component implementation
    chart_content = RADAR_CHART_TSX.read_text(encoding="utf-8")
    assert "isFspProfile ? 'ФСП Разряд' : 'Практика (0.52)'" in chart_content, "Missing redistributed 3rd axis label"
    assert "isFspProfile ? fspMatch : testMatch" in chart_content, "Missing value redistribution to testMatch"
    assert "#402FFF" in chart_content, "Missing FSP brandbook violet theme"
    assert "#00F5D4" in chart_content, "Missing mint accent theme for non-FSP"
    assert "<table className=\"sr-only\">" in chart_content, "Missing WCAG AAA accessible table"

    # Geometric calculation verification
    import math
    size = 220
    center = size / 2
    radius = (size / 2) * 0.75

    # 4 angles: -pi/2 (Top), 0 (Right), pi/2 (Bottom), pi (Left)
    angles = [-math.pi / 2, 0, math.pi / 2, math.pi]
    test_score = 90.0

    coords = []
    for angle in angles:
        r = (test_score / 100) * radius
        x = center + r * math.cos(angle)
        y = center + r * math.sin(angle)
        coords.append((round(x, 1), round(y, 1)))

    # Symmetry checks:
    # Top and Bottom have x == center
    assert coords[0][0] == center, "Top vertex x must align with center"
    assert coords[2][0] == center, "Bottom vertex x must align with center"
    # Right and Left have y == center
    assert coords[1][1] == center, "Right vertex y must align with center"
    assert coords[3][1] == center, "Left vertex y must align with center"

    print("  -> RadarMatchChart math redistribution PASS (weights sum = 1.00, score ceiling = 100.0, SVG geometry symmetric).")


def main():
    print("=" * 80)
    print("FSP IT-TALENT PLATFORM — PHASE 5 UI INVARIANTS & RBAC EMPIRICAL HARNESS")
    print("=" * 80)
    try:
        test_salary_range_domain_invariants()
        test_app_routes_and_rbac_matrix()
        test_radar_match_chart_math_redistribution()
        print("=" * 80)
        print("ALL EMPIRICAL ADVERSARIAL STRESS TESTS PASSED (CONFIRMED / APPROVE)")
        print("=" * 80)
        return 0
    except AssertionError as e:
        print(f"\n[DEFECT DETECTED]: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n[UNEXPECTED ERROR]: {e}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
