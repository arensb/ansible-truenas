# The TrueNAS middleware can be controlled in different ways: through
# the 'midclt' command-line tool, through a REST API, maybe others.
# The REST API is the recommended one.
#
# Since all of these methods provide the same functions, take the same
# arguments, and return the same results, we want users to be able to
# choose the one that works best for them. This module is a layer that
# sits between individual modules and the middleware, and uses
# whichever access method is chosen.

from ansible_collections.ooblick.truenas.plugins.module_utils.midclt \
    import Midclt


class MiddleWare:
    # XXX - What do we want the API to be? How does the caller choose
    # an access method?
    #
    # Create a MiddleWare object with a given access method, and then
    # use that?

    def __init__(self, access='midclt', *args):
        pass

    def call(self, func, *args):
        return Midclt.call(func, *args)
