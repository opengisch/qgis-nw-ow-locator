"""
Based on the SwissLocator plugin: https://github.com/opengisch/qgis-swiss-locator
"""

import os
import re
import sys
import traceback

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeedback,
    QgsLocatorContext,
    QgsLocatorFilter,
    QgsLocatorResult,
    QgsMessageLog,
    QgsProject,
    QgsRectangle,
    QgsWkbTypes,
)
from qgis.gui import QgisInterface, QgsRubberBand
from qgis.PyQt import sip
from qgis.PyQt.QtCore import QEventLoop, Qt, QUrl, pyqtSignal
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from qgis.PyQt.QtWidgets import QTabWidget, QWidget

from nw_ow_locator import DEBUG
from nw_ow_locator.__about__ import __title__
from nw_ow_locator.core.constants import MAP_SERVER_URL, USER_AGENT
from nw_ow_locator.core.filters.filter_type import FilterType
from nw_ow_locator.core.language import get_language
from nw_ow_locator.core.parameters import AVAILABLE_CRS
from nw_ow_locator.core.results import (
    NoResult,
)
from nw_ow_locator.core.results import result_from_data as _result_from_data
from nw_ow_locator.core.settings import Settings
from nw_ow_locator.gui.config_dialog import ConfigDialog
from nw_ow_locator.gui.maptip import MapTip
from nw_ow_locator.utils.utils import url_with_param


def result_from_data(result: QgsLocatorResult):
    # see https://github.com/qgis/QGIS/pull/40452
    if hasattr(result, "getUserData"):
        definition = result.getUserData()
    else:
        definition = result.userData
    return _result_from_data(definition)


class InvalidBox(Exception):
    pass


