#!/usr/bin/python
# -*- coding: utf-8 -*-
__metaclass__ = type

DOCUMENTATION = '''
---
module: nfs
short_description: Configure NFS service
description:
  - Configure the NFS service.
  - For individual NFS exports, see C(sharing_nfs)
options:
  udp:
    description:
      - If true, serve UDP clients. Use this if you have NFS clients
        that have to use UDP.
      - This sets the C(-u) option to C(nfsd).
    type: bool
  allow_nonroot:
    description:
      - When true, allow non-root requests to be served.
      - Sets the C(-n) option to C(mountd).
    type: bool
  protocols:
    description:
      - List of supported protocols. The elements are any of
        `nfsv3`, `nfsv4` or their synonyms.
    type: list
    elements: str
    choices:
      - nfsv3
      - nfsv4
      - NFSv3
      - NFSv4
      - v3
      - v4
  nfsv4:
    description:
      - If true, enable NFSv4. Otherwise, use NFSv3.
      - Deprecated. Use `protocols` instead.
    type: bool
  servers:
    description:
      - The number of NFS servers to create. This value is passed
        to the C(-n) parameter of C(nfsd).
    type: int
  v3owner:
    description:
      - Enable the NFSv3 ownership model for NFSv4.
      - Ignored unless NFSv4 is turned on through `protocols` or `nfsv4`.
  krb:
    description:
      - Turn on Kerberos for NFSv4. Forces shares to fail without a
        Kerberos ticket.
      - This enables the C(gssd) daemon.
      - Ignored unless C(nfsv4) is true.
  domain:
    description:
      - Overrides the default DNS domain name for NFSv4.
      - Passes the C(-domain) option to C(nfsuserd).
      - Ignored unless C(nfsv4) is true.
    type: str
  bindip:
    description:
      - List of IP addresses on which to listen for NFS requests.
        When this is the empty list, listen on all available addresses.
    type: list
    elements: str
  mountd_port:
    description:
      - Specifies the port that C(mountd) should bind to.
      - This passes the C(-p) option to C(mountd).
    type: int
  rpcstatd_port:
    description:
      - Specifies the port that C(rpc.statd) binds to.
      - This passes the C(-p) option to C(rpc.statd).
    type: int
  rpclockd_port:
    description:
      - Specifies the port that C(rpc.lockd) binds to.
      - This passes the C(-p) option to C(rpc.lockd).
    type: int
  userd_manage_gids:
    description:
      - Use this when a user is a member of more than 16 groups.
      - Passes the C(-manage-gids) option to C(nfsuserd).
    type: bool
  mountd_log:
    description:
      - When true, log successful mount requests.
      - Passes the C(-l) option to C(mountd).
    type: bool
  statd_lockd_log:
    description:
      - When true, turn on extra logging of C(rpc.statd) and C(rpc.lockd),
        for debugging.
      - Passes the C(-d) flag to C(rpc.statd) and C(-d 10) to
        C(rpc.lockd).
      - These are debugging flags and are not normally needed.
    type: bool
version_added: 0.4.0
'''

EXAMPLES = '''
- name: Enable UDP
  hosts: nfs_server
  become: yes
  tasks:
    - arensb.truenas.nfs:
        udp: yes

- name: Forbid mount requests from non-root accounts
  hosts: nfs_server
  become: yes
  tasks:
    - arensb.truenas.nfs:
        allow_nonroot: false

- name: Run 32 servers
  hosts: nfs_server
  become: yes
  tasks:
    - arensb.truenas.nfs:
        servers: 32

- name: Enable NFS v3 and v4
  hosts: nfs_server
  become: yes
  tasks:
    - arensb.truenas.nfs:
        protocols:
          - NFSv3
          - NFSv4

- name: Enable v4. Disable v3 if possible.
  hosts: nfs_server
  become: yes
  tasks:
    - arensb.truenas.nfs:
        protocols: NFSv4

# `nfsv4` is deprecated.
- name: Enable NFSv4
  hosts: nfs_server
  become: yes
  tasks:
    - arensb.truenas.nfs:
        nfsv4: yes

- name: Enable NFS v3 ownership model under v4
  hosts: nfs_server
  become: yes
  tasks:
    - arensb.truenas.nfs:
        v3owner: true

- name: Turn on Kerberos
  hosts: nfs_server
  become: yes
  tasks:
    - arensb.truenas.nfs:
        krb: true

- name: Listen on a specific interface
'''

