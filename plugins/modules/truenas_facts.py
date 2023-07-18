#!/usr/bin/python
__metaclass__ = type

# XXX - Make sure this does nothing on non-TrueNAS hosts, so that it
# can safely be added to the default set of fact-gathering modules.

# XXX
DOCUMENTATION = '''
---
module: truenas_facts
short_description: Gather TrueNAS-related facts
description:
  - Gather facts about a TrueNAS host, in the same way as
    C(setup) does.
  - Any facts discovered by this module will be mixed in with those
    discovered by other modules such as C(setup).
  - See U(https://docs.ansible.com/ansible/latest/reference_appendices/config.html#facts-modules)
    for how to use this module, as well as the Examples section.
  - You can set the environment variable C(ANSIBLE_FACTS_MODULES) to
    C(arensb.truenas.truenas_facts) to use only this module to gather facts,
    or to C(setup, arensb.truenas.truenas_facts) to use both the standard
    C(setup) module and this one.
  - Likewise, you can set the C(ansible_facts_modules) inventory
    variable to the list of modules to use, either just
    C(arensb.truenas.truenas_facts), or C([setup,
    arensb.truenas.truenas_facts]).
  - |
    This module may be used on non-TrueNAS hosts: it should simply fail
    gracefully and do nothing.
notes:
  - Supports C(check_mode).
  - Should run correctly on non-TrueNAS hosts.
version_added: 1.6.3
'''

# XXX
EXAMPLES = '''
- name: Manually gather information
  collections: arensb.truenas
  hosts: myhost
  tasks:
    - name: Gather TrueNAS-specific facts
      arensb.truenas.truenas_facts:
    # ansible_facts should have TrueNAS facts mixed in with the usual ones.
    - debug: var=ansible_facts
'''

# XXX - Look up these descriptions in exchanges about NFS failing.
RETURN = '''
ansible_facts.truenas_product_name:
  description:
    - A string giving the overall name of the product, usually
      C(TrueNAS)
  type: str
ansible_facts.truenas_product_type:
  description:
    - The flavor of TrueNAS. One of C(CORE), XXX, XXX...
  type: str
'''

from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec=dict(),
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        msg='',
        ansible_facts=dict(),
    )

    try:
        # We don't actually expect this to fail, since the MiddleWare
        # module comes with this module, and should therefore be
        # available everywhere.
        from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
            import MiddleWare as MW
    except ImportError as e:
        result['skipped'] = True
        module.exit_json(**result)

    # Creating a MiddleWare client can fail if the TrueNAS-related
    # modules aren't present on the remote system.
    try:
        mw = MW.client()
    except ModuleNotFoundError as e:
        result['msg'] = f'Got module not found exeption {e}'
        result['skipped'] = True
        module.exit_json(**result)
    except FileNotFoundError as e:
        result['msg'] = f'Got file not found exeption {e}'
        result['skipped'] = True
        module.exit_json(**result)

    result['msg'] += f"mw: {MW}.\n"

    result['ansible_facts'] = {
        "fact1": "value1",
        "fact2": ["a", "list", "of", "values"],
        "fact3": {
            "key": "value",
            "key2": ["another", "value"],
        },
    }
    module.exit_json(**result)
    return

    # XXX - Get the OS version, product, and whatnot.

    # XXX - system.boot_id
    # XXX - system.build_time
    # XXX - system.environment
    # XXX - system.feature_enabled
    #   Break down by feature?
    # XXX - system.host_id
    # XXX - system.info - This returns a structure. Is it better to

    # Assign variables from properties, for convenience
    name = module.params['name']
    # XXX

    # XXX - Look up the resource
    try:
        resource_info = mw.call("resource.query",
                                [["name", "=", name]])
        if len(resource_info) == 0:
            # No such resource
            resource_info = None
        else:
            # Resource exists
            resource_info = resource_info[0]
    except Exception as e:
        module.fail_json(msg=f"Error looking up resource {name}: {e}")

    # First, check whether the resource even exists.
    if resource_info is None:
        # Resource doesn't exist

        if state == 'present':
            # Resource is supposed to exist, so create it.

            # Collect arguments to pass to resource.create()
            arg = {
                "resourcename": name,
            }

            if feature is not None:
                arg['feature'] = feature

            if module.check_mode:
                result['msg'] = f"Would have created resource {name} with {arg}"
            else:
                #
                # Create new resource
                #
                try:
                    err = mw.call("resource.create", arg)
                    result['msg'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating resource {name}: {e}")

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
            arg = {}

            if feature is not None and resource_info['feature'] != feature:
                arg['feature'] = feature

            # If there are any changes, resource.update()
            if len(arg) == 0:
                # No changes
                result['changed'] = False
            else:
                #
                # Update resource.
                #
                if module.check_mode:
                    result['msg'] = f"Would have updated resource {name}: {arg}"
                else:
                    try:
                        err = mw.call("resource.update",
                                      resource_info['id'],
                                      arg)
                    except Exception as e:
                        module.fail_json(msg=f"Error updating resource {name} with {arg}: {e}")
                        # Return any interesting bits from err
                        result['status'] = err['status']
                result['changed'] = True
        else:
            # Resource is not supposed to exist

            if module.check_mode:
                result['msg'] = f"Would have deleted resource {name}"
            else:
                try:
                    #
                    # Delete resource.
                    #
                    err = mw.call("resource.delete",
                                  resource_info['id'])
                except Exception as e:
                    module.fail_json(msg=f"Error deleting resource {name}: {e}")
            result['changed'] = True
        result['skipped'] = True
        result['msg'] = f"Error looking up facts: {e}"
        module.exit_json(**result)

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
