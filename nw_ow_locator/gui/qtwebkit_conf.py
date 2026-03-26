#! python3  # noqa: E26
"""
Based on the SwissLocator plugin: https://github.com/opengisch/qgis-swiss-locator
"""

_WITH_QTWEBKIT = None


def with_qt_web_kit() -> bool:
    global _WITH_QTWEBKIT
    if _WITH_QTWEBKIT is None:
        try:
            from qgis.PyQt.QtWebKit import QWebSettings
            from qgis.PyQt.QtWebKitWidgets import QWebPage, QWebView
        except ModuleNotFoundError:
            _WITH_QTWEBKIT = False
        else:
            _WITH_QTWEBKIT = True

    return _WITH_QTWEBKIT
