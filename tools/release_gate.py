"""Release gate entrypoint before invoking publisher."""
# ruff: noqa: E402  # allow sys.path mutation before importing publisher
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml  # type: ignore[import]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from publisher.publisher import publish

CONTROL_PATH = Path("governance/CONTROL_switch_policy.yaml")
METRICS_PATH = Path("validation/metrics_summary.json")


def _load_policy() -> dict:
    if not CONTROL_PATH.exists():
        raise SystemExit("control policy missing; cannot gate release")
    return yaml.safe_load(CONTROL_PATH.read_text()) or {}


def _load_metrics() -> dict:
    if not METRICS_PATH.exists():
        raise SystemExit("metrics summary missing; run `make validate` first")
    try:
        return json.loads(METRICS_PATH.read_text())
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise SystemExit(f"invalid metrics summary: {exc}") from exc


def _resolve_verdict(metrics: dict) -> str:
    gate = metrics.get("gate") or {}
    gate_status = None
    if isinstance(gate, dict):
        raw_status = gate.get("status") or gate.get("result")
        if isinstance(raw_status, str):
            gate_status = raw_status.strip().lower()
    overall_status = metrics.get("overall_status")
    if isinstance(overall_status, str):
        overall_status = overall_status.strip().lower()
    verdict = gate_status or overall_status or "fail"
    if verdict not in {"pass", "warn", "fail"}:
        return "fail"
    return verdict


def main() -> None:
    policy = _load_policy()
    metrics = _load_metrics()
    verdict = _resolve_verdict(metrics)
    if verdict != "pass":
        policy_version = (
            policy.get("signatures", {}).get("version", "unknown")
            if isinstance(policy, dict)
            else "unknown"
        )
        raise SystemExit(
            f"release gate blocked under policy {policy_version}: {verdict.upper()}"
        )

    publish()


if __name__ == "__main__":
    main()
