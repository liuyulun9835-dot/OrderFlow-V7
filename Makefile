.PHONY: install lint test validate release

PYTHON = poetry run python

install:
	poetry install --with dev

lint:
	python tools/check_no_adapter_imports.py
	poetry run ruff check .
	poetry run black --check .
	poetry run isort --check .
	poetry run mypy .

test:
	poetry run pytest -q

validate:
	$(PYTHON) -m validation.core.aggregator

release:
	$(PYTHON) tools/release_gate.py
