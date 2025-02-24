#!/usr/bin/python
__metaclass__ = type

# Create and manage SMB shares.

DOCUMENTATION = '''
---
module: sharing_smb
short_description: Manage SMB sharing
description:
  - Create, manage, and delete SMB shares.
options:
  abe:
    description:
      - Enable Access Based Share Enumeration.
    type: bool
  acl:
    description:
      - When set, enables ACL support for the share.
    type: bool
  apple_encoding:
    description:
      - Use Apple-style character encoding.
      - By default, Samba uses a hashing algorithm for filename characters
        that are illegal in NTFS. This option causes it to translate such
        characters to the Unicode private range.
    type: bool
  auxsmbconf:
    description:
      - Additional smb4.conf options.
    type: str
  browsable:
    description:
      - If true, share is visible when browsing shares.
    type: bool
  comment:
    description:
      - Description of the share, for the system maintainer.
    type: str
  durablehandle:
    description:
      - Enables using file handles that can withstand short disconnections.
      - Enables support for POSIX byte-range locks.
    type: bool
  enabled:
    description:
      - If true, the share is enabled. Otherwise, it is present but
        disabled.
    type: bool
  fsrvp:
    description:
      - Enable File Server Remote VSS Protocol (FSRVP).
      - This allows RPC clients to manage snapshots for the share.
    type: bool
  guestok:
    description:
      - Enables guest access (no login).
    type: str
  hostsallow:
    description:
      - List of hostnames/IP addresses of hosts that are allowed access
        to the share.
      - If C(hostsallow) and C(hostsdeny) conflict, C(hostsallow) takes
        precedence.
    type: list
    elements: str
  home:
    description:
      - If true, this share may be used for home directories.
      - Only one such share is allowed.
  hostsdeny:
    description:
      - List of hostnames/IP addresses of hosts that are denied access
        to the share.
      - If C(hostsallow) and C(hostsdeny) conflict, C(hostsallow) takes
        precedence.
    type: list
    elements: str
  name:
    description:
      - Name of the share, as seen by the SMB client.
    type: str
    required: true
  path:
    description:
      - Directory to share, on the server.
    type: str
    required: true
  path_suffix:
    description:
      - Suffix appended to the share connection path. This may contain
        macros, as defined in smb.conf(5).
    type: str
  purpose:
    description:
      - |
        Specifies a family of configuration parameters for different use
        cases. Legal values include:
      - C(NO_PRESET), C(DEFAULT_SHARE), C(ENHANCED_TIMEMACHINE),
        C(MULTI_PROTOCOL_APP), C(MULTI_PROTOCOL_NFS), C(PRIVATE_DATASETS),
        C(WORM_DROPBOX).
      - Note that the C(purpose) parameter may override other parameters.
        In particular, C(DEFAULT_SHARE) specifies an empty C(hostsallow)
        and C(hostsdeny).
  recyclebin:
    description:
      - |
        If true, enables Windows Recycle Bin: deleted files are moved to the
        Recycle Bin. If false, deleted files are immediately deleted.
    type: bool
  ro:
    description:
      - If true, share is read-only.
    type: bool
  shadowcopy:
    description:
      - When set, export ZFS snapshots as VSS shadow copies.
    type: bool
  state:
    description:
      - Whether the share should exist or not.
    type: str
    choices: [ absent, present ]
    default: present
  streams:
    description:
      - Allow multiple NTFS data streams.
  timemachine:
    description:
      - Enables support for Apple Time Machine backups.
    type: bool
version_added: 1.4.3
'''

EXAMPLES = '''
- name: Simple default share
  sharing_smb:
    name: export1
    path: /mnt/path1

- name: Share with host lists
  sharing_smb:
    name: export2
    path: /mnt/path2
    comment: "Shared to just a few hosts."
    purpose: NO_PRESET
    hostsallow:
      - host1.dom.ain
      - host2.dom.ain
      - 10.2.3.0/24
    hostsdeny:
      - ALL
'''

