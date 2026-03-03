#! python3  # noqa: E265
"""
Based on the SwissLocator plugin: https://github.com/opengisch/qgis-swiss-locator
"""

from qgis.core import (
    QgsLocatorFilter,
    QgsSettingsEntryBool,
    QgsSettingsEntryEnumFlag,
    QgsSettingsEntryInteger,
    QgsSettingsEntryString,
    QgsSettingsEntryStringList,
    QgsSettingsTree,
)

from nw_ow_locator.__about__ import (
    __name__,
)
from nw_ow_locator.core.filters.filter_type import FilterType


class Settings:
    instance = None

    def __new__(cls):
        if cls.instance is None:
            cls.instance = super(Settings, cls).__new__(cls)

            settings_node = QgsSettingsTree.createPluginTreeNode(pluginName=__name__)

            cls.lang = QgsSettingsEntryString("lang", settings_node, "")
            cls.show_map_tip = QgsSettingsEntryBool(
                "show_map_tip", settings_node, False
            )
            # cls.feature_search_restrict = QgsSettingsEntryBool(
            #     "feature_search_restrict", settings_node, False
            # )
            # cls.layers_include_opendataswiss = QgsSettingsEntryBool(
            #     "layers_include_opendataswiss", settings_node, True
            # )
            # cls.feature_search_layers_list = QgsSettingsEntryStringList(
            #     "feature_search_layers_list", settings_node, []
            # )

            filters = {
                FilterType.Location.value: {
                    "priority": QgsSettingsEntryEnumFlag(
                        f"{FilterType.Location.value}_priority",
                        settings_node,
                        QgsLocatorFilter.Priority.Highest,
                    ),
                    "limit": QgsSettingsEntryInteger(
                        f"{FilterType.Location.value}_limit", settings_node, 8
                    ),
                },
                FilterType.Layers.value: {
                    "priority": QgsSettingsEntryEnumFlag(
                        f"{FilterType.Layers.value}_priority",
                        settings_node,
                        QgsLocatorFilter.Priority.High,
                    ),
                    "limit": QgsSettingsEntryInteger(
                        f"{FilterType.Layers.value}_limit", settings_node, 5
                    ),
                },
            }
            cls.filters = filters

        return cls.instance
