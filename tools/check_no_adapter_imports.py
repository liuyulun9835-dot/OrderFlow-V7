#!/usr/bin/env python3
"""Ensure core packages do not import adapter namespaces."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [ROOT / "features" / "core", ROOT / "validation" / "core"]
VIOLATIONS: list[tuple[Path, str]] = []

for target in TARGETS:
    for path in target.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                if "adapter" in stripped and "# allow-adapter" not in stripped:
                    VIOLATIONS.append((path.relative_to(ROOT), stripped))

if VIOLATIONS:
    print("core->adapter import violation detected:")
    for rel, line in VIOLATIONS:
        print(f"  {rel}: {line}")
    sys.exit(1)

sys.exit(0)
