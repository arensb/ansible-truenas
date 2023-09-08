#!/usr/bin/python
__metaclass__ = type

# XXX - Comparing schedules is harder than it looks: hour, day of the
# month, day of the week, month are all comma-separated lists of
# values.
#
# Hour can include ranges, e.g., "1-5,9-10".
#
# Likewise day of the month, e.g., "1-5,9-12".
#
# Day of the week is given as "sun", "mon", etc.
#
# Month is given as "jan", "feb", "mar", etc.
#
# The simple solution would be to just punt, and compare strings. That
# means that if the current cron job has "0 0 * * sun", but the caller
# has "weekday: 0" or "weekday: Sunday", that'll be seen as a change.
#
# This is probably good enough, at least for now. I'm not sure that
# normalizing cron times to compare them is worth the effort.

# XXX - There's no good way to delete all tasks and go back to a known
# blank slate. Maybe we want to change the rules if state==absent:
# don't require a name, schedule, or type, and delete anything that
# matches the given criteria.
#
# It's tempting to say that
#     - smart_test_task:
#         disks: ALL
#         state: absent
#
# should delete all jobs on all disks, but that might be a step too
# far. That should delete all jobs with 'all_disks' set.
#
# What if we have
#
#     - smart_test_task:
#         disks: ada0
#         state: absent
#
# and there's a matching job that runs on [ ada0, ada1 ]? In this
# case, the sensible thing to do might be to just edit the job and
# remove ada0.

DOCUMENTATION = '''
---
module: smart_test_task
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
      - This is a comma-separated list of integer ranges.
    type: str
  day:
    description:
      - Day of month when the task should run, in cron format.
      - This is a comma-separated list of integer ranges, e.g.,
        "10", "1-5", "1,3,7-10".
    type: str
    aliases: ['date', 'dom']
  month:
    description:
      - Month when the task should run, in cron format.
      - This is a comma-separated list of month names or numbers,
        e.g., "jan,feb,mar".
    type: str
  weekday:
    description:
      - Day of week when the task should run, in cron format.
      - This is a comma-separated list of day numbers of abbreviations,
        e.g. "1", "1,5", "sun,mon".
    type: str
    aliases: ['dow']
  state:
    description:
      - Whether the task should exist or not.
    type: str
    choices: [ absent, present ]
    default: present
version_added: 1.8.0
'''

EXAMPLES = '''
- name: Run a SHORT test every month
  hosts: my-truenas-server
  tasks:
    - arensb.truenas.smart_test_task:
        name: "Monthly job"
        disks: ALL
        test: short
        hour: 13
        day: 1
        month: "*"

- name: Run a SHORT test twice a month on some disks
  hosts: my-truenas-server
  tasks:
    - arensb.truenas.smart_test_task:
        name: "Bimonthly job on ada0, ada1"
        disks:
          - ada0
          - ada1
        test: short
        hour: 3
        day: 1,15
        month: "*"
'''

# XXX - Should be the same as pool_snapshot_task, for consistency:
# task: the newly-created task.
# deleted_tasks: list of deleted tasks, when deleting.
RETURN = '''
task:
  description:
    - A structure describing a newly-created task.
  type: dict
  returned: Success, when created.
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW


def main():
    def diskname2id(name: str):
        """Convert a disk name like 'da0' to an ID."""

        try:
            disk_id = mw.call("disk.device_to_identifier",
                              name,
                              output='str')
        except Exception as e:
            module.fail_json(msg=f"Can't look up disk {name}: {e}")

        return disk_id

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
            }

            # Special value "ALL" means to check all disks.
            # "all_disks" and "disks" are mutually-exclusive.
            if "ALL" in disks:
                arg['all_disks'] = True
            else:
                arg['disks'] = []

                for disk in disks:
                    arg['disks'].append(diskname2id(disk))

                # At this point, arg['disks'] should be an array of
                # the form:
                # ["{serial_lunid}ABC12345_1111111111111111",
                #  "{serial_lunid}DEF67890_2222222222222222",
                #  ...
                # ]

            if test is not None:
                # Convert to upper case.
                arg['type'] = test.upper()

            # Start with an empty schedule.
            schedule = {}

            # Set the time when the test should occur.
            if hour is not None:
                schedule['hour'] = hour

            if day is not None:
                schedule['dom'] = day

            if month is not None:
                schedule['month'] = month

            if weekday is not None:
                schedule['dow'] = weekday

            if len(schedule) > 0:
                # One or more schedule fields were specified.
                arg['schedule'] = schedule

            if module.check_mode:
                result['msg'] = f"Would have created resource {name} " \
                    f"with {arg}"
            else:
                #
                # Create new resource
                #
                try:
                    err = mw.call("smart.test.create", arg)
                    result['msg'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg="Error creating S.M.A.R.T. Test "
                                     f"task {name}: {e}")

                # Return whichever interesting bits smart.test.create()
                # returned.
                result['task'] = err

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

            if disks is not None:
                if "ALL" in disks:
                    # We want to monitor all disks.
                    if smart_test_info['all_disks'] is False:
                        smart_test_info['all_disks'] = True
                        result['changed'] = True
                else:
                    # Only want to monitor some disks.
                    want_disks = [diskname2id(disk) for disk in disks]

                    if smart_test_info['all_disks'] is True:
                        arg['all_disks'] = False
                        arg['disks'] = want_disks
                        result['changed'] = True
                    else:
                        # Use set comparison, because order doesn't matter.
                        if set(smart_test_info['disks']) != set(want_disks):
                            smart_test_info['disks'] = want_disks
                            result['changed'] = True

            if test is not None and smart_test_info['type'] != test.upper():
                arg['type'] = test.upper()

            # Schedule.
            # Create an empty schedule.
            schedule = {}

            # XXX - These comparisons are simplistic: they consider
            # "1-3" and "1,2,3" to be different, as well as "0" and
            # "sun". See comment at the top of the file.
            #
            # But implementing a real schedule comparison is probably
            # not worth the effort.
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
                    result['msg'] = "Would have updated " \
                        f"S.M.A.R.T. Test task {name}: {arg}"
                else:
                    try:
                        err = mw.call("smart.test.update",
                                      smart_test_info['id'],
                                      arg)
                    except Exception as e:
                        module.fail_json(msg="Error updating S.M.A.R.T. "
                                         f"Test task {name} with {arg}: {e}")
                        # Return any interesting bits from err
                        result['status'] = err['status']
                result['changed'] = True
        else:
            # S.M.A.R.T. Test task is not supposed to exist

            if module.check_mode:
                result['msg'] = "Would have deleted S.M.A.R.T. Test " \
                    f"task {name}"
            else:
                try:
                    #
                    # Delete S.M.A.R.T. Test task
                    #
                    err = mw.call("smart.test.delete",
                                  smart_test_info['id'])
                except Exception as e:
                    module.fail_json(msg="Error deleting S.M.A.R.T. "
                                     f"Test task {name}: {e}")
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
