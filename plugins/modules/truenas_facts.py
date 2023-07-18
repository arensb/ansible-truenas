#!/usr/bin/python
__metaclass__ = type

# XXX - This module adds to the execution time: at a first pass, about
# 1 second using client api, and 7 seconds(!) using midclt. It might
# be useful to profile the different calls, and see if there are any
# that are slow and less-useful.

# XXX - Currently, this module skips any time something goes wrong, on
# the assumption that it's on a non-TrueNAS system, so it shouldn't
# really be running. But in fact, if it _is_ on a TrueNAS box, a
# failure should cause a real failure.
#
# So maybe we can decree that the various middleware modules must
# raise an exception during class initialization or forever hold their
# peace, so that if the 'import' succeeds, anything after that is
# deemed to be an error.

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
version_added: 1.7.0
seealso:
  - name: Ansible Configuration Settings
    description: Configure which fact-gathering modules to use.
    link: https://docs.ansible.com/ansible/latest/reference_appendices/config.html#facts-modules
'''

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

RETURN = '''
ansible_facts.truenas_boot_id:
  description:
    - The host's unique boot identifier. Changes every time the
      system boots.
  returned: always
  type: str
  sample: 1f065a66-a5de-464d-a6b3-f786143028fc
ansible_facts.truenas_host_id:
  description:
    - A hex string based on (but not identical to) the contents of
      C(/etc/hostid).
    - This ID is permanent and persists across both reboots and upgrades,
      so it can be used as a unique identifier for the machine.
  returned: always
  type: str
  sample: 6f7145029674ad4f49fac7090dce20de0d02eef3bb462c25dce3ab15a367ac41
ansible_facts.truenas_product_name:
  description:
    - A string giving the overall name of the product, usually
      C(TrueNAS)
  returned: always
  type: str
  sample: TrueNAS
ansible_facts.truenas_product_type:
  description:
    - The flavor of TrueNAS. One of C(CORE), C(ENTERPRISE), or C(SCALE).
  type: str
  returned: always
  sample: CORE
ansible_facts.truenas_environment:
  description:
    - The environment in which TrueNAS is running. One of
      C(DEFAULT) or C(EC2).
  type: str
  returned: always
  sample: DEFAULT
ansible_facts.truenas_features:
  description:
    - A map that says, for each system feature, whether it is enabled
      or not.
  type: dict
  sample: {
      "DEDUP": true,
      "FIBRECHANNEL": false,
      "JAILS": true,
      "VM": true,
    }
ansible_facts.truenas_state:
  description:
    - The current state of the system, one of
      C(BOOTING), C(SHUTTING_DOWN), or C(READY).
  type: str
  returned: always
  sample: READY
ansible_facts.truenas_system_info:
  description:
    - A dictionary with a number of facts about the system. See the
      sample value below.
  type: complex
  returned: always
  sample: {
    "version": "TrueNAS-13.0-U5",
    "buildtime": {
      "$date": 1685357420000
    },
    "hostname": "myhost.dom.ain",
    "physmem": 8421797888,
    "model": "AMD(R) Razor(R) CPU  J1900  @ 3.99GHz",
    "cores": 8,
    "loadavg": [
      0.2568359375,
      0.28369140625,
      0.2607421875
    ],
    "uptime": "46 days, 13:14:50.823465",
    "uptime_seconds": 4022090.823465127,
    "system_serial": "To be filled by O.E.M.",
    "system_product": "To be filled by O.E.M.",
    "system_product_version": "To be filled by O.E.M.",
    "license": null,
    "boottime": {
      "$date": 1685626178000
    },
    "datetime": {
      "$date": 1689648269852
    },
    "birthday": {
      "$date": 1677351513088
    },
    "timezone": "America/New_York",
    "system_manufacturer": "To be filled by O.E.M.",
    "ecc_memory": false
  }
ansible_facts.truenas_build_time:
  description:
    - The system build time, when the OS was built.
    - Internally, this is a Python C(datetime.datetime) object, and is
      converted to a string by the time it gets to the Ansible client.
  type: str
  sample: 2023-05-29T06:50:20
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
        result['msg'] = f"Can't load required module: {e}"
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
