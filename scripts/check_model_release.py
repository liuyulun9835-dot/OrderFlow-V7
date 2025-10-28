#!/usr/bin/env python3
"""Model-layer release checklist.

Validates that model artifacts, signatures, validation outputs, and governance
status files exist before publishing. Only inspects model-layer surfaces.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List, Sequence

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"

REQUIRED_TOP_LEVEL = [
    ROOT / "validation" / "VALIDATION.md",
    ROOT / "validation" / "metrics_summary.json",
    ROOT / "status" / "model_core.json",
]


def find_model_dirs(model_names: Sequence[str] | None) -> List[Path]:
    if model_names:
        return [MODELS_DIR / name for name in model_names]
    if not MODELS_DIR.exists():
        return []
    return [p for p in MODELS_DIR.iterdir() if p.is_dir()]


def check_signature(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing signature.json"
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        return False, f"invalid JSON: {exc}"
    return True, "ok"


def ensure_artifacts(dir_path: Path) -> tuple[bool, str]:
    files = [p for p in dir_path.iterdir() if p.is_file() and p.name != "signature.json"]
    if not files:
        return False, "no artifact files alongside signature"
    return True, f"{len(files)} artifact file(s)"


def check_model_dir(dir_path: Path) -> tuple[bool, List[str]]:
    issues: List[str] = []
    if not dir_path.exists():
        issues.append("model directory missing")
        return False, issues
    signature_ok, sig_msg = check_signature(dir_path / "signature.json")
    if not signature_ok:
        issues.append(sig_msg)
    artifacts_ok, art_msg = ensure_artifacts(dir_path)
    if not artifacts_ok:
        issues.append(art_msg)
    return not issues, issues if issues else [sig_msg, art_msg]


def check_top_level(paths: Iterable[Path]) -> List[str]:
    missing = []
    for path in paths:
        if not path.exists():
            missing.append(str(path.relative_to(ROOT)))
    return missing


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models",
        nargs="*",
        help="Explicit model directories (relative to models/) to validate. Defaults to all directories under models/.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat absence of models directory as an error (default: warning).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    model_dirs = find_model_dirs(args.models)
    results = []
    exit_code = 0

    if not model_dirs:
        message = "no model directories discovered"
        if args.strict:
            exit_code = 1
            results.append(("models/", False, [message]))
        else:
            results.append(("models/", True, [message]))
    else:
        for dir_path in model_dirs:
            ok, details = check_model_dir(dir_path)
            if not ok:
                exit_code = 1
            rel = dir_path.relative_to(ROOT)
            results.append((str(rel), ok, details))

    missing_top = check_top_level(REQUIRED_TOP_LEVEL)
    if missing_top:
        exit_code = 1

    print("# Model Release Checklist")
    print()
    print("## Model artifacts")
    for name, ok, details in results:
        status = "OK" if ok else "MISSING"
        print(f"- {name}: {status}")
        for detail in details:
            print(f"  - {detail}")
    print()
    print("## Validation & governance")
    if missing_top:
        for path in missing_top:
            print(f"- {path}: MISSING")
    else:
        for path in REQUIRED_TOP_LEVEL:
            print(f"- {path.relative_to(ROOT)}: OK")

    return exit_code


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
