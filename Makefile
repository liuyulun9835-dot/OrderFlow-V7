install:
	poetry install

lint:
	ruff check . && black --check . && isort --check .

test:
	pytest -q

quickstart: install test
