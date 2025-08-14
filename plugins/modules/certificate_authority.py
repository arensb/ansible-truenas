#!/usr/bin/python
__metaclass__ = type

# Manage certificate authorities.

# XXX - Methods
# - certificateauthority.ca_sign_csr
# - certificateauthority.create
#   Used for multiple operations: create new CA, import existing CA
#   cert, create intermediate CA.
# - certificateauthority.delete
# - certificateauthority.query
# - certificateauthority.update
#   As with certificate.update, this is only for changing the name of
#   a CA, or to revoke it.

# XXX - As with the 'copy' module, use either 'src: <path>' or
# 'content: <string>' to specify the cert.

# XXX - This API allows you to create CA certs, but I don't want to
# implement that just yet. It seems fraught with peril. It might even
# be better to write a different module for this.

# XXX
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
      - See also O(content).
    type: path
  content:
    description:
      - Used instead of O(src) to specify a certificate inline.
    type: str
  state:
    description:
      - "'present': Ensure that the CA cert is installed."
      - "'absent': Ensure that the CA cert is absent. Revoke it if necessary."
    type: str
    choices: [ absent, present ]
    default: present
  revoked:
    description:
      - Whether this CA cert has been revoked.
    type: bool
    default: false
version_added: XXX
'''

# XXX
EXAMPLES = '''
- name: Install a CA cert from a file
  arensb.truenas.certificate_authority:
    name: my_ca_cert
    src: /etc/pki/my-ca.cert

- name: Install a CA cert from a string
  arensb.truenas.certificate_authority:
    name: my_ca_cert
    content: |-
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
    content=dict(type='str'),
    private_keyfile=dict(type='path'),
    private_key=dict(type='str'),
    passphrase=dict(type='str', no_log=True),
    revoked=dict(type='bool', default=False),
)
required_if = [
    ('state', 'present', ('src', 'content', 'revoked'), True),
]
mutually_exclusive = [
    ('src', 'content'),
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
    src = module.params['src']
    content = module.params['content']
    revoked = module.params['revoked']

    # XXX - Look up the CA cert
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

            # XXX - revoked

            # AFAIK you can't create (or upload) a new cert that's
            # already revoked. I don't know why you'd want to do that,
            # but if it turns out to be useful, we may need to call
            # certificateauthority.create() followed by
            # certificateauthority.update(revoked=true)

            # Either 'content' is set to the certificate, or 'src' is
            # a path to it. So we can just read that file into
            # 'content', so either way, at the end, 'content' will be
            # the cert as a string.
            if src is not None:
                try:
                    # XXX - 'src' needs to be opened on localhost, not
                    # on the client.
                    with open(src, 'rt') as f:
                        content = f.read()
                except Exception as e:
                    module.fail_json(msg=f"Error getting certificate: {e}")

            arg['certificate'] = content

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
            arg = {}

            if revoked is not None and ca_cert_info['revoked'] != revoked:
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
                        module.fail_json(msg=f"Error updating CA cert {name} with {arg}: {e}")
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
