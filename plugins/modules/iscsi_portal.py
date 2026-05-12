#!/usr/bin/python
# -*- coding: utf-8 -*-
__metaclass__ = type

# Manage iSCSI portals.

DOCUMENTATION = '''
---
module: iscsi_portal
short_description: Manage iSCSI portals
description:
  - Create, modify, and delete iSCSI portals.
  - A portal binds the iSCSI target service to one or more IP addresses
    on the server, and may optionally require discovery-time CHAP.
options:
  comment:
    description:
      - Free-form description for the portal. Used as the identifier
        because the TrueNAS API does not assign portals a stable name.
      - Required.
    type: str
    required: true
    aliases: [ name ]
  listen:
    description:
      - List of IP addresses the portal listens on. C(0.0.0.0) means
        "listen on all IPv4 addresses".
      - Required when creating a portal.
    type: list
    elements: str
  port:
    description:
      - TCP port the portal listens on. Only used on TrueNAS CORE,
        where the listen port is configured per-portal. Ignored on
        TrueNAS SCALE / Community Edition (use the C(listen_port)
        option of the C(iscsi) module there).
      - Omit to leave the existing port alone on update, or to use
        C(3260) on create.
    type: int
  discovery_authmethod:
    description:
      - Authentication method to require for discovery-phase logins.
      - Removed from C(iscsi.portal) in TrueNAS SCALE 25.04 and replaced
        by C(discovery_auth) on C(iscsi_auth). On 25.04+ this option is
        ignored with a warning.
    type: str
    choices: [ NONE, CHAP, CHAP_MUTUAL ]
  discovery_authgroup:
    description:
      - C(tag) of an C(iscsi_auth) entry to use for discovery
        authentication. Use null (omit) to disable; the TrueNAS API
        does not treat C(0) as "disabled".
      - Removed from C(iscsi.portal) in TrueNAS SCALE 25.04. On 25.04+
        this option is ignored with a warning.
    type: int
  state:
    description:
      - Whether the portal should exist or not.
    type: str
    choices: [ absent, present ]
    default: present
version_added: 1.15.0
'''

EXAMPLES = '''
- name: Listen-on-all portal
  arensb.truenas.iscsi_portal:
    comment: default
    listen:
      - 0.0.0.0

- name: Portal on a non-default port (TrueNAS CORE only)
  arensb.truenas.iscsi_portal:
    comment: alt-port
    listen:
      - 10.0.0.10
    port: 3261

- name: Portal that requires mutual CHAP at discovery (pre-25.04)
  arensb.truenas.iscsi_portal:
    comment: secured
    listen:
      - 10.0.0.10
    discovery_authmethod: CHAP_MUTUAL
    discovery_authgroup: 1

- name: Remove portal
  arensb.truenas.iscsi_portal:
    comment: old-portal
    state: absent
'''

RETURN = '''
portal:
  description:
    - A dict describing the portal after the operation.
  type: dict
'''

from ansible.module_utils.basic import AnsibleModule
from packaging import version
from ..module_utils.middleware import MiddleWare as MW
from ..module_utils.setup import get_tn_version


# TrueNAS SCALE 25.04 (Fangtooth) removed the discovery_auth* fields
# from iscsi.portal; they moved to iscsi.auth.discovery_auth.
TC_25_04 = version.parse("25.04")


def _is_scale_or_ce(tnv):
    return tnv['type'] in {"SCALE", "COMMUNITY_EDITION"}


def _supports_discovery_auth_on_portal(tnv):
    if tnv['type'] == 'CORE':
        return True
    if _is_scale_or_ce(tnv) and tnv['version'] < TC_25_04:
        return True
    return False


def _normalize_listen(items, want_port=False):
    """Reduce middleware listen entries to a comparable form.

    On modern TrueNAS the items are dicts with only ``ip``. On TrueNAS
    CORE they are dicts with ``ip`` and ``port``; ``want_port`` says
    whether the caller wants a tuple including the port (for CORE diff).
    """
    out = []
    for item in items or []:
        if isinstance(item, dict):
            ip = item.get('ip')
            port = item.get('port')
            out.append((ip, port) if want_port else ip)
        else:
            out.append((item, None) if want_port else item)
    return out


