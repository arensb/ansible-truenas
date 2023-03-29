#!/usr/bin/python
__metaclass__ = type

# Manage plugins.

# XXX - How do you know which values `props` takes?
# Maybe from plugin.defaults:
#     midclt call plugin.defaults '{"plugin":"syncthing"}'|jq .|l
#     {
#       "plugin": "syncthing",
#       "properties": {
#         "vnet": 1,
#         "boot": 1,
#         "nat": 1,
#         "nat_forwards": "tcp(80:8384),tcp(22000:22000),udp(22000:22000),udp(21027:21027)"
#       }
#     }
# The 'plugin' value (here: "syncthing") comes from "plugin" in the
# output of plugin.query()

# XXX
DOCUMENTATION = '''
---
module: plugin
short_description: Manage plugins.
description:
  - Install, remove, and manage TrueNAS plugins.
options:
  jail:
    description:
      - Name of the jail in which this instance of the plugin will be
        installed.
      - This is a jail identifier. See the I(jail) module for more
        details.
    type: str
    required: yes
  name:
    description:
      - Name of the plugin.
    type: str
    required: true
    aliases: [ plugin ]
  plugin_id:
    description:
      - The ID or slug of the plugin. Unlike the name, this is not
        displayed in the TrueNAS web UI.
    type: str
  repository:
    description:
      - Name of the repository in which to look for the plugin. This is
        displayed in the TrueNAS Plugins UI under "Browse a Collection".
      - Overridden by C(repository_url).
    type: str
  repository_url:
    description:
      - The URL of the repository containing the plugin.
      - If specified, C(repository_url) overrides C(repository).
    type: str
  state:
    description:
      - Whether the plugin should exist or not.
      - If 'absent', the plugin (and its jail) will be removed.
      - If 'present', the plugin will be installed if necessarily, but
        if it isn't running, won't be started.
      - 'running' and 'stopped' allow you to make sure the plugin's
        jail is up or down.
      - 'restarted' will restart the plugin's jail, similar to rebooting it.
    type: str
    choices: [ absent, present, restarted, running, stopped ]
    default: present
'''

# XXX
EXAMPLES = '''
'''

