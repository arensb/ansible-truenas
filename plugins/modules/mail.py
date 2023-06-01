#!/usr/bin/python
__metaclass__ = type

# Manage email settings

# XXX
DOCUMENTATION = '''
---
module: mail
short_description: Manage TrueNAS email settings
description:
options:
  # XXX
  from_email:
    description:
      - Address from which system email will be sent. Must be in the form
        of an email address: I(user@dom.ain).
      - This is used as both the envelope and header \"From\" address.
    type: str
  from_name:
    description:
      - Full name used in the email's \"From\" header.
  server:
  port:
  security:
  smtp:
  smtp_user:
  password:
  oauth:
    client_id:
    client_secret:
    refresh_token:
  # name:
  #   description:
  #     - Name of the resource
  #   type: str
  #   required: true
  # state:
  #   description:
  #     - Whether the resource should exist or not.
  #   type: str
  #   choices: [ absent, present ]
  #   default: present
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
    module = AnsibleModule(
        argument_spec=dict(
            # XXX
            from_name=dict(type='str'),
            from_email=dict(type='str'),
            server=dict(type='str'),
            port=dict(type='int', default=25),
            security=dict(type='str', default='PLAIN',
                          choices=["PLAIN", "SSL", "TLS"]),
            smtp=dict(type='bool'),
            smtp_user=dict(type='str'),
            smtp_password=dict(type='str', no_log=True, aliases=['password']),
            oauth_id=dict(type='str'),
            oauth_secret=dict(type='str', no_log=True),
            oauth_token=dict(type='str'),
            ),
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW()

    # Assign variables from properties, for convenience
    from_name = module.params['from_name']
    from_email = module.params['from_email']
    server = module.params['server']
    port = module.params['port']
    security = module.params['security']
    smtp = module.params['smtp']
    smtp_user = module.params['smtp_user']
    smtp_password = module.params['smtp_password']
    oauth_id = module.params['oauth_id']
    oauth_secret = module.params['oauth_secret']
    oauth_token = module.params['oauth_token']

    # Look up the configuration
    try:
        mail_info = mw.call("mail.config")
    except Exception as e:
        module.fail_json(msg=f"Error looking up mail config: {e}")

    # Make list of differences between what is and what should
    # be.
    arg = {}

    if from_name is not None and mail_info['fromname'] != from_name:
        arg['fromname'] = from_name
    if from_email is not None and mail_info['fromemail'] != from_email:
        arg['fromemail'] = from_email
    if server is not None and mail_info['outgoingserver'] != server:
        arg['outgoingserver'] = server
    if port is not None and mail_info['port'] != port:
        arg['port'] = port
    if security is not None and mail_info['security'] != security:
        arg['security'] = security
    if smtp is not None and mail_info['smtp'] != smtp:
        arg['smtp'] = smtp
    if smtp_user is not None and mail_info['user'] != smtp_user:
        arg['user'] = smtp_user
    if smtp_password is not None and mail_info['pass'] != smtp_password:
        arg['pass'] = smtp_password
    if oauth_id is not None and (
            'client_id' not in mail_info['oauth'] or
            mail_info['oauth']['client_id'] != oauth_id
    ):
        if 'oauth' not in arg:
            arg['oauth'] = {}
        arg['oauth']['client_id'] = oauth_id
    if oauth_secret is not None and (
            'client_secret' not in mail_info['oauth'] or
            mail_info['oauth']['client_secret'] != oauth_secret
    ):
        if 'oauth' not in arg:
            arg['oauth'] = {}
        arg['oauth']['client_secret'] = oauth_secret
    if oauth_token is not None and (
            'refresh_token' not in mail_info['oauth'] or
            mail_info['oauth']['refresh_token'] != oauth_token
    ):
        if 'oauth' not in arg:
            arg['oauth'] = {}
        arg['oauth']['refresh_token'] = oauth_token

    # If there are any changes, mail.update()
    if len(arg) == 0:
        # No changes
        result['changed'] = False
    else:
        #
        # Update mail settings.
        #
        if module.check_mode:
            result['msg'] = f"Would have updated mail: {arg}"
        else:
            try:
                err = mw.call("mail.update",
                              arg)
            except Exception as e:
                module.fail_json(msg=f"Error updating mail with {arg}: {e}")
                # Return any interesting bits from err
                result['status'] = err
        result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
