#!/usr/bin/python
__metaclass__ = type

# Create and maintain periodic disk pool snapshot tasks.

DOCUMENTATION = '''
---
module: pool_snapshot_task
short_description: Maintain periodic disk pool snapshot tasks.
description:
  - Creates, deletes, and configures disk pool snapshot tasks.
options:
  dataset:
    description:
      - The name of the dataset to snapshot. This can be a pool, ZFS
        dataset, or zvol.
    type: str
    required: true
  lifetime_unit:
    description:
      - A unit of time for the snapshot lifetime before it is deleted.
        One of the following units of time:
        C(hour), C(day), C(week), C(month), C(year),
        optionally pluralized.
      - Along with C(lifetime_value), specifies the length of time a
        snapshot will be kept before being deleted.
    type: str
    choices: [ hour, hours, day, days, week, weeks, month, months, year, years ]
  lifetime_value:
    description:
      - The number of units of time that the snapshot will exist before
        it is deleted. Used in conjunction with C(lifetime_unit).
    type: int
  match:
    description:
      - A snapshot task does not have a name or other visible unique
        identifier, so the C(match) option provides a way of specifying
        which of several tasks the play is configuring, as well as
        telling whether the task exists yet or not.
      - The C(match) option is a dict with one or more keywords
        identifying the task. At least one must be provided.
      - If the C(state) option is C(present), only the first matching
        dataset will be updated. If C(state) is C(absent), all matching
        datasets will be deleted.
    required: true
    suboptions:
      dataset:
        description:
          - Name of the dataset being snapshotted. This can be a pool,
            dataset, or zvol.
        type: str
      name_format:
        description:
          - This is a regular expression that the C(name_format) option must
            match. The idea being that you can name your snapshots something
            like C(daily-%Y%m%d), and identify them by the prefix, using
            C(name_format: ^daily-).
        type: str
  name_format:
    description:
      - A template specifying the name of the snapshot. This must include
        the strings "%Y", "%m", "%d", "%H", and "%M". Their meanings are
        as in C(strftime): year, month, date, hour, and minute.
        Other C(strftime) sequences may also be included.
    type: str
    required: true
  recursive:
    description:
      - Whether to take snapshots of the child datasets, as well as of
        the dataset itself.
    type: bool
  state:
    description:
      - Whether the task should exist or not.
    type: str
    choices: [ absent, present ]
    default: present
'''

# XXX
EXAMPLES = '''
'''

