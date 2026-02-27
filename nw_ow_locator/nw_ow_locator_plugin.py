#! python3  # noqa: E265

from functools import partial
from pathlib import Path

from qgis.core import NULL, Qgis, QgsApplication, QgsSettings
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QCoreApplication, QLocale, QTranslator, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QIcon
from qgis.PyQt.QtWidgets import QAction

from nw_ow_locator.__about__ import (
    DIR_PLUGIN_ROOT,
    __title__,
)
from nw_ow_locator.toolbelt import PlgLogger


class NwOwLocatorPlugin:
    def __init__(self, iface: QgisInterface):
        self.iface = iface
        self.log = PlgLogger().log

        # Translation: initialize the locale
        self.locale: str = (
            QgsSettings()
            .value("locale/userLocale", QLocale().name())
            .replace(str(NULL), "de_CH")[0:2]
        )
        locale_path: Path = (
            DIR_PLUGIN_ROOT / "resources" / "i18n" / f"{__title__}_{self.locale}.qm"
        )
        self.log(
            message=f"Translation: {self.locale}, {locale_path}",
            log_level=Qgis.MessageLevel.NoLevel,
        )
        if locale_path.exists():
            self.translator = QTranslator()
            self.translator.load(str(locale_path.resolve()))
            QCoreApplication.installTranslator(self.translator)

    def initGui(self):
        """Set up plugin UI elements."""
        pass

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def unload(self):
        """Cleans up when the plugin is disabled/uninstalled."""
        pass
