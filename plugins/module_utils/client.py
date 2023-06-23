# Class to interface with the middleware daemon through the
# middlewared.client Python class, rather than by executing 'midclt'.

__metaclass__ = type
"""
This module interfaces with middlewared on TrueNAS, and tries to do so
natively.
"""

import middlewared.client as client


class MiddlewareClient:
    client = None

    @staticmethod
    def _client():
        if MiddlewareClient.client is None:
            MiddlewareClient.client = client.Client()
        return MiddlewareClient.client

    @staticmethod
    def call(func, *args, opts=None, output=None):
        """Call the API function 'func' with arguments 'args'.

        'opts' and 'output' are just for compatibility, and are ignored.

        Returns the returned value.
        """
        client = MiddlewareClient._client()
        retval = client.call(func, args)
        return retval
