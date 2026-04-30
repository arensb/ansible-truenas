#!/usr/bin/python
# -*- coding: utf-8 -*-
__metaclass__ = type

# Manage iSCSI extents.

DOCUMENTATION = '''
---
module: iscsi_extent
short_description: Manage iSCSI extents
description:
  - Create, modify, and delete iSCSI extents.
  - An extent is the storage backing a LUN. It can be a ZFS zvol
    (C(type=DISK)) or a regular file (C(type=FILE)).
  - The dataset/zvol or directory must already exist; this module does
    not create them. Use the C(filesystem) module to manage zvols.
options:
  name:
    description:
      - Name of the extent. Used as the unique identifier.
    type: str
    required: true
  type:
    description:
      - Type of backing store.
      - C(DISK) (default) backs the extent with a ZFS zvol.
      - C(FILE) backs the extent with a regular file on a dataset.
    type: str
    choices: [ DISK, FILE ]
  disk:
    description:
      - Path of the backing zvol relative to C(/dev), in the form
        C(zvol/<pool>/<dataset>). Required when C(type=DISK).
    type: str
  path:
    description:
      - Path of the backing file. Required when C(type=FILE).
    type: str
  filesize:
    description:
      - Size of the backing file in bytes. Must be a multiple of
        C(blocksize). Required and must be non-zero when
        C(type=FILE). Use C(0) for a DISK extent to consume the whole
        zvol.
    type: int
  blocksize:
    description:
      - Logical block size reported to initiators. Default C(512).
    type: int
    choices: [ 512, 1024, 2048, 4096 ]
  pblocksize:
    description:
      - If true, also report the physical block size.
    type: bool
  avail_threshold:
    description:
      - Per-extent free-space alert threshold (percentage). Set to C(0)
        or null to disable.
    type: int
  comment:
    description:
      - Free-form description.
    type: str
  insecure_tpc:
    description:
      - Allow third-party copy (XCOPY/VAAI) without authentication.
    type: bool
  xen:
    description:
      - Enable Xen initiator compatibility mode.
    type: bool
  rpm:
    description:
      - Reported rotation rate. Strings, even for the numeric values.
    type: str
    choices: [ UNKNOWN, SSD, '5400', '7200', '10000', '15000' ]
  ro:
    description:
      - Make the extent read-only.
    type: bool
  enabled:
    description:
      - If false, the extent exists but is not advertised.
    type: bool
  serial:
    description:
      - Unique serial advertised to initiators. If unset, the
        middleware autogenerates one.
    type: str
  delete_file:
    description:
      - When deleting a C(FILE) extent, also remove the backing file
        from disk. Has no effect for C(DISK) extents.
    type: bool
    default: false
  force:
    description:
      - When deleting, bypass safety checks for active sessions.
    type: bool
    default: false
  state:
    description:
      - Whether the extent should exist or not.
    type: str
    choices: [ absent, present ]
    default: present
version_added: 1.15.0
'''

EXAMPLES = '''
- name: Zvol-backed extent
  arensb.truenas.iscsi_extent:
    name: lun0
    type: DISK
    disk: zvol/tank/iscsi/lun0

- name: File-backed extent
  arensb.truenas.iscsi_extent:
    name: lun-file
    type: FILE
    path: /mnt/tank/iscsi/lun-file.img
    filesize: 10737418240

- name: Read-only extent with custom block size
  arensb.truenas.iscsi_extent:
    name: lun-readonly
    type: DISK
    disk: zvol/tank/iscsi/ro
    blocksize: 4096
    ro: true

- name: Delete a FILE extent and remove the backing file
  arensb.truenas.iscsi_extent:
    name: lun-file
    state: absent
    delete_file: true
'''

