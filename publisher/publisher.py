"""Single publishing entry for V7 artifacts."""
from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

LOGGER = logging.getLogger(__name__)

_DIST_DIR = Path("publisher/dist")
_UPLOAD_LOG = Path("publisher/upload.log")
_PACKAGE_MANIFEST = _DIST_DIR / "package_manifest.json"

_ARTIFACT_SOURCES = [
    Path("model/hmm_tvtp_adaptive/artifacts/model_params.json"),
    Path("validation/metrics_summary.json"),
    Path("validation/VALIDATION.md"),
    Path("output/tvtp/transition_prob.parquet"),
]


def _ensure_dist() -> None:
    _DIST_DIR.mkdir(parents=True, exist_ok=True)


def _copy_artifacts() -> List[Path]:
    copied: List[Path] = []
    for source in _ARTIFACT_SOURCES:
        if not source.exists():
            LOGGER.warning("Skipping missing artifact: %s", source)
            continue
        destination = _DIST_DIR / source.name
        if source.is_file():
            shutil.copy2(source, destination)
        else:
            LOGGER.warning("Artifact is not a file; skipping: %s", source)
            continue
        copied.append(destination)
    return copied


def _build_signature(copied: List[Path]) -> Path:
    signature_path = _DIST_DIR / "signature.json"
    params_path = next(
        (path for path in copied if path.name == "model_params.json"), None
    )
    features: List[str] = []
    if params_path is not None:
        try:
            payload = json.loads(params_path.read_text())
            features = list(payload.get("feature_columns", []))
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            LOGGER.warning("Unable to decode model params for signature: %s", exc)
    signature = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "feature_columns": features,
        "sources": [str(path.name) for path in copied],
    }
    signature_path.write_text(json.dumps(signature, indent=2, sort_keys=True))
    return signature_path


def _write_manifest(copied: List[Path], signature: Path) -> Dict[str, Any]:
    manifest = {
        "artifacts": [
            {
                "name": path.name,
                "size": path.stat().st_size if path.exists() else 0,
            }
            for path in copied
        ],
        "signature": signature.name,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    _PACKAGE_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def _simulate_upload(manifest: Dict[str, Any]) -> None:
    message = f"{datetime.utcnow().isoformat()}Z :: uploaded package with {len(manifest['artifacts'])} artifacts"
    _UPLOAD_LOG.parent.mkdir(parents=True, exist_ok=True)
    with _UPLOAD_LOG.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")
    LOGGER.info("Simulated upload complete; details written to %s", _UPLOAD_LOG)


def publish() -> Dict[str, Any]:
    """Package artifacts and simulate publishing."""

    _ensure_dist()
    copied = _copy_artifacts()
    signature = _build_signature(copied)
    manifest = _write_manifest(copied, signature)
    _simulate_upload(manifest)
    return manifest


def main() -> None:
    publish()


__all__ = ["publish", "main"]
