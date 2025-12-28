#!/usr/bin/python
# -*- coding: utf-8 -*-
__metaclass__ = type

# Create and manage users.

# SMB and users with disabled passwords:
#
# Under TrueNAS SCALE, a user with SMB enabled also needs to have a
# password. TrueNAS CORE allows you to create a user with disabled
# password, but also with SMB turned on.
#
# I think the best way to deal with this is simply to document the
# behavior.

DOCUMENTATION = '''
---
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
  append_pubkeys:
    description:
      - If true, the keys specified in C(ssh_authorized_keys) will be added
        to the user's C(~/.ssh/authorized_keys), but any others that might
        be there will not be removed.
      - If false, any keys not explicitly listed in C(ssh_authorized_keys)
        will be removed from the user's C(~/.ssh/authorized_keys).
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
  email:
    description:
      - User's email address, in the form I(user@dom.ain).
    type: str
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
        writing, the home directory has to begin with "/mnt", or be
        "/nonexistent".
      - Note that if you create a user with home directory C("/nonexistent"),
        then later change it to a real directory, that directory will not
        be populated with dot files.
      - "Note: If you create an account with a home directory that does not
        end in the username (e.g., if C(name: bob) and
        C(home: /mnt/pool0/homes)), TrueNAS will append the username to
        form the real home directory (C(/mnt/pool0/homes/bob), in this
        example). This is not recommended. It is better to use the full
        home directory, ending with the username."
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
      - "Note: Currently there is no way to check whether the password
        needs to be changed, so this is used only when the user is created."
    type: str
  password_disabled:
    description:
      - If true, the user's password is disabled.
      - They can still log in through other methods (e.g., ssh key).
      - "This is not a flag: if you set C(password_disabled=true) on a user,
        the password field in C(/etc/master.passwd) is set to C(*), so
        if you set C(password_disabled=false) again, they won't be able to
        log in with their old password."
      - If you need that functionality, do something like prepend "*LOCK*"
        to the crypt string when locking a user, then remove it when
        unlocking.
      - "Note that under TrueNAS SCALE, a user with C(password_disabled)
        may not use SMB, so be sure to set C(smb: false)."
    type: bool
    default: false
  shell:
    description:
      - User's shell.
      - Must be one of the allowed shells from C(/etc/shells).
    type: str
  smb:
    description:
      - Specifies whether user should have access to SMB shares.
      - Under TrueNAS SCALE, a user with C(smb) enabled may not have
        their password disabled.
    type: bool
    default: true
  ssh_authorized_keys:
    description:
      - List of ssh public keys to put in the user's C(.ssh/authorized_keys)
        file.
    type: list
    elements: str
    aliases: [ pubkeys ]
  state:
    description:
      - Whether the user should exist or not.
    type: str
    choices: [ absent, present ]
    default: present
  sudo:
    description:
      - Deprecated. Use I(sudo_commands) and/or I(sudo_commands_nopasswd)
        instead.
      - Whether the user is allowed to sudo (see also I(sudo_nopasswd) and
        I(sudo_commands)).
      - "Note: this defaults to false. So if you create a user with
        I(sudo: yes), then comment out that line, the user will be removed
        from sudo."
    type: bool
  sudo_nopasswd:
    description:
      - Deprecated. Use I(sudo_commands_nopasswd) instead.
      - Allows user to sudo without a password.
    type: bool
    default: false
  sudo_commands:
    description:
      - List of commands the user is allowed to execute using C(sudo).
      - Each command must use an absolute path, except for the special
        value "ALL", which allows executing any command.
      - Commands may include options, e.g., C("/bin/ls -l").
      - In TrueNAS CORE, and in older versions of SCALE, only one of
        I(sudo_commands) and I(sudo_commands_nopasswd) may be specified.
    type: list
    elements: str
    default: []
  sudo_commands_nopasswd:
    description:
      - List of commands the user is allowed to execute using C(sudo),
        without having to give a password.
      - Each command must use an absolute path, except for the special
        value "ALL", which allows executing any command.
      - Commands may include options, e.g., C("/bin/ls -l").
      - In TrueNAS CORE, and in older versions of SCALE, only one of
        I(sudo_commands) and I(sudo_commands_nopasswd) may be specified.
    type: list
    elements: str
    default: []
  uid:
    description:
      - Set the I(UID) of the user.
      - If the I(IUID) is already taken, this will create a second user with
        the same I(UID).
    type: int
version_added: 0.1.0
'''

