from enum import Enum


class FilterType(Enum):
    Location = "locations"  # provides map.geo.admin.ch locations search
    Layers = "layers"  # provides layer search from the cantonal WMS
