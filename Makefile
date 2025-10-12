install:
poetry install

lint:
ruff check . && black --check . && isort --check .

test:
pytest -q

quickstart: install test

# === 全数据管线 (101–108) ===
data_pipeline:
@echo "=== Step 101: DLL 导出器检查 ==="
@echo "请确保已在 Visual Studio 编译并将 SimplifiedDataExporter.dll 放入 ATAS 指标目录"
@echo "如果未完成，请先手动完成，再运行本任务"
@echo "=== Step 102: ATAS Replay 批量导出 ==="
@scripts/batch_replay.bat || scripts/batch_replay.sh || true
@echo "=== Step 103: JSON Schema 校验 ==="
@poetry run python validation/src/validate_json.py
@echo "=== Step 104: Fetch Exchange Klines ==="
@poetry run python preprocessing/fetch_kline.py --symbol BTC/USDT --since 2020-01-01
@echo "=== Step 105: 成本字典检查 ==="
@echo "请手动确认 validation/configs/costs.yaml 内参数是否正确"
@echo "=== Step 106: Generate trading sessions ==="
@poetry run python preprocessing/gen_sessions.py --market crypto
@echo "=== Step 107: Merge ATAS JSON + Klines to features.parquet ==="
@poetry run python preprocessing/merge_to_features.py --symbol BTCUSDT
@echo "=== Step 108: Run QC report ==="
@poetry run python validation/src/qc_report.py
@echo "=== Data pipeline finished! ==="
