#!/usr/bin/env python3
"""scripts/audit_v7_1.py

Minimal audit script for V7.1 stability unified changes. Checks presence of required files and basic gate definitions.
Writes a human-readable markdown report to output/audits/v7_1_audit.md.
"""
from __future__ import annotations
import os
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "output" / "audits"
OUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = OUT_DIR / "v7_1_audit.md"

required_files = [
    "features/noise_metrics/__init__.py",
    "features/noise_metrics/compute_noise_energy.py",
    "features/noise_metrics/compute_drift_bandwidth.py",
    "features/noise_metrics/compute_clarity_spectrum.py",
    "features/noise_metrics/compute_adversarial_gap.py",
    "validation/noise_metrics.yaml",
    "docs/TODO_V7.md",
]

found = {}
for p in required_files:
    found[p] = (ROOT / p).exists()

# simple YAML parse of validation file for thresholds if exists
thresholds = {}
gates = []
val_path = ROOT / "validation" / "noise_metrics.yaml"
if val_path.exists():
    try:
        import yaml
        with open(val_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            thresholds = data.get("thresholds", {}) or {}
            gates = data.get("gates", []) or []
    except Exception:
        # fallback: attempt naive parse
        with open(val_path, "r", encoding="utf-8") as f:
            text = f.read()
            thresholds = {}
            gates = []

# governance schema check (existence only)
schema_model = (ROOT / "governance" / "SCHEMA_model.json")
schema_present = schema_model.exists()

# Produce report
lines = []
lines.append("# V7.1 Audit Report")
lines.append("")
lines.append("## Snapshot")
lines.append("")
lines.append(f"Branch: feat/v7_1-stability-unify")
lines.append("")
lines.append("## File presence checks")
lines.append("")
for p, ok in found.items():
    lines.append(f"- {p}: {'FOUND' if ok else 'MISSING'}")

lines.append("")
lines.append("## Validation/noise_metrics.yaml content summary")
lines.append("")
if thresholds:
    lines.append("### thresholds")
    for k, v in thresholds.items():
        lines.append(f"- {k}: {v}")
else:
    lines.append("- thresholds: NOT PARSED or EMPTY")

if gates:
    lines.append("")
    lines.append("### gates")
    for g in gates:
        lines.append(f"- {g}")
else:
    lines.append("- gates: NOT PARSED or EMPTY")

lines.append("")
lines.append("## Governance schema check")
lines.append("")
lines.append(f"- governance/SCHEMA_model.json: {'FOUND' if schema_present else 'MISSING'}")

lines.append("")
lines.append("## Gate evaluation summary")
lines.append("")
lines.append("Note: No runtime production data provided; gate thresholds cannot be statistically evaluated. The audit validates file presence and gate definitions only.")

lines.append("")
lines.append("## Next steps")
lines.append("")
lines.append("- If you want numeric gate checks, provide a sample dataset or run this script in an environment with historical metrics available.")

REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
print(f'Wrote audit report to: {REPORT_PATH}')
