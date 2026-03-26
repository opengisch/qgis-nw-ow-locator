#! python3  # noqa: E265
"""
Based on the SwissLocator plugin: https://github.com/opengisch/qgis-swiss-locator
"""

from qgis.core import NULL
from qgis.PyQt.QtCore import QLocale, QSettings

from .parameters import AVAILABLE_LANGUAGES
from .settings import Settings


def get_language() -> str:
    """
    Returns the language to be used.
    Reads from the settings, if it's None, try to use the locale one and defaults to English
    :return: 2 chars long string representing the language to be used
    """
    # get lang from settings
    lang = Settings().lang.value()
    if not lang:
        locale = str(QSettings().value("locale/userLocale")).replace(str(NULL), "en_CH")
        locale_lang = QLocale.languageToString(QLocale(locale).language())
        if locale_lang in AVAILABLE_LANGUAGES.keys():
            lang = AVAILABLE_LANGUAGES[locale_lang]
    if lang not in AVAILABLE_LANGUAGES.values():
        lang = "en"

    return lang
