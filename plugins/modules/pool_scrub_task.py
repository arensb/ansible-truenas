#!/usr/bin/python
__metaclass__ = type

DOCUMENTATION = '''
---
module: pool_scrub_task
short_description: Schedule periodic scrub of ZFS pools.
description:
  - Schedule periodic ZFS pool scrub tasks.
options:
  description:
    description:
      - Optional description of this task.
    type: str
  pool:
    description:
      - Name of the pool to scrub.
      - Only one scrub task is allowed per pool.
    type: str
    required: true
  threshold:
    description:
      - Minimum number of days between successful scrub tasks.
      - For instance, if you schedule a job to run every day, but set
        threshold to 7, the job will check every day to see whether
        it should run, but will only actually run once every 7 days.
    type: int
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
  enabled:
    description:
      - Whether the task should be enabled
    type: bool
  state:
    description:
      - Whether the scrub should exist or not.
    type: str
    choices: [ absent, present ]
    default: present
version_added: 1.8.0
'''

EXAMPLES = '''
- name: Create a default periodic scrub task.
  hosts: zfs_host
  become: yes
  tasks:
    - arensb.truenas.pool_scrub_task:
      pool: tank

- name: Create a weekly task with a 35-day threshold
  hosts: zfs_host
  become: yes
  tasks:
    - arensb.truenas.pool_scrub_task:
      pool: tank
      description: Test weekly, scrub monthly.
      threshold: 35
      hour: "3"
      day: "*"
      month: "*"
      weekday: "tue"

- name: Delete an existing scrub task.
  hosts: zfs_host
  become: yes
  tasks:
    - arensb.truenas.pool_scrub_task:
      pool: tank
      state: absent
'''

RETURN = '''
task:
  description:
    - A structure describing a newly-created task.
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW


def main():
    module = AnsibleModule(
        argument_spec=dict(
            pool=dict(type='str', required=True),
            description=dict(type='str'),
            threshold=dict(type='int'),
            enabled=dict(type='bool'),
            state=dict(type='str', default='present',
                       choices=['absent', 'present']),

            # Time specification copied from the builtin.cron module.
            minute=dict(type='str'),
            hour=dict(type='str'),
            day=dict(type='str', aliases=['date', 'dom']),
            month=dict(type='str'),
            weekday=dict(type='str', aliases=['dow']),
            ),
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW.client()

    # Assign variables from properties, for convenience
    description = module.params['description']
    pool = module.params['pool']
    threshold = module.params['threshold']
    enabled = module.params['enabled']
    state = module.params['state']
    minute = module.params['minute']
    hour = module.params['hour']
    day = module.params['day']
    month = module.params['month']
    weekday = module.params['weekday']

    # 'minute' isn't actually used anywhere; it's just here for
    # argument compatibility with builtin.cron. But let's use it just
    # to shut lint up.
    minute = minute

    # Look up the scrub task
    try:
        scrub_info = mw.call("pool.scrub.query",
                             [["pool_name", "=", pool]])
        if len(scrub_info) == 0:
            # No such resource
            scrub_info = None
        else:
            # Resource exists
            scrub_info = scrub_info[0]
    except Exception as e:
        module.fail_json(msg=f"Error looking up scrub task for {pool}: {e}")

    # First, check whether the task even exists.
    if scrub_info is None:
        # Task doesn't exist

        if state == 'present':
            # Task is supposed to exist, so create it.

            # Collect arguments to pass to pool.scrub.create()
            arg = {}

            # We were given a pool name, but we need an integer pool
            # ID, so look up the pool by name.
            try:
                pool_info = mw.call("pool.query",
                                    [["name", "=", pool]])
                if len(pool_info) == 0:
                    # No such pool
                    module.json_fail(msg="Error: no such pool: {pool}")
                else:
                    pool_info = pool_info[0]
            except Exception as e:
                module.json_fail(msg=f"Error looking up pool {pool}: {e}")

            arg['pool'] = pool_info['id']

            if description is not None:
                arg['description'] = description

            if threshold is not None:
                arg['threshold'] = threshold

            if enabled is not None:
                arg['enabled'] = enabled

            # Start with an empty schedule.
            schedule = {}

            # Set the time when the task should occur.
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
                result['msg'] = "Would have created " \
                    f"scrub task with {arg}"
            else:
                #
                # Create new scrub task
                #
                try:
                    err = mw.call("pool.scrub.create", arg)
                    result['msg'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating scrub task: {e}")

                # Return a description of the newly-created scrub task.
                result['task'] = err

            result['changed'] = True
        else:
            # Task is not supposed to exist.
            # All is well
            result['changed'] = False

    else:
        # Task exists
        if state == 'present':
            # Task is supposed to exist

            # Make list of differences between what is and what should
            # be.
            arg = {}

            if description is not None and \
               scrub_info['description'] != description:
                arg['description'] = description

            if threshold is not None and scrub_info['threshold'] != threshold:
                arg['threshold'] = threshold

            if enabled is not None and scrub_info['enabled'] != enabled:
                arg['enabled'] = enabled

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
               scrub_info['schedule']['hour'] != hour:
                schedule['hour'] = hour

            if day is not None and scrub_info['schedule']['dom'] != day:
                schedule['dom'] = day

            if month is not None and \
               scrub_info['schedule']['month'] != month:
                schedule['month'] = month

            if weekday is not None and \
               scrub_info['schedule']['dow'] != weekday:
                schedule['dow'] = weekday

            if len(schedule) > 0:
                arg['schedule'] = schedule

            # If there are any changes, pool.scrub.update()
            if len(arg) == 0:
                # No changes
                result['changed'] = False
            else:
                #
                # Update the task.
                #
                if module.check_mode:
                    result['msg'] = f"Would have updated scrub task: {arg}"
                else:
                    try:
                        err = mw.call("pool.scrub.update",
                                      scrub_info['id'],
                                      arg)
                    except Exception as e:
                        module.fail_json(msg="Error updating scrub task "
                                         f"with {arg}: {e}")
                        # Return any interesting bits from err
                        result['status'] = err['status']
                result['changed'] = True
        else:
            # Scrub task is not supposed to exist

            if module.check_mode:
                result['msg'] = f"Would have deleted scrub task for {pool}"
            else:
                try:
                    #
                    # Delete scrub task.
                    #
                    err = mw.call("pool.scrub.delete",
                                  scrub_info['id'])
                except Exception as e:
                    module.fail_json(msg=f"Error deleting scrub task: {e}")
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
