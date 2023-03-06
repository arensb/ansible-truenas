#!/usr/bin/python
__metaclass__ = type

# Create and manage groups.
#
# midclt call group.query '[["group","=","wheel"]]'
# midclt call group.query '[["gid","=",0]]'
# midclt call group.query '[["builtin","=",false]]'

from ansible.module_utils.basic import AnsibleModule, missing_required_lib

from ansible_collections.ooblick.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW

def main():
    module = AnsibleModule(
        argument_spec=dict(
            # gid(int)
            gid=dict(type='int'),
            # group name(str)
            name=dict(type='str', required=True),
            # sudo(bool)
            # sudo_nopasswd(bool)
            # smb(bool) - whether the group should be mapped onto an NT group.
            # users (list of uids)
            # local(bool) - what's this?
            # id_type_both(bool) - what's this?

            # From standard group module:
            # - gid(int)
            # - local(bool)
            # = name(str)
            # - non_unique(bool)
            non_unique=dict(type='bool', default=False),
            # - state(absent, *present)
            state=dict(type='str', default='present', choices=['absent', 'present'])
            # - system(bool)
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

    mw = MW()

    # Assign variables from properties, for convenience
    gid = module.params['gid']
    group = module.params['name']
    state = module.params['state']
    non_unique = module.params['non_unique']

    # XXX - Look up the group.
    try:
        err = mw.call("group.query",
                      [["group", "=", group]])
    except AnsibleModuleException as e:
        module.fail_json(msg=f"Error looking up group {group}: {e.stderr}")

    result['result'] = err

    # XXX - See what needs to be done.

    # XXX - If the group doesn't exist, try to create it.
    # group.create.

    if len(err) == 0:
        # The group doesn't exist
        # XXX
        if module.params['state'] == 'present':
            # XXX - The group is supposed to exist
            try:
                # XXX - Assemble arguments
                arg = {"name": group}
                if gid:
                    # GID is defined. Add to specification.
                    arg['gid'] = gid
                # XXX - smb
                # XXX - sudo
                # XXX - sudo_nopasswd
                # XXX - sudo_commands
                arg['allow_duplicate_gid'] = bool(non_unique)

                result['arg'] = arg
                if module.check_mode:
                    result['msg'] = "Would have tried to create group {group}"
                else:
                    err = mw.call("group.create", arg)
                    result['msg'] = err

            except Exception as e:
                module.fail_json(msg=f"Error creating group {group}: {e}")
            result['changed'] = True
        else:
            # The group isn't supposed to exist.
            result['changed'] = False

    else:
        # The group exists
        # XXX
        pass

    # XXX - If the group does exist, see how the existing one differs
    # from what's been specified. Put together a set of differences,
    # and submit a group.update(?) call.

    module.exit_json(**result)

### Main
if __name__ == "__main__":
    main()
