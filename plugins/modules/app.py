#!/usr/bin/python
__metaclass__ = type

DOCUMENTATION = """
---
module: app
short_description: Manage TrueNAS SCALE apps
description:
  - Create, delete, update, start, stop and restart TrueNAS SCALE apps.
  - Supports all catalog apps, including community, enterprise and stable.
  - Supports check mode and idempotent operations.
  - Custom Apps are not supported yet
options:
  name:
    description:
      - A unique name for the app.
    type: str
    required: true
  template:
    description:
      - The catalog app template to use. You can find the names of the templates
       in the TrueNAS SCALE UI or in the repository: https://github.com/truenas/apps
    type: str
    required: true
  state:
    description:
      - The desired state of the app.
    type: str
    choices: [ absent, present, restarted, running, stopped ]
    default: present
  train:
    description:
      - The release train of the app template, can be found on the TrueNAS SCALE UI
        or in the repository: https://github.com/truenas/apps
    type: str
    choices: [ community, enterprise, stable ]
    default: stable
  remove_ix_volumes:
    description:
      - Whether to remove the associated ix volumes when the app is deleted.
    type: bool
    default: false
  values:
    description:
      - An arbitrary dictionary of configuration values for the app. The possible
        keys and values are dependent on the app template, check the repository
        https://github.com/truenas/apps for the proper values. Each App has a
        `questions.yaml` that defines the variable names and their types for
        each app.
    type: dict
    default: {}
  tags:
    description:
      - A list of tags to apply to the app.
    type: list
    elements: str
    default: []
"""

import time
from functools import partial

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.arensb.truenas.plugins.module_utils.middleware import (
    MiddleWare as MW,
)

EXAMPLES = """

"""

RETURN = """

"""


def main():
    """
    Main entry point for the TrueNAS app management Ansible module.

    Handles creation, deletion, updating, starting, stopping and restarting of TrueNAS apps.
    Supports check mode and idempotent operations.
    """
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type="str", required=True),
            template=dict(type="str", required=True),
            state=dict(
                type="str",
                choices=[
                    "absent",
                    "present",
                    "restarted",
                    "running",
                    "stopped",
                ],
                default="present",
            ),
            remove_ix_volumes=dict(type="bool", default=False),
            train=dict(
                type="str",
                choices=[
                    "community",
                    "enterprise",
                    "stable",
                ],
                default="stable",
            ),
            values=dict(type="dict", default={}),
        ),
    )

    desired_name = module.params["name"]
    desired_state = module.params["state"]

    mw = MW.client()

    # we create partials for our CRUD functions as to avoid the verbosity of
    # the client dependency injection.
    create_app = partial(_create_app, client=mw, name=desired_name)
    delete_app = partial(_delete_app, client=mw, name=desired_name)
    restart_app = partial(_restart_app, client=mw, name=desired_name)
    stop_app = partial(_stop_app, client=mw, name=desired_name)
    update_app = partial(_update_app, client=mw, name=desired_name)
    ensure_running = partial(_ensure_running, client=mw, name=desired_name)
    ensure_stopped = partial(_ensure_stopped, client=mw, name=desired_name)

    result = dict(
        changed=False,
        msg="",
    )

    app_data = mw.call("app.query", [["name", "=", desired_name]])

    if not app_data and desired_state != "absent":
        # app doesn't exist, but it should, so create it
        if module.check_mode:
            result["msg"] = f"Would have created app {desired_name}"

        else:
            changed, msg = create_app(
                template=module.params["template"],
                train=module.params["train"],
                values=module.params["values"],
            )
            result["changed"] = changed
            result["msg"] = msg
            ensure_running(client=mw, name=desired_name)
        module.exit_json(**result)

    if app_data and desired_state == "absent":
        # app exists, but it should be deleted
        if module.check_mode:
            result["msg"] = f"Would have deleted app {desired_name}"

        else:
            changed, msg = delete_app(
                remove_ix_volumes=module.params["remove_ix_volumes"],
            )
            result["changed"] = changed
            result["msg"] = msg
        module.exit_json(**result)

    if app_data and desired_state == "stopped":
        # app exists, and it should be stopped
        if module.check_mode:
            result["msg"] = f"Would have stopped app {desired_name}"

        else:
            if app_data[0]["state"] != "STOPPED":
                changed, msg = stop_app()
                ensure_stopped()
                result["changed"] = changed
                result["msg"] = msg

        module.exit_json(**result)

    if app_data and desired_state in ("running", "present", "restarted"):
        if module.check_mode:
            result["msg"] = f"Would have updated app {desired_name}"

        else:
            # if the app already exists, we need to check if the values have changed
            # and potentially updated it. We don't want to eagerly update the app
            # because TrueNAS will restart the app if 'app.update' is called, even
            # if the values haven't changed.
            current_values = mw.call("app.config", app_data[0]["name"])

            for key in module.params["values"]:
                for subkey in module.params["values"][key]:
                    current = current_values[key][subkey]
                    desired = module.params["values"][key][subkey]

                    if _detect_changes(current, desired):
                        changed, msg = update_app(values=module.params["values"])
                        result["changed"] = changed
                        result["msg"] = msg

            # for any of the positive states, a desired restart is may be requested
            if desired_state == "restarted":
                changed, msg = restart_app()
                result["changed"] = changed
                result["msg"] = msg

            ensure_running()

        module.exit_json(**result)

    raise Exception(f"App {desired_name} is in an unknown state")

    module.exit_json(**result)


