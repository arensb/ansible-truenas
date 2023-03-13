#!/usr/bin/python
__metaclass__ = type

# Create and manage users.

DOCUMENTATION='''
module: user
short_description: Manage user accounts
description:
  - Add, change, and delete user accounts.
options:
  append:
    description:
      - If true, the user will be added to the groups listed in C(groups),
        but not removed from any other groups.
      - If false, the user will be added to the groups listed in C(groups),
        and removed from any other groups.
    type: bool
    default: false
  comment:
    description:
      - The full name (I(GECOS) field) of the user.
    type: str
    default: ""
  create_group:
    description:
      - If true, create a new group with the same name as the user.
      - If such a group already exists, it is used and no new group is
        created.
    type: bool
    default: true
  delete_group:
    description:
      - If true, delete the user's primary group if it is not being used
        by any other users.
      - If false, the primary group stays, even if it is now empty.
      - Only used when deleting a user.
    type: bool
    default: true
  group:
    description:
      - The name of the user's primary group.
      - Required unless C(create_group) is true.
    type: str
  groups:
    description:
      - List of additional groups user will be added to.
      - If C(append) is true, the user will be added to all of the groups
        listed here.
      - If C(append) is false, then in addition, the user will be removed
        from all other groups (except the primary).
    type: list
  home:
    description:
      - User's home directory.
      - Note that TrueNAS has restrictions on what this can be. As of this
        writing, the home directory has to begin with "/tmp", or be
        "/nonexistent".
      - Note that if you create a user with home directory C("/nonexistent"),
        then later change it to a real directory, that directory will not
        be populated with dot files.
  name:
    description:
      - Name of the user to manage.
    type: str
    required: true
    aliases: [ user ]
  password:
    description:
      - User's password, as a crypted string.
      - Required unless C(password_disabled) is true.
      - Note: Currently there is no way to check whether the password
        needs to be changed, so this is used only when the user is created.
    type: str
  password_disabled:
    description:
      - If true, the user's password is disabled.
      - They can still log in through other methods (e.g., ssh key).
      - This is not a flag: if you set C(password_disabled=true) on a user,
        the password field in C(/etc/master.passwd) is set to C(*), so
        if you set C(password_disabled=false) again, they won't be able to
        log in with their old password.
      - If you need that functionality, do something like prepend "*LOCK*"
        to the crypt string when locking a user, then remove it when
        unlocking.
    type: bool
    default: false
  shell:
    description:
      - User's shell.
      - Must be one of the allowed shells from C(/etc/shells).
    type: str
  ssh_authorized_keys:
    description:
      - List of ssh public keys to put in the user's C(.ssh/authorized_keys)
        file.
    type: list of str
    aliases: [ pubkeys ]
  state:
    description:
      - Whether the user should exist or not.
    type: str
    choices: [ absent, present ]
    default: present
  sudo:
    description:
      - Whether the user is allowed to sudo (see also C(sudo_nopasswd) and
        C(sudo_commands)).
      - Note: this defaults to false. So if you create a user with
        C(sudo: yes), then comment out that line, the user will be removed
        from sudo.
    type: bool
    default: false
  sudo_nopasswd:
    description:
      - Allows user to sudo without a password.
    type: bool
    default: false
  sudo_commands:
    description:
      - List of commands the user is allowed to execute using C(sudo).
      - Each command must use an absolute path.
      - Commands may include options, e.g., C("/bin/ls -l").
    type: list of strings
    default: []
  uid:
    description:
      - Set the I(UID) of the user.
      - If the I(IUID) is already taken, this will create a second user with
        the same I(UID).
    type: int
'''

EXAMPLES = '''
XXX
- name: Create an ordinary user and their group
  ooblick.truenas.user:
    name: bob
    comment: "Bob the User"
    create_group: yes
    password: "<encrypted password string>"

- name: Create an ordinary user and put them into an existing group
  ooblick.truenas.user:
    name: bob
    comment: "Bob the User"
    group: users
    password: "<encrypted string>"

- name: Create a user without a working password
  ooblick.truenas.user:
    name: bob
    comment: "Bob the User"
    group: bobsgroup
    password_disabled: yes

- name: Delete a user
  ooblick.truenas.user:
    name: bob
    state: absent

- name: Delete a user, but keep their primary group, even if it's now empty.
  ooblick.truenas.user:
    name: bob
    state: absent
    delete_group: no
'''

# XXX - Return the UID of new user.
RETURN = '''
'''

