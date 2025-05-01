# Class to handle getting information from TrueNAS by using the
# websockets API.

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
This module adds support for websockets API on TrueNAS.
"""

import os
from urllib.parse import urljoin

import truenas_api_client.exc
from ansible.errors import AnsibleError
from truenas_api_client import Client


class WebsocketClient:
    _client = None

    @classmethod
    def initialize(cls):
        """Initialize the WebSocket client."""
        if cls._client is None:


            api_key = os.getenv('TRUENAS_API_KEY')
            api_username = os.getenv('TRUENAS_API_USERNAME')
            api_password = os.getenv('TRUENAS_API_PASSWORD')
            uri = os.getenv('TRUENAS_URI')

            if api_key or (api_username and api_password):
                try:
                    cls._client = Client(uri=urljoin(uri, '/api/current')
                    if api_key:
                        cls._client.call("auth.login_with_api_key", api_key)
                    else:
                        cls._client.call("auth.login", api_username, api_password)
                except truenas_api_client.exc.ClientException as e:
                    # Fallback to another URI if the primary fails
                    try:
                        cls._client = Client(uri=urljoin(uri, '/websocket')
                        if api_key:
                            cls._client.call("auth.login_with_api_key", api_key)
                        else:
                            cls._client.call("auth.login", api_username, api_password)
                    except truenas_api_client.exc.ClientException as fallback_e:
                        raise AnsibleError(f"Primary URI failed: {e}, fallback URI failed: {fallback_e}")

    @classmethod
    def close(cls):
        """Close the WebSocket client."""
        if cls._client:
            cls._client.close()
            cls._client = None

    @classmethod
    def call(cls, func, *args, output='json'):
        """Call the API function using the initialized client."""
        if cls._client is None:
            cls.initialize()
        return cls._client.call(func, *args)

    @classmethod
    def job(cls, func, *args, **kwargs):
        """Run a job using the initialized client."""
        if cls._client is None:
            raise AnsibleError("WebSocket client is not initialized.")
        return cls.call(func, *args, **kwargs)