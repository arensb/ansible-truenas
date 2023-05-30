#!/usr/bin/python
__metaclass__ = type

# Create and manage SMB shares.

# XXX - name is unique. path isn't.

# XXX
DOCUMENTATION = '''
---
module: sharing_smb
short_description: Manage SMB sharing
description:
  - Create, manage, and delete SMB shares.
options:
  name:
    description:
      - Name of the share, as seen by the SMB client.
    type: str
    required: true
  path:
    description:
      - Directory to share, on the server.
    type: str
    required: true
  state:
    description:
      - Whether the share should exist or not.
    type: str
    choices: [ absent, present ]
    default: present
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
    # XXX - Parameters:
    # ! purpose: NO_PRESET, DEFAULT_SHARE, ENHANCED_TIMEMACHINE,
    #   MULTI_PROTOCOL_APP, MULTI_PROTOCOL_NFS, PRIVATE_DATASETS, WORM_DROPBOX
    #   These are canned configurations. Ignore.
    # x path (str) - directory to share
    #   (require)
    # - path_suffix (str): Appended to the share connection path.
    #   May contain macros. See smb.conf(5).
    # - home (bool): Allows the share to host home directories.
    #   Only one such share is allowed.
    # x name (str): (human-readable?) name of the share. Required.
    #   How share will appear in client's network browser.
    # - comment (str): Description or notes for the system maintainer.
    # - ro (bool): Read-only
    # - browsable (bool): if true (default), is visible when browsing shares.
    # - timemachine (bool): Enables Time Machine backups.
    # - recyclebin (bool): Enable Recycle Bin: deleted files are moved
    #   to the Recycle Bin, not deleted permanently as with NFS.
    # - guestok (bool): Allows passwordless access
    # - abe (bool): Access Based Share Enumeration(?): restrict visibility
    #   to only those who have read or write access.
    # - hostsallow (list): List of hostnames/IP addresses that have access.
    #   https://www.samba.org/samba/docs/current/man-html/smb.conf.5.html#HOSTSALLOW
    # - hostsdeny (list): List of hostnames/IP addresses that are explicitly
    #   denied access. Can be "ALL", to deny access to any that aren't allowed.
    # - aapl_name_mangling (bool)
    # - acl (bool): store SMB Security Descriptor as filesystem ACL.
    # - durablehandle (bool)
    # - shadowcopy (bool): enables volume shadow copy service.
    # - streams (bool): "enables support for storing alternate datastreams
    #   as filesystem extended attributes."
    # - fsrvp (bool): filesystem remote VSS protocol.
    # - auxsmbconf (str): additional smb4.conf parameters.
    # - enabled (bool)
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type='str', required=True),
            name=dict(type='str', required=True),
            state=dict(type='str', default='present',
                       choices=['absent', 'present']),
            ),
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW()

    # Assign variables from properties, for convenience
    name = module.params['name']
    path = module.params['path']
    state = module.params['state']

    # Look up the share
    try:
        share_info = mw.call("sharing.smb.query",
                             [["path", "=", path]])
        if len(share_info) == 0:
            # No such share
            share_info = None
        else:
            # share exists
            share_info = share_info[0]
    except Exception as e:
        module.fail_json(msg=f"Error looking up share {name}: {e}")

    # First, check whether the share even exists.
    if share_info is None:
        # Share doesn't exist

        if state == 'present':
            # Share is supposed to exist, so create it.

            # Collect arguments to pass to sharing.smb.create()
            arg = {
                "path": path,
                "name": name,
            }

            # if feature is not None:
            #     arg['feature'] = feature

            if module.check_mode:
                result['msg'] = f"Would have created share {name} with {arg}"
            else:
                #
                # Create new share
                #
                try:
                    err = mw.call("sharing.smb.create", arg)
                    result['msg'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating share {name}: {e}")

                # Return whichever interesting bits sharing.smb.create()
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

            # if feature is not None and share_info['feature'] != feature:
            #     arg['feature'] = feature

            # If there are any changes, sharing.smb.update()
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
                        err = mw.call("sharing.smb.update",
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
                    err = mw.call("sharing.smb.delete",
                                  share_info['id'])
                except Exception as e:
                    module.fail_json(msg=f"Error deleting share {name}: {e}")
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
