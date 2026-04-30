#!/usr/bin/python
# -*- coding: utf-8 -*-
__metaclass__ = type

# Manage iSCSI initiator (host) groups.

DOCUMENTATION = '''
---
module: iscsi_initiator
short_description: Manage iSCSI initiator groups
description:
  - Create, modify, and delete iSCSI initiator (host) groups.
  - An initiator group lists IQNs allowed to access targets that
    reference it. An empty C(initiators) list grants access to ALL
    initiators.
options:
  comment:
    description:
      - Free-form description for the initiator group. Used as the
        identifier because the TrueNAS API does not assign initiator
        groups a stable name.
      - Required.
    type: str
    required: true
    aliases: [ name ]
  initiators:
    description:
      - List of allowed initiator IQNs.
      - An empty list grants access to ALL initiators (the TrueNAS UI
        labels this "Allow All Initiators").
    type: list
    elements: str
  auth_network:
    description:
      - List of CIDR networks allowed to connect.
      - This field exists on C(iscsi.initiator) only on TrueNAS CORE.
        On TrueNAS SCALE / Community Edition the equivalent setting
        is C(auth_networks) on the C(iscsi_target) module. Passing
        the option on a non-CORE host produces a warning and is
        otherwise ignored.
    type: list
    elements: str
  state:
    description:
      - Whether the initiator group should exist or not.
    type: str
    choices: [ absent, present ]
    default: present
version_added: 1.15.0
'''

EXAMPLES = '''
- name: Allow two specific initiators
  arensb.truenas.iscsi_initiator:
    comment: lab-hosts
    initiators:
      - iqn.1993-08.org.debian:01:abc
      - iqn.1993-08.org.debian:01:def

- name: Allow all initiators
  arensb.truenas.iscsi_initiator:
    comment: anyone
    initiators: []

- name: Remove initiator group
  arensb.truenas.iscsi_initiator:
    comment: lab-hosts
    state: absent
'''

RETURN = '''
initiator:
  description:
    - A dict describing the initiator group after the operation.
  type: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.middleware import MiddleWare as MW
from ..module_utils.setup import get_tn_version


def main():
    module = AnsibleModule(
        argument_spec=dict(
            comment=dict(type='str', required=True, aliases=['name']),
            initiators=dict(type='list', elements='str'),
            auth_network=dict(type='list', elements='str'),
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

    comment = module.params['comment']
    initiators = module.params['initiators']
    auth_network = module.params['auth_network']
    state = module.params['state']

    try:
        tn_version = get_tn_version()
    except Exception as e:
        module.fail_json(msg=f"Error getting TrueNAS version: {e}")

    is_core = tn_version['type'] == 'CORE'

    if auth_network is not None and not is_core:
        module.warn("auth_network is only supported on TrueNAS CORE; "
                    "use the iscsi_target module's auth_networks option "
                    "on TrueNAS SCALE / Community Edition. The supplied "
                    "value is ignored.")
        auth_network = None

    try:
        rows = mw.call("iscsi.initiator.query",
                       [["comment", "=", comment]])
        ig = rows[0] if rows else None
    except Exception as e:
        module.fail_json(msg=f"Error looking up initiator group {comment}: {e}")

    if ig is None:
        if state == 'present':
            arg = {"comment": comment}
            if initiators is not None:
                arg['initiators'] = initiators
            if auth_network is not None:
                arg['auth_network'] = auth_network

            if module.check_mode:
                result['msg'] = f"Would have created initiator group {comment} with {arg}"
            else:
                try:
                    err = mw.call("iscsi.initiator.create", arg)
                    result['initiator'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating initiator group {comment}: {e}")
            result['changed'] = True
        else:
            result['changed'] = False
    else:
        if state == 'present':
            arg = {}

            if initiators is not None:
                if set(initiators) != set(ig.get('initiators') or []):
                    arg['initiators'] = initiators

            if auth_network is not None:
                if set(auth_network) != set(ig.get('auth_network') or []):
                    arg['auth_network'] = auth_network

            if len(arg) == 0:
                result['changed'] = False
                result['initiator'] = ig
            else:
                if module.check_mode:
                    result['msg'] = f"Would have updated initiator group {comment}: {arg}"
                else:
                    try:
                        err = mw.call("iscsi.initiator.update",
                                      ig['id'], arg)
                        result['initiator'] = err
                    except Exception as e:
                        result['failed_invocation'] = arg
                        module.fail_json(msg=f"Error updating initiator group {comment} with {arg}: {e}")
                result['changed'] = True
        else:
            if module.check_mode:
                result['msg'] = f"Would have deleted initiator group {comment}"
            else:
                try:
                    mw.call("iscsi.initiator.delete", ig['id'])
                except Exception as e:
                    module.fail_json(msg=f"Error deleting initiator group {comment}: {e}")
            result['changed'] = True

    module.exit_json(**result)


if __name__ == "__main__":
    main()
