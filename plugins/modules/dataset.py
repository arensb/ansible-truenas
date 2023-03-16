#!/usr/bin/python
__metaclass__ = type

# Manage ZFS datasets.

# XXX
DOCUMENTATION = '''
---
module: dataset
short_description: Manage ZFS datasets
description:
  - Create, delete, and manage ZFS datasets.
options:
  name:
    description:
      - Name of the dataset.
    type: str
    required: true
  state:
    description:
      - Whether the dataset should exist or not.
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
    # XXX - from pool.dataset.create:
    # x name (str)
    # - type: {FILESYSTEM, VOLUME}
    # - volsize (int)
    #   required for type==VOLUME. Should be a multiple of block size.
    # - volblocksize: {512, 1K, 2K, 4K, 8K, 16K, 32K, 64K, 128K}
    #   Only used for type=VOLUME
    # - sparse (bool)
    #   Only used for type=VOLUME
    # - force_size (bool)
    # - comments (str)
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
            # XXX
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
    state = module.params['state']

    # Look up the dataset.
    try:
        # pool.dataset.query has both "id" and "name", which are
        # always the same, it looks like. I think "id" is the
        # middleware database identifier, while "name" is what you'd
        # use while managing ZFS.
        dataset_info = mw.call("pool.dataset.query",
                               [["name", "=", name]])
        if len(dataset_info) == 0:
            # No such dataset
            dataset_info = None
        else:
            # Dataset exists
            dataset_info = dataset_info[0]
    except Exception as e:
        module.fail_json(msg=f"Error looking up dataset {name}: {e}")

    result['info'] = dataset_info

    # First, check whether the dataset even exists.
    if dataset_info is None:
        # Dataset doesn't exist

        if state == 'present':
            # Dataset is supposed to exist, so create it.

            # Collect arguments to pass to dataset.create()
            arg = {
                "name": name,
            }

            # if feature is not None:
            #     arg['feature'] = feature

            if module.check_mode:
                result['msg'] = f"Would have created dataset {name} with {arg}"
            else:
                #
                # Create new dataset
                #
                try:
                    err = mw.call("pool.dataset.create", arg)
                    result['msg'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating dataset {name}: {e}")

                # Return whichever interesting bits dataset.create()
                # returned.
                result['dataset_id'] = err

            result['changed'] = True
        else:
            # Dataset is not supposed to exist.
            # All is well
            result['changed'] = False

    else:
        # Dataset exists
        if state == 'present':
            # Dataset is supposed to exist

            # Make list of differences between what is and what should
            # be.
            arg = {}

            # if feature is not None and dataset_info['feature'] != feature:
            #     arg['feature'] = feature

            # If there are any changes, dataset.update()
            if len(arg) == 0:
                # No changes
                result['changed'] = False
            else:
                #
                # Update dataset.
                #
                if module.check_mode:
                    result['msg'] = f"Would have updated dataset {name}: {arg}"
                else:
                    try:
                        err = mw.call("pool.dataset.update",
                                      dataset_info['id'],
                                      arg)
                    except Exception as e:
                        module.fail_json(msg=f"Error updating dataset {name} with {arg}: {e}")
                        # Return any interesting bits from err
                        result['status'] = err['status']
                result['changed'] = True
        else:
            # Dataset is not supposed to exist

            if module.check_mode:
                result['msg'] = f"Would have deleted dataset {name}"
            else:
                try:
                    #
                    # Delete dataset.
                    #
                    err = mw.call("pool.dataset.delete",
                                  dataset_info['id'])
                except Exception as e:
                    module.fail_json(msg=f"Error deleting dataset {name}: {e}")
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
