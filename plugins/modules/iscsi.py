#!/usr/bin/python
# -*- coding: utf-8 -*-
__metaclass__ = type

# Configure the iSCSI service (global settings).

DOCUMENTATION = '''
---
module: iscsi
short_description: Configure iSCSI service
description:
  - Configure global parameters of the iSCSI (target) service.
  - For individual portals, initiator groups, authorized accesses, extents,
    targets, and target/extent associations, see the C(iscsi_portal),
    C(iscsi_initiator), C(iscsi_auth), C(iscsi_extent), C(iscsi_target),
    and C(iscsi_targetextent) modules.
options:
  basename:
    description:
      - Base part of the iSCSI Qualified Name (IQN).
      - Combined with the target name to form the full IQN advertised by
        the server. Should follow C(iqn.YYYY-MM.<reverse-domain>) form.
    type: str
  isns_servers:
    description:
      - List of iSNS server addresses to register with.
    type: list
    elements: str
  listen_port:
    description:
      - TCP port that the iSCSI target listens on.
      - Default is C(3260).
    type: int
  pool_avail_threshold:
    description:
      - Pool free-space alert threshold, as a percentage. Valid range is
        C(1) to C(99). Omit the parameter to leave the value alone; the
        TrueNAS API does not accept C(0) here.
    type: int
  alua:
    description:
      - Enable Asymmetric Logical Unit Access. Only meaningful on TrueNAS HA
        systems.
    type: bool
version_added: 1.15.0
'''

EXAMPLES = '''
- name: Set the iSCSI base name
  hosts: truenas
  become: yes
  tasks:
    - arensb.truenas.iscsi:
        basename: iqn.2005-10.org.example.ctl

- name: Use a non-default port and register with iSNS
  hosts: truenas
  become: yes
  tasks:
    - arensb.truenas.iscsi:
        listen_port: 3261
        isns_servers:
          - 10.0.0.5

- name: Make sure the iSCSI service is enabled and running
  hosts: truenas
  become: yes
  tasks:
    - arensb.truenas.iscsi:
        basename: iqn.2005-10.org.example.ctl
    - arensb.truenas.service:
        name: iscsitarget
        state: started
        enabled: yes
'''

RETURN = '''
status:
  description:
    - A dict describing the current state of the iSCSI global configuration.
    - In check_mode and when no changes are needed, this is the current
      state. After a successful update, this is the new state.
  type: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.middleware import MiddleWare as MW


def main():
    module = AnsibleModule(
        argument_spec=dict(
            basename=dict(type='str'),
            isns_servers=dict(type='list', elements='str'),
            listen_port=dict(type='int'),
            pool_avail_threshold=dict(type='int'),
            alua=dict(type='bool'),
        ),
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW.client()

    basename = module.params['basename']
    isns_servers = module.params['isns_servers']
    listen_port = module.params['listen_port']
    pool_avail_threshold = module.params['pool_avail_threshold']
    alua = module.params['alua']

    try:
        info = mw.call("iscsi.global.config")
    except Exception as e:
        module.fail_json(msg=f"Error looking up iSCSI global configuration: {e}")

    result['status'] = info

    arg = {}

    if basename is not None and info.get('basename') != basename:
        arg['basename'] = basename

    if isns_servers is not None and \
       set(isns_servers) != set(info.get('isns_servers') or []):
        arg['isns_servers'] = isns_servers

    if listen_port is not None and info.get('listen_port') != listen_port:
        arg['listen_port'] = listen_port

    if pool_avail_threshold is not None and \
       info.get('pool_avail_threshold') != pool_avail_threshold:
        arg['pool_avail_threshold'] = pool_avail_threshold

    if alua is not None and info.get('alua') is not alua:
        arg['alua'] = alua

    if len(arg) == 0:
        result['changed'] = False
    else:
        if module.check_mode:
            result['msg'] = f"Would have updated iscsi global config: {arg}"
        else:
            try:
                err = mw.call("iscsi.global.update", arg)
                result['status'] = err
            except Exception as e:
                module.fail_json(msg=f"Error updating iscsi global config with {arg}: {e}")
        result['changed'] = True

    module.exit_json(**result)


if __name__ == "__main__":
    main()
