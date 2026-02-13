.PHONY: help venv install install-backend install-frontend build build-frontend \
       dev-backend dev-frontend test test-backend test-frontend lint lint-backend lint-frontend

# Default target: list all available targets
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Setup:"
	@echo "  venv              Create Python virtual environment"
	@echo "  install           Install all dependencies (backend + frontend)"
	@echo "  install-backend   Install Python dependencies"
	@echo "  install-frontend  Install Node dependencies"
	@echo ""
	@echo "Build:"
	@echo "  build             Build all (frontend)"
	@echo "  build-frontend    Build frontend with Vite"
	@echo ""
	@echo "Dev:"
	@echo "  dev-backend       Run FastAPI dev server (port 8000)"
	@echo "  dev-frontend      Run Vite dev server (port 5173)"
	@echo ""
	@echo "Test:"
	@echo "  test              Run all tests (backend + frontend)"
	@echo "  test-backend      Run pytest"
	@echo "  test-frontend     Run vitest"
	@echo ""
	@echo "Lint:"
	@echo "  lint              Run all linters"
	@echo "  lint-backend      Run ruff (check + format)"
	@echo "  lint-frontend     Run eslint + prettier"

# Create a virtual environment (run once, then activate it)
venv:
	python -m venv .venv
	@echo "Activate with: source .venv/Scripts/activate"

# Install all dependencies
install: install-backend install-frontend

install-backend:
	pip install -e "./backend[dev]"

install-frontend:
	cd frontend && npm install

# Build
build: build-frontend

build-frontend:
	cd frontend && npm run build

# Dev servers
dev-backend:
	python -m uvicorn pct.main:app --reload --host 127.0.0.1 --port 8000

dev-frontend:
	cd frontend && npm run dev

# Tests
test: test-backend test-frontend

test-backend:
	cd backend && python -m pytest

test-frontend:
	cd frontend && npx vitest run

# Linting
lint: lint-backend lint-frontend

lint-backend:
	python -m ruff check backend/src/ backend/tests/ && python -m ruff format --check backend/src/ backend/tests/

lint-frontend:
	cd frontend && npx eslint src/ && npx prettier --check src/
