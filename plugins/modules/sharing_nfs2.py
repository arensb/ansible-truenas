#!/usr/bin/python
__metaclass__ = type

# Create and manage NFS shares.

# XXX
DOCUMENTATION = '''
---
module: sharing_nfs
short_description: Manage NFS sharing
description:
  - Create, manage, and delete NFS exports.
options:
  alldirs:
    description:
      - Allows clients to mount any subdirectory of the exported directory.
      - Can only be used on exports that contain only one directory.
      - False by default when a share is created.
    type: bool
  enabled:
    description:
      - Whether or not this export should be enabled.
      - Exports that are not enabled exist in the middleware database,
        but are not listed in C(/etc/exports).
      - True by default when a share is created.
    type: bool
  hosts:
    description:
      - List of allowed hosts, either hostnames or addresses.
      - An empty list means to allow all.
    type: list
  mapall_user:
    description:
      - All requests (including by root) are limited to the permissions
        of this user.
      - Set to the empty string (C("")) to remove this setting.
      - Mutually-exclusive with C(maproot_user).
    type: str
  mapall_group:
    description:
      - All requests (including by root) are limited to the permissions
        of this group.
      - Set to the empty string (C("")) to remove this setting.
      - Mutually-exclusive with C(maproot_group).
      - Requires C(mapall_user).
    type: str
  maproot_user:
    description:
      - Requests by user root are limited to the permissions of this user.
      - Set to the empty string (C("")) to remove this setting.
      - Mutually-exclusive with C(mapall_user).
    type: str
  maproot_group:
    description:
      - Requests by user root are also limited to the permissions of
        this group.
      - Set to the empty string (C("")) to remove this setting.
      - Mutually-exclusive with C(mapall_group).
      - Requires C(maproot_user).
    type: str
  name:
    description:
      - Name for this export group.
      - This will show up as the comment.
    type: str
    default: ""
    required: true
    aliases: [ comment ]
  networks:
    description:
      - List of allowed networks, in CIDR notation.
      - An empty list means to allow all.
      - Note that using incorrect CIDR may lead to this module seeing a
        change when nothing has changed. For example, if you specify
        "10.1.2.3/16", TrueNAS will normalize this to "10.1.0.0/16", but
        afterward, this module will think that you want to make a change.
    type: list
  path:
    description:
      - A directory to export.
    type: str
    required: true
  quiet:
    description:
      - Suppress certain error messages. This can be used to avoid spamming
        log files with messages about known errors. See exports(5) for
        examples.
      - False by default when a share is created.
    type: bool
  readonly:
    description:
      - Whether the directories are exported read-only, to prohibit clients
        from writing to them.
    type: bool
    aliases: [ ro, read_only ]
  state:
    description:
      - Whether this export should exist or not.
    type: str
    choices: [ absent, present ]
    default: present
'''

# XXX
EXAMPLES = '''
- name: Export a filesystem
  arensb.truenas.sharing_nfs:
    - name: Home export
      path: /mnt/pool0/home

- name: Export to only one network
  arensb.truenas.sharing_nfs:
    - name: Home export
      path: /mnt/pool0/home
      networks:
        - 192.168.0.0/16

- name: Explicitly export to all hosts and networks
  arensb.truenas.sharing_nfs:
    - name: Home export
      path: /mnt/pool0/home
      hosts: []
      networks: []
'''

