#! python3  # noqa: E265
"""
Centralized plugin metadata/constants.

Keeping these values in one place avoids import cycles and makes it easy to reuse
plugin title, homepage, icon path, etc. across the codebase.
"""

from __future__ import annotations

from pathlib import Path

DIR_PLUGIN_ROOT = Path(__file__).resolve().parent

# Public "about" constants (used across the plugin)
__title__ = "NW OW Locator"
__name__ = "nw_ow_locator"
__author__ = "OPENGIS.ch"
__email__ = "support@opengis.ch"
__license__ = "GPL-3.0"

# Icon used in menus/help entries
__icon_dir__ = DIR_PLUGIN_ROOT / "resources" / "icons"
__icon_path__ = __icon_dir__ / "nw_ow_locator.png"

# What gets exported when using: from nw_ow_locator.__about__ import *
__all__ = [
    "DIR_PLUGIN_ROOT",
    "__title__",
    "__name__",
    "__author__",
    "__email__",
    "__license__",
    "__icon_dir__",
    "__icon_path__",
]
