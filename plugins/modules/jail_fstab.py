#!/usr/bin/python
__metaclass__ = type

# Manage a jail's fstab

DOCUMENTATION = '''
---
module: jail_fstab
short_description: "Manage a jail's fstab"
description:
  - Add, remove, mount, and unmount filesystems that a jail sees.
  - Note that changes can only be made when the jail is stopped,
    so this module will attempt to stop the jail if it needs to, and
    then restart it after the changes are made.
  - If you do not want production jails to be restarted without your
    explicit approval, you can add a clause like
    C(check_mode: "{{ restart_jails != 'yes' }}")
options:
  append:
    description:
      - If C(yes), other filesystems may be mounted besides the ones listed
        in C(fstab).
      - If C(no), any mounts other than the ones in C(fstab) will be removed.
    type: bool
    default: no
  jail:
    description:
      - Name of the jail
    type: str
    required: yes
  fstab:
    description:
      - List of mount points. Each element is a dictionary.
    type: list
    suboptions:
      src:
        description:
          - The device to mount, or the directory to share with the jail.
        required: yes
        type: str
      mount:
        description:
          - The directory where the device should be mounted.
          - If this begins with C(/), it is an absolute path, as seen
            from outside the jail. Otherwise, it is a relative path,
            relative to the jail's root, typically
            C(/mnt/<pool>/iocage/jails/<jail-name>/root).
        required: yes
        type: str
      fstype:
        description:
          - Filesystem type.
          - When mounting an existing directory, use C(nullfs).
        type: str
        required: no
        default: "nullfs"
      options:
        description:
          - Filesystem options to pass to C(mount). Comma-separated string.
        type: str
        default: "ro"
      dump:
        description:
          - Used by the C(dump) command. This field gives the number of
            days between backups. A value of 0 means "no backups".
          - This is the C(fs_freq) field in fstab(5).
          - For a jail, this will typically be 0.
        type: int
        required: no
        default: 0
      fsck_pass:
        description:
          - Used by C(fsck) to determine the order in which to check
            filesystems at boot time.
          - This is not normally useful in a jail. It is included here
            for completeness.
        type: int
        required: no
        default: 0
      state:
        description:
          - Whether the filesystem should be mounted or not.
          - Set C(state) to C(absent) to ensure that nothing is mounted
            at a given mount point.
          - By default, filesystems are mounted, because it is assumed that
            you want them available. In addition, setting C(append) to C(no)
            ensures that any filesystems not on the list are unmounted.
          - When C(state) is C(present), the C(source) parameter is required.
            When C(state) is C(absent), C(source) can be omitted.
        type: str
        choices: [ 'present', 'absent' ]
        default: present
version_added: 1.8.0
'''

EXAMPLES = '''
- name: Mount some directories inside a jail
  arensb.truenas.jail_fstab:
    jail: the-jail-name
    fstab:
      # Absolute mount point:
      - src: /mnt/data/my-data
        mount: /mnt/data/iocage/jails/the-jail-name/root/my-data
        fstype: nullfs
        options: ro
        dump: 0
        pass: 0
      # Relative mount point:
      - src: /mnt/data/more-data
        mount: data/more

# Making changes to fstab involves stopping the jail, then restarting it.
# This shows how to not affect running services unless the 'bounce_jails'
# variable is set to 'yes'.
- name: Don't halt production services
  arensb.truenas.jail_fstab:
    jail: the-jail-name
    fstab:
      - src: /mnt/data/my-data
        mount: /mnt/data/iocage/jails/the-jail-name/root/my-data
  check_mode: "{{ ansible_check_mode or bounce_jails != 'yes' }}"

- name: Ensure that a filesystem is *not* mounted:
  arensb.truenas.jail_fstab:
    jail: the-jail-name
    fstab:
        - mount: /mnt/data/iocage/jails/the-jail-name/root/old-data
          state: absent
'''

