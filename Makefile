.ONESHELL:
.PHONY: install lint test data.qc cluster.fit tvtp.fit validate dryrun release

PYTHON = poetry run python

install:
	poetry install

lint:
	poetry run ruff check .
	poetry run black --check .
	poetry run isort --check .
	poetry run mypy .

test:
	poetry run pytest -q

data.qc:
	@$(PYTHON) - <<-'PY'
	from pathlib import Path
	report = Path("output/calibration_report.md")
	report.parent.mkdir(parents=True, exist_ok=True)
	report.write_text("# Calibration Report\n\nStub output for V7 data.qc pipeline.\n")
	print(f"wrote {report}")
	PY

cluster.fit:
	@$(PYTHON) - <<-'PY'
	import numpy as np
	import pandas as pd
	from model.clusterer_dynamic.fit import load_default_config, run
	
	features = ["bar_vpo_imbalance", "bar_vpo_absorption", "cvd_rolling", "volprofile_skew"]
	frame = pd.DataFrame(np.random.randn(512, len(features)), columns=features)
	config = load_default_config(features)
	run(frame, config)
	print("cluster.fit completed (stub data)")
	PY

tvtp.fit:
	@$(PYTHON) - <<-'PY'
	import numpy as np
	import pandas as pd
	from model.hmm_tvtp_adaptive.train import TrainingConfig, train
	
	features = ["macro_regime", "volatility_slope"]
	states = np.random.choice(["A", "B"], size=600)
	frame = pd.DataFrame({
	"state": states,
	"macro_regime": np.random.randn(600),
	"volatility_slope": np.random.randn(600),
	})
	config = TrainingConfig(feature_columns=features)
	train(frame, config)
	print("tvtp.fit completed (stub data)")
	PY

validate:
	@$(PYTHON) -c "import pandas as pd; from pathlib import Path; from validation.metrics import write_reports; transition_path = Path('output/tvtp/transition_prob.parquet'); csv_path = transition_path.with_suffix('.csv'); frame = pd.read_parquet(transition_path) if transition_path.exists() else (pd.read_csv(csv_path) if csv_path.exists() else pd.DataFrame()); write_reports(frame); print('validation reports updated')"

dryrun:
	@echo "[dryrun] Execute strategy dry-run with current artifacts (stub)"

release:
	@$(PYTHON) -c "import json, yaml; from pathlib import Path; metrics = json.loads(Path('validation/metrics_summary.json').read_text()); control = yaml.safe_load(Path('governance/CONTROL_switch_policy.yaml').read_text()); breach = []; \
    (breach.append('prototype_drift') if metrics.get('prototype_drift', 0.0) > control['drift_metrics']['prototype_drift']['fail'] else None); \
    (breach.append('ece') if metrics.get('ece', 0.0) > control['calibration']['ece']['fail'] else None); \
    (breach.append('brier') if metrics.get('brier', 0.0) > control['calibration']['brier']['fail'] else None); \
    (breach.append('abstain_rate') if metrics.get('abstain_rate', 0.0) > control['abstain_rate']['max'] or metrics.get('abstain_rate', 0.0) < control['abstain_rate']['min'] else None); \
    (breach.append('transition_hit_ratio') if metrics.get('transition_hit_ratio', 0.0) < control['transition_hit_ratio']['min'] else None); \
    ( (_ for _ in ()).throw(SystemExit(f\"release gate failed: {', '.join(breach)}\")) if breach else None ); print('release gate passed')"
