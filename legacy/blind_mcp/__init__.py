"""Compatibility shim. The project is now payband-mcp.

Anything imported from here comes straight from payband_mcp, so code written
against the old name keeps working. Nothing is reimplemented -- if this
module and payband_mcp ever disagreed, the disagreement would be the bug.
"""

from __future__ import annotations

import importlib
import sys
import warnings

import payband_mcp

warnings.warn(
    "blind-mcp has been renamed to payband-mcp. This release only re-exports "
    "it and will not be updated. Install payband-mcp and import payband_mcp.",
    DeprecationWarning,
    stacklevel=2,
)

__version__ = payband_mcp.__version__

# Bind the submodules under both names so `from blind_mcp import server` and
# `import blind_mcp.money` resolve to the same objects payband_mcp exposes.
for _name in ("ats", "fx", "http", "levels", "money", "parse", "server", "workday"):
    _module = importlib.import_module(f"payband_mcp.{_name}")
    sys.modules[f"{__name__}.{_name}"] = _module
    globals()[_name] = _module

del _name, _module, importlib, sys, warnings