# XXX
RETURN = '''
fstab:
  description:
    - The jail's fstab.
    - This is returned in check mode as well.
  type: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW

iocroot = None


def main():
    def get_iocroot():
        global iocroot

        # Return cached value, if there is one.
        if iocroot is not None:
            return iocroot

        # Look up the iocage root.
        try:
            iocroot = mw.call("jail.get_iocroot", output='str')
        except Exception:
            return None

        return iocroot

    module = AnsibleModule(
        argument_spec=dict(
            jail=dict(type='str', required=True),
            fstab=dict(type='list', elements='dict',
                       options=dict(
                           src=dict(type='str'),
                           mount=dict(type='str', required=True),
                           fstype=dict(type='str', default="nullfs"),
                           options=dict(type='str', default="ro"),
                           dump=dict(type='int', default=0),
                           fsck_pass=dict(type='int', default=0),
                           state=dict(type='str', default='present',
                                      choices=['present', 'absent'])
                       ),
                       required_if=[
                           ('state', 'present', ('src', 'mount'))
                       ]
                       ),
            append=dict(type='bool', default=False),
            ),
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW.client()

    # Assign variables from properties, for convenience
    jail = module.params['jail']
    fstab = module.params['fstab']
    append = module.params['append']

    # XXX - Error-checking
    result['iocroot'] = get_iocroot()

    # Look up the jail and its fstab
    try:
        jail_info = mw.call("jail.query",
                            [["id", "=", jail]],
                            # We only care about state for now.
                            {"select": ["state"]})

        if len(jail_info) == 0:
            # No such jail
            module.fail_json(msg=f"No such jail {jail}")
        else:
            # Jail exists
            jail_info = jail_info[0]

        fstab_info = mw.call("jail.fstab",
                             jail,
                             {"action": "LIST"})
    except Exception as e:
        module.fail_json(msg=f"Error looking up jail {jail}: {e}")

    result['jail_info'] = jail_info

    # Filter out the "SYSTEM" entries and only keep the "USER" ones.
    fstab_info = {k: v for (k, v) in fstab_info.items()
                  if v['type'] == "USER"}
    result['fstab'] = fstab_info

    # Iterate over the provided list of mount points and see if they
    # match what the caller wants.

    # XXX - Need to stop jail when adding, removing a mountpoint.

    # The jail needs to be stopped before making any changes, so in
    # this phase, we're just going to make a list of all the changes
    # to make. Specifically, we're going to construct a set of
    # arguments to call `jail.fstab' on.
    change_args = []

    for fs in fstab:
        # XXX - Debugging
        result['msg'] += f"Checking {fs['mount']}.\n"

        # If "mount" begins with "/", it's absolute. Otherwise, it's
        # relative to jail root:
        # {iocroot}/jails/{jailname}/root

        fs['mount_full'] = fs['mount']
        if not fs['mount_full'].startswith("/"):
            # This is a relative path. Make it absolute.
            fs['mount_full'] = \
                f"{get_iocroot()}/jails/{jail}/root/{fs['mount']}"

        # XXX - Debugging
        result['msg'] += f"  mount_full: {fs['mount_full']}\n"

        # fstab_info is a dict of entries of the form:
        # "NNN" : { "entry": [...], "type": "SYSTEM|USER" }
        # The "entry" sub-field is an array of strings:
        # 0: source
        # 1: destination
        # 2: fstype
        # 3: fsoptions
        # 4: dump
        # 5: pass
        #
        # We need the key, in case we need to replace the fstab entry.
        for nth, fields in fstab_info.items():
            if fields['entry'][1] != fs['mount_full']:
                # This isn't the one we're looking for.
                continue

            # Found it.
            entry = {
                "source": fields['entry'][0],
                "destination": fields['entry'][1],
                "fstype": fields['entry'][2],
                "fsoptions": fields['entry'][3],
                "dump": fields['entry'][4],
                "pass": fields['entry'][5],
                "index": nth,
                "type": fields['type'],
            }

            # There shouldn't be more than one.
            break

        if entry is None:
            if fs['state'] == 'absent':
                # The entry doesn't exist, and is supposed to not
                # exist. This is fine.
                continue

            # This entry does not exist in the jail, but should.
            # Create it.
            result['msg'] += "No such entry. Need to add it.\n"

            # Required fields for ADD:
            # - source
            # - destination
            # others are optional.
            args = {
                "action": "ADD",
                "source": fs['src'],
                "destination": fs['mount'],
            }
            if "fstype" in fs:
                args['fstype'] = fs['fstype']
            if "options" in fs:
                args['fsoptions'] = fs['options']
            if "dump" in fs:
                args['dump'] = fs['dump']
            if "fsck_pass" in fs:
                args['dump'] = fs['fsck_pass']

            change_args.append(args)

        elif fs['state'] == "absent":
            # It's present, but is supposed to be absent.
            change_args.append({
                "index": entry['index'],
                "action": "REMOVE",
                # "source": entry['source'],
                # "destination": entry['destination'],
            })

        else:
            # This entry exists in the jail, and is supposed to. Make
            # sure it matches what the caller wants.

            # XXX - Debugging.
            result['msg'] += "This entry exists. Need to check it.\n"

            # Collect a set of things to change about this mount point
            args = {}

            # Source
            if entry['source'] != fs['src']:
                args['source'] = fs['src']

            # fstype
            if fs['fstype'] is not None and \
               entry['fstype'] != fs['fstype']:
                args['fstype'] = fs['fstype']

            # Options
            if fs['options'] is not None and \
               entry['fsoptions'] != fs['options']:
                args['fsoptions'] = fs['options']

            # Dump
            if fs['dump'] is not None and \
               int(entry['dump']) != fs['dump']:
                args['dump'] = fs['dump']

            # fsck_pass
            if fs['fsck_pass'] is not None and \
               int(entry['pass']) != fs['fsck_pass']:
                args['pass'] = fs['fsck_pass']

            if len(args) > 0:
                args['action'] = "REPLACE"
                args['index'] = entry['index']

            result['msg'] += f"change_fields: {args}\n"

    if not append:
        result['msg'] += "Ought to delete other fs-es.\n"

        # XXX - For any remaining fstab entries:
        # jail.fstab <jail-name> {entry, action: REMOVE}

        # XXX - Required fields for REMOVE:
        # - source
        # - destination

        # Make a list of fstab_info items that don't appear in fstab.
        listed_mounts = [m['mount_full'] for m in fstab]
        extra_fses = [v['entry'] for (k, v) in fstab_info.items()
                      if v['entry'][1] not in listed_mounts]
        result['extra_fses'] = extra_fses

        for entry in extra_fses:
            change_args.append({
                "action": "remove",
                "entry": entry,
            })

    # XXX - If there are any changes:
    if len(change_args) > 0:
        # - Check the jail upness.
        result['msg'] += f"jail state: {jail_info['state']}\n"

        result['changed'] = True

        # Stop jail if necessary
        if jail_info['state'] == "up":
            # Need to shut down jail.
            if module.check_mode:
                result['msg'] += "Need to shut down jail.\n"
            else:
                try:
                    mw.job("jail.stop", jail)
                except Exception as e:
                    module.fail_json(msg=f"Error shutting down jail {jail}: {e}")

        else:
            result['msg'] += f"Jail is {jail_info['state']}, not up. Not shutting down.\n"

        # - apply the changes
        for args in change_args:
            result['msg'] += f"Need to make a change: {args}\n"

            if module.check_mode:
                result['msg'] += "Ought to make a change: {args}\n"

        # - Start jail if it was up before
        if jail_info['state'] == "up":
            # Need to restart jail
            if module.check_mode:
                result['msg'] += "Need to restart jail.\n"
            else:
                try:
                    mw.job("jail.start", jail)
                except Exception as e:
                    module.fail_json(msg=f"Error restarting jail {jail}: {e}")
        else:
            result['msg'] += "Jail wasn't up. Not restarting.\n"

    module.exit_json(**result)

    # XXX - Everything below is left over from the template. Delete it.

    # First, check whether the resource even exists.
    if fstab_info is None:
        # Resource doesn't exist

        if state == 'present':
            # Resource is supposed to exist, so create it.

            # Collect arguments to pass to resource.create()
            args = {
                "resourcename": jail,
            }

            if feature is not None:
                args['feature'] = feature

            if module.check_mode:
                result['msg'] = f"Would have created resource {jail} with {args}"
            else:
                #
                # Create new resource
                #
                try:
                    err = mw.call("resource.create", args)
                    result['msg'] = err
                except Exception as e:
                    result['failed_invocation'] = args
                    module.fail_json(msg=f"Error creating resource {jail}: {e}")

                # Return whichever interesting bits resource.create()
                # returned.
                result['resource_id'] = err

            result['changed'] = True
        else:
            # Resource is not supposed to exist.
            # All is well
            result['changed'] = False

    else:
        # Resource exists
        if state == 'present':
            # Resource is supposed to exist

            # Make list of differences between what is and what should
            # be.
            args = {}

            if feature is not None and fstab_info['feature'] != feature:
                args['feature'] = feature

            # If there are any changes, resource.update()
            if len(args) == 0:
                # No changes
                result['changed'] = False
            else:
                #
                # Update resource.
                #
                if module.check_mode:
                    result['msg'] = f"Would have updated resource {jail}: {args}"
                else:
                    try:
                        err = mw.call("resource.update",
                                      fstab_info['id'],
                                      args)
                    except Exception as e:
                        module.fail_json(msg=f"Error updating resource {jail} with {args}: {e}")
                        # Return any interesting bits from err
                        result['status'] = err['status']
                result['changed'] = True
        else:
            # Resource is not supposed to exist

            if module.check_mode:
                result['msg'] = f"Would have deleted resource {jail}"
            else:
                try:
                    #
                    # Delete resource.
                    #
                    err = mw.call("resource.delete",
                                  fstab_info['id'])
                except Exception as e:
                    module.fail_json(msg=f"Error deleting resource {jail}: {e}")
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
