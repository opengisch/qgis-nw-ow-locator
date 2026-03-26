"""
Based on the SwissLocator plugin: https://github.com/opengisch/qgis-swiss-locator
"""

import re
import xml.etree.ElementTree as etree

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsBlockingNetworkRequest,
    QgsFeedback,
    QgsFetchedContent,
    QgsLocatorResult,
    QgsProject,
    QgsRasterLayer,
)
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QCoreApplication, QUrl
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtNetwork import QNetworkRequest

from nw_ow_locator.__about__ import __icon_dir__
from nw_ow_locator.core.constants import NW_OW_WMS_URL
from nw_ow_locator.core.filters.filter_type import FilterType
from nw_ow_locator.core.filters.nw_ow_locator_filter import NwOwLocatorFilter
from nw_ow_locator.core.results import WMSLayerResult


class NwOwLocatorFilterWmsLayer(NwOwLocatorFilter):

    def __init__(
        self,
        iface: QgisInterface = None,
        crs: str = None,
        canton=None,
        capabilities=None,
    ):
        super().__init__(FilterType.Layers, iface, crs, canton)

        self.service_url = f"{NW_OW_WMS_URL}/{self.canton}/service"
        self.capabilities_url = (
            f"{self.service_url}?REQUEST=GetCapabilities&SERVICE=WMS"
        )
        self.capabilities = capabilities

        # do this on main thread only?
        if self.capabilities is None and iface is not None:

            self.content = QgsApplication.networkContentFetcherRegistry().fetch(
                self.capabilities_url
            )
            self.content.fetched.connect(self.handle_capabilities_response)
            self.info(self.content.status())

            if (
                self.content.status() == QgsFetchedContent.ContentStatus.Finished
                and self.content.filePath()
            ):
                file_path = self.content.filePath()
                self.info(
                    f"Capabilities for {self.canton} WMS Layers already downloaded. Reading from {file_path}"
                )
                self.capabilities = etree.parse(file_path).getroot()
            else:
                self.content.download()

    def get_capabilities(self):
        self.content.cancel()
        nam = QgsBlockingNetworkRequest()
        request = QNetworkRequest(QUrl(self.capabilities_url))
        nam.get(request, forceRefresh=True)
        reply = nam.reply()
        if (
            reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) == 200
        ):  # other codes are handled by NetworkAccessManager
            self.capabilities = etree.fromstring(reply.content().data().decode("utf8"))
        else:
            self.info(
                self.tr("Could not fetch capabilities for {} WMS Layers.").format(
                    self.canton
                ),
                Qgis.MessageLevel.Critical,
            )

    def displayName(self):
        return self.tr("{} WMS Layers").format(self.canton_full_name)

    def prefix(self):
        return f"{self.canton}l"

    def handle_capabilities_response(self):
        if (
            self.content.status() == QgsFetchedContent.ContentStatus.Finished
            and self.content.filePath()
        ):
            self.info(
                f"Capabilities for {self.canton} WMS Layers have been downloaded. Reading from {self.content.filePath()}"
            )
            self.capabilities = etree.parse(self.content.filePath()).getroot()
        else:
            self.info(
                self.tr("Could not fetch capabilities for {} WMS Layers.").format(
                    self.canton
                ),
                Qgis.MessageLevel.Critical,
            )

    def perform_fetch_results(self, search: str, feedback: QgsFeedback):
        if self.capabilities is None:
            self.info(
                self.tr(
                    "Capabilities for {} WMS Layers not available, cannot search."
                ).format(self.canton),
                Qgis.MessageLevel.Critical,
            )
            return

        # Get xml namespace
        match = re.match(r"\{.*\}", self.capabilities.tag)
        namespace = match.group(0) if match else ""
        search = search.lower()

        # Search for layers containing the search term in the name or title
        for layer in self.capabilities.findall(".//{}Layer".format(namespace)):
            layerName = self.find_text(layer, "{}Name".format(namespace))
            layerTitle = self.find_text(layer, "{}Title".format(namespace))
            # Find search term in name and title
            indexInName = layerName.lower().find(search)
            indexInTitle = layerTitle.lower().find(search)

            if layerName and (indexInName >= 0 or indexInTitle >= 0):
                if not layerTitle:
                    layerTitle = layerName

                result = QgsLocatorResult()
                result.filter = self
                result.icon = QIcon(str(__icon_dir__ / self.canton))
                result.displayString = layerTitle
                result.description = layerName
                # Create a score based on where the search term appears in the
                #  layer title or name. The score is defined between 0 and 1,
                #  with 1 being the best fit
                result.score = (
                    100 - min([idx for idx in [indexInName, indexInTitle] if idx >= 0])
                ) / 100
                result.userData = WMSLayerResult(
                    layer=layerName,
                    title=layerTitle,
                    url=self.service_url,
                ).as_definition()
                self.result_found = True
                self.resultFetched.emit(result)

    def parse_filter_results(self, search_result: QgsLocatorResult):
        if not isinstance(search_result, WMSLayerResult):
            return

        params = dict()
        params["contextualWMSLegend"] = 0
        params["crs"] = f"EPSG:{self.crs}"  # NOQA E231
        params["dpiMode"] = 7
        params["featureCount"] = 10
        params["format"] = search_result.format
        params["layers"] = search_result.layer
        params["styles"] = search_result.style or ""
        params["url"] = f"{search_result.url}"

        url_with_params = "&".join([f"{k}={v}" for (k, v) in params.items()])

        self.info(f"Loading layer: {url_with_params}")
        wms_layer = QgsRasterLayer(url_with_params, search_result.title, "wms")

        if not wms_layer.isValid():
            msg = self.tr("Cannot load Layers layer: {} ({})").format(
                search_result.title, search_result.layer
            )

            level = Qgis.MessageLevel.Warning
            self.info(msg, level)
        else:
            msg = self.tr("Layers layer added to the map: {} ({})").format(
                search_result.title, search_result.layer
            )

            level = Qgis.MessageLevel.Info

            QgsProject.instance().addMapLayer(wms_layer)

        self.message_emitted.emit(self.displayName(), msg, level, None)

    def tr(self, message, context="NwOwLocatorFilterWmsLayer", **kwargs):
        # Hard-code the context to the current class name. Translations
        #  occurring in inherited classes otherwise won't work.
        if not context:
            context = self.__class__.__name__
        return QCoreApplication.translate(context, message)


class NwOwLocatorFilterWmsLayerNw(NwOwLocatorFilterWmsLayer):
    def __init__(
        self,
        iface: QgisInterface = None,
        crs: str = None,
        capabilities=None,
    ):
        super().__init__(iface, crs, "nw", capabilities)

    def clone(self):
        if self.capabilities is None:
            self.get_capabilities()

        return NwOwLocatorFilterWmsLayerNw(
            crs=self.crs,
            capabilities=self.capabilities,
        )


class NwOwLocatorFilterWmsLayerOw(NwOwLocatorFilterWmsLayer):
    def __init__(
        self,
        iface: QgisInterface = None,
        crs: str = None,
        capabilities=None,
    ):
        super().__init__(iface, crs, "ow", capabilities)

    def clone(self):
        if self.capabilities is None:
            self.get_capabilities()

        return NwOwLocatorFilterWmsLayerOw(
            crs=self.crs,
            capabilities=self.capabilities,
        )
