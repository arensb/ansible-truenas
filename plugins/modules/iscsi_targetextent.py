#!/usr/bin/python
# -*- coding: utf-8 -*-
__metaclass__ = type

# Manage iSCSI target/extent associations (LUNs).

DOCUMENTATION = '''
---
module: iscsi_targetextent
short_description: Manage iSCSI target/extent associations (LUNs)
description:
  - Create, modify, and delete LUN bindings between an iSCSI target and
    an extent.
  - Identified by the C((target, extent)) pair. The C(lunid) is the
    LUN number presented to initiators; if not specified on create,
    the middleware picks the lowest free value.
options:
  target:
    description:
      - C(id) of an C(iscsi_target) row.
    type: int
    required: true
  extent:
    description:
      - C(id) of an C(iscsi_extent) row.
    type: int
    required: true
  lunid:
    description:
      - LUN number to advertise. Auto-assigned (lowest free) if unset
        on create.
    type: int
  force:
    description:
      - When deleting, bypass the active-session safety check.
    type: bool
    default: false
  state:
    description:
      - Whether the association should exist or not.
    type: str
    choices: [ absent, present ]
    default: present
version_added: 1.15.0
'''

EXAMPLES = '''
- name: Bind extent 5 to target 2 as LUN 0
  arensb.truenas.iscsi_targetextent:
    target: 2
    extent: 5
    lunid: 0

- name: Auto-assign LUN
  arensb.truenas.iscsi_targetextent:
    target: 2
    extent: 6

- name: Remove association
  arensb.truenas.iscsi_targetextent:
    target: 2
    extent: 5
    state: absent
'''

RETURN = '''
targetextent:
  description:
    - A dict describing the target/extent association after the operation.
  type: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.middleware import MiddleWare as MW


def main():
    module = AnsibleModule(
        argument_spec=dict(
            target=dict(type='int', required=True),
            extent=dict(type='int', required=True),
            lunid=dict(type='int'),
            force=dict(type='bool', default=False),
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

    target = module.params['target']
    extent = module.params['extent']
    lunid = module.params['lunid']
    force = module.params['force']
    state = module.params['state']

    label = f"target={target}, extent={extent}"

    try:
        rows = mw.call("iscsi.targetextent.query",
                       [["target", "=", target], ["extent", "=", extent]])
        row = rows[0] if rows else None
    except Exception as e:
        module.fail_json(msg=f"Error looking up targetextent ({label}): {e}")

    if row is None:
        if state == 'present':
            arg = {"target": target, "extent": extent}
            if lunid is not None:
                arg['lunid'] = lunid

            if module.check_mode:
                result['msg'] = f"Would have created targetextent ({label}) with {arg}"
            else:
                try:
                    err = mw.call("iscsi.targetextent.create", arg)
                    result['targetextent'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating targetextent ({label}): {e}")
            result['changed'] = True
        else:
            result['changed'] = False
    else:
        if state == 'present':
            arg = {}
            if lunid is not None and row.get('lunid') != lunid:
                arg['lunid'] = lunid

            if len(arg) == 0:
                result['changed'] = False
                result['targetextent'] = row
            else:
                if module.check_mode:
                    result['msg'] = f"Would have updated targetextent ({label}): {arg}"
                else:
                    try:
                        err = mw.call("iscsi.targetextent.update",
                                      row['id'], arg)
                        result['targetextent'] = err
                    except Exception as e:
                        result['failed_invocation'] = arg
                        module.fail_json(msg=f"Error updating targetextent ({label}) with {arg}: {e}")
                result['changed'] = True
        else:
            if module.check_mode:
                result['msg'] = f"Would have deleted targetextent ({label}, force={force})"
            else:
                try:
                    mw.call("iscsi.targetextent.delete", row['id'], force)
                except Exception as e:
                    module.fail_json(msg=f"Error deleting targetextent ({label}): {e}")
            result['changed'] = True

    module.exit_json(**result)


if __name__ == "__main__":
    main()
