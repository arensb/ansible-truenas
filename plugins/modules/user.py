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
  state:
    description:
      - Whether the user shoujld exist or not.
    type: str
    choices: [ absent, present ]
    default: present
'''

EXAMPLES = '''
XXX
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
            # - home(str)
            # - home_mode(str)
            # - shell(str) - Choose from user.shell_choices() (reads /etc/shells)
            # - full_name(str)
            # - email(str|null?)
            # - password(str) - Required if password_disabled is false
            # - password_disabled(bool)
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
            # - hidden(bool)
            # - non_unique(bool)
            # - seuser(str) - SELinux user type
            # - group(str) - primary group name
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
            arg = { "username": username }
            # XXX - No arguments yet.

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
            pass

    module.exit_json(**result)

### Main
if __name__ == "__main__":
    main()