RETURN = '''
extent:
  description:
    - A dict describing the extent after the operation.
  type: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.middleware import MiddleWare as MW


# Fields the middleware computes/manages and we should not diff against.
_SERVER_MANAGED = {'naa', 'vendor', 'product_id', 'locked', 'id'}


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str', required=True),
            type=dict(type='str', choices=['DISK', 'FILE']),
            disk=dict(type='str'),
            path=dict(type='str'),
            filesize=dict(type='int'),
            blocksize=dict(type='int', choices=[512, 1024, 2048, 4096]),
            pblocksize=dict(type='bool'),
            avail_threshold=dict(type='int'),
            comment=dict(type='str'),
            insecure_tpc=dict(type='bool'),
            xen=dict(type='bool'),
            rpm=dict(type='str',
                     choices=['UNKNOWN', 'SSD',
                              '5400', '7200', '10000', '15000']),
            ro=dict(type='bool'),
            enabled=dict(type='bool'),
            serial=dict(type='str'),
            delete_file=dict(type='bool', default=False),
            force=dict(type='bool', default=False),
            state=dict(type='str', default='present',
                       choices=['absent', 'present']),
        ),
        mutually_exclusive=[
            ['disk', 'path'],
        ],
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW.client()

    name = module.params['name']
    state = module.params['state']
    delete_file = module.params['delete_file']
    force = module.params['force']

    # Diffable input parameters mapped to API field names.
    inputs = {
        'type': module.params['type'],
        'disk': module.params['disk'],
        'path': module.params['path'],
        'filesize': module.params['filesize'],
        'blocksize': module.params['blocksize'],
        'pblocksize': module.params['pblocksize'],
        'avail_threshold': module.params['avail_threshold'],
        'comment': module.params['comment'],
        'insecure_tpc': module.params['insecure_tpc'],
        'xen': module.params['xen'],
        'rpm': module.params['rpm'],
        'ro': module.params['ro'],
        'enabled': module.params['enabled'],
        'serial': module.params['serial'],
    }

    try:
        rows = mw.call("iscsi.extent.query",
                       [["name", "=", name]])
        extent = rows[0] if rows else None
    except Exception as e:
        module.fail_json(msg=f"Error looking up extent {name}: {e}")

    if extent is None:
        if state == 'present':
            extent_type = inputs['type'] or 'DISK'
            if extent_type == 'DISK' and not inputs['disk']:
                module.fail_json(msg=f"Cannot create DISK extent {name}: 'disk' is required")
            if extent_type == 'FILE':
                if not inputs['path']:
                    module.fail_json(msg=f"Cannot create FILE extent {name}: 'path' is required")
                if not inputs['filesize']:
                    module.fail_json(msg=f"Cannot create FILE extent {name}: 'filesize' is required")

            arg = {"name": name}
            for k, v in inputs.items():
                if v is not None:
                    arg[k] = v

            if module.check_mode:
                result['msg'] = f"Would have created extent {name} with {arg}"
            else:
                try:
                    err = mw.call("iscsi.extent.create", arg)
                    result['extent'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating extent {name}: {e}")
            result['changed'] = True
        else:
            result['changed'] = False
    else:
        if state == 'present':
            arg = {}

            for k, v in inputs.items():
                if v is None:
                    continue
                if k in _SERVER_MANAGED:
                    continue
                if extent.get(k) != v:
                    arg[k] = v

            if len(arg) == 0:
                result['changed'] = False
                result['extent'] = extent
            else:
                if module.check_mode:
                    result['msg'] = f"Would have updated extent {name}: {arg}"
                else:
                    try:
                        err = mw.call("iscsi.extent.update",
                                      extent['id'], arg)
                        result['extent'] = err
                    except Exception as e:
                        module.fail_json(msg=f"Error updating extent {name} with {arg}: {e}")
                result['changed'] = True
        else:
            if module.check_mode:
                result['msg'] = f"Would have deleted extent {name} (delete_file={delete_file}, force={force})"
            else:
                try:
                    # iscsi.extent.delete signature: (id, remove, force)
                    mw.call("iscsi.extent.delete",
                            extent['id'], delete_file, force)
                except Exception as e:
                    module.fail_json(msg=f"Error deleting extent {name}: {e}")
            result['changed'] = True

    module.exit_json(**result)


if __name__ == "__main__":
    main()