RETURN = '''
status:
  description:
    - A data structure describing the state of the NFS service.
    - In check_mode and when no changes are needed, this is the current
      state of the NFS service. When changes have successfully been made,
      this is the new state of the NFS service.
  type: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.middleware import MiddleWare as MW


def main():
    module = AnsibleModule(
        argument_spec=dict(
            servers=dict(type='int'),
            udp=dict(type='bool'),
            allow_nonroot=dict(type='bool'),
            nfsv4=dict(type='bool'),
            protocols=dict(type='list', elements='str',
                           choices=['nfsv3', 'NFSv3', 'NFSV3', 'v3', 'V3',
                                    'nfsv4', 'NFSv4', 'NFSV4', 'v4', 'V4']),
            v3owner=dict(type='bool'),
            krb=dict(type='bool'),
            domain=dict(type='str'),
            bindip=dict(type='list', elements='str'),
            mountd_port=dict(type='int'),
            rpcstatd_port=dict(type='int'),
            rpclockd_port=dict(type='int'),
            userd_manage_gids=dict(type='bool'),
            mountd_log=dict(type='bool'),
            statd_lockd_log=dict(type='bool'),
            ),
        mutually_exclusive=[
            ['nfsv4', 'protocols']
        ],
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW.client()

    # Assign variables from properties, for convenience
    servers = module.params['servers']
    udp = module.params['udp']
    allow_nonroot = module.params['allow_nonroot']
    nfsv4 = module.params['nfsv4']
    protocols = module.params['protocols']
    v3owner = module.params['v3owner']
    krb = module.params['krb']
    domain = module.params['domain']
    bindip = module.params['bindip']
    mountd_port = module.params['mountd_port']
    rpcstatd_port = module.params['rpcstatd_port']
    rpclockd_port = module.params['rpclockd_port']
    userd_manage_gids = module.params['userd_manage_gids']
    mountd_log = module.params['mountd_log']
    statd_lockd_log = module.params['statd_lockd_log']

    # XXX - Debugging
    result['nfsv4'] = nfsv4
    result['protocols'] = protocols

    # Add a table of acceptable synonyms for the protocol names.
    # nfsvN, NFSvN, NFSVN, vN, VN.
    # Make it a dict that maps to the values to pass to midclt: NFSV3, NFSV4.
    protocol_names = {
        "nfsv3": "NFSV3",	"nfsv4": "NFSV4",
        "NFSv3": "NFSV3",	"NFSv4": "NFSV4",
        "NFSV3": "NFSV3",	"NFSV4": "NFSV4",
        "v3": "NFSV3",  	"v4": "NFSV4",
        "V3": "NFSV3",          "V4": "NFSV4",
    }

    # Get the list of protocols that we want. "None" means leave
    # the list alone, whatever it's currently set to. Otherwise, it's
    # a set: protocols in the set should be turned on, and protocols
    # not in the set should be turned off. (Yes, this means that an
    # empty list says to turn off all protocols. I'm not going to stop
    # you from doing stupid things.)
    want_protocols = None
    if protocols is not None:
        want_protocols = set([protocol_names[i] for i in protocols])
    elif nfsv4 is not None:
        if nfsv4:
            want_protocols = set(["NFSV3", "NFSV4"])
        else:
            want_protocols = set(["NFSV3"])
    # XXX - Debugging
    result['want_protocols'] = want_protocols
    try:
        nfs_info = mw.call("nfs.config")
    except Exception as e:
        module.fail_json(msg=f"Error looking up nfs configuration: {e}")

    result['status'] = nfs_info

    # Check whether nfs_info has key 'protocols'. If yes, use
    # protocol syntax. Otherwise, use nfsv4 = bool.
    use_protocols = 'protocols' in nfs_info

    # Make list of differences between what is and what should

    arg = {}

    if servers is not None and nfs_info['servers'] != servers:
        arg['servers'] = servers

    if udp is not None and nfs_info['udp'] is not udp:
        arg['udp'] = udp

    if allow_nonroot is not None and nfs_info['allow_nonroot'] \
       is not allow_nonroot:
        arg['allow_nonroot'] = allow_nonroot

    if want_protocols is not None:
        # The user cares which protocols are enabled.

        if not use_protocols:
            # If you only have a v4 toggle, you're getting v3 whether you
            # want it or not.
            want_protocols.add("NFSV3")

        if 'v4' in nfs_info:
            # This version of TrueNAS uses 'v4'.
            have_protocols = set(['NFSV3', 'NFSV4']) \
                if nfs_info['v4'] else set(['NFSV3'])
        else:
            # This version of TrueNAS uses 'protocols'
            have_protocols = set(nfs_info['protocols'])

        # XXX - Debugging
        result['have_protocols'] = have_protocols

        if have_protocols != want_protocols:
            if use_protocols:
                arg['protocols'] = list(want_protocols)
            else:
                # This isn't perfect: if you specify
                #       protocols: ["NFSV4"]
                #
                # then on TrueNAS SCALE, it turns off v3 and turns on
                # v4. On TrueNAS CORE, it turns on v4 and there's no
                # way to turn off v3.
                arg['v4'] = 'NFSV4' in want_protocols


    if krb is not None and nfs_info['v4_krb'] is not krb:
        arg['v4_krb'] = krb

    if domain is not None and nfs_info['v4_domain'] != domain:
        arg['v4_domain'] = domain

    if bindip is not None and \
       set(bindip) != set(nfs_info['bindip']):
        arg['bindip'] = bindip

    if mountd_port is not None and nfs_info['mountd_port'] != mountd_port:
        arg['mountd_port'] = mountd_port

    if rpcstatd_port is not None and \
       nfs_info['rpcstatd_port'] != rpcstatd_port:
        arg['rpcstatd_port'] = rpcstatd_port

    if rpclockd_port is not None and \
       nfs_info['rpclockd_port'] != rpclockd_port:
        arg['rpclockd_port'] = rpclockd_port

    if userd_manage_gids is not None and \
       nfs_info['userd_manage_gids'] is not userd_manage_gids:
        arg['userd_manage_gids'] = userd_manage_gids

    if mountd_log is not None and nfs_info['mountd_log'] is not mountd_log:
        arg['mountd_log'] = mountd_log

    if statd_lockd_log is not None and \
       nfs_info['statd_lockd_log'] is not statd_lockd_log:
        arg['statd_lockd_log'] = statd_lockd_log

    # If there are any changes, nfs.update()
    if len(arg) == 0:
        # No changes
        result['changed'] = False
    else:
        #
        # Update nfs.
        #
        if module.check_mode:
            result['msg'] = f"Would have updated nfs: {arg}"
        else:
            try:
                err = mw.call("nfs.update",
                              arg)
                result['status'] = err
            except Exception as e:
                module.fail_json(msg=f"Error updating nfs with {arg}: {e}")

        result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
if __name__ == "__main__":
    main()
