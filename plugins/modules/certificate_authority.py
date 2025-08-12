#!/usr/bin/python
__metaclass__ = type

# Manage certificate authorities.

# XXX - Methods
# - certificateauthority.ca_sign_csr
# - certificateauthority.create
#   Used for multiple operations: create new CA, import existing CA cert, create intermediate CA.
# - certificateauthority.delete
# - certificateauthority.query
# - certificateauthority.update
#   As with certificate.update, this is only for changing the name of a CA, or to revoke it.

# XXX - As with the 'copy' module, use either 'src: <path>' or
# 'content: <string>' to specify the cert.

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
  state:
    description:
      - 'absent': Revoke the CA.
      - Whether the resource should exist or not.
    type: str
    choices: [ absent, present ]
    default: present
version_added: XXX
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
