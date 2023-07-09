# Ansible Collection - arensb.truenas

Control a TrueNAS box using its API.

## Supported versions of Ansible
- Tested with 2.10.8

## Included content

This collection consists primarily of a set of Ansible modules to
configure a TrueNAS machine, using the
[TrueNAS API](https://www.truenas.com/docs/api/websocket.html)
to control the Middleware Daemon.

There are several ways to talk to the Middleware, but at present this
collection only supports running `midclt` commands on the box. So you
will need root access there, just as for any other Ansible client. In
the future, it may support RESTful control.

### Modules
Name                                | Description
----------------------------------- | ------------------
`arensb.truenas.filesystem`         | Manage ZFS filesystems.
`arensb.truenas.group`              | Manage Unix groups.
`arensb.truenas.hostname`           | Set the hostname.
`arensb.truenas.jail`               | Set up a jail.
`arensb.truenas.jails`              | Manage the jail system.
`arensb.truenas.nfs`                | Manage NFS service configuration.
`arensb.truenas.plugin`             | Manage plugins and their jails.
`arensb.truenas.pool_snapshot_task` | Periodic snapshots of ZFS volumes.
`arensb.truenas.service`            | Manage services.
`arensb.truenas.sharing_nfs`        | Manage NFS exports.
`arensb.truenas.sharing_smb`        | Manage SMB shares.
`arensb.truenas.systemdataset`      | Manage the system dataset.
`arensb.truenas.user`               | Manage users.

## Installing this collection

The easiest way to install this collection is
[through Ansible Galaxy](https://galaxy.ansible.com/arensb/truenas):

    ansible-galaxy collection install arensb.truenas

<!--
If you want a git repository, e.g., for development:

1. Pick a directory `/my/collections/ansible_collections` to put the collection in.
2. Make sure that in your `ansible.cfg`, you have
 -->

## Examples

    - name: Example tasks
      collections:
        - arensb.truenas
      hosts: truenas-box
      become: yes
      tasks:
        - name: Set the hostname
          hostname:
            name: new-hostname
        - name: Turn on sshd
          service:
            name: sshd

Note that since several of the module names are the same as builtin
ones, you may want to use the full name to avoid confusion:

    - hosts: truenas-box
      become: yes
      tasks:
        - arensb.truenas.hostname:
            name: new-hostname

The individual modules also have documentation strings, and should work with
`ansible-doc`, e.g.:

    ansible-doc -t module arensb.truenas.user

## Environment Variables

### `middleware_method`

There are two ways of communicating with the middleware daemon on
TrueNAS, referred to here as `midclt` and `client`. `midclt` is older
and better-tested, while `client` is faster but less-well-tested. The
default is `client`.

Set the `middleware_method` environment variable to either `client` or
`midclt` at either the play or task level in your playbook to manually
select how this module communicates with the middleware daemon.

Example:

    - collections: arensb.truenas
      hosts: my-nas
      become: yes
      environment:
        middleware_method: client
      tasks:
        - name: Create a jail
          jail:
            name: my-jail
            release: 13.1-RELEASE
            state: running

## Contributing to this collection
The best way to contribute a patch or feature is to create a pull request.

The `plugins/modules/template` file provides a starting point for new modules.

## Changelog
See [changelog.yaml](changelogs/changelog.yaml)

## Authors and Contributors

- Andrew Arensburger ([@arensb](https://mastodon.social/@arensb))
- Ed Hull (https://github.com/edhull)
