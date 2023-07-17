#!/usr/bin/python
__metaclass__ = type

# Manage email settings

DOCUMENTATION = '''
---
module: mail
short_description: Manage TrueNAS email settings
description:
  - Configure how TrueNAS sends mail.
options:
  from_email:
    description:
      - >
        Address from which system email will be sent. Must be in the form
        of an email address: C(user@dom.ain).
      - This is used as both the envelope and header \"From\" address.
    type: str
  from_name:
    description:
      - Full name used in the email's \"From\" header.
  server:
    description:
      - Outgoing mail server. This may be either the hostname or IP address
        of an SMTP server.
    type: str
  oauth_id:
    description: OAuth client ID.
    type: str
  oauth_secret:
    description: OAuth client secret.
    type: str
  oauth_token:
    description: OAuth access token.
    type: str
  port:
    description:
      - The TCP port on which to connect to the outgoing mail server.
    type: int
    default: 25
  security:
    description:
      - The encryption to use for outgoing mail.
    type: str
    choices: [ PLAIN, SSL, TLS ]
  smtp:
    description:
      - If true, means that SMTP authentication is enabled on the server,
        and I(smtp_user) and I(smtp_pass) are required to log in.
      - See also I(smtp_user) and I(smtp_password).
    type: bool
  smtp_user:
    description:
      - User to log in as on the SMTP server. Required if C(smtp=true).
      - See also I(smtp) and I(smtp_password).
    type: str
  smtp_password:
    description:
      - Password for I(smtp_user) on the SMTP server. Required if C(smtp=true).
      - See also I(smtp) and I(smtp_user).
    type: str
version_added: 1.3.0
'''

# XXX - Ought to have more examples with nontrivial SMTP, and OAuth.
EXAMPLES = '''
- name: Forward mail to a central server
  hosts: my-truenas-host
  tasks:
    - name: Forward to SMTP hub
      arensb.truenas.mail:
        from_email: root@my-truenas-host.dom.ain
        from_name: "Charlie Root"
        server: smtp.dom.ain
'''

RETURN = '''#'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW


def main():
    module = AnsibleModule(
        argument_spec=dict(
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
        # XXX - 'smtp_user' and 'smtp_pass' are required when 'smtp' is true.
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW.client()

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
