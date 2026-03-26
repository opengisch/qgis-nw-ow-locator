"""
Based on the SwissLocator plugin: https://github.com/opengisch/qgis-swiss-locator
"""

import os
import xml.etree.ElementTree as etree

from qgis.core import QgsLocator, QgsLocatorContext
from qgis.PyQt.QtTest import QSignalSpy
from qgis.testing import start_app, unittest
from qgis.testing.mocked import get_iface

from nw_ow_locator.core.filters.nw_ow_locator_filter_layer import (
    NwOwLocatorFilterWmsLayerOw,
)

start_app()


class TestNwOwLocatorFilterWmsLayer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.iface = get_iface()

    def setUp(self):
        pass

    def testParseFilterResults(self):
        def got_hit(result):
            print(result)
            print(result.displayString)
            got_hit._results_.append(result.displayString)

        got_hit._results_ = []

        capabilities_doc = os.path.join(
            os.path.dirname(__file__), "data", "capabilities_ow.xml"
        )
        capabilities = etree.parse(capabilities_doc).getroot()

        context = QgsLocatorContext()

        loc = QgsLocator()
        _filter = NwOwLocatorFilterWmsLayerOw(get_iface(), "2056", capabilities)
        loc.registerFilter(_filter)

        loc.foundResult.connect(got_hit)

        spy = QSignalSpy(loc.foundResult)

        loc.fetchResults("wald", context)

        spy.wait(1000)

        self.assertTrue(got_hit._results_[0].startswith("Waldreservate"))
        self.assertTrue(got_hit._results_[1].startswith("Waldabstandslinien"))
        self.assertTrue(got_hit._results_[2].startswith("Statische Waldgrenzen"))