# XXX
RETURN = '''
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW


def main():
    # Required arguments:
    # - dataset (path)
    # - recursive (bool)
    #   I don't know what a good default might be
    # - lifetime_value (int)
    # - lifetime_unit (enum)
    # - naming_schema (str)
    # - schedule (cron job)
    #
    # Other arguments:
    # - exclude (list(path))
    # - allow_empty (bool)
    # - enabled (bool)

    # dataset(str): name of the pool, volume, filesystem being backed up,
    #   e.g., "tank", "tank/iocage", "tank/iocage/download",
    #   "tank/iocage/download/13.3-RELEASE"
    module = AnsibleModule(
        argument_spec=dict(
            match=dict(type='dict', required=True,
                       options=dict(
                           # id=dict(type='int'),
                           dataset=dict(type='str'),
                           name_format=dict(type='str'),
                           # recursive=dict(type='bool'),
                           # lifetime=dict(type='str'),
                       )),
            state=dict(type='str', default='present',
                       choices=['absent', 'present']),
            dataset=dict(type='str', required=True),
            recursive=dict(type='bool', required=True),
            lifetime_value=dict(type='int', required=True),
            lifetime_unit=dict(type='str',
                               choices=['hour', 'hours', 'HOUR', 'HOURS',
                                        'day', 'days', 'DAY', 'DAYS',
                                        'week', 'weeks', 'WEEK', 'WEEKS',
                                        'month', 'months', 'MONTH', 'MONTHS',
                                        'year', 'years', 'YEAR', 'YEARS']),
            name_format=dict(type='str'),
            # XXX - begin (time: HH:MM)
            # XXX - end (time: HH:MM)
            # XXX - exclude (list(str))
            # XXX - allow_empty (bool)
            # XXX - enabled (bool)

            # Time specification copied from the builtin.cron module.
            minute=dict(type='str', default='*'),
            hour=dict(type='str', default='*'),
            day=dict(type='str', default='*', aliases=['dom']),
            month=dict(type='str', default='*'),
            weekday=dict(type='str', default='*', aliases=['dow']),
            ),
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW()

    # Assign variables from properties, for convenience
    match = module.params['match']
    state = module.params['state']
    dataset = module.params['dataset']
    recursive = module.params['recursive']
    lifetime_unit = module.params['lifetime_unit']
    lifetime_value = module.params['lifetime_value']
    name_format = module.params['name_format']
    minute = module.params['minute']
    hour = module.params['hour']
    day = module.params['day']
    month = module.params['month']
    weekday = module.params['weekday']

    # Look up the task.
    # Construct a set of criteria based on 'match'
    # "~" matches a regular expression, e.g., ["shell", "~", ".*zsh.*"]
    if match is None:
        module.fail_json(msg="No match conditions given.")

    queries = []
    if 'id' in match and match['id'] is not None:
        queries.append(["id", "=", match['id']])
    if 'dataset' in match and match['dataset'] is not None:
        queries.append(["dataset", "=", match['dataset']])
    if 'name_format' in match and match['name_format'] is not None:
        queries.append(["naming_schema", "~", match['name_format']])
    result['queries'] = queries
    if len(queries) == 0:
        # This can happen if the module spec includes some new match
        # options, but the code above doesn't parse them correctly or
        # something.
        # Also note the slightly different error message.
        module.fail_json(msg="No match conditions found.")

    # Note that 'matching_tasks' is the list of all tasks that match
    # the 'match' option, so we can delete them all if 'state==absent'.
    # 'task_info' is the first matching task, which we'll use when
    # creating and updating a task.
    try:
        matching_tasks = mw.call("pool.snapshottask.query", queries)
        if len(matching_tasks) == 0:
            # No such task
            task_info = None
        else:
            # Task exists
            task_info = matching_tasks[0]
    except Exception as e:
        module.fail_json(msg=f"Error looking up snapshot task {name}: {e}")

    # First, check whether the task even exists.
    if task_info is None:
        # Task doesn't exist

        if state == 'present':
            # Task is supposed to exist, so create it.

            # Collect arguments to pass to pool.snapshottask.create()
            arg = {
                "dataset": dataset,
                "recursive": recursive,
                "lifetime_value": lifetime_value,
                "lifetime_unit": lifetime_unit,
                "naming_schema": name_format,
            }

            # XXX
            # if feature is not None:
            #     arg['feature'] = feature

            # "exclude": exclude,

            if module.check_mode:
                result['msg'] = ("Would have created snapshot task "
                                 f"with {arg}")
            else:
                #
                # Create new task
                #
                try:
                    err = mw.call("pool.snapshottask.create", arg)
                    result['msg'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating snapshot task: {e}")

                # Return whichever interesting bits
                # pool.snapshottask.create() returned.
                result['task_id'] = err

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

            # XXX
            # if feature is not None and task_info['feature'] != feature:
            #     arg['feature'] = feature

            # If there are any changes, pool.snapshottask.update()
            if len(arg) == 0:
                # No changes
                result['changed'] = False
            else:
                #
                # Update task.
                #
                if module.check_mode:
                    result['msg'] = f"Would have updated snapshot task: {arg}"
                else:
                    try:
                        err = mw.call("pool.snapshottask.update",
                                      task_info['id'],
                                      arg)
                    except Exception as e:
                        module.fail_json(msg=(f"Error updating snapshot task "
                                              "with {arg}: {e}"))
                        # Return any interesting bits from err
                        result['status'] = err['status']
                result['changed'] = True
        else:
            # Task is not supposed to exist

            # XXX - Delete all matching tasks.
            if module.check_mode:
                result['msg'] = "Would have deleted snapshot task"
            else:
                try:
                    #
                    # Delete task.
                    #
                    err = mw.call("pool.snapshottask.delete",
                                  task_info['id'])
                except Exception as e:
                    module.fail_json(msg=f"Error deleting snapshot task: {e}")
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
