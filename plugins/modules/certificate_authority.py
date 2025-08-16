#!/usr/bin/python
__metaclass__ = type

# Manage certificate authorities.

# This module has an associated action module, which is a wrapper around this module.

# XXX - This API allows you to create CA certs, but I don't want to
# implement that just yet. It seems fraught with peril. It might even
# be better to write a different module for this.

# XXX - Can't delete a CA while it's in use by a cert. Make sure this
# is indicated in an error message if it happens.

DOCUMENTATION = '''
---
module: certificate_authority
short_description: Manage Certificate Authorities.
description:
  - Allows uploading and revoking CA certs. These CA certs are
    used as part of a key infrastructure to sign
    host certificates.
options:
  name:
    description:
      - Name of the CA.
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
    aliases: [ ca, cert, ca_cert ]
  private_keyfile:
    description:
      - Pathname of the file containing the CA's private key.
    type: path
  private_key:
    description:
      - Used instead of O(private_keyfile) to specify a CA private key inline.
    type: str
  passphrase:
    # description:
    #   - Passphrase fo t
  state:
    description:
      - "'present': Ensure that the CA cert is installed."
      - "'absent': Ensure that the CA cert is absent. Revoke it if necessary."
    type: str
    choices: [ absent, present ]
    default: present
  revoked:
    description:
      - Set to true to revoke a CA. It is possible to upload a CA and
        immediately revoke it, though it is not clear why this might
        be useful.
      - Only CAs with private key can be revoked.
      - Note that once revoked, a CA cannot be restored. This module
        can try to un-revoke a CA, but it will fail.
    type: bool
    default: false
version_added: XXX
'''

# XXX

# XXX - Include an example of uploading a CA with a key. Must include
# passphrase if key is signed.

EXAMPLES = '''
- name: Install a CA cert from a file
  arensb.truenas.certificate_authority:
    name: my_ca_cert
    src: /etc/pki/my-ca.cert

- name: Install a CA cert from a string
  arensb.truenas.certificate_authority:
    name: my_ca_cert
    certificate: |-
      -----BEGIN CERTIFICATE-----
      MIIFdTCCA12gAwIBAgIUQZLjifloJRGBwalKcoODV20BmhUwDQYJKoZIhvcNAQEL
      ...
      B5A/Sn7DTfQz
      -----END CERTIFICATE-----

- name: Remove and revoke a CA cert
  arensb.truenas.certificate_authority:
    name: my_ca_cert
    state: absent

- name: Remove a CA cert, even if it can't be revoked
  arensb.truenas.certificate_authority:
    name: my_ca_cert
    state: absent
    force: yes

- name: Revoke a CA cert, but keep it in the list.
  arensb.truenas.certificate_authority:
    name: my_ca_cert
    state: present
    revoked: yes
'''

