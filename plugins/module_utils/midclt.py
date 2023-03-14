# Class to handle getting information from TrueNAS by running 'midclt'
# on the host.

# midclt call apparently calls an API function.

# Filters aren't intuitive: A filter is a list of >= 0 elements, where
# each element is in turn an array. So to query the users with UID
# 1000, use
#
# midclt call user.query '[["id", "=", 1000]]'
#
# Example:
# midclt call user.query '[["username", "=", "root" ]]'
# midclt call plugin.defaults '{"plugin":"syncthing"}'

# XXX - There are multiple ways of controlling the middleware daemon:
# midclt is the command-lineversion, but I think the recommended way
# is to use the REST API.

# It'd be

__metaclass__ = type
"""
This module adds support for midclt on TrueNAS.
"""

import subprocess
import json
from json.decoder import JSONDecodeError

MIDCLT_CMD = "midclt"


class Midclt:
    # XXX - Maybe other commands beside "call"?:
    # ping, waitready, sql, subscribe.

    @staticmethod
    def call(func, *args):
        """Call the API function 'func', with arguments 'args'.

        Return the status and return value.
        """

        # Build the command line
        mid_args = [MIDCLT_CMD, "call", func]

        # If we were passed arguments, convert them to JSON strings,
        # and add to the command line.
        if len(args) > 0:
            for arg in args:
                argstr = json.dumps(arg)
                mid_args.append(argstr)

        # Run 'midclt' and get its output.
        try:
            mid_out = subprocess.check_output(mid_args,
                                              stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            # Exited with a non-zero code
            raise Exception(f"{MIDCLT_CMD} exited with status {e.returncode}: \"{e.stdout}\"")

        # Parse stdout as JSON
        try:
            retval = json.loads(mid_out)
        except JSONDecodeError as e:
            raise Exception(f"Can't parse {MIDCLT_CMD} output: {mid_out}: {e}")

        return retval
