"""
Unit tests for result serialization round-trips and the registry pattern.

These tests verify that every result type can be serialized via
as_definition() and deserialized back via result_from_data() without
data loss.  They do NOT require network access.
"""

import json

from qgis.core import QgsPointXY, QgsRectangle
from qgis.testing import start_app, unittest

from nw_ow_locator.core.results import (
    RESULT_REGISTRY,
    LocationResult,
    NoResult,
    ResultBase,
    WMSLayerResult,
    result_from_data,
)

start_app()


class TestResultRegistry(unittest.TestCase):
    """Verify the auto-registry populated by ResultBase.__init_subclass__."""

    def test_all_types_registered(self):
        expected = {
            "WMSLayerResult",
            "LocationResult",
            "NoResult",
        }
        self.assertEqual(set(RESULT_REGISTRY.keys()), expected)

    def test_registry_maps_to_correct_classes(self):
        self.assertIs(RESULT_REGISTRY["WMSLayerResult"], WMSLayerResult)
        self.assertIs(RESULT_REGISTRY["LocationResult"], LocationResult)
        self.assertIs(RESULT_REGISTRY["NoResult"], NoResult)

    def test_all_registered_classes_inherit_from_base(self):
        for cls in RESULT_REGISTRY.values():
            self.assertTrue(
                issubclass(cls, ResultBase),
                f"{cls.__name__} should inherit from ResultBase",
            )


class TestResultFromData(unittest.TestCase):
    """Test the top-level result_from_data dispatcher."""

    def test_unknown_type_returns_no_result(self):
        definition = json.dumps({"type": "UnknownType"})
        result = result_from_data(definition)
        self.assertIsInstance(result, NoResult)

    def test_missing_type_returns_no_result(self):
        definition = json.dumps({"foo": "bar"})
        result = result_from_data(definition)
        self.assertIsInstance(result, NoResult)


class TestWMSLayerResultRoundTrip(unittest.TestCase):
    """Serialize → deserialize WMSLayerResult and check all fields."""

    def test_full_round_trip(self):
        original = WMSLayerResult(
            layer="ch.swisstopo.pixelkarte-farbe",
            title="Pixelkarte",
            url="https://wms.geo.admin.ch/?VERSION=2.0.0",
            tile_matrix_set="EPSG:2056",
            _format="image/jpeg",
            style="default",
            tile_dimensions="Time=current",
        )
        definition = original.as_definition()
        restored = result_from_data(definition)

        self.assertIsInstance(restored, WMSLayerResult)
        self.assertEqual(restored.layer, original.layer)
        self.assertEqual(restored.title, original.title)
        self.assertEqual(restored.url, original.url)
        self.assertEqual(restored.tile_matrix_set, original.tile_matrix_set)
        self.assertEqual(restored.format, original.format)
        self.assertEqual(restored.style, original.style)
        self.assertEqual(restored.tile_dimensions, original.tile_dimensions)

    def test_minimal_round_trip(self):
        """Optional fields left as None should survive the round-trip."""
        original = WMSLayerResult(
            layer="ch.test",
            title="Test",
            url="https://example.com",
        )
        definition = original.as_definition()
        restored = result_from_data(definition)

        self.assertIsInstance(restored, WMSLayerResult)
        self.assertIsNone(restored.tile_matrix_set)
        self.assertIsNone(restored.style)
        self.assertIsNone(restored.tile_dimensions)

    def test_definition_contains_type_key(self):
        wms = WMSLayerResult("layer", "title", "url")
        data = json.loads(wms.as_definition())
        self.assertEqual(data["type"], "WMSLayerResult")


class TestLocationResultRoundTrip(unittest.TestCase):
    def test_round_trip(self):
        point = QgsPointXY(2600000, 1200000)
        bbox = QgsRectangle(2599000, 1199000, 2601000, 1201000)
        original = LocationResult(
            point=point,
            bbox=bbox,
            layer="ch.swisstopo.swissboundaries3d-gemeinde-flaeche.fill",
            feature_id="123",
            html_label="<b>Bern</b>",
        )
        definition = original.as_definition()
        restored = result_from_data(definition)

        self.assertIsInstance(restored, LocationResult)
        self.assertAlmostEqual(restored.point.x(), point.x(), places=1)
        self.assertAlmostEqual(restored.point.y(), point.y(), places=1)
        self.assertAlmostEqual(restored.bbox.xMinimum(), bbox.xMinimum(), places=1)
        self.assertAlmostEqual(restored.bbox.yMaximum(), bbox.yMaximum(), places=1)
        self.assertEqual(restored.layer, original.layer)
        self.assertEqual(restored.feature_id, original.feature_id)
        self.assertEqual(restored.html_label, original.html_label)

    def test_none_feature_id(self):
        original = LocationResult(
            point=QgsPointXY(8.0, 47.0),
            bbox=QgsRectangle(7.0, 46.0, 9.0, 48.0),
            layer="ch.test",
            feature_id=None,
            html_label="label",
        )
        definition = original.as_definition()
        restored = result_from_data(definition)
        self.assertIsNone(restored.feature_id)


class TestNoResult(unittest.TestCase):
    def test_round_trip(self):
        definition = NoResult.as_definition()
        restored = result_from_data(definition)
        self.assertIsInstance(restored, NoResult)

    def test_definition_contains_type(self):
        data = json.loads(NoResult.as_definition())
        self.assertEqual(data["type"], "NoResult")


if __name__ == "__main__":
    unittest.main()
