"""
Based on the SwissLocator plugin: https://github.com/opengisch/qgis-swiss-locator
"""

import os

from qgis.core import QgsLocatorFilter
from qgis.gui import (
    QgsSettingsBoolCheckBoxWrapper,
    QgsSettingsEditorWidgetWrapper,
    QgsSettingsEnumEditorWidgetWrapper,
    QgsSettingsIntegerSpinBoxWrapper,
    QgsSettingsStringComboBoxWrapper,
)
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QSpinBox,
)
from qgis.PyQt.uic import loadUiType

from ..core.filters.filter_type import FilterType
from ..core.parameters import AVAILABLE_LANGUAGES
from ..core.settings import Settings
from .qtwebkit_conf import with_qt_web_kit

DialogUi, _ = loadUiType(os.path.join(os.path.dirname(__file__), "../ui/config.ui"))


class ConfigDialog(QDialog, DialogUi):
    def accept(self):
        for wrapper in self.wrappers:
            wrapper.setSettingFromWidget()
        super().accept()

    def __init__(self, parent=None):
        self.settings = Settings()
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.wrappers: list[QgsSettingsEditorWidgetWrapper] = []

        self.lang.addItem(
            self.tr("use the application locale, defaults to English"), ""
        )
        for key, val in AVAILABLE_LANGUAGES.items():
            self.lang.addItem(key, val)

        self.wrappers.append(
            QgsSettingsStringComboBoxWrapper(
                self.lang,
                self.settings.lang,
                QgsSettingsStringComboBoxWrapper.Mode.Data,
            )
        )

        display_strings = {
            QgsLocatorFilter.Priority.Highest: self.tr("Highest"),
            QgsLocatorFilter.Priority.High: self.tr("High"),
            QgsLocatorFilter.Priority.Medium: self.tr("Medium"),
            QgsLocatorFilter.Priority.Low: self.tr("Low"),
            QgsLocatorFilter.Priority.Lowest: self.tr("Lowest"),
        }

        for filter_type in FilterType:
            cb = self.findChild(QComboBox, "{}_priority".format(filter_type.value))
            if cb is not None:  # Some filters might not have a config dialog
                ew = QgsSettingsEnumEditorWidgetWrapper(
                    editor=cb,
                    setting=self.settings.filters[filter_type.value]["priority"],
                    displayStrings=display_strings,
                )
                self.wrappers.append(ew)

            sb = self.findChild(QSpinBox, "{}_limit".format(filter_type.value))
            if sb is not None:
                sbw = QgsSettingsIntegerSpinBoxWrapper(
                    sb, self.settings.filters[filter_type.value]["limit"]
                )
                self.wrappers.append(sbw)

        if not with_qt_web_kit():
            self.show_map_tip.setEnabled(False)
            self.show_map_tip.setToolTip(
                self.tr("You need to install QtWebKit to use map tips.")
            )
        else:
            self.wrappers.append(
                QgsSettingsBoolCheckBoxWrapper(
                    self.show_map_tip, self.settings.show_map_tip
                )
            )