# XXX
RETURN = '''
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW

# XXX - Maybe correct bad CIDR? I think it might be as simple as:
# import ipaddress
# network = str(ipaddress.ip_network('10.1.2.3/16', False))
# => '10.1.0.0/16'


def main():
    # XXX - One important use case isn't addressed: ensure that
    # /mnt/path is _not_ exported.
    #
    # Unfortunately, since we use 'name' as an identifier, this is
    # hard to check. So maybe require 'name' only if 'state==present'.
    #
    # It's probably cleaner to have separate functions for
    # state==present and state==absent.

    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str', required=True, aliases=['comment']),
            path=dict(type='str', required=True),
            state=dict(type='str', default='present',
                       choices=['absent', 'present']),
            alldirs=dict(type='bool'),
            quiet=dict(type='bool'),
            enabled=dict(type='bool'),
            readonly=dict(type='bool'),
            maproot_user=dict(type='str'),
            maproot_group=dict(type='str'),
            mapall_user=dict(type='str'),
            mapall_group=dict(type='str'),
            networks=dict(type='list', elements='str'),
            hosts=dict(type='list', elements='str'),
        ),
        supports_check_mode=True,
        mutually_exclusive=[
            ['maproot_user', 'mapall_user'],
            ['maproot_group', 'mapall_group'],
        ],
        required_by=dict(
            # Can't have map*_group without its corresponding map*_user.
            maproot_group=('maproot_user'),
            mapall_group=('mapall_user'),
        ),
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW()

    # Assign variables from properties, for convenience
    name = module.params['name']
    path = module.params['path']
    state = module.params['state']
    alldirs = module.params['alldirs']
    quiet = module.params['quiet']
    enabled = module.params['enabled']
    readonly = module.params['readonly']
    maproot_user = module.params['maproot_user']
    maproot_group = module.params['maproot_group']
    mapall_user = module.params['mapall_user']
    mapall_group = module.params['mapall_group']
    networks = module.params['networks']
    hosts = module.params['hosts']

    # Look up the share.
    # Use the comment as an identifier. 
    try:
        export_info = mw.call("sharing.nfs.query",
                              [["comment", "=", name]])
        if len(export_info) == 0:
            # No such export
            export_info = None
        else:
            # Export exists
            export_info = export_info[0]
    except Exception as e:
        module.fail_json(msg=f"Error looking up NFS export {name}: {e}")

    # First, check whether the export even exists.
    if export_info is None:
        # Export doesn't exist

        if state == 'present':
            # Export is supposed to exist, so create it.

            # Collect arguments to pass to sharing.nfs.create()
            arg = {
                "comment": name,
                "path": path,
            }

            if alldirs is not None:
                arg['alldirs'] = alldirs

            if quiet is not None:
                arg['quiet'] = quiet

            if enabled is not None:
                arg['enabled'] = enabled

            if readonly is not None:
                arg['ro'] = readonly

            if maproot_user is not None:
                arg['maproot_user'] = maproot_user

            if maproot_group is not None:
                arg['maproot_group'] = maproot_group

            if mapall_user is not None:
                arg['mapall_user'] = mapall_user

            if mapall_group is not None:
                arg['mapall_group'] = mapall_group

            if networks is not None:
                arg['networks'] = networks

            if hosts is not None:
                arg['hosts'] = hosts

            if module.check_mode:
                result['msg'] = f"Would have created NFS export \"{name}\" with {arg}"
            else:
                #
                # Create new export
                #
                try:
                    err = mw.call("sharing.nfs.create", arg)
                    result['msg'] = err
                except Exception as e:
                    # result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating NFS export \"{name}\": {e}")

                # Return whichever interesting bits sharing.nfs.create()
                # returned.
                # XXX
                result['resource_id'] = err

            result['changed'] = True
        else:
            # NFS export is not supposed to exist.
            # All is well
            result['changed'] = False

    else:
        # NFS export exists
        if state == 'present':
            # It is supposed to exist

            # Make list of differences between what is and what should
            # be.
            arg = {}

            if alldirs is not None and export_info['alldirs'] != alldirs:
                arg['alldirs'] = alldirs

            if quiet is not None and export_info['quiet'] != quiet:
                arg['quiet'] = quiet

            if enabled is not None and export_info['enabled'] != enabled:
                arg['enabled'] = enabled

            if readonly is not None and export_info['readonly'] != readonly:
                arg['ro'] = readonly

            if maproot_user is not None and \
               export_info['maproot_user'] != maproot_user:
                arg['maproot_user'] = maproot_user

                # maproot_user and mapall_user are mutually exclusive.
                # If setting one, make sure to unset the other.
                if export_info['mapall_user'] is not None:
                    arg['mapall_user'] = None

            if maproot_group is not None and \
               export_info['maproot_group'] != maproot_group:
                arg['maproot_group'] = maproot_group

                # maproot_group and mapall_group are mutually exclusive.
                # If setting one, make sure to unset the other.
                if export_info['mapall_group'] is not None:
                    arg['mapall_group'] = None

            if mapall_user is not None and \
               export_info['mapall_user'] != mapall_user:
                arg['mapall_user'] = mapall_user

                # maproot_user and mapall_user are mutually exclusive.
                # If setting one, make sure to unset the other.
                if export_info['maproot_user'] is not None:
                    arg['maproot_user'] = None

            if mapall_group is not None and \
               export_info['mapall_group'] != mapall_group:
                arg['mapall_group'] = mapall_group

                # maproot_group and mapall_group are mutually exclusive.
                # If setting one, make sure to unset the other.
                if export_info['maproot_group'] is not None:
                    arg['maproot_group'] = None

            # Check whether the path is the same as the old.
            # We use set comparison because the order doesn't matter.
            if path != export_info['path']:
                arg['path'] = path

            # Check whether the new set of networks is the same as the
            # old set.
            if networks is not None and \
               set(networks) != set(export_info['networks']):
                arg['networks'] = networks

            # Check whether the new set of hosts is the same as the
            # old set.
            if hosts is not None and \
               set(hosts) != set(export_info['hosts']):
                arg['hosts'] = hosts

            # If there are any changes, sharing.nfs.update()
            if len(arg) == 0:
                # No changes
                result['changed'] = False
            else:
                #
                # Update the export.
                #
                if module.check_mode:
                    result['msg'] = f"Would have updated NFS export \"{name}\": {arg}"
                else:
                    try:
                        err = mw.call("sharing.nfs.update",
                                      export_info['id'],
                                      arg)
                        result['status'] = err
                    except Exception as e:
                        module.fail_json(msg=f"Error updating NFS export \"{name}\" with {arg}: {e}")
                        # Returns a structure similar to sharing.nfs.query(),
                        # with all the information about the export.
                        result['status'] = err['status']
                result['changed'] = True
        else:
            # NFS export is not supposed to exist

            if module.check_mode:
                result['msg'] = f"Would have deleted NFS export \"{name}\"."
            else:
                try:
                    #
                    # Delete NFS export.
                    #
                    err = mw.call("sharing.nfs.delete",
                                  export_info['id'])
                    result['status'] = err
                except Exception as e:
                    module.fail_json(msg=f"Error deleting NFS export \"{name}\": {e}")
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