# XXX
RETURN = '''
ca_cert:
  description:
    - A data structure describing a newly-created or -installed CA certificate.
    - Only returned when a certificate is created.
  type: dict
  sample:
    id: "6841f242-840a-11e6-a437-00e04d680384"
    msg: "method"
    method: "certificateauthority.create"
    params:
      - name: "imported_ca"
        certificate: "Certificate string"
        privatekey: "Private key string"
        create_type: "CA_CREATE_IMPORTED"
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW

# Put this at file scope so that the action module can slurp this in
# and validate arguments.
argument_spec = dict(
    name=dict(type='str', required=True),
    state=dict(type='str', default='present',
               choices=['absent', 'present']),
    src=dict(type='path'),
    certificate=dict(type='str',
                     aliases=['ca', 'cert', 'ca_cert']),
    private_keyfile=dict(type='path'),
    private_key=dict(type='str'),
    passphrase=dict(type='str', no_log=True),
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
    global argument_spec, required_if, mutually_exclusive

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,

        # If we're creating/uploading a CA, need to give either the CA
        # cert, or a path to it, but not both.
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
    # src = module.params['src']
    certificate = module.params['certificate']
    # private_keyfile = module.params['private_keyfile']
    private_key = module.params['private_key']
    passphrase = module.params['passphrase']
    revoked = module.params['revoked']

    # Look up the CA cert
    try:
        ca_cert_info = mw.call("certificateauthority.query",
                               [["name", "=", name]])
        if len(ca_cert_info) == 0:
            # No such CA cert
            ca_cert_info = None
        else:
            # CA cert exists
            ca_cert_info = ca_cert_info[0]
    except Exception as e:
        module.fail_json(msg=f"Error looking up CA cert {name}: {e}")

    # First, check whether the CA cert even exists.
    if ca_cert_info is None:
        # CA cert doesn't exist

        if state == 'present':
            # CA cert is supposed to exist, so create it.

            # Collect arguments to pass to certificateauthority.create()
            arg = {
                "name": name,
                "create_type": "CA_CREATE_IMPORTED",
            }

            # AFAIK you can't create (or upload) a new cert that's
            # already revoked. I don't know why you'd want to do that,
            # but if it turns out to be useful, we may need to call
            # certificateauthority.create() followed by
            # certificateauthority.update(revoked=true)

            if certificate is not None:
                arg['certificate'] = certificate

            if private_key is not None:
                arg['privatekey'] = private_key

            if passphrase is not None:
                arg['passphrase'] = passphrase

            if module.check_mode:
                result['msg'] = f"Would have created CA certificate {name} with {arg}"
            else:
                #
                # Install new CA cert
                #
                try:
                    err = mw.call("certificateauthority.create", arg)
                    result['msg'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating CA certificate {name}: {e}")

                # Return whichever interesting bits certificateauthority.create()
                # returned.
                result['ca_cert'] = err

            if revoked is not None and revoked:
                # XXX - To revoke a CA, need its private key. Add this
                # to requirements.
                if module.check_mode:
                    result['msg'] += f"Would mark CA {name} as revoked."
                else:
                    arg2 = {
                        "revoked": revoked,
                    }

                    try:
                        err2 = mw.call("certificateauthority.update", err['id'], arg2)
                    except Exception as e:
                        module.fail_json(msg=f"Error revoking CA certificate {name}: {e}")
                        # XXX - Do we need to roll back the CA creation? Can we?

            result['changed'] = True
        else:
            # The CA cert is not supposed to exist.
            # All is well
            result['changed'] = False

    else:
        # CA exists
        if state == 'present':
            # This CA is supposed to exist

            # Make list of differences between what is and what should
            # be.

            # Only the name and 'revoked' can be changed. And since
            # this module uses 'name' as an identifier, the name can't
            # be changed, either.
            arg = {}

            if revoked is not None and ca_cert_info['revoked'] != revoked:
                # You can revoke a cert, but you can't un-revoke it.
                arg['revoked'] = revoked

            # If there are any changes, certificateauthority.update()
            if len(arg) == 0:
                # No changes
                result['changed'] = False
            else:
                #
                # Update the CA.
                #
                if module.check_mode:
                    result['msg'] = f"Would have updated CA cert {name}: {arg}"
                else:
                    try:
                        err = mw.call("certificateauthority.update",
                                      ca_cert_info['id'],
                                      arg)
                    except Exception as e:
                        module.fail_json(msg=f"Error updating CA cert {name} ({ca_cert_info['id']}) with {arg}: {e}")
                        # Return any interesting bits from err
                        result['status'] = err['status']
                result['changed'] = True
        else:
            # CA is not supposed to exist

            if module.check_mode:
                result['msg'] = f"Would have deleted CA {name}"
            else:
                try:
                    #
                    # Delete CA.
                    #
                    err = mw.call("certificateauthority.delete",
                                  ca_cert_info['id'])
                except Exception as e:
                    module.fail_json(msg=f"Error deleting CA cert {name}: {e}")
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
