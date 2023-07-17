#!/usr/bin/python
__metaclass__ = type

DOCUMENTATION = '''
---
module: jails
short_description: Configure jail system
description:
  - Configure the jail system. Some of this overlaps with the plugin system.
  - Does not configure individual jails. For that, see C(jail).
options:
  pool:
    description:
      - The currently active pool. New jails and plugins will be created here.
      - Does not move existing jails (or plugins). They continue to run
        wherever they currently are.
    type: str
version_added: 1.1.0
'''

# XXX
EXAMPLES = '''
'''

# XXX
RETURN = '''
status:
  description: True iff pool activation was successful.
  type: bool
  sample: True
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW


def main():
    module = AnsibleModule(
        argument_spec=dict(
            pool=dict(type='str'),
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

    # Look up which pool is currently activated.
    try:
        active_pool = mw.call("jail.get_activated_pool",
                              output='str')
    except Exception as e:
        module.fail_json(msg=f"Error looking up active pool: {e}")
    result['active_pool'] = active_pool

    # Make list of differences between what is and what should
    # be.

    # By default, assume nothing is changing. If something does change,
    # update this.
    result['changed'] = False

    if pool is not None and active_pool != pool:
        #
        # Update the active pool
        #
        if module.check_mode:
            result['msg'] = f"Would have activated pool {pool}"
        else:
            try:
                err = mw.call("jail.activate", pool,
                              output='str')
            except Exception as e:
                module.fail_json(msg=f"Error activating pool {pool}: {e}")
            result['status'] = err

            if err != 'True':
                module.fail_json(msg=f"Error activating pool {pool}: "
                                 f"err == {err}")

        result['changed'] = True

    # In principle, other things could be changed. Put them here.

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
