"""Macro factor feature compatibility wrapper."""
from __future__ import annotations

import warnings

# TODO (sunset 2025-11-15, issue #128): drop features.macro_factor once callers migrate to features.core.
from features.core.macro_factor import MacroFactorConfig, build

warnings.warn(
    "features.macro_factor is deprecated; use features.core.macro_factor instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["MacroFactorConfig", "build"]
