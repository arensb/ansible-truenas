#!/usr/bin/python
__metaclass__ = type

# Create and manage NFS shares.

# XXX
DOCUMENTATION='''
module: sharing_nfs
short_description: Manage NFS sharing
description:
  - Create, manage, and delete NFS exports.
options:
  alldirs:
    description:
      - Allows clients to mount any subdirectory of the exported directory.
      - Can only be used on exports that contain only one directory.
    type: bool
  name:
    description:
      - Name for this export group.
      - This will show up as the comment.
    type: str
    default: ""
    required: true
    aliases: [ comment ]
  paths:
    description:
      - List of directories to export.
      - All paths must be in the same filesystem. And if multiple directories
        from the same filesystem are being imported, they must be in the
        same NFS export.
    type: list
    required: true
  quiet:
    description:
      - Suppress certain error messages. This can be used to avoid spamming
        log files with messages about known errors. See exports(5) for
        examples.
    type: bool
  state:
    description:
      - Whether this export should exist or not.
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

from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible_collections.ooblick.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW

def main():
    # XXX - sharing.nfs.create:
    # x paths (array(str))
    # x comment (str)
    # - networks (array(str))
    # - hosts (array(str))
    # - alldirs (bool)
    # - ro (bool)
    # - quiet (bool)
    # - maproot_user (str)
    # - maproot_group (str)
    # - mapall_user (str)
    # - mapall_group (str)
    # - security (array(str))
    # - enabled (bool)
    #
    # windows.win_share:
    # = name
    # = path
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str', required=True, aliases=['comment']),
            paths=dict(type='list', elements='str', required=True),
            state=dict(type='str', default='present',
                       choices=['absent', 'present']),
            alldirs=dict(type='bool'),
            quiet=dict(type='bool'),
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
    paths = module.params['paths']
    state = module.params['state']
    alldirs = module.params['alldirs']
    quiet = module.params['quiet']

    # Look up the share.
    #
    # Use the comment as an identifier. In the general case, we would
    # have to take a set of directories and try to map them to an
    # existing export set. But let's say we're given:
    #
    # - sharing_nfs:
    #     paths:
    #       - /path/to/a
    #     <options>
    #
    # And when we look up the existing exports, we find only one, with
    # paths==['/path/to/b']
    #
    # Does this mean we should export /path/to/a as a new export, and wind
    # up with
    #   - id: 1, paths: [/path/to/b]
    #   - id: 2, paths: [/path/to/a]
    #
    # Or does it mean that the caller originally exported /path/to/b,
    # and now wants to change it to /path/to/a, so we wind up with just:
    #   - id: 1, paths: [/path/to/a]
    #
    # Some special cases can be solved (e.g., when a and b are on
    # different filesystems), but not the general case.

    # Notes:
    #
    # - Two directories in the same export must be in the same zfs
    #   filesystem. You can't have
    #   paths:
    #     - /mnt/pool0/fs0/somedir
    #     - /mnt/pool0/fs1/otherdir
    #
    # - If two directories in the same filesystem are exported, they
    #   must be in the same export set. You can't have:
    #   - sharing_nfs:
    #       name: Export 1
    #       paths: /mnt/pool0/fs0/somedir
    #   - sharing_nfs:
    #       name: Export 2
    #       paths: /mnt/pool0/fs0/otherdir
    #
    #   Here, "somedir" and "otherdir" must be put in the same "sharing_nfs"
    #   block.
    #
    # - Likewise, can't export a directory to different networks in
    #   different exports.

    try:
        export_info = mw.call("sharing.nfs.query",
                                [["comment", "=", name]])
        if len(export_info) == 0:
            # No such export
            export_info = None
        else:
            # Export exists
            export_info = export_info[0]
    except Exception as e:
        module.fail_json(msg=f"Error looking up NFS export {name}: {e}")

    # First, check whether the export even exists.
    if export_info is None:
        # Export doesn't exist

        if state == 'present':
            # Export is supposed to exist, so create it.

            # Collect arguments to pass to sharing.nfs.create()
            arg = {
                "comment": name,
                "paths": paths,
            }

            if alldirs is not None:
                arg['alldirs'] = alldirs

            if quiet is not None:
                arg['quiet'] = quiet

            if module.check_mode:
                result['msg'] = f"Would have created NFS export \"{name}\" with {arg}"
            else:
                #
                # Create new export
                #
                try:
                    err = mw.call("sharing.nfs.create", arg)
                    result['msg'] = err
                except Exception as e:
                    # result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating NFS export \"{name}\": {e}")

                # Return whichever interesting bits sharing.nfs.create()
                # returned.
                # XXX
                result['resource_id'] = err

            result['changed'] = True
        else:
            # NFS export is not supposed to exist.
            # All is well
            result['changed'] = False

    else:
        # NFS export exists
        if state == 'present':
            # It is supposed to exist

            # Make list of differences between what is and what should
            # be.
            arg = {}

            if alldirs is not None and export_info['alldirs'] != alldirs:
                arg['alldirs'] = alldirs

            if quiet is not None and export_info['quiet'] != quiet:
                arg['quiet'] = quiet

            # Check whether the new set of paths is the same as the
            # old set.
            # We use set comparison because the order doesn't matter.
            if set(paths) != set(export_info['paths']):
                arg['paths'] = paths

            # If there are any changes, sharing.nfs.update()
            if len(arg) == 0:
                # No changes
                result['changed'] = False
            else:
                #
                # Update the export.
                #
                if module.check_mode:
                    result['msg'] = f"Would have updated NFS export \"{name}\": {arg}"
                else:
                    try:
                        err = mw.call("sharing.nfs.update",
                                      export_info['id'],
                                      arg)
                    except Exception as e:
                        module.fail_json(msg=f"Error updating NFS export \"{name}\" with {arg}: {e}")
                        # Return any interesting bits from err
                        result['status'] = err['status']
                result['changed'] = True
        else:
            # NFS export is not supposed to exist

            if module.check_mode:
                result['msg'] = f"Would have deleted NFS export \"{name}\"."
            else:
                try:
                    #
                    # Delete NFS export.
                    #
                    err = mw.call("sharing.nfs.delete",
                                  export_info['id'])
                except Exception as e:
                    module.fail_json(msg=f"Error deleting NFS export \"{name}\": {e}")
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
