#!/usr/bin/python
__metaclass__ = type

# Create and manage WebDAV shares.

# XXX
DOCUMENTATION = '''
---
module: sharing_webdav
short_description: Manage WebDAV shares
description:
  - Create, manage, and delete WebDAV shares.
options:
  name:
    description:
      - Name of the share. This is an identifier.
    type: str
    required: true
  description:
    description:
      - Human-readable description of the share.
    type: str
    required: false
  path:
    description:
      - Directory (path) to be shared.
    type: str
    required: true
  ro:
    description:
      - If true, this share is read-only, i.e., users may not write to it.
    type: bool
    required: false
    default: false
  chown:
    description:
      - If true, change the ownership of all files to user C(webdav), group C(webdav).
      - If false, files to be shared must be manually updated to be owned by group C(webdav) or C(www).
    required: false
    default: true
  state:
    description:
      - Whether the share should exist or not.
    type: str
    choices: [ present, absent ]
    default: present
  enabled:
    description:
      - If true, the share is enabled. Otherwise, it is present but
        disabled.
      - This has no effect if C(state) is C(absent).
    type: bool
    default: true
version_added: 1.15.0
'''

# XXX
EXAMPLES = '''
'''

# XXX
RETURN = '''
'''

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.middleware import MiddleWare as MW


def main():
    # XXX - perm: bool -> chown
    # XXX - ro: bool
    # XXX - comment: str -> description
    # XXX - name: str
    # XXX - path: str
    # XXX - enabled: bool
    module = AnsibleModule(
        argument_spec=dict(
            # XXX - As in sharing_smb, both 'path' and 'name' are
            # required to create a share. When operating on existing
            # shares, we can look up by name or path, and find the
            # other one.
            path=dict(type='str'),
            name=dict(type='str'),
            description=dict(type='str'),       # comment
            ro=dict(type='bool'),
            chown=dict(type='bool'),            # perm
            state=dict(type='str', default='present',
                       choices=['absent', 'present']),
            enabled=dict(type='bool'),
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
    path = module.params['path']
    description = module.params['description']
    ro = module.params['ro']
    chown = module.params['chown']
    state = module.params['state']
    enabled = module.params['enabled']
    # XXX

    # XXX - Look up the share
    try:
        share_info = mw.call("sharing.webdav.query",
                                [["name", "=", name]])
        if len(share_info) == 0:
            # No such share
            share_info = None
        else:
            # Share exists
            share_info = share_info[0]
    except Exception as e:
        module.fail_json(msg=f"Error looking up share {name}: {e}")

    # First, check whether the share even exists.
    if share_info is None:
        # Share doesn't exist

        if state == 'present':
            # Share is supposed to exist, so create it.

            # Collect arguments to pass to sharing.webdav.create()
            arg = {
                "name": name,
                "path": path,
            }

            if description is not None:
                arg['comment'] = description

            if ro is not None:
                arg['ro'] = ro

            if chown is not None:
                arg['perm'] = chown

            if enabled is not None:
                arg['enabled'] = enabled

            if module.check_mode:
                result['msg'] = f"Would have created share {name} with {arg}"
            else:
                #
                # Create new share
                #
                try:
                    err = mw.call("sharing.webdav.create", arg)
                    result['msg'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating share {name}: {e}")

                # Return whichever interesting bits sharing.webdav.create()
                # returned.
                result['share'] = err

            result['changed'] = True
        else:
            # Share is not supposed to exist.
            # All is well
            result['changed'] = False

    else:
        # Share exists
        if state == 'present':
            # Share is supposed to exist

            # Make list of differences between what is and what should
            # be.
            arg = {}

            if chown is not None and share_info['perm'] != chown:
                arg['perm'] = chown

            if ro is not None and share_info['ro'] != ro:
                arg['ro'] = ro

            if description is not None and share_info['comment'] != description:
                arg['comment'] = description

            if path is not None and share_info['path'] != path:
                arg['path'] = path

            if enabled is not None and share_info['enabled'] != enabled:
                arg['enabled'] = enabled

            # If there are any changes, sharing.webdav.update()
            if len(arg) == 0:
                # No changes
                result['changed'] = False
            else:
                #
                # Update share.
                #
                if module.check_mode:
                    result['msg'] = f"Would have updated share {name}: {arg}"
                else:
                    try:
                        err = mw.call("sharing.webdav.update",
                                      share_info['id'],
                                      arg)
                    except Exception as e:
                        module.fail_json(msg=f"Error updating share {name} with {arg}: {e}")
                        # Return any interesting bits from err
                        result['status'] = err['status']
                result['changed'] = True
        else:
            # Share is not supposed to exist

            if module.check_mode:
                result['msg'] = f"Would have deleted share {name}"
            else:
                try:
                    #
                    # Delete share.
                    #
                    err = mw.call("sharing.webdav.delete",
                                  share_info['id'])
                except Exception as e:
                    module.fail_json(msg=f"Error deleting share {name}: {e}")
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
