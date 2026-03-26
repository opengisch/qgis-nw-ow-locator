# Centralised API base URLs for geo.admin.ch services.
# Keeping them in one place makes it easy to find and update endpoints.

API_BASE_URL = "https://api3.geo.admin.ch"

SEARCH_URL = f"{API_BASE_URL}/rest/services/ech/SearchServer"
MAP_SERVER_URL = f"{API_BASE_URL}/rest/services/ech/MapServer"


MAP_GEO_ADMIN_URL = "https://map.geo.admin.ch"

NW_OW_WMS_URL = "https://www.gis-daten.ch/wms"

USER_AGENT = b"Mozilla/5.0 QGIS Swiss Geoportal Locator Filter"
