#!/usr/bin/python
__metaclass__ = type

# XXX - Make sure this does nothing on non-TrueNAS hosts, so that it
# can safely be added to the default set of fact-gathering modules.

# XXX
DOCUMENTATION = '''
---
module: truenas_facts
short_description: Gather TrueNAS-related facts
description:
  - Gather facts about a TrueNAS host, in the same way as
    C(setup) does.
  - Any facts discovered by this module will be mixed in with those
    discovered by other modules such as C(setup).
  - See U(https://docs.ansible.com/ansible/latest/reference_appendices/config.html#facts-modules)
    for how to use this module, as well as the Examples section.
  - You can set the environment variable C(ANSIBLE_FACTS_MODULES) to
    C(arensb.truenas.truenas_facts) to use only this module to gather facts,
    or to C(setup, arensb.truenas.truenas_facts) to use both the standard
    C(setup) module and this one.
  - Likewise, you can set the C(ansible_facts_modules) inventory
    variable to the list of modules to use, either just
    C(arensb.truenas.truenas_facts), or C([setup,
    arensb.truenas.truenas_facts]).
  - |
    This module may be used on non-TrueNAS hosts: it should simply fail
    gracefully and do nothing.
notes:
  - Supports C(check_mode).
  - Should run correctly on non-TrueNAS hosts.
version_added: 1.6.3
'''

# XXX
EXAMPLES = '''
- name: Manually gather information
  collections: arensb.truenas
  hosts: myhost
  tasks:
    - name: Gather TrueNAS-specific facts
      arensb.truenas.truenas_facts:
    # ansible_facts should have TrueNAS facts mixed in with the usual ones.
    - debug: var=ansible_facts
'''

# XXX - Look up these descriptions in exchanges about NFS failing.
RETURN = '''
ansible_facts.truenas_product_name:
  description:
    - A string giving the overall name of the product, usually
      C(TrueNAS)
  type: str
ansible_facts.truenas_product_type:
  description:
    - The flavor of TrueNAS. One of C(CORE), XXX, XXX...
  type: str
'''

from ansible.module_utils.basic import AnsibleModule
from datetime import datetime


def main():
    module = AnsibleModule(
        argument_spec=dict(),
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        msg='',
        ansible_facts=dict(),
    )

    try:
        # We don't actually expect this to fail, since the MiddleWare
        # module comes with this module, and should therefore be
        # available everywhere.
        from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
            import MiddleWare as MW
    except ImportError as e:
        result['skipped'] = True
        module.exit_json(**result)

    # Creating a MiddleWare client can fail if the TrueNAS-related
    # modules aren't present on the remote system.
    try:
        mw = MW.client()
    except ModuleNotFoundError as e:
        result['msg'] = f'Got module not found exeption {e}'
        result['skipped'] = True
        module.exit_json(**result)
    except FileNotFoundError as e:
        result['msg'] = f'Got file not found exeption {e}'
        result['skipped'] = True
        module.exit_json(**result)

    try:
        result['ansible_facts']['truenas_boot_id'] = \
            mw.call("system.boot_id", output='str')
        result['ansible_facts']['truenas_host_id'] = \
            mw.call("system.host_id", output='str')
        result['ansible_facts']['truenas_product_name'] = \
            mw.call("system.product_name", output='str')
        result['ansible_facts']['truenas_product_type'] = \
            mw.call("system.product_type", output='str')
        result['ansible_facts']['truenas_environment'] = \
            mw.call("system.environment", output='str')
        result['ansible_facts']['truenas_state'] = \
            mw.call("system.state", output='str')
        result['ansible_facts']['truenas_system_info'] = \
            mw.call("system.info")

        # The build time is a timestamp, but it's returned in different
        # ways by different middlewared APIs.
        #
        # Also, different Ansible modules deal with timestamps
        # differently: some use time_t, others use human-readable strings.
        # So for now at least, let's return a datetime.datetime
        build_time = mw.call("system.build_time")
        if isinstance(build_time, datetime):
            # The direct Python connection to middlewared returns
            # a datetime.datetime object, so just return that.
            result['ansible_facts']['truenas_build_time'] = build_time
        elif isinstance(build_time, dict) and '$date' in build_time:
            # 'midclt' returns a dict of the form
            #   {"$date": 1234567890000}
            # which is the number of milliseconds since the epoch.
            # Convert that to a datetime.
            result['ansible_facts']['truenas_build_time'] = \
                datetime.fromtimestamp(build_time['$date']/1000)
        else:
            # This is unexpected. Add a warning message, return the
            # supplied value, and hope for the best.
            module.warn(f'Unexpected type or build_time: {type(build_time)}.')
            result['ansible_facts']['truenas_build_time'] = build_time

        # Get the set of features and whether they're enabled.
        result['truenas_features'] = {}
        for feat in ('DEDUP', 'FIBRECHANNEL', 'JAILS', 'VM'):
            feat_set = mw.call("system.feature_enabled", feat, output='str')
            result['truenas_features'][feat] = feat_set
    except Exception as e:
        result['skipped'] = True
        result['msg'] = f"Error looking up facts: {e}"
        module.exit_json(**result)

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