def main():
    module = AnsibleModule(
        argument_spec=dict(
            comment=dict(type='str', required=True, aliases=['name']),
            listen=dict(type='list', elements='str'),
            port=dict(type='int'),
            discovery_authmethod=dict(type='str',
                                      choices=['NONE', 'CHAP', 'CHAP_MUTUAL']),
            discovery_authgroup=dict(type='int'),
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
    listen = module.params['listen']
    port = module.params['port']
    discovery_authmethod = module.params['discovery_authmethod']
    discovery_authgroup = module.params['discovery_authgroup']
    state = module.params['state']

    try:
        tn_version = get_tn_version()
    except Exception as e:
        module.fail_json(msg=f"Error getting TrueNAS version: {e}")

    is_core = tn_version['type'] == 'CORE'
    discovery_on_portal = _supports_discovery_auth_on_portal(tn_version)

    if port is not None and not is_core:
        module.warn("'port' is ignored on TrueNAS SCALE / Community "
                    "Edition; configure the listen port via the "
                    "'iscsi' module's listen_port option.")

    if (discovery_authmethod is not None or discovery_authgroup is not None) \
       and not discovery_on_portal:
        module.warn("discovery_authmethod/discovery_authgroup are not "
                    "available on iscsi.portal in TrueNAS SCALE 25.04+; "
                    "use the iscsi_auth module's discovery_auth option "
                    "instead. The supplied values are ignored.")
        discovery_authmethod = None
        discovery_authgroup = None

    def _existing_port_map():
        """Return ip->port for the IPs already on this portal."""
        if not is_core:
            return {}
        return {ip: prt
                for ip, prt in _normalize_listen(
                    (portal or {}).get('listen'), want_port=True)
                if prt is not None}

    def build_listen(ip_list):
        if not is_core:
            return [{"ip": ip} for ip in ip_list]
        existing = _existing_port_map()
        out = []
        for ip in ip_list:
            # Explicit port wins; otherwise reuse the existing port for
            # this IP if known; otherwise fall back to 3260 on create.
            if port is not None:
                prt = port
            elif ip in existing:
                prt = existing[ip]
            else:
                prt = 3260
            out.append({"ip": ip, "port": prt})
        return out

    try:
        rows = mw.call("iscsi.portal.query",
                       [["comment", "=", comment]])
        portal = rows[0] if rows else None
    except Exception as e:
        module.fail_json(msg=f"Error looking up portal {comment}: {e}")

    if portal is None:
        if state == 'present':
            if not listen:
                module.fail_json(msg=f"Cannot create portal {comment}: 'listen' is required")

            arg = {
                "comment": comment,
                "listen": build_listen(listen),
            }
            if discovery_authmethod is not None:
                arg['discovery_authmethod'] = discovery_authmethod
            if discovery_authgroup is not None:
                arg['discovery_authgroup'] = discovery_authgroup

            if module.check_mode:
                result['msg'] = f"Would have created portal {comment} with {arg}"
            else:
                try:
                    err = mw.call("iscsi.portal.create", arg)
                    result['portal'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating portal {comment}: {e}")
            result['changed'] = True
        else:
            result['changed'] = False
    else:
        if state == 'present':
            arg = {}

            if listen is not None:
                if is_core:
                    current = set(_normalize_listen(portal.get('listen'),
                                                    want_port=True))
                    desired = {(item['ip'], item['port'])
                               for item in build_listen(listen)}
                else:
                    current = set(_normalize_listen(portal.get('listen')))
                    desired = set(listen)
                if desired != current:
                    arg['listen'] = build_listen(listen)

            if discovery_authmethod is not None and \
               portal.get('discovery_authmethod') != discovery_authmethod:
                arg['discovery_authmethod'] = discovery_authmethod

            if discovery_authgroup is not None and \
               portal.get('discovery_authgroup') != discovery_authgroup:
                arg['discovery_authgroup'] = discovery_authgroup

            if len(arg) == 0:
                result['changed'] = False
                result['portal'] = portal
            else:
                if module.check_mode:
                    result['msg'] = f"Would have updated portal {comment}: {arg}"
                else:
                    try:
                        err = mw.call("iscsi.portal.update",
                                      portal['id'], arg)
                        result['portal'] = err
                    except Exception as e:
                        result['failed_invocation'] = arg
                        module.fail_json(msg=f"Error updating portal {comment} with {arg}: {e}")
                result['changed'] = True
        else:
            if module.check_mode:
                result['msg'] = f"Would have deleted portal {comment}"
            else:
                try:
                    mw.call("iscsi.portal.delete", portal['id'])
                except Exception as e:
                    module.fail_json(msg=f"Error deleting portal {comment}: {e}")
            result['changed'] = True

    module.exit_json(**result)


if __name__ == "__main__":
    main()