# XXX
RETURN = '''
plugin:
  description:
    - An object describing a newly-created plugin.
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW


def main():
    def lookup_plugin():
        """Helper function: get repo and plugin details.

        We've been given a plugin name or ID, and a repository name or
        ID. Make sure we have a repository URL and a plugin ID, and return
        those."""

        # Assume that either repository_url or repository is
        # non-None.

        nonlocal module, repository_url, repository, \
            plugin_id, name

        # First step: if we don't have a repo URL, look it up from the
        # name.
        if repository_url is None:
            # Look up the list of repositories, and try to find one
            # with the name we need.
            try:
                repositories = mw.call("plugin.official_repositories")
            except Exception as e:
                module.fail_json(msg=f"Error looking up repositories: {e}")

            for key, repo in repositories.items():
                if repo['name'] == repository:
                    # Found it.
                    repository_url = repo['git_repository']
                    break
            else:
                module.fail_json(msg=f"No repository named {repository}")

        # Second step. We have a repo URL.
        # If we don't have a plugin ID, look it up in the repo.
        if plugin_id is None:
            # Get list of packages in the repo.
            try:
                pkgs = mw.job("plugin.available",
                              {"plugin_repository": repository_url})
            except Exception as e:
                module.fail_json(msg=f"Error looking up packages in repository {repository_url}: {e}")

            # Look up plugin by name
            for pkg in pkgs:
                if pkg['name'] == name:
                    plugin_id = pkg['plugin']
                    break
            else:
                module.fail_json(msg=f"No package named {name} in repository {repository_url}")

        return (repository_url, plugin_id)

    def search_plugin():
        """Helper function. We have a plugin name or ID, but no repository.

        Search all known repositories for the plugin."""

        nonlocal module, plugin_id, name, result
        # nonlocal result         # XXX - Debugging

        # XXX - Get list of known repositories.
        try:
            repositories = mw.call("plugin.official_repositories")
        except Exception as e:
            module.fail_json(msg=f"Error looking up repositories: {e}")

        # XXX - If plugin_id is given:
        #       - Search each repo for that ID
        # else (we only have a name):
        #       - Search each repo for the given name.
        result['debug_msg'] = ""    # XXX - Debug
        result['debug_msg'] += "Found repositories: {repositories}"
        for key, repo in repositories.items():
            # XXX - Get the packages in this repo
            result['debug_msg'] += f"Checking repository {repo}\n"    # XXX - Debug
            repo_url = repo['git_repository']

            # Get list of packages in this repo.
            try:
                packages = mw.job("plugin.available",
                                  {"plugin_repository": repo['git_repository']})
            except Exception as e:
                module.fail_json(msg=f"Error looking up packages in repo {repo['name']}: {e}")

            # Look for the package in this repo
            for pkg in packages:
                result['debug_msg'] += f"Package {pkg}\n"       # XXX -  Debug
                if plugin_id is None:
                    # Look by name
                    if pkg['name'] == name:
                        # Found it
                        result['debug_msg'] += "Found it\n"
                        return (repo_url, pkg['plugin'])
                else:
                    # Look by ID
                    if pkg['plugin'] == plugin_id:
                        # Found it
                        return (repo_url, pkg['plugin'])
        else:
            result['debug_msg'] += "Inside else clause\n"
            module.fail_json(msg=f"Can't find package {name if plugin_id is None else plugin_id} in any repository.")

        # module.fail_json(msg=f"Can't find package {name if plugin_id is None else plugin_id} in any repository.")
        result['debug_msg'] += "Dying at end of function\n"
        module.exit_json(**result)

    # def find_plugin():
    #     """Helper function to try to find the right repository and ID
    #     for the plugin."""

    #     nonlocal module, arg, repository_url, repository, \
    #         plugin_id, name

    #     # First, try to figure out which repository to use.
    #     # If 'repository_url' is specified, use that.
    #     # Otherwise, if 'repository' is specified, look it up by name.
    #     if repository_url is not None:
    #         # If you're going to specify the URL, we're going to
    #         # assume that you know the ID of the plugin. We're not
    #         # going to try to look it up from the human-friendly name.
    #         arg['plugin_repository'] = repository_url

    #         if plugin_id is not None:
    #             arg['plugin_name'] = plugin_id

    #             # If the caller was kind enough to give us both the
    #             # repository URL and the plugin ID, reward them by
    #             # exiting early, so we can be done more quickly.
    #             return

    #     # If we get here, we're missing either the repository URL, or
    #     # the plugin ID. Either way, we'll need the list of known
    #     # repositories
    #     try:
    #         repositories = mw.call("plugin.official_repositories")
    #     except Exception as e:
    #         module.fail_json(msg=f"Error looking up repositories: {e}")

    #     if repository_url is None and repository is not None:
    #         # We don't have the repository URL, but we have its
    #         # human-friendly name.

    #         # Find the repo whose human-friendly name is the one we
    #         # were given.
    #         repository_url = None
    #         for key, repo in repositories.items():
    #             if repo['name'] != repository:
    #                 # Nope. This isn't it.
    #                 continue

    #             # Found it.
    #             repository_url = repo['git_repository']
    #             arg['plugin_repository'] = repository_url
    #             break
    #         else:
    #             # Got to the end of the loop without finding anything.
    #             module.fail_json(msg=f"No such repository: {repository}")

    #     # We have the repository URL, but we might need to look up the
    #     # plugin ID.
    #     if repository_url is not None:
    #         if plugin_id is not None:
    #             # Great. We now have both the repo URL and the
    #             # plugin ID, so we can terminate early.
    #             arg['plugin_name'] = plugin_id
    #             return True
    #         elif name is not None:
    #             # We have the repo URL, but not the plugin ID. Find it
    #             # in the repo.
    #             try:
    #                 err = mw.job("plugin.available",
    #                              {"plugin_repository", repository_url})
    #             except Exception as e:
    #                 module.fail_json(msg=f"Can't find plugin {name} in repository {repository_url}")
    #             arg['plugin_name'] = err['plugin']

    #     # We still have to find the plugin ID.
    #     if plugin_id is not None:
    #         arg['plugin_name'] = plugin_id
    #         return True

    #     # if plugin_name is not None:
    #     #     # Search plugins in the repository. If we don't know
    #     #     # the repository yet, search all known repositories.

    module = AnsibleModule(
        argument_spec=dict(
            # XXX
            # - props
            #   - vnet (bool?)
            #   - boot
            #   - nat (bool?)
            #   - nat_forwards?
            # - branch (str)
            # - repository (str)

            # - enabled (bool) Whether it starts at boot time, similar
            #       to service 'enabled'
            #       Alias: 'boot'
            #       Defalt: True
            jail=dict(type='str', required=True),
            name=dict(type='str', aliases=['plugin']),
            plugin_id=dict(type='str'),
            state=dict(type='str', default='present',
                       choices=['absent', 'present']),
            repository_url=dict(type='str'),
            repository=dict(type='str'),
            ),
        supports_check_mode=True,
        # mutually_exclusive=[
        #     ['name', 'plugin_id'],
        #     ['repository_url', 'repository']],
        required_one_of=[
            ['name', 'plugin_id'],
            # ['repository_url', 'repository'],
        ],
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW()

    # Assign variables from properties, for convenience
    name = module.params['name']
    plugin_id = module.params['plugin_id']
    jail = module.params['jail']
    state = module.params['state']
    repository_url = module.params['repository_url']
    repository = module.params['repository']

    # Look up the plugin
    try:
        plugin_info = mw.call("plugin.query",
                              [["id", "=", jail]])
        if len(plugin_info) == 0:
            # No such plugin
            plugin_info = None
        else:
            # Plugin exists
            plugin_info = plugin_info[0]
    except Exception as e:
        module.fail_json(msg=f"Error looking up plugin {name}: {e}")

    # XXX - plugin.official_repositories() lists available repositories:
    # {
    #   "IXSYSTEMS": {
    #     "name": "iXsystems",
    #     "git_repository": "https://github.com/freenas/iocage-ix-plugins.git"
    #   },
    #   "COMMUNITY": {
    #     "name": "Community",
    #     "git_repository": "https://github.com/ix-plugin-hub/iocage-plugin-index.git"
    #   }
    # }

    # XXX - plugin.available() lists plugins available to install.
    # To search a particular repository:
    # {"plugin_repository":"<git_repository url>"}
    # Use the git_repository url from plugin.official_repositories().
    #   - plugin: id / slug?
    #   - license: str?
    #   - official: bool
    #   - icon (str)
    #   - version: version string
    #   - revision(str): ?
    #   - epoch(str): ?

    # XXX - To create a jail with plugin:
    # midclt call -job -jp description plugin.create '{"plugin_name":"bind","jail_name":"bind0","plugin_repository":"https://github.com/ix-plugin-hub/iocage-plugin-index.git"}'
    #
    # Prints a fair amount of somewhat interesting status.
    # Returns an object:
    # {"jid": 39, "name": "bind0", "boot": "on", "state": "up", "type": "pluginv2", "release": "13.1-RELEASE-p7", "ip4": "vnet0|172.16.0.10/30", "ip6": null, "template": null, "doc_url": null, "plugin": "bind", "plugin_repository": "https://github.com/ix-plugin-hub/iocage-plugin-index.git", "category": null, "maintainer": null, "id": "bind0", "plugin_info": null, "admin_portals": ["use shell"], "version": "9.16.39", "revision": "0", "epoch": "0", "install_notes": "named_enable:  -> YES\nnamed_enable:  -> YES\nwrote key file \"/usr/local/etc/namedb/rndc.key\"\nAdmin Portal:\nuse shell"}

    # XXX - I'd like to be able to:
    # - name: Install plugin foo
    #   plugin:
    #     name: foo
    #     jail: foo0
    #     [repository_url: https://blah/blah/blah/]
    #     [repository: iXsystems]
    #     [branch: main]
    #
    # A nice way for it to work would be:
    # - if repository_url is specified, look there.
    # - else, if repository is specified, look it up with
    #   plugin.official_repositories()
    # - else: look through all the repositories and use the first one
    #   that contains "foo".
    #   - Use plugin.available({"plugin_repository":<url>}) to find
    #     available plugins.

    # First, check whether the plugin is installed.
    if plugin_info is None:
        # Plugin doesn't exist

        if state == 'present':
            # Plugin is supposed to exist, so create it.

            # Collect arguments to pass to plugin.create()
            arg = {
                "jail_name": jail,
            }

            if repository_url is None and repository is None:
                # We don't know which repo the plug in is in, so we'll
                # need to search them all.
                (repository_url, plugin_id) = search_plugin()
            else:
                # We have either the name or URL of the repository.
                # Find the plugin there.
                (repository_url, plugin_id) = lookup_plugin()

            arg['plugin_repository'] = repository_url
            arg['plugin_name'] = plugin_id

            # Other features the caller might set:
            # If feature is not None:
            #     arg['feature'] = feature

            if module.check_mode:
                result['msg'] = f"Would have created plugin {name if plugin_id is None else plugin_id} with {arg}"
            else:
                #
                # Create new plugin
                #
                try:
                    err = mw.call("plugin.create", arg)
                    result['msg'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating plugin {name}: {e}")

                # Return whichever interesting bits plugin.create()
                # returned.
                result['plugin'] = err

            result['changed'] = True
        else:
            # Plugin is not supposed to exist.
            # All is well
            result['changed'] = False

    else:
        # Plugin exists
        if state == 'present':
            # Plugin is supposed to exist

            # Make list of differences between what is and what should
            # be.
            arg = {}

            # if feature is not None and plugin_info['feature'] != feature:
            #     arg['feature'] = feature

            # If there are any changes, plugin.update()
            if len(arg) == 0:
                # No changes
                result['changed'] = False
            else:
                #
                # Update plugin.
                #
                if module.check_mode:
                    result['msg'] = f"Would have updated plugin {name}: {arg}"
                else:
                    try:
                        err = mw.call("plugin.update",
                                      plugin_info['id'],
                                      arg)
                    except Exception as e:
                        module.fail_json(msg=f"Error updating plugin {name} with {arg}: {e}")
                        # Return any interesting bits from err
                        result['status'] = err['status']
                result['changed'] = True
        else:
            # Plugin is not supposed to exist

            if module.check_mode:
                result['msg'] = f"Would have deleted plugin {name}"
            else:
                try:
                    #
                    # Delete plugin.
                    #
                    err = mw.call("plugin.delete",
                                  plugin_info['id'])
                except Exception as e:
                    module.fail_json(msg=f"Error deleting plugin {name}: {e}")
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