EXAMPLES = '''
- name: Create an ordinary user and their group
  arensb.truenas.user:
    name: bob
    comment: "Bob the User"
    create_group: yes
    password: "<encrypted password string>"

- name: Create an ordinary user and put them into an existing group
  arensb.truenas.user:
    name: bob
    comment: "Bob the User"
    group: users
    password: "<encrypted string>"

- name: Create a user without a working password
  arensb.truenas.user:
    name: bob
    comment: "Bob the User"
    group: bobsgroup
    password_disabled: yes

- name: Delete a user
  arensb.truenas.user:
    name: bob
    state: absent

- name: Delete a user, but keep their primary group, even if it's now empty.
  arensb.truenas.user:
    name: bob
    state: absent
    delete_group: no
'''

RETURN = '''
user_id:
  description:
    - The ID of a newly-created user.
    - This is not the I(uid) as found in C(/etc/passwd), but the database
      ID.
  type: int
'''

import sys
from ansible.module_utils.basic import AnsibleModule
from ..module_utils.middleware import MiddleWare as MW
from ..module_utils import setup
# For parsing version numbers
from packaging import version

def main():
    # Figure out which version of TrueNAS we're running, and thus how
    # to call middlewared.
    try:
        tn_version = setup.get_tn_version()
    except Exception as e:
        # Normally we'd module.exit_json(), but we don't have a module yet.
        print(f'{{"failed":true, "msg": "Error getting TrueNAS version: {e}"}}')
        sys.exit(1)

    # The sudo api changed in several branches, so in the test below,
    # we need an overly complex three-way test to figure out which API
    # to use.
    #
    # Commit                                     Version
    # 2934f3844cc844202dafa1cc0145eb65f456c4bc - 12.12.3
    # 01cd04590008262799753b316e6a56e4b32c84ca - 22.12.1
    # ef76438b9f58911966a63a9df802a6d347a48bba - 23.10
    #
    # And when CORE is updates, we'll need to add another branch.

    # Having an 'old_sudo' variable will make it easier to get rid of
    # this code when the world has upgraded.
    old_sudo_api = True
    if tn_version['name'] == "TrueNAS" and \
       tn_version['type'] in {"SCALE", "COMMUNITY_EDITION"} and \
       \
       (tn_version['version'] >= version.parse("12.12") and
        tn_version['version'] < version.parse("13")) \
       or \
       (tn_version['version'] >= version.parse("22.12.1") and
        tn_version['version'] < version.parse("23")) \
       or \
       tn_version['version'] >= version.parse("23.10"):
        old_sudo_api = False

    # In order to deal with the two 'user' APIs we'll define two
    # Ansible APIs. Both prefer to use 'sudo_commands' and
    # 'sudo_commands_nopasswd' to specify sudo access, but with
    # compatibility tweaks.

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
    # x smb(bool) - Does user have access to SMB shares?
    # x sudo(bool)
    # x sudo_nopasswd(bool)
    # x sudo_commands(bool)
    # x sshpubkey(str|null?)
    # x groups(list)
    # - attributes(obj) - Arbitrary user information

    mod_argument_spec = dict(
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
            password_disabled=dict(type='bool', no_log=False),

            # XXX - There should probably be an option saying whether
            # or not to allow other keys in .ssh/authorized_keys, the
            # same way that 'append' says whether or not to allow
            # additional groups.
            ssh_authorized_keys=dict(type='list', elements='str',
                                     aliases=['pubkeys']),
            append_pubkeys=dict(type='bool', default=False),

            groups=dict(type='list'),
            home=dict(type='path'),
            # XXX - remove: delete home directory. builtin.user allows
            # doing this.

            smb=dict(type='bool', default=True),

            sudo_commands=dict(type='list',
                               elements='str'),
            sudo_commands_nopasswd=dict(type='list',
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
            email=dict(type='str'),
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
        )
    mod_mutually_exclusive = []
    mod_required_if = [
        ['password_disabled', False, ['password']],
        ]

    # Make adjustments for systems using the old API.
    if old_sudo_api:
        mod_argument_spec['sudo'] = dict(type='bool')
        mod_argument_spec['sudo_nopasswd'] = dict(type='bool')
        mod_mutually_exclusive.append(['sudo_commands',
                                       'sudo_commands_nopasswd'])

    module = AnsibleModule(
        argument_spec=mod_argument_spec,
        supports_check_mode=True,
        mutually_exclusive=mod_mutually_exclusive,
        required_if=mod_required_if
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW.client()

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
    email = module.params['email']
    state = module.params['state']
    delete_group = module.params['delete_group']
    smb = module.params['smb']
    sudo = module.params['sudo'] \
        if 'sudo' in module.params else None
    sudo_nopasswd = module.params['sudo_nopasswd'] \
        if 'sudo_nopasswd' in module.params else None
    sudo_commands = module.params['sudo_commands']
    sudo_commands_nopasswd = module.params['sudo_commands_nopasswd']
    ssh_authorized_keys = module.params['ssh_authorized_keys']
    append_pubkeys = module.params['append_pubkeys']
    shell = module.params['shell']

    # Warn user against using deprecated options.
    if sudo is not None:
        # Only with old sudo
        module.warn("The 'sudo' option is deprecated. Please use "
                    "'sudo_commands' and 'sudo_commands_nopasswd' instead.")

    if sudo_nopasswd is not None:
        # Only with old sudo
        module.warn("The 'sudo_nopasswd' option is deprecated. Please use "
                    "'sudo_commands' and 'sudo_commands_nopasswd' instead.")

    # If either 'sudo' or 'sudo_nopasswd' was specified, let's assume
    # that the caller is using old-style syntax. Otherwise, we'll let
    # the contents of 'sudo_commands' and 'sudo_commands_nopasswd'
    # determine the other middleware options.
    old_sudo_call = False
    if old_sudo_api and \
       (sudo is not None or sudo_nopasswd is not None):
        old_sudo_call = True

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

    # First, check whether the user even exists.
    if user_info is None:
        # User doesn't exist

        if state == 'present':
            # User is supposed to exist, so create it.

            # Collect arguments to pass to user.create()
            arg = {
                "username": username,

            }

            # Easy cases first
            if password_disabled is not None:
                arg['password_disabled'] = password_disabled

                # SCALE at least doesn't like you passing in an empty
                # password, even if password_disabled has been
                # specified. So let's make sure that a password is
                # wanted, first.
                if not password_disabled:
                    arg['password'] = password

            if comment is None:
                arg['full_name'] = ""
            else:
                arg['full_name'] = comment

            if email is not None:
                arg['email'] = email

            if uid is not None:
                arg['uid'] = uid

            if smb is not None:
                arg['smb'] = smb

            if old_sudo_call:
                # 'old_sudo_call' isn't set to True until we know that
                # middleware uses the old sudo API. So by the time we
                # get to this section, we know that the host is using
                # the old middleware API.

                if sudo is not None:
                    arg['sudo'] = sudo
                if sudo_nopasswd is not None:
                    arg['sudo_nopasswd'] = sudo_nopasswd
                if sudo_commands is not None:
                    arg['sudo_commands'] = sudo_commands
            elif old_sudo_api:
                # New-style call, but old middleware API.

                if sudo_commands is None:
                    if sudo_commands_nopasswd is None:
                        # Caller has no opinion about sudoing.
                        pass
                    else:
                        # sudo_commands == None
                        # sudo_commands_nopasswd == [...]
                        arg['sudo'] = True
                        arg['sudo_nopasswd'] = True
                        arg['sudo_commands'] = \
                            [] if 'ALL' in sudo_commands_nopasswd \
                            else sudo_commands_nopasswd
                else:
                    if sudo_commands_nopasswd is None:
                        # sudo_commands == [...]
                        # sudo_commands_nopasswd == None
                        arg['sudo'] = True
                        arg['sudo_nopasswd'] = False
                        arg['sudo_commands'] = \
                            [] if 'ALL' in sudo_commands \
                            else sudo_commands
                    else:
                        # sudo_commands == [...]
                        # sudo_commands_nopasswd == [...]
                        # Can't happen: error.
                        pass
            else:
                # New-style call, and new-style middleware API.
                if sudo_commands is not None:
                    arg['sudo_commands'] = sudo_commands

                if sudo_commands_nopasswd is not None:
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
                        module.fail_json(
                            msg=f"Error getting next available UID: {e}"
                        )
                    arg['uid'] = next_uid

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
            result['invocation'] = arg

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

            if password_disabled is not None and \
               user_info['password_disabled'] != password_disabled:
                arg['password_disabled'] = password_disabled

            if comment is not None and user_info['full_name'] != comment:
                arg['full_name'] = comment

            if email is not None and user_info['email'] != email:
                arg['email'] = email

            if shell is not None and user_info['shell'] != shell:
                arg['shell'] = shell

            if smb is not None and user_info['smb'] != smb:
                arg['smb'] = smb

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

            if old_sudo_call:
                # By the time we get to this section, we know that the
                # host uses the old middleware sudo API.

                if sudo is not None and \
                   user_info['sudo'] != sudo:
                    arg['sudo'] = sudo

                if sudo_nopasswd is not None and \
                   user_info['sudo_nopasswd'] != sudo_nopasswd:
                    arg['sudo_nopasswd'] = sudo_nopasswd

                if sudo_commands is not None and \
                   user_info['sudo_commands'] != sudo_commands:
                    arg['sudo_commands'] = sudo_commands

            elif old_sudo_api:
                # New-style call, but old middleware API.

                want_sudo = None
                want_sudo_nopasswd = None
                want_sudo_commands = None

                if sudo_commands is None:
                    if sudo_commands_nopasswd is None:
                        # sudo_commands == None
                        # sudo_commands_nopasswd == None
                        # Caller has no opinion on sudoing.
                        pass
                    else:
                        # sudo_commands == None
                        # sudo_commands_nopasswd == [...]
                        want_sudo = True
                        want_sudo_nopasswd = True
                        want_sudo_commands = \
                            [] if 'ALL' in sudo_commands_nopasswd \
                            else sudo_commands_nopasswd
                else:
                    if sudo_commands_nopasswd is None:
                        # sudo_commands == [...]
                        # sudo_commands_nopasswd == None
                        want_sudo = True
                        want_sudo_nopasswd = False
                        want_sudo_commands = \
                            [] if 'ALL' in sudo_commands \
                            else sudo_commands
                    else:
                        # sudo_commands == [...]
                        # sudo_commands_nopasswd == [...]
                        # Can't happen, since the two are mutually
                        # exclusive.
                        pass

                if want_sudo is not None and \
                   user_info['sudo'] != want_sudo:
                    arg['sudo'] = want_sudo
                if want_sudo_nopasswd is not None and \
                   user_info['sudo_nopasswd'] != want_sudo_nopasswd:
                    arg['sudo_nopasswd'] = want_sudo_nopasswd
                if want_sudo_commands is not None and \
                   set(user_info['sudo_commands']) != set(want_sudo_commands):
                    arg['sudo_commands'] = want_sudo_commands

            else:
                # New-style call, and new middleware API.

                # Let's perform set comparison, because it doesn't matter
                # in which order the sudo commands are listed.
                if sudo_commands is not None and \
                   set(user_info['sudo_commands']) != set(sudo_commands):
                    arg['sudo_commands'] = sudo_commands

                if sudo_commands_nopasswd is not None and \
                   set(user_info['sudo_commands_nopasswd']) != \
                       set(sudo_commands_nopasswd):
                    arg['sudo_commands_nopasswd'] = sudo_commands_nopasswd

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

                # Keys might have trailing whitespace, but that
                # doesn't make them unique.
                want_keys = set([k.rstrip() for k in ssh_authorized_keys])

                if append_pubkeys:
                    # See which keys need to be added to the user
                    new_keys = want_keys.difference(old_keys)

                    # This conditional here is so that, if there are
                    # no new keys to be added, we don't add an entry
                    # to 'arg', making this module report that there
                    # was a change.
                    if len(new_keys) != 0:
                        # Append any new keys to the end of the file.
                        arg['sshpubkey'] = \
                            "\n".join(old_keys.union(want_keys)) + "\n"

                elif old_keys != want_keys:
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
                want_groupset = {g['id'] for g in grouplist_info}
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

            # If there are changes, user.update()
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
                result['invocation'] = arg

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
