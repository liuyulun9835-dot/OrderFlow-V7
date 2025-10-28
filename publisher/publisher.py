from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_id() -> str:
    git_sha = os.getenv("GIT_SHA", "")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return (git_sha + "+" if git_sha else "") + ts


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_gate_pass() -> dict:
    ms_path = Path("validation/metrics_summary.json")
    if not ms_path.exists():
        print("[publisher] missing validation/metrics_summary.json, abort.", file=sys.stderr)
        sys.exit(1)
    summary = json.loads(ms_path.read_text(encoding="utf-8"))
    gate_res = summary.get("gate", {}).get("result")
    if gate_res != "pass":
        print(f"[publisher] gate.result={gate_res} != pass, abort.", file=sys.stderr)
        sys.exit(1)
    return summary


def write_signatures(
    model_dir: Path,
    summary: dict,
    manifest_path: Path | None = None,
    calib_path: Path | None = None,
) -> None:
    model_dir.mkdir(parents=True, exist_ok=True)
    signature = {
        "schema_version": "v1",
        "build_id": _build_id(),
        "data_manifest_hash": _sha256_file(manifest_path)
        if (manifest_path and manifest_path.exists())
        else "<unset>",
        "calibration_hash": _sha256_file(calib_path)
        if (calib_path and calib_path.exists())
        else "<unset>",
        "policy_version": summary.get("policy_version", "unknown"),
    }
    (model_dir / "signature.json").write_text(
        json.dumps(signature, indent=2), encoding="utf-8"
    )
    status = {
        "model": model_dir.name,
        "version": signature["build_id"],
        "validated_at_utc": summary.get("timestamp_utc", _now_iso()),
        "gate_result": summary.get("gate", {}).get("result", "unknown"),
        "artifacts": sorted(
            str(path) for path in model_dir.glob("**/*") if path.is_file()
        ),
    }
    Path("status").mkdir(exist_ok=True)
    (Path("status") / "model_core.json").write_text(
        json.dumps(status, indent=2), encoding="utf-8"
    )


def main() -> None:
    summary = ensure_gate_pass()
    model_name = os.getenv("MODEL_NAME", "V7_CORE_MODEL")
    model_dir = Path("models") / model_name
    (model_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (model_dir / "artifacts" / "weights.bin").write_bytes(b"\x00")
    manifest = Path(os.getenv("DATA_MANIFEST", ""))
    calib = Path(os.getenv("CALIB_FILE", ""))
    write_signatures(model_dir, summary, manifest, calib)
    print(f"[publisher] published artifacts for {model_name}")


if __name__ == "__main__":
    main()
