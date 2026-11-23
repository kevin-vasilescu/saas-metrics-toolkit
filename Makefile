.PHONY: install lint format test check build

install:
	pip install -e ".[dev]"

lint:
	ruff check .
	ruff format --check .
	mypy --strict src

format:
	ruff check --fix .
	ruff format .

test:
	pytest --cov --cov-report=term-missing --cov-fail-under=90

check: lint test

build:
	python -m build
	twine check dist/*
