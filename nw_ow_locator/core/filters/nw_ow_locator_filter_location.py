#! python3  # noqa: E265
"""
Based on the SwissLocator plugin: https://github.com/opengisch/qgis-swiss-locator
"""

import json

from qgis.core import (
    QgsFeedback,
    QgsGeometry,
    QgsLocatorResult,
    QgsPointXY,
    QgsWkbTypes,
)
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QCoreApplication, QTimer, QUrl
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtNetwork import QNetworkRequest

from nw_ow_locator.__about__ import __icon_dir__
from nw_ow_locator.core.filters.filter_type import FilterType
from nw_ow_locator.core.filters.map_geo_admin import map_geo_admin_url
from nw_ow_locator.core.filters.nw_ow_locator_filter import NwOwLocatorFilter
from nw_ow_locator.core.results import LocationResult
from nw_ow_locator.gui.qtwebkit_conf import with_qt_web_kit
from nw_ow_locator.utils.html_stripper import strip_tags
from nw_ow_locator.utils.utils import url_with_param


class NwOwLocatorFilterLocation(NwOwLocatorFilter):
    def __init__(
        self,
        iface: QgisInterface = None,
        crs: str = None,
        canton=None,
        perimeter=None,
        bbox=None,
    ):
        super().__init__(FilterType.Location, iface, crs, canton)
        self.searchPerimeter = None
        self.searchBbox = None
        if perimeter:
            self.searchPerimeter = perimeter
            self.searchBbox = bbox
        else:
            self.fetch_canton_perimeter()

        if self.iface is not None:
            # Overwrite the changed-crs event listener from the parent
            # to refetch the search perimeter in the correct CRS
            self.map_canvas.destinationCrsChanged.connect(
                self.create_transforms_and_refetch_perimeter
            )

    def displayName(self):
        return self.tr("{} Location Search").format(self.canton_full_name)

    def prefix(self):
        return f"{self.canton}s"

    def create_transforms_and_refetch_perimeter(self):
        self.create_transforms()
        self.fetch_canton_perimeter()

    def perform_fetch_results(self, search: str, feedback: QgsFeedback):
        limit = self.settings.filters[self.type.value]["limit"].value()
        url, params = map_geo_admin_url(
            search, self.type.value, self.crs, self.lang, limit, self.searchBbox
        )
        request = self.request_for_url(url, params, self.HEADERS)
        self.fetch_request(request, feedback, self.handle_content)

    def handle_content(self, content: str, feedback: QgsFeedback):
        try:
            data = json.loads(content)
            for loc in data["results"]:
                if not self.is_inside_search_perimeter(loc):
                    continue
                result = QgsLocatorResult()
                result.filter = self
                group_name, group_layer = self.group_info(loc["attrs"]["origin"])
                result.displayString = strip_tags(loc["attrs"]["label"])
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
                result.icon = QIcon(str(__icon_dir__ / self.canton))
                self.result_found = True
                self.resultFetched.emit(result)

        except Exception as e:
            self.logException(e)

    def fetch_feature(self, layer, feature_id):
        # Try to get more info
        url = f"https://api3.geo.admin.ch/rest/services/ech/MapServer/{layer}/{feature_id}"
        params = {"lang": self.lang, "sr": self.crs}
        url = url_with_param(url, params)
        request = QNetworkRequest(QUrl(url))
        self.fetch_request(request, QgsFeedback(), self.parse_feature_response)

    def parse_feature_response(self, content, feedback: QgsFeedback):
        data = json.loads(content)
        if "feature" not in data:
            return

        geometry = self.parse_polygon(data["feature"])
        if geometry:
            self.feature_rubber_band.reset(QgsWkbTypes.GeometryType.PolygonGeometry)
            self.feature_rubber_band.addGeometry(geometry, None)

    def fetch_canton_perimeter(self):
        if not (self.transform_ch and self.transform_ch.isValid()):
            return
        url = f"https://api3.geo.admin.ch/rest/services/ech/MapServer/find?"
        params = {
            "layer": "ch.swisstopo.swissboundaries3d-kanton-flaeche.fill",
            "searchText": self.canton,
            "searchField": "ak",
            "sr": self.crs,
            "returnGeometry": "true",
        }
        url = url_with_param(url, params)
        request = QNetworkRequest(url)
        self.fetch_request(request, QgsFeedback(), self.parse_perimeter_response)

    def parse_perimeter_response(self, content, feedback: QgsFeedback):
        data = json.loads(content)
        if "results" not in data or len(data["results"]) == 0:
            return

        geometry = self.parse_polygon(data["results"][0])
        if geometry:
            self.info(f"Received {self.canton_full_name} perimeter from geo.admin.ch")
            self.searchPerimeter = geometry
            bbox = geometry.boundingBox()
            bboxCoords = [
                bbox.xMinimum(),
                bbox.yMinimum(),
                bbox.xMaximum(),
                bbox.yMaximum(),
            ]
            self.searchBbox = ",".join([str(coord) for coord in bboxCoords])

    def parse_polygon(self, feature):
        if "geometry" not in feature or "rings" not in feature["geometry"]:
            return None

        rings = feature["geometry"]["rings"]
        for r in range(0, len(rings)):
            for p in range(0, len(rings[r])):
                rings[r][p] = QgsPointXY(rings[r][p][0], rings[r][p][1])
        geometry = QgsGeometry.fromPolygonXY(rings)
        if not geometry:
            return None
        if not (self.transform_ch and self.transform_ch.isValid()):
            return geometry.transform(self.transform_ch)
        else:
            return geometry

    def parse_filter_results(self, search_result: QgsLocatorResult):
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
            },
            "haltestellen": {
                "name": self.tr("Public transport"),
                "layer": "ch.bav.haltestellen-oev",
            },
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

    def is_inside_search_perimeter(self, loc):
        if not self.searchPerimeter:
            return True

        point = QgsPointXY(loc["attrs"]["y"], loc["attrs"]["x"])
        point_geom = QgsGeometry.fromPointXY(point)
        return point_geom.within(self.searchPerimeter)

    def tr(self, message, context="NwOwLocatorFilterLocation", **kwargs):
        # Hard-code the context to the current class name. Translations
        #  occurring in inherited classes otherwise won't work.
        if not context:
            context = self.__class__.__name__
        return QCoreApplication.translate(context, message)


class NwOwLocatorFilterLocationNw(NwOwLocatorFilterLocation):
    def __init__(
        self,
        iface: QgisInterface = None,
        crs: str = None,
        perimeter=None,
        bbox=None,
    ):
        super().__init__(iface, crs, "nw", perimeter, bbox)

    def clone(self):
        return NwOwLocatorFilterLocationNw(
            crs=self.crs,
            perimeter=self.searchPerimeter,
            bbox=self.searchBbox,
        )


class NwOwLocatorFilterLocationOw(NwOwLocatorFilterLocation):
    def __init__(
        self,
        iface: QgisInterface = None,
        crs: str = None,
        perimeter=None,
        bbox=None,
    ):
        super().__init__(iface, crs, "ow", perimeter, bbox)

    def clone(self):
        return NwOwLocatorFilterLocationOw(
            crs=self.crs,
            perimeter=self.searchPerimeter,
            bbox=self.searchBbox,
        )
