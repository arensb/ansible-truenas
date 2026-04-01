#!/usr/bin/python
__metaclass__ = type

# Configure the WebDAV service.
#
# This only exists under CORE. Under SCALE, need to install a separate
# application:
# https://www.truenas.com/docs/scale/22.12/scaletutorials/apps/communityapps/webdav/

DOCUMENTATION = '''
---
module: webdav
short_description: Configure the WebDAV service
description:
  - "Configures how to access the WebDAV service: the port, username, password,
    and so on."
  - Use the C(service) module to start and enable it, and the C(sharing_webdav)
    module to configure shares. Use the C(certificate) service to install
    a certificate for WebDAV over HTTPS.
options:
  protocol:
    description:
      - Protocol to use to connect to the WebDAV service.
      - The value "HTTPHTTPS" allows connecting using either HTTP or HTTPS.
    type: str
    choices: [ HTTP, HTTPS, HTTPHTTPS ]
    required: false
  port:
    description:
      - TCP port on which the HTTP service listens.
    type: int
    required: false
  portssl:
    description:
      - TCP port on which the HTTPS service listens.
    type: int
    required: false
  password:
    description:
      - WebDAV password, as a plaintext string.
    type: str
    required: false
  auth_type:
    description:
      - Authentication type.
    type: str
    choices: [ NONE, BASIC, DIGEST ]
    required: false
  certssl:
    description:
      - The name of the certificate to use for HTTPS.
      - Use the C(certificate) module to install a certificate.
    type: str
    required: false
version_added: 1.15.0
'''

EXAMPLES = '''
# Turn on WebDAV, configure it, and create a share.
- name: Configure WebDAV
  hosts: myhosts
  become: yes
  tasks:
    - name: Create SMS backup directory
      arensb.truenas.sharing_webdav:
        name: myshare
        path: "/mnt/tank/myfilesystem/myshare"
    - name: Configure WebDAV service
      arensb.truenas.webdav:
        protocol: HTTP
        port: 9100
        password: "{{ webdav_password }"
        auth_type: BASIC
    - name: Enable WebDAV service
      arensb.truenas.service:
        name: webdav
        state: started
        enabled: yes
'''

RETURN = '''
webdav:
  description:
    - A data structure containing the new service configuration.
  type: dict
  sample:
    id: 1
    protocol: HTTP
    tcpport: 8080
    tcpportssl: 8081
    password: "Password123"
    htauth: "DIGEST"
    certssl: null
'''

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.middleware import MiddleWare as MW


def main():
    module = AnsibleModule(
        argument_spec=dict(
            protocol=dict(type='str',
                          choices=[ 'HTTP', 'HTTPS', 'HTTPHTTPS' ]),
            port=dict(type='int'),
            portssl=dict(type='int'),
            password=dict(type='str'),
            auth_type=dict(type='str',
                           choices=[ 'NONE', 'BASIC', 'DIGEST' ]),
            certssl=dict(type=str),
            ),
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW.client()

    # Assign variables from properties, for convenience
    protocol = module.params['protocol']
    port = module.params['port']
    portssl = module.params['portssl']
    password = module.params['password']
    auth_type = module.params['auth_type']
    certssl = module.params['certssl']

    certlist = {}
    """List of certificates that can be used for WebDAV.
    Keys are names (str) and values are indexes (int) to be used
    in webdav.update.
    """

    # Look up the current configuration.
    try:
        webdav_config = mw.call("webdav.config")
        # XXX - Error-checking

        # Get the list of available certs.
        tmp_certlist = mw.call("webdav.cert_choices")
        for cert_id, cert_name in tmp_certlist.items():
            certlist[cert_name] = cert_id
    except Exception as e:
        module.fail_json(msg=f"Error looking up WebDAV configuration: {e}")

    # Make list of differences between what is and what should
    # be.
    arg = {}

    if protocol is not None and webdav_config['protocol'] != protocol:
        arg['protocol'] = protocol

    if port is not None and webdav_config['tcpport'] != port:
        arg['tcpport'] = port

    if portssl is not None and webdav_config['tcpportssl'] != portssl:
        arg['tcpportssl'] = portssl

    if password is not None and webdav_config['password'] != password:
        arg['password'] = password

    if auth_type is not None and webdav_config['htauth'] != auth_type:
        arg['htauth'] = auth_type

    if certssl is not None:
        # Make sure this cert is available for use.
        if certssl not in certlist:
            module.fail_json(f"No cert {certssl} available for WebDAV.")

        # Yes, it is. The caller has given us a cert name, but we need
        # to compare indexes.
        if webdav_config['certssl'] != certlist[certssl]:
            arg['certssl'] = certssl

    # If there are any changes, webdav.update()
    if len(arg) == 0:
        # No changes
        result['changed'] = False
    else:
        #
        # Update configuration.
        #
        if module.check_mode:
            result['msg'] = f"Would have updated WebDAV configuration: {arg}"
        else:
            try:
                err = mw.call("webdav.update",
                              arg)
            except Exception as e:
                module.fail_json(msg=f"Error updating WebDAV config with {arg}: {e}")
                # Return any interesting bits from err
                result['status'] = err['status']
            result['webdav'] = err

        result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
