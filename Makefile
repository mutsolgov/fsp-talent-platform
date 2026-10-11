.DEFAULT_GOAL := help

PYTHON ?= python3
NODE ?= node
NPM ?= npm
DOCKER_COMPOSE ?= docker compose

# Robust pytest resolution: use pytest if in PATH, otherwise python3 -m pytest
PYTEST ?= $(shell command -v pytest 2>/dev/null || echo "$(PYTHON) -m pytest")

.PHONY: help up down restart logs status ps build build-frontend verify-frontend \
        test test-backend test-frontend consistency benchmark quality-gate seed demo-10min demo clean

help: ## Display available targets and descriptions
	@echo "========================================================================"
	@echo "FSP IT-Talent Platform — Developer & Packaging Toolchain"
	@echo "========================================================================"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all containers in background
	$(DOCKER_COMPOSE) up -d

down: ## Stop all containers
	$(DOCKER_COMPOSE) down

restart: down up ## Restart containerized environment

logs: ## Follow docker container logs
	$(DOCKER_COMPOSE) logs -f

status: ## Show status of running containers
	$(DOCKER_COMPOSE) ps

ps: status ## Alias for status

build: ## Build docker compose containers
	$(DOCKER_COMPOSE) build

build-frontend: ## Transpile and bundle React 19 SPA
	$(NPM) --prefix frontend run build

verify-frontend: ## Run static frontend build verifier (77 components, 35 routes)
	$(NODE) frontend/scripts/verify_build.js

test: test-backend test-frontend ## Run both backend tests and frontend tests

test-backend: ## Run backend tests (132 passed)
	PYTHONPATH=backend $(PYTEST) backend/tests -q

test-frontend: ## Run frontend test suite (81 passed)
	$(NPM) --prefix frontend run test

consistency: ## Run cross-document consistency quality gate (17/17 checks)
	$(PYTHON) scripts/check_consistency.py

benchmark: ## Run 900-pair Golden Validation Benchmark
	$(PYTHON) scripts/run_validation_benchmark.py

quality-gate: consistency benchmark ## Run consistency gate + benchmark 900-pair quality gate
	$(PYTHON) tests/run_quality_gate.py

seed: ## Seed reference taxonomies and synthetic demo dataset
	$(PYTHON) scripts/seed_demo_dataset.py

demo-10min: ## Run automated 10-minute jury evaluation protocol
	$(PYTHON) scripts/run_10min_demo.py

demo: demo-10min ## Alias for demo-10min

clean: ## Clean temporary files, caches, and test artifacts
	rm -rf frontend/.build_temp frontend/dist .pytest_cache htmlcov .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -maxdepth 1 -name "test_*.db" -delete 2>/dev/null || true
