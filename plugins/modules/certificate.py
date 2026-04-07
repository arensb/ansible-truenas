#!/usr/bin/python
# -*- coding: utf-8 -*-
__metaclass__ = type

# Manage certificates.

# XXX - What should happen with
# certificate:
#   name: my_cert
#   revoked: yes
# when the cert doesn't exist?
#
# Right now, it tries to install the cert, and immediately revoke it.
# And that's what it should do: if the caller wanted the cert to not
# exist, they'd have used "state: absent", not "revoked: yes".
# So the cert needs to be installed for it to be revoked.
#
# Maybe add "state: revoked_or_absent"? Or "revoke: if_present"?

# XXX - There might be a chicken-and-egg problem: how do we update the
# host's https cert while also using https to talk to the API
# endpoint?

# XXX - Maybe add an 'is_CA' argument? At some point in the future,
# might want to transition from having both certificate and
# certificate_authority, to just having certificate.

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
      - This file must only contain the certificate, not any signing certificates.
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
  passphrase:
    description:
      - Passphrase for the certificate.
  state:
    description:
      - Whether the certificate should exist or not.
    type: str
    choices: [ absent, present ]
    default: present
  revoked:
    description:
      - Set to true to revoke a certificate. It is possible to upload
        a certificate and immediately revoke it, though it is not
        clear why this might be useful.
      - "Perhaps counterintuitively, only specifying O(name) and
        O(revoked=yes) will cause an error when the cert does not exist.
        This is because the cert needs to be uploaded before it can be
        revoked."
      - Note that under TrueNAS SCALE 25.10, certificates cannot be revoked.
        This option is ignored.
    type: bool
    default: false
notes:
  - There appears to be a bug in TrueNAS 25.04.0 that prevents installing
    certificates with keys greater than 2048 bits long. In fact, 2048 seems
    to be the only usable key size for certificates.
  - Although TrueNAS supports creating certificates in the console,
    this module does not. It is not immediately clear how this should work
    in an idempotent Ansible module. At least for now, it is recommended
    that you generate certificates as part of your PKI system, and upload
    them to TrueNAS devices. Failing that, you can manually generate a cert
    in the TrueNAS console, and download it to your Ansible server.
version_added: 1.12.0
'''

EXAMPLES = '''
- name: Install an existing cert from a file.
  arensb.truenas.certificate:
    name: my_cert
    src: /etc/pki/truenas-host.cert

- name: Same, but include a private key and passphrase.
  arensb.truenas.certificate:
    name: my_cert
    src: /etc/pki/truenas-host.cert
    private_key: |-
      -----BEGIN PRIVATE KEY-----
      MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC9QCpnXKNXoOdx
      ...
    passphrase: "squeamish ossifrage"

- name: Revoke a cert
  arensb.truenas.certificate:
    name: my_cert
    revoked: true

- name: Remove a cert
  arensb.truenas.certificate:
    name: my_cert
    state: absent
'''

RETURN = '''
certificate:
  description:
    - A data structure describing a newly-created or -installed certificate.
    - Only returned when a certificate is created.
  type: dict
  sample:
    id: "6841f242-840a-11e6-a437-00e04d680384"
    msg: "method"
    method: "certificate.create"
    params:
      - name: "imported_cert"
        certificate: "Certificate string"
        privatekey: "Private key string"
        create_type: "CERTIFICATE_CREATE_IMPORTED"
