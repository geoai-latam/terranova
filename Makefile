.PHONY: check fmt instalar

instalar:
	uv sync --locked
	uv run pre-commit install

check:
	uv run scripts/check.py

fmt:
	uv run ruff check --fix .
	uv run ruff format .
