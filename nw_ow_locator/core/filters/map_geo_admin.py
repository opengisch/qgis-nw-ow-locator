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
        # "true" will sort features by distance to the bbox center, which leads to unexpected results.
        "sortbbox": "false",
    }
    if bbox:
        base_params["bbox"] = bbox
    return SEARCH_URL, base_params
