DEBUG = False


def classFactory(iface):
    """Load the plugin class.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .nw_ow_locator_plugin import NwOwLocatorPlugin

    return NwOwLocatorPlugin(iface)
