#!/usr/bin/python
__metaclass__ = type

# Create and manage TrueNAS middleware API keys.

# XXX - How to bootstrap an Ansible installation? This is probably
# best done in two playbooks, if at all.
#
# It might be tempting to write a playbook to be run by an admin, that
# runs around all of the TrueNAS boxen, creates API keys, and saves
# them in a vault, for day to day playbooks to use. But that only
# makes sense if you're setting up a bunch of boxen, or if they're
# cattle that you want to automate all the way.
#
# In practice, you'll probably create an API key once, by hand, and
# save that to an Ansible vault file.
#
# Though maybe you have a setup where multiple admins or scripts have
# access to the TrueNAS host, each with their own API key, and you
# want to maintain them automatically.

# XXX
DOCUMENTATION = '''
---
module: api_key
short_description: Manage middleware API keys.
description:
  - TrueNAS devices are configured not by managing files, as is traditional
    in Unix, but by issuing commands to the middleware daemon. This can
    be done by logging in to the TrueNAS device and issuing shell
    commands, but the recommended way is to connect over HTTP and issue
    REST API commands. This requires an API key.
  - This module allows creating, deleting, and updating API keys.
  - API key management is done by issuing middleware commands, so
    generating an API key runs into an obvious chicken-and-egg problem.
    To generate the first API key, it is necessary to log in to the
    TrueNAS device, either its HTTP console, or via ssh.
options:
  name:
    description:
      - Name of the key.
    type: str
    required: true
  state:
    description:
      - Whether the key should exist or not.
      - If C(present), the key will be created if it does not already exist.
        This is the only time the key will be shown.
      - If C(absent), the key will be deleted if it exists.
      - If C(reset), the key will be reset, i.e., regenerated. This is
        the only time the new key will be shown.
        If the key does not exist, this will fail with an error.
    type: str
    choices: [ absent, present, reset ]
    default: present
version_added: 1.14.0
'''

# XXX
# XXX - Show an example of bootstrapping to get the initial key.
EXAMPLES = '''
- name: Delete a key
  api_key:
    name: "my old key"
    state: absent
'''

RETURN = '''
- name: api_key
  description:
    - Structure describing a newly-created API key.
    - This is returned when a new key is created,
      or an existing one is reset.
  type: dict
  sample:
    id: 107
    name: "My new key"
    created_at: "2025-09-09T01:27:16.750000+00:00"
    key: "107-jUBFIpge2..."
'''

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.middleware import MiddleWare as MW


def main():
    module = AnsibleModule(
        argument_spec=dict(
            # XXX
            name=dict(type='str'),
            state=dict(type='str', default='present',
                       choices=['absent', 'present', 'reset']),
            ),
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW.client()

    # Assign variables from properties, for convenience
    name = module.params['name']
    state = module.params['state']

    # Look up the API key
    try:
        apikey_info = mw.call("api_key.query",
                                [["name", "=", name]])
        if len(apikey_info) == 0:
            # No such key
            apikey_info = None
        else:
            # Key exists
            apikey_info = apikey_info[0]
    except Exception as e:
        module.fail_json(msg=f"Error looking up API key {name}: {e}")

    # First, check whether the key even exists.
    if apikey_info is None:
        # Key doesn't exist

        if state == 'present':
            # Key is supposed to exist, so create it.

            # Collect arguments to pass to api_key.create()
            arg = {
                "name": name,
            }

            # if feature is not None:
            #     arg['feature'] = feature

            if module.check_mode:
                result['msg'] = f"Would have created API key {name} with {arg}"
            else:
                #
                # Create new API key
                #
                try:
                    err = mw.call("api_key.create", arg)
                    result['api_key'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating API key {name}: {e}")

                # Return whichever interesting bits api_key.create()
                # returned.
                result['api_key'] = err

            result['changed'] = True

        elif state == 'reset':
            # Can't reset a nonexistent key.
            module.fail_json(msg=f"Attempting to reset nonexistent key {name}")

        else:
            # Key is not supposed to exist.
            # All is well
            result['changed'] = False

    else:
        # Key exists
        if state == 'present':
            # Key is supposed to exist

            # We don't support renaming keys, so there's really
            # nothing you can do to change this key. So we're done
            # here.
            result['changed'] = False

        elif state == 'reset':
            # Reset the key and return the new value.
            arg = {
                "reset": True,
            }

            try:
                err = mw.call("api_key.update", apikey_info['id'], arg)
                # Return the new key
                result['api_key'] = err
            except Exception as e:
                module.fail_json(msg=f"Error resetting API key {name}: {e}")

        else:
            # Key is not supposed to exist

            if module.check_mode:
                result['msg'] = f"Would have deleted API key {name}"
            else:
                try:
                    #
                    # Delete key.
                    #
                    err = mw.call("api_key.delete",
                                  apikey_info['id'])
                except Exception as e:
                    module.fail_json(msg=f"Error deleting API key {name}: {e}")
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
