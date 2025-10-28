from __future__ import annotations

import sys
from pathlib import Path


REQUIRED = [
    Path("validation/metrics_summary.json"),
    Path("validation/VALIDATION.md"),
]


def check() -> int:
    ok = True
    for path in REQUIRED:
        if not path.exists():
            print(f"[check] missing {path}", file=sys.stderr)
            ok = False
    if not Path("models").exists():
        print(
            "[check] models directory not found (will be created by publisher)",
            file=sys.stderr,
        )
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(check())
