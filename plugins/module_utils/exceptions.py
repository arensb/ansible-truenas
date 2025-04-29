# Exceptions for talking to TrueNAS Middleware daemon.

class MethodNotFoundError(Exception):
    """This exception roughly corresponds to
    middlewared.utils.service.call.MethodNotFoundError: the caller has
    invoked a nonexistent middlewared method. But since we don't
    always have access to that class, we define our own exception to
    signify the same thing.
    """

    def __init__(self, method, errmsg=""):
        self.method = method
        self.errmsg = errmsg

    def __str__(self):
        return f"Method {self.method} Not Found. Error: {self.errmsg}"
