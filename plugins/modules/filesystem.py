#!/usr/bin/python
__metaclass__ = type

# Manage ZFS filesystems.

DOCUMENTATION = '''
---
module: filesystem
short_description: Manage ZFS filesystems
description:
  - Create, delete, and manage ZFS filesystems. Currently this is limited
    to just creation and deletion.
options:
  comment:
    description:
      - Comment attached to the filesystem.
    type: str
  name:
    description:
      - Name of the filesystem.
    type: str
    required: true
  state:
    description:
      - Whether the filesystem should exist or not.
    type: str
    choices: [ absent, present ]
    default: present
version_added: 0.3.0
'''

# XXX
EXAMPLES = '''
- name: Create a filesystem
  arensb.truenas.filesystem:
    name: pool0/mydata

- name: Delete a filesystem
  arensb.truenas.filesystem:
    name: pool0/mydata
    state: absent
'''

# XXX
RETURN = '''
filesystem:
  description:
    - A data structure describing the characteristics of a newly-created
      filesystem.
  type: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW


def main():
    # XXX - from pool.dataset.create:
    # x name (str)
    # ! type: {FILESYSTEM, VOLUME}
    # ! volsize (int)
    #   required for type==VOLUME. Should be a multiple of block size.
    # ! volblocksize: {512, 1K, 2K, 4K, 8K, 16K, 32K, 64K, 128K}
    #   Only used for type=VOLUME
    # ! sparse (bool)
    #   Only used for type=VOLUME
    # - force_size (bool)
    # x comments (str)
    # - sync: {STANDARD, ALWAYS, DISABLED}
    # - compression: {OFF, LZ4, GZIP, GZIP-1, GZIP-9, ZSTD, LZJB, ...}
    # - atime: {ON, OFF}
    # - exec: {ON, OFF}
    # - managedby (str)
    # - quota (int or null)
    # - quota_warning (int)
    # - quota_critical (int)
    # - refquota (int or null)
    # - refquota_warning (int)
    # - refquota_critical (int)
    # - reservation (int)
    # - refreservation (int)
    # - special_small_block_size (int)
    # - copies (int)
    # - snapdir {VISIBLE, HIDDEN}
    # - dedupliation {ON, VERIFY, OFF}
    # - checksum {ON, OFF, FLETCHER{2,4}, SHA{256,512}, SKEIN}
    # - readonly {ON, OFF}
    # - recordsize (str)
    # - casesensitivity {SENSITIVE, INSENSITIVE, MIXED}
    # - aclmode {PASSTHROUGH, RESTRICTED}
    # - acltype {NOACL, NFS4ACL, POSIXACL}
    # - share_type {GENERIC, SMB}
    # - xattr {ON, SA}
    # - encryption_options (obj):
    #   - generate_key (bool)
    #   - pbkdf2iters (int)
    #   - algorithm {AES-*-CCM}
    #   - passphrase (str or null)
    #   - key (str or null)
    # - encryption (bool)
    # - inherit_encryption (bool)
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str'),
            state=dict(type='str', default='present',
                       choices=['absent', 'present']),
            comment=dict(type=str),
            # XXX
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
    state = module.params['state']
    comment = module.params['comment']

    # Look up the filesystem.
    try:
        # pool.dataset.query has both "id" and "name", which are
        # always the same, it looks like. I think "id" is the
        # middleware database identifier, while "name" is what you'd
        # use while managing ZFS.
        fs_info = mw.call("pool.dataset.query",
                          [["name", "=", name]])
        if len(fs_info) == 0:
            # No such filesystem
            fs_info = None
        else:
            # Filesystem exists
            fs_info = fs_info[0]

    except Exception as e:
        module.fail_json(msg=f"Error looking up filesystem {name}: {e}")

    result['info'] = fs_info

    # First, check whether the filesystem even exists.
    if fs_info is None:
        # Filesystem doesn't exist

        if state == 'present':
            # Filesystem is supposed to exist, so create it.

            # Collect arguments to pass to dataset.create()
            arg = {
                "name": name,
            }

            if comment is not None:
                arg['comment'] = comment

            if module.check_mode:
                result['msg'] = f"Would have created filesystem {name} with {arg}"
            else:
                #
                # Create new filesystem
                #
                try:
                    err = mw.call("pool.dataset.create", arg)
                    result['msg'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating filesystem {name}: {e}")

                # Returns a long data structure. Looks like the same
                # one that pool.dataset.create() takes, or that
                # pool.dataset.update() returns (I haven't compared
                # them).
                # Looks interesting. Return it.
                result['filesystem'] = err

            result['changed'] = True
        else:
            # Filesystem is not supposed to exist.
            # All is well
            result['changed'] = False

    else:
        # Filesystem exists
        if state == 'present':
            # Filesystem is supposed to exist

            # Make list of differences between what is and what should
            # be.
            arg = {}

            # XXX - Looks like 'comments' is actually an object:
            #    "comments": {
            #      "value": "<comment>",
            #      "rawvalue": "<comment>",
            #      "parsed": "<comment>",
            #      "source": "LOCAL"
            #    },
            #
            # I don't know what the difference is between "value",
            # "rawvalue", and "parsed". Every time I've looked,
            # they've been the same. It doesn't seem to be about
            # escaping \n, or <b>HTML</b>.

            # XXX - If you set the comments to "" (empty string), you
            # wind up with the same data structure, with empty string
            # for all three values.
            # How to delete the comment entirely?

            if comment is not None:
                if "comments" not in fs_info or \
                   "rawvalue" not in fs_info['comments'] or \
                   fs_info['comments']['rawvalue'] != comment:
                    arg['comments'] = comment

            # If there are any changes, filesystem.update()
            if len(arg) == 0:
                # No changes
                result['changed'] = False
            else:
                #
                # Update filesystem.
                #
                if module.check_mode:
                    result['msg'] = f"Would have updated filesystem {name}: {arg}"
                else:
                    try:
                        err = mw.call("pool.dataset.update",
                                      fs_info['id'],
                                      arg)
                    except Exception as e:
                        module.fail_json(msg=f"Error updating filesystem {name} with {arg}: {e}")
                        # Return any interesting bits from err
                        result['status'] = err['status']
                result['changed'] = True
        else:
            # Filesystem is not supposed to exist

            if module.check_mode:
                result['msg'] = f"Would have deleted filesystem {name}"
            else:
                try:
                    #
                    # Delete filesystem.
                    #

                    # XXX - Is it a good idea to just assume
                    # "recursive" by default? The caller has already
                    # had to manually specify "state: absent", so
                    # probably okay.
                    err = mw.call("pool.dataset.delete",
                                  fs_info['id'],
                                  {"recursive": True})
                except Exception as e:
                    module.fail_json(msg=f"Error deleting filesystem {name}: {e}")
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