# XXX - Add 'sample:' for when a share is created.
RETURN = '''
share:
  description:
    - A data structure describing a newly-created share.
  type: dict
status:
  description:
    - When this module exits abnormally, C(status) contains an error message.
  type: str
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type='str', required=True),
            name=dict(type='str', required=True),
            state=dict(type='str', default='present',
                       choices=['absent', 'present']),
            purpose=dict(type='str',
                         choices=['NO_PRESET', 'DEFAULT_SHARE',
                                  'ENHANCED_TIMEMACHINE', 'MULTI_PROTOCOL_AFP',
                                  'MULTI_PROTOCOL_NFS', 'PRIVATE_DATASETS',
                                  'WORM_DROPBOX']),
            hostsallow=dict(type='list', elements='str'),
            hostsdeny=dict(type='list', elements='str'),
            enabled=dict(type='bool'),
            path_suffix=dict(type='str'),
            comment=dict(type='str'),
            auxsmbconf=dict(type='str'),
            home=dict(type='bool'),
            ro=dict(type='bool'),
            browsable=dict(type='bool'),
            timemachine=dict(type='bool'),
            recyclebin=dict(type='bool'),
            guestok=dict(type='bool'),
            abe=dict(type='bool'),
            apple_encoding=dict(type='bool'),
            acl=dict(type='bool'),
            durablehandle=dict(type='bool'),
            shadowcopy=dict(type='bool'),
            streams=dict(type='bool'),
            fsrvp=dict(type='bool'),
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
    path = module.params['path']
    state = module.params['state']
    purpose = module.params['purpose']
    hostsallow = module.params['hostsallow']
    hostsdeny = module.params['hostsdeny']
    enabled = module.params['enabled']
    path_suffix = module.params['path_suffix']
    comment = module.params['comment']
    auxsmbconf = module.params['auxsmbconf']
    is_home = module.params['home']
    is_ro = module.params['ro']
    browsable = module.params['browsable']
    timemachine = module.params['timemachine']
    recyclebin = module.params['recyclebin']
    guestok = module.params['guestok']
    is_abe = module.params['abe']
    apple_encoding = module.params['apple_encoding']
    has_acl = module.params['acl']
    durablehandle = module.params['durablehandle']
    shadowcopy = module.params['shadowcopy']
    streams = module.params['streams']
    fsrvp = module.params['fsrvp']

    # Look up the share
    try:
        share_info = mw.call("sharing.smb.query",
                             [["path", "=", path]])
        if len(share_info) == 0:
            # No such share
            share_info = None
        else:
            # share exists
            share_info = share_info[0]
    except Exception as e:
        module.fail_json(msg=f"Error looking up share {name}: {e}")

    # First, check whether the share even exists.
    if share_info is None:
        # Share doesn't exist

        if state == 'present':
            # Share is supposed to exist, so create it.

            # Collect arguments to pass to sharing.smb.create()
            arg = {
                "path": path,
                "name": name,
            }

            if purpose is not None:
                arg['purpose'] = purpose

            if hostsallow is not None:
                arg['hostsallow'] = hostsallow

            if hostsdeny is not None:
                arg['hostsdeny'] = hostsdeny

            if enabled is not None:
                arg['enabled'] = enabled

            if path_suffix is not None:
                arg['path_suffix'] = path_suffix

            if comment is not None:
                arg['comment'] = comment

            if auxsmbconf is not None:
                arg['auxsmbconf'] = auxsmbconf

            if is_home is not None:
                arg['home'] = is_home

            if is_ro is not None:
                arg['ro'] = is_ro

            if browsable is not None:
                arg['browsable'] = browsable

            if timemachine is not None:
                arg['timemachine'] = timemachine

            if recyclebin is not None:
                arg['recyclebin'] = recyclebin

            if guestok is not None:
                arg['guestok'] = guestok

            if is_abe is not None:
                arg['abe'] = is_abe

            if apple_encoding is not None:
                arg['aapl_name_mangling'] = apple_encoding

            if has_acl is not None:
                arg['acl'] = has_acl

            if durablehandle is not None:
                arg['durablehandle'] = durablehandle

            if shadowcopy is not None:
                arg['shadowcopy'] = shadowcopy

            if streams is not None:
                arg['streams'] = streams

            if fsrvp is not None:
                arg['fsrvp'] = fsrvp

            if module.check_mode:
                result['msg'] = f"Would have created share {name} with {arg}"
            else:
                #
                # Create new share
                #
                try:
                    err = mw.call("sharing.smb.create", arg)
                    result['msg'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating share {name}: {e}")

                # Return whichever interesting bits sharing.smb.create()
                # returned.
                result['share'] = err

            result['changed'] = True
        else:
            # Share is not supposed to exist.
            # All is well
            result['changed'] = False

    else:
        # Share exists
        if state == 'present':
            # Share is supposed to exist

            # Make list of differences between what is and what should
            # be.
            arg = {}

            if name is not None and \
               share_info['name'] != name:
                arg['name'] = name

            if purpose is not None:
                if share_info['purpose'] != purpose:
                    arg['purpose'] = purpose

            # For hostsallow and hostsdeny, order doesn't matter, so
            # compare them as sets.
            if hostsallow is not None:
                if set(hostsallow) != set(share_info['hostsallow']):
                    arg['hostsallow'] = hostsallow

            if hostsdeny is not None:
                if set(hostsdeny) != set(share_info['hostsdeny']):
                    arg['hostsdeny'] = hostsdeny

            if enabled is not None and \
               share_info['enabled'] != enabled:
                arg['enabled'] = enabled

            if path_suffix is not None and \
               share_info['path_suffix'] != path_suffix:
                arg['path_suffix'] = path_suffix

            if comment is not None and \
               share_info['comment'] != comment:
                arg['comment'] = comment

            if auxsmbconf is not None and \
               share_info['auxsmbconf'] != auxsmbconf:
                arg['auxsmbconf'] = auxsmbconf

            if is_home is not None and \
               share_info['home'] != is_home:
                arg['home'] = is_home

            if is_ro is not None and \
               share_info['ro'] != is_ro:
                arg['ro'] = is_ro

            if browsable is not None and \
               share_info['browsable'] != browsable:
                arg['browsable'] = browsable

            if timemachine is not None and \
               share_info['timemachine'] != timemachine:
                arg['timemachine'] = timemachine

            if recyclebin is not None and \
               share_info['recyclebin'] != recyclebin:
                arg['recyclebin'] = recyclebin

            if guestok is not None and \
               share_info['guestok'] != guestok:
                arg['guestok'] = guestok

            if is_abe is not None and \
               share_info['abe'] != is_abe:
                arg['abe'] = is_abe

            if apple_encoding is not None and \
               share_info['aapl_name_mangling'] != apple_encoding:
                arg['aapl_name_mangling'] = apple_encoding

            if has_acl is not None and \
               share_info['acl'] != has_acl:
                arg['acl'] = has_acl

            if durablehandle is not None and \
               share_info['durablehandle'] != durablehandle:
                arg['durablehandle'] = durablehandle

            if shadowcopy is not None and \
               share_info['shadowcopy'] != shadowcopy:
                arg['shadowcopy'] = shadowcopy

            if streams is not None and \
               share_info['streams'] != streams:
                arg['streams'] = streams

            if fsrvp is not None and \
               share_info['fsrvp'] != fsrvp:
                arg['fsrvp'] = fsrvp

            # If there are any changes, sharing.smb.update()
            if len(arg) == 0:
                # No changes
                result['changed'] = False
            else:
                #
                # Update share.
                #
                if module.check_mode:
                    result['msg'] = f"Would have updated share {name}: {arg}"
                else:
                    try:
                        err = mw.call("sharing.smb.update",
                                      share_info['id'],
                                      arg)
                    except Exception as e:
                        module.fail_json(msg=f"Error updating share {name} with {arg}: {e}")
                        # Return any interesting bits from err
                        result['status'] = err['status']
                result['changed'] = True
        else:
            # Share is not supposed to exist

            if module.check_mode:
                result['msg'] = f"Would have deleted share {name}"
            else:
                try:
                    #
                    # Delete share.
                    #
                    err = mw.call("sharing.smb.delete",
                                  share_info['id'])
                except Exception as e:
                    module.fail_json(msg=f"Error deleting share {name}: {e}")
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
