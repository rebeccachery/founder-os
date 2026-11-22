# Founder OS — common tasks. `make help` lists them.
PY      ?= .venv/bin/python
PIP     ?= .venv/bin/pip
TODAY   := $(shell date +%Y-%m-%d)

.DEFAULT_GOAL := help
.PHONY: help install api dashboard scout briefing check lint typecheck test cov \
        eval eval-silver label rescore nightly nightly-install nightly-uninstall clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Create .venv, install Python + dashboard deps, seed .env files
	test -d .venv || python3.12 -m venv .venv || python3 -m venv .venv
	$(PIP) install -q -r requirements-dev.txt
	cd dashboard && npm ci
	test -f .env || cp .env.example .env
	test -f dashboard/.env.local || cp dashboard/.env.local.example dashboard/.env.local

# --- run --------------------------------------------------------------------
api: ## Start the API on :8000 (auto-reload)
	$(PY) -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

dashboard: ## Start the dashboard on :3000
	cd dashboard && npm run dev

scout: ## Run Funding Scout now
	$(PY) workflows/run_agent.py --agent funding_scout

briefing: ## Rebuild today's executive briefing
	$(PY) workflows/run_agent.py --agent executive_assistant

# --- quality ----------------------------------------------------------------
check: lint typecheck test ## Lint + types + tests (what CI runs)

lint: ## Ruff
	$(PY) -m ruff check .

typecheck: ## Mypy (Python) + tsc (dashboard)
	$(PY) -m mypy
	cd dashboard && npx tsc --noEmit

test: ## Pytest
	$(PY) -m pytest

cov: ## Pytest with coverage report
	$(PY) -m pytest --cov --cov-report=term-missing:skip-covered

# --- evaluation -------------------------------------------------------------
eval: ## Evaluate rankers (gold labels if present, else fixture)
	$(PY) -m evals.run

eval-silver: ## Evaluate rankers on silver labels from your scout DB; writes evals/results/
	$(PY) -m evals.run --silver --out evals/results/silver_$(TODAY).md

label: ## Hand-label scout results for the gold eval set
	$(PY) -m evals.label

rescore: ## Preview re-scoring stored opportunities with the current ranker (add ARGS=--apply)
	$(PY) workflows/rescore_scout.py $(ARGS)

# --- nightly ----------------------------------------------------------------
nightly: ## Run the nightly job once, now
	FOUNDER_OS_PYTHON=$(abspath $(PY)) scripts/nightly.sh; tail -n 20 storage/logs/nightly-$(TODAY).log

nightly-install: ## Install the launchd job (06:30 daily; override: make nightly-install AT="7 15")
	scripts/install_nightly.sh $(AT)

nightly-uninstall: ## Remove the launchd job
	scripts/install_nightly.sh --uninstall

clean: ## Remove caches and build output
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage dashboard/.next
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
