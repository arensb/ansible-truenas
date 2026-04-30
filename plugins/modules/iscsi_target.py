#!/usr/bin/python
# -*- coding: utf-8 -*-
__metaclass__ = type

# Manage iSCSI targets.

DOCUMENTATION = '''
---
module: iscsi_target
short_description: Manage iSCSI targets
description:
  - Create, modify, and delete iSCSI targets.
  - A target is the IQN that initiators connect to. The target name
    is appended to the iSCSI service C(basename) to form the full IQN.
  - Each target has a list of access C(groups), where each group binds
    a portal, an initiator group, and an authentication setting.
options:
  name:
    description:
      - Name of the target. Combined with the service basename to form
        the full IQN.
    type: str
    required: true
  alias:
    description:
      - Free-form alias.
    type: str
  mode:
    description:
      - Transport mode. C(ISCSI) is the only meaningful value on
        non-FC hardware.
    type: str
    choices: [ ISCSI, FC, BOTH ]
  groups:
    description:
      - List of access groups bound to this target.
    type: list
    elements: dict
    suboptions:
      portal:
        description:
          - C(id) of an C(iscsi_portal) entry.
        type: int
        required: true
      initiator:
        description:
          - C(id) of an C(iscsi_initiator) group, or null to allow all.
        type: int
      authmethod:
        description:
          - Authentication method for this group.
        type: str
        choices: [ NONE, CHAP, CHAP_MUTUAL ]
        default: NONE
      auth:
        description:
          - C(tag) of an C(iscsi_auth) entry. Required if
            C(authmethod) is not C(NONE).
        type: int
  auth_networks:
    description:
      - List of CIDR networks allowed to connect to this target.
        Empty list means "any network".
    type: list
    elements: str
  force:
    description:
      - When deleting, bypass the active-session safety check.
    type: bool
    default: false
  state:
    description:
      - Whether the target should exist or not.
    type: str
    choices: [ absent, present ]
    default: present
version_added: 1.15.0
'''

EXAMPLES = '''
- name: Simple target with one portal, no auth, all initiators
  arensb.truenas.iscsi_target:
    name: tgt0
    groups:
      - portal: 1
        initiator: 1
        authmethod: NONE

- name: Target with CHAP and a network restriction
  arensb.truenas.iscsi_target:
    name: tgt-secure
    alias: "secure target"
    groups:
      - portal: 1
        initiator: 2
        authmethod: CHAP
        auth: 1
    auth_networks:
      - 10.0.0.0/24

- name: Remove target (force, ignoring active sessions)
  arensb.truenas.iscsi_target:
    name: tgt-old
    state: absent
    force: true
'''

RETURN = '''
target:
  description:
    - A dict describing the target after the operation.
  type: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.middleware import MiddleWare as MW


def _normalize_group(g):
    """Reduce a group dict to its diffable fields with stable defaults
    so user-supplied and server-returned groups can be compared."""
    return {
        'portal': g.get('portal'),
        'initiator': g.get('initiator'),
        'authmethod': g.get('authmethod') or 'NONE',
        'auth': g.get('auth'),
    }


def _group_sort_key(g):
    # Coerce None to a stable tuple-comparable sentinel.
    return tuple((-1 if g[k] is None else g[k])
                 for k in ('portal', 'initiator', 'authmethod', 'auth'))


def _groups_equal(a, b):
    # Server stores groups as a set; compare unordered to avoid
    # spurious diffs when the user supplies them in a different order
    # than the API returns.
    if a is None or b is None:
        return a == b
    na = sorted([_normalize_group(g) for g in a], key=_group_sort_key)
    nb = sorted([_normalize_group(g) for g in b], key=_group_sort_key)
    return na == nb


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str', required=True),
            alias=dict(type='str'),
            mode=dict(type='str', choices=['ISCSI', 'FC', 'BOTH']),
            groups=dict(
                type='list', elements='dict',
                options=dict(
                    portal=dict(type='int', required=True),
                    initiator=dict(type='int'),
                    authmethod=dict(type='str',
                                    choices=['NONE', 'CHAP', 'CHAP_MUTUAL'],
                                    default='NONE'),
                    auth=dict(type='int'),
                ),
            ),
            auth_networks=dict(type='list', elements='str'),
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

    name = module.params['name']
    alias = module.params['alias']
    mode = module.params['mode']
    groups = module.params['groups']
    auth_networks = module.params['auth_networks']
    force = module.params['force']
    state = module.params['state']

    try:
        rows = mw.call("iscsi.target.query",
                       [["name", "=", name]])
        target = rows[0] if rows else None
    except Exception as e:
        module.fail_json(msg=f"Error looking up target {name}: {e}")

    if target is None:
        if state == 'present':
            arg = {"name": name}
            if alias is not None:
                arg['alias'] = alias
            if mode is not None:
                arg['mode'] = mode
            if groups is not None:
                arg['groups'] = [_normalize_group(g) for g in groups]
            if auth_networks is not None:
                arg['auth_networks'] = auth_networks

            if module.check_mode:
                result['msg'] = f"Would have created target {name} with {arg}"
            else:
                try:
                    err = mw.call("iscsi.target.create", arg)
                    result['target'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating target {name}: {e}")
            result['changed'] = True
        else:
            result['changed'] = False
    else:
        if state == 'present':
            arg = {}

            if alias is not None and target.get('alias') != alias:
                arg['alias'] = alias

            if mode is not None and target.get('mode') != mode:
                arg['mode'] = mode

            if groups is not None and \
               not _groups_equal(groups, target.get('groups')):
                arg['groups'] = [_normalize_group(g) for g in groups]

            if auth_networks is not None and \
               set(auth_networks) != set(target.get('auth_networks') or []):
                arg['auth_networks'] = auth_networks

            if len(arg) == 0:
                result['changed'] = False
                result['target'] = target
            else:
                if module.check_mode:
                    result['msg'] = f"Would have updated target {name}: {arg}"
                else:
                    try:
                        err = mw.call("iscsi.target.update",
                                      target['id'], arg)
                        result['target'] = err
                    except Exception as e:
                        module.fail_json(msg=f"Error updating target {name} with {arg}: {e}")
                result['changed'] = True
        else:
            if module.check_mode:
                result['msg'] = f"Would have deleted target {name} (force={force})"
            else:
                try:
                    mw.call("iscsi.target.delete", target['id'], force)
                except Exception as e:
                    module.fail_json(msg=f"Error deleting target {name}: {e}")
            result['changed'] = True

    module.exit_json(**result)


if __name__ == "__main__":
    main()
