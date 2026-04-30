#!/usr/bin/python
# -*- coding: utf-8 -*-
__metaclass__ = type

# Manage iSCSI authorized accesses (CHAP entries).

DOCUMENTATION = '''
---
module: iscsi_auth
short_description: Manage iSCSI authorized accesses (CHAP credentials)
description:
  - Create, modify, and delete iSCSI authorized accesses.
  - Each entry holds a CHAP user/secret (and optionally a mutual CHAP
    peer user/secret), and is grouped by an integer C(tag). Multiple
    entries can share a tag; portals and targets reference the tag,
    not the row C(id).
  - The combination of C(tag) and C(user) uniquely identifies a row.
options:
  tag:
    description:
      - Group tag this entry belongs to. Portals and targets reference
        the tag.
    type: int
    required: true
  user:
    description:
      - CHAP username.
    type: str
    required: true
  secret:
    description:
      - CHAP secret. The TrueNAS middleware enforces a length of 12 to
        16 characters.
      - Required when creating a new entry. When updating, the secret is
        only changed if you explicitly supply this option (the existing
        secret cannot be read back, so it is impossible to know whether
        a change is needed - supplying it always counts as a change).
    type: str
    no_log: true
  peeruser:
    description:
      - Mutual-CHAP peer username. Empty disables mutual CHAP.
    type: str
  peersecret:
    description:
      - Mutual-CHAP peer secret. Same length constraints as C(secret).
      - Always counts as a change when supplied (cannot be read back).
    type: str
    no_log: true
  state:
    description:
      - Whether the entry should exist or not.
    type: str
    choices: [ absent, present ]
    default: present
version_added: 1.15.0
'''

EXAMPLES = '''
- name: Create a CHAP entry in group 1
  arensb.truenas.iscsi_auth:
    tag: 1
    user: client1
    secret: somesecret1234

- name: Add a mutual CHAP entry in group 2
  arensb.truenas.iscsi_auth:
    tag: 2
    user: client2
    secret: secret123456
    peeruser: server
    peersecret: peersecret12

- name: Remove a CHAP entry
  arensb.truenas.iscsi_auth:
    tag: 1
    user: client1
    state: absent
'''

RETURN = '''
auth:
  description:
    - A dict describing the CHAP entry after the operation.
    - The C(secret) field is excluded from the return value.
  type: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.middleware import MiddleWare as MW


def _scrub(row):
    """Strip secret fields before returning the row to the user."""
    if not row:
        return row
    out = dict(row)
    out.pop('secret', None)
    out.pop('peersecret', None)
    return out


def main():
    module = AnsibleModule(
        argument_spec=dict(
            tag=dict(type='int', required=True),
            user=dict(type='str', required=True),
            secret=dict(type='str', no_log=True),
            peeruser=dict(type='str'),
            peersecret=dict(type='str', no_log=True),
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

    tag = module.params['tag']
    user = module.params['user']
    secret = module.params['secret']
    peeruser = module.params['peeruser']
    peersecret = module.params['peersecret']
    state = module.params['state']

    try:
        rows = mw.call("iscsi.auth.query",
                       [["tag", "=", tag], ["user", "=", user]])
        row = rows[0] if rows else None
    except Exception as e:
        module.fail_json(msg=f"Error looking up iscsi auth (tag={tag}, user={user}): {e}")

    if row is None:
        if state == 'present':
            if secret is None:
                module.fail_json(
                    msg=f"Cannot create iscsi auth (tag={tag}, user={user}): 'secret' is required")

            arg = {
                "tag": tag,
                "user": user,
                "secret": secret,
            }
            if peeruser is not None:
                arg['peeruser'] = peeruser
            if peersecret is not None:
                arg['peersecret'] = peersecret

            if module.check_mode:
                result['msg'] = f"Would have created iscsi auth (tag={tag}, user={user})"
            else:
                try:
                    err = mw.call("iscsi.auth.create", arg)
                    result['auth'] = _scrub(err)
                except Exception as e:
                    module.fail_json(msg=f"Error creating iscsi auth (tag={tag}, user={user}): {e}")
            result['changed'] = True
        else:
            result['changed'] = False
    else:
        if state == 'present':
            arg = {}

            if peeruser is not None and row.get('peeruser') != peeruser:
                arg['peeruser'] = peeruser

            # Secrets cannot be read back; if the user supplied one,
            # treat it as a requested change.
            if secret is not None:
                arg['secret'] = secret
            if peersecret is not None:
                arg['peersecret'] = peersecret

            if len(arg) == 0:
                result['changed'] = False
                result['auth'] = _scrub(row)
            else:
                if module.check_mode:
                    redacted = {k: ('<set>' if k in ('secret', 'peersecret') else v)
                                for k, v in arg.items()}
                    result['msg'] = f"Would have updated iscsi auth (tag={tag}, user={user}): {redacted}"
                else:
                    try:
                        err = mw.call("iscsi.auth.update", row['id'], arg)
                        result['auth'] = _scrub(err)
                    except Exception as e:
                        module.fail_json(msg=f"Error updating iscsi auth (tag={tag}, user={user}): {e}")
                result['changed'] = True
        else:
            if module.check_mode:
                result['msg'] = f"Would have deleted iscsi auth (tag={tag}, user={user})"
            else:
                try:
                    mw.call("iscsi.auth.delete", row['id'])
                except Exception as e:
                    module.fail_json(msg=f"Error deleting iscsi auth (tag={tag}, user={user}): {e}")
            result['changed'] = True

    module.exit_json(**result)


if __name__ == "__main__":
    main()
