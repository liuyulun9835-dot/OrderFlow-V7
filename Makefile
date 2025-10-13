install:
poetry install

lint:
ruff check . && black --check . && isort --check .

test:
pytest -q

quickstart: install test

# === 全数据管线 (103–108) ===
data_pipeline:
@echo "=== Step 103: JSON Schema 校验 ==="
@poetry run python validation/src/validate_json.py
@echo "=== Step 104: Fetch Exchange Klines ==="
@poetry run python preprocessing/fetch_kline.py --symbol BTC/USDT --since 2020-01-01
@echo "=== Step 105: 成本字典检查 ==="
@echo "请手动确认 validation/configs/costs.yaml 已根据你的账户修改"
@echo "=== Step 106: Generate trading sessions ==="
@poetry run python preprocessing/gen_sessions.py --market crypto
@echo "=== Step 107: Merge ATAS JSON + Klines to features.parquet ==="
@poetry run python preprocessing/merge_to_features.py --symbol BTCUSDT
@echo "=== Step 108: Run QC report ==="
@poetry run python validation/src/qc_report.py
@echo "=== Data pipeline finished! ==="
