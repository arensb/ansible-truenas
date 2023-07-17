#!/usr/bin/python
__metaclass__ = type

# Create and manage NFS shares.

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
  paths:
    description:
      - Deprecated; use C(path) instead.
      - List of directories to export.
      - All paths must be in the same filesystem. And if multiple directories
        from the same filesystem are being imported, they must be in the
        same NFS export.
    type: list
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
version_added: 0.1.0
'''

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

import sys
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW
import ansible_collections.arensb.truenas.plugins.module_utils.setup as setup
from packaging import version


class NFS1:
    """Class to implement version 1 of the sharing_nfs middleware protocol.

    This version accepts 'paths' (plural) as a group of directories
    exported at the same time, though it's not happy about it, and prefers
    'path' singular, just like nfs2."""

    def __init__(self):
        self.module = AnsibleModule(
            argument_spec=dict(
                name=dict(type='str', aliases=['comment']),
                path=dict(type='str'),
                paths=dict(type='list', elements='str'),
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
                ['path', 'paths'],
                ['maproot_user', 'mapall_user'],
                ['maproot_group', 'mapall_group'],
            ],
            required_one_of=[['path', 'paths']],
            # required_if=[
            #     ['state', 'present', ['name']],
            # ],
            required_by=dict(
                # Can't have map*_group without its corresponding map*_user.
                maproot_group=('maproot_user'),
                mapall_group=('mapall_user'),
            ),
        )

        self.result = dict(
            changed=False,
            msg=''
        )

        self.mw = MW.client()

    def run(self):
        """Run the module."""

        # Assign variables from properties, for convenience
        name = self.module.params['name']
        path = self.module.params['path']
        paths = self.module.params['paths']
        state = self.module.params['state']
        alldirs = self.module.params['alldirs']
        quiet = self.module.params['quiet']
        enabled = self.module.params['enabled']
        readonly = self.module.params['readonly']
        maproot_user = self.module.params['maproot_user']
        maproot_group = self.module.params['maproot_group']
        mapall_user = self.module.params['mapall_user']
        mapall_group = self.module.params['mapall_group']
        networks = self.module.params['networks']
        hosts = self.module.params['hosts']

        # The Hypocritical Section:
        #
        # In the documentation, we recommend using 'path' (singular)
        # because that makes more sense, and is compatible with nfs2().
        # But in this version, middlewared requires a 'paths' array, so we
        # convert 'path' to 'paths' if necessary, after berating the
        # caller for using 'paths'.
        if paths is not None:
            # If 'paths' is given, and is plural, issue warning urging
            # user to switch to 'path' singular.
            if len(paths) in (0, 1):
                self.module.warn("The 'paths' option is deprecated. Please use 'path' instead.")
            else:
                # If 'paths' is given and is singular, issue warning
                # urging user to switch to 'path' singular'.
                self.module.warn("The 'paths' option is deprecated. Please break it up into several 'path' plays.")
        else:
            paths = [path]

        # Look up the share.
        #
        # Use the comment as an identifier. In the general case, we would
        # have to take a set of directories and try to map them to an
        # existing export set. But let's say we're given:
        #
        # - sharing_nfs:
        #     paths:
        #       - /path/to/a
        #     <options>
        #
        # And when we look up the existing exports, we find only one, with
        # paths==['/path/to/b']
        #
        # Does this mean we should export /path/to/a as a new export, and wind
        # up with
        #   - id: 1, paths: [/path/to/b]
        #   - id: 2, paths: [/path/to/a]
        #
        # Or does it mean that the caller originally exported /path/to/b,
        # and now wants to change it to /path/to/a, so we wind up with just:
        #   - id: 1, paths: [/path/to/a]
        #
        # Some special cases can be solved (e.g., when a and b are on
        # different filesystems), but not the general case.

        # Notes:
        #
        # - Two directories in the same export must be in the same zfs
        #   filesystem. You can't have
        #   paths:
        #     - /mnt/pool0/fs0/somedir
        #     - /mnt/pool0/fs1/otherdir
        #
        # - If two directories in the same filesystem are exported, they
        #   must be in the same export set. You can't have:
        #   - sharing_nfs:
        #       name: Export 1
        #       paths: /mnt/pool0/fs0/somedir
        #   - sharing_nfs:
        #       name: Export 2
        #       paths: /mnt/pool0/fs0/otherdir
        #
        #   Here, "somedir" and "otherdir" must be put in the same "sharing_nfs"
        #   block.
        #
        # - Likewise, can't export a directory to different networks in
        #   different exports.

        # XXX - If we're trying to remove an export, look by path, not by
        # comment. And 'paths' is an array, so I don't think there's a
        # good way to search by "string is member of $array", so we might
        # need to query all of 'sharing.nfs.query()', and see if the path
        # is in any export.
        try:
            export_info = self.mw.call("sharing.nfs.query",
                                       [["comment", "=", name]])
            if len(export_info) == 0:
                # No such export
                export_info = None
            else:
                # Export exists
                export_info = export_info[0]
        except Exception as e:
            self.module.fail_json(msg=f"Error looking up NFS export {name}: {e}")

        # First, check whether the export even exists.
        if export_info is None:
            # Export doesn't exist

            if state == 'present':
                # Export is supposed to exist, so create it.

                # Collect arguments to pass to sharing.nfs.create()
                arg = {
                    "comment": name,
                    "paths": paths,
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

                if self.module.check_mode:
                    self.result['msg'] = f"Would have created NFS export \"{name}\" with {arg}"
                else:
                    #
                    # Create new export
                    #
                    try:
                        err = self.mw.call("sharing.nfs.create", arg)
                        self.result['msg'] = err
                    except Exception as e:
                        # self.result['failed_invocation'] = arg
                        self.module.fail_json(msg=f"Error creating NFS export \"{name}\": {e}")

                    # Return whichever interesting bits sharing.nfs.create()
                    # returned.
                    # XXX
                    self.result['resource_id'] = err

                self.result['changed'] = True
            else:
                # NFS export is not supposed to exist.
                # All is well

                # XXX - Is this correct? 'paths' is an array. So if the
                # caller specifies
                #   sharing_nfs:
                #     paths: /path/one
                #     state: absent
                #     # No 'name'.
                # and there's an export with
                #     /path/one
                #     /path/two
                #     /path/three
                # how should this be handled?
                self.result['changed'] = False

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
                if set(paths) != set(export_info['paths']):
                    arg['paths'] = paths

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
                    self.result['changed'] = False
                else:
                    #
                    # Update the export.
                    #
                    if self.module.check_mode:
                        self.result['msg'] = f"Would have updated NFS export \"{name}\": {arg}"
                    else:
                        try:
                            err = self.mw.call("sharing.nfs.update",
                                               export_info['id'],
                                               arg)
                            self.result['status'] = err
                        except Exception as e:
                            self.module.fail_json(msg=f"Error updating NFS export \"{name}\" with {arg}: {e}")
                            # Returns a structure similar to sharing.nfs.query(),
                            # with all the information about the export.
                            self.result['status'] = err['status']
                    self.result['changed'] = True
            else:
                # NFS export is not supposed to exist

                if self.module.check_mode:
                    self.result['msg'] = f"Would have deleted NFS export \"{name}\"."
                else:
                    try:
                        #
                        # Delete NFS export.
                        #
                        err = self.mw.call("sharing.nfs.delete",
                                           export_info['id'])
                        self.result['status'] = err
                    except Exception as e:
                        self.module.fail_json(msg=f"Error deleting NFS export \"{name}\": {e}")
                self.result['changed'] = True

        self.module.exit_json(**self.result)


def nfs2():
    # NFS sharing for TrueNAS SCALE >= 22.12.2, and presumably some future
    # version of TrueNAS CORE.
    #
    # Unlike nfs1(), this version takes only one directory, in the
    # 'path' argument, not multiple directories in the 'paths'
    # directory. This makes it possible to use the path as an
    # identifier, which is a much better approach anyway. 'name' now
    # becomes an optional comment.
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str', aliases=['comment']),
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

    mw = MW.client()

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
    # Use the path as an identifier.
    try:
        export_info = mw.call("sharing.nfs.query",
                              [["path", "=", path]])
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

            if name is not None and export_info['comment'] != name:
                arg['comment'] = name

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


def main():
    # Figure out which version of TrueNAS we're running, and thus how
    # to call middlewared.
    try:
        tn_version = setup.get_tn_version()
    except Exception as e:
        # Normally we'd module.exit_json(), but we don't have a module yet.
        print(f'{{"failed":true, "msg": "Error getting TrueNAS version: {e}"}}')
        sys.exit(1)

    # Call the appropriate function to handle this.

    # TrueNAS SCALE 22.12.2 is when middlewared switched the NFS
    # parameter from 'paths' to 'path'.
    TC_22_12_2 = version.parse("22.12.2")
    if tn_version['name'] == "TrueNAS" and \
       tn_version['type'] == "SCALE" and \
       tn_version['version'] >= TC_22_12_2:
        return nfs2()
    else:
        return NFS1().run()


# Main
if __name__ == "__main__":
    main()
