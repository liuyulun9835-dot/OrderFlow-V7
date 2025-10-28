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
	poetry run python -m validation.core.aggregator

release:
	@$(PYTHON) - <<-'PY'
	from pathlib import Path
	import json
	import yaml

	metrics_path = Path('validation/metrics_summary.json')
	if not metrics_path.exists():
		raise SystemExit('metrics summary missing; run `make validate` first')

	metrics_payload = json.loads(metrics_path.read_text())
	statuses = metrics_payload.get('statuses', {})
	overall = metrics_payload.get('overall_status', 'fail').lower()
	breaches = [name for name, status in statuses.items() if status == 'fail']

	control = yaml.safe_load(Path('governance/CONTROL_switch_policy.yaml').read_text()) or {}
	policy_version = control.get('signatures', {}).get('version', 'unknown')

	if overall == 'fail' or breaches:
		raise SystemExit(f'release gate failed (policy {policy_version}): {breaches or overall}')

	from publisher.publisher import publish

	manifest = publish()
	print(json.dumps(manifest, indent=2, sort_keys=True))
	PY
