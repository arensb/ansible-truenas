#!/usr/bin/python
__metaclass__ = type

# XXX - One-line description of module

# XXX - Things to do:
# - certificate.acme_server_choices
#   Might only be useful when generating a cert or CSR.
# - certificate.country_choices
#   Might only be useful when generating a cert or CSR.
# - certificate.create
#   Used for both generating certs and importing existing ones.
#   Also for generating let's encrypt certs.
# - certificate.delete
#   Save for later.
# - certificate.ec_curve_choices
#   Might only be useful when generating a cert or CSR.
# - certificate.extended_key_usage_choices
#   Might only be useful when generating a cert or CSR.
# - certificate.key_type_choices
# - certificate.profiles
#   Could be useful for generating a specific type of cert.
# - certificate.query
#   Look up existing certs.
# - certificate.update (Job)
#   Can only update ID and whether it's revoked. So it's not useful for updating a cert.

# XXX - To upload existing cert:
# - name
# - certificate
# - create_type: CERTIFICATE_CREATE_IMPORTED
# - privatekey

# XXX - There might be a chicken-and-egg problem: how do we update the
# host's https cert while also using https to talk to the API
# endpoint?

# XXX
DOCUMENTATION = '''
---
module: certificate
short_description: Manage host certificates.
description:
  - Allows uploading and revoking host certificates.
options:
  name:
    description:
      - Name of the certificate. This serves as an identifier
        for Ansible.
    type: str
    required: true
  src:
    description:
      - Pathname of the file containing the certificate.
      - See also O(certificate).
    type: path
  certificate:
    description:
      - Used instead of O(src) to specify a certificate inline.
    type: str
  private_keyfile:
    description:
      - Pathname of the file containing the CA's private key.
    type: path
  private_key:
    description:
      - Used instead of O(private_keyfile) to specify a CA private key inline.
    type: str
  state:
    description:
      - Whether the certificate should exist or not.
    type: str
    choices: [ absent, present ]
    default: present
  revoked:
    description:
      - Set to true to revoke a certificater. It is possible to upload
        a certificate and immediately revoke it, though it is not
        clear why this might be useful.
      # - Only CAs with private key can be revoked.
      # - Note that once revoked, a CA cannot be restored. This module
      #   can try to un-revoke a CA, but it will fail.
    type: bool
    default: false
version_added: XXX
'''

# XXX

# XXX - Add an existing cert from string
#     - certificate
#     - type: CERTIFICATE_CREATE_IMPORTED
# XXX - Add an existing cert from a file
#     - src
#     - type: CERTIFICATE_CREATE_IMPORTED
# XXX - Add unsigned cert, if possible.
# XXX - Add cert signed by an existing CA.
# XXX - Delete a cert.
# XXX - Revoke a cert.

EXAMPLES = '''
- name: Install an existing cert from a file.
  arensb.truenas.certificate:
    name: my_cert
    src: /etc/pki/truenas-host.cert
'''

# XXX
RETURN = '''
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW

argument_spec=dict(
    name=dict(type='str', required=True),
    state=dict(type='str', default='present',
               choices=['absent', 'present']),
    src=dict(type='path'),
    certificate=dict(type='str'),
    private_keyfile=dict(type='path'),
    private_key=dict(type='str'),
    revoked=dict(type='bool', default=False),
)
required_if = [
    ('state', 'present', ('src', 'certificate', 'revoked'), True),
]
mutually_exclusive = [
    ('src', 'certificate'),
    ('private_keyfile', 'private_key'),
]
def main():
    global argument_spec

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=required_if,
        mutually_exclusive=mutually_exclusive,
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW.client()

    # Assign variables from properties, for convenience
    name = module.params['name']
    state = module.params['state']
    certificate = module.params['certificate']
    private_key = module.params['private_key']
    revoked = module.params['revoked']

    # Look up the certificate
    try:
        cert_info = mw.call("certificate.query",
                                [["name", "=", name]])
        if len(cert_info) == 0:
            # No such cert
            cert_info = None
        else:
            # Cert exists
            cert_info = cert_info[0]
    except Exception as e:
        module.fail_json(msg=f"Error looking up certificate {name}: {e}")

    # First, check whether the certificate even exists.
    if cert_info is None:
        # Cert doesn't exist

        if state == 'present':
            # Cert is supposed to exist, so create it.

            # Collect arguments to pass to certificate.create()
            arg = {
                "name": name,
                "create_type": "CERTIFICATE_CREATE_IMPORTED",
            }

            # When importing a key, 'certificate' and 'private_key'
            # are required.
            if certificate is not None:
                arg['certificate'] = certificate

            if private_key is not None:
                arg['privatekey'] = private_key

            if module.check_mode:
                result['msg'] = f"Would have created certificate {name} with {arg}"
            else:
                #
                # Create new cert
                #
                try:
                    # Note that this is a job, not a regular call.
                    err = mw.job("certificate.create", arg)
                    result['msg'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating certificate {name}: {e}")

                # Return whichever interesting bits certificate.create()
                # returned.
                result['certificate'] = err

            if revoked is not None and revoked:
                # XXX - To revoke a cert, need its private key. Add
                # this to requirements.
                if module.check_mode:
                    result['msg'] += f"Would mark certificate {name} as revoked."
                else:
                    arg2 = {
                        "revoked": revoked,
                    }

                    try:
                        err2 = mw.call("certificate.update", err['id'], arg2)
                    except Exception as e:
                        module.fail_json(msg=f"Error revoking certificate {name}: {e}")
                        # XXX - Do we need to roll back the cert creation? Can we?

            result['changed'] = True
        else:
            # Cert is not supposed to exist.
            # All is well
            result['changed'] = False

    else:
        # Cert exists
        if state == 'present':
            # Cert is supposed to exist

            # Make list of differences between what is and what should
            # be.
            #
            # Note that certificate.update() can only change 'name'
            # and 'revoked'. And since we use 'name' as an identifier
            arg = {}

            if revoked is not None and cert_info['revoked'] != revoked:
                # XXX - You can revoke a cert, but you can't un-revoke it.
                arg['revoked'] = revoked

            # If there are any changes, certificate.update()
            if len(arg) == 0:
                # No changes
                result['changed'] = False
            else:
                #
                # Update certificate.
                #
                if module.check_mode:
                    result['msg'] = f"Would have updated certificate {name}: {arg}"
                else:
                    try:
                        err = mw.call("certificate.update",
                                      cert_info['id'],
                                      arg)
                    except Exception as e:
                        module.fail_json(msg=f"Error updating certificate {name} with {arg}: {e}")
                        # Return any interesting bits from err
                        result['status'] = err['status']
                result['changed'] = True
        else:
            # Cert is not supposed to exist

            # XXX - "force" option?

            if module.check_mode:
                result['msg'] = f"Would have deleted certificate {name}"
            else:
                try:
                    #
                    # Delete certificate.
                    #
                    err = mw.call("certificate.delete",
                                  cert_info['id'])
                except Exception as e:
                    module.fail_json(msg=f"Error deleting certificate {name}: {e}")
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
