#!/usr/bin/python
# -*- coding: utf-8 -*-
__metaclass__ = type

# Create and manage groups.
#
# midclt call group.query '[["group","=","wheel"]]'
# midclt call group.query '[["gid","=",0]]'
# midclt call group.query '[["builtin","=",false]]'

DOCUMENTATION = '''
---
module: group
short_description: Manage groups
description:
  - Create, destroy, and manage groups on a TrueNAS host.
options:
  name:
    description:
      - Name of the group to manage.
    type: str
    required: true
  gid:
    description:
      - Optional I(GID) to set for the group
    type: int
  state:
    description:
      - Whether the group should be present or not.
    type: str
    choices: [ absent, present ]
    default: present
  non_unique:
    description:
      - Allow a non-unique I(GID) for the group.
      - If I(non_unique) is true, a I(GID) must be specified.
      - This is ignored starting with I(SCALE 25.04)
    type: bool
    default: no
seealso:
- module: ansible.builtin.group
author:
- Andrew Arensburger (@arensb)
notes:
- Supports C(check_mode)
version_added: 0.1.0
'''

EXAMPLES = '''
- name: Make sure group "mygroup" exists
  arensb.truenas.group:
    name: mygroup

- name: Make sure group "badgroup" is gone
  arensb.truenas.group:
    name: badgroup
    state: absent
'''

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.middleware import MiddleWare as MW
from ..module_utils.setup import get_tn_version
from packaging import version


def main():
    module = AnsibleModule(
        argument_spec=dict(
            gid=dict(type='int'),
            name=dict(type='str', required=True),

            # sudo(bool)
            # sudo_nopasswd(bool)

            # XXX - The sudo stuff here looks a lot like the sudo
            # stuff in the 'user' module. So most likely it's been
            # changed in TrueNAS SCALE as well. if so, go with a
            # new-style interface: use 'sudo_commands' and
            # 'sudo_commands_nopasswd' instead of 'sudo (bool)' and
            # 'sudo_nopasswd (bool)'

            # smb(bool) - whether the group should be mapped onto an NT group.

            # users (list of uids) I think it's more intuitive to
            # specify which groups a user shouldbe in, but if someone
            # has a use case for this, it can be added.

            # local(bool) - what's this?
            # id_type_both(bool) - what's this?
            # - system(bool)

            non_unique=dict(type='bool', default=False),
            state=dict(type='str', default='present',
                       choices=['absent', 'present'])
        ),
        supports_check_mode=True,
        required_if=[
            ['non_unique', True, ['gid']]
        ]
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW.client()

    try:
        tn_version = get_tn_version()
    except Exception as e:
        module.fail_json(msg=f"Error getting TrueNAS version: {e}")

    # Assign variables from properties, for convenience
    gid = module.params['gid']
    group = module.params['name']
    state = module.params['state']
    non_unique = module.params['non_unique']
    # TrueNAS scale versions starting with 25.04 throws an error if allow_duplicate_gid
    # is passed in
    TC_25_04 = version.parse("25.04")
    if tn_version['name'] == "TrueNAS" and \
        tn_version['type'] in {"SCALE", "COMMUNITY_EDITION"} and \
        tn_version['version'] >= TC_25_04:
        non_unique = None

    # Look up the group.
    # group.query returns an array of objects like:
    # {
    #    "builtin": false,
    #    "gid": 1000,
    #    "group": "mygroup",
    #    "id": 123,
    #    "id_type_both": false,
    #    "local": true,
    #    "smb": true,
    #    "sudo": false,
    #    "sudo_commands": [],
    #    "sudo_nopasswd": false,
    #    "users": [
    #        456
    #    ]
    # },
    try:
        group_info = mw.call("group.query",
                             [["group", "=", group]])
        # group_info is an array. We specified a "group=<name>"
        # filter, so we'll get either 0 or 1 elements back.
        if len(group_info) == 0:
            # No such group
            group_info = None
        else:
            # Group exists
            group_info = group_info[0]
    except Exception as e:
        module.fail_json(msg=f"Error looking up group {group}: {e.stderr}")

    # XXX - Mostly for debugging:
    result['group_info'] = group_info

    if group_info is None:
        # The group doesn't exist
        if state == 'present':
            # The group is supposed to exist

            # Assemble arguments
            arg = {"name": group}

            if gid is not None:
                # GID is defined. Add to specification.
                arg['gid'] = gid

            # XXX - smb

            # XXX - sudo

            # XXX - sudo_nopasswd

            # XXX - sudo_commands

            if non_unique is not None:
                arg['allow_duplicate_gid'] = non_unique

                result['arg'] = arg
            if module.check_mode:
                result['msg'] = f"Would have created group {group}"
            else:
                try:
                    err = mw.call("group.create", arg)

                    # XXX - Maybe rerun "group.info" and get fresh
                    # info? Or at least update group_info with what's
                    # currently in 'err'
                    result['msg'] = err
                except Exception as e:
                    module.fail_json(msg=f"Error creating group {group}: {e}")

                result['msg'] = err

            result['changed'] = True
        else:
            # The group isn't supposed to exist.
            result['changed'] = False

    else:
        # The group exists
        if state == 'present':
            # The group is supposed to exist.
            #
            # compare 'group_info' to the module parameters and see if
            # anything needs to change.

            # Build up arguments to pass to group.update.
            arg = {}

            # gid
            if gid is not None and group_info['gid'] != gid:
                arg['gid'] = gid

            # XXX - name - I don't think it makes sense to change
            # the group name, since that's the way Ansible
            # identifies it.

            # XXX - smb
            # XXX - sudo
            # XXX - sudo_nopasswd
            # XXX - sudo_commands [...]

            if len(arg) == 0:
                # Nothing to do
                result['changed'] = False
            else:
                # Something has changed.

                # allow_duplicate_gid is not a parameter like others.
                # It pertains not to the group, but to this operation.
                if non_unique is not None:
                    arg['allow_duplicate_gid'] = non_unique

                if module.check_mode:
                    result['msg'] = f"Would have updated group {group}: {arg}"
                else:
                    try:
                        err = mw.call("group.update",
                                      group_info['id'],
                                      arg)
                    except Exception as e:
                        # XXX
                        module.fail_json(msg=f"Error updating group {group}: {e}")
                result['changed'] = True
        else:
            # The group isn't supposed to exist.
            if module.check_mode:
                result['msg'] = "Would have deleted group {group}"
            else:
                # The id, here, is not the Unix GID. It's a unique
                # identifier in TrueNAS's own database. Two groups
                # with different names can have the same gid, but will
                # always have different id.

                # XXX - There's another optional parameter saying to
                # delete all users who have this as their primary
                # group. But that's dangerous, so let's not implement
                # it until needed.
                err = mw.call("group.delete",
                              group_info['id'],
                              )
                result['msg'] = err
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
