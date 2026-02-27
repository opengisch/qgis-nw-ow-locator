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
__summary__ = "Suche für Örtlichkeiten und Geodaten in den Kantonen Nidwalden und Obwalden  |  Search for places and data in the cantons Nidwalden und Obwalden"
__uri_homepage__ = "https://github.com/opengisch/qgis-nw-ow-locator/pages"
__uri_tracker__ = "https://github.com/opengisch/qgis-nw-ow-locator/issues"
__author__ = "OPENGIS.ch"
__email__ = "support@opengis.ch"
__license__ = "GPL-3.0"
__copyright__ = "Copyright (c) 2026 OPENGIS.ch"
__version__ = "0.1.0"

# Icon used in menus/help entries
__icon_path__ = DIR_PLUGIN_ROOT / "resources" / "icons" / "nw_ow_locator.png"

# What gets exported when using: from nw_ow_locator.__about__ import *
__all__ = [
    "DIR_PLUGIN_ROOT",
    "__title__",
    "__summary__",
    "__uri_homepage__",
    "__uri_tracker__",
    "__author__",
    "__email__",
    "__license__",
    "__copyright__",
    "__version__",
    "__icon_path__",
]
