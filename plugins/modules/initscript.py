#!/usr/bin/python
__metaclass__ = type

# Manage init/shutdown scripts.

# XXX
DOCUMENTATION = '''
---
module: initscript
short_description: Manage init/shutdown scripts.
description:
  - Set up and manage init and shutdown scripts and commands.
options:
  name:
    description:
      - Name of the script. Acts as an identifier.
    type: str
    required: true
  cmd:
    description:
      - Command to execute.
      - Mutually exclusive with C(path) and C(script).
    type: str
    aliases: [ command ]
  path:
    description:
      - Path to a script to execute.
      - Mutually exclusive with C(cmd) and C(script).
    type: str
  script:
    description:
      - Text of the script to execute.
      - When it is time to execute the script, the text will be saved to
        a temporary file, which will then be executed with C(sh).
      - Mutually exclusive with C(cmd) and C(path).
    type: str
  when:
    description:
      - "When to execute the script:"
      - "C(preinit): at boot time, before most services have started,
        but filesystems and network are available."
      - "C(postinit): late in the boot process, after most services have
        started, but before TrueNAS services."
      - "C(shutdown): during shutdown."
    choices:
      - preinit
      - postinit
      - shutdown
  timeout:
    description:
      - Time in seconds that the system should wait for the script to
        terminate.
    type: int
  state:
    description:
      - Whether the script should exist or not.
    type: str
    choices: [ absent, present ]
    default: present
version_added: 1.10.0
'''

# XXX
EXAMPLES = '''
'''

# XXX
RETURN = '''
id:
  description:
    - The ID of a newly-created script.
  type: int
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW


def main():
    module = AnsibleModule(
        argument_spec=dict(
            # XXX
            name=dict(type='str'),
            cmd=dict(type='str', aliases=['command']),
            path=dict(type='str'),
            script=dict(type='str'),
            when=dict(type='str',
                      choices=['preinit', 'postinit', 'shutdown',
                               'PREINIT', 'POSTINIT', 'SHUTDOWN']),
            timeout=dict(type='int'),
            state=dict(type='str', default='present',
                       choices=['absent', 'present']),
            ),
        supports_check_mode=True,
        # The upshot of the 'required_if' and 'mutually_exclusive'
        # constraints is that if you want the script to exist, you
        # have to provide exactly one of 'cmd', 'path', or 'script'.
        # If you want it to be absent, you don't have to provide any
        # of them.
        required_if=[
            ('state', 'present', ('cmd', 'path', 'script'), True)
        ],
        mutually_exclusive=['cmd', 'path', 'script'],
    )

    result = dict(
        changed=False,
        msg='',
        debug='',
    )

    mw = MW.client()

    # Assign variables from properties, for convenience
    name = module.params['name']
    cmd = module.params['cmd']
    path = module.params['path']
    script = module.params['script']
    when = module.params['when']
    timeout = module.params['timeout']
    state = module.params['state']

    # Look up the script.
    try:
        script_info = mw.call("initshutdownscript.query",
                              [["comment", "=", name]])
        if len(script_info) == 0:
            # No such script
            script_info = None
        else:
            # Script exists
            script_info = script_info[0]
    except Exception as e:
        module.fail_json(msg=f"Error looking up script {name}: {e}")

    result['debug'] += f"got script_info: {script_info}"
    # First, check whether the script even exists.
    if script_info is None:
        # Script doesn't exist

        if state == 'present':
            # Script is supposed to exist, so create it.

            # Collect arguments to pass to initshutdownscript.create()
            arg = {
                "comment": name,
            }

            # Figure out what kind of script/command it is.
            if cmd is not None:
                arg['type'] = "COMMAND"
                arg['command'] = cmd
            elif path is not None:
                arg['type'] = "SCRIPT"
                arg['script'] = path
            else:
                arg['type'] = "SCRIPT"
                arg['script_text'] = script

            if when is not None:
                arg['when'] = when.upper()

            if timeout is not None:
                arg['timeout'] = timeout

            if module.check_mode:
                result['msg'] = f"Would have created script {name} with {arg}"
            else:
                #
                # Create new script.
                #
                try:
                    err = mw.call("initshutdownscript.create", arg)
                    result['msg'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating script {name}: {e}")

                # Return whichever interesting bits initshutdownscript.create()
                # returned.
                result['id'] = err['id']
                result['script'] = err

            result['changed'] = True
        else:
            # Script is not supposed to exist.
            # All is well
            result['changed'] = False

    else:
        # Script exists
        if state == 'present':
            # Script is supposed to exist

            # Make list of differences between what is and what should
            # be.
            arg = {}

            # Check arguments, depending what kind of script this is.
            if cmd is not None:
                result['debug'] += "type: command\n"
                # This is a command.
                if script_info['type'] != "COMMAND":
                    result['debug'] += "wrong type\n"
                    arg['type'] = "COMMAND"
                if script_info['command'] != cmd:
                    result['debug'] += "wrong command\n"
                    arg['cmd'] = cmd
                if script_info['script'] != "":
                    result['debug'] += "wrong script\n"
                    arg['script'] = ""
                if script_info['script_text'] != "":
                    result['debug'] += "wrong script_text\n"
                    arg['script_text'] = ""
            elif path is not None:
                result['debug'] += "type: script (path)\n"
                # This is a script, specified by pathname.
                if script_info['type'] != "SCRIPT":
                    result['debug'] += "wrong type\n"
                    arg['type'] = "SCRIPT"
                if script_info['command'] != "":
                    result['debug'] += "wrong command\n"
                    arg['cmd'] = ""
                if script_info['script'] != path:
                    result['debug'] += "wrong script\n"
                    arg['script'] = path
                if script_info['script_text'] != "":
                    result['debug'] += "wrong script_text\n"
                    arg['script_text'] = ""
            else:
                result['debug'] += "type: script (body)\n"
                # This is a script, specified by script body.
                if script_info['type'] != "SCRIPT":
                    result['debug'] += "wrong type\n"
                    arg['type'] = "SCRIPT"
                if script_info['command'] != "":
                    result['debug'] += "wrong command\n"
                    arg['cmd'] = ""
                if script_info['script'] != "":
                    result['debug'] += "wrong script\n"
                    arg['script'] = ""
                if script_info['script_text'] != script:
                    result['debug'] += "wrong script_tet\n"
                    arg['script_text'] = script

            if when is not None and script_info['when'] != when.upper():
                result['debug'] += "wrong when\n"
                arg['when'] = when.upper()

            if timeout is not None and script_info['timeout'] != timeout:
                result['debug'] += "wrong timeout\n"
                arg['timeout'] = timeout

            # If there are any changes, initshutdownscript.update()
            if len(arg) == 0:
                # No changes
                result['changed'] = False
            else:
                #
                # Update script.
                #
                if module.check_mode:
                    result['msg'] = f"Would have updated script {name}: {arg}"
                else:
                    try:
                        err = mw.call("initshutdownscript.update",
                                      script_info['id'],
                                      arg)
                    except Exception as e:
                        module.fail_json(msg=f"Error updating script {name} with {arg}: {e}")
                        # Return any interesting bits from err
                        result['status'] = err['status']
                result['changed'] = True
        else:
            # Script is not supposed to exist

            if module.check_mode:
                result['msg'] = f"Would have deleted script {name}"
            else:
                try:
                    #
                    # Delete script.
                    #
                    err = mw.call("initshutdownscript.delete",
                                  script_info['id'])
                except Exception as e:
                    module.fail_json(msg=f"Error deleting script {name}: {e}")
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
