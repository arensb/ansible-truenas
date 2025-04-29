# Class to interface with the middleware daemon through the
# middlewared.client Python class, rather than by executing 'midclt'.

__metaclass__ = type
"""
This module interfaces with middlewared on TrueNAS, and tries to do so
natively.
"""

import middlewared.client as client
from middlewared.utils.service.call import MethodNotFoundError
from ansible_collections.arensb.truenas.plugins.module_utils.exceptions \
    import MethodNotFoundError as AnsibleMethodNotFoundError


class MiddlewareClient:
    client = None

    @staticmethod
    def _client():
        """
        Singleton. Return a middleware client handle, creating one if
        necessary.
        """
        if MiddlewareClient.client is None:
            MiddlewareClient.client = client.Client()
        return MiddlewareClient.client

    @staticmethod
    def call(func, *args, output=None):
        """Call the API function 'func' with arguments 'args'.

        'output' is just for compatibility, and is ignored.

        Returns the returned value.
        """
        client = MiddlewareClient._client()
        try:
            retval = client.call(func, *args)
        except MethodNotFoundError as e:
            # Note that we're catching
            # middlewared.utils.service.call.MethodNotFoundError and
            # replacing it with a different Exception, because the
            # caller doesn't know whether it has access to the
            # original exception, so it can't import it.
            raise AnsibleMethodNotFoundError(func, str(e))
        except Exception as e:
            raise e

        return retval

    @staticmethod
    def job(func, *args):
        """Run the API function 'func', with arguments 'args'.

        Jobs are different from calls in that jobs are asynchronous,
        since they may run for a long time.

        This method starts a job, then waits for it to complete. If it
        finishes successfully, 'job' returns the job's status.
        """

        client = MiddlewareClient._client()
        err = client.call(func,
                          *args,
                          job=True)
        return err
