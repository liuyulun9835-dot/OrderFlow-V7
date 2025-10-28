"""Minimal publisher implementation to package validation artifacts."""
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

DIST_DIR = Path("dist")
MANIFEST_PATH = DIST_DIR / "manifest.json"
UPLOAD_LOG_PATH = DIST_DIR / "upload.log"
METRICS_SOURCE = Path("validation/metrics_summary.json")
MODEL_NAME = os.getenv("MODEL_NAME", "model_core")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_gate_pass() -> Dict[str, object]:
    if not METRICS_SOURCE.exists():
        print("[publisher] missing metrics_summary.json, abort.")
        sys.exit(1)

    try:
        payload: Dict[str, object] = json.loads(METRICS_SOURCE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        print(f"[publisher] invalid metrics_summary.json ({exc}), abort.")
        sys.exit(1)

    gate = payload.get("gate")
    result = gate.get("result") if isinstance(gate, dict) else None
    if result != "pass":
        print(f"[publisher] gate.result != pass, abort. summary={gate}")
        sys.exit(1)

    return payload


def _collect_model_artifacts() -> List[Path]:
    base = Path("model")
    if not base.exists():
        return []
    return [path for path in base.rglob("*") if path.is_file()]


def _write_manifest(artifacts: List[Path]) -> Dict[str, object]:
    payload: Dict[str, object] = {
        "generated_at": _now(),
        "artifacts": [str(path) for path in artifacts],
    }
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def _copy_metrics() -> Path | None:
    if not METRICS_SOURCE.exists():
        return None
    destination = DIST_DIR / METRICS_SOURCE.name
    shutil.copy2(METRICS_SOURCE, destination)
    return destination


def _derive_gate_status() -> str:
    if METRICS_SOURCE.exists():
        try:
            payload = json.loads(METRICS_SOURCE.read_text())
        except json.JSONDecodeError:
            return "UNKNOWN"
        gate = payload.get("gate")
        if isinstance(gate, dict):
            status = gate.get("status") or gate.get("result")
            if isinstance(status, str):
                return status.upper()
        status = payload.get("overall_status")
        if isinstance(status, str):
            return status.upper()
    return "UNKNOWN"


def _append_upload_log(status: str) -> None:
    timestamp = _now()
    UPLOAD_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with UPLOAD_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} :: gate={status}\n")


def _build_id() -> str:
    git_sha = os.getenv("GIT_SHA", "").strip()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if git_sha:
        return f"{git_sha}+{timestamp}"
    return timestamp


def _write_signatures(summary: Dict[str, object]) -> None:
    model_dir = Path("models") / MODEL_NAME
    model_dir.mkdir(parents=True, exist_ok=True)

    build_id = _build_id()
    signature = {
        "schema_version": "v1",
        "build_id": build_id,
        "data_manifest_hash": "<fill-or-wire-later>",
        "calibration_hash": "<fill-or-wire-later>",
        "policy_version": summary.get("policy_version", "unknown"),
    }
    (model_dir / "signature.json").write_text(
        json.dumps(signature, indent=2), encoding="utf-8"
    )

    artifacts = sorted(
        str(path)
        for path in model_dir.glob("**/*")
        if path.is_file()
    )
    status_payload = {
        "model": MODEL_NAME,
        "version": build_id,
        "validated_at_utc": summary.get("timestamp_utc"),
        "gate_result": summary.get("gate", {}).get("result"),
        "artifacts": artifacts,
    }
    status_dir = Path("status")
    status_dir.mkdir(parents=True, exist_ok=True)
    (status_dir / "model_core.json").write_text(
        json.dumps(status_payload, indent=2), encoding="utf-8"
    )


def publish() -> Dict[str, object]:
    """Collect artifacts into dist/ and emit a minimal upload log."""

    summary = _ensure_gate_pass()
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    artifacts = _collect_model_artifacts()
    manifest = _write_manifest(artifacts)
    _copy_metrics()
    status = _derive_gate_status()
    _append_upload_log(status)
    _write_signatures(summary)
    print("publisher: done")
    return manifest


def main() -> None:
    """Module entry point for CLI compatibility."""

    publish()


__all__ = ["publish", "main"]
