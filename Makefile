.PHONY: help install setup test run clean lint format init-db

help:
	@echo "Illness Prediction System - Available Commands"
	@echo "================================================"
	@echo "install      - Install dependencies"
	@echo "setup        - Complete setup (venv + install + init-db)"
	@echo "init-db      - Initialize database tables"
	@echo "run          - Run the application in development mode"
	@echo "test         - Run all tests"
	@echo "test-unit    - Run unit tests only"
	@echo "test-property - Run property-based tests only"
	@echo "test-cov     - Run tests with coverage report"
	@echo "lint         - Run linters (flake8)"
	@echo "format       - Format code (black, isort)"
	@echo "clean        - Remove generated files"

install:
	pip install -r requirements.txt

setup:
	python -m venv venv
	@echo "Virtual environment created. Activate it with:"
	@echo "  source venv/bin/activate  (Linux/Mac)"
	@echo "  venv\\Scripts\\activate     (Windows)"
	@echo "Then run: make install && make init-db"

init-db:
	python -m src.database.init_db

run:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest

test-unit:
	pytest -m unit

test-property:
	pytest -m property

test-cov:
	pytest --cov=src --cov-report=html --cov-report=term

lint:
	flake8 src/ tests/ --max-line-length=120 --exclude=venv,__pycache__

format:
	black src/ tests/ --line-length=120
	isort src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".hypothesis" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf dist/
	rm -rf build/
