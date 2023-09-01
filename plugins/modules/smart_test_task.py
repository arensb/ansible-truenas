#!/usr/bin/python
__metaclass__ = type

# XXX - One-line description of module

# XXX
DOCUMENTATION = '''
---
module: smart_test
short_description: Schedule S.M.A.R.T. tests
description:
  - Schedule S.M.A.R.T. tests under "Tasks".
options:
  name:
    description:
      - Name of the test. This must be unique across S.M.A.R.T. test
        tasks, since it effectively acts as an identifier.
    type: str
    required: true
  test:
    description:
      - The test to perform. Choices are "long", "short",
        "conveyance", and "offline".
    type: str
    choices: [ long, short, conveyance, offline ]
  disks:
    description:
      - List of disk devices to check, e.g., "da0".
      - The special value "ALL" means to check all disks.
    type: list
    elements: str
    aliases: [ discs ]
    required: true
  minute:
    description:
      - This parameter is ignored, and exists only for compatibility
        with builtin.cron.
    type: str
  hour:
    description:
      - Hour when the task should run, in cron format.
    type: str
  day:
    description:
      - Day of month when the task should run, in cron format.
    type: str
    aliases: ['date', 'dom']
  month:
    description:
      - Month when the task should run, in cron format.
    type: str
  weekday:
    description:
      - Day of week when the task should run, in cron format.
    type: str
    aliases: ['dow']
  state:
    description:
      - Whether the resource should exist or not.
    type: str
    choices: [ absent, present ]
    default: present
version_added: XXX
'''

# XXX
EXAMPLES = '''
'''

