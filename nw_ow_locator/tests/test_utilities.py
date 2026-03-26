"""
Unit tests for base filter utilities, URL builders, html_stripper,
and constants module.

These tests do NOT require network access or the full QGIS locator pipeline.
"""

from qgis.core import QgsRectangle
from qgis.testing import start_app, unittest

from nw_ow_locator.core.constants import (
    API_BASE_URL,
    MAP_GEO_ADMIN_URL,
    MAP_SERVER_URL,
    SEARCH_URL,
    USER_AGENT,
)
from nw_ow_locator.core.filters.map_geo_admin import map_geo_admin_url
from nw_ow_locator.core.filters.nw_ow_locator_filter import (
    InvalidBox,
    NwOwLocatorFilter,
)
from nw_ow_locator.utils.html_stripper import strip_tags

start_app()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants(unittest.TestCase):
    """Verify that constants are well-formed URLs."""

    def test_api_base_url(self):
        self.assertTrue(API_BASE_URL.startswith("https://"))

    def test_search_url_derives_from_base(self):
        self.assertTrue(SEARCH_URL.startswith(API_BASE_URL))

    def test_map_server_url_derives_from_base(self):
        self.assertTrue(MAP_SERVER_URL.startswith(API_BASE_URL))

    def test_all_urls_are_strings(self):
        for url in (
            SEARCH_URL,
            MAP_SERVER_URL,
            MAP_GEO_ADMIN_URL,
        ):
            self.assertIsInstance(url, str)

    def test_user_agent_is_bytes(self):
        self.assertIsInstance(USER_AGENT, bytes)


# ---------------------------------------------------------------------------
# box2geometry
# ---------------------------------------------------------------------------


class TestBox2Geometry(unittest.TestCase):
    """Test SwissLocatorFilter.box2geometry static method."""

    def test_valid_box(self):
        rect = NwOwLocatorFilter.box2geometry("BOX(2599000 1199000,2601000 1201000)")
        self.assertIsInstance(rect, QgsRectangle)
        self.assertAlmostEqual(rect.xMinimum(), 2599000.0)
        self.assertAlmostEqual(rect.yMinimum(), 1199000.0)
        self.assertAlmostEqual(rect.xMaximum(), 2601000.0)
        self.assertAlmostEqual(rect.yMaximum(), 1201000.0)

    def test_valid_box_with_decimals(self):
        rect = NwOwLocatorFilter.box2geometry("BOX(7.123 46.456,8.789 47.012)")
        self.assertAlmostEqual(rect.xMinimum(), 7.123, places=3)
        self.assertAlmostEqual(rect.yMaximum(), 47.012, places=3)

    def test_invalid_box_raises(self):
        with self.assertRaises(InvalidBox):
            NwOwLocatorFilter.box2geometry("not a box")

    def test_incomplete_box_raises(self):
        with self.assertRaises(InvalidBox):
            NwOwLocatorFilter.box2geometry("BOX(100 200)")


# ---------------------------------------------------------------------------
# URL builders
# ---------------------------------------------------------------------------


class TestMapGeoAdminUrl(unittest.TestCase):
    def test_returns_search_url(self):
        url, params = map_geo_admin_url("bern", "locations", "2056", "de", 10)
        self.assertEqual(url, SEARCH_URL)

    def test_params_contain_search_text(self):
        url, params = map_geo_admin_url("zürich", "locations", "2056", "de", 5)
        self.assertEqual(params["searchText"], "zürich")
        self.assertEqual(params["type"], "locations")
        self.assertEqual(params["lang"], "de")
        self.assertEqual(params["sr"], "2056")
        self.assertEqual(params["limit"], "5")

    def test_params_return_geometry(self):
        _, params = map_geo_admin_url("test", "layers", "21781", "fr", 20)
        self.assertEqual(params["returnGeometry"], "true")


# ---------------------------------------------------------------------------
# html_stripper
# ---------------------------------------------------------------------------


class TestHtmlStripper(unittest.TestCase):
    def test_strips_bold(self):
        self.assertEqual(strip_tags("<b>Bern</b>"), "Bern")

    def test_strips_nested_tags(self):
        self.assertEqual(
            strip_tags("<div><span>Hello</span> <b>World</b></div>"),
            "Hello World",
        )

    def test_plain_text_unchanged(self):
        self.assertEqual(strip_tags("plain text"), "plain text")

    def test_empty_string(self):
        self.assertEqual(strip_tags(""), "")

    def test_entities_preserved(self):
        # HTML entities should be fed through as-is by the parser
        result = strip_tags("<b>A &amp; B</b>")
        self.assertIn("A", result)
        self.assertIn("B", result)


if __name__ == "__main__":
    unittest.main()
