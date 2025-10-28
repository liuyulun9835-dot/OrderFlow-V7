.PHONY: install lint test validate release

install:
python -m pip install -U pip
pip install -e .[dev]

lint:
python -m ruff check .
python -m mypy .

test:
pytest -q

validate:
python -m validation.core.aggregator --runs-dir validation/runs --out-dir validation

release: validate
python publisher/publisher.py
