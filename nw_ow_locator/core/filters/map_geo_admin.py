from nw_ow_locator.core.constants import SEARCH_URL


def map_geo_admin_url(
    search: str,
    _type: str,
    crs: str,
    lang: str,
    limit: int,
    bbox: str | None = None,
):
    base_params = {
        "type": _type,
        "searchText": str(search),
        "returnGeometry": "true",
        "lang": lang,
        "sr": crs,
        # "true" will sort features by distance to the bbox center, which can lead to
        # unexpected address results: Addresses that are less similar to the search term
        # will be returned first. However, this is still producing more and better
        # results than setting it to "false". For example, it retrieves parcels for
        # search term "123", with "true", it wouldn't.
        # It's important to reorder results after receiving the response.
        "sortbbox": "true",
    }
    if bbox:
        base_params["bbox"] = bbox
    return SEARCH_URL, base_params