class NwOwLocatorFilter(QgsLocatorFilter):

    HEADERS = {b"User-Agent": USER_AGENT}

    message_emitted = pyqtSignal(str, str, Qgis.MessageLevel, QWidget)

    canton_full_names = {
        "nw": "Nidwalden",
        "ow": "Obwalden",
    }

    def __init__(
        self,
        filter_type: FilterType,
        iface: QgisInterface = None,
        crs: str = None,
        canton=None,
    ):
        """ "
        :param filter_type: the type of filter
        :param iface: QGIS interface, given when on the main thread (which will display/trigger results), None otherwise
        :param crs: if iface is not given, it shall be provided, see clone()
        """
        super().__init__()
        self.type = filter_type
        self.canton = canton
        self.canton_full_name = self.canton_full_names[canton]
        self.rubber_band = None
        self.feature_rubber_band = None
        self.iface = iface
        self.map_canvas = None
        self.settings = Settings()
        self.transform_ch = None
        self.transform_4326 = None
        self.map_tip = None
        self.current_timer = None
        self.crs = None
        self.event_loop = None
        self.result_found = False
        self.access_managers = {}
        self.minimum_search_length = 3

        self.nam = QNetworkAccessManager()
        self.nam.setRedirectPolicy(
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy
        )
        self.network_replies = dict()

        if crs:
            self.crs = crs

        self.lang = get_language()

        if iface is not None:
            # happens only in main thread
            self.map_canvas = iface.mapCanvas()
            self.map_canvas.destinationCrsChanged.connect(self.create_transforms)

            self.rubber_band = QgsRubberBand(
                self.map_canvas, QgsWkbTypes.GeometryType.PointGeometry
            )
            self.rubber_band.setColor(QColor(255, 211, 50, 255))
            self.rubber_band.setIcon(self.rubber_band.ICON_CIRCLE)
            self.rubber_band.setIconSize(18)
            self.rubber_band.setWidth(5)
            self.rubber_band.setBrushStyle(Qt.BrushStyle.NoBrush)

            self.feature_rubber_band = QgsRubberBand(
                self.map_canvas, QgsWkbTypes.GeometryType.PolygonGeometry
            )
            self.feature_rubber_band.setColor(QColor(255, 50, 50, 200))
            self.feature_rubber_band.setFillColor(QColor(255, 255, 50, 160))
            self.feature_rubber_band.setBrushStyle(Qt.BrushStyle.SolidPattern)
            self.feature_rubber_band.setLineStyle(Qt.PenStyle.SolidLine)
            self.feature_rubber_band.setWidth(4)

            self.create_transforms()

    def name(self):
        return self.__class__.__name__

    def priority(self):
        return self.settings.filters[self.type.value]["priority"].value()

    def displayName(self):
        # this should be re-implemented
        raise NameError(
            "Filter type is not valid. This method should be reimplemented."
        )

    def prefix(self):
        # this should be re-implemented
        raise NameError(
            "Filter type is not valid. This method should be reimplemented."
        )

    def clearPreviousResults(self):
        self.rubber_band.reset(QgsWkbTypes.GeometryType.PointGeometry)
        self.feature_rubber_band.reset(QgsWkbTypes.GeometryType.PolygonGeometry)
        if self.map_tip is not None:
            del self.map_tip
            self.map_tip = None
        if self.current_timer is not None:
            self.current_timer.stop()
            self.current_timer.deleteLater()
            self.current_timer = None

    def hasConfigWidget(self):
        return True

    def openConfigWidget(self, parent=None):
        dlg = ConfigDialog(parent)
        wid = dlg.findChild(
            QTabWidget, "tabWidget", Qt.FindChildOption.FindDirectChildrenOnly
        )
        tab = wid.findChild(QWidget, self.type.value)
        wid.setCurrentWidget(tab)
        dlg.exec()

    def create_transforms(self):
        # this should happen in the main thread
        map_crs = self.map_canvas.mapSettings().destinationCrs()
        if map_crs.isValid() and ":" in map_crs.authid():
            self.crs = map_crs.authid().split(":")[1]
        if self.crs not in AVAILABLE_CRS:
            self.crs = "2056"
        assert self.crs in AVAILABLE_CRS
        src_crs_ch = QgsCoordinateReferenceSystem("EPSG:{}".format(self.crs))
        assert src_crs_ch.isValid()
        dst_crs = self.map_canvas.mapSettings().destinationCrs()
        self.transform_ch = QgsCoordinateTransform(
            src_crs_ch, dst_crs, QgsProject.instance()
        )

        src_crs_4326 = QgsCoordinateReferenceSystem("EPSG:4326")
        self.transform_4326 = QgsCoordinateTransform(
            src_crs_4326, dst_crs, QgsProject.instance()
        )

    @staticmethod
    def box2geometry(box: str) -> QgsRectangle:
        """
        Creates a rectangle from a Box definition as string
        :param box: the box as a string
        :return: the rectangle
        """
        coords = re.findall(r"\b(\d+(?:\.\d+)?)\b", box)
        if len(coords) != 4:
            raise InvalidBox(f"Could not parse: {box}")
        return QgsRectangle(
            float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3])
        )

    @staticmethod
    def request_for_url(url, params, headers) -> QNetworkRequest:
        url = url_with_param(url, params)
        request = QNetworkRequest(url)
        for k, v in list(headers.items()):
            request.setRawHeader(k, v)
        return request

    def handle_reply(self, url: str, feedback: QgsFeedback, slot, data=None):
        if sip.isdeleted(self):
            return
        self.dbg_info(f"feature handle reply {url}")
        if url not in self.network_replies:
            # might be happening when both event_loop.quit() and reply.abort() are called
            self.dbg_info(
                f"url {url} missing from network_replies, "
                "it was likely already handled or cancelled"
            )
            return
        reply = self.network_replies[url]

        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                self.info(f"could not load url: {reply.errorString()}")
            else:
                content = reply.readAll().data().decode("utf-8")
                if data:
                    slot(content, feedback, data)
                else:
                    slot(content, feedback)

        except Exception as e:
            self.logException(e)

        # clean nam
        reply.deleteLater()
        self.network_replies.pop(url, None)

        # quit loop if every nam has completed
        if len(self.network_replies) == 0:
            self.dbg_info(f"{url} no nam left, exit loop")
            self.event_loop.quit()

    def fetch_request(
        self, request: QNetworkRequest, feedback: QgsFeedback, slot, data=None
    ):
        return self.fetch_requests([request], feedback, slot, data)

    def fetch_requests(
        self, requests: list[QNetworkRequest], feedback: QgsFeedback, slot, data=None
    ):
        # init event loop
        # wait for all requests to end
        if self.event_loop is None:
            self.event_loop = QEventLoop()
        feedback.canceled.connect(self.event_loop.quit)

        for request in requests:
            url = request.url().url()
            self.info(f"fetching {url}")
            reply = self.nam.get(request)
            reply.finished.connect(
                lambda _url=url: self.handle_reply(_url, feedback, slot, data)
            )
            feedback.canceled.connect(reply.abort)
            self.network_replies[url] = reply

        # Let the requests end and catch all exceptions (and clean up requests)
        if len(self.network_replies) > 0:
            self.event_loop.exec(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)

        # After event loop exits (e.g. due to cancellation), clean up any
        # remaining replies to prevent callbacks on a deleted filter object
        for url, reply in list(self.network_replies.items()):
            reply.finished.disconnect()
            reply.abort()
            reply.deleteLater()
        self.network_replies.clear()

    def fetchResults(
        self, search: str, context: QgsLocatorContext, feedback: QgsFeedback
    ):
        try:
            if len(search) < self.minimum_search_length:
                return

            self.result_found = False

            self.perform_fetch_results(search, feedback)

            if not self.result_found:
                result = QgsLocatorResult()
                result.filter = self
                result.displayString = self.tr("No result found.", "NwOwLocatorFilter")
                result.userData = NoResult().as_definition()
                self.resultFetched.emit(result)

        except Exception as e:
            self.logException(e)

    def perform_fetch_results(self, search: str, feedback: QgsFeedback):
        raise NotImplementedError("This method should be reimplemented by the filter.")

    def triggerResult(self, result: QgsLocatorResult):
        # this should be run in the main thread, i.e. mapCanvas should not be None

        # Remove any map tip
        self.clearPreviousResults()

        search_result = result_from_data(result)

        if search_result is NoResult:
            return

        self.parse_filter_results(search_result)

    def parse_filter_results(self, search_result: QgsLocatorResult):
        raise NotImplementedError("This method should be reimplemented by the filter.")

    def show_map_tip(self, layer, feature_id, point):
        if layer and feature_id:
            url = f"{MAP_SERVER_URL}/{layer}/{feature_id}/htmlPopup"
            params = {"lang": self.lang, "sr": self.crs}
            url = url_with_param(url, params)
            self.dbg_info(url)
            request = QNetworkRequest(QUrl(url))
            self.fetch_request(
                request, QgsFeedback(), self.parse_map_tip_response, data=point
            )

    def parse_map_tip_response(self, content, feedback, point):
        self.map_tip = MapTip(self.iface, content, point.asPoint())
        self.map_tip.closed.connect(self.clearPreviousResults)

    def highlight(self, point, bbox=None):
        if bbox is None:
            bbox = point
        self.rubber_band.reset(QgsWkbTypes.GeometryType.PointGeometry)
        self.rubber_band.addGeometry(point, None)
        rect = bbox.boundingBox()
        rect.scale(1.1)
        self.map_canvas.setExtent(rect)
        self.map_canvas.refresh()

    def logException(self, e: Exception, level=Qgis.MessageLevel.Critical):
        # Log error message
        self.info(str(e), level)
        exc_type, exc_obj, exc_traceback = sys.exc_info()
        filename = os.path.split(exc_traceback.tb_frame.f_code.co_filename)[1]
        # Log filename and line numbers
        self.info(
            f"{exc_type} {filename} {exc_traceback.tb_lineno}",
            level,
        )
        # Log traceback
        self.info(
            "".join(traceback.format_exception(exc_type, exc_obj, exc_traceback)),
            level,
        )

    @staticmethod
    def info(msg="", level=Qgis.MessageLevel.Info):
        QgsMessageLog.logMessage(str(msg), __title__, level)

    def dbg_info(self, msg=""):
        if DEBUG:
            self.info(msg)

    @staticmethod
    def find_text(xmlElement, match):
        node = xmlElement.find(match)
        return node.text if node is not None else ""
