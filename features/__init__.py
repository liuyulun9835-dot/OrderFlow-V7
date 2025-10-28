"""Feature namespace with core vs adapter separation."""
from __future__ import annotations

import warnings

from . import core as core

# Expose core symbols directly for backwards compatibility.
from .core import *  # noqa: F401,F403

__all__ = list(getattr(core, "__all__", ()))

# Adapter access emits a deprecation warning.
_TODO_DEPRECATE = "TODO: sunset adapter exports after 2025-11-15 (tracking issue #128)."


def __getattr__(name: str):
    if hasattr(core, name):
        return getattr(core, name)
    from . import adapter as adapter  # local import to avoid cycles

    if hasattr(adapter, name):
        warnings.warn(
            "features.adapter is deprecated; migrate to external CDK implementations. "
            + _TODO_DEPRECATE,
            DeprecationWarning,
            stacklevel=2,
        )
        return getattr(adapter, name)
    raise AttributeError(name)


def __dir__() -> list[str]:
    from . import adapter as adapter

    return sorted(set(__all__ + list(getattr(adapter, "__all__", ()))))
