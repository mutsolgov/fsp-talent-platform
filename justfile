# ==============================================================================
# FSP IT-Talent Platform — Modern Command Runner (justfile)
# Packaging & Delivery Toolchain (Phase 6)
# ==============================================================================

# Default recipe: list available commands
default:
    @just --list

# Show available commands
help:
    @just --list

# Start all containers in background
up:
    docker compose up -d

# Stop all containers
down:
    docker compose down

# Restart containerized environment
restart: down up

# Follow docker container logs
logs:
    docker compose logs -f

# Show status of running containers
status:
    docker compose ps

# Build container images
build:
    docker compose build

# Transpile and bundle React 19 SPA
build-frontend:
    npm --prefix frontend run build

# Run static frontend build verifier (77 components, 35 routes)
verify-frontend:
    node frontend/scripts/verify_build.js

# Run both backend and frontend test suites
test: test-backend test-frontend

# Run full backend pytest suite (132 passed)
test-backend:
    PYTHONPATH=backend python3 -m pytest backend/tests -q

# Run frontend test suite (81 passed)
test-frontend:
    npm --prefix frontend run test

# Run cross-document consistency quality gate (17/17 checks)
consistency:
    python3 scripts/check_consistency.py

# Run 900-pair Golden Validation Benchmark
benchmark:
    python3 scripts/run_validation_benchmark.py

# Run full quality gate (consistency + benchmark validation suite)
quality-gate: consistency benchmark
    python3 tests/run_quality_gate.py

# Seed reference taxonomies and synthetic demo dataset
seed:
    python3 scripts/seed_demo_dataset.py

# Run automated 10-minute jury evaluation protocol
demo-10min:
    python3 scripts/run_10min_demo.py

# Alias for demo-10min
demo: demo-10min

# Clean temporary files, caches, and test artifacts
clean:
    rm -rf frontend/.build_temp frontend/dist .pytest_cache htmlcov .coverage
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -maxdepth 1 -name "test_*.db" -delete 2>/dev/null || true
