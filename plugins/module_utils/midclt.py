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

__metaclass__ = type
"""
This module adds support for midclt on TrueNAS.
"""

import subprocess
import json
from json.decoder import JSONDecodeError

MIDCLT_CMD = "midclt"


class MidcltError(Exception):
    def __init__(self, value, progress=None, error=None, exception=None):
        self.value = value
        # progress: an object with job progress info:
        # {
        #     percent: int, percent completion
        #     description: str, running log of stdout (?)
        #     extra: ?, can be null.
        # }
        self.progress = progress
        # error: str, job stderr error message
        self.error = error
        # exception: str, failed job stack trace
        self.exception = exception

    def __str__(self):
        return f'{self.error}: {repr(self.value)}'


class Midclt:

    # See whether 'midclt' exists, so we can abort early on if the
    # rest isn't going to work.
    try:
        import shutil
        if shutil.which(MIDCLT_CMD) is None:
            raise FileNotFoundError(f"Can't find command {MIDCLT_CMD}.")
    except ModuleNotFoundError:
        raise

    @staticmethod
    def _to_json(msg):
        """Given a string printed by 'midclt', convert it to JSON."""

        # Convert from bytes to string, if necessary.
        if isinstance(msg, bytes):
            msg = str(msg, 'utf-8')

        # Trim whitespace if necessary.
        msg = msg.strip()

        # Special case: some jobs print "True" or "False", which
        # is not valid JSON.
        # jail.stop() can print "null", but that's valid JSON.
        if msg in ("True", "False"):
            # Convert to lower case, which is legal JSON.
            msg = msg.lower()

        return json.loads(msg)

    @staticmethod
    def call(func, *args, opts=[], output='json'):
        """Call the API function 'func', with arguments 'args'.

        'opts' are additional options passed to 'midclt call', not to
        'func'.

        'output' specifies the expected format of the output from 'midclt':
        most commands output JSON, but some print strings. Allowed
        values are: "json", "str".

        Return the status and return value.
        """

        # Build the command line
        mid_args = [MIDCLT_CMD, "call", *opts, func]

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

        if output == "str":
            # I assume everyone's using UTF-8 by now.
            retval = str(mid_out, 'utf-8').rstrip()
        elif output == "json":
            # Parse stdout as JSON
            try:
                retval = Midclt._to_json(mid_out)
            except JSONDecodeError as e:
                raise Exception(f"Can't parse {MIDCLT_CMD} output: {mid_out}: {e}")
        else:
            raise Exception(f"Invalid output format {output}")

        return retval

    @staticmethod
    def job(func, *args, **kwargs):
        """Run the API function 'func', with arguments 'args'.

        Jobs are different from calls in that jobs are asynchronous,
        since they may run for a long time.

        This method starts a job, then waits for it to complete. If it
        finishes successfully, 'job' returns the job's status.
        """

        try:
            err = Midclt.call(func,
                              opts=["-job", "-jp", "description"],
                              output='str',
                              *args, **kwargs)

            # We've asked for 'str' output, so 'err' should be a bunch of
            # lines: first a bunch of progress messages, and then a
            # JSON string on the last line.
            lines = err.rstrip().split("\n")

            # Get the last line, which is hopefully JSON.
            ret_str = lines.pop()
            retval = Midclt._to_json(ret_str)

        except Exception:
            # Any number of things might have gone wrong:
            # - Wrong options to the middleware call
            # - err isn't a string
            # - err is the empty string (and pop() fails)
            # - The last line isn't proper JSON.
            raise

        return retval
