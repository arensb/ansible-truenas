#!/usr/bin/python
__metaclass__ = type

# Manage plugins.

# XXX - 'state' only accepts {present, absent}. But docstring says
# it accepts running, stopped, and restarted.

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
#
# midclt call plugin.defaults \
#    '{"plugin":"calibre-web",
#    "plugin_repository":"https://github.com/ix-plugin-hub/iocage-plugin-index.git"}'

# XXX - A plugin is basically a jail, with software installed on top.
# A lot of the configuration is the same, though, like networking, and
# mounting filesystems.
#
# So to the extent possible, the options for 'plugin' should match the
# ones for 'jail'.

DOCUMENTATION = '''
---
module: plugin
short_description: Manage plugins.
description:
  - Install, remove, and manage TrueNAS plugins.
options:
  enabled:
    description:
      - Whether the plugin is started at boot time.
    type: bool
  # jail:
  #   description:
  #     - Name of the jail in which this instance of the plugin will be
  #       installed.
  #     - This is a jail identifier. See the I(jail) module for more
  #       details.
  #   type: str
  name:
    description:
      - Name of the plugin instance.
      - "This is different from the plugin package: you can run multiple
        copies of the same software package in different jails, if you
        give them all unique names."
    type: str
    required: true
  plugin:
    description:
      - The human-friendly name of the plugin, as displayed in the TrueNAS
        console.
      - If I(plugin_id) is supplied, C(plugin) is ignored.
  plugin_id:
    description:
      - The ID or slug of the plugin. Unlike the name, this is not
        displayed in the TrueNAS web UI.
      - Overrides I(plugin).
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
      - "'running' and 'stopped' allow you to make sure the plugin's
        jail is up or down."
      - "'restarted' will restart the plugin's jail, similar to rebooting it."
    type: str
    choices: [ absent, present, restarted, running, stopped ]
    default: present
version_added: 1.1.0
'''

# XXX
EXAMPLES = '''
- name: Install a plugin by name from any collection
  arensb.truenas.plugin:
    name: Plex
    plugin: Plex Media Server

- name: Install a plugin by name from a specific collection
  arensb.truenas.plugin:
    name: Plex 2
    plugin: Plugin Media Server
    repository: iXsystems

- name: "Fully specified: use both plugin ID and repository URL"
  arensb.truenas.plugin:
    name: Plex 3
    plugin_id: plexmediaserver
    repository_url: https://github.com/ix-plugin-hub/iocage-plugin-index.git

# Install two instances of a plugin in different jails.
- arensb.truenas.plugin:
    name: Brad's Library
    plugin: Calibre-Web
    repository: Community
- arensb.truenas.plugin:
    name: Janet's Library
    plugin: Calibre-Web
    repository: Community
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
            plugin_id, plugin

        # First step: if we don't have a repo URL, look it up from the
        # collection name.
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
                if pkg['name'] == plugin:
                    plugin_id = pkg['plugin']
                    break
            else:
                module.fail_json(msg=f"No package named {plugin} in repository {repository_url}")

        return (repository_url, plugin_id)

    def search_plugin():
        """Helper function. We have a plugin name or ID, but no repository.

        Search all known repositories for the plugin."""

        nonlocal module, plugin_id, plugin, result

        # XXX - I think that if the plugin_id is given, that's all we
        # need: we can save time and let the middleware do the lookup.

        # Get list of known repositories.
        try:
            repositories = mw.call("plugin.official_repositories")
        except Exception as e:
            module.fail_json(msg=f"Error looking up repositories: {e}")

        for key, repo in repositories.items():
            # Get the packages in this repo
            repo_url = repo['git_repository']

            # Get list of packages in this repo.
            try:
                packages = mw.job("plugin.available",
                                  {"plugin_repository": repo['git_repository']})
            except Exception as e:
                module.fail_json(msg=f"Error looking up packages in repo {repo['name']}: {e}")

            # Look for the package in this repo
            for pkg in packages:
                if plugin_id is None:
                    # Look by name
                    if pkg['name'] == plugin:
                        # Found it
                        return (repo_url, pkg['plugin'])
                else:
                    # Look by ID
                    if pkg['plugin'] == plugin_id:
                        # Found it
                        return (repo_url, pkg['plugin'])
        else:
            module.fail_json(msg=f"Can't find package {plugin if plugin_id is None else plugin_id} in any repository.")

        module.fail_json(msg="Should never get this far.")

    module = AnsibleModule(
        argument_spec=dict(
            # XXX
            # - props
            #   - vnet (bool?)
            #   - boot
            #   - nat (bool?)
            #   - nat_forwards?
            # - branch (str)

            # - enabled (bool) Whether it starts at boot time, similar
            #       to service 'enabled'
            #       Alias: 'boot'
            #       Defalt: True
            name=dict(type='str', required=True),
            plugin=dict(type='str'),
            plugin_id=dict(type='str'),
            state=dict(type='str', default='present',
                       choices=['absent', 'present']),
            repository=dict(type='str'),
            repository_url=dict(type='str'),
            enabled=dict(type='bool'),
            ),
        supports_check_mode=True,
        # mutually_exclusive=[
        #     ['plugin', 'plugin_id'],
        #     ['repository_url', 'repository']],
        required_one_of=[
            ['plugin', 'plugin_id'],
        ],
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW.client()

    # Assign variables from properties, for convenience
    name = module.params['name']
    plugin = module.params['plugin']
    plugin_id = module.params['plugin_id']
    state = module.params['state']
    repository = module.params['repository']
    repository_url = module.params['repository_url']
    enabled = module.params['enabled']

    # Look up the plugin
    try:
        plugin_info = mw.call("plugin.query",
                              [["name", "=", name]])
        if len(plugin_info) == 0:
            # No such plugin
            plugin_info = None
        else:
            # Plugin exists
            plugin_info = plugin_info[0]
    except Exception as e:
        module.fail_json(msg=f"Error looking up plugin {name}: {e}")

    # First, check whether the plugin is installed.
    if plugin_info is None:
        # Plugin doesn't exist

        if state == 'present':
            # Plugin is supposed to exist, so create it.
            #
            # At the very least, need: {
            #    jail_name: <name>,
            #    plugin_name: <plugin_id>,
            # }

            # XXX - Props:
            # midclt call ... plugin.create
            #   {
            #     "jail_name": "my jail",
            #     "plugin_name":"minio",
            #     "props": [
            #        "boot=off"
            #     ]
            #   }

            # Collect arguments to pass to plugin.create()
            arg = {
                "jail_name": name,
            }
            props = []

            if repository_url is None and repository is None:
                # We don't know which repo the plug in is in, so we'll
                # need to search them all.
                (repository_url, plugin_id) = search_plugin()
            else:
                # We have either the name or URL of the repository.
                # Find the plugin there.
                (repository_url, plugin_id) = lookup_plugin()

            if repository_url is not None:
                arg['plugin_repository'] = repository_url
            arg['plugin_name'] = plugin_id

            # Other features the caller might set:
            if enabled is not None:
                props.append(f"boot={'yes' if enabled else 'no'}")

            if len(props) > 0:
                arg['props'] = props

            if module.check_mode:
                result['msg'] = f"Would have created plugin {name} with {arg}"
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
                result['msg'] = f"Would have stopped and deleted plugin {name}"
            else:
                # Stop the jail
                if plugin_info['jid'] is not None:
                    try:
                        err = mw.job("jail.stop", name)
                    except Exception as e:
                        module.fail_json(msg=f"Error stopping jail {name}): {e}")

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
