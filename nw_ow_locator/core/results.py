#! python3  # noqa: E265
"""
Based on the SwissLocator plugin: https://github.com/opengisch/qgis-swiss-locator
"""

import json

from qgis.core import QgsGeometry, QgsRectangle


class LocationResult:
    def __init__(self, point, bbox, layer, feature_id, html_label):
        self.point = point
        self.bbox = bbox
        self.layer = layer
        self.feature_id = feature_id
        self.html_label = html_label

    @staticmethod
    def from_dict(dict_data: dict):
        return LocationResult(
            QgsGeometry.fromWkt(dict_data["point"]).asPoint(),
            QgsRectangle.fromWkt(dict_data["bbox"]),
            dict_data["layer"],
            dict_data["feature_id"],
            dict_data["html_label"],
        )

    def as_definition(self):
        definition = {
            "type": "LocationResult",
            "point": self.point.asWkt(),
            "bbox": self.bbox.asWktPolygon(),
            "layer": self.layer,
            "feature_id": self.feature_id,
            "html_label": self.html_label,
        }
        return json.dumps(definition)


class WMSLayerResult:
    def __init__(
        self,
        layer,
        title,
        url,
        tile_matrix_set: str = None,
        _format: str = "image/png",
        style: str = None,
        tile_dimensions: str = None,
    ):
        self.title = title
        self.layer = layer
        self.url = url
        self.tile_matrix_set = tile_matrix_set
        self.format = _format
        self.style = style
        self.tile_dimensions = tile_dimensions

    @staticmethod
    def from_dict(dict_data: dict):
        return WMSLayerResult(
            dict_data["layer"],
            dict_data["title"],
            dict_data["url"],
            tile_matrix_set=dict_data.get("tile_matrix_set"),
            _format=dict_data.get("format"),
            style=dict_data.get("style"),
            tile_dimensions=dict_data.get("tile_dimensions"),
        )

    def as_definition(self):
        definition = {
            "type": "WMSLayerResult",
            "title": self.title,
            "layer": self.layer,
            "url": self.url,
            "tile_matrix_set": self.tile_matrix_set,
            "format": self.format,
            "style": self.style,
            "tile_dimensions": self.tile_dimensions,
        }
        return json.dumps(definition)


class NoResult:
    def __init__(self):
        pass

    @staticmethod
    def as_definition():
        definition = {"type": "NoResult"}
        return json.dumps(definition)
