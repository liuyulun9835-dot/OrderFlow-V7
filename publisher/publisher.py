"""Minimal publisher implementation to package validation artifacts."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

DIST_DIR = Path("dist")
MANIFEST_PATH = DIST_DIR / "manifest.json"
UPLOAD_LOG_PATH = DIST_DIR / "upload.log"
METRICS_SOURCE = Path("validation/metrics_summary.json")


def _collect_model_artifacts() -> List[Path]:
    base = Path("model")
    if not base.exists():
        return []
    return [path for path in base.rglob("*") if path.is_file()]


def _write_manifest(artifacts: List[Path]) -> Dict[str, object]:
    payload: Dict[str, object] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
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
            status = gate.get("status")
            if isinstance(status, str):
                return status.upper()
        status = payload.get("overall_status")
        if isinstance(status, str):
            return status.upper()
    return "UNKNOWN"


def _append_upload_log(status: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    UPLOAD_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with UPLOAD_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} :: gate={status}\n")


def publish() -> Dict[str, object]:
    """Collect artifacts into dist/ and emit a minimal upload log."""

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    artifacts = _collect_model_artifacts()
    manifest = _write_manifest(artifacts)
    _copy_metrics()
    status = _derive_gate_status()
    _append_upload_log(status)
    print("publisher: done")
    return manifest


def main() -> None:
    """Module entry point for CLI compatibility."""

    publish()


__all__ = ["publish", "main"]
