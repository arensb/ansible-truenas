#!/usr/bin/python
__metaclass__ = type

DOCUMENTATION = '''
---
module: smart
short_description: Configure S.M.A.R.T. service
description:
  - Configure the S.M.A.R.T. service.
  - To turn on the S.M.A.R.T. service and make sure it starts
    at boot time, see C(service).
  - This module does not schedule S.M.A.R.T. scans. That is done
    by C(smart_scan).
options:
  interval:
    description:
      - Time in minutes between S.M.A.R.T. tests.
      - Technically, this is how often smartd activates to check whether
        any tests are configured to run.
    type: int
  power_mode:
    description:
      - Selects the power mode. Options are C(never), C(sleep), C(standby),
        and C(idle). These correspond to the C(-n POWERMODE) option to
        C(smartd).
      - "C(never): Check the device regardless of its power mode."
      - "C(sleep): Check the device unless it is in C(sleep) mode."
      - "C(standby): Check the device unless it is in C(sleep) or C(standby)
        mode."
      - "C(idle): Check the device unless it is in C(sleep), C(standby), or
        C(idle) mode."
    type: str
    choices: [ NEVER, SLEEP, STANDBY, IDLE ]
  temp_difference:
    description:
      - Significant temperature difference. A report will be generated if
        the temperature is more than C(temp_difference) degrees Celsius
        different from the last test.
      - Set to 0 to disable this behavior.
    type: int
  temp_info:
    description:
      - Threshold temperature, in degrees Celsius.
      - If a disk goes above this temperature, SMART will generate a
        message with log level of LOG_INFO.
      - Set to 0 to disable this behavior.
    type: int
  temp_crit:
    description:
      - Threshold temperature, in degrees Celsius.
      - If a disk goes above this temperature, SMART will generate a
        message with log level of LOG_CRIT.
      - Set to 0 to disable this behavior.
    type: int
version_added: 1.8.0
'''

EXAMPLES = '''
- name: Configure S.M.A.R.T. service
  hosts: myhost
  become: yes
  tasks:
    - arensb.truenas.smart:
        power_mode: never
        # Generate report if a disk is 2 degrees hotter or cooler than
        # last time.
        temp_difference: 2
        # Generate a LOG_INFO message if a disk goes above 40 degrees.
        temp_info: 40
        # Generate a LOG_CRIT message if a disk goes above 45 degrees.
        temp_crit: 45
'''

RETURN = '''
status:
  description:
    - A data structure giving the current state of the S.M.A.R.T.
      service, after this module has made changes.
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW


def main():
    module = AnsibleModule(
        argument_spec=dict(
            interval=dict(type='int'),
            power_mode=dict(type='str',
                            choices=['never', 'sleep', 'standby', 'idle']),
            temp_difference=dict(type='int'),
            temp_info=dict(type='int'),
            temp_crit=dict(type='int'),
            ),
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW.client()

    # Assign variables from properties, for convenience
    interval = module.params['interval']
    power_mode = module.params['power_mode']
    temp_difference = module.params['temp_difference']
    temp_info = module.params['temp_info']
    temp_crit = module.params['temp_crit']

    # Look up the S.M.A.R.T. configuration
    try:
        smart_info = mw.call("smart.config")
    except Exception as e:
        module.fail_json(msg=f"Error looking up S.M.A.R.T. configuration: {e}")

    # Make list of differences between what is and what should
    # be.
    arg = {}

    if interval is not None and smart_info['interval'] != interval:
        arg['interval'] = interval
    if power_mode is not None and \
       smart_info['powermode'].lower() != power_mode:
        arg['powermode'] = power_mode.upper()
    if temp_difference is not None and \
       smart_info['difference'] != temp_difference:
        arg['difference'] = temp_difference
    if temp_info is not None and smart_info['informational'] != temp_info:
        arg['informational'] = temp_info
    if temp_crit is not None and smart_info['critical'] != temp_crit:
        arg['critical'] = temp_crit

    # If there are any changes, smart.update()
    if len(arg) == 0:
        # No changes
        result['changed'] = False
    else:
        #
        # Update smart.
        #
        if module.check_mode:
            result['msg'] = f"Would have updated S.M.A.R.T.: {arg}"
        else:
            try:
                err = mw.call("smart.update",
                              arg)
                # New state of the S.M.A.R.T. service.
                result['status'] = err
            except Exception as e:
                module.fail_json(msg=f"Error updating S.M.A.R.T. with {arg}: {e}")
                # Return any interesting bits from err
                result['status'] = err['status']
        result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
