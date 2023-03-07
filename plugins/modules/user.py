#!/usr/bin/python
__metaclass__ = type

# Create and manage users.

DOCUMENTATION='''
XXX
options:
  name:
    description:
      - Name of the user to manage.
    type: str
    required: true
    aliases: [ user ]
  comment:
    description:
      - The full name (I(GECOS) field) of the user.
    type: str
    default: ""
  group:
    description:
      - The name of the user's primary group.
      - Required unless C(group_create) is true.
    type: str
  group_create:
    description:
      - If true, create a new group with the same name as the user.
      - If such a group already exists, it is used and no new group is
        created.
    type: bool
    default: False
  password:
    description:
      - User's password, as a crypted string.
      - Required unless C(password_disabled) is true.
    type: str
  password_disabled:
    description:
      - If true, the user's password is disabled.
      - They can still log in through other methods (e.g., ssh key).
    type: bool
    default: false
  state:
    description:
      - Whether the user shoujld exist or not.
    type: str
    choices: [ absent, present ]
    default: present
'''

EXAMPLES = '''
XXX
- name: Create an ordinary user and their group
  ooblick.truenas.user:
    name: bob
    comment: "Bob the User"
    group_create: yes
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
'''

from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible_collections.ooblick.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW

def main():
    module = AnsibleModule(
        argument_spec=dict(
            # TrueNAS user.create:
            # - uid(int) - If not supplied, use next one available
            # - username(str)
            name=dict(type='str', required=True, aliases=['user']),
            # - group(int) - Required if group_create is false.
            # - group_create(bool)

            # XXX - I'm not sure what the sensible default here is.
            group_create=dict(type='bool', default=False),

            # - home(str)
            # - home_mode(str)
            # - shell(str) - Choose from user.shell_choices() (reads /etc/shells)
            # - full_name(str)
            # - email(str|null?)
            # - password(str) - Required if password_disabled is false
            password=dict(type='str', default='', no_log=True),
            # - password_disabled(bool)
            password_disabled=dict(type='bool', default=False),
            # - locked(bool)
            # - microsoft_account(bool)
            # - smb(bool) - Does user have access to SMB shares?
            # - sudo(bool)
            # - sudo_nopasswd(bool)
            # - sudo_commands(bool)
            # - sshpubkey(str|null?)
            # - groups(list)
            # - attributes(obj) - Arbitrary user information

            # From builtin.user module
            # - name(str)
            # - uid(int)
            # - comment(str) - GECOS
            comment=dict(type='str', default=''),
            # - hidden(bool)
            # - non_unique(bool)
            # - seuser(str) - SELinux user type
            # - group(str) - primary group name
            group=dict(type='str'),
            # - groups(list) - List of group names
            # - append(bool) - whether to add to or set group list
            # - shell(str)
            # - home(path)
            # - skeleton(path) - skeleton directory
            # - password(str) - crypted password
            # - state(absent, present)
            state=dict(type='str', default='present',
                       choices=['absent', 'present']),
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

    # XXX - user.query [["username","=","ansible"]]
    # returns a lot more detail than
    # user.get_user_obj {"username":"ansible"}
    # I suspect that get_user_obj() just looks up an entry in
    # /etc/passwd, while query() has a more generalized notion of what
    # a user is.

    # Assign variables from properties, for convenience
    username = module.params['name']
    password = module.params['password']
    password_disabled = module.params['password_disabled']
    group = module.params['group']
    group_create = module.params['group_create']
    comment = module.params['comment']
    state = module.params['state']

    # XXX - Look up the user
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
    except AnsibleModuleException as e:
        module.fail_json(msg=f"Error looking up user {username}: {e.stderr}")

    # XXX - Mostly for debugging:
    result['user_info'] = user_info

    # First, check whether the user even exists.
    if user_info is None:
        # User doesn't exist

        if state == 'present':
            # User is supposed to exist
            # XXX - user.create()

            # Collect arguments to pass to user.create()
            arg = {
                "username": username,

                # full_name is required.
                "full_name": comment,

                # Either password_disabled == True, or password must be
                # supplied.
                "password": password,
                "password_disabled": password_disabled,
            }

            # XXX - Look up the primary group. user.create() requires
            # a group number (not a GID!), but for compatibility with
            # the Ansible builtin.user module, we want to be able to
            # use a string for "group". So we need to look the group
            # up by name.
            if group_create:
                arg['group_create'] = True
            else:
                try:
                    group_info = mw.call("group.query",
                                         [["group", "=", group]])
                except Exception as e:
                    module.fail_json(msg=f"Error looking up group {group}: {e}")

                if len(group_info) == 0:
                    group_info = None
                else:
                    group_info = group_info[0]

                arg['group'] = group_info['id']

                # XXX - Just for debugging.
                result['group_info'] = group_info

            if module.check_mode:
                result['msg'] = f"Would have created user {username}"
            else:
                try:
                    err = mw.call("user.create", arg)
                    result['msg'] = err
                except Exception as e:
                    module.fail_json(msg=f"Error creating user {username}: {e}")

        else:
            # User is not supposed to exist.
            # All is well
            result['changed'] = False
    else:
        # User exists
        # XXX
        if state == 'present':
            # User is supposed to exist

            # XXX - Make list of differences between what is and what
            # should be.

            # XXX - If there are any, user.update()
            pass
        else:
            # User is not supposed to exist
            # XXX - user.delete()

            # XXX - Delete the group as well?
            pass

    module.exit_json(**result)

### Main
if __name__ == "__main__":
    main()