def _create_app(client, name, template, train, values):
    """
    Create a new TrueNAS app.

    Args:
        client: TrueNAS middleware client instance
        name: Name of the app to create
        template: App template to use
        train: Train to use (community, enterprise, stable)
        values: Dictionary of configuration values for the app

    Returns:
        tuple: (bool, str) - Success status and result/error message
    """
    try:
        result = client.job(
            "app.create",
            {
                "app_name": name,
                "catalog_app": template,
                "train": train,
                "values": values,
            },
        )

        return True, str(result)

    except Exception:
        raise


def _delete_app(client, name, remove_ix_volumes=False):
    """
    Delete a TrueNAS app.

    Args:
        client: TrueNAS middleware client instance
        name: Name of the app to delete
        remove_ix_volumes: Whether to remove associated ix volumes

    Returns:
        tuple: (bool, str) - Success status and result/error message
    """
    try:
        result = client.job(
            "app.delete",
            name,
            {
                "remove_ix_volumes": remove_ix_volumes,
            },
        )

        return True, str(result)

    except Exception as e:
        return (
            False,
            str(e),
        )


def _restart_app(client, name):
    """
    Restart a TrueNAS app.

    Args:
        client: TrueNAS middleware client instance
        name: Name of the app to restart

    Returns:
        tuple: (bool, str) - Success status and result/error message
    """
    try:
        result = client.job("app.restart", name)
        return True, str(result)

    except Exception as e:
        return (
            False,
            str(e),
        )


def _update_app(client, name, values):
    """
    Update a TrueNAS app's configuration.

    Args:
        client: TrueNAS middleware client instance
        name: Name of the app to update
        values: New configuration values for the app

    Returns:
        tuple: (bool, str) - Success status and result/error message
    """
    try:
        result = client.job(
            "app.update",
            name,
            {
                "values": values,
            },
        )
        return True, str(result)

    except Exception as e:
        return (
            False,
            str(e),
        )


def _stop_app(client, name):
    """
    Stop a running TrueNAS app.

    Args:
        client: TrueNAS middleware client instance
        name: Name of the app to stop

    Returns:
        tuple: (bool, str) - Success status and result/error message
    """
    try:
        result = client.job("app.stop", name)
        return True, str(result)

    except Exception as e:
        return (
            False,
            str(e),
        )


def _ensure_running(client, name):
    """
    Ensure a TrueNAS app is in running state.

    Starts the app if it's not running and waits for it to be fully deployed.
    Raises an exception if the app fails to reach running state.

    Args:
        client: TrueNAS middleware client instance
        name: Name of the app to ensure is running

    Returns:
        tuple: (bool, str) - Success status and result message

    Raises:
        Exception: If the app fails to reach running state
    """
    result = client.call("app.query", [["name", "=", name]])

    if result[0]["state"] != "RUNNING":
        client.job("app.start", name)

    while True:
        result = client.call("app.query", [["name", "=", name]])

        if result[0]["state"] == "DEPLOYING":
            time.sleep(1)
        else:
            break

    if result[0]["state"] != "RUNNING":
        raise Exception(f"App {name} is not running: {result[0]['state']}")

    return True, "Success"


def _ensure_stopped(client, name):
    """
    Ensure a TrueNAS app is in stopped state.

    Waits for the app to fully stop if it's in stopping state.
    Raises an exception if the app fails to reach stopped state.

    Args:
        client: TrueNAS middleware client instance
        name: Name of the app to ensure is stopped

    Returns:
        bool: True if the app is stopped

    Raises:
        Exception: If the app fails to reach stopped state
    """
    result = client.call("app.query", [["name", "=", name]])

    while True:
        result = client.call("app.query", [["name", "=", name]])

        if result[0]["state"] == "STOPPING":
            time.sleep(1)
        else:
            break

    if result[0]["state"] == "STOPPED":
        return True

    raise Exception(f"App {name} is not stopped: {result[0]['state']}")


def _detect_changes(current_values, desired_values):
    """
    Compare two dictionaries and detect if merging desired_values into current_values
    would result in any changes. Only checks keys present in desired_values.

    Args:
        current_values: Current dictionary of values
        desired_values: Dictionary of desired values to check against current

    Returns:
        bool: True if applying desired_values would change current_values
    """
    # Handle non-dict values
    if not isinstance(desired_values, dict):
        return current_values != desired_values

    # Handle dict values
    if not isinstance(current_values, dict):
        return True  # Current is not a dict but desired is - this is a change

    # Recursively check each key in desired_values
    for key, desired_value in desired_values.items():
        if key not in current_values:
            return True  # New key in desired - this is a change

        if _detect_changes(current_values[key], desired_value):
            return True  # Recursive check found a change

    return False


if __name__ == "__main__":
    main()
