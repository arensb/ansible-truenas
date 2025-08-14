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
  - Upload and revoke host certificates.
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
  state:
    description:
      - Whether the resource should exist or not.
    type: str
    choices: [ absent, present ]
    default: present
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


def main():
    module = AnsibleModule(
        argument_spec=dict(
            # XXX
            name=dict(type='str'),
            state=dict(type='str', default='present',
                       choices=['absent', 'present']),
            ),
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW.client()

    # Assign variables from properties, for convenience
    name = module.params['name']
    # XXX

    # XXX - Look up the resource
    try:
        resource_info = mw.call("resource.query",
                                [["name", "=", name]])
        if len(resource_info) == 0:
            # No such resource
            resource_info = None
        else:
            # Resource exists
            resource_info = resource_info[0]
    except Exception as e:
        module.fail_json(msg=f"Error looking up resource {name}: {e}")

    # First, check whether the resource even exists.
    if resource_info is None:
        # Resource doesn't exist

        if state == 'present':
            # Resource is supposed to exist, so create it.

            # Collect arguments to pass to resource.create()
            arg = {
                "resourcename": name,
            }

            if feature is not None:
                arg['feature'] = feature

            if module.check_mode:
                result['msg'] = f"Would have created resource {name} with {arg}"
            else:
                #
                # Create new resource
                #
                try:
                    # XXX - This is a job, not a regular call.
                    err = mw.call("resource.create", arg)
                    result['msg'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating resource {name}: {e}")

                # Return whichever interesting bits resource.create()
                # returned.
                result['resource_id'] = err

            result['changed'] = True
        else:
            # Resource is not supposed to exist.
            # All is well
            result['changed'] = False

    else:
        # Resource exists
        if state == 'present':
            # Resource is supposed to exist

            # Make list of differences between what is and what should
            # be.
            arg = {}

            if feature is not None and resource_info['feature'] != feature:
                arg['feature'] = feature

            # If there are any changes, resource.update()
            if len(arg) == 0:
                # No changes
                result['changed'] = False
            else:
                #
                # Update resource.
                #
                if module.check_mode:
                    result['msg'] = f"Would have updated resource {name}: {arg}"
                else:
                    try:
                        err = mw.call("resource.update",
                                      resource_info['id'],
                                      arg)
                    except Exception as e:
                        module.fail_json(msg=f"Error updating resource {name} with {arg}: {e}")
                        # Return any interesting bits from err
                        result['status'] = err['status']
                result['changed'] = True
        else:
            # Resource is not supposed to exist

            if module.check_mode:
                result['msg'] = f"Would have deleted resource {name}"
            else:
                try:
                    #
                    # Delete resource.
                    #
                    err = mw.call("resource.delete",
                                  resource_info['id'])
                except Exception as e:
                    module.fail_json(msg=f"Error deleting resource {name}: {e}")
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
