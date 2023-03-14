#!/usr/bin/python
__metaclass__ = type

# Set the hostname.

# XXX - network.configuration.update
# - hostname
# - domain

# XXX
DOCUMENTATION='''
module: hostname
description:
  - Set the hostname.
  - Does not set the FQDN.
options:
  name:
    description:
    type: str
    required: yes
'''

EXAMPLES = '''
- name: Set hostname
  ooblick.truenas.hostname:
    name: my-little-host
'''

# XXX
# RETURN = '''
# '''

from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible_collections.ooblick.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW

# XXX - network.configuration.update includes three hostnames:
# hostname, hostname_b, hostname_virtual. From
# https://www.truenas.com/docs/core/uireference/network/globalconfigscreen/
# it sounds as though "hostname" is the current host, "hostname_b" is
# its partner in a HA setup, and I don't know what "hostname_virtual" is for.

def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str'),
            ),
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW()

    # Assign variables from properties, for convenience
    name = module.params['name']

    # Look up the current network config.
    try:
        network_config = mw.call("network.configuration.config")
    except Exception as e:
        module.fail_json(msg=f"Error looking up network configuration: {e}")

    # See whether anything has changed.
    if network_config['hostname'] != name:
        #
        # Update hostname
        #
        if module.check_mode:
            result['msg'] = f"Would have updated hostname to {name}."
        else:
            try:
                err = mw.call("network.configuration.update",
                              { "hostname": name })
            except Exception as e:
                module.fail_json(msg=f"Error updating hostname with {arg}: {e}")
            result['status'] = err
        result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
