# Common utility functions.
# Code that it'd be nice to have in Ansible's 'setup' module.

from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW
# For parsing version numbers
from packaging import version

# Version of TrueNAS we're running, so that we know how to invoke
# middlewared.
tn_version = None


# XXX - It would be nice to extend the 'setup' module to gather this
# information, set some facts, and then any module that needs them can
# refer to those facts.
def get_tn_version():
    """Get the version of TrueNAS being run"""

    # Return memoized data if we've already looked it up.
    global tn_version
    if tn_version is not None:
        return tn_version

    mw = MW.client()

    try:
        # product_name is a string like "TrueNAS".
        # product_type is a string like "CORE".
        # product_version is a string like "TrueNAS-13.0-U5", or "TrueNAS-SCALE-22.12.3.1"
        product_name = mw.call("system.product_name", output='str')
        product_type = mw.call("system.product_type", output='str')
        sys_version = mw.call("system.version", output='str')
    except Exception:
        raise

    # Strip "TrueNAS-" from the beginning of the version string,
    # leaving just the version number.
    if sys_version.startswith(f"{product_name}-"):
        sys_version = sys_version[len(product_name)+1:]

    # Strip "SCALE-" from the beginning of the version string if it exists.
    if sys_version.startswith(f"{product_type}-"):
        sys_version = sys_version[len(product_type)+1:]

    sys_version = version.parse(sys_version)

    tn_version = {
        "name": product_name,
        "type": product_type,
        "version": sys_version,
    }

    return tn_version