# XXX - Should be the same as pool_snapshot_task, for consistency:
# task: the newly-created task.
# deleted_tasks: list of deleted tasks, when deleting.
RETURN = '''
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW


def main():
    # XXX - schedule: similar to pool_snapshot_task
    #   hour
    #   dom - day of month (1-31)
    #   month
    #   dow - day of week
    # desc(str) - description - name
    # all_disks(bool)
    # disks(list(str))
    # type (enum: LONG, SHORT, CONVEYANCE, OFFLINE)
    #
    # disks is an array of strings. Can include the magic value "all",
    # meaning all disks.

    # XXX - Doesn't take a "minute" parameter. Do we want to accept
    # one anyway, just for compatibility with cron? Just ignore it.

    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str', required=True),
            test=dict(type='str',
                      choices=['long', 'short', 'conveyance', 'offline',
                               'LONG', 'SHORT', 'CONVEYANCE', 'OFFLINE']),
            state=dict(type='str', default='present',
                       choices=['absent', 'present']),
            disks=dict(type='list', elements='str',
                       required=True, aliases=['discs']),

            # Time specification copied from the builtin.cron module.
            minute=dict(type='str'),
            hour=dict(type='str'),
            day=dict(type='str', aliases=['date', 'dom']),
            month=dict(type='str'),
            weekday=dict(type='str', aliases=['dow']),
            ),
        required_if=[
            # If you want the task to exist, need to say when it
            # should occur. (If you want it to be absent, that's not
            # required.)
            ['state', 'present', ['hour', 'day', 'month', 'weekday'], True],
        ],
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW.client()

    # Assign variables from properties, for convenience
    name = module.params['name']
    test = module.params['test']
    state = module.params['state']
    disks = module.params['disks']
    minute = module.params['minute']
    hour = module.params['hour']
    day = module.params['day']
    month = module.params['month']
    weekday = module.params['weekday']

    # 'minute' isn't actually used anywhere; it's just here for
    # argument compatibility with builtin.cron. But let's use it just
    # to shut lint up.
    minute = minute

    # Look up the task
    try:
        smart_test_info = mw.call("smart.test.query",
                                  [["desc", "=", name]])
        if len(smart_test_info) == 0:
            # No such resource
            smart_test_info = None
        else:
            # Resource exists
            smart_test_info = smart_test_info[0]
    except Exception as e:
        module.fail_json(msg=f"Error looking up S.M.A.R.T. Test {name}: {e}")

    # First, check whether the task even exists.
    if smart_test_info is None:
        # Resource doesn't exist

        if state == 'present':
            # Resource is supposed to exist, so create it.

            # Collect arguments to pass to resource.create()
            arg = {
                'desc': name,
                'schedule': {
                    # Default values:
                    'hour': '*',
                    'dom': '*',
                    'month': '*',
                    'dow': '*',
                },
            }

            # Special value "ALL" means to check all disks.
            # "all_disks" and "disks" are mutually-exclusive.
            if "ALL" in disks:
                arg['all_disks'] = True
            else:
                arg['disks'] = []

                # Look up the list of disks: we need to use their LUN
                # IDs in the S.M.A.R.T. task request.
                try:
                    disk_data = mw.call("device.get_disks")
                except Exception as e:
                    module.fail_json(msg=f"Error looking up disks: {e}")

                for disk in disks:
                    # Look up the disk in the list of known disks, to
                    # get its ID.
                    if disk not in disk_data:
                        module.fail_json(msg=f"Unknown disk: {disk}")

                    # Construct a disk identifier out of the
                    # information we have.
                    if 'serial_lunid' in disk_data[disk]:
                        arg['disks'].\
                            append("{{serial_lunid}}"
                                   f"{disk_data[disk]['serial_lunid']}")
                    elif 'serial' in disk_data[disk]:
                        arg['disks'].\
                            append("{{serial}}"
                                   f"{disk_data[disk]['serial']}")
                # At this point, arg['disks'] should be an array of
                # the form:
                # ["{serial_lunid}ABC12345_1111111111111111",
                #  "{serial_lunid}DEF67890_2222222222222222",
                #  ...
                # ]

            if test is not None:
                # Convert to upper case.
                arg['type'] = test.upper()

            # Set the time when the test should occur. If any value
            # hasn't been specified, it defaults to "*", above.
            if hour is not None:
                arg['schedule']['hour'] = hour

            if day is not None:
                arg['schedule']['dom'] = day

            if month is not None:
                arg['schedule']['month'] = month

            if weekday is not None:
                arg['schedule']['dow'] = weekday

            if module.check_mode:
                result['msg'] = f"Would have created resource {name} with {arg}"
            else:
                #
                # Create new resource
                #
                try:
                    err = mw.call("smart.test.create", arg)
                    result['msg'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating S.M.A.R.T. Test task {name}: {e}")

                # Return whichever interesting bits smart.test.create()
                # returned.
                result['smart_test_task'] = err

            result['changed'] = True
        else:
            # Resource is not supposed to exist.
            # All is well
            result['changed'] = False

    else:
        # Resource exists
        if state == 'present':
            # Resource is supposed to exist

            # Make list of differences between what is and what should
            # be.
            arg = {}

            # XXX - Need to call device.get_disks to map disks to IDs.
            # XXX - disks. Use set comparison, because order doesn't matter.

            if test is not None and smart_test_info['type'] != test.upper():
                arg['type'] = test.upper()

            # Schedule.
            # Create an empty schedule.
            schedule = {}

            if hour is not None and \
               smart_test_info['schedule']['hour'] != hour:
                schedule['hour'] = hour
            if day is not None and smart_test_info['schedule']['dom'] != day:
                schedule['dom'] = day
            if month is not None and \
               smart_test_info['schedule']['month'] != month:
                schedule['month'] = month
            if weekday is not None and \
               smart_test_info['schedule']['dow'] != weekday:
                schedule['dow'] = weekday
            if len(schedule) > 0:
                arg['schedule'] = schedule

            # If there are any changes, resource.update()
            if len(arg) == 0:
                # No changes
                result['changed'] = False
            else:
                #
                # Update the S.M.A.R.T. Test task
                #
                if module.check_mode:
                    result['msg'] = f"Would have updated S.M.A.R.T. Test task {name}: {arg}"
                else:
                    try:
                        err = mw.call("smart.test.update",
                                      smart_test_info['id'],
                                      arg)
                    except Exception as e:
                        module.fail_json(msg=f"Error updating S.M.A.R.T. Test task {name} with {arg}: {e}")
                        # Return any interesting bits from err
                        result['status'] = err['status']
                result['changed'] = True
        else:
            # S.M.A.R.T. Test task is not supposed to exist

            if module.check_mode:
                result['msg'] = f"Would have deleted S.M.A.R.T. Test task {name}"
            else:
                try:
                    #
                    # Delete S.M.A.R.T. Test task
                    #
                    err = mw.call("smart.test.delete",
                                  smart_test_info['id'])
                except Exception as e:
                    module.fail_json(msg=f"Error deleting S.M.A.R.T. Test task {name}: {e}")
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
