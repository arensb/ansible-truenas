#!/usr/bin/python
__metaclass__ = type

# Configure a jail.
# To configure the jail system, see the jails module.

# XXX
DOCUMENTATION = '''
---
module: jail
short_description: Manage a jail
description:
  - Create, destroy, or configure a jail.
  - To manage the jail system itself, see the C(jails) module.
options:
  name:
    description:
      - Name of the jail. This must be a unique ID.
    type: str
    required: true
  # packages:
  #   description:
  #     - List of packages to install when the jail is created.
  #   type: list
  #   elements: str
  release:
    description:
      - Name of FreeBSD release to base this jail on.
      - Required when creating a jail.
    type: str
  state:
    description:
      - Whether the jail should exist or not.
      - If 'absent', the jail will be removed.
      - If 'present', the jail will be created if it doesn't exist, but
        will not be started.
      - 'running' and 'stopped' allow you to make sure the jail is up or down.
      - 'restarted' will restart the jail, similar to rebooting it.
    type: str
    choices: [ absent, present, restarted, running, stopped ]
    default: present
'''

# XXX
EXAMPLES = '''
'''

# XXX
RETURN = '''
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW


def main():
    # XXX
    # - clone_of (str) name of RELEASE to clone
    # - basejail (bool)
    # - release (str)
    # - template (str)
    # - pkglist (list(str)) -> packages
    # - uuid (str): use name
    # - empty (bool)
    # - short (bool)
    # - props (list)
    # - https (bool)

    # XXX - When creating, required:
    # - release
    # - uuid

    # XXX - What's the difference between clone jail and basejail?
    # - Clone jail: "thin": read-only mount of a FreeBSD release, plus
    #   whatever is needed to customize the jail, plus user data.
    #   Use this for cheap cattle.
    #   Can't delete the release image until all jails that use it are
    #   gone.
    # - Thick jail: allocate a new disk and copy the OS to it. Do
    #   anything you like to it.
    # - Base jail: like a thick jail, except that some directories
    #   (/bin, /lib, /usr/bin, that sort of thing) are deleted, then mounted
    #   from the image.

    # XXX - Create a lookup(?) plugin to see which releases are
    # available. Might need to write this as a module that doesn't do
    # anything except return a value, since it has to run on the
    # client, not on the Ansible master.

    # XXX - jail.exec(): run a command inside a jail
    # XXX - jail.fetch(): fetch a release or plugin
    # XXX - jail.fstab(): manipulate a jail's fstab.
    # XXX - (jail.import_image() - import from image)

    # XXX - jail.rc_action(): Run the start/stop/restart script.
    #   Put this in the 'state' option, similar to 'service' module?
    #   aws.ec2 has: absent, present, restarted, running, stopped)[Default: present]

    # XXX - jail.start(): (job) start the jail itself.
    # XXX - jail.stop(): (job) stop the jail itself.
    # XXX - jail.restart(): (job) restart the jail itself.

    # XXX - jail.update()
    # - plugin (bool)

    module = AnsibleModule(
        argument_spec=dict(
            # XXX
            name=dict(type='str'),
            state=dict(type='str', default='present',
                       choices=['absent', 'present', 'restarted', 'running', 'stopped']),
            release=dict(type='str'),
            # packages=dict(type='list', elements='str'),
            ),
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW()

    # Assign variables from properties, for convenience
    name = module.params['name']
    state = module.params['state']
    release = module.params['release']
    # packages = module.params['packages']

    # XXX - Look up the jail
    try:
        jail_info = mw.call("jail.query",
                            [["id", "=", name]])
        if len(jail_info) == 0:
            # No such jail
            jail_info = None
        else:
            # Jail exists
            jail_info = jail_info[0]
    except Exception as e:
        module.fail_json(msg=f"Error looking up jail {name}: {e}")

    # First, check whether the jail even exists.
    if jail_info is None:
        # Jail doesn't exist

        if state in ('present', 'restarted', 'running', 'stopped'):
            # Jail is supposed to exist, so create it.

            # A release is required when creating a jail.
            module.fail_on_missing_params(['release'])

            # Collect arguments to pass to jail.create()
            arg = {
                "uuid": name,
                "release": release,
            }

            # if release is None:
            #     arg['feature'] = feature

            if module.check_mode:
                result['msg'] = f"Would have created jail {name} with {arg}"
            else:
                #
                # Create new jail
                #
                try:
                    err = mw.job("jail.create", arg)
                    result['msg'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating jail {name}: {e}")

                result['jail'] = err

                # XXX - err['state'] can be "up", "down", and apparently
                # that's it.

                # XXX - If state == running, jail.start().
                # if state == restarted, jail.restart().

                # At this point, normally the jail is down. Check
                # whether that's what the caller wanted.
                if state in ('present', 'stopped'):
                    # This is fine.
                    # I'm okay with the events that are unfolding currently.
                    pass
                else:
                    try:
                        err = mw.job("jail.start", name)
                        result['state'] = err
                    except Exception as e:
                        module.fail_json(msg=f"Error starting jail {name}: {e}")

            result['changed'] = True
        else:
            # Jail is not supposed to exist.
            # All is well
            result['changed'] = False

    else:
        # Jail exists
        if state == 'absent':
            # Jail is not supposed to exist

            if jail_info['state'] == "up":
                #
                # Stop the jail.
                #
                if module.check_mode:
                    result['msg'] += f"Would have stopped jail {name}."
                else:
                    try:
                        err = mw.job("jail.stop", name)
                    except Exception as e:
                        module.fail_json(msg=f"Error stopping jail {name}: {e}")
                    result['status_stop'] = err

            if module.check_mode:
                result['msg'] += f"Would have deleted jail {name}."
            else:
                try:
                    #
                    # Delete jail.
                    #
                    err = mw.call("jail.delete", name)
                except Exception as e:
                    module.fail_json(msg=f"Error deleting jail {name}: {e}")
            result['changed'] = True
            module.exit_json(**result)

        # The jail exists. Check whether its configuration needs to be
        # updated.

        # Start out by assuming that nothing is changing.
        result['changed'] = False

        # XXX
        # Make list of differences between what is and what should
        # be.
        arg = {}

        # if feature is not None and jail_info['feature'] != feature:
        #     arg['feature'] = feature

        # If there are any changes, jail.update()
        if len(arg) == 0:
            # No changes
            pass
        else:
            #
            # Update jail.
            #
            if module.check_mode:
                result['msg'] = f"Would have updated jail {name}: {arg}"
            else:
                try:
                    err = mw.call("jail.update", name,
                                  arg)
                except Exception as e:
                    module.fail_json(msg=f"Error updating jail {name} with {arg}: {e}")
                    # Return any interesting bits from err
                    result['status'] = err['status']
            result['changed'] = True

        # XXX - Now see whether it needs to be brought up or down, or
        # restarted.
        if 'state' == 'running':
            if jail_info['state'] == 'up':
                # All is well
                pass
            else:
                # We want it to be running, but it's not.
                if module.check_mode:
                    result['msg'] += f"Would have started jail {name}"
                else:
                    try:
                        err = mw.job("jail.start", name)
                    except Exception as e:
                        module.fail_json(msg=f"Error starting jail {name}: {e}")
                result['changed'] = True
        elif state == 'stopped':
            # XXX
            if jail_info['state'] == 'up':
                # We want it to be stopped, but it's up.
                # XXX
                if module.check_mode:
                    result['msg'] += f"Would have stopped jail {name}"
                else:
                    try:
                        err = mw.job("jail.stop", name)
                    except Exception as e:
                        module.fail_json(msg=f"Error stopping jail {name}: {e}")
                    result['status'] = err
                result['changed'] = True
            else:
                # We want it to be stopped, and it's down.
                # all is well
                pass
        elif state == 'restarted':
            # Either way, restart it.
            if module.check_mode:
                result['msg'] += f"Would have restarted jail {name}"
            else:
                try:
                    err = mw.job("jail.restart", name)
                except Exception as e:
                    module.fail_json(msg=f"Error restarting jail {name}: {e}")
                result['status'] = err
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