from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible_collections.ooblick.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW

def main():
    # user.create() arguments:
    # x uid (int)
    # x username (str)
    # x group(int) - Required if create_group is false.
    # x create_group(bool)
    # x home(str)
    # - home_mode(str)
    # x shell(str) - Choose from user.shell_choices() (reads /etc/shells)
    # x full_name(str)
    # - email(str|null?)
    # ~ password(str) - Required if password_disabled is false
    # x password_disabled(bool)
    # - locked(bool)
    # - microsoft_account(bool)
    # - smb(bool) - Does user have access to SMB shares?
    # x sudo(bool)
    # x sudo_nopasswd(bool)
    # x sudo_commands(bool)
    # x sshpubkey(str|null?)
    # x groups(list)
    # - attributes(obj) - Arbitrary user information
    module = AnsibleModule(
        argument_spec=dict(
            # TrueNAS user.create arguments:
            uid=dict(type='int'),
            name=dict(type='str', required=True, aliases=['user']),

            # I'm not sure what the sensible default here is. I think
            # it's True, because builtin.user runs 'useradd' (on
            # Linux), and that creates a new group by default. So does
            # 'adduser' on FreeBSD. It also simplifies the playbook:
            # you can just have
            #   - user:
            #       name: bob
            # and something sensible will happen.
            create_group=dict(type='bool', default=True),

            password=dict(type='str', default='', no_log=True),

            # We set no_log explicitly to False, because otherwise
            # module_utils.basic sees "password" in the name and gets
            # worried.
            password_disabled=dict(type='bool', default=False, no_log=False),

            # XXX - There should probably be an option saying whether
            # or not to allow other keys in .ssh/authorized_keys, the
            # same way that 'append' says whether or not to allow
            # additional groups.
            ssh_authorized_keys=dict(type='list', elements='str',
                                     aliases=['pubkeys']),

            groups=dict(type='list'),
            home=dict(type='path'),
            # XXX - remove: delete home directory. builtin.user allows
            # doing this.

            sudo=dict(type='bool', default=False),
            sudo_nopasswd=dict(type='bool', default=False,),
            sudo_commands=dict(type='list',
                               elements='str'),

            # I think the way builtin.user works is, if you delete a
            # user without 'force: yes', the old home directory sticks
            # around.
            #
            # On TrueNAS, it doesn't look as though there's any way in
            # the GUI to delete a directory, so this is something that
            # needs to be done on the host (rm -rf ~bob), not through
            # middleware.
            #
            # see 'subversion' for an example of running a command.
            #
            # XXX - What if the user home directory is a zfs volume?
            # Then the user didn't create it through this interface,
            # and is responsible for cleaning it up.

            # XXX - move_home

            # From builtin.user module
            # x name(str)
            # x uid(int)
            # x comment(str) - GECOS
            comment=dict(type='str'),
            # - hidden(bool)
            # - non_unique(bool)
            # - seuser(str) - SELinux user type
            # - group(str) - primary group name
            group=dict(type='str'),
            # x groups(list) - List of group names
            # x append(bool) - whether to add to or set group list
            append=dict(type='bool', default=False),
            # x shell(str)
            shell=dict(type='str'),
            # x home(path)
            # - skeleton(path) - skeleton directory
            # ~ password(str) - crypted password
            # x state(absent, present)
            state=dict(type='str', default='present',
                       choices=['absent', 'present']),

            delete_group=dict(type='bool', default=True)
            # - create_home(bool)
            # - move_home(bool)
            # - system(bool) - system account, whatever that means
            # - force(bool) - Force removing user and dirs
            # - remove(bool) - When removing user, remove directories as well.
            # - login_class(str)
            # - generate_ssh_key(bool)
            # - ssh_key_bits(int)
            # - ssh_key_type(str) - default "rsa"
            # - ssh_key_file(path) - relative to home directory
            # - ssh_key_comment(str)
            # - ssh_key_passphrase(str)
            # - update_password(always, on_create)
            # - expires(float) - expiry time in epoch
            # - password_lock(bool) - Prevent logging in with password
            # - local(bool) - Local account, not AD or NIS.
            # - profile(str) - Solaris
            # - authorization(str) - Solaris
            # - role(str) - Solaris
        ),
        supports_check_mode=True,
        required_if=[
            ['password_disabled', False, ['password']]
        ]
    )

    result = dict(
        changed=False,
        msg=''
    )

    module.debug("Inside ooblick.truenas.user")

    mw = MW()

    # Assign variables from properties, for convenience
    uid = module.params['uid']
    username = module.params['name']
    password = module.params['password']
    password_disabled = module.params['password_disabled']
    group = module.params['group']
    create_group = module.params['create_group']
    groups = module.params['groups']
    append = module.params['append']
    home = module.params['home']
    comment = module.params['comment']
    state = module.params['state']
    delete_group = module.params['delete_group']
    sudo = module.params['sudo']
    sudo_nopasswd = module.params['sudo_nopasswd']
    sudo_commands = module.params['sudo_commands']
    ssh_authorized_keys = module.params['ssh_authorized_keys']
    shell = module.params['shell']

    # Look up the user.
    # Note that
    #   user.query [["username","=","ansible"]]
    # returns a lot more detail than
    #   user.get_user_obj {"username":"ansible"}
    # I suspect that get_user_obj() just looks up an entry in
    # /etc/passwd, while query() has a more generalized notion of what
    # a user is.
    try:
        user_info = mw.call("user.query",
                            [["username", "=", username]])
        # user.query() returns an array of results, but the query
        # above can only return 0 or 1 results.
        if len(user_info) == 0:
            # No such user
            user_info = None
        else:
            # User exists
            user_info = user_info[0]
    except Exception as e:
        module.fail_json(msg=f"Error looking up user {username}: {e}")

    # # XXX - Mostly for debugging:
    # result['user_info'] = user_info

    # First, check whether the user even exists.
    if user_info is None:
        # User doesn't exist

        if state == 'present':
            # User is supposed to exist, so create it.

            # Collect arguments to pass to user.create()
            arg = {
                "username": username,

                # Either password_disabled == True, or password must be
                # supplied.
                "password": password,
                "password_disabled": password_disabled,
            }

            # Easy cases first
            if comment is None:
                arg['full_name'] = ""
            else:
                arg['full_name'] = comment

            if uid is not None:
                arg['uid'] = uid

            if sudo is not None:
                arg['sudo'] = sudo

            if sudo_nopasswd is not None:
                arg['sudo_nopasswd'] = sudo_nopasswd

            if sudo_commands is not None:
                arg['sudo_commands'] = sudo_commands

            if shell is not None:
                arg['shell'] = shell

            # XXX - Looks like there's a bug in TrueNAS: if you
            # specify a home directory but no uid, it tries to chown
            # the new directory to the user's uid, but the uid
            # evidently hasn't been assigned yet.
            #
            # It works in the GUI because it fills the UID in for you.
            # And it works when home=/nonexistent because there's
            # nothing to chown.
            if home is not None:
                # XXX - Ought to have a variable or fact saying that
                # this is a problem, and to work around it.
                if uid is None:
                    try:
                        next_uid = mw.call("user.get_next_uid")
                    except Exception as e:
                        module.fail_json(msg=f"Error getting next available UID: {e}")
                    arg['uid'] = next_uid

                    result['uid'] = next_uid    # XXX - For debugging

                arg['home'] = home

            if ssh_authorized_keys is not None:
                arg['sshpubkey'] = "\n".join(ssh_authorized_keys)+"\n"

            # Look up the primary group. user.create() requires
            # a group number (not a GID!), but for compatibility with
            # the Ansible builtin.user module, we want to be able to
            # use a string for "group". So we need to look the group
            # up by name.
            if create_group:
                arg['group_create'] = True
            else:
                try:
                    group_info = mw.call("group.query",
                                         [["group", "=", group]])
                except Exception as e:
                    module.fail_json(msg=f"Error looking up group {group}: {e}")

                if len(group_info) == 0:
                    # No such group.
                    # If we got here, presumably it's because a primary
                    # group was set through 'group', but 'create_group'
                    # was not set.
                    group_info = None
                else:
                    group_info = group_info[0]
                    arg['group'] = group_info['id']

            if groups is not None and len(groups) > 0:
                # Look up the groups in the list. Get their IDs.
                # Add argument arg['groups'] with the list of IDs.
                try:
                    grouplist_info = mw.call("group.query",
                                             [["group", "in", groups]])
                except Exception as e:
                    module.fail_json(msg=f"Error looking up groups: {e}")

                # Get the IDs
                arg['groups'] = [g['id'] for g in grouplist_info]

            if module.check_mode:
                result['msg'] = f"Would have created user {username} with {arg}"
            else:
                #
                # Create new user
                #
                try:
                    err = mw.call("user.create", arg)
                    result['msg'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating user {username}: {e}")

                # user.create() only returns the new user ID, but
                # return that.
                result['user_id'] = err

            result['changed'] = True

        else:
            # User is not supposed to exist.
            # All is well
            result['changed'] = False
    else:
        # User exists
        if state == 'present':
            # User is supposed to exist

            # Make list of differences between what is and what should
            # be.

            # user.query() output:
            # [
            #   {
            #     "id": 37,
            #     "uid": 1001,
            #     "username": "arnie",
            #     "unixhash": "*",
            #     "smbhash": "*",
            #     "home": "/nonexistent",
            #     "shell": "/bin/csh",
            #     "full_name": "",
            #     "builtin": false,
            #     "smb": true,
            #     "password_disabled": true,
            #     "locked": false,
            #     "sudo": false,
            #     "sudo_nopasswd": false,
            #     "sudo_commands": [],
            #     "microsoft_account": false,
            #     "attributes": {},
            #     "email": null,
            #     "group": {
            #       "id": 47,
            #       "bsdgrp_gid": 1001,
            #       "bsdgrp_group": "arnie",
            #       "bsdgrp_builtin": false,
            #       "bsdgrp_sudo": false,
            #       "bsdgrp_sudo_nopasswd": false,
            #       "bsdgrp_sudo_commands": [],
            #       "bsdgrp_smb": false
            #     },
            #     "groups": [
            #       43
            #     ],
            #     "sshpubkey": null,
            #     "local": true,
            #     "id_type_both": false
            #   }
            # ]

            arg = {}

            # elements in argument_spec:
            # - name (username)
            # - password (crypt)
            # - password_disabled
            # - comment
            # - group (primary group)

            if uid is not None and user_info['uid'] != uid:
                arg['uid'] = uid

            # XXX - There's probably a way to get user.query() to
            # return the current crypt string of a user,but I don't
            # know what that is. Until then, we can't check whether
            # the password needs to be changed.

            # if password is not None and user_info['password'] != password:
            #     arg['password'] = password

            if user_info['password_disabled'] != password_disabled:
                arg['password_disabled'] = password_disabled

            if comment is not None and user_info['full_name'] != comment:
                arg['full_name'] = comment

            if shell is not None and user_info['shell'] != shell:
                arg['shell'] = shell

            if home is not None:
                # If the username has also changed, need to update the
                # home directory as well.

                # XXX - Maybe we want to just mandate that the 'home'
                # option has to be the full home directory.

                new_username = arg['username'] if 'username' in arg \
                    else user_info['username']

                if user_info['home'] == home:
                    # The home directory is already set correctly.
                    # Nothing to do here.
                    pass
                elif user_info['home'] == f"{home}/{new_username}":
                    # The user's existing home directory is the
                    # specified 'option' path, followed by the
                    # (possibly new) username.
                    #
                    # All is as it should be. Nothing to do here.
                    pass
                else:
                    # Something has changed
                    arg['home'] = home

            if sudo is not None and user_info['sudo'] != sudo:
                arg['sudo'] = sudo

            if sudo_nopasswd is not None and \
               user_info['sudo_nopasswd'] != sudo_nopasswd:
                arg['sudo_nopasswd'] = sudo_nopasswd

            # Let's perform set comparison, because it doesn't matter
            # in which order the sudo commands are listed.
            if sudo_commands is None:
                # sudo_commands should be empty
                if user_info['sudo_commands'] != []:
                    arg['sudo_commands'] = []
            else:
                if set(user_info['sudo_commands']) != set(sudo_commands):
                    arg['sudo_commands'] = sudo_commands

            # XXX - Figure out whether home directory permissions need to be
            # set. This turns out to be more difficult than expected.

            # Figure out whether any of the ssh keys need to be updated.
            # Use sets, because order doesn't matter.
            if ssh_authorized_keys is not None:
                # Get the old keys
                if user_info['sshpubkey'] is None:
                    # Empty set
                    old_keys = set()
                else:
                    old_keys = set(user_info['sshpubkey'].rstrip().split("\n"))

                want_keys = set(ssh_authorized_keys)

                if old_keys != want_keys:
                    # user.update() expects a string, not a list.
                    # And don't forget the \n at the end of the file.
                    arg['sshpubkey'] = "\n".join(ssh_authorized_keys)+"\n"

            # Check primary group.
            if group is not None and user_info['group']['bsdgrp_group'] != group:
                # Look up primary group information.
                try:
                    grp = mw.call("group.query",
                                  [["group", "=", group]])
                except Exception as e:
                    module.fail_json(msg=f"Error looking up group {group}: {e}")

                # As above, 'grp' is an array of 0 or 1 elements.
                if len(grp) == 0:
                    # The lookup was successful, and successfully
                    # found that there's no such group.
                    module.fail_json(msg=f"No such group: {group}")
                arg['group'] = grp[0]['id']

            # XXX - Add 'groups', 'append'
            # user_info['groups'] is a list of ints. Each one is a group
            # to look up.
            # I think the easy way to do this is:
            # group.query [["id", "in", [1, 2, 20, 605]]]
            #
            # if append is true:
            #   check the groups in 'groups', and make sure
            #   user is in all of them.
            # else:
            #   Same, but make sure user is not in any other groups.

            # XXX - Figure out which groups the user should be in. The
            # "groups" option to user.update() specifies the full set
            # of groups (aside from the primary group) that the user
            # will be in: the user will be removed from any groups not
            # in that set. So we need to figure out what that set is.
            #
            # If groups is None, then the caller doesn't care what the
            # groups are, so leave them alone. Don't even set the
            # 'arg' option.
            #
            # Else, if append is False, look up the groups specified in
            # 'groups', and set arg[groups] to that.
            #
            # Else, look up the existing groups on the NAS (nas_groups).
            # Do a set addition: want_groups = groups + nas_groups
            # if want_groups != nas_groups, then something has changed, and
            # add arg[groups]

            # XXX - 'builtin_users' is a special case: when a user is
            # given Samba access (through the user.create(smb=true)
            # option), they're automatically added to 'builtin_users'.
            # https://www.truenas.com/community/threads/who-is-group.106782/
            #
            # However, removing SMB from the user does not remove them
            # from builtin_users.

            # if groups is not None and len(groups) > 0:
            #     # XXX - Look up the groups in the list. Get their IDs.
            #     # Add argument arg['groups'] with the list of IDs.
            #     try:
            #         grouplist_info = mw.call("group.query",
            #                                  [["group", "in", groups]])
            #     except Exception as e:
            #         module.fail_json(msg=f"Error looking up groups: {e}")

            #     # # Get the IDs
            #     # arg['groups'] = [g['id'] for g in grouplist_info]

            #     # XXX - Get difference between user groups and desired
            #     # groups.

            # Do we care what groups the user is in?
            if groups is not None:
                # Yes, we care.

                # XXX - Look up the IDs of the groups in 'groups'.
                if len(groups) == 0:
                    grouplist_info = []
                else:
                    try:
                        grouplist_info = mw.call("group.query",
                                                 [["group", "in", groups]])
                    except Exception as e:
                        module.fail_json(msg=f"Error looking up groups {groups}: {e}")

                # Get the set (not list) of groups the user is in on the
                # NAS.
                nas_groupset = set(user_info['groups'])
                # XXX
                result['nas_groupset'] = nas_groupset

                # Get the set (not list) of group IDs specified in the
                # 'groups' option:
                want_groupset = { g['id'] for g in grouplist_info }
                result['want_groupset'] = want_groupset

                if append:
                    # User should be in both sets of groups.
                    final_groupset = want_groupset.union(nas_groupset)
                    pass
                else:
                    # User should be in the groups specified by 'groups',
                    # and no others.
                    final_groupset = want_groupset

                result['final_groupset'] = final_groupset
                if final_groupset != nas_groupset:
                    arg['groups'] = list(final_groupset)

            # XXX - If there are any, user.update()
            if len(arg) == 0:
                # No changes
                result['changed'] = False
            else:
                #
                # Update user.
                #
                if module.check_mode:
                    result['msg'] = f"Would have updated user {username}: {arg}"
                else:
                    try:
                        err = mw.call("user.update",
                                      user_info['id'],
                                      arg)
                    except Exception as e:
                        module.fail_json(msg=f"Error updating user {username} with {arg}: {e}")
                    # user.update() doesn't return anything
                    # interesting: just the numeric user ID.
                    # Otherwise, we'd want to include that in
                    # 'result'.
                result['changed'] = True

        else:
            # User is not supposed to exist

            if module.check_mode:
                result['msg'] = f"Would have deleted user {username}"
            else:
                try:
                    #
                    # Delete user.
                    #
                    err = mw.call("user.delete",
                                  user_info['id'],
                                  {"delete_group": delete_group})
                except Exception as e:
                    module.fail_json(msg=f"Error deleting user {username}: {e}")
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
