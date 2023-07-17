#!/usr/bin/python
__metaclass__ = type

# Manage the system dataset. Set which pool to put it on.

# XXX
DOCUMENTATION = '''
---
module: systemdataset
short_description: Manage the system dataset.
description:
  - Manage the system dataset, including migrating it from one
    pool to another.
options:
  pool:
    description:
      - Name of the pool that should hold the system dataset.
    type: str
  syslog:
    description:
      - Whether to store system logs on the system dataset.
      - If unset, logs will be stored in C(/var).
    type: bool
version_added: 0.5.0
'''

EXAMPLES = '''
- name: Migrate system dataset to ZFS pool mypool2
  arensb.truenas.systemdataset:
    pool: mypool2

- name: Don't store system logs on the system dataset.
  arensb.truenas.systemdataset:
    syslog: no
'''

RETURN = '''
status:
  description:
    - An object describing the new state of the system dataset.
    - This is in the same format as the value returned by systemdataset.config
  type: dict
  sample: |
    {
      "id": 1,
      "pool": "mypool2",
      "uuid": "abcdef123456",
      "uuid_a": "abcdef123456",
      "uuid_b": null,
      "is_decrypted": true,
      "basename": "mypool2/.system",
      "syslog": true
      "path": "/var/db/system",
    }
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW


def main():
    module = AnsibleModule(
        argument_spec=dict(
            pool=dict(type='str'),
            syslog=dict(type='bool'),
            ),
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW.client()

    # Assign variables from properties, for convenience
    pool = module.params['pool']
    syslog = module.params['syslog']

    # Look up the current state of the system dataset.
    try:
        sysdataset_info = mw.call("systemdataset.config")
    except Exception as e:
        module.fail_json(msg=f"Error getting system dataset configuration: {e}")

    # Make list of differences between what is and what should
    # be.
    arg = {}

    if pool is not None and sysdataset_info['pool'] != pool:
        arg['pool'] = pool

    if syslog is not None and sysdataset_info['syslog'] != syslog:
        arg['syslog'] = syslog

    # If there are any changes, resource.update()
    if len(arg) == 0:
        # No changes
        result['changed'] = False
    else:
        #
        # Update the system dataset.
        #
        if module.check_mode:
            result['msg'] = f"Would have updated system dataset: {arg}"
            result['status'] = sysdataset_info
        else:
            try:
                err = mw.job("systemdataset.update",
                             arg)
            except Exception as e:
                module.fail_json(msg=f"Error updating system dataset with {arg}: {e}")
            # Return any interesting bits
            result['msg'] = "Updated"
            result['status'] = err

        result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
