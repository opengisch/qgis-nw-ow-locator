#! python3  # noqa: E265#! python3  # noqa: E265
"""
Based on the SwissLocator plugin: https://github.com/opengisch/qgis-swiss-locator
"""

import json
import os

from qgis.core import (
    QgsFeedback,
    QgsGeometry,
    QgsLocatorResult,
    QgsPointXY,
    QgsWkbTypes,
)
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QTimer, QUrl
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtNetwork import QNetworkRequest

from nw_ow_locator.__about__ import DIR_PLUGIN_ROOT
from nw_ow_locator.core.filters.filter_type import FilterType
from nw_ow_locator.core.filters.map_geo_admin import map_geo_admin_url
from nw_ow_locator.core.filters.nw_ow_locator_filter import NwOwLocatorFilter
from nw_ow_locator.core.results import LocationResult
from nw_ow_locator.gui.qtwebkit_conf import with_qt_web_kit
from nw_ow_locator.utils.html_stripper import strip_tags
from nw_ow_locator.utils.utils import url_with_param


class NwOwLocatorFilterLocation(NwOwLocatorFilter):
    def __init__(self, iface: QgisInterface = None, crs: str = None):
        super().__init__(FilterType.Location, iface, crs)
        self.canton = "nw"

    def clone(self):
        return NwOwLocatorFilterLocation(crs=self.crs)

    def displayName(self):
        return self.tr("NW Suchdienst")

    def prefix(self):
        # TODO: "nwl" ?? also needs one for ow
        return "nws"

    def perform_fetch_results(self, search: str, feedback: QgsFeedback):
        limit = self.settings.filters[self.type.value]["limit"].value()
        url, params = map_geo_admin_url(
            search, self.type.value, self.crs, self.lang, limit, self.canton
        )
        request = self.request_for_url(url, params, self.HEADERS)
        self.fetch_request(request, feedback, self.handle_content)

    def handle_content(self, content: str, feedback: QgsFeedback):
        try:
            data = json.loads(content)
            for loc in data["results"]:
                result = QgsLocatorResult()
                result.filter = self
                result.group = self.tr("Swiss Geoportal")
                for key, val in loc["attrs"].items():
                    self.dbg_info(f"{key}: {val}")
                group_name, group_layer = self.group_info(loc["attrs"]["origin"])
                if "layerBodId" in loc["attrs"]:
                    self.dbg_info("layer: {}".format(loc["attrs"]["layerBodId"]))
                if "featureId" in loc["attrs"]:
                    self.dbg_info("feature: {}".format(loc["attrs"]["featureId"]))

                result.displayString = strip_tags(loc["attrs"]["label"])
                # result.description = loc['attrs']['detail']
                # if 'featureId' in loc['attrs']:
                #     result.description = loc['attrs']['featureId']
                result.group = group_name
                result.userData = LocationResult(
                    point=QgsPointXY(loc["attrs"]["y"], loc["attrs"]["x"]),
                    bbox=self.box2geometry(loc["attrs"]["geom_st_box2d"]),
                    layer=group_layer,
                    feature_id=(
                        loc["attrs"]["featureId"]
                        if "featureId" in loc["attrs"]
                        else None
                    ),
                    html_label=loc["attrs"]["label"],
                ).as_definition()
                result.icon = QIcon(os.path.join(DIR_PLUGIN_ROOT, "swiss_locator.png"))
                self.result_found = True
                self.resultFetched.emit(result)

        except Exception as e:
            self.logException(e)

    def fetch_feature(self, layer, feature_id):
        # Try to get more info
        url = f"https://api3.geo.admin.ch/rest/services/api/MapServer/{layer}/{feature_id}"
        params = {"lang": self.lang, "sr": self.crs}
        url = url_with_param(url, params)
        request = QNetworkRequest(QUrl(url))
        self.fetch_request(request, QgsFeedback(), self.parse_feature_response)

    def parse_feature_response(self, content, feedback: QgsFeedback):
        data = json.loads(content)
        self.dbg_info(data)

        if "feature" not in data or "geometry" not in data["feature"]:
            return

        if "rings" in data["feature"]["geometry"]:
            rings = data["feature"]["geometry"]["rings"]
            self.dbg_info(rings)
            for r in range(0, len(rings)):
                for p in range(0, len(rings[r])):
                    rings[r][p] = QgsPointXY(rings[r][p][0], rings[r][p][1])
            geometry = QgsGeometry.fromPolygonXY(rings)
            geometry.transform(self.transform_ch)

            self.feature_rubber_band.reset(QgsWkbTypes.GeometryType.PolygonGeometry)
            self.feature_rubber_band.addGeometry(geometry, None)

    def processFilterSpecificResult(self, search_result: QgsLocatorResult):
        if not isinstance(search_result, LocationResult):
            return

        point = QgsGeometry.fromPointXY(search_result.point)
        if search_result.bbox.isNull():
            bbox = None
        else:
            bbox = QgsGeometry.fromRect(search_result.bbox)
            bbox.transform(self.transform_ch)
        layer = search_result.layer
        feature_id = search_result.feature_id
        if not point:
            return

        point.transform(self.transform_ch)

        self.highlight(point, bbox)

        if layer and feature_id:
            self.fetch_feature(layer, feature_id)

            if self.settings.show_map_tip.value() and with_qt_web_kit():
                self.show_map_tip(layer, feature_id, point)
        else:
            self.current_timer = QTimer()
            self.current_timer.timeout.connect(self.clearPreviousResults)
            self.current_timer.setSingleShot(True)
            self.current_timer.start(5000)

    def group_info(self, group: str):
        groups = {
            "zipcode": {
                "name": self.tr("ZIP code"),
                "layer": "ch.swisstopo-vd.ortschaftenverzeichnis_plz",
            },
            "gg25": {
                "name": self.tr("Municipal boundaries"),
                "layer": "ch.swisstopo.swissboundaries3d-gemeinde-flaeche.fill",
            },
            "district": {
                "name": self.tr("District"),
                "layer": "ch.swisstopo.swissboundaries3d-bezirk-flaeche.fill",
            },
            "kantone": {
                "name": self.tr("Cantons"),
                "layer": "ch.swisstopo.swissboundaries3d-kanton-flaeche.fill",
            },
            "gazetteer": {
                "name": self.tr("Index"),
                "layer": "ch.swisstopo.swissnames3d",
            },  # there is also: ch.bav.haltestellen-oev ?
            "address": {
                "name": self.tr("Address"),
                "layer": "ch.bfs.gebaeude_wohnungs_register",
            },
            "parcel": {"name": self.tr("Parcel"), "layer": None},
        }
        if group not in groups:
            self.info("Could not find group {} in dictionary".format(group))
            return None, None
        return groups[group]["name"], groups[group]["layer"]
