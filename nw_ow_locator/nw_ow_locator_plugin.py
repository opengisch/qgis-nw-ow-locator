#! python3  # noqa: E265

from pathlib import Path

from qgis.core import NULL, Qgis, QgsSettings, QgsSettingsTree
from qgis.gui import QgisInterface, QgsMessageBarItem
from qgis.PyQt.QtCore import QCoreApplication, QLocale, QTranslator
from qgis.PyQt.QtWidgets import QWidget

from nw_ow_locator.__about__ import DIR_PLUGIN_ROOT, __name__
from nw_ow_locator.core.filters.nw_ow_locator_filter_layer import (
    NwOwLocatorFilterWmsLayerNw,
    NwOwLocatorFilterWmsLayerOw,
)
from nw_ow_locator.core.filters.nw_ow_locator_filter_location import (
    NwOwLocatorFilterLocationNw,
    NwOwLocatorFilterLocationOw,
)


class NwOwLocatorPlugin:
    def __init__(self, iface: QgisInterface):
        self.iface = iface

        # Translation: initialize the locale
        self.locale: str = (
            QgsSettings()
            .value("locale/userLocale", QLocale().name())
            .replace(str(NULL), "de_CH")[0:2]
        )
        locale_path: Path = DIR_PLUGIN_ROOT / "i18n" / f"{__name__}_{self.locale}.qm"
        if locale_path.exists():
            self.translator = QTranslator()
            self.translator.load(str(locale_path.resolve()))
            QCoreApplication.installTranslator(self.translator)

        self.locator_filters = []

    def initGui(self):
        """Set up plugin UI elements."""
        for _filter in (
            NwOwLocatorFilterLocationNw,
            NwOwLocatorFilterLocationOw,
            NwOwLocatorFilterWmsLayerNw,
            NwOwLocatorFilterWmsLayerOw,
        ):
            locatorFilter = _filter(self.iface)
            self.iface.registerLocatorFilter(locatorFilter)
            locatorFilter.message_emitted.connect(self.show_message)
            self.locator_filters.append(locatorFilter)

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
        for locator_filter in self.locator_filters:
            locator_filter.message_emitted.disconnect(self.show_message)
            self.iface.deregisterLocatorFilter(locator_filter)

        QgsSettingsTree.unregisterPluginTreeNode(__name__)

    def show_message(
        self, title: str, msg: str, level: Qgis.MessageLevel, widget: QWidget = None
    ):
        if widget:
            self.widget = widget
            self.item = QgsMessageBarItem(title, msg, self.widget, level, 7)
            self.iface.messageBar().pushItem(self.item)
        else:
            self.iface.messageBar().pushMessage(title, msg, level)