'''

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.middleware import MiddleWare as MW
from ..module_utils import setup
from packaging import version

argument_spec=dict(
    name=dict(type='str', required=True),
    state=dict(type='str', default='present',
               choices=['absent', 'present']),
    src=dict(type='path'),
    certificate=dict(type='str'),
    private_keyfile=dict(type='path'),
    private_key=dict(type='str'),
    passphrase=dict(type='str'),
    revoked=dict(type='bool', default=False),
)
required_if = [
    ('state', 'present', ('src', 'certificate', 'revoked'), True),
]
mutually_exclusive = [
    ('src', 'certificate'),
    ('private_keyfile', 'private_key'),
]

class Cert:
    """Class to implement the certificate module, with support for
    multiple API versions."""

    def __init__(self):
        """Common initialization: handle module arguments before
        control gets handed to one of the run*() methods."""
        global argument_spec, required_if, mutually_exclusive

        self.module = AnsibleModule(
            argument_spec=argument_spec,
            supports_check_mode=True,
            required_if=required_if,
            mutually_exclusive=mutually_exclusive,
        )

        self.result = dict(
            changed=False,
            msg=''
        )

        self.mw = MW.client()

    def run1(self):
        # Assign variables from properties, for convenience
        name = self.module.params['name']
        state = self.module.params['state']
        certificate = self.module.params['certificate']
        private_key = self.module.params['private_key']
        passphrase = self.module.params['passphrase']
        revoked = self.module.params['revoked']

        # Look up the certificate
        try:
            cert_info = self.mw.call("certificate.query",
                                    [["name", "=", name]])
            if len(cert_info) == 0:
                # No such cert
                cert_info = None
            else:
                # Cert exists
                cert_info = cert_info[0]
        except Exception as e:
            self.module.fail_json(msg=f"Error looking up certificate {name}: {e}")

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

                if passphrase is not None:
                    arg['passphrase'] = passphrase

                if self.module.check_mode:
                    self.result['msg'] = f"Would have created certificate {name} with {arg}"
                else:
                    #
                    # Create new cert
                    #
                    try:
                        # Note that this is a job, not a regular call.
                        err = self.mw.job("certificate.create", arg)
                        self.result['certificate'] = err
                    except Exception as e:
                        self.result['failed_invocation'] = arg
                        self.module.fail_json(msg=f"Error creating certificate {name}: {e}")

                    # Return whichever interesting bits certificate.create()
                    # returned.
                    self.result['certificate'] = err

                if revoked is not None and revoked:
                    # XXX - To revoke a cert, need its private key. Add
                    # this to requirements.

                    # XXX - Under SCALE 25.10, it looks as though you can't revoke a cert.
                    # You can only change its name.
                    if self.module.check_mode:
                        self.result['msg'] += f"\nWould mark certificate {name} as revoked."
                    else:
                        arg2 = {
                            "revoked": revoked,
                        }

                        try:
                            err2 = self.mw.call("certificate.update", err['id'], arg2)
                            # This overwrites the earlier result[certificate].
                            self.result['certificate'] = err2
                        except Exception as e:
                            self.module.fail_json(msg=f"Error revoking certificate {name}: {e}")
                            # XXX - Do we need to roll back the cert creation? Can we?

                self.result['changed'] = True
            else:
                # Cert is not supposed to exist.
                # All is well
                self.result['changed'] = False

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
                    self.result['changed'] = False
                else:
                    #
                    # Update certificate.
                    #
                    if self.module.check_mode:
                        self.result['msg'] = f"Would have updated certificate {name}: {arg}"
                    else:
                        try:
                            err = self.mw.job("certificate.update",
                                          cert_info['id'],
                                          arg)
                            # certificate.update
                            self.result['status'] = err
                        except Exception as e:
                            self.module.fail_json(msg=f"Error updating certificate {name} with {arg}: {e}")
                        # Return any interesting bits from err
                        self.result['status'] = err['status']
                    self.result['changed'] = True
            else:
                # Cert is not supposed to exist

                # XXX - "force" option?

                if self.module.check_mode:
                    self.result['msg'] = f"Would have deleted certificate {name}"
                else:
                    try:
                        #
                        # Delete certificate.
                        #
                        err = self.mw.job("certificate.delete",
                                     cert_info['id'])
                    except Exception as e:
                        self.module.fail_json(msg=f"Error deleting certificate {name}: {e}")
                self.result['changed'] = True

        self.module.exit_json(**self.result)

    def run_25_10(self):
        """Run on SCALE 25.10 or above."""

        # Assign variables from properties, for convenience
        name = self.module.params['name']
        state = self.module.params['state']
        certificate = self.module.params['certificate']
        private_key = self.module.params['private_key']
        passphrase = self.module.params['passphrase']
        revoked = self.module.params['revoked']

        # Look up the certificate
        try:
            # XXX - We _could_ filter by "cert_type_CA == false", but
            # if we want 'certificate' to take over
            # 'certificate_authority' at some point in the future,
            # let's leave it be.
            cert_info = self.mw.call("certificate.query",
                                    [["name", "=", name]])
            if len(cert_info) == 0:
                # No such cert
                cert_info = None
            else:
                # Cert exists
                cert_info = cert_info[0]
        except Exception as e:
            self.module.fail_json(msg=f"Error looking up certificate {name}: {e}")

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

                if passphrase is not None:
                    arg['passphrase'] = passphrase

                if self.module.check_mode:
                    self.result['msg'] = f"Would have created certificate {name} with {arg}"
                else:
                    #
                    # Create new cert
                    #
                    try:
                        # Note that this is a job, not a regular call.
                        err = self.mw.job("certificate.create", arg)
                        self.result['certificate'] = err
                    except Exception as e:
                        self.result['failed_invocation'] = arg
                        self.module.fail_json(msg=f"Error creating certificate {name}: {e}")

                    # Return whichever interesting bits certificate.create()
                    # returned.
                    self.result['certificate'] = err

                self.result['changed'] = True
            else:
                # Cert is not supposed to exist.
                # All is well
                self.result['changed'] = False

        else:
            # Cert exists
            if state == 'present':
                # Cert is supposed to exist

                # Make list of differences between what is and what should
                # be.

                # Only the name can be changed. And since this
                # self.module uses 'name' as an identifier, the name
                # can't be changed, either.

                # No changes
                self.result['changed'] = False

            else:
                # Cert is not supposed to exist

                # XXX - "force" option?

                if self.module.check_mode:
                    self.result['msg'] = f"Would have deleted certificate {name}"
                else:
                    try:
                        #
                        # Delete certificate.
                        #
                        err = self.mw.job("certificate.delete",
                                     cert_info['id'])
                    except Exception as e:
                        self.module.fail_json(msg=f"Error deleting certificate {name}: {e}")

                    # Return any interesting bits from err
                    self.result['status'] = err
                self.result['changed'] = True

        self.module.exit_json(**self.result)

    def run(self):
        # Figure out which version of TrueNAS we're running, and thus how
        # to call middlewared.
        try:
            tn_version = setup.get_tn_version()
        except Exception as e:
            # Normally we'd module.exit_json(), but we don't have a module yet.
            print(f'{{"failed":true, "msg": "Error getting TrueNAS version: {e}"}}')
            sys.exit(1)

        # Call the appropriate function to handle this.

        # In TrueNAS SCALE 25.10, 'certificateauthority' was rolled into
        # 'certificate'.
        TC_25_10 = version.parse("25.10")
        if tn_version['name'] == "TrueNAS" and \
           tn_version['type'] in {"SCALE", "COMMUNITY_EDITION"} and \
           tn_version['version'] >= TC_25_10:
            return self.run_25_10()
        else:
            return self.run1()

def main():
    return Cert().run()

# Main
if __name__ == "__main__":
    main()
