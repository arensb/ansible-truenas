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
  - 'If you do not want production jails to be restarted without your
    explicit approval, you can add a clause like
    C(check_mode: "{{ restart_jails != ''yes'' }}")'
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
          - This is a relative path, relative to the jail's root, typically
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
version_added: 1.9.0
'''

EXAMPLES = '''
- name: Mount some directories inside a jail
  arensb.truenas.jail_fstab:
    jail: the-jail-name
    fstab:
      - src: /mnt/data/my-data
        mount: /my-data
        fstype: nullfs
        options: ro
        dump: 0
        pass: 0
      - src: /mnt/data/more-data
        mount: /data/more

# Making changes to fstab involves stopping the jail, then restarting it.
# This shows how to not affect running services unless the 'bounce_jails'
# variable is set to 'yes'.
- name: Don't halt production services
  arensb.truenas.jail_fstab:
    jail: the-jail-name
    fstab:
      - src: /mnt/data/my-data
        mount: /my-data
  check_mode: "{{ ansible_check_mode or bounce_jails != 'yes' }}"

- name: Ensure that a filesystem is *not* mounted:
  arensb.truenas.jail_fstab:
    jail: the-jail-name
    fstab:
        - mount: /old-data
          state: absent
'''

RETURN = '''
fstab:
  description:
    - 'The fstab of the jail fstab. This is a dict of elements of the form
      C({"IDX": [source, destination, fstype, fsoptions, dump, pass], "type": "USER"})'
    - "C(IDX) is an integer string: the position of the entry in its fstab,
      zero-based."
    - C(source) is the device being mounted, or the directory being shared
      with the jail.
    - C(destination) is the directory where the filesystem is mounted.
      This is an absolute path as seen from outside the jail.
    - C(fstype) is the mount's filesystem type. For a null mount (filesystem
      shared with the jail), this is C(nullfs).
    - C(fsoptions) are the options passed to C(mount).
    - C(dump) and C(pass) are the dump and pass values from the C(fstab)
      entry.
    - C(type) specifies whether this is a system or user filesystem. In this
      module, it is always C("USER").
    - C(fstab) is returned in check mode as well.
  type: dict
changes:
  description:
    - In check mode, this is a detailed list of changed that would
      be made.
  type: list
status:
  description:
    - This module may affect multiple filesystems. C(status) is a list
      of results, one for each change made.
    - For a successful change, this is typically C(True).
  type: list
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW


def main():
    module = AnsibleModule(
        argument_spec=dict(
            jail=dict(type='str', required=True),
            fstab=dict(type='list', required=True,
                       elements='dict',
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
        msg='',
        status=[]
    )
    if module.check_mode:
        # List of changes being made
        result['changes'] = []

    mw = MW.client()

    # Assign variables from properties, for convenience
    jail = module.params['jail']
    fstab = module.params['fstab']
    append = module.params['append']

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

    # Filter out the "SYSTEM" entries and only keep the "USER" ones.
    fstab_info = {k: v for (k, v) in fstab_info.items()
                  if v['type'] == "USER"}
    result['fstab'] = fstab_info

    # Get the root of the jail. We're going to need it in a second.
    try:
        iocroot = mw.call("jail.get_iocroot", output='str')
    except Exception as e:
        module.fail_json(msg=f"Error looking up iocroot: {e}")
    jail_root = f"{iocroot}/jails/{jail}/root"

    # fstab_info is in the form returned by jail.fstab("LIST"). This
    # has two problems:
    #
    # 1) It's hard to work with: the elements are of the form
    #  "14": {
    #    "entry": [
    #      "/mnt/mypool/mydata",
    #      "/mnt/mypool/iocage/jails/mymail/root/mydata",
    #      "nullfs",
    #      "ro",
    #      "0",
    #      "0"
    #    ],
    #    "type": "USER"
    #  },
    #
    # 2) The mount directory (entry[1]) is a full path as seen by the
    # host, while every other command ("ADD", "REPLACE", "REMOVE")
    # wants a mount point relative to the jail's root, as seen inside
    # the jail: "/data".
    #
    # So before going any further, let's rewrite fstab_info in object
    # form.
    fstab_info = [{
        "index": k,
        "source": v['entry'][0],
        "destination": v['entry'][1],
        # "mount" is the mount point, relative to the jail.
        "mount": v['entry'][1].removeprefix(jail_root),
        "fstype": v['entry'][2],
        "fsoptions": v['entry'][3],
        "dump": v['entry'][4],
        "pass": v['entry'][5],
    } for (k, v) in fstab_info.items()]

    # Iterate over the provided list of mount points and see if they
    # match what the caller wants.

    # The jail needs to be stopped before making any changes, so in
    # this phase, we're just going to make a list of all the changes
    # to make. Specifically, we're going to construct a set of
    # arguments to call `jail.fstab' on.
    change_args = []

    for fs in fstab:
        # Find the fstab_info entry that corresponds to 'fs'. Note
        # that this construct is "clever" (he said with disdain).
        entry = next((i for i in fstab_info if i['mount'] == fs['mount']),
                     None)

        if entry is None:
            if fs['state'] == 'absent':
                # The entry doesn't exist, and is supposed to not
                # exist. This is fine.
                continue

            # This entry does not exist in the jail, but should.
            # Create it.

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
                "action": "REMOVE",
                "source": entry['source'],
                "destination": entry['mount'],
            })

        else:
            # This entry exists in the jail, and is supposed to. Make
            # sure it matches what the caller wants.

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
                # Grr. For some reason, jail.fstab("REPLACE") demands
                # index, source, and destination.
                args['index'] = entry['index']
                args['source'] = fs['src']
                args['destination'] = fs['mount']
                change_args.append(args)

    if not append:
        # Make a list of fstab_info items that don't appear in fstab.
        listed_mounts = [m['mount'] for m in fstab]
        extra_fses = [i for i in fstab_info if i['mount'] not in listed_mounts]

        for entry in extra_fses:
            # For some reason, both source and destination are
            # required for action=REMOVE
            change_args.append({
                "action": "REMOVE",
                "source": entry['source'],
                "destination": entry['mount'],
            })

    # If there are any changes, apply them.
    # If needed, stop the jail first and bring it up afterward.
    if len(change_args) > 0:
        # Check the jail upness.
        result['changed'] = True

        # Stop jail if necessary
        if jail_info['state'] == "up":
            # Need to shut down jail.
            if module.check_mode:
                result['changes'].append("shut down jail")
            else:
                try:
                    mw.job("jail.stop", jail)
                except Exception as e:
                    module.fail_json(
                        msg=f"Error shutting down jail {jail}: {e}")

        # Apply the changes
        for args in change_args:
            if module.check_mode:
                result['changes'].append(args)
            else:
                try:
                    err = mw.call("jail.fstab", jail, args)
                except Exception as e:
                    module.fail_json(
                        msg=f"Error modifying fstab with {args}: error {e}")
                # XXX - What should the 'status' field be?
                result['status'].append(err)

        # Start jail if it was up before
        if jail_info['state'] == "up":
            # Need to restart jail
            if module.check_mode:
                result['changes'].append("restart jail")
            else:
                try:
                    mw.job("jail.start", jail)
                except Exception as e:
                    module.fail_json(msg=f"Error restarting jail {jail}: {e}")

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
